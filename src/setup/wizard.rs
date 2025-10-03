use anyhow::Result;
use colored::Colorize;
use dialoguer::{theme::ColorfulTheme, Select, Input, Confirm, Password};
use indicatif::{ProgressBar, ProgressStyle};
use std::time::Duration;
use tokio::process::Command;
use std::io::Write;

use super::config::{Config, LlmProvider, VectorDbProvider, EmbeddingsProvider};
use super::models::ModelDetector;

pub struct SetupWizard {
    detector: ModelDetector,
}

impl SetupWizard {
    pub fn new() -> Self {
        Self {
            detector: ModelDetector::new(),
        }
    }

    pub async fn run(&self) -> Result<()> {
        self.print_banner();
        
        println!("\n{}", "Welcome to ipcrawler setup wizard! >>".bright_cyan().bold());
        println!("{}\n", "Let's configure your AI models for intelligent reconnaissance.\n".bright_white());

        // Check existing config
        if Config::exists() {
            println!("{}", "[!IMPORTANT!]  Existing configuration found.".yellow());
            let overwrite = Confirm::with_theme(&ColorfulTheme::default())
                .with_prompt("Do you want to reconfigure?")
                .default(false)
                .interact()?;
            
            if !overwrite {
                println!("{}", "Setup cancelled.".yellow());
                return Ok(());
            }
        }

        // Detect services
        println!("{}", "\n[SEARCH] Detecting available services...\n".bright_cyan().bold());
        let spinner = self.create_spinner("Checking services...");
        
        let ollama_available = self.detector.check_ollama().await?;
        let qdrant_available = self.detector.check_qdrant().await?;
        
        spinner.finish_and_clear();

        self.print_service_status("Ollama", ollama_available);
        self.print_service_status("Qdrant", qdrant_available);

        // Choose setup path
        let config = if ollama_available {
            self.setup_with_ollama(qdrant_available).await?
        } else {
            self.setup_with_cloud(qdrant_available).await?
        };

        // Save configuration
        println!("\n{}", "[SAVE] Saving configuration...".bright_cyan());
        config.save()?;
        
        let config_path = Config::config_path()?;
        println!("{} {}", "✓".green().bold(), format!("Configuration saved to: {}", config_path.display()).bright_white());

        // Final summary
        self.print_summary(&config);

        println!("\n{}", "[+] Setup complete! You're ready to use ipcrawler with AI-powered queries.".bright_green().bold());
        println!("\n{}", "Try it out:".bright_white());
        println!("  {}", "ipcrawler run -t 192.168.1.1 -o ./scan --templates-dir ./templates".bright_yellow());
        println!("  {}", "ipcrawler ask \"what services were found?\" -o ./scan".bright_yellow());

        Ok(())
    }

    async fn setup_with_ollama(&self, qdrant_available: bool) -> Result<Config> {
        println!("\n{}", "[INFO] Great! Ollama is running locally.".bright_green());
        
        let setup_choice = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Choose your setup")
            .items(&[
                "Custom configuration (custom)",
            ])
            .default(0)
            .interact()?;

        match setup_choice {
            0 => self.configure_ollama(qdrant_available).await,
            1 => self.configure_openai(qdrant_available).await,
            2 => self.configure_custom(qdrant_available).await,
            _ => unreachable!(),
        }
    }

    async fn setup_with_cloud(&self, qdrant_available: bool) -> Result<Config> {
        println!("\n{}", "[INFO]  Ollama not detected. You can:".bright_blue());
        println!("   1. Install Ollama: {}", "https://ollama.ai".bright_cyan().underline());
        println!("   2. Use cloud providers (OpenAI, etc.)\n");

        let setup_choice = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Choose your setup")
            .items(&[
                "Use OpenAI (requires API key) (cloud)",
                "Install Ollama first (recommended for privacy) (local)",
                "Custom configuration (custom)",
            ])
            .default(0)
            .interact()?;

        match setup_choice {
            0 => self.configure_openai(qdrant_available).await,
            1 => {
                self.show_ollama_installation();
                anyhow::bail!("Please install Ollama and run setup again");
            }
            2 => self.configure_custom(qdrant_available).await,
            _ => unreachable!(),
        }
    }

