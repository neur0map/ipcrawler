use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use colored::*;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use std::collections::HashSet;

pub struct ProgressManager {
    multi: Arc<MultiProgress>,
    main_bar: Arc<Mutex<Option<ProgressBar>>>,
    overall_bar: Arc<Mutex<Option<ProgressBar>>>,
    discovery_bar: Arc<Mutex<Option<ProgressBar>>>,
    discovered_ports: Arc<Mutex<HashSet<u16>>>,
    discovered_services: Arc<Mutex<HashSet<String>>>,
    discovered_vulns: Arc<Mutex<usize>>,
}

impl ProgressManager {
    pub fn new() -> Self {
        let multi = Arc::new(MultiProgress::new());
        Self {
            multi,
            main_bar: Arc::new(Mutex::new(None)),
            overall_bar: Arc::new(Mutex::new(None)),
            discovery_bar: Arc::new(Mutex::new(None)),
            discovered_ports: Arc::new(Mutex::new(HashSet::new())),
            discovered_services: Arc::new(Mutex::new(HashSet::new())),
            discovered_vulns: Arc::new(Mutex::new(0)),
        }
    }
    
    /// Get a clone of the MultiProgress instance for sharing across threads
    pub fn get_multi(&self) -> Arc<MultiProgress> {
        self.multi.clone()
    }

    /// Create the main overall progress bar
    pub fn create_overall_progress(&self, total_tools: u64) -> ProgressBar {
        let pb = self.multi.add(ProgressBar::new(total_tools));
        pb.set_style(
            ProgressStyle::with_template(
                "[{elapsed_precise}] {bar:40.green/black} {percent:>3}% • {pos}/{len} tools completed"
            )
            .unwrap()
            .progress_chars("█▉▊▋▌▍▎▏  ")
        );
        *self.overall_bar.lock().unwrap() = Some(pb.clone());
        pb
    }

    /// Create the discovery summary bar
    pub fn create_discovery_bar(&self) -> ProgressBar {
        let pb = self.multi.add(ProgressBar::new(0));
        pb.set_style(
            ProgressStyle::with_template(
                "Discovery: {msg}"
            )
            .unwrap()
        );
        pb.set_message("0 ports • 0 services • 0 vulnerabilities");
        *self.discovery_bar.lock().unwrap() = Some(pb.clone());
        pb
    }
    
    /// Update discovery statistics
    pub fn update_discovery(&self, ports: usize, services: usize, vulns: usize) {
        if let Some(ref bar) = *self.discovery_bar.lock().unwrap() {
            bar.set_message(format!("{} ports • {} services • {} vulnerabilities", 
                ports, services, vulns));
        }
    }
    
    /// Add discovered ports and update display
    pub fn add_discovered_ports(&self, new_ports: Vec<u16>) {
        if new_ports.is_empty() { return; }
        
        let mut ports = self.discovered_ports.lock().unwrap();
        let mut updated = false;
        
        for port in new_ports {
            if ports.insert(port) {  // Returns true if newly inserted
                updated = true;
            }
        }
        
        if updated {
            let services = self.discovered_services.lock().unwrap();
            let vulns = *self.discovered_vulns.lock().unwrap();
            
            if let Some(ref bar) = *self.discovery_bar.lock().unwrap() {
                bar.set_message(format!("{} ports • {} services • {} vulnerabilities", 
                    ports.len(), services.len(), vulns));
            }
        }
    }
    
    /// Add discovered services and update display  
    pub fn add_discovered_services(&self, new_services: Vec<String>) {
        if new_services.is_empty() { return; }
        
        let mut services = self.discovered_services.lock().unwrap();
        let mut updated = false;
        
        for service in new_services {
            if services.insert(service) {  // Returns true if newly inserted
                updated = true;
            }
        }
        
        if updated {
            let ports = self.discovered_ports.lock().unwrap();
            let vulns = *self.discovered_vulns.lock().unwrap();
            
            if let Some(ref bar) = *self.discovery_bar.lock().unwrap() {
                bar.set_message(format!("{} ports • {} services • {} vulnerabilities", 
                    ports.len(), services.len(), vulns));
            }
        }
    }

    /// Create the main initialization progress bar
    pub fn create_main_progress(&self, total_steps: u64, message: &str) -> ProgressBar {
        let pb = self.multi.add(ProgressBar::new(total_steps));
        pb.set_style(
            ProgressStyle::with_template(
                "[{elapsed_precise}] {bar:40.cyan/blue} {pos:>7}/{len:7} {msg}"
            )
            .unwrap()
            .progress_chars("█▉▊▋▌▍▎▏  ")
        );
        pb.set_message(message.to_string());
        *self.main_bar.lock().unwrap() = Some(pb.clone());
        pb
    }

