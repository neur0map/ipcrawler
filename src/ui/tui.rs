use crate::config::Severity;
use crate::executor::runner::TaskUpdate;
use crate::output::parser::Finding;
use crossterm::{
    event::{self, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Cell, Paragraph, Row, Table},
    Frame, Terminal,
};
use std::collections::HashMap;
use std::io;
use std::time::{Duration, Instant};
use tokio::sync::mpsc::UnboundedReceiver;

pub struct TerminalUI {
    targets: Vec<String>,
    ports: Vec<u16>,
    start_time: Instant,
    tasks: HashMap<String, TaskInfo>,
    findings: Vec<Finding>,
    logs: Vec<LogEntry>,
    queued_count: usize,
    running_count: usize,
    completed_count: usize,
    scroll_offset: u16,
    logs_scroll_offset: u16,
    // Track tool-level progress
    tool_progress: HashMap<String, ToolProgress>,
}

#[derive(Clone)]
struct TaskInfo {
    tool_name: String,
    target: String,
    port: Option<u16>,
    status: String,
    duration: Option<Duration>,
}

#[derive(Clone, Default)]
struct ToolProgress {
    total_tasks: usize,
    completed_tasks: usize,
    running_tasks: usize,
    failed_tasks: usize,
    targets: Vec<String>,
}

#[derive(Clone)]
struct LogEntry {
    timestamp: Instant,
    tool_name: String,
    target: String,
    output_type: LogType,
    content: String,
}

#[derive(Clone)]
enum LogType {
    Stdout,
    Stderr,
    Error,
}

impl TerminalUI {
    pub fn new(targets: Vec<String>, ports: Vec<u16>) -> Self {
        Self {
            targets,
            ports,
            start_time: Instant::now(),
            tasks: HashMap::new(),
            findings: Vec::new(),
            logs: Vec::new(),
            queued_count: 0,
            running_count: 0,
            completed_count: 0,
            scroll_offset: 0,
            logs_scroll_offset: 0,
            tool_progress: HashMap::new(),
        }
    }

    pub async fn run(&mut self, mut update_rx: UnboundedReceiver<TaskUpdate>) -> io::Result<()> {
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen)?;

        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;

        terminal.clear()?;

        loop {
            terminal.draw(|f| self.draw(f))?;

            if event::poll(Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    match key.code {
                        KeyCode::Char('q') => break,
                        KeyCode::Up => {
                            if self.scroll_offset > 0 {
                                self.scroll_offset -= 1;
                            }
                        }
                        KeyCode::Down => {
                            self.scroll_offset += 1;
                        }
                        KeyCode::Left => {
                            if self.logs_scroll_offset > 0 {
                                self.logs_scroll_offset -= 1;
                            }
                        }
                        KeyCode::Right => {
                            self.logs_scroll_offset += 1;
                        }
                        KeyCode::Tab => {
                            // Toggle between findings and logs view
                            // This could be expanded to show different panels
                        }
                        _ => {}
                    }
                }
            }

            while let Ok(update) = update_rx.try_recv() {
                self.handle_update(update);
            }

