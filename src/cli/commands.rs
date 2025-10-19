use clap::Parser;
use std::path::PathBuf;
use crate::cli::keys::KeyAction;

#[derive(Parser)]
#[command(name = "ipcrawler")]
#[command(about = "IP-focused reconnaissance tool with LLM-powered output parsing")]
#[command(version = "0.1.0")]
#[command(author = "Carlos M. <carlos@neur0map.io>")]
pub struct Args {
    /// Target IP addresses or domain names (if provided, will perform scan)
    #[arg(required = false)]
    pub targets: Vec<String>,
    
    /// Output directory (default: current directory)
    #[arg(short, long, value_name = "DIR")]
    pub output: Option<PathBuf>,
    
    /// Port range (e.g., 22-3000, 80,443,8080)
    #[arg(short = 'p', long, value_name = "RANGE")]
    pub port_range: Option<String>,
    
    /// Verbose output
    #[arg(short, long)]
    pub verbose: bool,
    
    /// LLM provider to use (openai, groq, openrouter, ollama)
    #[arg(long, value_name = "PROVIDER")]
    pub llm_provider: Option<String>,
    
    /// Maximum cost per request in USD
    #[arg(long, value_name = "COST", default_value = "0.01")]
    pub max_cost_per_request: f64,
    
    /// Show cost statistics
    #[arg(long)]
    pub show_stats: bool,
    
    /// Reset daily cost tracking
    #[arg(long)]
    pub reset_stats: bool,
    
    /// Subcommands
    #[command(subcommand)]
    pub command: Option<Commands>,
}

#[derive(Parser)]
pub enum Commands {
    /// Scan targets for reconnaissance
    Scan {
        /// Target IP addresses or domain names
        #[arg(required = true)]
        targets: Vec<String>,
        
        /// Output directory (default: current directory)
        #[arg(short, long, value_name = "DIR")]
        output: Option<PathBuf>,
        
        /// Port range (e.g., 22-3000, 80,443,8080)
        #[arg(short = 'p', long, value_name = "RANGE")]
        port_range: Option<String>,
        
        /// Verbose output
        #[arg(short, long)]
        verbose: bool,
        
        /// LLM provider to use (openai, groq, openrouter, ollama)
        #[arg(long, value_name = "PROVIDER")]
        llm_provider: Option<String>,
        
        /// Maximum cost per request in USD
        #[arg(long, value_name = "COST", default_value = "0.01")]
        max_cost_per_request: f64,
        
        /// Show cost statistics
        #[arg(long)]
        show_stats: bool,
        
        /// Reset daily cost tracking
        #[arg(long)]
        reset_stats: bool,
    },
    
    /// API key management
    #[command(subcommand)]
    Keys(KeyAction),
}