    async fn configure_ollama(&self, qdrant_available: bool) -> Result<Config> {
        println!("\n{}", "[OLLAMA] Configuring Ollama...".bright_cyan().bold());

        // Check installed models
        let spinner = self.create_spinner("Checking installed models...");
        let installed = self.detector.list_ollama_models().await.unwrap_or_default();
        spinner.finish_and_clear();

        let llm_model = if installed.is_empty() {
            println!("\n{}", "No models installed yet.".yellow());
            self.prompt_ollama_model_install().await?
        } else {
            println!("\n{}", "[PACKAGE] Installed models:".bright_white().bold());
            for model in &installed {
                println!("  {} {} {}", 
                    "•".bright_blue(),
                    model.name.bright_white(),
                    format!("({})", model.size.as_ref().unwrap_or(&"".to_string())).bright_black()
                );
            }
            
            let install_more = Confirm::with_theme(&ColorfulTheme::default())
                .with_prompt("Install additional models?")
                .default(false)
                .interact()?;

            if install_more {
                self.prompt_ollama_model_install().await?
            } else {
                self.select_ollama_model(&installed)?
            }
        };

        // Choose embedding model
        let embedding_model = self.select_embedding_model(true)?;

        // Setup vector DB
        let vector_db_config = self.configure_vector_db(qdrant_available).await?;

        Ok(Config {
            llm: super::config::LlmConfig {
                provider: LlmProvider::Ollama,
                model: llm_model,
                api_key: None,
                api_base: Some("http://localhost:11434".to_string()),
            },
            embeddings: super::config::EmbeddingsConfig {
                provider: EmbeddingsProvider::Ollama,
                model: embedding_model,
                api_key: None,
            },
            vector_db: vector_db_config,
        })
    }

    async fn configure_openai(&self, qdrant_available: bool) -> Result<Config> {
        println!("\n{}", "(cloud)  Configuring OpenAI...".bright_cyan().bold());

        // Get API key
        let api_key = Password::with_theme(&ColorfulTheme::default())
            .with_prompt("OpenAI API Key")
            .interact()?;

        if api_key.is_empty() {
            anyhow::bail!("API key is required");
        }

        // Select model
        let models = ModelDetector::available_openai_models();
        let model_names: Vec<String> = models.iter()
            .map(|m| format!("{} - {}", m.name, m.description))
            .collect();

        let model_idx = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Select LLM model")
            .items(&model_names)
            .default(0)
            .interact()?;

        let llm_model = models[model_idx].name.clone();

        // Select embedding model
        let embedding_model = self.select_embedding_model(false)?;

        // Vector DB
        let vector_db_config = self.configure_vector_db(qdrant_available).await?;

        Ok(Config {
            llm: super::config::LlmConfig {
                provider: LlmProvider::OpenAI,
                model: llm_model,
                api_key: Some(api_key.clone()),
                api_base: None,
            },
            embeddings: super::config::EmbeddingsConfig {
                provider: EmbeddingsProvider::OpenAI,
                model: embedding_model,
                api_key: Some(api_key),
            },
            vector_db: vector_db_config,
        })
    }

    async fn configure_custom(&self, qdrant_available: bool) -> Result<Config> {
        println!("\n{}", "(custom)  Custom configuration...".bright_cyan().bold());

        let provider_choice = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Select LLM provider")
            .items(&["OpenAI", "Ollama", "Groq", "Together AI"])
            .default(0)
            .interact()?;

        match provider_choice {
            0 => self.configure_openai(qdrant_available).await,
            1 => self.configure_ollama(qdrant_available).await,
            _ => {
                println!("{}", "Other providers coming soon!".yellow());
                self.configure_openai(qdrant_available).await
            }
        }
    }

    async fn prompt_ollama_model_install(&self) -> Result<String> {
        println!("\n{}", "[DOWNLOAD] Recommended models for reconnaissance:".bright_white().bold());
        
        let models = ModelDetector::recommended_ollama_models();
        let model_names: Vec<String> = models.iter()
            .map(|m| format!("{} - {} ({})", 
                m.name, 
                m.description,
                m.size.as_ref().unwrap_or(&"".to_string())
            ))
            .collect();

        let model_idx = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Select model to install")
            .items(&model_names)
            .default(0)
            .interact()?;

        let model_name = &models[model_idx].name;
        
        println!("\n{} {}", "[DOWNLOAD]".to_string(), format!("Pulling model: {}", model_name).bright_cyan());
        println!("{}", "This may take a few minutes depending on model size...".bright_black());

        let pb = ProgressBar::new_spinner();
        pb.set_style(
            ProgressStyle::default_spinner()
                .template("{spinner:.cyan} {msg}")
                .unwrap()
        );
        pb.set_message(format!("Downloading {}...", model_name));
        pb.enable_steady_tick(Duration::from_millis(100));

        let output = Command::new("ollama")
            .arg("pull")
            .arg(model_name)
            .output()
            .await?;

        pb.finish_and_clear();

        if output.status.success() {
            println!("{} {}", "✓".green().bold(), format!("Model {} installed successfully", model_name).bright_white());
            Ok(model_name.clone())
        } else {
            let error = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("Failed to install model: {}", error);
        }
    }

