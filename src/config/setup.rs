use super::Config;
use anyhow::Result;
use colored::Colorize;
use inquire::{Confirm, Select, Text};
use std::io::{self, Write};

pub struct SetupWizard;

impl SetupWizard {
    pub fn run() -> Result<()> {
        // Clear screen and move to top
        print!("\x1B[2J\x1B[H");
        io::stdout().flush().ok();

        println!("\n{}", "=".repeat(60).cyan());
        println!("{}", "IPCrawler Configuration Setup".cyan().bold());
        println!("{}", "=".repeat(60).cyan());

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
        println!("{}", "-".repeat(60).cyan());

        // Provider selection
        let providers = vec!["groq", "openai", "anthropic", "ollama"];

        config.llm.provider = Select::new("Select LLM provider:", providers.clone())
            .with_starting_cursor(
                providers
                    .iter()
                    .position(|&p| p == config.llm.provider)
                    .unwrap_or(0),
            )
            .prompt()
            .unwrap_or_else(|_| {
                println!("Using default provider: groq");
                "groq"
            })
            .to_string();

        // Show recommended models for this provider
        Self::show_recommended_models(&config.llm.provider);

        // API Key (skip for Ollama) - secure hidden input
        if config.llm.provider != "ollama" {
            let prompt = format!("Enter {} API key", config.llm.provider);

            println!("  Input will be hidden for security");
            match Self::secure_input(&prompt) {
                Ok(key) if !key.is_empty() => {
                    config.llm.api_key = Some(key);
                }
                Ok(_) => {
                    println!("  Skipped - you can set this later with environment variable");
                }
                Err(_) => {
                    println!("  Skipped (non-interactive mode)");
                }
            }
        } else {
            config.llm.api_key = None;
            println!("  Note: Ollama uses local models, no API key needed");
        }

        // Model selection
        let default_model = Self::get_default_model(&config.llm.provider);
        let model_prompt = format!("Model name (press Enter for default: {})", default_model);

        match Text::new(&model_prompt).with_default("").prompt() {
            Ok(model) if !model.is_empty() => {
                println!("  Using custom model: {}", model);
                config.llm.model = Some(model);
            }
            _ => {
                println!("  Using default: {}", default_model);
                config.llm.model = None;
            }
        }

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

    fn get_terminal_size() -> (usize, usize) {
        match terminal_size::terminal_size() {
            Some((terminal_size::Width(w), terminal_size::Height(_))) => (w as usize, 24),
            None => (80, 24), // Default fallback
        }
    }

    fn show_recommended_models(provider: &str) {
        let (width, _) = Self::get_terminal_size();
        let _max_width = width - 10; // Leave padding for future use

        println!("\n  Recommended models for {}:", provider.cyan());
        match provider {
            "groq" => {
                println!("    • llama-3.3-70b-versatile (default, fastest)");
                println!("    • llama-3.1-70b-versatile");
                println!("    • mixtral-8x7b-32768");
            }
            "openai" => {
                println!("    • gpt-4o-mini (default, cost-effective)");
                println!("    • gpt-4o (more capable)");
                println!("    • gpt-4-turbo");
            }
            "anthropic" => {
                println!("    • claude-3-5-sonnet-20241022 (default)");
                println!("    • claude-3-5-haiku-20241022 (faster)");
                println!("    • claude-3-opus-20240229 (most capable)");
            }
            "ollama" => {
                println!("    • llama3.2 (default)");
                println!("    • llama3.1");
                println!("    • mistral");
                println!("    • codellama");
            }
            _ => {}
        }
        println!();
    }

    fn secure_input(prompt: &str) -> Result<String> {
        print!("{}: ", prompt);
        io::stdout().flush()?;

        let password = rpassword::read_password()?;

        if !password.is_empty() {
            println!("✓ Configured");
        } else {
            println!("(skipped)");
        }

        Ok(password)
    }
}
