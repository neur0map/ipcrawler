mod cli;
mod config;
mod executor;
mod output;
mod system;
mod tools;
mod ui;

use anyhow::Result;
use chrono::Local;
use clap::Parser;
use cli::{parse_ports, parse_targets, Cli};
use executor::queue::{Task, TaskQueue};
use executor::runner::TaskRunner;
use output::parser::OutputParser;
use output::reporter::ReportGenerator;
use std::fs;
use std::path::PathBuf;
use tokio::sync::mpsc;
use tools::{ToolInstaller, ToolRegistry};
use ui::TerminalUI;

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    let targets = parse_targets(&cli.target)?;
    let ports = parse_ports(&cli.ports)?;

    let output_dir = cli.output.unwrap_or_else(|| {
        let timestamp = Local::now().format("%Y%m%d_%H%M%S");
        PathBuf::from(format!("./ipcrawler-results/{}", timestamp))
    });

    fs::create_dir_all(&output_dir)?;

    println!("Loading tools from: {}", cli.tools_dir.display());
    let mut registry = ToolRegistry::new(&cli.tools_dir);
    let tool_count = registry.discover_tools()?;

    if tool_count == 0 {
        eprintln!("No tools found in {}. Please add YAML tool definitions.", cli.tools_dir.display());
        std::process::exit(1);
    }

    println!("Loaded {} tools", tool_count);

    let installer = ToolInstaller::new(cli.install);

    println!("Checking tool installations...");
    for tool in registry.get_all_tools() {
        match installer.ensure_tool_installed(tool) {
            Ok(true) => {}
            Ok(false) => {
                eprintln!("Tool '{}' not installed. Skipping.", tool.name);
            }
            Err(e) => {
                eprintln!("Error installing tool '{}': {}", tool.name, e);
            }
        }
    }

    println!("\nGenerating tasks...");
    let mut queue = TaskQueue::new();

    for tool in registry.get_all_tools() {
        for target in &targets {
            if tool.command.contains("{{port}}") {
                for port in &ports {
                    match Task::new(tool, target.clone(), Some(*port), &output_dir) {
                        Ok(task) => queue.add_task(task),
                        Err(e) => eprintln!("Failed to create task: {}", e),
                    }
                }
            } else {
                match Task::new(tool, target.clone(), None, &output_dir) {
                    Ok(task) => queue.add_task(task),
                    Err(e) => eprintln!("Failed to create task: {}", e),
                }
            }
        }
    }

    let total_tasks = queue.len();
    println!("Created {} tasks", total_tasks);

    if total_tasks == 0 {
        eprintln!("No tasks to execute. Exiting.");
        std::process::exit(1);
    }

    let runner = TaskRunner::new(5);

    let (update_tx, update_rx) = mpsc::unbounded_channel();

    let mut ui = TerminalUI::new(targets.clone(), ports.clone());

    let tasks: Vec<Task> = {
        let mut task_list = Vec::new();
        while let Some(task) = queue.pop() {
            task_list.push(task);
        }
        task_list
    };

    let ui_handle = tokio::spawn(async move {
        ui.run(update_rx).await
    });

    let results = runner.run_tasks(tasks.clone(), update_tx).await;

    let _ = ui_handle.await;

    println!("\nProcessing results...");

    let mut all_findings = Vec::new();

    for result in &results {
        if let Some(tool) = registry.get_tool(&result.tool_name) {
            match OutputParser::parse(tool, result) {
                Ok(findings) => {
                    all_findings.extend(findings);
                }
                Err(e) => {
                    eprintln!("Error parsing output for {}: {}", result.tool_name, e);
                }
            }
        }
    }

    all_findings = OutputParser::deduplicate(all_findings);
    OutputParser::sort_by_severity(&mut all_findings);

    println!("Found {} findings", all_findings.len());

    println!("\nGenerating reports...");

    ReportGenerator::generate_markdown(
        &all_findings,
        &results,
        &targets,
        &ports,
        &output_dir,
    )?;

    ReportGenerator::save_json(&all_findings, &results, &output_dir)?;

    ReportGenerator::save_individual_logs(&results, &output_dir)?;

    println!("\nScan complete!");
    println!("Reports saved to: {}", output_dir.display());
    println!("  - report.md: Markdown summary report");
    println!("  - results.json: JSON results");
    println!("  - logs/: Individual tool outputs");

    Ok(())
}
