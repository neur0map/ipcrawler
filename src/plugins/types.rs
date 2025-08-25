use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::Service, state::RunState};
use crate::config::GlobalConfig;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum PluginPhase {
    Reconnaissance,  // DNS enum, subdomain discovery
    PortDiscovery,   // Nmap, masscan - find open ports
    ServiceProbing,  // HTTP probes, service enumeration
    Vulnerability,   // Nuclei, custom vuln scans
}

#[derive(Debug, Clone)]
pub struct PluginInfo {
    pub name: &'static str,
    pub phase: PluginPhase,
    pub description: &'static str,
    pub dependencies: Vec<&'static str>,  // Tool dependencies (nmap, dig, curl, etc.)
    pub required_tools: Vec<&'static str>,
}

pub trait Plugin: Send + Sync {
    fn info(&self) -> PluginInfo;
    fn validate_dependencies(&self) -> Result<()>;
}

#[async_trait]
pub trait ReconPlugin: Plugin {
    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>>;
}

#[async_trait]
pub trait PortScanPlugin: Plugin {
    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>>;
}

// Keep old trait for backward compatibility
#[async_trait]
pub trait PortScan: Send + Sync {
    fn name(&self) -> &'static str;
    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>>;
}

#[async_trait]
pub trait ServiceProbePlugin: Plugin {
    fn matches(&self, service: &Service) -> bool;
    async fn run(&self, service: &Service, state: &RunState, config: &GlobalConfig) -> Result<()>;
}

// Keep old trait for backward compatibility
#[async_trait]
pub trait ServiceScan: Send + Sync {
    fn name(&self) -> &'static str;
    fn matches(&self, service: &Service) -> bool;
    async fn run(&self, service: &Service, state: &RunState, config: &GlobalConfig) -> Result<()>;
}

#[async_trait]
#[allow(dead_code)]
pub trait Report: Send + Sync {
    fn name(&self) -> &'static str;
    async fn generate(&self, state: &RunState) -> Result<()>;
}
