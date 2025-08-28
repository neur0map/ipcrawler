use super::{
    events::Event,
    models::{RunDirs, Service, Target},
};
use crate::core::errors::ExecError;
use crate::ui::events::UiEvent;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginFindings {
    pub plugin_name: String,
    pub high_value_files: usize,
    pub secrets_found: usize,
    pub total_findings: usize,
    pub summary: String,
    pub artifacts_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunState {
    pub target: String, // Just the target value for serialization
    pub run_id: String,
    pub ports_open: Vec<(u16, String)>,
    pub services: Vec<Service>,
    pub tasks_started: usize,
    pub tasks_completed: usize,
    pub errors: Vec<ExecError>,
    pub plugin_findings: std::collections::HashMap<String, PluginFindings>,

    #[serde(skip)]
    #[allow(dead_code)]
    pub target_obj: Option<Target>, // Full target object, not serialized

    #[serde(skip)]
    #[allow(dead_code)]
    pub dirs: Option<RunDirs>, // Dirs reference, not serialized

    #[serde(skip)]
    pub ui_sender: Option<mpsc::UnboundedSender<UiEvent>>, // UI event channel
}

impl RunState {
    pub fn new(target: &Target, dirs: &RunDirs) -> Self {
        Self {
            target: target.value.clone(),
            run_id: target.run_id.clone(),
            ports_open: vec![],
            services: vec![],
            tasks_started: 0,
            tasks_completed: 0,
            errors: vec![],
            plugin_findings: std::collections::HashMap::new(),
            target_obj: Some(target.clone()),
            dirs: Some(dirs.clone()),
            ui_sender: None,
        }
    }

    pub fn set_ui_sender(&mut self, sender: mpsc::UnboundedSender<UiEvent>) {
        self.ui_sender = Some(sender);
    }

    pub fn on_event(&mut self, ev: Event) {
        match ev {
            Event::TaskStarted(name) => {
                tracing::info!("Task started: {}", name);
                self.tasks_started += 1;

                // Emit UI event
                self.emit_progress_update();
            }
            Event::TaskCompleted(name) => {
                tracing::info!("Task completed: {}", name);
                self.tasks_completed += 1;

                // Emit UI progress update
                self.emit_progress_update();
            }
            Event::PortDiscovered(p, n) => {
                tracing::info!("Port discovered: {}:{}", p, n.clone());
                self.ports_open.push((p, n.clone()));

                // Emit UI event for real-time port discovery
                if let Some(sender) = &self.ui_sender {
                    let _ = sender.send(crate::ui::events::UiEvent::PortDiscovered {
                        port: p,
                        service: n,
                    });
                }
            }
            Event::ServiceDiscovered(s) => {
                tracing::info!("Service discovered: {}:{}/{:?}", s.address, s.port, s.proto);
                self.services.push(s);
            }
            Event::TaskFailed(e) => {
                tracing::error!("Task failed: {:?}", e);
                self.errors.push(e);
            }
        }
    }

    /// Emit progress update to UI
    fn emit_progress_update(&self) {
        if let Some(sender) = &self.ui_sender {
            let _ = sender.send(UiEvent::ProgressUpdate {
                completed: self.tasks_completed,
                total: self.tasks_started.max(self.tasks_completed), // Use max to handle edge cases
            });
        }
    }
}
