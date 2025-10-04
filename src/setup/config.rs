use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use keyring::Entry;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub llm: LlmConfig,
    pub vector_db: VectorDbConfig,
    pub embeddings: EmbeddingsConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmConfig {
    pub provider: LlmProvider,
    pub model: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api_key: Option<String>,  // Deprecated: Use keychain instead
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api_base: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LlmProvider {
    OpenAI,
    Ollama,
    Groq,
    Together,
    Azure,
    OpenRouter,
    Huggingface,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorDbConfig {
    pub provider: VectorDbProvider,
    pub url: String,
    pub collection: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum VectorDbProvider {
    Qdrant,
    Redis,
    InMemory,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingsConfig {
    pub provider: EmbeddingsProvider,
    pub model: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api_key: Option<String>,  // Deprecated: Use keychain instead
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum EmbeddingsProvider {
    OpenAI,
    Ollama,
    Local,
    Huggingface,
}

impl Config {
    /// Service name for keychain storage
    const KEYCHAIN_SERVICE: &'static str = "ipcrawler";
    const KEYCHAIN_LLM_KEY: &'static str = "llm_api_key";
    const KEYCHAIN_EMBEDDINGS_KEY: &'static str = "embeddings_api_key";
    
    /// Save API key to system keychain (macOS Keychain, Windows Credential Manager, etc.)
    pub fn save_llm_api_key(api_key: &str) -> Result<()> {
        let entry = Entry::new(Self::KEYCHAIN_SERVICE, Self::KEYCHAIN_LLM_KEY)
            .context("Failed to create keychain entry")?;
        entry.set_password(api_key)
            .context("Failed to save API key to keychain")?;
        tracing::info!("✓ LLM API key saved securely to system keychain");
        Ok(())
    }
    
    /// Save embeddings API key to system keychain
    pub fn save_embeddings_api_key(api_key: &str) -> Result<()> {
        let entry = Entry::new(Self::KEYCHAIN_SERVICE, Self::KEYCHAIN_EMBEDDINGS_KEY)
            .context("Failed to create keychain entry")?;
        entry.set_password(api_key)
            .context("Failed to save API key to keychain")?;
        tracing::info!("✓ Embeddings API key saved securely to system keychain");
        Ok(())
    }
    
    /// Get LLM API key from system keychain
    pub fn get_llm_api_key() -> Option<String> {
        let entry = Entry::new(Self::KEYCHAIN_SERVICE, Self::KEYCHAIN_LLM_KEY).ok()?;
        entry.get_password().ok()
    }
    
    /// Get embeddings API key from system keychain
    pub fn get_embeddings_api_key() -> Option<String> {
        let entry = Entry::new(Self::KEYCHAIN_SERVICE, Self::KEYCHAIN_EMBEDDINGS_KEY).ok()?;
        entry.get_password().ok()
    }
    
    /// Delete API keys from keychain
    pub fn delete_api_keys() -> Result<()> {
        if let Ok(entry) = Entry::new(Self::KEYCHAIN_SERVICE, Self::KEYCHAIN_LLM_KEY) {
            let _ = entry.delete_password();
        }
        if let Ok(entry) = Entry::new(Self::KEYCHAIN_SERVICE, Self::KEYCHAIN_EMBEDDINGS_KEY) {
            let _ = entry.delete_password();
        }
        tracing::info!("✓ API keys removed from keychain");
        Ok(())
    }
    
    #[allow(dead_code)]
    pub fn default_openai() -> Self {
        Self {
            llm: LlmConfig {
                provider: LlmProvider::OpenAI,
                model: "gpt-4".to_string(),
                api_key: None,
                api_base: None,
            },
            vector_db: VectorDbConfig {
                provider: VectorDbProvider::Qdrant,
                url: "http://localhost:6333".to_string(),
                collection: "pentest_data".to_string(),
            },
            embeddings: EmbeddingsConfig {
                provider: EmbeddingsProvider::OpenAI,
                model: "text-embedding-ada-002".to_string(),
                api_key: None,
            },
        }
    }

    #[allow(dead_code)]
    pub fn default_ollama() -> Self {
        Self {
            llm: LlmConfig {
                provider: LlmProvider::Ollama,
                model: "llama3.1".to_string(),
                api_key: None,
                api_base: Some("http://localhost:11434".to_string()),
            },
            vector_db: VectorDbConfig {
                provider: VectorDbProvider::Qdrant,
                url: "http://localhost:6333".to_string(),
                collection: "pentest_data".to_string(),
            },
            embeddings: EmbeddingsConfig {
                provider: EmbeddingsProvider::Ollama,
                model: "nomic-embed-text".to_string(),
                api_key: None,
            },
        }
    }

    pub fn config_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .context("Could not find config directory")?
            .join("ipcrawler");
        
        std::fs::create_dir_all(&config_dir)?;
        Ok(config_dir.join("config.yaml"))
    }

    #[allow(dead_code)]
    pub fn load() -> Result<Self> {
        let path = Self::config_path()?;
        
        if !path.exists() {
            anyhow::bail!("Config file not found. Run 'ipcrawler setup' first.");
        }

        let content = std::fs::read_to_string(&path)
            .context("Failed to read config file")?;
        
        let mut config: Self = serde_yaml::from_str(&content)
            .context("Failed to parse config file")?;
        
        // Load API keys from keychain if not in config file
        if config.llm.api_key.is_none() {
            config.llm.api_key = Self::get_llm_api_key();
        }
        if config.embeddings.api_key.is_none() {
            config.embeddings.api_key = Self::get_embeddings_api_key();
        }
        
        Ok(config)
    }

    pub fn save(&self) -> Result<()> {
        let path = Self::config_path()?;
        
        // Ensure parent directory exists with proper permissions
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("Failed to create config directory: {}", parent.display()))?;
        }
        
        // Create config without API keys (they go in keychain)
        let mut config_to_save = self.clone();
        let llm_key = config_to_save.llm.api_key.take();
        let embeddings_key = config_to_save.embeddings.api_key.take();
        
        let yaml = serde_yaml::to_string(&config_to_save)
            .context("Failed to serialize config")?;
        
        std::fs::write(&path, &yaml)
            .with_context(|| format!("Failed to write config file to: {}\nPlease check permissions", path.display()))?;
        
        // Save API keys to keychain if present
        if let Some(api_key) = llm_key {
            if !api_key.is_empty() {
                Self::save_llm_api_key(&api_key)?;
            }
        }
        if let Some(api_key) = embeddings_key {
            if !api_key.is_empty() {
                Self::save_embeddings_api_key(&api_key)?;
            }
        }
        
        Ok(())
    }

    pub fn exists() -> bool {
        Self::config_path()
            .map(|p| p.exists())
            .unwrap_or(false)
    }
}
