pub mod app_state;
pub mod layout;
pub mod metrics;
pub mod renderer;
pub mod widgets;

use crossterm::{
    cursor::{Hide, Show},
    event::{self, Event, KeyCode, KeyEvent, KeyModifiers},
    execute,
    terminal::{
        disable_raw_mode, enable_raw_mode, Clear, ClearType, EnterAlternateScreen,
        LeaveAlternateScreen,
    },
};
use std::io;
use std::time::{Duration, Instant};
use tokio::sync::mpsc;

use self::app_state::{AppState, AppStatus, LogLevel};
use self::layout::{compute_layout, LayoutSpec};
use self::renderer::Renderer;
use crate::ui::events::UiEvent;

pub struct Dashboard {
    state: AppState,
    layout_spec: LayoutSpec,
    renderer: Renderer,
    needs_redraw: bool,
    terminal_size: (u16, u16),
}

impl Dashboard {
    pub fn new(target: String) -> io::Result<Self> {
        // Try to get terminal size, fall back to reasonable defaults if it fails
        let (mut cols, mut rows) = crossterm::terminal::size().unwrap_or_else(|e| {
            tracing::warn!("Failed to detect terminal size: {}. Using default 80x24", e);
            (80, 24)
        });

        // Handle edge case where terminal reports size as 0x0
        if cols == 0 || rows == 0 {
            tracing::warn!(
                "Terminal reported size as {}x{}. Using default 80x24",
                cols,
                rows
            );
            cols = 80;
            rows = 24;
        }

        Ok(Self {
            state: AppState::new(target),
            layout_spec: LayoutSpec::default(),
            renderer: Renderer::new(),
            needs_redraw: true,
            terminal_size: (cols, rows),
        })
    }

    fn setup_terminal() -> io::Result<()> {
        enable_raw_mode()?;

        // Set terminal size to 205x50
        execute!(io::stdout(), crossterm::terminal::SetSize(205, 50))?;

        execute!(
            io::stdout(),
            EnterAlternateScreen,
            Hide,
            Clear(ClearType::All)
        )?;
        Ok(())
    }

    fn teardown_terminal() -> io::Result<()> {
        execute!(io::stdout(), Show, LeaveAlternateScreen)?;
        disable_raw_mode()?;
        Ok(())
    }

    pub async fn run(mut self, mut rx: mpsc::UnboundedReceiver<UiEvent>) -> io::Result<()> {
        Self::setup_terminal()?;

        // Install panic handler to ensure terminal cleanup
        let original_hook = std::panic::take_hook();
        std::panic::set_hook(Box::new(move |panic_info| {
            let _ = Self::teardown_terminal();
            original_hook(panic_info);
        }));

        let result = self.run_loop(&mut rx).await;

        // Ensure terminal cleanup happens even if there's an error
        if let Err(e) = Self::teardown_terminal() {
            tracing::warn!("Terminal teardown failed: {}", e);
        }

        result
    }

    async fn run_loop(&mut self, rx: &mut mpsc::UnboundedReceiver<UiEvent>) -> io::Result<()> {
        let mut metrics_ticker = tokio::time::interval(Duration::from_secs(1));
        let mut render_ticker = tokio::time::interval(Duration::from_millis(50));

        loop {
            tokio::select! {
                // Handle UI events from the application (or channel closed)
                ui_event = rx.recv() => {
                    if let Some(event) = ui_event {
                        self.handle_ui_event(event);
                        self.needs_redraw = true;
                    }
                    // If None, channel is closed but we keep running
                }

                // Update system metrics
                _ = metrics_ticker.tick() => {
                    self.update_metrics();
                    self.needs_redraw = true;
                }

                // Render tick
                _ = render_ticker.tick() => {
                    // Poll for input events (non-blocking)
                    if event::poll(Duration::from_millis(0))? {
                        if let Event::Key(key_event) = event::read()? {
                            if self.handle_key_event(key_event) {
                                tracing::info!("Dashboard received exit command, shutting down");
                                break;
                            }
                        } else if let Event::Resize(cols, rows) = event::read()? {
                            // Update terminal size on resize events
                            if cols > 0 && rows > 0 {
                                self.terminal_size = (cols, rows);
                            } else {
                                // Fallback if resize event has invalid dimensions
                                self.terminal_size = crossterm::terminal::size().unwrap_or((80, 24));
                            }
                            self.needs_redraw = true;
                        }
                    }

                    // Render if needed
                    if self.needs_redraw {
                        self.render()?;
                        self.needs_redraw = false;
                    }
                }
            }
        }

        Ok(())
    }

