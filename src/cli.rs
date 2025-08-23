use clap::Parser;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "ipcrawler")]
#[command(author = "Security Professionals")]
#[command(version = "1.0.0")]
#[command(about = "Modern IP Reconnaissance & Security Scanner")]
#[command(disable_help_flag = true)]
#[command(disable_version_flag = true)]
pub struct Cli {
    /// Target specification - IP address, hostname, or CIDR range
    #[arg(short = 't', long = "target", help = "Target to scan (IP, hostname, or CIDR range)", required_unless_present_any = ["validate", "paths", "list_tools", "resume", "doctor", "update", "list", "help", "version"])]
    pub target: Option<String>,

    /// Scan configuration profiles
    #[arg(short = 'c', long = "config", default_value = "default", help = "Configuration profile(s) - comma-separated for multiple", value_delimiter = ',')]
    pub config: Vec<String>,

    /// Output directory customization  
    #[arg(short = 'o', long = "output", help = "Custom output directory (default: ./recon-results/)")]
    pub output: Option<PathBuf>,

    /// Debug mode for troubleshooting
    #[arg(short = 'd', long = "debug", help = "Enable detailed debug logging and error traces")]
    pub debug: bool,

    /// Verbose output mode
    #[arg(short = 'v', long = "verbose", help = "Show detailed progress tables and tool output")]
    pub verbose: bool,

    /// Configuration validation
    #[arg(long = "validate", help = "Validate configuration files and exit")]
    pub validate: bool,

    /// Show system paths
    #[arg(long = "paths", help = "Display all config, data, and output directory paths")]
    pub paths: bool,

    /// Resume interrupted scans
    #[arg(long = "resume", help = "Resume interrupted scan from specified output directory")]
    pub resume: Option<PathBuf>,

    /// Preview mode (no execution)
    #[arg(long = "dry-run", help = "Preview commands without executing (simulation mode)")]
    pub dry_run: bool,

    /// List available tools
    #[arg(long = "list-tools", help = "Show all configured security tools and status")]
    pub list_tools: bool,

    /// Quick profile selection
    #[arg(short = 'p', long = "profile", help = "Quick profile selection (basic, full, stealth, web, network)")]
    pub profile: Option<String>,

    /// System health check
    #[arg(long = "doctor", help = "Check system dependencies and tool availability")]
    pub doctor: bool,

    /// Update tool
    #[arg(long = "update", help = "Update ipcrawler to the latest version")]
    pub update: bool,

    /// Browse available profiles
    #[arg(short = 'l', long = "list", help = "List all available configuration profiles")]
    pub list: bool,

    /// Disable failure handling
    #[arg(long = "no-emergency-stop", help = "Continue execution even if tools fail or timeout")]
    pub no_emergency_stop: bool,

    /// Disable notifications
    #[arg(long = "no-notifications", help = "Disable desktop notifications during scanning")]
    pub no_notifications: bool,

    /// Show help message
    #[arg(short = 'h', long = "help", help = "Print help")]
    pub help: bool,

    /// Show version
    #[arg(short = 'V', long = "version", help = "Print version")]
    pub version: bool,
}