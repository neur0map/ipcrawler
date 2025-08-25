use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::Service, state::RunState};
use crate::config::GlobalConfig;

#[async_trait]
pub trait PortScan: Send + Sync {
    fn name(&self) -> &'static str;
    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>>;
}

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
