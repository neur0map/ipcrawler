use super::{events::Event, models::{Service, Target, RunDirs}};
use crate::core::errors::ExecError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct RunState {
    pub target: String,  // Just the target value for serialization
    pub run_id: String,
    pub ports_open: Vec<(u16, String)>,
    pub services: Vec<Service>,
    pub tasks_started: usize,
    pub tasks_completed: usize,
    pub errors: Vec<ExecError>,
    
    #[serde(skip)]
    pub target_obj: Option<Target>,  // Full target object, not serialized
    
    #[serde(skip)]
    pub dirs: Option<RunDirs>,  // Dirs reference, not serialized
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
            target_obj: Some(target.clone()),
            dirs: Some(dirs.clone()),
        }
    }

    pub fn on_event(&mut self, ev: Event) {
        match ev {
            Event::TaskStarted(name) => {
                tracing::info!("Task started: {}", name);
                self.tasks_started += 1;
            }
            Event::TaskCompleted(name) => {
                tracing::info!("Task completed: {}", name);
                self.tasks_completed += 1;
            }
            Event::PortDiscovered(p, n) => {
                tracing::info!("Port discovered: {}:{}", p, n);
                self.ports_open.push((p, n));
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
}