use std::collections::{HashMap, VecDeque};
use std::time::{Duration, Instant};
use std::io;
use tokio::sync::mpsc;
use crate::ui::events::{UiEvent, TaskResult, ActiveTask};
use ratatui::{
    prelude::*,
    widgets::{Block, Borders, Gauge, List, ListItem, Paragraph},
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
};
use crossterm::{
    event::{DisableMouseCapture, EnableMouseCapture, Event as CrossEvent, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
    tty::IsTty,
};


const MAX_VISIBLE_TASKS: usize = 8;
const MAX_RESULT_LINES: usize = 10;
const UI_REFRESH_MS: u64 = 125; // 8 Hz for smooth updates

/// UI data snapshot to avoid borrowing issues during rendering
#[derive(Clone)]
struct UiData {
    active_tasks: Vec<ActiveTask>,
    waiting_tasks: Vec<ActiveTask>,
    completed_tasks: Vec<(String, TaskResult, Instant)>,
    total_tasks: usize,
    completed_count: usize,
    current_phase: String,
    target: String,
    last_cpu: f32,
    last_memory: f64,
    start_time: Instant,
    port_discoveries: Vec<(u16, String, Instant)>,
    log_messages: Vec<(String, Instant)>,
    port_scanners: Vec<String>,
    service_scanners: Vec<String>,
}

impl UiData {
    fn from_manager(manager: &ProgressManager) -> Self {
        Self {
            active_tasks: manager.active_tasks.values().cloned().collect(),
            waiting_tasks: manager.waiting_tasks.iter().cloned().collect(),
            completed_tasks: manager.completed_tasks.clone(),
            total_tasks: manager.total_tasks,
            completed_count: manager.completed_count,
            current_phase: manager.current_phase.clone(),
            target: manager.target.clone(),
            last_cpu: manager.last_cpu,
            last_memory: manager.last_memory,
            start_time: manager.start_time,
            port_discoveries: manager.port_discoveries.iter().cloned().collect(),
            log_messages: manager.log_messages.iter().cloned().collect(),
            port_scanners: manager.port_scanners.clone(),
            service_scanners: manager.service_scanners.clone(),
        }
    }
    
    /// Draw the header with target and system stats
    fn draw_header(&self, f: &mut Frame, area: Rect) {
        let elapsed = self.start_time.elapsed();
        let elapsed_str = format!("{}:{:02}:{:02}", 
            elapsed.as_secs() / 3600,
            (elapsed.as_secs() % 3600) / 60,
            elapsed.as_secs() % 60
        );
        
        let header_text = if !self.target.is_empty() {
            format!(
                "Target: {} │ Runtime: {} │ CPU: {:.1}% │ RAM: {:.1}GB",
                self.target, elapsed_str, self.last_cpu, self.last_memory
            )
        } else {
            format!("Initializing... │ Runtime: {} │ CPU: {:.1}% │ RAM: {:.1}GB",
                elapsed_str, self.last_cpu, self.last_memory
            )
        };
        
        let header = Paragraph::new(header_text)
            .style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
            .block(Block::default()
                .borders(Borders::ALL)
                .title("IPCrawler")
                .title_style(Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
            );
        
        f.render_widget(header, area);
    }
    
    /// Draw the main progress section
    fn draw_progress(&self, f: &mut Frame, area: Rect) {
        let progress_ratio = if self.total_tasks > 0 {
            self.completed_count as f64 / self.total_tasks as f64
        } else {
            0.0
        };
        
        let progress_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(1),
                Constraint::Length(1),
                Constraint::Length(1),
            ].as_ref())
            .split(area);
        
        // Phase information with plugin inventory
        let phase_info = if !self.port_scanners.is_empty() || !self.service_scanners.is_empty() {
            format!("{} │ Available: {} port scanners, {} service scanners", 
                self.current_phase,
                self.port_scanners.len(),
                self.service_scanners.len())
        } else {
            self.current_phase.clone()
        };
        let phase_text = Paragraph::new(phase_info)
            .style(Style::default().fg(Color::Yellow));
        f.render_widget(phase_text, progress_chunks[0]);
        
        // Progress bar
        let progress_bar = Gauge::default()
            .block(Block::default().borders(Borders::ALL).title("Overall Progress"))
            .gauge_style(Style::default().fg(Color::Green).bg(Color::DarkGray))
            .ratio(progress_ratio)
            .label(format!("{}/{} tasks ({:.1}%)", 
                self.completed_count, self.total_tasks, progress_ratio * 100.0));
        
        f.render_widget(progress_bar, progress_chunks[1]);
        
        // Queue status
        let queue_text = format!(
            "Active: {} │ Waiting: {} │ Completed: {}",
            self.active_tasks.len(),
            self.waiting_tasks.len(),
            self.completed_tasks.len()
        );
        let queue_info = Paragraph::new(queue_text)
            .style(Style::default().fg(Color::Blue));
        f.render_widget(queue_info, progress_chunks[2]);
    }
    
    /// Draw active tasks with real-time status
    fn draw_active_tasks(&self, f: &mut Frame, area: Rect) {
        let mut items = Vec::new();
        
        // Active tasks
        for task in &self.active_tasks {
            let duration = task.duration().as_secs_f32();
            let status_color = match task.status.as_str() {
                "initializing" => Color::Yellow,
                "scanning" => Color::Cyan,
                _ => Color::White,
            };
            
            let item_text = format!(
                "▶ {} ({:.1}s) - {}",
                task.name, duration, task.status
            );
            
            items.push(ListItem::new(Line::from(vec![
                Span::styled(item_text, Style::default().fg(status_color))
            ])));
        }
        
        // Waiting tasks (limited display)
        let waiting_display = self.waiting_tasks.len().min(3);
        for task in self.waiting_tasks.iter().take(waiting_display) {
            let duration = task.duration().as_secs_f32();
            let item_text = format!("⏸ {} ({:.1}s) - waiting", task.name, duration);
            
            items.push(ListItem::new(Line::from(vec![
                Span::styled(item_text, Style::default().fg(Color::DarkGray))
            ])));
        }
        
        if self.waiting_tasks.len() > waiting_display {
            let remaining = self.waiting_tasks.len() - waiting_display;
            items.push(ListItem::new(Line::from(vec![
                Span::styled(format!("... and {} more waiting", remaining), 
                    Style::default().fg(Color::DarkGray).add_modifier(Modifier::ITALIC))
            ])));
        }
        
        if items.is_empty() {
            items.push(ListItem::new(Line::from(vec![
                Span::styled("No active tasks", Style::default().fg(Color::DarkGray))
            ])));
        }
        
        let task_list = List::new(items)
            .block(Block::default()
                .borders(Borders::ALL)
                .title("Active Tasks")
                .title_style(Style::default().fg(Color::Green))
            );
        
        f.render_widget(task_list, area);
    }
    
    /// Draw results and log feed
    fn draw_results(&self, f: &mut Frame, area: Rect) {
        let results_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(50),
                Constraint::Percentage(50),
            ].as_ref())
            .split(area);
        
        // Port discoveries
        let mut port_items = Vec::new();
        for (port, service, timestamp) in &self.port_discoveries {
            let age = timestamp.elapsed().as_secs();
            let age_str = if age < 60 { format!("{}s", age) } else { format!("{}m", age / 60) };
            
            port_items.push(ListItem::new(Line::from(vec![
                Span::styled(format!("{}:", port), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                Span::raw(" "),
                Span::styled(service.clone(), Style::default().fg(Color::White)),
                Span::raw(" "),
                Span::styled(format!("({})", age_str), Style::default().fg(Color::DarkGray)),
            ])));
        }
        
        if port_items.is_empty() {
            port_items.push(ListItem::new(Line::from(vec![
                Span::styled("No ports discovered yet", Style::default().fg(Color::DarkGray))
            ])));
        }
        
        let port_list = List::new(port_items)
            .block(Block::default()
                .borders(Borders::ALL)
                .title("Port Discoveries")
                .title_style(Style::default().fg(Color::Green))
            );
        
        f.render_widget(port_list, results_chunks[0]);
        
        // Recent logs
        let mut log_items = Vec::new();
        for (message, timestamp) in &self.log_messages {
            let age = timestamp.elapsed().as_secs();
            let age_str = if age < 60 { format!("{}s", age) } else { format!("{}m", age / 60) };
            
            let color = if message.starts_with("✓") {
                Color::Green
            } else if message.starts_with("✗") {
                Color::Red
            } else if message.starts_with("Phase") {
                Color::Yellow
            } else {
                Color::White
            };
            
            log_items.push(ListItem::new(Line::from(vec![
                Span::styled(format!("[{}] ", age_str), Style::default().fg(Color::DarkGray)),
                Span::styled(message.clone(), Style::default().fg(color)),
            ])));
        }
        
        if log_items.is_empty() {
            log_items.push(ListItem::new(Line::from(vec![
                Span::styled("No activity yet", Style::default().fg(Color::DarkGray))
            ])));
        }
        
        let log_list = List::new(log_items)
            .block(Block::default()
                .borders(Borders::ALL)
                .title("Activity Log")
                .title_style(Style::default().fg(Color::Green))
            );
        
        f.render_widget(log_list, results_chunks[1]);
    }
}

