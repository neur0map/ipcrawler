use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct LayoutSpec {
    pub control_bar_height: u16,
    pub system_monitor_height: u16,
    pub status_row_height: u16,
    pub tab_bar_height: u16,
}

impl Default for LayoutSpec {
    fn default() -> Self {
        Self {
            control_bar_height: 3,
            system_monitor_height: 3,
            status_row_height: 8,
            tab_bar_height: 3,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Layout {
    pub panels: HashMap<String, Rect>,
}

#[derive(Debug, Clone, Copy)]
pub struct Rect {
    pub x: u16,
    pub y: u16,
    pub width: u16,
    pub height: u16,
}

impl Rect {
    pub fn new(x: u16, y: u16, width: u16, height: u16) -> Self {
        Self { x, y, width, height }
    }

    pub fn inner(&self, margin: u16) -> Self {
        Self {
            x: self.x + margin,
            y: self.y + margin,
            width: self.width.saturating_sub(margin * 2),
            height: self.height.saturating_sub(margin * 2),
        }
    }
}

pub fn compute_layout(spec: &LayoutSpec, cols: u16, rows: u16) -> Layout {
    let mut panels = HashMap::new();
    let mut current_y = 0;

    // Control bar
    panels.insert(
        "control_bar".to_string(),
        Rect::new(0, current_y, cols, spec.control_bar_height),
    );
    current_y += spec.control_bar_height;

    // System monitor
    panels.insert(
        "system_monitor".to_string(),
        Rect::new(0, current_y, cols, spec.system_monitor_height),
    );
    current_y += spec.system_monitor_height;

    // Status row (scan progress + active tasks)
    let status_width = cols / 2;
    panels.insert(
        "scan_progress".to_string(),
        Rect::new(0, current_y, status_width, spec.status_row_height),
    );
    panels.insert(
        "active_tasks".to_string(),
        Rect::new(status_width, current_y, cols - status_width, spec.status_row_height),
    );
    current_y += spec.status_row_height;

    // Tab bar
    panels.insert(
        "tab_bar".to_string(),
        Rect::new(0, current_y, cols, spec.tab_bar_height),
    );
    current_y += spec.tab_bar_height;

    // Results view - split into two panels (remaining space)
    let results_height = rows.saturating_sub(current_y);
    let results_width = cols / 2;
    let logs_width = cols - results_width; // Ensure no overlap
    
    // Left panel: Results
    panels.insert(
        "results_view".to_string(),
        Rect::new(0, current_y, results_width, results_height),
    );
    
    // Right panel: Live Logs  
    panels.insert(
        "logs_view".to_string(),
        Rect::new(results_width, current_y, logs_width, results_height),
    );

    Layout {
        panels,
    }
}