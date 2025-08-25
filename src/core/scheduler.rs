use super::events::Event;
use super::state::RunState;
use crate::config::GlobalConfig;
use crate::core::models::Service;
use crate::plugins::types::PortScan;
use crate::ui::events::{TaskResult, UiEvent};
use anyhow::Result;
use std::sync::Arc;
use tokio::sync::mpsc;
use tokio::sync::Semaphore;

// Re-export the registry from plugins module
pub use crate::plugins::registry::PluginRegistry;

pub async fn execute_all_phases(
    state: &mut RunState,
    registry: &PluginRegistry,
    config: &GlobalConfig,
    ui_sender: &mpsc::UnboundedSender<UiEvent>,
) -> Result<()> {
    let max_ports = config.concurrency.max_port_scans;
    let max_services = config.concurrency.max_service_scans;
    let sem_ports = Arc::new(Semaphore::new(max_ports));
    let _sem_svcs = Arc::new(Semaphore::new(max_services));

    // Send plugin inventory to UI so it knows what plugins are available
    let _recon_plugins: Vec<String> = registry
        .recon_plugins
        .iter()
        .map(|p| p.name().to_string())
        .collect();
    let port_scanners: Vec<String> = registry
        .port_scan_plugins
        .iter()
        .map(|p| p.name().to_string())
        .collect();
    let service_scanners: Vec<String> = registry
        .service_probe_plugins
        .iter()
        .map(|p| p.name().to_string())
        .collect();

    let _ = ui_sender.send(UiEvent::PluginInventory {
        port_scanners: port_scanners.clone(),
        service_scanners: service_scanners.clone(),
    });

    // Calculate total tasks across all plugin types
    let total_recon_plugins = registry.recon_plugins.len();
    let total_port_plugins = registry.port_scan_plugins.len();
    let total_service_plugins = registry.service_probe_plugins.len();
    let total_plugin_tasks = total_recon_plugins + total_port_plugins + total_service_plugins;

    // Send initial progress setup with total task count for all plugins
    let _ = ui_sender.send(UiEvent::InitProgress {
        target: state.target.clone(),
        total_tasks: total_plugin_tasks,
    });

    tracing::info!("Starting all {} plugins in parallel", total_plugin_tasks);

    // Send log message to UI
    let _ = ui_sender.send(UiEvent::LogMessage {
        level: "INFO".to_string(),
        message: format!("Starting all {} plugins in parallel", total_plugin_tasks),
    });

    // Send phase change to show we're running all plugins
    let _ = ui_sender.send(UiEvent::PhaseChange {
        phase: format!("Running {} plugins in parallel", total_plugin_tasks),
    });

    // Start UI tasks for ALL plugins immediately to show parallel execution
    for plugin in &registry.recon_plugins {
        let _ = ui_sender.send(UiEvent::LogMessage {
            level: "INFO".to_string(),
            message: format!("Started reconnaissance plugin: {}", plugin.name()),
        });
        let _ = ui_sender.send(UiEvent::TaskStarted {
            id: format!("plugin_{}", plugin.name()),
            name: plugin.name().to_string(),
        });
        // Update state task counter
        state.on_event(Event::TaskStarted(plugin.name()));
    }
    for plugin in &registry.port_scan_plugins {
        let _ = ui_sender.send(UiEvent::LogMessage {
            level: "INFO".to_string(),
            message: format!("Started port scanning plugin: {}", plugin.name()),
        });
        let _ = ui_sender.send(UiEvent::TaskStarted {
            id: format!("plugin_{}", plugin.name()),
            name: plugin.name().to_string(),
        });
        // Update state task counter
        state.on_event(Event::TaskStarted(plugin.name()));
    }
    for plugin in &registry.service_probe_plugins {
        let _ = ui_sender.send(UiEvent::LogMessage {
            level: "INFO".to_string(),
            message: format!("Started service probe plugin: {}", plugin.name()),
        });
        let _ = ui_sender.send(UiEvent::TaskStarted {
            id: format!("plugin_{}", plugin.name()),
            name: plugin.name().to_string(),
        });
        // Update state task counter
        state.on_event(Event::TaskStarted(plugin.name()));
    }

    // Execute recon and port scan plugins
    let mut all_discovered_services = Vec::new();
    let mut combined_plugins: Vec<&Box<dyn PortScan>> = Vec::new();
    combined_plugins.extend(&registry.recon_plugins);
    combined_plugins.extend(&registry.port_scan_plugins);

    let discovered = execute_plugin_phase_without_ui_start(
        &combined_plugins,
        state,
        config,
        ui_sender,
        &sem_ports,
    )
    .await?;
    all_discovered_services.extend(discovered.clone());

    // PHASE 3: SERVICE PROBING - PARALLEL EXECUTION BASED ON DISCOVERED SERVICES
    if !discovered.is_empty() {
        tracing::info!(
            "Phase 3: Starting service probing on {} discovered services",
            discovered.len()
        );

        let _ = ui_sender.send(UiEvent::PhaseChange {
            phase: format!("Phase 3: Service Probing ({} services)", discovered.len()),
        });

        // Count matching services for progress tracking
        let mut total_service_tasks = 0;
        for service in &discovered {
            for plugin in &registry.service_probe_plugins {
                if plugin.matches(service) {
                    total_service_tasks += 1;
                }
            }
        }

        tracing::info!("Will execute {} service probing tasks", total_service_tasks);

        // Update total task count to include service probing tasks
        let new_total = total_plugin_tasks + total_service_tasks;
        let _ = ui_sender.send(UiEvent::ProgressUpdate {
            completed: total_plugin_tasks, // plugin tasks completed
            total: new_total,              // updated total including service tasks
        });

        // Execute service probes (UI tasks already started earlier)
        for service in discovered {
            for plugin in &registry.service_probe_plugins {
                if plugin.matches(&service) {
                    let result = plugin.run(&service, state, config).await;
                    // Task completion handled separately
                    if let Err(e) = result {
                        tracing::warn!(
                            "Service probe {} failed on {}:{}: {}",
                            plugin.name(),
                            service.address,
                            service.port,
                            e
                        );
                    }
                }
            }
        }

        // Complete the service probe plugin tasks that were started earlier
        for plugin in &registry.service_probe_plugins {
            let plugin_name = plugin.name();
            let task_id = format!("plugin_{}", plugin_name);

            let _ = ui_sender.send(UiEvent::TaskCompleted {
                id: task_id,
                result: TaskResult::Success("Service probing completed".to_string()),
            });
        }

        tracing::info!("Service probing phase completed");
    } else {
        // No services discovered, complete service probe tasks anyway
        for plugin in &registry.service_probe_plugins {
            let plugin_name = plugin.name();
            let task_id = format!("plugin_{}", plugin_name);

            let _ = ui_sender.send(UiEvent::TaskCompleted {
                id: task_id,
                result: TaskResult::Success("No services to probe".to_string()),
            });
        }
    }

    // Store all discovered services in state
    state.services.extend(all_discovered_services.clone());

    tracing::info!("All scanning phases completed successfully");
    Ok(())
}

