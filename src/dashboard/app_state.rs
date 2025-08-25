use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy)]
pub enum AppStatus {
    Running,
    Completed,
}

#[derive(Debug, Clone)]
pub struct AppState {
    pub controls: Controls,
    pub system: SystemStats,
    pub scan: ScanProgress,
    pub tasks: Vec<Task>,
    pub tabs: TabBar,
    pub results: Results,
    pub target: String,
    pub status: AppStatus,
    pub start_time: Instant,
}

#[derive(Debug, Clone)]
pub struct Controls {
    pub target_text: String,
    pub elapsed: Duration,
}

#[derive(Debug, Clone)]
pub struct SystemStats {
    pub cpu_pct: f32,
    pub ram_gb: f64,
}

#[derive(Debug, Clone)]
pub struct ScanProgress {
    pub phase_label: String,
    pub progress_pct: u8,
    pub tasks_done: usize,
    pub tasks_total: usize,
}

#[derive(Debug, Clone)]
pub struct Task {
    pub id: String,
    pub name: String,
    pub seconds_active: u64,
    pub started_at: Instant,
}

#[derive(Debug, Clone)]
pub struct TabBar {
    pub tabs: Vec<Tab>,
    pub active_tab_id: String,
}

#[derive(Debug, Clone)]
pub struct Tab {
    pub id: String,
    pub label: String,
}

#[derive(Debug, Clone)]
pub struct Results {
    pub rows: Vec<String>,
    pub scroll_offset: usize,
}

impl AppState {
    pub fn new(target: String) -> Self {
        Self {
            controls: Controls {
                target_text: target.clone(),
                elapsed: Duration::from_secs(0),
            },
            system: SystemStats {
                cpu_pct: 0.0,
                ram_gb: 0.0,
            },
            scan: ScanProgress {
                phase_label: "Initializing".to_string(),
                progress_pct: 0,
                tasks_done: 0,
                tasks_total: 0,
            },
            tasks: Vec::new(),
            tabs: TabBar {
                tabs: vec![
                    Tab { id: "overview".to_string(), label: "Overview".to_string() },
                    Tab { id: "ports".to_string(), label: "Ports".to_string() },
                    Tab { id: "services".to_string(), label: "Services".to_string() },
                    Tab { id: "logs".to_string(), label: "Logs".to_string() },
                ],
                active_tab_id: "overview".to_string(),
            },
            results: Results {
                rows: Vec::new(),
                scroll_offset: 0,
            },
            target,
            status: AppStatus::Running,
            start_time: Instant::now(),
        }
    }

    pub fn add_result(&mut self, result: String) {
        self.results.rows.push(result);
    }
}