    fn select_ollama_model(&self, installed: &[super::models::ModelInfo]) -> Result<String> {
        let model_names: Vec<String> = installed.iter()
            .map(|m| format!("{} ({})", m.name, m.size.as_ref().unwrap_or(&"".to_string())))
            .collect();

        let model_idx = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Select LLM model")
            .items(&model_names)
            .default(0)
            .interact()?;

        Ok(installed[model_idx].name.clone())
    }

    fn select_embedding_model(&self, ollama_available: bool) -> Result<String> {
        let models = ModelDetector::available_embedding_models();
        
        let filtered: Vec<_> = if ollama_available {
            models
        } else {
            models.into_iter()
                .filter(|m| m.requires_api_key)
                .collect()
        };

        let model_names: Vec<String> = filtered.iter()
            .map(|m| format!("{} ({}) - {}", 
                m.name, 
                m.provider,
                m.description
            ))
            .collect();

        let model_idx = Select::with_theme(&ColorfulTheme::default())
            .with_prompt("Select embedding model")
            .items(&model_names)
            .default(0)
            .interact()?;

        Ok(filtered[model_idx].name.clone())
    }

    async fn configure_vector_db(&self, qdrant_available: bool) -> Result<super::config::VectorDbConfig> {
        if !qdrant_available {
            println!("\n{}", "[!IMPORTANT!]  Qdrant not detected.".yellow());
            
            let install = Confirm::with_theme(&ColorfulTheme::default())
                .with_prompt("Install Qdrant with Docker?")
                .default(true)
                .interact()?;

            if install {
                self.install_qdrant().await?;
            } else {
                println!("{}", "[INFO]  Install Qdrant manually: docker run -p 6333:6333 qdrant/qdrant".bright_blue());
            }
        }

        let url = Input::with_theme(&ColorfulTheme::default())
            .with_prompt("Qdrant URL")
            .default("http://localhost:6333".to_string())
            .interact()?;

        let collection = Input::with_theme(&ColorfulTheme::default())
            .with_prompt("Collection name")
            .default("pentest_data".to_string())
            .interact()?;

        Ok(super::config::VectorDbConfig {
            provider: VectorDbProvider::Qdrant,
            url,
            collection,
        })
    }

