use clap::{Parser, Subcommand, Args};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "ipcrawler")]
#[command(version, about = "Auto-reconnaissance tool with RAG for intelligent querying", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Run reconnaissance on target
    Run(RunArgs),
    
    /// Query indexed data with natural language
    Ask(AskArgs),
    
    /// Manage templates
    Templates(TemplatesCmd),
    
    /// Setup wizard for configuring AI models
    Setup,
    
    /// Clean/manage vector database
    Clean(CleanArgs),
}

#[derive(Args)]
pub struct RunArgs {
    /// Target IP address or hostname
    #[arg(short, long)]
    pub target: String,
    
    /// Output directory for results
    #[arg(short, long, default_value = "./output")]
    pub output: PathBuf,
    
    /// Custom templates directory
    #[arg(long)]
    pub templates_dir: Option<PathBuf>,
    
    /// Enable verbose logging
    #[arg(short, long)]
    pub verbose: bool,
}

#[derive(Args)]
pub struct AskArgs {
    /// Natural language question
    pub question: String,
    
    /// Output directory containing indexed data
    #[arg(short, long, default_value = "./output")]
    pub output: PathBuf,
    
    /// Number of top results to consider
    #[arg(short = 'k', long, default_value = "5")]
    pub top_k: usize,
}

#[derive(Args)]
pub struct TemplatesCmd {
    #[command(subcommand)]
    pub action: TemplatesAction,
}

#[derive(Subcommand)]
pub enum TemplatesAction {
    /// List all available templates
    List {
        /// Templates directory
        #[arg(long)]
        templates_dir: Option<PathBuf>,
    },
    
    /// Show details of a specific template
    Show {
        /// Template name
        name: String,
        
        /// Templates directory
        #[arg(long)]
        templates_dir: Option<PathBuf>,
    },
}

#[derive(Args)]
pub struct CleanArgs {
    /// Target to clean (IP/hostname). If not specified, lists all collections
    #[arg(short, long)]
    pub target: Option<String>,
    
    /// Clean all collections (use with caution!)
    #[arg(long)]
    pub all: bool,
    
    /// Qdrant URL
    #[arg(long, default_value = "http://localhost:6333")]
    pub qdrant_url: String,
    
    /// Just list collections without cleaning
    #[arg(short, long)]
    pub list: bool,
}
