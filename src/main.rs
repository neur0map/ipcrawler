mod cli;
mod templates;
mod watcher;
mod indexer;
mod query;
mod setup;

use anyhow::{Context, Result};
use clap::Parser;
use cli::{Cli, Commands, TemplatesAction};
use std::path::PathBuf;
use templates::{TemplateParser, TemplateExecutor};
use watcher::FileWatcher;
use indexer::IndexingPipeline;
use query::QueryEngine;
use qdrant_client::Qdrant as QdrantClient;

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    
    match cli.command {
        Commands::Run(args) => {
            init_logging(args.verbose);
            run_reconnaissance(args).await?;
        }
        Commands::Ask(args) => {
            init_logging(false);
            query_data(args).await?;
        }
        Commands::Templates(cmd) => {
            init_logging(false);
            handle_templates(cmd).await?;
        }
        Commands::Setup => {
            let wizard = setup::SetupWizard::new();
            wizard.run().await?;
        }
        Commands::Clean(args) => {
            init_logging(false);
            clean_database(args).await?;
        }
    }
    
    Ok(())
}

fn init_logging(verbose: bool) {
    let filter = if verbose {
        "ipcrawler=debug,info"
    } else {
        "ipcrawler=info"
    };
    
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .init();
}

fn sanitize_target(target: &str) -> String {
    target
        .replace(".", "_")
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .to_lowercase()
}

fn detect_collection_from_output(output: &PathBuf) -> Option<String> {
    // Try to extract target from output directory name
    // Examples: ./scan_192.168.1.1 -> ipcrawler_192_168_1_1
    let dir_name = output.file_name()?.to_str()?;
    
    // Check if it contains an IP-like pattern
    if dir_name.contains("_") || dir_name.contains(".") {
        Some(format!("ipcrawler_{}", sanitize_target(dir_name)))
    } else {
        None
    }
}

async fn clean_database(args: cli::CleanArgs) -> Result<()> {
    let client = QdrantClient::from_url(&args.qdrant_url)
        .build()
        .context("Failed to connect to Qdrant")?;
    
    // List all collections
    let collections_list = client.list_collections().await
        .context("Failed to list collections")?;
    
    let ipcrawler_collections: Vec<_> = collections_list
        .collections
        .into_iter()
        .filter(|c| c.name.starts_with("ipcrawler_"))
        .collect();
    
    if args.list || (args.target.is_none() && !args.all) {
        // Just list collections
        println!("\n📊 Qdrant Collections:\n");
        if ipcrawler_collections.is_empty() {
            println!("  No ipcrawler collections found.");
        } else {
            for collection in &ipcrawler_collections {
                println!("  • {}", collection.name);
            }
        }
        println!("\n💡 Use --target <IP> to clean specific target");
        println!("💡 Use --all to clean ALL collections (destructive!)");
        return Ok(());
    }
    
    if args.all {
        // Clean all ipcrawler collections
        println!("\n⚠️  WARNING: This will delete ALL ipcrawler collections!");
        println!("Collections to delete:");
        for collection in &ipcrawler_collections {
            println!("  • {}", collection.name);
        }
        
        print!("\nAre you sure? (yes/no): ");
        use std::io::{self, Write};
        io::stdout().flush()?;
        
        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        
        if input.trim().to_lowercase() != "yes" {
            println!("Cancelled.");
            return Ok(());
        }
        
        for collection in &ipcrawler_collections {
            client.delete_collection(&collection.name).await
                .context(format!("Failed to delete collection: {}", collection.name))?;
            println!("✓ Deleted: {}", collection.name);
        }
        
        println!("\n✅ All collections deleted!");
        
    } else if let Some(target) = &args.target {
        // Clean specific target
        let collection_name = format!("ipcrawler_{}", sanitize_target(target));
        
        // Check if collection exists
        if !ipcrawler_collections.iter().any(|c| c.name == collection_name) {
            println!("⚠️  Collection '{}' not found.", collection_name);
            println!("\nAvailable collections:");
            for collection in &ipcrawler_collections {
                println!("  • {}", collection.name);
            }
            return Ok(());
        }
        
        client.delete_collection(&collection_name).await
            .context(format!("Failed to delete collection: {}", collection_name))?;
        
        println!("✅ Deleted collection: {}", collection_name);
        println!("   Data for target '{}' has been removed.", target);
    }
    
    Ok(())
}

