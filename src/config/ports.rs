use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortsConfig {
    pub port_ranges: HashMap<String, String>,
}

impl Default for PortsConfig {
    fn default() -> Self {
        let mut config = PortsConfig {
            port_ranges: HashMap::new(),
        };

        // Add default port ranges
        config.port_ranges.insert("fast".to_string(), "21,22,23,25,53,80,110,111,135,139,143,443,993,995,1723,3306,3389,5432,5900,8080,8443,9100,10000".to_string());
        config.port_ranges.insert(
            "common".to_string(),
            "21,22,23,25,53,80,110,135,139,143,443,993,995,1723,3389".to_string(),
        );
        config
            .port_ranges
            .insert("top-1000".to_string(), "nmap-top-1000".to_string());
        config
            .port_ranges
            .insert("top-10000".to_string(), "nmap-top-10000".to_string());
        config
            .port_ranges
            .insert("all".to_string(), "1-65535".to_string());
        config.port_ranges.insert(
            "web".to_string(),
            "80,443,8000,8080,8443,8888,9000,9090,9443".to_string(),
        );
        config.port_ranges.insert(
            "database".to_string(),
            "1433,1521,3306,5432,5984,6379,27017,27018,27019".to_string(),
        );
        config.port_ranges.insert(
            "remote".to_string(),
            "22,23,3389,5900,5901,5902,5903,5904,5905".to_string(),
        );
        config
            .port_ranges
            .insert("mail".to_string(), "25,110,143,465,587,993,995".to_string());
        config
            .port_ranges
            .insert("ftp".to_string(), "20,21,989,990".to_string());

        config
    }
}

impl PortsConfig {
    pub fn load_from_file(path: &str) -> Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let config: PortsConfig = serde_yaml::from_str(&content)?;
        Ok(config)
    }

    pub fn load_or_default() -> Self {
        match Self::load_from_file("config/ports.yaml") {
            Ok(config) => config,
            Err(_) => {
                eprintln!("Warning: Could not load ports.yaml, using defaults");
                PortsConfig::default()
            }
        }
    }

    pub fn get_port_range(&self, name: &str) -> Option<&String> {
        self.port_ranges.get(name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = PortsConfig::default();
        assert!(config.get_port_range("fast").is_some());
        assert!(config.get_port_range("common").is_some());
        assert!(config.get_port_range("top-1000").is_some());
        assert!(config.get_port_range("web").is_some());
    }

    #[test]
    fn test_port_range_access() {
        let config = PortsConfig::default();
        let fast_range = config.get_port_range("fast").unwrap();
        assert!(fast_range.contains("80"));
        assert!(fast_range.contains("443"));
    }
}
