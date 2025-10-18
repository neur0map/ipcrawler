use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::time::Duration;
use chrono::{DateTime, Utc};
use sha2::{Sha256, Digest};
use hex;
use crate::providers::ParsedResult;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CachedResult {
    result: ParsedResult,
    timestamp: DateTime<Utc>,
    output_hash: String,
}

pub struct ResultCache {
    cache_dir: PathBuf,
    ttl: Duration,
    memory_cache: HashMap<String, CachedResult>,
}

impl ResultCache {
    pub fn new() -> Result<Self> {
        let mut cache_dir = dirs::cache_dir()
            .unwrap_or_else(|| dirs::home_dir().unwrap_or_default());
        cache_dir.push("ipcrawler");
        cache_dir.push("cache");

        fs::create_dir_all(&cache_dir)?;

        Ok(Self {
            cache_dir,
            ttl: Duration::from_secs(24 * 60 * 60), // 24 hours
            memory_cache: HashMap::new(),
        })
    }

    

    fn generate_cache_key(&self, tool_name: &str, target: &str, output: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(tool_name.as_bytes());
        hasher.update(target.as_bytes());
        hasher.update(output.as_bytes());
        let hash = hasher.finalize();
        
        format!("{}_{}_{}", 
            tool_name, 
            target.replace('.', "_").replace('/', "_"),
            hex::encode(&hash[..8])
        )
    }

    fn get_cache_file_path(&self, cache_key: &str) -> PathBuf {
        let mut path = self.cache_dir.clone();
        path.push(format!("{}.json", cache_key));
        path
    }

    fn is_expired(&self, cached: &CachedResult) -> bool {
        let age = Utc::now().signed_duration_since(cached.timestamp);
        age.to_std().unwrap_or(Duration::MAX) > self.ttl
    }

    pub fn get(&mut self, tool_name: &str, target: &str, output: &str) -> Option<ParsedResult> {
        let cache_key = self.generate_cache_key(tool_name, target, output);
        
        // Check memory cache first
        if let Some(cached) = self.memory_cache.get(&cache_key) {
            if !self.is_expired(cached) {
                return Some(cached.result.clone());
            } else {
                // Remove expired entry
                self.memory_cache.remove(&cache_key);
            }
        }

        // Check file cache
        let cache_file = self.get_cache_file_path(&cache_key);
        if cache_file.exists() {
            match fs::read_to_string(&cache_file) {
                Ok(content) => {
                    match serde_json::from_str::<CachedResult>(&content) {
                        Ok(cached) => {
                            if !self.is_expired(&cached) {
                                // Add to memory cache
                                self.memory_cache.insert(cache_key, cached.clone());
                                return Some(cached.result);
                            } else {
                                // Remove expired file
                                let _ = fs::remove_file(&cache_file);
                            }
                        }
                        Err(_) => {
                            // Invalid cache file, remove it
                            let _ = fs::remove_file(&cache_file);
                        }
                    }
                }
                Err(_) => {
                    // Can't read file, remove it
                    let _ = fs::remove_file(&cache_file);
                }
            }
        }

        None
    }

    pub fn store(&mut self, tool_name: &str, target: &str, output: &str, result: &ParsedResult) -> Result<()> {
        let cache_key = self.generate_cache_key(tool_name, target, output);
        
        let cached = CachedResult {
            result: result.clone(),
            timestamp: Utc::now(),
            output_hash: {
                let mut hasher = Sha256::new();
                hasher.update(output.as_bytes());
                hex::encode(hasher.finalize())
            },
        };

        // Store in memory cache
        self.memory_cache.insert(cache_key.clone(), cached.clone());

        // Store in file cache
        let cache_file = self.get_cache_file_path(&cache_key);
        let json_data = serde_json::to_string(&cached)
            .context("Failed to serialize cached result")?;
        
        fs::write(&cache_file, json_data)
            .context("Failed to write cache file")?;

        Ok(())
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CacheStats {
    pub memory_entries: usize,
    pub file_entries: usize,
    pub total_size_bytes: u64,
    pub ttl_seconds: u64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::providers::ParsedResult;

    #[test]
    fn test_cache_operations() -> Result<()> {
        let mut cache = ResultCache::with_ttl(Duration::from_secs(1))?;
        
        let result = ParsedResult {
            tool_name: "test_tool".to_string(),
            target: "test.com".to_string(),
            timestamp: Utc::now().to_rfc3339(),
            findings: serde_json::json!({"test": "data"}),
            summary: "Test summary".to_string(),
            confidence: 0.9,
            tokens_used: Some(100),
            cost: Some(0.001),
        };

        // Store result
        cache.store("test_tool", "test.com", "test output", &result)?;

        // Retrieve result
        let retrieved = cache.get("test_tool", "test.com", "test output");
        assert!(retrieved.is_some());

        let retrieved = retrieved.unwrap();
        assert_eq!(retrieved.tool_name, result.tool_name);
        assert_eq!(retrieved.target, result.target);

        Ok(())
    }
}