use std::sync::Arc;
use tokio::sync::{Semaphore, Mutex};
use anyhow::Result;
use futures::future::try_join_all;
use super::{state::RunState, events::Event};
use crate::config::GlobalConfig;
use crate::plugins::types::{ServiceScan, PortScan};
use crate::ui::events::{UiEvent, TaskResult};
use crate::core::models::Service;
use tokio::sync::mpsc;

pub struct PluginRegistry {
    pub port_scans: Vec<Box<dyn crate::plugins::types::PortScan>>,
    pub service_scans: Vec<Box<dyn crate::plugins::types::ServiceScan>>,
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self {
            port_scans: vec![
                Box::new(crate::plugins::portscan_nmap::NmapPortScan),
                Box::new(crate::plugins::dns_enum::DnsEnum),
            ],
            service_scans: vec![
                Box::new(crate::plugins::http_probe::HttpProbe),
                Box::new(crate::plugins::httpx_probe::HttpxProbe),
            ],
        }
    }
}

pub async fn execute_all_async(state: &mut RunState, registry: &PluginRegistry, config: &GlobalConfig, ui_sender: &mpsc::UnboundedSender<UiEvent>) -> Result<()> {
    let max_ports = config.concurrency.max_port_scans;
    let max_services = config.concurrency.max_service_scans;
    let sem_ports = Arc::new(Semaphore::new(max_ports));
    let sem_svcs = Arc::new(Semaphore::new(max_services));

    // Send plugin inventory to UI so it knows what plugins are available
    let port_scanners: Vec<String> = registry.port_scans.iter().map(|p| p.name().to_string()).collect();
    let service_scanners: Vec<String> = registry.service_scans.iter().map(|p| p.name().to_string()).collect();
    
    let _ = ui_sender.send(UiEvent::PluginInventory {
        port_scanners: port_scanners.clone(),
        service_scanners: service_scanners.clone(),
    });

    // PHASE 1: PORT SCANS - TRUE PARALLEL EXECUTION
    let discovered: Vec<Service>;
    let total_port_plugins = registry.port_scans.len();
    
    tracing::info!("Phase 1: Starting {} port scan plugins in parallel", total_port_plugins);
    
    // Send phase change event
    let _ = ui_sender.send(UiEvent::PhaseChange {
        phase: format!("Phase 1: Port Scanning ({} plugins)", total_port_plugins),
    });
    
    // Initialize UI progress display with port scan count
    let _ = ui_sender.send(UiEvent::InitProgress {
        target: state.target.clone(),
        total_tasks: total_port_plugins,
    });
    
    // Execute port scans in parallel
    let mut port_scan_tasks = Vec::new();
    
    for plugin in &registry.port_scans {
        let plugin_name = plugin.name();
        let task_id = format!("port_{}", plugin_name);
        let ui_sender_clone = ui_sender.clone();
        let sem_permit = sem_ports.clone();
        
        // Clone state data needed for this task
        let target = state.target.clone(); 
        let dirs = state.dirs.clone();
        let target_obj = state.target_obj.clone();
        let config_clone = config.clone();
        
        // Create a task for this plugin
        let plugin_task = {
            let _plugin_name_clone = plugin_name.to_string();
            tokio::spawn(async move {
                let _permit = sem_permit.acquire().await?;
                
                // Start task in UI immediately
                let _ = ui_sender_clone.send(UiEvent::TaskStarted {
                    id: task_id.clone(),
                    name: plugin_name.to_string(),
                });
                let _ = ui_sender_clone.send(UiEvent::TaskProgress {
                    id: task_id.clone(),
                    status: "scanning".to_string(),
                });
                
                // Create temporary state for this plugin
                let mut temp_state = RunState {
                    target,
                    run_id: format!("temp_{}", plugin_name),
                    ports_open: Vec::new(),
                    services: Vec::new(),
                    tasks_started: 0,
                    tasks_completed: 0,
                    errors: Vec::new(),
                    target_obj,
                    dirs,
                    ui_sender: Some(ui_sender_clone.clone()),
                };
                
                tracing::info!("Starting parallel port scan: {}", plugin_name);
                
                // Create a concrete plugin instance based on the plugin name
                let result = match plugin_name {
                    "nmap_portscan" => {
                        let plugin = crate::plugins::portscan_nmap::NmapPortScan;
                        plugin.run(&mut temp_state, &config_clone).await
                    }
                    "naabu_portscan" => {
                        let plugin = crate::plugins::portscan_naabu::NaabuPortScan;
                        plugin.run(&mut temp_state, &config_clone).await
                    }
                    "dns_enum" => {
                        let plugin = crate::plugins::dns_enum::DnsEnum;
                        plugin.run(&mut temp_state, &config_clone).await
                    }
                    _ => {
                        tracing::warn!("Unknown plugin: {}, skipping", plugin_name);
                        Ok(Vec::new())
                    }
                };
                
                match result {
                    Ok(services) => {
                        let _ = ui_sender_clone.send(UiEvent::TaskCompleted {
                            id: task_id,
                            result: TaskResult::Success(format!("completed - {} services", services.len())),
                        });
                        tracing::info!("Completed parallel port scan: {} ({} services)", plugin_name, services.len());
                        Ok((services, temp_state.ports_open))
                    }
                    Err(e) => {
                        let _ = ui_sender_clone.send(UiEvent::TaskCompleted {
                            id: task_id,
                            result: TaskResult::Failed(format!("failed: {}", e)),
                        });
                        tracing::error!("Port scan failed {}: {}", plugin_name, e);
                        Err(e)
                    }
                }
            })
        };
        
        port_scan_tasks.push(plugin_task);
    }
    
    // Wait for all port scan tasks to complete and aggregate results
    let port_scan_results = try_join_all(port_scan_tasks).await?;
    
    use std::collections::HashMap;
    let mut service_map: HashMap<(String, u16), Service> = HashMap::new();
    
    for result in port_scan_results {
        match result {
            Ok((services, ports)) => {
                // Deduplicate services by (address, port) key
                for service in services {
                    let key = (service.address.clone(), service.port);
                    service_map.insert(key, service);
                }
                
                // Aggregate discovered ports into main state
                for (port, service_name) in ports {
                    state.on_event(Event::PortDiscovered(port, service_name));
                }
            }
            Err(e) => {
                tracing::warn!("Port scan task failed (continuing with other plugins): {}", e);
                // Don't fail the entire scan if one plugin fails
                // Continue with results from successful plugins
            }
        }
    }
    
    // Convert deduplicated services back to vector
    discovered = service_map.into_values().collect();
    
    tracing::info!("Port scanning phase complete. Found {} services", discovered.len());
    
    if discovered.is_empty() {
        tracing::warn!("No services discovered by port scans. Service scanning phase will be skipped.");
        let _ = ui_sender.send(UiEvent::Shutdown);
        return Ok(());
    }

    // PHASE 2: SERVICE SCANS - TRUE PARALLEL EXECUTION WITH REAL-TIME PROGRESS
    let mut service_tasks = Vec::new();
    let mut total_service_tasks = 0;
    
    // Count total tasks first for progress display
    for service in discovered.iter() {
        tracing::info!("Checking service {}:{} ({})", service.address, service.port, service.name);
        for plugin in &registry.service_scans {
            if plugin.matches(service) {
                total_service_tasks += 1;
                tracing::info!("Plugin {} matches service {}:{}", plugin.name(), service.address, service.port);
            }
        }
    }
    
    tracing::info!("Phase 2: Found {} service scan tasks", total_service_tasks);
    
    if total_service_tasks == 0 {
        tracing::info!("No matching services found for service scanning");
        let _ = ui_sender.send(UiEvent::Shutdown);
        return Ok(());
    }
    
    // Send phase change event for service scanning
    let _ = ui_sender.send(UiEvent::PhaseChange {
        phase: format!("Phase 2: Service Scanning ({} tasks)", total_service_tasks),
    });
    
    // Update UI for service scanning phase (adds to existing progress)
    let _ = ui_sender.send(UiEvent::InitProgress {
        target: state.target.clone(),
        total_tasks: total_service_tasks,
    });
    
    // Shared progress tracker
    let completed_count = Arc::new(Mutex::new(0usize));
    let active_tasks: Arc<Mutex<HashMap<String, std::time::Instant>>> = Arc::new(Mutex::new(HashMap::new()));
    
    for service in discovered.iter() {
        for plugin in &registry.service_scans {
            if !plugin.matches(service) { continue; }
            
            let plugin_name = plugin.name();
            let service = service.clone();
            let sem_svcs = Arc::clone(&sem_svcs);
            let completed_count = Arc::clone(&completed_count);
            let active_tasks = Arc::clone(&active_tasks);
            
            // Create owned data for the spawned task
            let state_data = state.clone();
            let config_data = config.clone();
            let _target = state.target.clone();
            let _service_plugin_name = format!("{}({}:{})", plugin_name, service.address, service.port);
            
            // Use a concrete plugin implementation approach
            if plugin_name == "http_probe" {
                let plugin = crate::plugins::http_probe::HttpProbe;
                let task_id = format!("{}:{}:{}", plugin_name, service.address, service.port);
                let task_id_clone = task_id.clone();
                
                // Create task ID and UI event sender for this service scan
                let service_plugin_name = format!("{}({}:{})", plugin_name, service.address, service.port);
                let ui_sender_clone = ui_sender.clone();
                
                let task = tokio::spawn(async move {
                    // Start task in UI immediately (before acquiring semaphore for visibility)
                    let _ = ui_sender_clone.send(UiEvent::TaskStarted {
                        id: task_id.clone(),
                        name: service_plugin_name.clone(),
                    });
                    
                    let _permit = sem_svcs.acquire().await.map_err(|e| anyhow::anyhow!("Failed to acquire semaphore: {}", e))?;
                    
                    let _ = ui_sender_clone.send(UiEvent::TaskProgress {
                        id: task_id.clone(),
                        status: "scanning".to_string(),
                    });
                    
                    // Mark task as active
                    {
                        let mut active = active_tasks.lock().await;
                        active.insert(task_id.clone(), std::time::Instant::now());
                    }
                    
                    tracing::info!("Starting service scan: {} for {}:{}", plugin_name, service.address, service.port);
                    
                    let result = plugin.run(&service, &state_data, &config_data).await;
                    
                    // Remove from active and increment completed
                    {
                        let mut active = active_tasks.lock().await;
                        active.remove(&task_id);
                    }
                    
                    {
                        let mut completed = completed_count.lock().await;
                        *completed += 1;
                    }
                    
                    match result {
                        Ok(_) => {
                            let _ = ui_sender_clone.send(UiEvent::TaskCompleted {
                                id: task_id,
                                result: TaskResult::Success("completed".to_string()),
                            });
                            tracing::info!("Completed service scan: {} for {}:{}", plugin_name, service.address, service.port);
                            Ok(())
                        }
                        Err(e) => {
                            let _ = ui_sender_clone.send(UiEvent::TaskCompleted {
                                id: task_id,
                                result: TaskResult::Failed(format!("failed: {}", e)),
                            });
                            tracing::error!("Service scan failed {} for {}:{}: {}", plugin_name, service.address, service.port, e);
                            Err(e)
                        }
                    }
                });
                
                service_tasks.push((task, task_id_clone));
            }
            // Add more plugin types here as needed
        }
    }
    
    // Execute all tasks concurrently
    let tasks: Vec<_> = service_tasks.into_iter().map(|(task, _)| task).collect();
    
    // Wait for all tasks to complete
    let results = try_join_all(tasks).await;
    
    match results {
        Ok(_) => {
            let _completed = *completed_count.lock().await;
            tracing::info!("All service scans completed successfully");
        }
        Err(e) => {
            tracing::error!("Service scan task failed: {}", e);
            return Err(anyhow::anyhow!("Service scan task failed: {}", e));
        }
    }
    
    tracing::info!("All scanning phases complete");
    let _ = ui_sender.send(UiEvent::Shutdown);
    Ok(())
}

#[allow(dead_code)]
pub async fn execute_all(state: &mut RunState, config: &GlobalConfig) -> Result<()> {
    let registry = PluginRegistry::default();
    
    // This is a simplified version - real usage should have UI sender from app
    let (_ui_sender, mut _ui_receiver) = mpsc::unbounded_channel::<UiEvent>();
    // Note: This won't have live progress - use execute_all_with_ui_sender for full functionality
    
    execute_all_async(state, &registry, config, &_ui_sender).await
}

pub async fn execute_all_with_ui_sender(state: &mut RunState, config: &GlobalConfig, ui_sender: &mpsc::UnboundedSender<UiEvent>) -> Result<()> {
    let registry = PluginRegistry::default();
    execute_all_async(state, &registry, config, ui_sender).await
}
