mod cli;
mod config;
mod display;
mod parser;
mod storage;
mod templates;

use anyhow::{Context, Result};
use chrono::Utc;
use clap::Parser;
use cli::{Cli, Commands};
use colored::Colorize;
use config::Config;
use parser::{EntityExtractor, LlmParser};
use storage::{OutputManager, ReportManager};
use templates::{TemplateExecutor, TemplateParser, TemplateSelector};
use tracing::{error, info};

const VERSION: &str = env!("CARGO_PKG_VERSION");

fn print_version() {
    let art = r#"
    ___ ____   ____                    _           
   |_ _|  _ \ / ___|_ __ __ ___      _| | ___ _ __ 
    | || |_) | |   | '__/ _` \ \ /\ / / |/ _ \ '__|
    | ||  __/| |___| | | (_| |\ V  V /| |  __/ |   
   |___|_|    \____|_|  \__,_| \_/\_/ |_|\___|_|   
    "#;

    println!("{}", art.cyan().bold());
    println!("  {} {}\n", "Version".bold(), VERSION.yellow());
    println!("  Intelligent Penetration Testing Scanner");
    println!("  AI-powered output parsing - No hardcoded regex");
    println!(
        "\n  {} https://github.com/yourusername/ipcrawler",
        "Repository:".dimmed()
    );
    println!("  {} MIT\n", "License:".dimmed());
}

#[tokio::main]
async fn main() -> Result<()> {
    // Check for version flag first to show ASCII art
    if std::env::args().any(|arg| arg == "-V" || arg == "--version") {
        print_version();
        return Ok(());
    }

    let mut cli = Cli::parse();

    // Handle setup and config commands early (before loading config)
    match &cli.command {
        Some(Commands::Setup) => {
            println!(); // Ensure clean line before setup
            return config::setup::SetupWizard::run();
        }
        Some(Commands::Config) => {
            let cfg = Config::load()?;
            cfg.display_masked();
            return Ok(());
        }
        _ => {}
    }

    // Load config and merge with CLI args
    let cfg = Config::load()?;
    cli = cli.merge_with_config(cfg);

    init_logging(cli.verbose);

    if let Err(e) = cli.validate() {
        eprintln!("{} {}", "Error:".red().bold(), e);
        std::process::exit(1);
    }

    match &cli.command {
        Some(Commands::List) => list_templates(&cli).await?,
        Some(Commands::Show { template }) => show_template(&cli, template).await?,
        Some(Commands::Setup) | Some(Commands::Config) => {
            // Already handled above
        }
        None => run_scan(cli).await?,
    }

    Ok(())
}

fn init_logging(verbose: bool) {
    let filter = if verbose {
        "ipcrawler=debug"
    } else {
        "ipcrawler=warn" // Only warnings and errors in normal mode
    };

    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .without_time()
        .init();
}

