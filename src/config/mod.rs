pub mod setup;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub llm: LlmConfig,
    
    #[serde(default)]
    pub defaults: DefaultsConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmConfig {
    pub provider: String,
    pub api_key: Option<String>,
    pub model: Option<String>,
    pub embedding_model: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DefaultsConfig {
    pub templates_dir: String,
    pub verbose: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            llm: LlmConfig::default(),
            defaults: DefaultsConfig::default(),
        }
    }
}

impl Default for LlmConfig {
    fn default() -> Self {
        Self {
            provider: "groq".to_string(),
            api_key: None,
            model: None,
            embedding_model: None,
        }
    }
}

impl Default for DefaultsConfig {
    fn default() -> Self {
        Self {
            templates_dir: "templates".to_string(),
            verbose: false,
        }
    }
}

impl Config {
    pub fn config_dir() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .context("Failed to get config directory")?
            .join("ipcrawler");
        
        Ok(config_dir)
    }

    pub fn config_path() -> Result<PathBuf> {
        Ok(Self::config_dir()?.join("config.toml"))
    }

    pub fn load() -> Result<Self> {
        let config_path = Self::config_path()?;
        
        if !config_path.exists() {
            return Ok(Config::default());
        }

        let content = fs::read_to_string(&config_path)
            .context("Failed to read config file")?;

        let config: Config = toml::from_str(&content)
            .context("Failed to parse config file")?;

        Ok(config)
    }

    pub fn save(&self) -> Result<()> {
        let config_dir = Self::config_dir()?;
        fs::create_dir_all(&config_dir)
            .context("Failed to create config directory")?;

        let config_path = Self::config_path()?;
        let content = toml::to_string_pretty(self)
            .context("Failed to serialize config")?;

        fs::write(&config_path, content)
            .context("Failed to write config file")?;

        // Set secure permissions (Unix only)
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(&config_path)?.permissions();
            perms.set_mode(0o600); // rw-------
            fs::set_permissions(&config_path, perms)?;
        }

        Ok(())
    }

    pub fn exists() -> bool {
        if let Ok(path) = Self::config_path() {
            path.exists()
        } else {
            false
        }
    }

    pub fn display_masked(&self) {
        println!("\n[Current Configuration]");
        println!("{}", "-".repeat(60));
        
        println!("\nLLM Settings:");
        println!("  Provider: {}", self.llm.provider);
        
        if let Some(ref key) = self.llm.api_key {
            let masked = Self::mask_api_key(key);
            println!("  API Key:  {}", masked);
        } else {
            println!("  API Key:  (not set)");
        }
        
        if let Some(ref model) = self.llm.model {
            println!("  Model:    {}", model);
        } else {
            println!("  Model:    (default)");
        }
        
        if let Some(ref embed_model) = self.llm.embedding_model {
            println!("  Embedding: {}", embed_model);
        } else {
            println!("  Embedding: (default)");
        }
        
        println!("\nDefault Settings:");
        println!("  Templates Dir: {}", self.defaults.templates_dir);
        println!("  Verbose:       {}", self.defaults.verbose);
        
        if let Ok(config_path) = Self::config_path() {
            println!("\nConfig File: {}", config_path.display());
        }
        
        println!();
    }

    fn mask_api_key(key: &str) -> String {
        if key.len() <= 8 {
            return "*".repeat(key.len());
        }
        
        let prefix = &key[..4];
        let suffix = &key[key.len()-4..];
        format!("{}...{}", prefix, suffix)
    }

    pub fn get_provider(&self) -> &str {
        &self.llm.provider
    }

    pub fn get_api_key(&self) -> Option<&str> {
        self.llm.api_key.as_deref()
    }

    pub fn get_model(&self) -> Option<&str> {
        self.llm.model.as_deref()
    }

    pub fn get_templates_dir(&self) -> &str {
        &self.defaults.templates_dir
    }

    pub fn is_verbose(&self) -> bool {
        self.defaults.verbose
    }
}
