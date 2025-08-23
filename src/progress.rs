use colored::*;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::collections::HashSet;
use std::sync::{Arc, Mutex};
use std::time::Duration;

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

    /// Create the discovery summary bar
    pub fn create_discovery_bar(&self) -> ProgressBar {
        let pb = self.multi.add(ProgressBar::new(0));
        pb.set_style(
            ProgressStyle::with_template("Discovery: {msg}")
                .expect("Failed to create progress style"),
        );
        pb.set_message("0 ports • 0 services • 0 vulnerabilities");
        *self.discovery_bar.lock().unwrap() = Some(pb.clone());
        pb
    }

    /// Add discovered ports and update display
    pub fn add_discovered_ports(&self, new_ports: Vec<u16>) {
        if new_ports.is_empty() {
            return;
        }

        // Single atomic operation to avoid race conditions
        let mut ports = self.discovered_ports.lock().unwrap();
        let mut updated = false;

        for port in new_ports {
            if ports.insert(port) {
                // Returns true if newly inserted
                updated = true;
            }
        }

        if updated {
            let port_count = ports.len();
            drop(ports); // Release lock before acquiring others

            let services = self.discovered_services.lock().unwrap();
            let service_count = services.len();
            drop(services);

            let vulns = *self.discovered_vulns.lock().unwrap();

            if let Some(ref bar) = *self.discovery_bar.lock().unwrap() {
                bar.set_message(format!(
                    "{} ports • {} services • {} vulnerabilities",
                    port_count, service_count, vulns
                ));
            }
        }
    }

    /// Add discovered services and update display  
    pub fn add_discovered_services(&self, new_services: Vec<String>) {
        if new_services.is_empty() {
            return;
        }

        // Single atomic operation to avoid race conditions
        let mut services = self.discovered_services.lock().unwrap();
        let mut updated = false;

        for service in new_services {
            if services.insert(service) {
                // Returns true if newly inserted
                updated = true;
            }
        }

        if updated {
            let service_count = services.len();
            drop(services); // Release lock before acquiring others

            let ports = self.discovered_ports.lock().unwrap();
            let port_count = ports.len();
            drop(ports);

            let vulns = *self.discovered_vulns.lock().unwrap();

            if let Some(ref bar) = *self.discovery_bar.lock().unwrap() {
                bar.set_message(format!(
                    "{} ports • {} services • {} vulnerabilities",
                    port_count, service_count, vulns
                ));
            }
        }
    }

    /// Add discovered vulnerabilities and update display
    pub fn add_discovered_vulns(&self, vuln_count: usize) {
        let mut vulns = self.discovered_vulns.lock().unwrap();
        *vulns += vuln_count;
        let total_vulns = *vulns;
        drop(vulns);

        let ports = self.discovered_ports.lock().unwrap();
        let port_count = ports.len();
        drop(ports);

        let services = self.discovered_services.lock().unwrap();
        let service_count = services.len();
        drop(services);

        if let Some(ref bar) = *self.discovery_bar.lock().unwrap() {
            bar.set_message(format!(
                "{} ports • {} services • {} vulnerabilities",
                port_count, service_count, total_vulns
            ));
        }
    }

    /// Create a spinner for ongoing operations with modern style
    pub fn create_spinner(&self, message: &str) -> ProgressBar {
        let spinner = self.multi.add(ProgressBar::new_spinner());
        spinner.set_style(
            ProgressStyle::with_template("{spinner:.blue} [{elapsed_precise}] {msg}")
                .expect("Failed to create progress style")
                .tick_strings(&["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]),
        );
        spinner.set_message(message.to_string());
        spinner.enable_steady_tick(Duration::from_millis(80));
        spinner
    }

    /// Create a simple status line (replaces println! for status messages)
    pub fn print_status(&self, status: &str, message: &str, color: colored::Color) {
        let formatted = format!("{} {}", status.color(color).bold(), message.normal());
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
        let formatted = format!(
            "  {} {}",
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
