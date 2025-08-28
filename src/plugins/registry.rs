use anyhow::Result;

pub struct PluginRegistry {
    pub recon_plugins: Vec<Box<dyn crate::plugins::types::PortScan>>,
    pub port_scan_plugins: Vec<Box<dyn crate::plugins::types::PortScan>>,
    pub service_probe_plugins: Vec<Box<dyn crate::plugins::types::ServiceScan>>,
    pub vulnerability_plugins: Vec<Box<dyn crate::plugins::types::PortScan>>,
}

impl PluginRegistry {
    pub fn new() -> Self {
        let mut recon_plugins: Vec<Box<dyn crate::plugins::types::PortScan>> = vec![
            Box::new(crate::plugins::nslookup::NslookupPlugin),
            Box::new(crate::plugins::dig::DigPlugin),
        ];

        // Only add hosts discovery plugin if tools are available
        if Self::hosts_discovery_tools_available() {
            recon_plugins.push(Box::new(
                crate::plugins::hosts_discovery::HostsDiscoveryPlugin,
            ));
        } else {
            tracing::info!("Hosts discovery plugin disabled - dnsx or httpx not available");
        }

        let mut port_scan_plugins: Vec<Box<dyn crate::plugins::types::PortScan>> = vec![];

        // Only add port scanner plugin if tools are available
        if Self::port_scanner_tools_available() {
            port_scan_plugins.push(Box::new(crate::plugins::port_scanner::PortScannerPlugin));
        } else {
            tracing::info!("Port scanner plugin disabled - rustscan or nmap not available");
        }

        let mut service_probe_plugins: Vec<Box<dyn crate::plugins::types::ServiceScan>> = vec![];
        
        // Only add looter plugin if tools are available
        if Self::looter_tools_available() {
            // Create a default global config for looter plugin initialization
            let default_config = crate::config::types::GlobalConfig::default();
            match crate::plugins::looter::LooterPlugin::new(&default_config) {
                Ok(looter_plugin) => {
                    service_probe_plugins.push(Box::new(looter_plugin));
                }
                Err(e) => {
                    tracing::warn!("Failed to initialize looter plugin: {}", e);
                }
            }
        } else {
            tracing::info!("Looter plugin disabled - required tools not available");
        }

        Self {
            recon_plugins,
            port_scan_plugins,
            service_probe_plugins,
            vulnerability_plugins: vec![
                // Empty for now
            ],
        }
    }

    pub fn validate_all_plugins(&self) -> Result<()> {
        let mut all_tools = std::collections::HashSet::new();

        // Check recon plugins
        for plugin in &self.recon_plugins {
            let tools = self.get_plugin_tools(plugin.name())?;
            all_tools.extend(tools);
        }

        // Check port scan plugins
        for plugin in &self.port_scan_plugins {
            let tools = self.get_plugin_tools(plugin.name())?;
            all_tools.extend(tools);
        }

        // Check service probe plugins
        for plugin in &self.service_probe_plugins {
            let tools = self.get_plugin_tools(plugin.name())?;
            all_tools.extend(tools);
        }

        // Validate all required tools are available
        let mut missing_tools = Vec::new();
        for tool in &all_tools {
            if which::which(tool).is_err() {
                missing_tools.push(tool.clone());
            }
        }

        if !missing_tools.is_empty() {
            anyhow::bail!(
                "Missing required tools for plugins: {}. Install them with 'make tools'",
                missing_tools.join(", ")
            );
        }

        tracing::info!(
            "All {} plugins validated successfully",
            self.total_plugins()
        );
        self.log_plugin_summary();

        Ok(())
    }

    fn get_plugin_tools(&self, plugin_name: &str) -> Result<Vec<String>> {
        let tools = match plugin_name {
            "nslookup" => vec!["nslookup".to_string()],
            "dig" => vec!["dig".to_string()],
            "hosts_discovery" => {
                // Only validate if plugin is actually loaded
                if Self::hosts_discovery_tools_available() {
                    vec!["dnsx".to_string(), "httpx".to_string()]
                } else {
                    vec![]
                }
            }
            "port_scanner" => {
                // Only validate if plugin is actually loaded
                if Self::port_scanner_tools_available() {
                    // Require nmap, rustscan is optional
                    vec!["nmap".to_string()]
                } else {
                    vec![]
                }
            }
            "looter" => {
                // Only validate if plugin is actually loaded
                if Self::looter_tools_available() {
                    // Check for minimum required tools - one from each category
                    let mut tools = vec![];
                    if which::which("katana").is_ok() {
                        tools.push("katana".to_string());
                    } else if which::which("hakrawler").is_ok() {
                        tools.push("hakrawler".to_string());
                    }
                    
                    if which::which("feroxbuster").is_ok() {
                        tools.push("feroxbuster".to_string());
                    } else if which::which("ffuf").is_ok() {
                        tools.push("ffuf".to_string());
                    } else if which::which("gobuster").is_ok() {
                        tools.push("gobuster".to_string());
                    }
                    
                    if which::which("xh").is_ok() {
                        tools.push("xh".to_string());
                    }
                    
                    tools
                } else {
                    vec![]
                }
            }
            _ => vec![],
        };
        Ok(tools)
    }

    pub fn total_plugins(&self) -> usize {
        self.recon_plugins.len()
            + self.port_scan_plugins.len()
            + self.service_probe_plugins.len()
            + self.vulnerability_plugins.len()
    }

    /// Check if hosts discovery tools (dnsx, httpx) are available
    fn hosts_discovery_tools_available() -> bool {
        which::which("dnsx").is_ok() && which::which("httpx").is_ok()
    }

    /// Check if port scanner tools (rustscan, nmap) are available
    /// Allow plugin to load if at least nmap is available
    fn port_scanner_tools_available() -> bool {
        which::which("nmap").is_ok()
    }

    /// Check if looter plugin tools are available
    /// Require at least basic tools for the plugin to be useful
    fn looter_tools_available() -> bool {
        // Check for essential tools - at least one crawler and one directory brute-forcer
        let crawler_available = which::which("katana").is_ok() || which::which("hakrawler").is_ok();
        let brute_forcer_available = which::which("feroxbuster").is_ok() || 
                                   which::which("ffuf").is_ok() || 
                                   which::which("gobuster").is_ok();
        let http_client_available = which::which("xh").is_ok() || which::which("curl").is_ok();
        
        crawler_available && brute_forcer_available && http_client_available
    }

    pub fn log_plugin_summary(&self) {
        tracing::info!("Plugin Registry Summary:");
        tracing::info!("  Reconnaissance: {} plugins", self.recon_plugins.len());
        for plugin in &self.recon_plugins {
            tracing::info!("    - {}", plugin.name());
        }

        tracing::info!("  Port Discovery: {} plugins", self.port_scan_plugins.len());
        for plugin in &self.port_scan_plugins {
            tracing::info!("    - {}", plugin.name());
        }

        tracing::info!(
            "  Service Probing: {} plugins",
            self.service_probe_plugins.len()
        );
        for plugin in &self.service_probe_plugins {
            tracing::info!("    - {}", plugin.name());
        }

        if !self.vulnerability_plugins.is_empty() {
            tracing::info!(
                "  Vulnerability Scanning: {} plugins",
                self.vulnerability_plugins.len()
            );
            for plugin in &self.vulnerability_plugins {
                tracing::info!("    - {}", plugin.name());
            }
        }
    }
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self::new()
    }
}
