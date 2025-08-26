use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq)]
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
    pub logs: Logs,
    pub target: String,
    pub status: AppStatus,
    pub start_time: Instant,
    pub animation_frame: usize,
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

#[derive(Debug, Clone)]
pub struct Logs {
    pub entries: Vec<LogEntry>,
    pub scroll_offset: usize,
    pub max_entries: usize,
}

#[derive(Debug, Clone)]
pub struct LogEntry {
    pub timestamp: String,
    pub level: LogLevel,
    pub message: String,
}

#[derive(Debug, Clone)]
pub enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
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
                    Tab {
                        id: "overview".to_string(),
                        label: "Overview".to_string(),
                    },
                    Tab {
                        id: "ports".to_string(),
                        label: "Ports".to_string(),
                    },
                    Tab {
                        id: "services".to_string(),
                        label: "Services".to_string(),
                    },
                    Tab {
                        id: "logs".to_string(),
                        label: "Logs".to_string(),
                    },
                    Tab {
                        id: "help".to_string(),
                        label: "Help".to_string(),
                    },
                ],
                active_tab_id: "overview".to_string(),
            },
            results: Results {
                rows: Vec::new(),
                scroll_offset: 0,
            },
            logs: Logs {
                entries: Vec::new(),
                scroll_offset: 0,
                max_entries: 1000, // Keep last 1000 log entries
            },
            target,
            status: AppStatus::Running,
            start_time: Instant::now(),
            animation_frame: 0,
        }
    }

    pub fn add_result(&mut self, result: String) {
        self.results.rows.push(result);
    }

    pub fn add_log(&mut self, level: LogLevel, message: String) {
        let timestamp = chrono::Local::now().format("%H:%M:%S").to_string();
        let entry = LogEntry {
            timestamp,
            level,
            message,
        };

        self.logs.entries.push(entry);

        // Keep only the last max_entries
        if self.logs.entries.len() > self.logs.max_entries {
            self.logs.entries.remove(0);
        }

        // Auto-scroll to bottom when new entries arrive
        let visible_entries = 20; // Approximate visible entries
        if self.logs.entries.len() > visible_entries {
            self.logs.scroll_offset = self.logs.entries.len() - visible_entries;
        }
    }
}