/// Modern ratatui-based progress manager with multi-panel display
pub struct ProgressManager {
    // Terminal and display
    terminal: Terminal<CrosstermBackend<io::Stdout>>,
    
    // Active task management
    active_tasks: HashMap<String, ActiveTask>,
    waiting_tasks: VecDeque<ActiveTask>,
    completed_tasks: Vec<(String, TaskResult, Instant)>,
    
    // Progress tracking
    total_tasks: usize,
    completed_count: usize,
    current_phase: String,
    
    // Event receiver
    event_rx: mpsc::UnboundedReceiver<UiEvent>,
    
    // Target and system info
    target: String,
    last_cpu: f32,
    last_memory: f64,
    start_time: Instant,
    
    // Results feed
    port_discoveries: VecDeque<(u16, String, Instant)>,
    log_messages: VecDeque<(String, Instant)>,
    
    // Plugin inventory
    port_scanners: Vec<String>,
    service_scanners: Vec<String>,
}

impl ProgressManager {
    /// Create new progress manager with terminal setup
    pub fn new() -> Result<(Self, mpsc::UnboundedSender<UiEvent>), io::Error> {
        let (event_tx, event_rx) = mpsc::unbounded_channel();
        
        // More robust TTY and terminal capability checking
        if !io::stdout().is_tty() {
            return Err(io::Error::new(
                io::ErrorKind::Unsupported,
                "Terminal UI requires a TTY (interactive terminal)"
            ));
        }
        
        // Check if terminal supports required features
        let term = std::env::var("TERM").unwrap_or_default();
        if term.is_empty() || term == "dumb" {
            return Err(io::Error::new(
                io::ErrorKind::Unsupported,
                "Terminal type not supported for UI"
            ));
        }
        
        // Setup terminal with comprehensive error handling
        enable_raw_mode().map_err(|e| {
            io::Error::new(io::ErrorKind::Other, format!("Failed to enable raw mode: {}", e))
        })?;
        
        let mut stdout = io::stdout();
        
        // Try to enter alternate screen with better error handling
        execute!(stdout, EnterAlternateScreen, EnableMouseCapture).map_err(|e| {
            let _ = disable_raw_mode();
            io::Error::new(io::ErrorKind::Other, format!("Failed to setup terminal: {}", e))
        })?;
        
        let backend = CrosstermBackend::new(stdout);
        let terminal = Terminal::new(backend).map_err(|e| {
            let _ = disable_raw_mode();
            let _ = execute!(io::stdout(), LeaveAlternateScreen, DisableMouseCapture);
            io::Error::new(io::ErrorKind::Other, format!("Failed to create terminal: {}", e))
        })?;
        
        let manager = Self {
            terminal,
            active_tasks: HashMap::new(),
            waiting_tasks: VecDeque::new(),
            completed_tasks: Vec::new(),
            total_tasks: 0,
            completed_count: 0,
            current_phase: "Initializing...".to_string(),
            event_rx,
            target: String::new(),
            last_cpu: 0.0,
            last_memory: 0.0,
            start_time: Instant::now(),
            port_discoveries: VecDeque::new(),
            log_messages: VecDeque::new(),
            port_scanners: Vec::new(),
            service_scanners: Vec::new(),
        };
        
        Ok((manager, event_tx))
    }
    