    fn handle_ui_event(&mut self, event: UiEvent) {
        use UiEvent::*;

        match event {
            InitProgress {
                target,
                total_tasks,
            } => {
                self.state.target = target;
                self.state.scan.tasks_total = total_tasks;
            }
            TaskStarted { id, name } => {
                self.state.tasks.push(app_state::Task {
                    id,
                    name,
                    seconds_active: 0,
                    started_at: Instant::now(),
                });
            }
            TaskProgress { id, status } => {
                // Update task status in the tasks list
                if let Some(_task) = self.state.tasks.iter_mut().find(|t| t.id == id) {
                    // We could add a status field back to Task if needed for progress display
                    tracing::debug!("Task {} progress: {}", id, status);
                }
            }
            TaskCompleted { id, result } => {
                self.state.tasks.retain(|t| t.id != id);
                self.state.scan.tasks_done += 1;

                // Update progress percentage
                if self.state.scan.tasks_total > 0 {
                    self.state.scan.progress_pct = (self.state.scan.tasks_done as f32
                        / self.state.scan.tasks_total as f32
                        * 100.0) as u8;
                }

                match result {
                    crate::ui::events::TaskResult::Success(msg) => {
                        self.state.add_result(format!("✓ {}: {}", id, msg));
                    }
                    crate::ui::events::TaskResult::Failed(msg) => {
                        self.state.add_result(format!("✗ {}: {}", id, msg));
                    }
                }
            }
            PhaseChange { phase } => {
                self.state.scan.phase_label = phase;
            }
            PortDiscovered { port, service } => {
                self.state
                    .add_result(format!("{:5}/tcp  {:20} OPEN", port, service));
            }
            SystemStats {
                cpu_percent,
                memory_used_gb,
            } => {
                self.state.system.cpu_pct = cpu_percent;
                self.state.system.ram_gb = memory_used_gb;
            }
            ProgressUpdate { completed, total } => {
                self.state.scan.tasks_done = completed;
                self.state.scan.tasks_total = total;
                if total > 0 {
                    self.state.scan.progress_pct = (completed as f32 / total as f32 * 100.0) as u8;
                }
            }
            PluginInventory {
                port_scanners,
                service_scanners,
            } => {
                // Store plugin info for display if needed
                // For now, just log that we received the inventory
                tracing::debug!(
                    "Received plugin inventory: {} port scanners, {} service scanners",
                    port_scanners.len(),
                    service_scanners.len()
                );
            }
            LogMessage { level, message } => {
                let log_level = match level.as_str() {
                    "DEBUG" => LogLevel::Debug,
                    "INFO" => LogLevel::Info,
                    "WARN" => LogLevel::Warn,
                    "ERROR" => LogLevel::Error,
                    _ => LogLevel::Info,
                };
                self.state.add_log(log_level, message);
            }
            Shutdown => {
                self.state.status = AppStatus::Completed;
                // Update status but don't exit - user should press 'q' to quit
                self.needs_redraw = true;
            }
        }
    }