    async fn install_qdrant(&self) -> Result<()> {
        println!("\n{}", "[DOCKER] Starting Qdrant with Docker...".bright_cyan());

        // Check if Docker daemon is running
        let docker_running = match Command::new("docker")
            .arg("info")
            .output()
            .await
        {
            Ok(output) => output.status.success(),
            Err(_) => false,
        };

        if !docker_running {
            println!("\n{}", "[!IMPORTANT!]  Docker daemon is not running!".yellow().bold());
            println!("\n{}", "To start Docker:".bright_white());
            println!("  {} Start Docker Desktop application", "•".bright_blue());
            println!("  {} Wait for Docker to be ready (usually 10-30 seconds)", "•".bright_blue());
            println!("  {} Then run {} again\n", "•".bright_blue(), "ipcrawler setup".bright_yellow());
            
            let wait = Confirm::with_theme(&ColorfulTheme::default())
                .with_prompt("Wait for Docker to start? (will retry in 15 seconds)")
                .default(true)
                .interact()?;
            
            if wait {
                println!("\n{}", "[WAITING] Waiting 15 seconds for Docker to start...".bright_cyan());
                
                // Try to start Docker Desktop on macOS
                let _ = Command::new("open")
                    .args(&["-a", "Docker"])
                    .output()
                    .await;
                
                tokio::time::sleep(Duration::from_secs(15)).await;
                
                // Check again
                let recheck_running = match Command::new("docker")
                    .arg("info")
                    .output()
                    .await
                {
                    Ok(output) => output.status.success(),
                    Err(_) => false,
                };
                
                if !recheck_running {
                    println!("{}", "[!IMPORTANT!]  Docker still not ready. Please start Docker Desktop manually.".yellow());
                    anyhow::bail!("Docker daemon not running. Start Docker Desktop and try again.");
                }
                
                println!("{} {}", "✓".green().bold(), "Docker is ready!".bright_white());
            } else {
                anyhow::bail!("Docker daemon not running. Start Docker Desktop and run setup again.");
            }
        }

        let pb = ProgressBar::new_spinner();
        pb.set_style(
            ProgressStyle::default_spinner()
                .template("{spinner:.cyan} {msg}")
                .unwrap()
        );
        pb.set_message("Pulling and starting Qdrant...");
        pb.enable_steady_tick(Duration::from_millis(100));

        let output = Command::new("docker")
            .args(&[
                "run",
                "-d",
                "-p", "6333:6333",
                "--name", "ipcrawler-qdrant",
                "qdrant/qdrant"
            ])
            .output()
            .await?;

        pb.finish_and_clear();

        if output.status.success() {
            println!("{} {}", "✓".green().bold(), "Qdrant started successfully".bright_white());
            println!("{}", "   Container: ipcrawler-qdrant".bright_black());
            println!("{}", "   URL: http://localhost:6333".bright_black());
            Ok(())
        } else {
            let error = String::from_utf8_lossy(&output.stderr);
            if error.contains("already in use") || error.contains("is already in use by container") {
                println!("{} {}", "✓".green().bold(), "Qdrant is already running".bright_white());
                Ok(())
            } else {
                anyhow::bail!("Failed to start Qdrant: {}", error);
            }
        }
    }

    fn print_banner(&self) {
        println!("\n{}", "╔═══════════════════════════════════════════════════╗".bright_cyan());
        println!("{}", "║                                                   ║".bright_cyan());
        println!("{}  {}  {}", "║".bright_cyan(), "ipcrawler Setup Wizard".bright_white().bold(), "║".bright_cyan());
        println!("{}", "║                                                   ║".bright_cyan());
        println!("{}", "╚═══════════════════════════════════════════════════╝".bright_cyan());
    }

    fn print_service_status(&self, name: &str, available: bool) {
        let status = if available {
            format!("{} {}", "✓".green().bold(), "Running".bright_green())
        } else {
            format!("{} {}", "✗".red().bold(), "Not detected".bright_red())
        };
        println!("  {} {}: {}", "•".bright_blue(), name.bright_white(), status);
    }

    fn create_spinner(&self, msg: &str) -> ProgressBar {
        let pb = ProgressBar::new_spinner();
        pb.set_style(
            ProgressStyle::default_spinner()
                .template("{spinner:.cyan} {msg}")
                .unwrap()
        );
        pb.set_message(msg.to_string());
        pb.enable_steady_tick(Duration::from_millis(100));
        pb
    }

    fn print_summary(&self, config: &Config) {
        println!("\n{}", "[SUMMARY] Configuration Summary".bright_cyan().bold());
        println!("{}", "─────────────────────────".bright_black());
        
        println!("\n  {} {}", "LLM Provider:".bright_white(), format!("{:?}", config.llm.provider).bright_green());
        println!("  {} {}", "LLM Model:".bright_white(), config.llm.model.bright_green());
        
        if let Some(api_base) = &config.llm.api_base {
            println!("  {} {}", "API Base:".bright_white(), api_base.bright_green());
        }
        
        println!("\n  {} {}", "Embeddings:".bright_white(), config.embeddings.model.bright_green());
        println!("  {} {:?}", "Provider:".bright_white(), config.embeddings.provider);
        
        println!("\n  {} {}", "Vector DB:".bright_white(), config.vector_db.url.bright_green());
        println!("  {} {}", "Collection:".bright_white(), config.vector_db.collection.bright_green());
    }

    fn show_ollama_installation(&self) {
        println!("\n{}", "[PACKAGE] Installing Ollama:".bright_cyan().bold());
        println!("\n  {}  Visit: {}", "1.".bright_white(), "https://ollama.ai".bright_cyan().underline());
        println!("  {}  Download and install for your OS", "2.".bright_white());
        println!("  {}  Run: {}", "3.".bright_white(), "ollama pull llama3.1".bright_yellow());
        println!("  {}  Run setup again: {}\n", "4.".bright_white(), "ipcrawler setup".bright_yellow());
    }
}