    /// Run the UI event loop with real-time rendering
    pub async fn run(mut self) {
        let mut ui_interval = tokio::time::interval(Duration::from_millis(UI_REFRESH_MS));
        
        loop {
            tokio::select! {
                // Handle UI events
                event = self.event_rx.recv() => {
                    match event {
                        Some(event) => {
                            if !self.handle_event(event).await {
                                break; // Shutdown requested
                            }
                        }
                        None => break, // Channel closed
                    }
                }
                
                // Periodic UI refreshes for live updates
                _ = ui_interval.tick() => {
                    if let Err(_) = self.draw() {
                        break; // Terminal error
                    }
                }
                
                // Handle terminal input (for graceful exit)
                _ = tokio::time::sleep(Duration::from_millis(50)) => {
                    if crossterm::event::poll(Duration::ZERO).unwrap_or(false) {
                        if let Ok(CrossEvent::Key(key)) = crossterm::event::read() {
                            if key.code == KeyCode::Char('q') || key.code == KeyCode::Esc {
                                break;
                            }
                        }
                    }
                }
            }
        }
        
        // Clean shutdown
        self.shutdown().unwrap_or(());
    }
    
    /// Handle a single UI event
    async fn handle_event(&mut self, event: UiEvent) -> bool {
        match event {
            UiEvent::InitProgress { target, total_tasks } => {
                self.target = target.clone();
                // For phase transitions, add to existing total rather than replace
                if self.total_tasks > 0 {
                    self.total_tasks += total_tasks;
                    self.log_message(format!("Added {} more tasks (total: {})", total_tasks, self.total_tasks));
                } else {
                    self.total_tasks = total_tasks;
                    self.log_message(format!("Initialized: {} tasks for {}", total_tasks, target));
                }
            }
            
            UiEvent::PluginInventory { port_scanners, service_scanners } => {
                self.port_scanners = port_scanners.clone();
                self.service_scanners = service_scanners.clone();
                let total_plugins = port_scanners.len() + service_scanners.len();
                self.log_message(format!("Available plugins: {} port scanners, {} service scanners ({} total)", 
                    port_scanners.len(), service_scanners.len(), total_plugins));
            }
            
            UiEvent::TaskStarted { id, name } => {
                let task = ActiveTask::new(id.clone(), name.clone());
                
                if self.active_tasks.len() < MAX_VISIBLE_TASKS {
                    self.active_tasks.insert(id, task);
                } else {
                    self.waiting_tasks.push_back(task);
                }
                
                self.log_message(format!("Started: {}", name));
            }
            
            UiEvent::TaskProgress { id, status } => {
                if let Some(task) = self.active_tasks.get_mut(&id) {
                    task.status = status.clone();
                } else {
                    // Update waiting tasks too
                    for task in &mut self.waiting_tasks {
                        if task.id == id {
                            task.status = status.clone();
                            break;
                        }
                    }
                }
            }
            
            UiEvent::TaskCompleted { id, result } => {
                self.completed_count += 1;
                
                // Find and remove the task
                let task_name = if let Some(task) = self.active_tasks.remove(&id) {
                    let name = task.name.clone();
                    self.completed_tasks.push((task.name.clone(), result.clone(), Instant::now()));
                    
                    // Promote a waiting task if available
                    if let Some(waiting_task) = self.waiting_tasks.pop_front() {
                        let task_id = waiting_task.id.clone();
                        self.active_tasks.insert(task_id, waiting_task);
                    }
                    
                    name
                } else {
                    // Remove from waiting queue
                    if let Some(pos) = self.waiting_tasks.iter().position(|t| t.id == id) {
                        let task = self.waiting_tasks.remove(pos).unwrap();
                        self.completed_tasks.push((task.name.clone(), result.clone(), Instant::now()));
                        task.name
                    } else {
                        "Unknown".to_string()
                    }
                };
                
                match result {
                    TaskResult::Success(msg) => {
                        self.log_message(format!("✓ {}: {}", task_name, msg));
                    }
                    TaskResult::Failed(msg) => {
                        self.log_message(format!("✗ {}: {}", task_name, msg));
                    }
                }
            }
            
            UiEvent::ProgressUpdate { completed, total } => {
                self.completed_count = completed;
                if total > self.total_tasks {
                    self.total_tasks = total;
                }
            }
            
            UiEvent::SystemStats { cpu_percent, memory_used_gb } => {
                self.last_cpu = cpu_percent;
                self.last_memory = memory_used_gb;
            }
            
            UiEvent::PortDiscovered { port, service } => {
                self.port_discoveries.push_back((port, service.clone(), Instant::now()));
                
                // Keep only recent discoveries
                while self.port_discoveries.len() > MAX_RESULT_LINES {
                    self.port_discoveries.pop_front();
                }
                
                self.log_message(format!("Port {}: {}", port, service));
            }
            
            UiEvent::PhaseChange { phase } => {
                self.current_phase = phase.clone();
                self.log_message(format!("Phase: {}", phase));
            }
            
            UiEvent::Shutdown => {
                return false;
            }
        }
        
        true
    }
    