            if self.running_count == 0 && self.queued_count == 0 && self.completed_count > 0 {
                tokio::time::sleep(Duration::from_secs(2)).await;
                break;
            }
        }

        disable_raw_mode()?;
        execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
        terminal.show_cursor()?;

        Ok(())
    }

    fn handle_update(&mut self, update: TaskUpdate) {
        match update {
            TaskUpdate::Started {
                task_id,
                tool_name,
                target,
                port,
            } => {
                // Update tool progress
                let progress = self.tool_progress.entry(tool_name.clone()).or_default();
                progress.total_tasks += 1;
                progress.running_tasks += 1;
                if !progress.targets.contains(&target) {
                    progress.targets.push(target.clone());
                }

                self.tasks.insert(
                    task_id.0.clone(),
                    TaskInfo {
                        tool_name: tool_name.clone(),
                        target,
                        port,
                        status: "Running".to_string(),
                        duration: None,
                    },
                );
            }
            TaskUpdate::Completed {
                task_id,
                stdout,
                stderr,
                ..
            } => {
                let task_info = if let Some(task) = self.tasks.get_mut(&task_id.0) {
                    // Update tool progress
                    let progress = self
                        .tool_progress
                        .entry(task.tool_name.clone())
                        .or_default();
                    progress.running_tasks = progress.running_tasks.saturating_sub(1);
                    progress.completed_tasks += 1;

                    task.status = "Completed".to_string();
                    Some(task.clone())
                } else {
                    None
                };

                // Add outputs to logs
                if let Some(task) = task_info {
                    if !stdout.is_empty() {
                        self.logs.push(LogEntry {
                            timestamp: Instant::now(),
                            tool_name: task.tool_name.clone(),
                            target: task.target.clone(),
                            output_type: LogType::Stdout,
                            content: stdout,
                        });
                    }

                    if !stderr.is_empty() {
                        self.logs.push(LogEntry {
                            timestamp: Instant::now(),
                            tool_name: task.tool_name.clone(),
                            target: task.target.clone(),
                            output_type: LogType::Stderr,
                            content: stderr,
                        });
                    }
                }
            }
            TaskUpdate::Failed {
                task_id,
                error,
                stdout,
                stderr,
            } => {
                let task_info = if let Some(task) = self.tasks.get_mut(&task_id.0) {
                    // Update tool progress
                    let progress = self
                        .tool_progress
                        .entry(task.tool_name.clone())
                        .or_default();
                    progress.running_tasks = progress.running_tasks.saturating_sub(1);
                    progress.failed_tasks += 1;

                    task.status = format!("Failed: {}", error);
                    Some(task.clone())
                } else {
                    None
                };

                // Add error and outputs to logs
                if let Some(task) = task_info {
                    self.logs.push(LogEntry {
                        timestamp: Instant::now(),
                        tool_name: task.tool_name.clone(),
                        target: task.target.clone(),
                        output_type: LogType::Error,
                        content: error,
                    });

                    if !stdout.is_empty() {
                        self.logs.push(LogEntry {
                            timestamp: Instant::now(),
                            tool_name: task.tool_name.clone(),
                            target: task.target.clone(),
                            output_type: LogType::Stdout,
                            content: stdout,
                        });
                    }

                    if !stderr.is_empty() {
                        self.logs.push(LogEntry {
                            timestamp: Instant::now(),
                            tool_name: task.tool_name.clone(),
                            target: task.target.clone(),
                            output_type: LogType::Stderr,
                            content: stderr,
                        });
                    }
                }
            }
            TaskUpdate::Progress {
                queued,
                running,
                completed,
            } => {
                self.queued_count = queued;
                self.running_count = running;
                self.completed_count = completed;
            }
        }
    }

    fn draw(&self, f: &mut Frame) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(5),
                Constraint::Min(8),
                Constraint::Min(8),
                Constraint::Min(8),
            ])
            .split(f.area());

        self.draw_header(f, chunks[0]);
        self.draw_task_table(f, chunks[1]);
        self.draw_findings(f, chunks[2]);
        self.draw_logs(f, chunks[3]);
    }

    fn draw_header(&self, f: &mut Frame, area: Rect) {
        let elapsed = self.start_time.elapsed();
        let elapsed_str = format!(
            "{:02}:{:02}:{:02}",
            elapsed.as_secs() / 3600,
            (elapsed.as_secs() % 3600) / 60,
            elapsed.as_secs() % 60
        );

        let total = self.queued_count + self.running_count + self.completed_count;

        let header_lines = vec![
            Line::from(vec![Span::styled(
                "IPCRAWLER - Automated Penetration Testing",
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD),
            )]),
            Line::from(vec![
                Span::raw("Targets: "),
                Span::styled(self.targets.join(", "), Style::default().fg(Color::Yellow)),
                Span::raw(" | Ports: "),
                Span::styled(
                    self.ports
                        .iter()
                        .map(|p| p.to_string())
                        .collect::<Vec<_>>()
                        .join(", "),
                    Style::default().fg(Color::Yellow),
                ),
            ]),
            Line::from(vec![
                Span::raw("Progress: "),
                Span::styled(
                    format!("{}/{} tasks completed", self.completed_count, total),
                    Style::default().fg(Color::Green),
                ),
                Span::raw(" | Elapsed: "),
                Span::styled(elapsed_str, Style::default().fg(Color::Magenta)),
            ]),
        ];

        let header = Paragraph::new(header_lines)
            .block(Block::default().borders(Borders::ALL).title("Scan Info"));

        f.render_widget(header, area);
    }

    fn draw_task_table(&self, f: &mut Frame, area: Rect) {
        let header_cells = ["Status", "Tool", "Targets", "Progress", "Duration"]
            .iter()
            .map(|h| {
                Cell::from(*h).style(
                    Style::default()
                        .fg(Color::Yellow)
                        .add_modifier(Modifier::BOLD),
                )
            });

        let header = Row::new(header_cells).height(1).bottom_margin(1);

        // Group tasks by tool name
        let mut tool_list: Vec<_> = self.tool_progress.iter().collect();
        tool_list.sort_by(|a, b| a.0.cmp(b.0));

        let rows = tool_list.iter().map(|(tool_name, progress)| {
            // Determine overall status based on task counts
            let (status_icon, status_style) = if progress.running_tasks > 0 {
                (">", Style::default().fg(Color::Cyan))
            } else if progress.failed_tasks > 0 && progress.completed_tasks == 0 {
                ("X", Style::default().fg(Color::Red))
            } else if progress.completed_tasks > 0 {
                ("OK", Style::default().fg(Color::Green))
            } else {
                ("...", Style::default().fg(Color::Gray))
            };

            // Show targets as comma-separated list (truncated if too long)
            let targets_str = if progress.targets.len() > 2 {
                format!(
                    "{}, ... ({} total)",
                    progress.targets[0],
                    progress.targets.len()
                )
            } else {
                progress.targets.join(", ")
            };

            // Show progress as completed/total
            let progress_str = format!("{}/{}", progress.completed_tasks, progress.total_tasks);

            // Calculate average duration or show running indicator
            let duration_str = if progress.running_tasks > 0 {
                "Running".to_string()
            } else {
                "Completed".to_string()
            };

            let cells = vec![
                Cell::from(status_icon).style(status_style),
                Cell::from(tool_name.as_str()),
                Cell::from(targets_str),
                Cell::from(progress_str),
                Cell::from(duration_str),
            ];

            Row::new(cells).height(1)
        });

        let widths = [
            Constraint::Length(8),
            Constraint::Length(15),
            Constraint::Length(20),
            Constraint::Length(10),
            Constraint::Length(12),
        ];

        let table = Table::new(rows, widths).header(header).block(
            Block::default()
                .borders(Borders::ALL)
                .title("Tool Execution Status"),
        );

        f.render_widget(table, area);
    }

    fn draw_findings(&self, f: &mut Frame, area: Rect) {
        let visible_height = area.height.saturating_sub(2) as usize;

        let finding_lines: Vec<Line> = self
            .findings
            .iter()
            .rev()
            .skip(self.scroll_offset as usize)
            .take(visible_height)
            .map(|finding| {
                let severity_style = match finding.severity {
                    Severity::Critical => {
                        Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)
                    }
                    Severity::High => Style::default().fg(Color::LightRed),
                    Severity::Medium => Style::default().fg(Color::Yellow),
                    Severity::Low => Style::default().fg(Color::Blue),
                    Severity::Info => Style::default().fg(Color::Gray),
                };

                let port_str = finding.port.map_or(String::new(), |p| format!(":{ }", p));

                Line::from(vec![
                    Span::styled(format!("[{}] ", finding.severity.as_str()), severity_style),
                    Span::raw(format!(
                        "{} on {}{} ({})",
                        finding.title, finding.target, port_str, finding.tool
                    )),
                ])
            })
            .collect();

        let findings_para = Paragraph::new(finding_lines).block(
            Block::default()
                .borders(Borders::ALL)
                .title("Live Findings (↑↓ to scroll, q to quit)"),
        );

        f.render_widget(findings_para, area);
    }

    fn draw_logs(&self, f: &mut Frame, area: Rect) {
        let visible_height = area.height.saturating_sub(2) as usize;

        let log_lines: Vec<Line> = self
            .logs
            .iter()
            .rev()
            .skip(self.logs_scroll_offset as usize)
            .take(visible_height)
            .map(|log| {
                let (type_str, style) = match log.output_type {
                    LogType::Stdout => ("STDOUT", Style::default().fg(Color::Green)),
                    LogType::Stderr => ("STDERR", Style::default().fg(Color::Yellow)),
                    LogType::Error => (
                        "ERROR",
                        Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
                    ),
                };

                let elapsed = log.timestamp.duration_since(self.start_time);
                let timestamp = format!(
                    "[{:02}:{:02}:{:02}] ",
                    elapsed.as_secs() / 3600,
                    (elapsed.as_secs() % 3600) / 60,
                    elapsed.as_secs() % 60
                );

                // Truncate long output lines for display
                let content = if log.content.len() > 100 {
                    format!("{}...", &log.content[..97])
                } else {
                    log.content.clone()
                };

                Line::from(vec![
                    Span::styled(timestamp, Style::default().fg(Color::Gray)),
                    Span::styled(format!("[{}] ", type_str), style),
                    Span::styled(
                        format!("{}@{}: ", log.tool_name, log.target),
                        Style::default().fg(Color::Cyan),
                    ),
                    Span::raw(content),
                ])
            })
            .collect();

        let logs_para = Paragraph::new(log_lines).block(
            Block::default()
                .borders(Borders::ALL)
                .title("Tool Output Logs (←→ to scroll, q to quit)"),
        );

        f.render_widget(logs_para, area);
    }

    fn status_order(status: &str) -> u8 {
        if status.contains("Running") {
            0
        } else if status.contains("Queued") {
            1
        } else if status.contains("Completed") {
            2
        } else {
            3
        }
    }
}
