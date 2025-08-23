use std::process;

pub struct HelpDisplay;

impl HelpDisplay {

    pub fn show_help(long_help: bool) {
        if long_help {
            show_long_help();
        } else {
            show_short_help();
        }
        process::exit(0);
    }
}

fn show_short_help() {
    println!(r#"
┌────────────────────────────────────────────────────────────────────────────┐
│                    ipcrawler - Security Scanner                            │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ ESSENTIAL OPTIONS                                                          │
├────────────────────────────────────────────────────────────────────────────┤
│ -t, --target <TARGET>   │ Target to scan (IP, hostname, CIDR)             │
│ -c, --config <CONFIG>   │ Scan profile [default: default]                 │
│ -v, --verbose           │ Show detailed progress and tables               │
│ -d, --debug             │ Enable debug logging and traces                 │
│ --dry-run               │ Preview commands without execution              │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ SYSTEM COMMANDS                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ --validate              │ Check configuration syntax                      │
│ --doctor                │ Check tool dependencies                         │
│ --paths                 │ Show directory paths                            │
│ --list                  │ List available profiles                         │
│ -h, --help              │ Show this help (use --help for full details)   │
│ -V, --version           │ Show version                                     │
└────────────────────────────────────────────────────────────────────────────┘"#);
}

fn show_long_help() {
    show_unified_long_help();
}

// Removed separate dev/prod help functions - now unified

fn show_unified_long_help() {
        println!(r#"
┌────────────────────────────────────────────────────────────────────────────┐
│                    ipcrawler - Security Scanner                            │
└────────────────────────────────────────────────────────────────────────────┘

PROFESSIONAL SECURITY SCANNER
    Network reconnaissance tool for security assessments and penetration testing.
    Automates discovery using industry-standard security tools with smart chaining.

┌────────────────────────────────────────────────────────────────────────────┐
│ CORE FEATURES                                                              │
├────────────────────────────────────────────────────────────────────────────┤
│ Target Analysis     │ Smart IP/hostname/CIDR range processing             │
│ Multi-tool Support  │ Integrates nmap, masscan, gobuster, nikto, etc.    │
│ Real-time Progress  │ Live discovery tracking with gradient colors       │
│ Report Generation   │ JSON, HTML, Markdown, and TXT output formats       │
│ Raw Data Preserve   │ Complete tool outputs saved for analysis           │
│ Profile System      │ Pre-configured scan profiles for scenarios         │
│ Smart Chaining      │ Automatic port passing between discovery tools     │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ COMMON USAGE                                                               │
├────────────────────────────────────────────────────────────────────────────┤
│ Single host         │ ipcrawler -t example.com                           │
│ Network range       │ ipcrawler -t 192.168.1.0/24                       │
│ Custom config       │ ipcrawler -t target.com -c custom-profile          │
│ Verbose scan        │ ipcrawler -t target.com -v                        │
│ Debug mode          │ ipcrawler -t target.com -d                        │
│ Dry run             │ ipcrawler -t example.com --dry-run                  │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ SYSTEM COMMANDS                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ --validate          │ Check configuration syntax and tool definitions    │
│ --doctor            │ Check tool installation and dependencies           │
│ --paths             │ Show directory paths and configuration locations   │
│ --list              │ Show available scan profiles                       │
│ -h, --help          │ Show this help                                      │
│ -V, --version       │ Show version information                           │
└────────────────────────────────────────────────────────────────────────────┘

REPORTS GENERATED
  JSON format for automated processing and integration
  HTML dashboard for interactive analysis with charts
  Markdown for documentation and sharing
  Text summary for quick terminal review
  Raw tool outputs preserved for manual analysis

ADVANCED FEATURES
  Smart port discovery chaining (naabu → nmap)
  Real-time progress with gradient-colored output
  Configurable timeout and retry logic
  Emergency stop handling (Ctrl+C)
  Comprehensive error logging and recovery"#);
}