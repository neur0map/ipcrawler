use std::io::{self, Write};
use crossterm::{
    cursor::MoveTo,
    execute, queue,
    style::{Color, Print, SetBackgroundColor, SetForegroundColor, ResetColor, Attribute, SetAttribute},
    terminal::{Clear, ClearType},
};

use crate::dashboard::{
    app_state::{AppState, AppStatus, LogLevel},
    layout::{Layout, Rect},
    widgets::{draw_box, draw_progress_bar, truncate_string},
};

pub struct Renderer {
    stdout: io::Stdout,
}

impl Renderer {
    pub fn new() -> Self {
        Self {
            stdout: io::stdout(),
        }
    }

    pub fn clear_screen(&mut self) -> io::Result<()> {
        execute!(self.stdout, Clear(ClearType::All))
    }

    pub fn render_size_warning(&mut self, cols: u16, rows: u16) -> io::Result<()> {
        let msg = format!("Terminal too small: {}x{} (need ≥70x20)", cols, rows);
        let x = cols.saturating_sub(msg.len() as u16) / 2;
        let y = rows / 2;
        
        queue!(
            self.stdout,
            Clear(ClearType::All),
            MoveTo(x, y),
            SetForegroundColor(Color::Yellow),
            Print(msg),
            ResetColor
        )?;
        self.stdout.flush()
    }

    pub fn render_frame(&mut self, state: &AppState, layout: &Layout) -> io::Result<()> {
        // Render each panel
        if let Some(rect) = layout.panels.get("control_bar") {
            self.render_control_bar(state, rect)?;
        }
        
        if let Some(rect) = layout.panels.get("system_monitor") {
            self.render_system_monitor(state, rect)?;
        }
        
        if let Some(rect) = layout.panels.get("scan_progress") {
            self.render_scan_progress(state, rect)?;
        }
        
        if let Some(rect) = layout.panels.get("active_tasks") {
            self.render_active_tasks(state, rect)?;
        }
        
        if let Some(rect) = layout.panels.get("tab_bar") {
            self.render_tab_bar(state, rect)?;
        }
        
        if let Some(rect) = layout.panels.get("results_view") {
            self.render_results_view(state, rect)?;
        }
        
        if let Some(rect) = layout.panels.get("logs_view") {
            self.render_logs_view(state, rect)?;
        }
        
        Ok(())
    }

    fn render_control_bar(&mut self, state: &AppState, rect: &Rect) -> io::Result<()> {
        draw_box(&mut self.stdout, rect, "IPCrawler")?;
        let inner = rect.inner(1);
        
        // Target and controls
        let target_str = truncate_string(&format!("Target: {}", state.controls.target_text), inner.width as usize - 20);
        queue!(
            self.stdout,
            MoveTo(inner.x, inner.y),
            SetForegroundColor(Color::Cyan),
            Print(&target_str),
            ResetColor
        )?;
        
        // Control buttons (visual only)
        let controls = " [Q]uit | [←→] Switch Tabs | [↑↓] Scroll ";
        
        queue!(
            self.stdout,
            MoveTo(inner.x + inner.width - controls.len() as u16, inner.y),
            SetForegroundColor(Color::Green),
            Print(controls),
            ResetColor
        )
    }

    fn render_system_monitor(&mut self, state: &AppState, rect: &Rect) -> io::Result<()> {
        draw_box(&mut self.stdout, rect, "System")?;
        let inner = rect.inner(1);
        
        // Format elapsed time
        let elapsed = state.controls.elapsed;
        let elapsed_str = format!("{:02}:{:02}:{:02}",
            elapsed.as_secs() / 3600,
            (elapsed.as_secs() % 3600) / 60,
            elapsed.as_secs() % 60
        );
        
        // CPU meter
        let cpu_width = 10;
        let cpu_filled = ((state.system.cpu_pct / 100.0) * cpu_width as f32) as usize;
        let cpu_meter: String = "█".repeat(cpu_filled) + &"░".repeat(cpu_width - cpu_filled);
        
        // Status indicator
        let status_str = match state.status {
            AppStatus::Completed => " [DONE]",
            _ => "",
        };
        
        let monitor_str = format!(
            "CPU: {} {:.1}% | RAM: {:.1}GB | Time: {}{}",
            cpu_meter, state.system.cpu_pct, state.system.ram_gb, elapsed_str, status_str
        );
        
        queue!(
            self.stdout,
            MoveTo(inner.x, inner.y),
            Print(truncate_string(&monitor_str, inner.width as usize))
        )
    }