async fn run_reconnaissance(args: cli::RunArgs) -> Result<()> {
    tracing::info!(">> Starting ipcrawler");
    tracing::info!("Target: {}", args.target);
    tracing::info!("Output: {}", args.output.display());
    
    // Create output directory
    tokio::fs::create_dir_all(&args.output)
        .await
        .context("Failed to create output directory")?;
    
    // Determine templates directory
    let templates_dir = args.templates_dir.clone().unwrap_or_else(|| {
        std::env::current_exe()
            .ok()
            .and_then(|exe| exe.parent().map(|p| p.join("../templates")))
            .unwrap_or_else(|| PathBuf::from("./templates"))
    });
    
    if !templates_dir.exists() {
        tracing::warn!("Templates directory not found: {}", templates_dir.display());
        tracing::warn!("Creating default templates directory");
        tokio::fs::create_dir_all(&templates_dir).await?;
    }
    
    // Load templates
    tracing::info!("[INFO] Loading templates from: {}", templates_dir.display());
    let parser = TemplateParser::new(templates_dir);
    let templates = parser.load_all()?;
    
    if templates.is_empty() {
        tracing::warn!("[!IMPORTANT!]  No templates found. Please add YAML templates to the templates directory.");
        tracing::info!("Example templates can be found in the documentation.");
        return Ok(());
    }
    
    tracing::info!("Found {} enabled templates", templates.len());
    for template in &templates {
        tracing::info!("  • {} - {}", template.name, template.description);
    }
    
    // Resolve dependencies
    let executor = TemplateExecutor::new();
    let ordered_templates = executor.resolve_dependencies(&templates)
        .context("Failed to resolve template dependencies")?;
    
    tracing::info!("✓ Dependency resolution complete");
    
    // Start file watcher
    tracing::info!("[WATCHING]  Starting file watcher on: {}", args.output.display());
    let mut watcher = FileWatcher::new(&args.output)?;
    
    // Start indexing task with target-specific collection
    let collection_name = format!("ipcrawler_{}", sanitize_target(&args.target));
    tracing::info!("Using collection: {}", collection_name);
    let indexer = IndexingPipeline::new(collection_name);
    
    tokio::spawn(async move {
        while let Some(paths) = watcher.next().await {
            for path in paths {
                if let Err(e) = indexer.index_file(&path).await {
                    tracing::error!("Failed to index {}: {}", path.display(), e);
                }
            }
        }
    });
    
    // Execute templates in order
    tracing::info!("[EXECUTING] Starting template execution");
    for template in ordered_templates {
        let substituted = template.substitute_variables(
            &args.target,
            args.output.to_str().unwrap_or("./output"),
        );
        
        if let Err(e) = executor.execute(&substituted, &args.output).await {
            tracing::error!("Template '{}' failed: {}", template.name, e);
            tracing::warn!("Continuing with remaining templates...");
        }
        
        tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
    }
    
    tracing::info!("[OK] Reconnaissance complete!");
    tracing::info!("📁 Results saved to: {}", args.output.display());
    tracing::info!("💡 Query your data with: ipcrawler ask \"your question\" -o {}", args.output.display());
    
    Ok(())
}

async fn query_data(args: cli::AskArgs) -> Result<()> {
    if !args.output.exists() {
        anyhow::bail!("Output directory not found: {}", args.output.display());
    }
    
    // Try to detect target from output directory name or use default
    let collection_name = detect_collection_from_output(&args.output)
        .unwrap_or_else(|| "ipcrawler_default".to_string());
    
    tracing::info!("Querying collection: {}", collection_name);
    let engine = QueryEngine::new(collection_name, args.top_k);
    let result = engine.query(&args.question, &args.output).await?;
    
    println!("\n{}\n", result);
    
    Ok(())
}

async fn handle_templates(cmd: cli::TemplatesCmd) -> Result<()> {
    let templates_dir = match &cmd.action {
        TemplatesAction::List { templates_dir } => templates_dir.clone(),
        TemplatesAction::Show { templates_dir, .. } => templates_dir.clone(),
    }
    .unwrap_or_else(|| PathBuf::from("./templates"));
    
    let parser = TemplateParser::new(templates_dir.clone());
    
    match cmd.action {
        TemplatesAction::List { .. } => {
            let templates = parser.load_all()?;
            
            if templates.is_empty() {
                println!("No templates found in: {}", templates_dir.display());
                return Ok(());
            }
            
            println!("\nAvailable templates ({}):\n", templates.len());
            for template in templates {
                let deps = if template.depends_on.is_empty() {
                    "none".to_string()
                } else {
                    template.depends_on.join(", ")
                };
                
                println!("  [INFO] {}", template.name);
                println!("     Description: {}", template.description);
                println!("     Binary: {}", template.command.binary);
                println!("     Dependencies: {}", deps);
                println!();
            }
        }
        TemplatesAction::Show { name, .. } => {
            let template = parser.load_by_name(&name)?;
            
            println!("\n[INFO] Template: {}\n", template.name);
            println!("Description: {}", template.description);
            println!("Enabled: {}", template.enabled);
            println!("Binary: {}", template.command.binary);
            println!("Arguments:");
            for arg in &template.command.args {
                println!("  - {}", arg);
            }
            println!("\nDependencies: {}", 
                if template.depends_on.is_empty() { 
                    "none".to_string() 
                } else { 
                    template.depends_on.join(", ") 
                });
            println!("Timeout: {}s", template.timeout);
            
            if !template.outputs.is_empty() {
                println!("\nOutput patterns:");
                for output in &template.outputs {
                    println!("  - {}", output.pattern);
                }
            }
            
            if !template.env.is_empty() {
                println!("\nEnvironment variables:");
                for (key, value) in &template.env {
                    println!("  {} = {}", key, value);
                }
            }
            println!();
        }
    }
    
    Ok(())
}
