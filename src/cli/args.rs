use clap::{Parser, ArgAction};

#[derive(Parser, Debug, Clone)]
#[command(
    name = "ipcrawler", 
    version, 
    author = "ipcrawler",
    about = "DNS Reconnaissance Tool - Multi-tool DNS enumeration with real-time TUI",
    long_about = "IPCrawler is a concurrent DNS reconnaissance tool that uses both nslookup and dig \
                 to perform comprehensive DNS enumeration. Features real-time terminal UI, \
                 configurable scanning options, and detailed output artifacts.\n\n\
                 FEATURES:\n  \
                 • Concurrent DNS queries using nslookup and dig\n  \
                 • Real-time terminal UI with live results\n  \
                 • Supports both IPv4/IPv6 addresses and domain names\n  \
                 • Configurable via global.toml (optional overrides)\n  \
                 • Comprehensive DNS record types (A, AAAA, MX, NS, TXT, CNAME, SOA, PTR)\n  \
                 • Detailed output artifacts with timestamped runs\n\n\
                 REQUIREMENTS:\n  \
                 • nslookup and dig commands available in PATH\n  \
                 • Terminal size ≥ 70x20 characters\n  \
                 • File descriptors ≥ 1024 (increase with ulimit -n)\n\n\
                 CONFIGURATION:\n  \
                 Edit global.toml to override default plugin behavior. Uncomment sections\n  \
                 to customize record types, timeouts, delays, and tool commands.\n\n\
                 OUTPUT:\n  \
                 Results saved to artifacts/runs/run_TARGET_TIMESTAMP/ with both\n  \
                 individual tool outputs and summary reports in multiple formats."
)]
pub struct Cli {
    /// Target host, IP address, or domain to scan
    /// 
    /// Examples:
    ///   google.com      - Domain name
    ///   8.8.8.8         - IPv4 address  
    ///   2001:4860:4860::8888 - IPv6 address
    #[arg(short = 't', long = "target", value_name = "HOST")]
    pub target: String,

    /// Enable verbose output and detailed logging
    #[arg(short = 'v', long = "verbose", action = ArgAction::SetTrue)]
    pub verbose: bool,

    /// Enable debug logging (implies --verbose)
    #[arg(short = 'd', long = "debug", action = ArgAction::SetTrue)]
    pub debug: bool,

    /// Skip system preflight checks
    /// 
    /// Bypasses validation of file descriptors, disk space,
    /// and required tools availability
    #[arg(long = "skip-checks", action = ArgAction::SetTrue)]
    pub skip_checks: bool,
}