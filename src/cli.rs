use clap::Parser;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "ipcrawler")]
#[command(about = "IP-focused reconnaissance tool for penetration testing")]
#[command(version = "0.1.0")]
pub struct Args {
    /// Target IP address(es)
    #[arg(required = true)]
    pub targets: Vec<String>,
    
    /// Output directory (default: current directory)
    #[arg(short, long, value_name = "DIR")]
    pub output: Option<PathBuf>,
    
    /// Verbose output
    #[arg(short, long)]
    pub verbose: bool,
}
