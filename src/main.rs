use clap::Parser;
use colored::*;

use tokio;

mod cli;
mod executor;
mod template;
mod reporter;
mod output;

use cli::Args;
use executor::Executor;
use template::TemplateManager;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    
    // Validate IP(s)
    for ip in &args.targets {
        if !is_valid_ip(ip) {
            eprintln!("{} Invalid IP address: {}", "Error:".red(), ip);
            std::process::exit(1);
        }
    }

    // Initialize template manager
    let template_manager = TemplateManager::new("templates")?;
    
    // Initialize executor
    let mut executor = Executor::new(
        args.targets.clone(),
        args.output.clone(),
        args.verbose,
        template_manager,
    )?;
    
    // Run reconnaissance
    executor.execute().await?;
    
    println!("\n{} IPCrawler completed successfully!", "✓".green());
    Ok(())
}

fn is_valid_ip(ip: &str) -> bool {
    ip.parse::<std::net::IpAddr>().is_ok()
}