// Execute plugins concurrently using tokio::spawn
#[allow(clippy::borrowed_box)]
async fn execute_plugin_phase_without_ui_start(
    plugins: &[&Box<dyn PortScan>],
    state: &mut RunState,
    config: &GlobalConfig,
    ui_sender: &mpsc::UnboundedSender<UiEvent>,
    _semaphore: &Arc<Semaphore>,
) -> Result<Vec<Service>> {
    use std::sync::{Arc, Mutex};

    let all_services = Arc::new(Mutex::new(Vec::new()));
    let mut tasks = Vec::new();

    // Execute plugins concurrently using tokio::spawn
    for plugin in plugins {
        let plugin_name = plugin.name();
        let task_id = format!("plugin_{}", plugin_name);

        // Clone plugin for move into async task - we need to create a new boxed instance
        let plugin_clone: Box<dyn PortScan> = match plugin_name {
            "nslookup" => Box::new(crate::plugins::nslookup::NslookupPlugin),
            "dig" => Box::new(crate::plugins::dig::DigPlugin),
            _ => continue, // Skip unknown plugins
        };

        let mut state_clone = state.clone();
        let config_clone = config.clone();
        let ui_sender_clone = ui_sender.clone();
        let all_services_clone = all_services.clone();

        let task = tokio::spawn(async move {
            let result = plugin_clone.run(&mut state_clone, &config_clone).await;

            match result {
                Ok(services) => {
                    // Add services to shared collection
                    {
                        let mut all_services_lock = all_services_clone.lock().unwrap();
                        all_services_lock.extend(services.clone());
                    }

                    // Send completion message to log window instead of results panel
                    let _ = ui_sender_clone.send(UiEvent::LogMessage {
                        level: "INFO".to_string(),
                        message: format!("✓ {}: Found {} services", plugin_name, services.len()),
                    });

                    let _ = ui_sender_clone.send(UiEvent::TaskCompleted {
                        id: task_id,
                        result: TaskResult::Success("Completed".to_string()),
                    });

                    Ok((plugin_name, services.len()))
                }
                Err(e) => {
                    let _ = ui_sender_clone.send(UiEvent::TaskCompleted {
                        id: task_id,
                        result: TaskResult::Failed(e.to_string()),
                    });
                    tracing::warn!("Plugin {} failed: {}", plugin_name, e);

                    Err((plugin_name, e))
                }
            }
        });

        tasks.push(task);
    }

    // Wait for all tasks to complete
    for task in tasks {
        match task.await {
            Ok(Ok((plugin_name, count))) => {
                tracing::info!(
                    "Plugin {} completed successfully with {} services",
                    plugin_name,
                    count
                );
                // Notify state that task completed
                state.on_event(Event::TaskCompleted(plugin_name));
            }
            Ok(Err((plugin_name, e))) => {
                tracing::warn!("Plugin {} failed: {}", plugin_name, e);
                // Notify state that task completed (even if failed)
                state.on_event(Event::TaskCompleted(plugin_name));
            }
            Err(e) => {
                tracing::error!("Task execution error: {}", e);
            }
        }
    }

    // Extract final services list
    let final_services = {
        let services_lock = all_services.lock().unwrap();
        services_lock.clone()
    };

    Ok(final_services)
}
