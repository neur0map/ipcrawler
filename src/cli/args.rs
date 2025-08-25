use clap::{Parser, ArgAction};

#[derive(Parser, Debug, Clone)]
#[command(name = "ipcrawler", version, author = "ipcrawler")]
pub struct Cli {
    /// Target host/IP/domain to scan (required)
    #[arg(short = 't', long = "target")]
    pub target: String,

    /// Verbose human output
    #[arg(short = 'v', long = "verbose", action = ArgAction::SetTrue)]
    pub verbose: bool,

    /// Debug logs (implies verbose)
    #[arg(short = 'd', long = "debug", action = ArgAction::SetTrue)]
    pub debug: bool,

    /// Force simple progress mode (no TUI)
    #[arg(long = "simple", action = ArgAction::SetTrue)]
    pub simple: bool,

    /// Skip preflight checks (file descriptors, disk space, etc.)
    #[arg(long = "skip-checks", action = ArgAction::SetTrue)]
    pub skip_checks: bool,
}