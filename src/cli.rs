use clap::Parser;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "ipcrawler")]
#[command(author = "Security Team")]
#[command(version = "1.0")]
#[command(about = "🎯 Modern IP reconnaissance automation tool")]
#[command(long_about = r#"🎯 ipcrawler - Modern IP Reconnaissance Automation Tool

OVERVIEW:
  A powerful, flexible reconnaissance scanner that automates discovery of ports,
  services, vulnerabilities, and other network intelligence using industry-standard tools.

FEATURES:
  ✓ Multi-format reports (JSON, HTML, Markdown, Text)
  ✓ Interactive markdown summary viewing (with 'see' integration)
  ✓ Generic parsing engine (works with any tool output)
  ✓ Real-time discovery tracking with confidence scoring
  ✓ Raw output preservation for manual analysis
  ✓ Smart directory resolution (dev/production modes)
  ✓ Template-driven output formatting

OUTPUT LOCATIONS:
  📁 Development Mode (when run from project):
     → ./recon-results/{target}_{timestamp}/

  📁 Production Mode (system-wide installation):
     → ~/Library/Application Support/io.recon-tool.recon-tool/results/{target}_{timestamp}/

  📄 Generated Reports:
     • scan_summary.json  - Structured data with raw outputs
     • scan_summary.html  - Interactive web report  
     • scan_summary.md    - Documentation format
     • scan_summary.txt   - Terminal-friendly summary

EXAMPLES:
  ipcrawler -t example.com                    # Basic scan with default config
  ipcrawler -t 192.168.1.1 -c network        # Network-focused scan
  ipcrawler -t example.com -o /tmp/scan/      # Custom output directory
  ipcrawler --paths                           # Show all directory paths
  ipcrawler --list                            # List available profiles
  ipcrawler --doctor                          # Check tool dependencies

ENHANCED FEATURES:
  📖 Interactive Summary Viewing:
     After each scan, optionally view the markdown summary with the 'see' tool
     Opens in new terminal window (130x60) with syntax highlighting
     Install with: cargo install see-cat

For detailed path information: ipcrawler --paths"#)]
pub struct Cli {
    #[arg(short = 't', long = "target", help = "IP address or hostname to scan", required_unless_present_any = ["validate", "paths", "list_tools", "resume", "doctor", "update", "list"])]
    pub target: Option<String>,

    #[arg(short = 'c', long = "config", default_value = "default", help = "Configuration profile names or file paths (comma-separated for multiple configs)", value_delimiter = ',')]
    pub config: Vec<String>,

    #[arg(short = 'o', long = "output", help = "Output directory (default: ./recon-results/)")]
    pub output: Option<PathBuf>,

    #[arg(short = 'd', long = "debug", help = "Enable debug mode")]
    pub debug: bool,

    #[arg(short = 'v', long = "verbose", help = "Verbose output")]
    pub verbose: bool,

    #[arg(long = "validate", help = "Validate configuration file and exit")]
    pub validate: bool,

    #[arg(long = "paths", help = "Show directory paths for configs, data, and outputs")]
    pub paths: bool,

    #[arg(long = "resume", help = "Resume interrupted scan from output directory")]
    pub resume: Option<PathBuf>,

    #[arg(long = "dry-run", help = "Show what would be executed without running tools")]
    pub dry_run: bool,

    #[arg(long = "list-tools", help = "List available tools from configuration")]
    pub list_tools: bool,

    #[arg(short = 'p', long = "profile", help = "Quick profile selection (alternative to --config)")]
    pub profile: Option<String>,

    #[arg(long = "doctor", help = "Check system dependencies and tool availability")]
    pub doctor: bool,

    #[arg(long = "update", help = "Update ipcrawler to the latest version")]
    pub update: bool,

    #[arg(short = 'l', long = "list", help = "List all available configuration profiles with descriptions")]
    pub list: bool,

    #[arg(long = "no-emergency-stop", help = "Disable emergency stop on tool failures (continue execution)")]
    pub no_emergency_stop: bool,

    #[arg(long = "no-notifications", help = "Disable desktop notifications")]
    pub no_notifications: bool,
}