async fn run_scan(cli: Cli) -> Result<()> {
    let target = cli.target.as_ref().unwrap();
    let output_path = cli.get_output_path();
    let verbose = cli.verbose;

    if !verbose {
        println!("{}", "IPCrawler".cyan().bold());
        println!("Target: {} | Output: {}", target, output_path.display());
    } else {
        println!(
            "{}",
            "IPCrawler - Intelligent Penetration Testing Scanner"
                .cyan()
                .bold()
        );
        println!("{} {}", "Target:".bold(), target);
        println!("{} {}\n", "Output:".bold(), output_path.display());
    }

    let output_manager = OutputManager::new(output_path.clone());
    output_manager.initialize().await?;

    info!("Loading templates from: {}", cli.templates_dir.display());
    let parser = TemplateParser::new(cli.templates_dir.clone());
    let all_templates = parser.load_all().context("Failed to load templates")?;

    if all_templates.is_empty() {
        error!("No templates found in {}", cli.templates_dir.display());
        anyhow::bail!("No templates available");
    }

    info!("Found {} templates", all_templates.len());

    let selector = TemplateSelector::new();
    let selected_templates = selector.select_templates(all_templates);

    if selected_templates.is_empty() {
        error!("No templates selected for execution");
        anyhow::bail!("No templates to execute");
    }

    if verbose {
        println!(
            "\n{} {} templates\n",
            "Executing".green().bold(),
            selected_templates.len()
        );
    } else {
        println!("\nRunning {} tools...\n", selected_templates.len());
    }

    let start_time = Utc::now();
    let executor = TemplateExecutor::new(
        target.clone(),
        output_path.to_string_lossy().to_string(),
        verbose,
    );
    let results = executor.execute_all(selected_templates).await;

    let successful = results.iter().filter(|r| r.success).count();
    let failed = results.len() - successful;

    // Calculate total time (sum of all individual tool times)
    let total_time: f64 = results.iter().map(|r| r.duration.as_secs_f64()).sum();

    println!(
        "\n{} completed, {} failed ({:.2}s)\n",
        successful.to_string().green(),
        failed.to_string().red(),
        total_time
    );

    // Show error details for failed tools
    if failed > 0 {
        println!("{}", "[Failed Tools Details]".red().bold());
        println!("{}", "-".repeat(60).dimmed());
        for result in results.iter().filter(|r| !r.success) {
            println!("\n  {} {}", "Tool:".bold(), result.template_name.yellow());
            if let Some(error) = result.get_error_details() {
                let error_preview = if error.len() > 200 {
                    format!("{}...", &error[..200])
                } else {
                    error
                };
                println!("  {} {}", "Error:".bold(), error_preview.dimmed());
            }
        }
        println!();
    }

    // Show tool output previews in verbose mode
    if verbose && !results.is_empty() {
        println!("{}", "[Tool Output Previews]".cyan().bold());
        println!("{}", "-".repeat(60));
        for result in results.iter().filter(|r| r.success) {
            println!("\n  {} {}", "Tool:".bold(), result.template_name.cyan());
            let preview = result.get_output_preview(10);
            if !preview.is_empty() {
                for line in preview.lines() {
                    println!("    {}", line.dimmed());
                }
            } else {
                println!("    {}", "(no output)".dimmed());
            }
        }
        println!();
    }

    let llm_parser = if !cli.no_parse {
        match LlmParser::new(
            &cli.llm_provider,
            cli.llm_model.clone(),
            cli.llm_api_key.clone().unwrap_or_default(),
        ) {
            Ok(parser) => {
                println!("{}", "Parsing outputs with LLM...".cyan());
                Some(parser)
            }
            Err(e) => {
                error!("Failed to initialize LLM parser: {}", e);
                println!("{}", "Warning: Skipping LLM parsing".yellow());
                None
            }
        }
    } else {
        None
    };

    let extractor = EntityExtractor::new(llm_parser);
    let mut all_entities = Vec::new();

    for result in &results {
        if result.success {
            if let Some(output_file) = &result.output_file {
                match tokio::fs::read_to_string(output_file).await {
                    Ok(content) => match extractor.extract(&result.template_name, &content).await {
                        Ok(entities) => all_entities.push(entities),
                        Err(e) => error!(
                            "Failed to extract entities from {}: {}",
                            result.template_name, e
                        ),
                    },
                    Err(e) => error!("Failed to read output file {}: {}", output_file, e),
                }
            }
        }
    }

    let merged_entities = extractor.merge_entities(all_entities);

    ReportManager::save_entities(&merged_entities, &output_manager.get_entities_file()).await?;

    let report =
        ReportManager::build_report(target.clone(), start_time, results, merged_entities.clone());

    ReportManager::save_report(&report, &output_manager.get_report_file()).await?;

    // Display human-readable results in terminal
    use display::{HtmlReport, MarkdownReport, TerminalDisplay};

    TerminalDisplay::display_entities(&merged_entities, target);
    TerminalDisplay::display_summary(
        target,
        report.duration,
        report.summary.total_tools,
        report.summary.successful_tools,
        &merged_entities,
    );

    // Generate HTML and Markdown reports
    if let Err(e) = HtmlReport::generate(&report, &merged_entities, &output_manager).await {
        error!("Failed to generate HTML report: {}", e);
    }

    if let Err(e) = MarkdownReport::generate(&report, &merged_entities, &output_manager).await {
        error!("Failed to generate Markdown report: {}", e);
    }

    println!("\n{}", "[Scan completed successfully]".green().bold());
    println!("\n{}", "Output Files:".cyan().bold());
    println!("  - {}", output_manager.get_entities_file().display());
    println!("  - {}", output_manager.get_report_file().display());
    println!("  - {}", output_manager.get_html_report_file().display());
    println!(
        "  - {}",
        output_manager.get_markdown_report_file().display()
    );
    println!("  - {}/", output_manager.get_raw_dir().display());
    println!();

    Ok(())
}

async fn list_templates(cli: &Cli) -> Result<()> {
    let parser = TemplateParser::new(cli.templates_dir.clone());
    let templates = parser.load_all()?;

    println!("{}\n", "Available Templates:".cyan().bold());

    for template in templates {
        let status = if template.is_enabled() {
            "✓".green()
        } else {
            "✗".red()
        };

        let sudo_marker = if template.requires_sudo() {
            " [sudo]".yellow()
        } else {
            "".normal()
        };

        println!("  {} {}{}", status, template.name.bold(), sudo_marker);
        println!("     {}", template.description);
        println!();
    }

    Ok(())
}

async fn show_template(cli: &Cli, template_name: &str) -> Result<()> {
    let parser = TemplateParser::new(cli.templates_dir.clone());
    let template = parser.find_template(template_name)?;

    println!("{} {}\n", "Template:".cyan().bold(), template.name);
    println!("{} {}", "Description:".bold(), template.description);
    println!("{} {}", "Enabled:".bold(), template.is_enabled());
    println!("{} {}", "Requires sudo:".bold(), template.requires_sudo());
    println!("{} {}s", "Timeout:".bold(), template.get_timeout());
    println!("\n{}", "Command:".bold());
    println!(
        "  {} {}",
        template.command.binary,
        template.command.args.join(" ")
    );

    Ok(())
}
