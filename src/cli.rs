use clap::{Parser, Subcommand};
use std::path::PathBuf;
use chrono;

#[derive(Parser)]
#[command(name = "ipcrawler")]
#[command(author, version)]
#[command(about = "Intelligent penetration testing scanner with AI-powered parsing")]
#[command(long_about = "IPCrawler automates security tool execution and uses AI to parse outputs into structured data.\nNo hardcoded regex patterns - works with any tool output format.")]
#[command(after_help = "EXAMPLES:\n  ipcrawler setup                           Configure API keys and settings\n  ipcrawler 192.168.1.1                    Run scan (auto-generated output dir)\n  ipcrawler example.com -o ./scan          Run scan with custom output dir\n  ipcrawler example.com -v                  Run with verbose output\n  sudo ipcrawler <target>                  Run with elevated privileges")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Commands>,

    #[arg(value_name = "TARGET", help = "Target to scan (IP, domain, or URL)")]
    pub target: Option<String>,

    #[arg(short = 'o', long = "output", value_name = "PATH", help = "Output directory (default: ./ipcrawler_<target>_<timestamp>)")]
    pub output: Option<PathBuf>,

    #[arg(short = 't', long = "templates", value_name = "DIR", default_value = "templates", help = "Templates directory path")]
    pub templates_dir: PathBuf,

    #[arg(short = 'v', long = "verbose", help = "Enable verbose output")]
    pub verbose: bool,

    #[arg(long = "llm-provider", value_name = "PROVIDER", default_value = "openai", help = "LLM provider: groq, openai, anthropic, ollama")]
    pub llm_provider: String,

    #[arg(long = "llm-model", value_name = "MODEL", help = "LLM model name (provider-specific)")]
    pub llm_model: Option<String>,

    #[arg(long = "llm-api-key", value_name = "KEY", env = "LLM_API_KEY", help = "LLM API key (or use LLM_API_KEY env var)")]
    pub llm_api_key: Option<String>,

    #[arg(long = "no-parse", help = "Skip LLM parsing, save raw outputs only")]
    pub no_parse: bool,

    #[arg(long = "consistency-passes", value_name = "N", default_value = "3", help = "Number of LLM parsing passes for consistency (1-5, default: 3)")]
    pub consistency_passes: usize,

    #[arg(short = 'p', long = "ports", value_name = "PORTS", help = "Port specification (e.g., 22,80,443 or 1-1000). Default: top 1000 most common ports")]
    pub ports: Option<String>,

    #[arg(short = 'w', long = "wordlist", value_name = "NAME", help = "Wordlist name or path (e.g., common, medium, big, or /path/to/list.txt). Default: common")]
    pub wordlist: Option<String>,
}

#[derive(Subcommand)]
pub enum Commands {
    #[command(about = "List all available tool templates")]
    List,
    
    #[command(about = "Show detailed information about a template")]
    Show {
        #[arg(value_name = "TEMPLATE", help = "Template name (e.g., nmap, nikto)")]
        template: String,
    },

    #[command(about = "Interactive configuration wizard")]
    Setup,

    #[command(about = "Display current configuration settings")]
    Config,

    #[command(about = "List available wordlists")]
    Wordlists,
}

impl Cli {
    pub fn validate(&self) -> anyhow::Result<()> {
        // Setup and Config commands don't need target/output
        if matches!(self.command, Some(Commands::Setup) | Some(Commands::Config)) {
            return Ok(());
        }

        if self.command.is_none() && self.target.is_none() {
            anyhow::bail!("Please provide a target or use a subcommand");
        }

        if self.consistency_passes == 0 || self.consistency_passes > 5 {
            anyhow::bail!("Consistency passes must be between 1 and 5 (got: {})", self.consistency_passes);
        }

        Ok(())
    }

    pub fn get_output_path(&self) -> PathBuf {
        if let Some(ref path) = self.output {
            return path.clone();
        }

        // Generate default output path
        let target_safe = self.target
            .as_ref()
            .map(|t| {
                t.replace("http://", "")
                    .replace("https://", "")
                    .replace("/", "_")
                    .replace(":", "_")
            })
            .unwrap_or_else(|| "scan".to_string());

        let timestamp = chrono::Utc::now().format("%Y%m%d_%H%M%S");
        PathBuf::from(format!("./ipcrawler_{}_{}", target_safe, timestamp))
    }

    pub fn merge_with_config(mut self, config: crate::config::Config) -> Self {
        // Use config values if CLI args are not provided
        if self.llm_provider == "openai" && config.get_provider() != "openai" {
            // Only override if still default
            self.llm_provider = config.get_provider().to_string();
        }

        if self.llm_api_key.is_none() {
            self.llm_api_key = config.get_api_key().map(|s| s.to_string());
        }

        if self.llm_model.is_none() {
            self.llm_model = config.get_model().map(|s| s.to_string());
        }

        if self.templates_dir.to_str() == Some("templates") {
            self.templates_dir = PathBuf::from(config.get_templates_dir());
        }

        if !self.verbose && config.is_verbose() {
            self.verbose = true;
        }

        self
    }
}
