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
use config::WordlistConfig;
use executor::queue::{Task, TaskQueue};
use executor::runner::TaskRunner;
use output::parser::OutputParser;
use output::reporter::ReportGenerator;
use std::fs;
use std::path::PathBuf;
use system::detect::is_running_as_root;
use tokio::sync::mpsc;
use tools::{ToolChecker, ToolRegistry};
use ui::TerminalUI;

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Detect sudo/root privileges at startup
    let running_as_root = is_running_as_root();
    if running_as_root {
        println!("Running with elevated privileges (sudo/root)");
    } else {
        println!("Running without elevated privileges");
        println!("Note: Some tools may require sudo for optimal results");
    }

    // Load wordlist configuration
    let wordlist_config = WordlistConfig::load_default().unwrap_or_else(|e| {
        eprintln!("Warning: Failed to load wordlist config: {}", e);
        eprintln!("Using default wordlist path");
        WordlistConfig {
            wordlists: std::collections::HashMap::new(),
        }
    });

    let wordlist_path = wordlist_config.resolve(&cli.wordlist).unwrap_or_else(|_| {
        eprintln!(
            "Warning: Wordlist '{}' not found, using as direct path",
            cli.wordlist
        );
        cli.wordlist.clone()
    });

    println!("Using wordlist: {}", wordlist_path);

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
        eprintln!(
            "No tools found in {}. Please add YAML tool definitions.",
            cli.tools_dir.display()
        );
        std::process::exit(1);
    }

    println!("Loaded {} tools", tool_count);

    // Perform comprehensive tool availability check
    let checker = ToolChecker::new();
    let all_tools: Vec<&_> = registry.get_all_tools();
    let availability_report = checker.check_all_tools(&all_tools);

    println!("\nChecking tool availability...");
    println!("{}", checker.get_installation_summary(&availability_report));

    if availability_report.missing_count > 0 {
        let install_all = checker.prompt_install_all(&availability_report)?;

        if install_all {
            checker.install_missing_tools(&availability_report)?;
        } else {
            checker.prompt_individual_installs(&availability_report)?;
        }

        // Re-check tool availability after installation
        println!("\nVerifying installed tools...");
        let all_tools: Vec<&_> = registry.get_all_tools();
        let verification_report = checker.check_all_tools(&all_tools);

        if verification_report.missing_count > 0 {
            eprintln!(
                "\nWARNING: {} tools are still missing after installation:",
                verification_report.missing_count
            );
            for status in &verification_report.tools {
                if !status.installed {
                    eprintln!("  ✗ {} (binary: {})", status.name, status.binary);
                }
            }
            eprintln!("\nThe scan will proceed but these tools will be skipped.");
        } else {
            println!("✓ All tools are now installed and available!");
        }
    }

    println!("\nGenerating tasks...");
    let mut queue = TaskQueue::new();

    // Get final tool availability status
    let all_tools: Vec<&_> = registry.get_all_tools();
    let final_check = checker.check_all_tools(&all_tools);

    // Create a hashset of installed tool names for quick lookup
    let installed_tools: std::collections::HashSet<String> = final_check
        .tools
        .iter()
        .filter(|status| status.installed)
        .map(|status| status.name.clone())
        .collect();

    for tool in registry.get_all_tools() {
        // Skip tools that are not installed
        if !installed_tools.contains(&tool.name) {
            continue;
        }

        for target in &targets {
            // Check if tool needs all ports at once (batch scanning like nmap)
            let needs_ports_batch = tool.command.contains("{{ports}}")
                || tool
                    .sudo_command
                    .as_ref()
                    .is_some_and(|c| c.contains("{{ports}}"));

            // Check if tool needs individual port scanning
            let needs_port_individual = tool.command.contains("{{port}}")
                || tool
                    .sudo_command
                    .as_ref()
                    .is_some_and(|c| c.contains("{{port}}"));

            if needs_ports_batch {
                // Create ONE task that scans all ports (efficient for nmap, masscan, etc.)
                match Task::new_with_ports(
                    tool,
                    target.clone(),
                    &ports,
                    &output_dir,
                    running_as_root,
                    Some(&wordlist_path),
                ) {
                    Ok(task) => queue.add_task(task),
                    Err(e) => eprintln!("Failed to create task: {}", e),
                }
            } else if needs_port_individual {
                // Create one task per port (for port-specific tools like nikto, whatweb)
                for port in &ports {
                    match Task::new(
                        tool,
                        target.clone(),
                        Some(*port),
                        &output_dir,
                        running_as_root,
                        Some(&wordlist_path),
                    ) {
                        Ok(task) => queue.add_task(task),
                        Err(e) => eprintln!("Failed to create task: {}", e),
                    }
                }
            } else {
                // Tool doesn't need ports (like whois, ping, traceroute)
                match Task::new(
                    tool,
                    target.clone(),
                    None,
                    &output_dir,
                    running_as_root,
                    Some(&wordlist_path),
                ) {
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

    let ui_handle = tokio::spawn(async move { ui.run(update_rx).await });

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

    ReportGenerator::generate_markdown(&all_findings, &results, &targets, &ports, &output_dir)?;

    ReportGenerator::save_json(&all_findings, &results, &output_dir)?;

    ReportGenerator::save_individual_logs(&results, &output_dir)?;

    println!("\nScan complete!");
    println!("Reports saved to: {}", output_dir.display());
    println!("  - report.md: Markdown summary report");
    println!("  - results.json: JSON results");
    println!("  - logs/: Individual tool outputs");

    Ok(())
}