    /// Add a log message with timestamp
    fn log_message(&mut self, message: String) {
        self.log_messages.push_back((message, Instant::now()));
        
        // Keep only recent messages
        while self.log_messages.len() > MAX_RESULT_LINES {
            self.log_messages.pop_front();
        }
    }
    
    /// Draw the complete UI
    fn draw(&mut self) -> Result<(), io::Error> {
        // Prepare UI data before drawing to avoid borrowing issues
        let ui_data = UiData::from_manager(self);
        
        self.terminal.draw(|f| {
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(3),  // Header
                    Constraint::Length(5),  // Progress
                    Constraint::Min(8),     // Active tasks (expandable)
                    Constraint::Length(12), // Results/logs
                ].as_ref())
                .split(f.area());
            
            ui_data.draw_header(f, chunks[0]);
            ui_data.draw_progress(f, chunks[1]);
            ui_data.draw_active_tasks(f, chunks[2]);
            ui_data.draw_results(f, chunks[3]);
        })?;
        
        Ok(())
    }

    
    /// Clean shutdown and restore terminal
    fn shutdown(mut self) -> Result<(), io::Error> {
        disable_raw_mode()?;
        execute!(
            self.terminal.backend_mut(),
            LeaveAlternateScreen,
            DisableMouseCapture
        )?;
        self.terminal.show_cursor()?;
        Ok(())
    }
}

