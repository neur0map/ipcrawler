use super::Config;
use anyhow::{anyhow, Result};
use colored::Colorize;
use inquire::{Confirm, Select, Text};
use std::io::{self, Write};
use std::process::Command;

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

        // Embedding model configuration
        println!("\n{}", "[Embedding Model Configuration]".cyan().bold());
        println!("{}", "-".repeat(60).cyan());
        println!("Embedding models are used for RAG (Retrieval-Augmented Generation)");
        println!("They help the LLM understand context and find relevant information.\n");

        if config.llm.provider == "ollama" {
            let embedding_models = vec![
                "nomic-embed-text (recommended - 137M params, 768 dim)",
                "mxbai-embed-large (high accuracy - 335M params, 1024 dim)",
                "all-minilm (fast - 23M params, 384 dim)",
                "snowflake-arctic-embed-m (strong retrieval - 109M params, 768 dim)",
                "bge-small-en-v1.5 (efficient - 33M params, 384 dim)",
                "Skip - configure later",
            ];

            match Select::new("Select embedding model to install:", embedding_models)
                .with_starting_cursor(0)
                .prompt()
            {
                Ok(selection) => {
                    if selection == "Skip - configure later" {
                        println!("  Skipped - you can configure this later");
                        config.llm.embedding_model = None;
                    } else {
                        // Extract model name from selection
                        let model_name = selection.split(' ').next().unwrap_or("nomic-embed-text");
                        config.llm.embedding_model = Some(model_name.to_string());

                        println!("\n  Downloading and installing {}...", model_name.cyan());
                        Self::install_ollama_model(model_name)?;
                        println!("  ✓ {} installed successfully", model_name.green());
                    }
                }
                Err(_) => {
                    println!("  Using default: nomic-embed-text");
                    config.llm.embedding_model = Some("nomic-embed-text".to_string());
                    println!("\n  Downloading and installing nomic-embed-text...");
                    Self::install_ollama_model("nomic-embed-text").ok(); // Best effort
                }
            }
        } else {
            // For cloud providers, offer embedding options
            let embedding_options = match config.llm.provider.as_str() {
                "openai" => vec![
                    "text-embedding-3-small (recommended, 1536 dim)",
                    "text-embedding-3-large (higher quality, 3072 dim)",
                    "text-embedding-ada-002 (legacy, 1536 dim)",
                    "Use Ollama locally (free, requires Ollama)",
                    "Skip - configure later",
                ],
                "groq" => vec![
                    "Use Ollama locally (recommended, free)",
                    "OpenAI text-embedding-3-small (requires OpenAI API key)",
                    "Skip - configure later",
                ],
                "anthropic" => vec![
                    "Use Ollama locally (recommended, free)",
                    "OpenAI text-embedding-3-small (requires OpenAI API key)",
                    "Skip - configure later",
                ],
                _ => vec!["Skip - configure later"],
            };

            match Select::new(
                "Select embedding model provider:",
                embedding_options.clone(),
            )
            .with_starting_cursor(0)
            .prompt()
            {
                Ok(selection) => {
                    if selection == "Skip - configure later" {
                        println!("  Skipped - you can configure this later");
                        config.llm.embedding_model = None;
                    } else if selection.starts_with("Use Ollama") {
                        // User wants Ollama for embeddings
                        let ollama_models = vec![
                            "nomic-embed-text (recommended - 137M params, 768 dim)",
                            "mxbai-embed-large (high accuracy - 335M params, 1024 dim)",
                            "all-minilm (fast - 23M params, 384 dim)",
                            "snowflake-arctic-embed-m (strong retrieval - 109M params, 768 dim)",
                            "bge-small-en-v1.5 (efficient - 33M params, 384 dim)",
                            "ONNX: all-MiniLM-L6-v2 (ultra-fast local - 80MB, 384 dim)",
                            "ONNX: bge-small-en-v1.5 (balanced - 130MB, 384 dim)",
                            "ONNX: e5-small-v2 (multilingual - 130MB, 384 dim)",
                        ];

                        match Select::new("Select embedding model to use:", ollama_models)
                            .with_starting_cursor(0)
                            .prompt()
                        {
                            Ok(model_selection) => {
                                if model_selection.starts_with("ONNX:") {
                                    // ONNX model - extract model name
                                    let parts: Vec<&str> =
                                        model_selection.split_whitespace().collect();
                                    let model_name = parts.get(1).unwrap_or(&"all-MiniLM-L6-v2");
                                    config.llm.embedding_model =
                                        Some(format!("onnx:{}", model_name));

                                    println!("\n  ✓ ONNX model configured: {}", model_name.cyan());
                                    println!("  Note: ONNX models run locally without Ollama");
                                    println!("  Will be downloaded automatically on first use via sentence-transformers");
                                } else {
                                    // Ollama model
                                    let model_name = model_selection
                                        .split(' ')
                                        .next()
                                        .unwrap_or("nomic-embed-text");
                                    config.llm.embedding_model =
                                        Some(format!("ollama:{}", model_name));

                                    println!(
                                        "\n  Downloading and installing {}...",
                                        model_name.cyan()
                                    );
                                    match Self::install_ollama_model(model_name) {
                                        Ok(_) => println!(
                                            "  ✓ {} installed successfully",
                                            model_name.green()
                                        ),
                                        Err(e) => {
                                            println!("  ⚠ {}", format!("Warning: {}", e).yellow());
                                            println!("  You can install it manually later with: ollama pull {}", model_name);
                                        }
                                    }
                                }
                            }
                            Err(_) => {
                                println!("  Using default: nomic-embed-text");
                                config.llm.embedding_model =
                                    Some("ollama:nomic-embed-text".to_string());
                            }
                        }
                    } else if selection.starts_with("OpenAI") {
                        println!(
                            "  Note: Requires OpenAI API key (set via OPENAI_API_KEY env var)"
                        );
                        config.llm.embedding_model =
                            Some("openai:text-embedding-3-small".to_string());
                        println!("  ✓ OpenAI embeddings configured");
                    } else {
                        // Extract model name from selection for OpenAI native models
                        let model_name = selection
                            .split(' ')
                            .next()
                            .unwrap_or("text-embedding-3-small");
                        config.llm.embedding_model = Some(model_name.to_string());
                        println!("  ✓ {} configured", model_name.cyan());
                    }
                }
                Err(_) => {
                    println!("  Skipped (non-interactive mode)");
                    config.llm.embedding_model = None;
                }
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

    fn install_ollama_model(model_name: &str) -> Result<()> {
        // Check if ollama is installed
        let check = Command::new("ollama").arg("--version").output();

        if check.is_err() {
            return Err(anyhow!(
                "Ollama is not installed. Please install from https://ollama.ai"
            ));
        }

        println!("  This may take a few minutes depending on model size...\n");

        // Pull the model with live output
        let status = Command::new("ollama")
            .arg("pull")
            .arg(model_name)
            .status()?;

        if !status.success() {
            return Err(anyhow!("Failed to install model {}", model_name));
        }

        Ok(())
    }
}
