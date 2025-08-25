use crate::config::GlobalConfig;
use crate::core::{models::Service, state::RunState};
use anyhow::Result;
use async_trait::async_trait;

// Main trait for port scanning plugins
#[async_trait]
pub trait PortScan: Send + Sync {
    fn name(&self) -> &'static str;
    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>>;
}

// Main trait for service scanning plugins
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