    fn render_scan_progress(&mut self, state: &AppState, rect: &Rect) -> io::Result<()> {
        draw_box(&mut self.stdout, rect, "Scan Progress")?;
        let inner = rect.inner(1);
        
        // Phase label
        queue!(
            self.stdout,
            MoveTo(inner.x, inner.y),
            SetForegroundColor(Color::Yellow),
            Print(truncate_string(&state.scan.phase_label, inner.width as usize)),
            ResetColor
        )?;
        
        // Progress bar
        if inner.height > 2 {
            draw_progress_bar(
                &mut self.stdout,
                inner.x,
                inner.y + 2,
                inner.width.min(40),
                state.scan.progress_pct,
            )?;
        }
        
        // Task count
        if inner.height > 3 {
            let task_str = format!("{}/{} tasks", state.scan.tasks_done, state.scan.tasks_total);
            queue!(
                self.stdout,
                MoveTo(inner.x, inner.y + 4),
                Print(task_str)
            )?;
        }
        
        Ok(())
    }

    fn render_active_tasks(&mut self, state: &AppState, rect: &Rect) -> io::Result<()> {
        draw_box(&mut self.stdout, rect, "Active Tasks")?;
        let inner = rect.inner(1);
        
        if state.tasks.is_empty() {
            queue!(
                self.stdout,
                MoveTo(inner.x, inner.y),
                SetForegroundColor(Color::DarkGrey),
                Print("No active tasks"),
                ResetColor
            )?;
        } else {
            let max_tasks = inner.height as usize;
            for (i, task) in state.tasks.iter().take(max_tasks).enumerate() {
                queue!(
                    self.stdout,
                    MoveTo(inner.x, inner.y + i as u16),
                    SetForegroundColor(Color::Green),
                    Print("• "),
                    ResetColor,
                    Print(truncate_string(&format!("{} [{}s]", task.name, task.seconds_active), inner.width as usize - 2))
                )?;
            }
        }
        
        Ok(())
    }

    fn render_tab_bar(&mut self, state: &AppState, rect: &Rect) -> io::Result<()> {
        draw_box(&mut self.stdout, rect, "Tabs (←→ to switch)")?;
        let inner = rect.inner(1);
        
        let mut x_offset = inner.x;
        for (i, tab) in state.tabs.tabs.iter().enumerate() {
            let is_active = tab.id == state.tabs.active_tab_id;
            let tab_str = if is_active {
                format!("[{}]", tab.label)
            } else {
                format!(" {} ", tab.label)
            };
            
            if is_active {
                queue!(
                    self.stdout,
                    MoveTo(x_offset, inner.y),
                    SetBackgroundColor(Color::Blue),
                    SetForegroundColor(Color::White),
                    SetAttribute(Attribute::Bold),
                    Print(&tab_str),
                    ResetColor,
                    SetAttribute(Attribute::Reset)
                )?;
            } else {
                queue!(
                    self.stdout,
                    MoveTo(x_offset, inner.y),
                    SetForegroundColor(Color::DarkGrey),
                    Print(&tab_str),
                    ResetColor
                )?;
            }
            
            x_offset += tab_str.len() as u16 + 2;
            
            // Add separator between tabs (except last)
            if i < state.tabs.tabs.len() - 1 {
                queue!(
                    self.stdout,
                    MoveTo(x_offset - 1, inner.y),
                    SetForegroundColor(Color::DarkGrey),
                    Print("|"),
                    ResetColor
                )?;
            }
        }
        
        Ok(())
    }

