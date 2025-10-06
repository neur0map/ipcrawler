use super::Config;
use anyhow::Result;
use colored::Colorize;
use inquire::{Confirm, Select, Text};

pub struct SetupWizard;

impl SetupWizard {
    pub fn run() -> Result<()> {
        println!("\n{}", "IPCrawler Configuration Setup".cyan().bold());
        println!("{}", "=".repeat(60));
        
        let mut config = if Config::exists() {
            println!("\nFound existing configuration.");
            
            match Confirm::new("Update existing configuration?")
                .with_default(true)
                .prompt()
            {
                Ok(true) => Config::load()?,
                Ok(false) => {
                    println!("Setup cancelled.");
                    return Ok(());
                }
                Err(_) => {
                    println!("\n{}", "Note: Running in non-interactive mode".yellow());
                    println!("Will update existing configuration.\n");
                    Config::load()?
                }
            }
        } else {
            println!("\nNo configuration found. Creating new configuration.");
            Config::default()
        };

        // Run setup
        Self::setup_wizard(&mut config)?;
        
        config.save()?;
        
        println!("\n{}", "[Configuration saved successfully]".green().bold());
        
        if let Ok(path) = Config::config_path() {
            println!("Config file: {}", path.display());
        }
        
        println!("\nYou can now run scans without setting environment variables:");
        println!("  ipcrawler <target>");
        println!("\nTo view your configuration:");
        println!("  ipcrawler config");
        println!();
        
        Ok(())
    }

    fn setup_wizard(config: &mut Config) -> Result<()> {
        println!("\n{}", "[LLM Provider Configuration]".cyan().bold());
        println!("{}", "-".repeat(60));
        
        // Provider selection
        let providers = vec!["groq", "openai", "anthropic", "ollama"];
        
        config.llm.provider = Select::new("Select LLM provider:", providers.clone())
            .with_starting_cursor(providers.iter().position(|&p| p == config.llm.provider).unwrap_or(0))
            .prompt()
            .unwrap_or_else(|_| {
                println!("Using default provider: groq");
                "groq"
            })
            .to_string();
        
        // API Key (skip for Ollama)
        if config.llm.provider != "ollama" {
            let prompt = format!("Enter API key for {} (leave empty to skip)", config.llm.provider);
            let current_key = config.llm.api_key.as_deref().unwrap_or("");
            
            match Text::new(&prompt)
                .with_default(current_key)
                .prompt()
            {
                Ok(key) if !key.is_empty() => {
                    config.llm.api_key = Some(key);
                }
                Ok(_) => {
                    println!("API key skipped");
                }
                Err(_) => {
                    println!("API key skipped (non-interactive mode)");
                }
            }
        } else {
            config.llm.api_key = None;
        }
        
        // Model (optional)
        let default_model = Self::get_default_model(&config.llm.provider);
        let model_prompt = format!("Model name (default: {})", default_model);
        
        match Text::new(&model_prompt)
            .with_default(config.llm.model.as_deref().unwrap_or(""))
            .prompt()
        {
            Ok(model) if !model.is_empty() => {
                config.llm.model = Some(model);
            }
            _ => {
                config.llm.model = None;
            }
        }
        
        // Default settings
        println!("\n{}", "[Default Settings]".cyan().bold());
        println!("{}", "-".repeat(60));
        
        config.defaults.templates_dir = Text::new("Templates directory:")
            .with_default(&config.defaults.templates_dir)
            .prompt()
            .unwrap_or_else(|_| "templates".to_string());
        
        config.defaults.verbose = Confirm::new("Enable verbose output by default?")
            .with_default(config.defaults.verbose)
            .prompt()
            .unwrap_or(false);
        
        Ok(())
    }

    fn get_default_model(provider: &str) -> &'static str {
        match provider {
            "groq" => "llama-3.3-70b-versatile",
            "openai" => "gpt-4o-mini",
            "anthropic" => "claude-3-5-sonnet-20241022",
            "ollama" => "llama3.2",
            _ => "",
        }
    }
}
