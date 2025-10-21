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
    queued_count: usize,
    running_count: usize,
    completed_count: usize,
    scroll_offset: u16,
}

#[derive(Clone)]
struct TaskInfo {
    tool_name: String,
    target: String,
    port: Option<u16>,
    status: String,
    duration: Option<Duration>,
}

impl TerminalUI {
    pub fn new(targets: Vec<String>, ports: Vec<u16>) -> Self {
        Self {
            targets,
            ports,
            start_time: Instant::now(),
            tasks: HashMap::new(),
            findings: Vec::new(),
            queued_count: 0,
            running_count: 0,
            completed_count: 0,
            scroll_offset: 0,
        }
    }

    pub async fn run(
        &mut self,
        mut update_rx: UnboundedReceiver<TaskUpdate>,
    ) -> io::Result<()> {
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
            TaskUpdate::Started { task_id, tool_name, target, port } => {
                self.tasks.insert(
                    task_id.0.clone(),
                    TaskInfo {
                        tool_name,
                        target,
                        port,
                        status: "Running".to_string(),
                        duration: None,
                    },
                );
            }
            TaskUpdate::Completed { task_id, .. } => {
                if let Some(task) = self.tasks.get_mut(&task_id.0) {
                    task.status = "Completed".to_string();
                }
            }
            TaskUpdate::Failed { task_id, error } => {
                if let Some(task) = self.tasks.get_mut(&task_id.0) {
                    task.status = format!("Failed: {}", error);
                }
            }
            TaskUpdate::Progress { queued, running, completed } => {
                self.queued_count = queued;
                self.running_count = running;
                self.completed_count = completed;
            }
        }
    }

    #[allow(dead_code)]
    pub fn add_finding(&mut self, finding: Finding) {
        self.findings.push(finding);
    }

    #[allow(dead_code)]
    pub fn add_findings(&mut self, findings: Vec<Finding>) {
        self.findings.extend(findings);
    }

    fn draw(&self, f: &mut Frame) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(5),
                Constraint::Min(10),
                Constraint::Min(8),
            ])
            .split(f.area());

        self.draw_header(f, chunks[0]);
        self.draw_task_table(f, chunks[1]);
        self.draw_findings(f, chunks[2]);
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
            Line::from(vec![
                Span::styled(
                    "IPCRAWLER - Automated Penetration Testing",
                    Style::default()
                        .fg(Color::Cyan)
                        .add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(vec![
                Span::raw("Targets: "),
                Span::styled(
                    self.targets.join(", "),
                    Style::default().fg(Color::Yellow),
                ),
                Span::raw(" | Ports: "),
                Span::styled(
                    self.ports.iter().map(|p| p.to_string()).collect::<Vec<_>>().join(", "),
                    Style::default().fg(Color::Yellow),
                ),
            ]),
            Line::from(vec![
                Span::raw("Progress: "),
                Span::styled(
                    format!("{}/{} tools completed", self.completed_count, total),
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
        let header_cells = ["Status", "Tool", "Target", "Port", "Duration"]
            .iter()
            .map(|h| Cell::from(*h).style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)));

        let header = Row::new(header_cells).height(1).bottom_margin(1);

        let mut task_list: Vec<_> = self.tasks.values().collect();
        task_list.sort_by(|a, b| {
            let a_order = Self::status_order(&a.status);
            let b_order = Self::status_order(&b.status);
            a_order.cmp(&b_order)
        });

        let rows = task_list.iter().map(|task| {
            let status_icon = if task.status.contains("Completed") {
                "✓"
            } else if task.status.contains("Running") {
                "►"
            } else if task.status.contains("Failed") {
                "✗"
            } else {
                "⋯"
            };

            let status_style = if task.status.contains("Completed") {
                Style::default().fg(Color::Green)
            } else if task.status.contains("Running") {
                Style::default().fg(Color::Cyan)
            } else if task.status.contains("Failed") {
                Style::default().fg(Color::Red)
            } else {
                Style::default().fg(Color::Gray)
            };

            let port_str = task.port.map_or("-".to_string(), |p| p.to_string());
            let duration_str = task.duration
                .map_or("-".to_string(), |d| format!("{:.1}s", d.as_secs_f64()));

            let cells = vec![
                Cell::from(status_icon).style(status_style),
                Cell::from(task.tool_name.clone()),
                Cell::from(task.target.clone()),
                Cell::from(port_str),
                Cell::from(duration_str),
            ];

            Row::new(cells).height(1)
        });

        let widths = [
            Constraint::Length(8),
            Constraint::Length(12),
            Constraint::Length(15),
            Constraint::Length(6),
            Constraint::Length(10),
        ];

        let table = Table::new(rows, widths)
            .header(header)
            .block(Block::default().borders(Borders::ALL).title("Tool Execution Status"));

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
                    Severity::Critical => Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
                    Severity::High => Style::default().fg(Color::LightRed),
                    Severity::Medium => Style::default().fg(Color::Yellow),
                    Severity::Low => Style::default().fg(Color::Blue),
                    Severity::Info => Style::default().fg(Color::Gray),
                };

                let port_str = finding.port.map_or(String::new(), |p| format!(":{ }", p));

                Line::from(vec![
                    Span::styled(
                        format!("[{}] ", finding.severity.as_str()),
                        severity_style,
                    ),
                    Span::raw(format!(
                        "{} on {}{} ({})",
                        finding.title, finding.target, port_str, finding.tool
                    )),
                ])
            })
            .collect();

        let findings_para = Paragraph::new(finding_lines)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title("Live Findings (↑↓ to scroll, q to quit)"),
            );

        f.render_widget(findings_para, area);
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
