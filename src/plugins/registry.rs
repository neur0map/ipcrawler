use std::collections::HashMap;
use anyhow::Result;
use crate::plugins::types::PluginPhase;

pub struct PluginRegistry {
    pub recon_plugins: Vec<Box<dyn crate::plugins::types::PortScan>>,
    pub port_scan_plugins: Vec<Box<dyn crate::plugins::types::PortScan>>, 
    pub service_probe_plugins: Vec<Box<dyn crate::plugins::types::ServiceScan>>,
    pub vulnerability_plugins: Vec<Box<dyn crate::plugins::types::PortScan>>,
}

impl PluginRegistry {
    pub fn new() -> Self {
        Self {
            recon_plugins: vec![
                Box::new(crate::plugins::dns_enum::DnsEnum),
            ],
            port_scan_plugins: vec![
                Box::new(crate::plugins::portscan_nmap::NmapPortScan),
            ],
            service_probe_plugins: vec![
                Box::new(crate::plugins::http_probe::HttpProbe),
                Box::new(crate::plugins::httpx_probe::HttpxProbe),
            ],
            vulnerability_plugins: vec![
                // Add nuclei or other vuln scanners here
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
        
        tracing::info!("All {} plugins validated successfully", self.total_plugins());
        self.log_plugin_summary();
        
        Ok(())
    }
    
    fn get_plugin_tools(&self, plugin_name: &str) -> Result<Vec<String>> {
        let tools = match plugin_name {
            "dns_enum" => vec!["dig".to_string()],
            "nmap_portscan" => vec!["nmap".to_string()],
            "http_probe" => vec!["curl".to_string()],
            "httpx_probe" => vec!["httpx".to_string()],
            _ => vec![],
        };
        Ok(tools)
    }
    
    pub fn total_plugins(&self) -> usize {
        self.recon_plugins.len() + 
        self.port_scan_plugins.len() + 
        self.service_probe_plugins.len() + 
        self.vulnerability_plugins.len()
    }
    
    pub fn get_phase_counts(&self) -> HashMap<PluginPhase, usize> {
        let mut counts = HashMap::new();
        counts.insert(PluginPhase::Reconnaissance, self.recon_plugins.len());
        counts.insert(PluginPhase::PortDiscovery, self.port_scan_plugins.len());
        counts.insert(PluginPhase::ServiceProbing, self.service_probe_plugins.len());
        counts.insert(PluginPhase::Vulnerability, self.vulnerability_plugins.len());
        counts
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
        
        tracing::info!("  Service Probing: {} plugins", self.service_probe_plugins.len());
        for plugin in &self.service_probe_plugins {
            tracing::info!("    - {}", plugin.name());
        }
        
        if !self.vulnerability_plugins.is_empty() {
            tracing::info!("  Vulnerability Scanning: {} plugins", self.vulnerability_plugins.len());
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