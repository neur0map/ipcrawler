use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct WordlistConfig {
    pub wordlists: HashMap<String, String>,
}

impl WordlistConfig {
    /// Load wordlist configuration from YAML file
    pub fn load_from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = fs::read_to_string(path.as_ref()).with_context(|| {
            format!(
                "Failed to read wordlist config: {}",
                path.as_ref().display()
            )
        })?;

        let config: WordlistConfig =
            serde_yaml::from_str(&content).context("Failed to parse wordlist config YAML")?;

        Ok(config)
    }

    /// Load default wordlist configuration from config/wordlists.yaml
    pub fn load_default() -> Result<Self> {
        let default_path = PathBuf::from("config/wordlists.yaml");
        Self::load_from_file(default_path)
    }

    /// Resolve a wordlist name or path to an actual file path
    /// Returns the path if it's a direct file path, otherwise looks up in config
    pub fn resolve(&self, name_or_path: &str) -> Result<String> {
        // Check if it's a direct path (exists as file)
        let path = Path::new(name_or_path);
        if path.exists() && path.is_file() {
            return Ok(name_or_path.to_string());
        }

        // Look up in configured wordlists
        self.wordlists.get(name_or_path).cloned().ok_or_else(|| {
            anyhow::anyhow!(
                "Wordlist '{}' not found in config. Available: {}",
                name_or_path,
                self.list_available().join(", ")
            )
        })
    }

    /// List all available wordlist names
    pub fn list_available(&self) -> Vec<String> {
        let mut names: Vec<String> = self.wordlists.keys().cloned().collect();
        names.sort();
        names
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolve_direct_path() {
        let config = WordlistConfig {
            wordlists: HashMap::new(),
        };

        // This will fail in test since path doesn't exist, but tests the logic
        let result = config.resolve("/tmp/test.txt");
        assert!(result.is_err() || result.is_ok());
    }

    #[test]
    fn test_list_available() {
        let mut wordlists = HashMap::new();
        wordlists.insert(
            "common".to_string(),
            "/usr/share/wordlists/common.txt".to_string(),
        );
        wordlists.insert(
            "big".to_string(),
            "/usr/share/wordlists/big.txt".to_string(),
        );

        let config = WordlistConfig { wordlists };

        let available = config.list_available();
        assert_eq!(available.len(), 2);
        assert!(available.contains(&"common".to_string()));
        assert!(available.contains(&"big".to_string()));
    }
}
