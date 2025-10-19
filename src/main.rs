use clap::Parser;
use colored::*;
use std::process;

mod cli;
mod providers;
mod core;
mod storage;
mod optimization;
mod cost;
mod template;
mod report;

use cli::Args;
use cli::commands::Commands;
use cli::keys::KeyCommands;
use core::detector::SystemDetector;
use core::executor::Executor;
use core::parser::LLMParser;
use storage::secure::SecureKeyStore;
use template::manager::TemplateManager;
use cost::tracker::CostTracker;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();

    match args.command {
        Some(Commands::Keys(key_action)) => {
            let keys_cmd = KeyCommands { action: key_action };
            return cli::keys::handle_keys_command(keys_cmd).await;
        }
        Some(Commands::Scan {
            targets,
            output,
            port_range,
            verbose,
            llm_provider,
            max_cost_per_request,
            show_stats: _,
            reset_stats: _,
        }) => {
            return execute_scan(
                targets,
                output,
                port_range,
                verbose,
                llm_provider,
                max_cost_per_request,
            ).await;
        }
        None => {
            // If no subcommand, check if targets were provided directly
            if !args.targets.is_empty() {
                return execute_scan(
                    args.targets,
                    args.output,
                    args.port_range,
                    args.verbose,
                    args.llm_provider,
                    args.max_cost_per_request,
                ).await;
            } else {
                // No targets and no subcommand, show help
                eprintln!("{} No targets specified. Usage:", "Error:".red());
                eprintln!("  ipcrawler <target>                    # Scan target");
                eprintln!("  ipcrawler scan <target>               # Scan target with explicit command");
                eprintln!("  ipcrawler keys <subcommand>           # Manage API keys");
                eprintln!("  ipcrawler --help                      # Show all options");
                process::exit(1);
            }
        }
    }
}

async fn execute_scan(
    targets: Vec<String>,
    output: Option<std::path::PathBuf>,
    port_range: Option<String>,
    verbose: bool,
    llm_provider: Option<String>,
    max_cost_per_request: f64,
) -> anyhow::Result<()> {
    // Validate targets
    if targets.is_empty() {
        eprintln!("{} No targets specified", "Error:".red());
        process::exit(1);
    }

    for target in &targets {
        if !is_valid_target(target) {
            eprintln!("{} Invalid target: {}", "Error:".red(), target);
            process::exit(1);
        }
    }

    // Initialize system components
    let detector = SystemDetector::new()?;
    let key_store = SecureKeyStore::new()?;
    let template_manager = TemplateManager::new("templates")?;
    let cost_tracker = CostTracker::new(max_cost_per_request)?;
    let llm_parser = LLMParser::new(
        key_store,
        cost_tracker,
        llm_provider,
        verbose,
    )?;

    // Initialize executor
    let mut executor = Executor::new(
        targets,
        output,
        verbose,
        port_range,
        detector,
        template_manager,
        llm_parser,
    )?;

    // Execute reconnaissance
    match executor.execute().await {
        Ok(_) => {
            println!("\n{} IPCrawler completed successfully!", "✓".green());
            Ok(())
        }
        Err(e) => {
            eprintln!("{} {}", "Error:".red(), e);
            process::exit(1);
        }
    }
}

fn is_valid_target(target: &str) -> bool {
    // Accept IP addresses or domain names
    target.parse::<std::net::IpAddr>().is_ok() || 
    regex::Regex::new(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$").unwrap().is_match(target)
}