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
    pub summary: Summary,
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
pub struct Summary {
    pub content: Vec<String>,
    pub scroll_offset: usize,
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
                        id: "summary".to_string(),
                        label: "Summary".to_string(),
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
            summary: Summary {
                content: Vec::new(),
                scroll_offset: 0,
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

    pub fn load_summary(&mut self, markdown_path: &std::path::Path) {
        use std::fs;
        if let Ok(content) = fs::read_to_string(markdown_path) {
            self.summary.content = self.parse_markdown(content);
            self.summary.scroll_offset = 0;
        }
    }

    fn parse_markdown(&self, markdown: String) -> Vec<String> {
        let mut rendered_lines = Vec::new();

        for line in markdown.lines() {
            let trimmed = line.trim();

            if let Some(stripped) = trimmed.strip_prefix("# ") {
                // H1 headers - cyan and bold
                rendered_lines.push(format!("\x1b[1;36m{}\x1b[0m", stripped));
                rendered_lines.push("".to_string()); // Add spacing
            } else if let Some(stripped) = trimmed.strip_prefix("## ") {
                // H2 headers - green and bold
                rendered_lines.push(format!("\x1b[1;32m{}\x1b[0m", stripped));
                rendered_lines.push("".to_string());
            } else if let Some(stripped) = trimmed.strip_prefix("### ") {
                // H3 headers - yellow
                rendered_lines.push(format!("\x1b[1;33m{}\x1b[0m", stripped));
            } else if trimmed.starts_with("- ") || trimmed.starts_with("* ") {
                // Bullet points - green bullet
                rendered_lines.push(format!("\x1b[32m●\x1b[0m {}", &trimmed[2..]));
            } else if let Some(stripped) = trimmed.strip_prefix("```") {
                // Code blocks - gray background
                if stripped.is_empty() {
                    rendered_lines.push("\x1b[100m \x1b[0m".to_string());
                } else {
                    rendered_lines.push(format!("\x1b[100m {} \x1b[0m", stripped));
                }
            } else if trimmed.starts_with("`") && trimmed.ends_with("`") && trimmed.len() > 2 {
                // Inline code - gray background
                let code = &trimmed[1..trimmed.len() - 1];
                rendered_lines.push(format!("\x1b[100m{}\x1b[0m", code));
            } else if trimmed.starts_with("**") && trimmed.ends_with("**") && trimmed.len() > 4 {
                // Bold text
                let bold_text = &trimmed[2..trimmed.len() - 2];
                rendered_lines.push(format!("\x1b[1m{}\x1b[0m", bold_text));
            } else if !trimmed.is_empty() {
                // Regular text
                rendered_lines.push(trimmed.to_string());
            } else {
                // Empty lines
                rendered_lines.push("".to_string());
            }
        }

        rendered_lines
    }
}