/// Create and start the UI task - call this once from main
#[allow(dead_code)]
pub async fn start_ui_task() -> mpsc::UnboundedSender<UiEvent> {
    start_ui_task_with_options(false).await
}

/// Create and start the UI task with options
pub async fn start_ui_task_with_options(force_simple: bool) -> mpsc::UnboundedSender<UiEvent> {
    if force_simple {
        return create_simple_progress_tracker().await;
    }
    
    match ProgressManager::new() {
        Ok((manager, sender)) => {
            // Spawn the UI task
            tokio::spawn(async move {
                manager.run().await;
            });
            sender
        }
        Err(e) => {
            // Fall back to a simple progress tracker for non-TTY environments
            eprintln!("Warning: Could not initialize terminal UI ({}), falling back to simple progress", e);
            create_simple_progress_tracker().await
        }
    }
}

/// Create a simple progress tracker for non-TUI environments
async fn create_simple_progress_tracker() -> mpsc::UnboundedSender<UiEvent> {
    let (sender, mut receiver) = mpsc::unbounded_channel();
    
    // Spawn a simple progress tracker that just logs major events
    tokio::spawn(async move {
        let mut target = String::new();
        let mut total_tasks = 0;
        let mut completed_tasks = 0;
        
        while let Some(event) = receiver.recv().await {
            match event {
                UiEvent::PluginInventory { port_scanners, service_scanners } => {
                    println!("🔧 Available plugins: {} port scanners ({}), {} service scanners ({})", 
                        port_scanners.len(), port_scanners.join(", "),
                        service_scanners.len(), service_scanners.join(", "));
                }
                UiEvent::InitProgress { target: t, total_tasks: total } => {
                    target = t.clone();
                    total_tasks += total;
                    println!("🎯 Starting scan of {} ({} tasks)", t, total);
                }
                UiEvent::TaskStarted { name, .. } => {
                    println!("▶️  Started: {}", name);
                }
                UiEvent::TaskCompleted { result, .. } => {
                    completed_tasks += 1;
                    match result {
                        TaskResult::Success(msg) => println!("✅ Completed: {}", msg),
                        TaskResult::Failed(msg) => println!("❌ Failed: {}", msg),
                    }
                    println!("📊 Progress: {}/{} tasks completed", completed_tasks, total_tasks);
                }
                UiEvent::PortDiscovered { port, service } => {
                    println!("🔍 Found port {}: {}", port, service);
                }
                UiEvent::PhaseChange { phase } => {
                    println!("🔄 {}", phase);
                }
                UiEvent::Shutdown => break,
                _ => {} // Ignore other events for simple mode
            }
        }
        
        println!("✨ Scan of {} completed", target);
    });
    
    sender
}

/// Start system stats monitoring task with faster updates
pub fn start_system_stats_task(ui_sender: mpsc::UnboundedSender<UiEvent>) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        use sysinfo::System;
        
        let mut system = System::new_all();
        // Much faster updates for live stats - 1 second intervals
        let mut interval = tokio::time::interval(Duration::from_millis(1000));
        
        // Initial refresh
        system.refresh_cpu();
        system.refresh_memory();
        
        loop {
            interval.tick().await;
            
            // Refresh system info
            system.refresh_cpu();
            system.refresh_memory();
            
            let stats = super::events::UiEvent::SystemStats {
                cpu_percent: system.global_cpu_info().cpu_usage(),
                memory_used_gb: system.used_memory() as f64 / 1024.0 / 1024.0 / 1024.0,
            };
            
            if ui_sender.send(stats).is_err() {
                break; // UI task shut down
            }
        }
    })
}