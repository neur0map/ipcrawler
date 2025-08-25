use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use super::types::GlobalConfig;

const DEFAULT_CONFIG_PATHS: &[&str] = &[
    "./global.toml",
    "./config/global.toml", 
    "~/.config/ipcrawler/global.toml",
    "/etc/ipcrawler/global.toml",
];

pub struct ConfigLoader;

impl ConfigLoader {
    /// Load configuration from various sources with fallbacks
    pub fn load() -> Result<GlobalConfig> {
        Self::load_with_custom_path(None)
    }

    /// Load configuration with a custom path
    pub fn load_with_custom_path(custom_path: Option<&Path>) -> Result<GlobalConfig> {
        // Try custom path first if provided
        if let Some(path) = custom_path {
            if path.exists() {
                return Self::load_from_file(path)
                    .with_context(|| format!("Failed to load config from custom path: {:?}", path));
            }
            tracing::warn!("Custom config path does not exist: {:?}, falling back to defaults", path);
        }

        // Try default paths
        for default_path in DEFAULT_CONFIG_PATHS {
            let path = Self::expand_path(default_path);
            if path.exists() {
                match Self::load_from_file(&path) {
                    Ok(config) => {
                        tracing::info!("Loaded configuration from: {:?}", path);
                        return Ok(config);
                    }
                    Err(e) => {
                        tracing::warn!("Failed to load config from {:?}: {}", path, e);
                        continue;
                    }
                }
            }
        }

        // Fall back to default configuration
        tracing::info!("No configuration file found, using default settings");
        Ok(GlobalConfig::default())
    }

    /// Load configuration from a specific file
    fn load_from_file(path: &Path) -> Result<GlobalConfig> {
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read config file: {:?}", path))?;
        
        let config: GlobalConfig = toml::from_str(&content)
            .with_context(|| format!("Failed to parse TOML config: {:?}", path))?;

        // Validate configuration
        Self::validate_config(&config)?;

        Ok(config)
    }

    /// Validate configuration values
    fn validate_config(config: &GlobalConfig) -> Result<()> {
        // Validate concurrency settings
        if config.concurrency.max_total_scans == 0 {
            anyhow::bail!("max_total_scans must be greater than 0");
        }

        if config.concurrency.max_port_scans >= config.concurrency.max_total_scans {
            anyhow::bail!("max_port_scans must be less than max_total_scans");
        }

        // Validate tool commands are not empty
        if config.tools.nmap.command.is_empty() {
            anyhow::bail!("nmap command cannot be empty");
        }

        if config.tools.http_probe.command.is_empty() {
            anyhow::bail!("http_probe command cannot be empty");
        }

        // Validate timeout values
        if config.tools.nmap.limits.timeout_ms == 0 {
            anyhow::bail!("nmap timeout_ms must be greater than 0");
        }

        if config.tools.http_probe.limits.timeout_ms == 0 {
            anyhow::bail!("http_probe timeout_ms must be greater than 0");
        }

        // Validate port strategy settings
        match config.tools.nmap.port_strategy {
            super::types::PortStrategy::Top => {
                if config.tools.nmap.ports.top_ports.is_none() || 
                   config.tools.nmap.ports.top_ports.unwrap() == 0 {
                    anyhow::bail!("top_ports must be specified and greater than 0 for 'top' port strategy");
                }
            }
            super::types::PortStrategy::Range => {
                let start = config.tools.nmap.ports.range_start;
                let end = config.tools.nmap.ports.range_end;
                if start.is_none() || end.is_none() {
                    anyhow::bail!("range_start and range_end must be specified for 'range' port strategy");
                }
                if start.unwrap() >= end.unwrap() {
                    anyhow::bail!("range_start must be less than range_end");
                }
            }
            super::types::PortStrategy::List => {
                if config.tools.nmap.ports.specific_ports.is_none() || 
                   config.tools.nmap.ports.specific_ports.as_ref().unwrap().is_empty() {
                    anyhow::bail!("specific_ports must be specified and non-empty for 'list' port strategy");
                }
            }
            super::types::PortStrategy::Default => {
                // No validation needed for default
            }
        }

        Ok(())
    }

    /// Expand paths with tilde and environment variables
    fn expand_path(path: &str) -> PathBuf {
        if path.starts_with("~/") {
            if let Ok(home) = std::env::var("HOME") {
                return PathBuf::from(home).join(&path[2..]);
            }
        }
        PathBuf::from(path)
    }

    /// Save configuration to a file (for testing/export)
    #[allow(dead_code)]
    pub fn save_to_file(config: &GlobalConfig, path: &Path) -> Result<()> {
        let content = toml::to_string_pretty(config)
            .context("Failed to serialize configuration to TOML")?;
        
        std::fs::write(path, content)
            .with_context(|| format!("Failed to write config file: {:?}", path))?;
        
        Ok(())
    }

    /// Generate a default configuration file template
    #[allow(dead_code)]
    pub fn generate_template(path: &Path) -> Result<()> {
        let default_config = GlobalConfig::default();
        Self::save_to_file(&default_config, path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::NamedTempFile;

    #[test]
    fn test_load_default_config() {
        let config = ConfigLoader::load().unwrap();
        assert_eq!(config.concurrency.max_total_scans, 50);
        assert_eq!(config.concurrency.max_port_scans, 10);
        assert_eq!(config.tools.nmap.command, "nmap");
    }

    #[test]
    fn test_load_custom_config() {
        let mut temp_file = NamedTempFile::new().unwrap();
        let config_content = r#"
[concurrency]
max_total_scans = 100
max_port_scans = 20
max_service_scans = 80
min_file_descriptors = 2048
recommended_file_descriptors = 4096

[tools.nmap]
command = "custom-nmap"
base_args = ["-sS", "-O"]
"#;
        fs::write(&temp_file, config_content).unwrap();
        
        let config = ConfigLoader::load_with_custom_path(Some(temp_file.path())).unwrap();
        assert_eq!(config.concurrency.max_total_scans, 100);
        assert_eq!(config.concurrency.max_port_scans, 20);
        assert_eq!(config.tools.nmap.command, "custom-nmap");
        assert_eq!(config.tools.nmap.base_args, vec!["-sS", "-O"]);
    }

    #[test]
    fn test_validation_errors() {
        let mut temp_file = NamedTempFile::new().unwrap();
        let invalid_config = r#"
[concurrency]
max_total_scans = 0
max_port_scans = 10
"#;
        fs::write(&temp_file, invalid_config).unwrap();
        
        let result = ConfigLoader::load_with_custom_path(Some(temp_file.path()));
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("max_total_scans must be greater than 0"));
    }
}