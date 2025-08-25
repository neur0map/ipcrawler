pub mod app_state;
pub mod layout;
pub mod renderer;
pub mod widgets;
pub mod metrics;

use std::io;
use std::time::{Duration, Instant};
use crossterm::{
    cursor::{Hide, Show},
    event::{self, Event, KeyCode, KeyEvent, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen, Clear, ClearType},
};
use tokio::sync::mpsc;

use self::app_state::{AppState, AppStatus};
use self::layout::{LayoutSpec, compute_layout};
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
        let (cols, rows) = crossterm::terminal::size()?;
        
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
        execute!(
            io::stdout(),
            EnterAlternateScreen,
            Hide,
            Clear(ClearType::All)
        )?;
        Ok(())
    }

    fn teardown_terminal() -> io::Result<()> {
        execute!(
            io::stdout(),
            Show,
            LeaveAlternateScreen
        )?;
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
        
        Self::teardown_terminal()?;
        result
    }

    async fn run_loop(&mut self, rx: &mut mpsc::UnboundedReceiver<UiEvent>) -> io::Result<()> {
        let mut metrics_ticker = tokio::time::interval(Duration::from_secs(1));
        let mut render_ticker = tokio::time::interval(Duration::from_millis(50));
        
        loop {
            tokio::select! {
                // Handle UI events from the application
                Some(ui_event) = rx.recv() => {
                    self.handle_ui_event(ui_event);
                    self.needs_redraw = true;
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
                                break;
                            }
                        } else if let Event::Resize(cols, rows) = event::read()? {
                            self.terminal_size = (cols, rows);
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
            InitProgress { target, total_tasks } => {
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
                self.state.add_result(format!("{:5}/tcp  {:20} OPEN", port, service));
            }
            SystemStats { cpu_percent, memory_used_gb } => {
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
            PluginInventory { port_scanners, service_scanners } => {
                // Store plugin info for display if needed
                // For now, just log that we received the inventory
                tracing::debug!("Received plugin inventory: {} port scanners, {} service scanners", 
                    port_scanners.len(), service_scanners.len());
            }
            Shutdown => {
                self.state.status = AppStatus::Completed;
            }
        }
    }

    fn handle_key_event(&mut self, key: KeyEvent) -> bool {
        match key.code {
            KeyCode::Char('q') | KeyCode::Char('Q') => {
                // Send SIGINT to gracefully stop the program
                std::process::exit(0);
            }
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                // Send SIGINT to gracefully stop the program
                std::process::exit(0);
            }
            KeyCode::Up => {
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
                self.state.results.scroll_offset = self.state.results.scroll_offset.saturating_sub(10);
                self.needs_redraw = true;
            }
            KeyCode::PageDown => {
                let max_offset = self.state.results.rows.len().saturating_sub(10);
                self.state.results.scroll_offset = (self.state.results.scroll_offset + 10).min(max_offset);
                self.needs_redraw = true;
            }
            KeyCode::Left => {
                let tab_count = self.state.tabs.tabs.len();
                if tab_count > 0 {
                    let current_idx = self.state.tabs.tabs.iter()
                        .position(|t| t.id == self.state.tabs.active_tab_id)
                        .unwrap_or(0);
                    let prev_idx = if current_idx == 0 { tab_count - 1 } else { current_idx - 1 };
                    self.state.tabs.active_tab_id = self.state.tabs.tabs[prev_idx].id.clone();
                    self.needs_redraw = true;
                }
            }
            KeyCode::Right => {
                let tab_count = self.state.tabs.tabs.len();
                if tab_count > 0 {
                    let current_idx = self.state.tabs.tabs.iter()
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
            self.renderer.render_size_warning(self.terminal_size.0, self.terminal_size.1)?;
            return Ok(());
        }

        // Compute layout
        let layout = compute_layout(&self.layout_spec, self.terminal_size.0, self.terminal_size.1);
        
        // Clear and render
        self.renderer.clear_screen()?;
        self.renderer.render_frame(&self.state, &layout)?;
        self.renderer.flush()?;
        
        Ok(())
    }
}

pub async fn start_dashboard_task(target: String) -> mpsc::UnboundedSender<UiEvent> {
    let (tx, rx) = mpsc::unbounded_channel();
    
    tokio::spawn(async move {
        let dashboard = Dashboard::new(target);
        if let Ok(dashboard) = dashboard {
            let _ = dashboard.run(rx).await;
        }
    });
    
    tx
}