    fn render_results_view(&mut self, state: &AppState, rect: &Rect) -> io::Result<()> {
        draw_box(&mut self.stdout, rect, "Results")?;
        let inner = rect.inner(1);
        
        if state.results.rows.is_empty() {
            queue!(
                self.stdout,
                MoveTo(inner.x, inner.y),
                SetForegroundColor(Color::DarkGrey),
                Print("No results yet..."),
                ResetColor
            )?;
        } else {
            let visible_rows = inner.height as usize;
            let start_idx = state.results.scroll_offset;
            let end_idx = (start_idx + visible_rows).min(state.results.rows.len());
            
            for (i, row_idx) in (start_idx..end_idx).enumerate() {
                if let Some(row) = state.results.rows.get(row_idx) {
                    // Account for box border margins
                    let available_width = if inner.width > 0 { inner.width as usize } else { 0 };
                    let row_str = truncate_string(row, available_width);
                    
                    // Color based on content
                    let color = if row.contains("✓") {
                        Color::Green
                    } else if row.contains("✗") {
                        Color::Red
                    } else if row.contains("OPEN") {
                        Color::Cyan
                    } else {
                        Color::White
                    };
                    
                    // Clear only this panel's area to prevent overflow into other panels
                    let clear_width = inner.width as usize;
                    queue!(
                        self.stdout,
                        MoveTo(inner.x, inner.y + i as u16),
                        Print(" ".repeat(clear_width))
                    )?;
                    
                    queue!(
                        self.stdout,
                        MoveTo(inner.x, inner.y + i as u16),
                        SetForegroundColor(color),
                        Print(row_str),
                        ResetColor
                    )?;
                }
            }
            
            // Scroll indicator
            if state.results.rows.len() > visible_rows {
                let scroll_pct = if state.results.rows.len() > 1 {
                    (state.results.scroll_offset as f32 / (state.results.rows.len() - 1) as f32 * 100.0) as u16
                } else {
                    0
                };
                
                queue!(
                    self.stdout,
                    MoveTo(inner.x + inner.width - 10, inner.y + inner.height - 1),
                    SetForegroundColor(Color::DarkGrey),
                    Print(format!("[{:3}%]", scroll_pct)),
                    ResetColor
                )?;
            }
        }
        
        Ok(())
    }

    fn render_logs_view(&mut self, state: &AppState, rect: &Rect) -> io::Result<()> {
        draw_box(&mut self.stdout, rect, "Live Logs")?;
        let inner = rect.inner(1);
        
        if state.logs.entries.is_empty() {
            queue!(
                self.stdout,
                MoveTo(inner.x, inner.y),
                SetForegroundColor(Color::DarkGrey),
                Print("No logs yet..."),
                ResetColor
            )?;
        } else {
            let visible_rows = inner.height as usize;
            let start_idx = state.logs.scroll_offset;
            let end_idx = (start_idx + visible_rows).min(state.logs.entries.len());
            
            for (i, entry_idx) in (start_idx..end_idx).enumerate() {
                if let Some(entry) = state.logs.entries.get(entry_idx) {
                    // Color based on log level
                    let level_color = match entry.level {
                        LogLevel::Debug => Color::DarkGrey,
                        LogLevel::Info => Color::White,
                        LogLevel::Warn => Color::Yellow,
                        LogLevel::Error => Color::Red,
                    };
                    
                    let level_str = match entry.level {
                        LogLevel::Debug => "DBG",
                        LogLevel::Info => "INF", 
                        LogLevel::Warn => "WRN",
                        LogLevel::Error => "ERR",
                    };
                    
                    // Calculate proper message width: timestamp (8) + space (1) + level (3) + space (1) = 13 chars
                    let prefix_width = 13;
                    let message_width = if inner.width as usize > prefix_width {
                        inner.width as usize - prefix_width
                    } else {
                        0
                    };
                    let truncated_message = truncate_string(&entry.message, message_width);
                    
                    // Clear only this panel's area to prevent overflow into other panels
                    let clear_width = inner.width as usize;
                    queue!(
                        self.stdout,
                        MoveTo(inner.x, inner.y + i as u16),
                        Print(" ".repeat(clear_width))
                    )?;
                    
                    queue!(
                        self.stdout,
                        MoveTo(inner.x, inner.y + i as u16),
                        SetForegroundColor(Color::DarkGrey),
                        Print(&entry.timestamp),
                        Print(" "),
                        SetForegroundColor(level_color),
                        Print(level_str),
                        Print(" "),
                        SetForegroundColor(Color::White),
                        Print(&truncated_message),
                        ResetColor
                    )?;
                }
            }
            
            // Scroll indicator
            if state.logs.entries.len() > visible_rows {
                let scroll_pct = if state.logs.entries.len() > 1 {
                    (state.logs.scroll_offset as f32 / (state.logs.entries.len() - 1) as f32 * 100.0) as u16
                } else {
                    0
                };
                
                queue!(
                    self.stdout,
                    MoveTo(inner.x + inner.width - 10, inner.y + inner.height - 1),
                    SetForegroundColor(Color::DarkGrey),
                    Print(format!("[{:3}%]", scroll_pct)),
                    ResetColor
                )?;
            }
        }
        
        Ok(())
    }

    pub fn flush(&mut self) -> io::Result<()> {
        self.stdout.flush()
    }
}