    fn handle_key_event(&mut self, key: KeyEvent) -> bool {
        match key.code {
            KeyCode::Char('q') | KeyCode::Char('Q') => {
                // Return true to exit the dashboard loop
                return true;
            }
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                // Ctrl+C also exits
                return true;
            }
            KeyCode::Up => {
                // Scroll active panel (results on left, logs on right based on which has focus)
                if self.state.results.scroll_offset > 0 {
                    self.state.results.scroll_offset -= 1;
                    self.needs_redraw = true;
                }
            }
            KeyCode::Down => {
                let max_offset = self.state.results.rows.len().saturating_sub(10);
                if self.state.results.scroll_offset < max_offset {
                    self.state.results.scroll_offset += 1;
                    self.needs_redraw = true;
                }
            }
            KeyCode::PageUp => {
                self.state.results.scroll_offset =
                    self.state.results.scroll_offset.saturating_sub(10);
                self.needs_redraw = true;
            }
            KeyCode::PageDown => {
                let max_offset = self.state.results.rows.len().saturating_sub(10);
                self.state.results.scroll_offset =
                    (self.state.results.scroll_offset + 10).min(max_offset);
                self.needs_redraw = true;
            }
            // TODO: Add Shift+Up/Down or Ctrl+Up/Down for logs scrolling
            KeyCode::Left => {
                let tab_count = self.state.tabs.tabs.len();
                if tab_count > 0 {
                    let current_idx = self
                        .state
                        .tabs
                        .tabs
                        .iter()
                        .position(|t| t.id == self.state.tabs.active_tab_id)
                        .unwrap_or(0);
                    let prev_idx = if current_idx == 0 {
                        tab_count - 1
                    } else {
                        current_idx - 1
                    };
                    self.state.tabs.active_tab_id = self.state.tabs.tabs[prev_idx].id.clone();
                    self.needs_redraw = true;
                }
            }
            KeyCode::Right => {
                let tab_count = self.state.tabs.tabs.len();
                if tab_count > 0 {
                    let current_idx = self
                        .state
                        .tabs
                        .tabs
                        .iter()
                        .position(|t| t.id == self.state.tabs.active_tab_id)
                        .unwrap_or(0);
                    let next_idx = (current_idx + 1) % tab_count;
                    self.state.tabs.active_tab_id = self.state.tabs.tabs[next_idx].id.clone();
                    self.needs_redraw = true;
                }
            }
            _ => {}
        }
        false
    }

    fn update_metrics(&mut self) {
        // Update task ages
        for task in &mut self.state.tasks {
            task.seconds_active = task.started_at.elapsed().as_secs();
        }

        // Update elapsed time
        self.state.controls.elapsed = self.state.start_time.elapsed();

        // Update system metrics
        if let Ok((cpu, mem)) = metrics::get_system_stats() {
            self.state.system.cpu_pct = cpu;
            self.state.system.ram_gb = mem;
        }
    }

    fn render(&mut self) -> io::Result<()> {
        // Check terminal size
        if self.terminal_size.0 < 70 || self.terminal_size.1 < 20 {
            self.renderer
                .render_size_warning(self.terminal_size.0, self.terminal_size.1)?;
            return Ok(());
        }

        // Compute layout
        let layout = compute_layout(
            &self.layout_spec,
            self.terminal_size.0,
            self.terminal_size.1,
        );

        // Clear and render
        self.renderer.clear_screen()?;
        self.renderer.render_frame(&self.state, &layout)?;
        self.renderer.flush()?;

        Ok(())
    }
}

pub async fn start_dashboard_task(
    target: String,
) -> (
    mpsc::UnboundedSender<UiEvent>,
    bool,
    Option<tokio::task::JoinHandle<()>>,
) {
    let (tx, mut rx) = mpsc::unbounded_channel();

    // Check if we can enable raw mode (interactive terminal)
    let can_use_dashboard = crossterm::terminal::enable_raw_mode().is_ok();
    if can_use_dashboard {
        let _ = crossterm::terminal::disable_raw_mode(); // Reset for dashboard to handle properly
        tracing::info!("Dashboard mode enabled - terminal supports raw mode");
    } else {
        tracing::info!(
            "Dashboard mode disabled - terminal does not support raw mode, falling back to CLI"
        );
    }

    let handle = if can_use_dashboard {
        Some(tokio::spawn(async move {
            match Dashboard::new(target) {
                Ok(dashboard) => match dashboard.run(rx).await {
                    Ok(()) => {
                        tracing::info!("Dashboard completed successfully");
                    }
                    Err(e) => {
                        tracing::error!("Dashboard runtime error: {}", e);
                    }
                },
                Err(e) => {
                    tracing::error!(
                        "Failed to create dashboard: {}. Falling back to CLI event consumer",
                        e
                    );
                    // Still need to consume events to prevent channel from blocking
                    while let Some(_event) = rx.recv().await {
                        // Consume and ignore events when dashboard fails
                    }
                }
            }
            tracing::info!("Dashboard task ending");
        }))
    } else {
        // Still need to consume events to prevent channel from blocking
        tokio::spawn(async move {
            while let Some(_event) = rx.recv().await {
                // Consume and ignore events in non-interactive mode
            }
        });
        None
    };

    // Add small delay to ensure dashboard starts
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

    (tx, can_use_dashboard, handle)
}
