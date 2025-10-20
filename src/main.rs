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
            show_stats,
            reset_stats: _,
        }) => {
            if show_stats {
                return show_cost_stats().await;
            }
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
            println!("{} Scan completed successfully", "Success:".green());
        }
        Err(e) => {
            eprintln!("{} Scan failed: {}", "Error:".red(), e);
            process::exit(1);
        }
    }

    Ok(())
}

async fn show_cost_stats() -> anyhow::Result<()> {
    let cost_tracker = CostTracker::new(0.01)?;
    
    println!("{} Cost Usage Statistics", "Statistics:".cyan());
    println!("{}", "─".repeat(50));
    
    // Show daily usage
    let daily_usage = cost_tracker.get_daily_usage();
    println!("{} ${:.4} ({} requests)", "Daily Usage:".green(), daily_usage.cost, daily_usage.requests);
    
    // Show monthly usage
    let monthly_usage = cost_tracker.get_monthly_usage();
    println!("{} ${:.4} ({} requests)", "Monthly Usage:".green(), monthly_usage.cost, monthly_usage.requests);
    
    println!("\n{} Per-Provider Usage:", "Details:".yellow());
    
    // Try to show some provider usage (limited without full provider list access)
    if let Some(openai_usage) = cost_tracker.get_provider_usage("openai") {
        println!("  OpenAI: ${:.4} ({} requests)", openai_usage.cost, openai_usage.requests);
    }
    if let Some(groq_usage) = cost_tracker.get_provider_usage("groq") {
        println!("  Groq: ${:.4} ({} requests)", groq_usage.cost, groq_usage.requests);
    }
    if let Some(openrouter_usage) = cost_tracker.get_provider_usage("openrouter") {
        println!("  OpenRouter: ${:.4} ({} requests)", openrouter_usage.cost, openrouter_usage.requests);
    }
    if let Some(ollama_usage) = cost_tracker.get_provider_usage("ollama") {
        println!("  Ollama: ${:.4} ({} requests)", ollama_usage.cost, ollama_usage.requests);
    }
    
    // Show message if no provider usage found
    if cost_tracker.get_provider_usage("openai").is_none() && 
       cost_tracker.get_provider_usage("groq").is_none() && 
       cost_tracker.get_provider_usage("openrouter").is_none() && 
       cost_tracker.get_provider_usage("ollama").is_none() {
        println!("  No provider usage data available yet.");
    }
    
    Ok(())
}

fn is_valid_target(target: &str) -> bool {
    // Accept IP addresses or domain names
    target.parse::<std::net::IpAddr>().is_ok() || 
    regex::Regex::new(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$").unwrap().is_match(target)
}