    /// Create a spinner for ongoing operations with modern style
    pub fn create_spinner(&self, message: &str) -> ProgressBar {
        let spinner = self.multi.add(ProgressBar::new_spinner());
        spinner.set_style(
            ProgressStyle::with_template("{spinner:.blue} [{elapsed_precise}] {msg}")
                .unwrap()
                .tick_strings(&["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
        );
        spinner.set_message(message.to_string());
        spinner.enable_steady_tick(Duration::from_millis(80));
        spinner
    }

    /// Create a progress bar for tool execution with modern styling
    pub fn create_tool_progress(&self, tool_name: &str, timeout_secs: u64) -> ProgressBar {
        let pb = self.multi.add(ProgressBar::new(timeout_secs));
        pb.set_style(
            ProgressStyle::with_template(
                "[{elapsed_precise}] {bar:40.cyan/blue} {percent:>3}% {msg}"
            )
            .unwrap()
            .progress_chars("█▉▊▋▌▍▎▏  ")
        );
        pb.set_message(format!("{}: initializing", tool_name));
        pb
    }
    
    /// Create a tool progress bar with custom length (for known operations)
    pub fn create_tool_progress_with_len(&self, tool_name: &str, len: u64) -> ProgressBar {
        let pb = self.multi.add(ProgressBar::new(len));
        pb.set_style(
            ProgressStyle::with_template(
                "[{elapsed_precise}] {bar:40.cyan/blue} {pos:>7}/{len:7} {msg}"
            )
            .unwrap()
            .progress_chars("█▉▊▋▌▍▎▏  ")
        );
        pb.set_message(format!("{}: processing", tool_name));
        pb
    }

    /// Create a simple status line (replaces println! for status messages)
    pub fn print_status(&self, status: &str, message: &str, color: colored::Color) {
        let formatted = format!("{} {}", 
            status.color(color).bold(),
            message.normal()
        );
        self.multi.println(formatted).unwrap();
    }

    /// Print success message
    pub fn print_success(&self, message: &str) {
        self.print_status("OK", message, colored::Color::Green);
    }

    /// Print error message
    pub fn print_error(&self, message: &str) {
        self.print_status("ERR", message, colored::Color::Red);
    }

    /// Print info message
    pub fn print_info(&self, message: &str) {
        self.print_status("", message, colored::Color::Blue);
    }

    /// Print warning message
    pub fn print_warning(&self, message: &str) {
        self.print_status("WARN", message, colored::Color::Yellow);
    }

    /// Print info message only in verbose mode
    pub fn print_verbose_info(&self, message: &str, verbose: bool) {
        if verbose {
            self.print_info(message);
        }
    }

    /// Print success message only in verbose mode
    pub fn print_verbose_success(&self, message: &str, verbose: bool) {
        if verbose {
            self.print_success(message);
        }
    }

    /// Print a section header
    pub fn print_section(&self, title: &str) {
        let formatted = format!("\n{}", title.bright_cyan().bold());
        self.multi.println(formatted).unwrap();
    }

    /// Print a subsection with indentation
    pub fn print_subsection(&self, title: &str, content: &str) {
        let formatted = format!("  {} {}", 
            title.bright_white().bold(),
            content.bright_black()
        );
        self.multi.println(formatted).unwrap();
    }

    /// Finish and clean up all progress bars
    pub fn finish(&self) {
        if let Some(ref main_bar) = *self.main_bar.lock().unwrap() {
            main_bar.finish_and_clear();
        }
        if let Some(ref overall_bar) = *self.overall_bar.lock().unwrap() {
            overall_bar.finish_and_clear();
        }
        if let Some(ref discovery_bar) = *self.discovery_bar.lock().unwrap() {
            discovery_bar.finish_and_clear();
        }
        
        // Clear the internal references
        *self.main_bar.lock().unwrap() = None;
        *self.overall_bar.lock().unwrap() = None;
        *self.discovery_bar.lock().unwrap() = None;
    }

    /// Get the underlying MultiProgress for advanced usage
    pub fn multi_progress(&self) -> &MultiProgress {
        &self.multi
    }

    /// Force clear all progress bars immediately (for emergency cleanup)
    pub fn clear_all(&self) {
        // Abandon any active bars instead of finishing them
        if let Some(ref main_bar) = *self.main_bar.lock().unwrap() {
            main_bar.abandon();
        }
        if let Some(ref overall_bar) = *self.overall_bar.lock().unwrap() {
            overall_bar.abandon();
        }
        if let Some(ref discovery_bar) = *self.discovery_bar.lock().unwrap() {
            discovery_bar.abandon();
        }
        
        // Clear the internal references
        *self.main_bar.lock().unwrap() = None;
        *self.overall_bar.lock().unwrap() = None;
        *self.discovery_bar.lock().unwrap() = None;
    }

    /// Prompt user for Y/N input with default to 'n'
    pub fn prompt_user_yn(&self, question: &str, default_yes: bool) -> bool {
        use std::io::{self, Write};
        
        let default_char = if default_yes { "Y/n" } else { "y/N" };
        print!("📖 {} [{}]: ", question, default_char);
        io::stdout().flush().unwrap_or(());
        
        let mut input = String::new();
        match io::stdin().read_line(&mut input) {
            Ok(_) => {
                let response = input.trim().to_lowercase();
                match response.as_str() {
                    "y" | "yes" => true,
                    "n" | "no" => false,
                    "" => default_yes, // Default on empty input
                    _ => default_yes,  // Default on invalid input
                }
            }
            Err(_) => default_yes, // Default on error
        }
    }
}

/// Tool execution progress tracker
pub struct ToolProgressTracker {
    progress_bar: ProgressBar,
    tool_name: String,
    start_time: std::time::Instant,
}

impl ToolProgressTracker {
    pub fn new(progress_manager: &ProgressManager, tool_name: &str, timeout_secs: u64) -> Self {
        let progress_bar = progress_manager.create_tool_progress(tool_name, timeout_secs);
        Self {
            progress_bar,
            tool_name: tool_name.to_string(),
            start_time: std::time::Instant::now(),
        }
    }

    pub fn update_progress(&self, elapsed_secs: u64) {
        self.progress_bar.set_position(elapsed_secs);
    }

    pub fn finish_success(&self) {
        let duration = self.start_time.elapsed();
        self.progress_bar.finish_with_message(
            format!("{} completed in {:.2}s", self.tool_name, duration.as_secs_f64())
        );
    }

    pub fn finish_error(&self, error: &str) {
        self.progress_bar.finish_with_message(
            format!("{} failed: {}", self.tool_name, error)
        );
    }

    pub fn abandon(&self, reason: &str) {
        self.progress_bar.abandon_with_message(
            format!("{} abandoned: {}", self.tool_name, reason)
        );
    }
}
