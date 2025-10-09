use anyhow::{Context, Result};
use serde::Deserialize;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Deserialize)]
struct WordlistsConfig {
    wordlists: WordlistsSection,
}

#[derive(Debug, Deserialize)]
struct WordlistsSection {
    default: String,
    #[serde(flatten)]
    lists: HashMap<String, WordlistEntry>,
}

#[derive(Debug, Deserialize)]
struct WordlistEntry {
    path: String,
    description: String,
    size: String,
}

pub struct WordlistManager {
    config: WordlistsConfig,
    templates_dir: PathBuf,
}

impl WordlistManager {
    pub fn new(templates_dir: PathBuf) -> Result<Self> {
        let config_path = templates_dir.join("wordlists.toml");
        
        let content = fs::read_to_string(&config_path)
            .with_context(|| format!("Failed to read wordlists config: {}", config_path.display()))?;
        
        let config: WordlistsConfig = toml::from_str(&content)
            .context("Failed to parse wordlists.toml")?;
        
        Ok(Self {
            config,
            templates_dir,
        })
    }

    /// Get the default wordlist name
    pub fn default_wordlist(&self) -> &str {
        &self.config.wordlists.default
    }

    /// Resolve a wordlist name or path to an actual file path
    pub fn resolve(&self, name_or_path: &str) -> Result<String> {
        // If it's an absolute path or relative path (contains /), use it directly
        if name_or_path.contains('/') || Path::new(name_or_path).exists() {
            let path = Path::new(name_or_path);
            if path.exists() {
                return Ok(name_or_path.to_string());
            } else {
                anyhow::bail!("Wordlist file not found: {}", name_or_path);
            }
        }

        // Otherwise, look it up in the config
        if let Some(entry) = self.config.wordlists.lists.get(name_or_path) {
            let path = Path::new(&entry.path);
            if path.exists() {
                Ok(entry.path.clone())
            } else {
                anyhow::bail!(
                    "Wordlist '{}' points to non-existent file: {}\nInstall the wordlist or update templates/wordlists.toml",
                    name_or_path,
                    entry.path
                );
            }
        } else {
            anyhow::bail!(
                "Unknown wordlist: '{}'\nAvailable: {}\nOr provide a direct file path",
                name_or_path,
                self.list_available().join(", ")
            );
        }
    }

    /// List all available wordlist names
    pub fn list_available(&self) -> Vec<String> {
        let mut names: Vec<String> = self.config.wordlists.lists.keys().cloned().collect();
        names.sort();
        names
    }

    /// Get information about a wordlist
    pub fn info(&self, name: &str) -> Option<(String, String, String)> {
        self.config.wordlists.lists.get(name).map(|entry| {
            (
                entry.path.clone(),
                entry.description.clone(),
                entry.size.clone(),
            )
        })
    }

    /// List all wordlists with their info
    pub fn list_all(&self) -> Vec<(String, String, String, bool)> {
        let mut wordlists: Vec<_> = self
            .config
            .wordlists
            .lists
            .iter()
            .map(|(name, entry)| {
                let exists = Path::new(&entry.path).exists();
                (
                    name.clone(),
                    entry.path.clone(),
                    entry.description.clone(),
                    exists,
                )
            })
            .collect();
        
        wordlists.sort_by(|a, b| a.0.cmp(&b.0));
        wordlists
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolve_direct_path() {
        // Test that direct paths work
        let path = "/tmp/test.txt";
        std::fs::write(path, "test").unwrap();
        
        // Would need to create a test config, skipping for now
        std::fs::remove_file(path).ok();
    }
}
