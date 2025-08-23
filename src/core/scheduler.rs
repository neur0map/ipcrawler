use std::sync::Arc;
use tokio::sync::Semaphore;
use anyhow::Result;
use super::{state::RunState, events::Event};
use crate::config::GlobalConfig;

pub struct PluginRegistry {
    pub port_scans: Vec<Box<dyn crate::plugins::types::PortScan>>,
    pub service_scans: Vec<Box<dyn crate::plugins::types::ServiceScan>>,
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self {
            port_scans: vec![
                Box::new(crate::plugins::portscan_nmap::NmapPortScan),
            ],
            service_scans: vec![
                Box::new(crate::plugins::http_probe::HttpProbe),
            ],
        }
    }
}

pub async fn execute_all_async(state: &mut RunState, registry: &PluginRegistry, config: &GlobalConfig) -> Result<()> {
    let max_scans = config.concurrency.max_total_scans;
    let max_ports = config.concurrency.max_port_scans;
    let sem_ports = Arc::new(Semaphore::new(max_ports));
    let sem_svcs = Arc::new(Semaphore::new(max_scans - max_ports));

    // Port scans
    let mut discovered = vec![];
    for p in &registry.port_scans {
        let _permit = sem_ports.acquire().await?;
        state.on_event(Event::TaskStarted(p.name()));
        match p.run(state, config).await {
            Ok(mut svcs) => {
                for svc in &svcs {
                    state.on_event(Event::ServiceDiscovered(svc.clone()));
                }
                discovered.append(&mut svcs);
                state.on_event(Event::TaskCompleted(p.name()));
            }
            Err(e) => {
                tracing::error!("Port scan failed: {}", e);
                return Err(e);
            }
        }
    }

    // Service scans
    for s in discovered.iter() {
        for plg in &registry.service_scans {
            if !plg.matches(s) { continue; }
            let _permit = sem_svcs.acquire().await?;
            state.on_event(Event::TaskStarted(plg.name()));
            if let Err(e) = plg.run(s, state, config).await {
                tracing::error!("Service scan failed: {}", e);
                return Err(e);
            }
            state.on_event(Event::TaskCompleted(plg.name()));
        }
    }

    Ok(())
}

pub fn execute_all(state: &mut RunState, config: &GlobalConfig) -> Result<()> {
    let registry = PluginRegistry::default();
    tokio::runtime::Runtime::new()?.block_on(execute_all_async(state, &registry, config))
}
