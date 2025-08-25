use std::time::Duration;

/// UI-specific events for thread-safe communication with the single UI owner
#[derive(Debug, Clone)]
#[allow(dead_code)]
pub enum UiEvent {
    /// Initialize progress tracking
    InitProgress {
        target: String,
        total_tasks: usize,
    },
    
    /// Task lifecycle events
    TaskStarted {
        id: String,
        name: String,
    },
    TaskProgress {
        id: String,
        status: String,
    },
    TaskCompleted {
        id: String,
        result: TaskResult,
    },
    
    /// System monitoring
    SystemStats {
        cpu_percent: f32,
        memory_used_gb: f64,
    },
    
    /// Progress updates from RunState
    ProgressUpdate {
        completed: usize,
        total: usize,
    },
    
    /// Port discovery event
    PortDiscovered {
        port: u16,
        service: String,
    },
    
    /// Phase transition event
    PhaseChange {
        phase: String,
    },
    
    /// Plugin inventory - shows all available plugins
    PluginInventory {
        port_scanners: Vec<String>,
        service_scanners: Vec<String>,
    },
    
    /// UI lifecycle
    Shutdown,
}

#[derive(Debug, Clone)]
pub enum TaskResult {
    Success(String), // success message
    Failed(String),  // error message
}

/// Active task information for bounded display
#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct ActiveTask {
    pub id: String,
    pub name: String,
    pub status: String,
    pub started_at: std::time::Instant,
}

impl ActiveTask {
    #[allow(dead_code)]
    pub fn new(id: String, name: String) -> Self {
        Self {
            id,
            name,
            status: "initializing".to_string(),
            started_at: std::time::Instant::now(),
        }
    }
    
    #[allow(dead_code)]
    pub fn duration(&self) -> Duration {
        self.started_at.elapsed()
    }
}