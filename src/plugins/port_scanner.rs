use crate::config::GlobalConfig;
use crate::core::{
    models::{Proto, Service},
    state::RunState,
};
use crate::executors::command::execute;
use crate::plugins::types::PortScan;
use crate::ui::events::UiEvent;
use anyhow::Result;
use async_trait::async_trait;
use chrono::Utc;
use std::collections::HashSet;
use std::path::Path;
use tokio::sync::mpsc;

#[derive(Clone)]
pub struct PortScannerPlugin;

impl PortScannerPlugin {
    /// Validate if target is acceptable for port scanning
    fn validate_target(&self, target: &str) -> bool {
        // Accept IP addresses and domain names, reject URLs or invalid formats
        target.parse::<std::net::IpAddr>().is_ok()
            || (target.contains('.') && !target.contains(' ') && !target.starts_with("http"))
    }

    /// Get port range based on scan strategy configuration
    fn get_port_range(&self, config: &GlobalConfig) -> String {
        if let Some(tools) = &config.tools {
            if let Some(port_scanner) = &tools.port_scanner {
                if let Some(ports) = &port_scanner.ports {
                    match ports.scan_strategy.as_str() {
                        "top-100" => self.get_top_ports(100),
                        "top-1000" => self.get_top_ports(1000),
                        "top-10000" => self.get_top_ports(10000),
                        "full" => "1-65535".to_string(),
                        "custom" => ports.custom_range.clone(),
                        _ => self.get_top_ports(1000), // Default to top-1000
                    }
                } else {
                    self.get_top_ports(1000) // Default when no ports config
                }
            } else {
                self.get_top_ports(1000) // Default when no port_scanner config
            }
        } else {
            self.get_top_ports(1000) // Default when no tools config
        }
    }

    /// Get top N most common ports for different tools
    fn get_top_ports(&self, count: u32) -> String {
        match count {
            100 => "top-100".to_string(),
            1000 => "top-1000".to_string(),
            10000 => "top-10000".to_string(),
            _ => "top-1000".to_string(), // Fallback
        }
    }

    /// Get RustScan port range arguments
    fn get_rustscan_port_args(&self, config: &GlobalConfig) -> Vec<String> {
        let port_strategy = self.get_port_range(config);

        match port_strategy.as_str() {
            // RustScan only supports --top (top 1000), so use that for all "top" strategies
            "top-100" | "top-1000" | "top-10000" => vec!["--top".to_string()],
            "1-65535" => vec!["--range".to_string(), "1-65535".to_string()],
            custom_range => {
                // Parse custom range to determine if it's a range or comma-separated ports
                if custom_range.contains('-') && !custom_range.contains(',') {
                    vec!["--range".to_string(), custom_range.to_string()]
                } else {
                    vec!["--ports".to_string(), custom_range.to_string()]
                }
            }
        }
    }

    /// Send structured log message to UI
    fn send_log(&self, ui_sender: &mpsc::UnboundedSender<UiEvent>, level: &str, message: &str) {
        let _ = ui_sender.send(UiEvent::LogMessage {
            level: level.to_string(),
            message: message.to_string(),
        });
    }

    /// Detect if running with sudo privileges
    async fn detect_sudo_privileges(&self) -> bool {
        match execute("id", &["-u"], Path::new("."), Some(5000)).await {
            Ok(result) => {
                if result.exit_code == 0 {
                    result.stdout.trim() == "0"
                } else {
                    false
                }
            }
            Err(_) => false,
        }
    }

    /// Execute rustscan for fast port discovery (required tool)
    async fn execute_rustscan(
        &self,
        target: &str,
        config: &GlobalConfig,
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
    ) -> Result<Vec<u16>> {
        // Check if rustscan is available
        if which::which("rustscan").is_err() {
            self.send_log(
                ui_sender,
                "ERROR",
                "RustScan not available - port scanner requires RustScan for port discovery",
            );
            return Err(anyhow::anyhow!("Port scanner requires RustScan for port discovery. Install with: cargo install rustscan"));
        }

        self.send_log(
            ui_sender,
            "INFO",
            &format!("Starting RustScan fast port discovery for {}", target),
        );

        let port_scanner_config = config
            .tools
            .as_ref()
            .and_then(|tools| tools.port_scanner.as_ref());

        // Get configuration or use defaults
        let (enabled, base_args, timeout_ms, total_timeout_ms, batch_size, ulimit, tries) =
            if let Some(port_config) = port_scanner_config {
                let rs_config = &port_config.rustscan;
                (
                    port_config.enabled,
                    rs_config.base_args.clone(),
                    rs_config.timeout_ms,
                    rs_config.total_timeout_ms,
                    rs_config.batch_size,
                    rs_config.ulimit,
                    rs_config.tries,
                )
            } else {
                self.send_log(
                    ui_sender,
                    "WARN",
                    "Port scanner configuration not found in global.toml, using defaults",
                );
                // Default values
                (
                    true,
                    vec!["--greppable".to_string(), "--no-config".to_string()],
                    3000,
                    300000,
                    4500,
                    5000,
                    1,
                )
            };

        if !enabled {
            return Err(anyhow::anyhow!("Port scanner is disabled in configuration"));
        }

        let mut args = base_args;

        // Add target-specific arguments
        args.extend(vec![
            "-a".to_string(),
            target.to_string(), // Target address
        ]);

        // Add port range based on configuration
        let port_args = self.get_rustscan_port_args(config);
        args.extend(port_args);

        // Add other rustscan arguments
        args.extend(vec![
            "--timeout".to_string(),
            timeout_ms.to_string(),
            "--tries".to_string(),
            tries.to_string(),
            "--batch-size".to_string(),
            batch_size.to_string(),
        ]);

        // Add custom ulimit if configured
        if ulimit > 0 {
            args.extend(vec!["--ulimit".to_string(), ulimit.to_string()]);
        }

        // Convert to &str for execute function
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();

        let command = if let Some(port_config) = port_scanner_config {
            &port_config.rustscan.command
        } else {
            "rustscan"
        };

        match execute(command, &args_str, Path::new("."), Some(total_timeout_ms)).await {
            Ok(command_result) => {
                if command_result.exit_code == 0 {
                    let ports = self.parse_rustscan_output(&command_result.stdout);
                    if ports.is_empty() {
                        self.send_log(
                            ui_sender,
                            "WARN",
                            &format!("RustScan found no open ports for {}", target),
                        );
                    } else {
                        self.send_log(
                            ui_sender,
                            "INFO",
                            &format!(
                                "RustScan discovered {} open ports for {}",
                                ports.len(),
                                target
                            ),
                        );
                    }
                    Ok(ports)
                } else {
                    let error_msg = format!(
                        "RustScan failed for {} (exit code {}): {}",
                        target, command_result.exit_code, command_result.stderr
                    );
                    self.send_log(ui_sender, "ERROR", &error_msg);
                    Err(anyhow::anyhow!(error_msg))
                }
            }
            Err(e) => {
                let error_msg = format!("RustScan command failed for {}: {}", target, e);
                self.send_log(ui_sender, "ERROR", &error_msg);
                Err(anyhow::anyhow!(error_msg))
            }
        }
    }

    /// Execute nmap with intelligent sudo handling
    async fn execute_nmap(
        &self,
        target: &str,
        ports: &[u16],
        config: &GlobalConfig,
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
    ) -> Result<Vec<Service>> {
        if ports.is_empty() {
            return Ok(Vec::new());
        }

        self.send_log(
            ui_sender,
            "INFO",
            &format!(
                "Starting Nmap service detection for {} ports on {}",
                ports.len(),
                target
            ),
        );
        tracing::info!(
            "Starting Nmap service detection for {} ports on {}",
            ports.len(),
            target
        );

        let port_scanner_config = config
            .tools
            .as_ref()
            .and_then(|tools| tools.port_scanner.as_ref())
            .ok_or_else(|| anyhow::anyhow!("Port scanner configuration not available"))?;
        let nmap_config = &port_scanner_config.nmap;

        // Detect sudo privileges if configured to do so
        let has_sudo = if nmap_config.auto_detect_sudo {
            let sudo_detected = self.detect_sudo_privileges().await;
            if sudo_detected {
                self.send_log(
                    ui_sender,
                    "INFO",
                    "Sudo privileges detected - using advanced Nmap scans",
                );
            } else {
                self.send_log(
                    ui_sender,
                    "INFO",
                    "No sudo privileges - using connect scans and service detection",
                );
            }
            sudo_detected
        } else {
            false
        };

        let mut args = nmap_config.base_args.clone();

        // Build port list string (e.g., "22,80,443,8080")
        let port_list = ports
            .iter()
            .map(|p| p.to_string())
            .collect::<Vec<_>>()
            .join(",");

        // Add nmap-specific arguments based on sudo availability
        args.extend(vec![
            "-p".to_string(),
            port_list,          // Only scan discovered ports
            target.to_string(), // Target address
        ]);

        if has_sudo {
            // Privileged scan options - more comprehensive
            args.extend(vec![
                "-sS".to_string(), // SYN stealth scan
                "-sV".to_string(), // Service version detection
                "-sC".to_string(), // Default script scan (safe with sudo)
                "-O".to_string(),  // OS detection
            ]);
        } else {
            // Non-privileged scan options - focus on service detection
            if nmap_config.fallback_to_connect_scan {
                args.extend(vec![
                    "-sT".to_string(), // TCP connect scan (non-privileged)
                    "-sV".to_string(), // Service version detection
                ]);
            } else {
                return Err(anyhow::anyhow!(
                    "Nmap requires sudo privileges and fallback is disabled"
                ));
            }
        }

        // Common arguments regardless of privilege level
        args.extend(vec![
            "-T4".to_string(), // Aggressive timing
            "--max-retries".to_string(),
            nmap_config.max_retries.to_string(),
            "--host-timeout".to_string(),
            format!("{}s", nmap_config.host_timeout_sec),
        ]);

        // Add service detection intensity if configured
        if nmap_config.version_intensity > 0 {
            args.extend(vec![
                "--version-intensity".to_string(),
                nmap_config.version_intensity.to_string(),
            ]);
        }

        // Convert to &str for execute function
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();

        // Log the exact Nmap command being executed
        self.send_log(
            ui_sender,
            "INFO",
            &format!("Executing Nmap: {} {}", nmap_config.command, args.join(" ")),
        );
        tracing::info!("Executing Nmap: {} {}", nmap_config.command, args.join(" "));

        match execute(
            &nmap_config.command,
            &args_str,
            Path::new("."),
            Some(nmap_config.total_timeout_ms),
        )
        .await
        {
            Ok(command_result) => {
                if command_result.exit_code == 0 {
                    let services = self.parse_nmap_output(&command_result.stdout, target);
                    self.send_log(
                        ui_sender,
                        "INFO",
                        &format!(
                            "Nmap completed service detection for {} - found {} services",
                            target,
                            services.len()
                        ),
                    );
                    Ok(services)
                } else {
                    let error_msg = format!(
                        "Nmap failed for {} (exit code {}): {}",
                        target, command_result.exit_code, command_result.stderr
                    );
                    self.send_log(ui_sender, "WARN", &error_msg);

                    // Try to provide graceful degradation info
                    if !has_sudo && command_result.stderr.contains("requires root privileges") {
                        self.send_log(
                            ui_sender,
                            "INFO",
                            "Nmap needs sudo for some features - continuing with available data",
                        );
                    }

                    // Don't fail completely - return empty services instead
                    Ok(Vec::new())
                }
            }
            Err(e) => {
                let error_msg = format!("Nmap command failed for {}: {}", target, e);
                self.send_log(ui_sender, "WARN", &error_msg);
                // Return empty instead of failing to allow graceful degradation
                Ok(Vec::new())
            }
        }
    }

    /// Parse RustScan output to extract port numbers
    fn parse_rustscan_output(&self, output: &str) -> Vec<u16> {
        let mut ports = HashSet::new();

        for line in output.lines() {
            let line = line.trim();

            // RustScan greppable format: "127.0.0.1 -> [22,445,5000,...]"
            if line.contains(" -> [") && line.ends_with("]") {
                // Extract the port list from brackets
                if let Some(bracket_start) = line.find('[') {
                    if let Some(bracket_end) = line.rfind(']') {
                        let ports_str = &line[bracket_start + 1..bracket_end];
                        for port_str in ports_str.split(',') {
                            if let Ok(port) = port_str.trim().parse::<u16>() {
                                ports.insert(port);
                            }
                        }
                    }
                }
            } else if line.contains("Open") && line.contains(":") {
                // Extract port from "Open IP:PORT" format
                if let Some(port_part) = line.split(':').next_back() {
                    if let Ok(port) = port_part.trim().parse::<u16>() {
                        ports.insert(port);
                    }
                }
            } else if line.contains("/tcp") || line.contains("/udp") {
                // Extract port from "PORT/PROTOCOL" format
                if let Some(port_part) = line.split('/').next() {
                    if let Ok(port) = port_part.trim().parse::<u16>() {
                        ports.insert(port);
                    }
                }
            } else {
                // Try parsing line as just a port number
                if let Ok(port) = line.parse::<u16>() {
                    if port > 0 {
                        ports.insert(port);
                    }
                }
            }
        }

        let mut port_vec: Vec<u16> = ports.into_iter().collect();
        port_vec.sort();
        port_vec
    }

    /// Parse Nmap output to extract service information
    fn parse_nmap_output(&self, output: &str, target: &str) -> Vec<Service> {
        let mut services = Vec::new();

        for line in output.lines() {
            let line = line.trim();

            // Skip empty lines and headers
            if line.is_empty()
                || line.starts_with("Starting")
                || line.starts_with("Nmap")
                || line.starts_with("Not shown")
            {
                continue;
            }

            // Parse service lines (e.g., "22/tcp open ssh OpenSSH 8.2")
            if (line.contains("/tcp") || line.contains("/udp")) && line.contains("open") {
                if let Some(service) = self.parse_nmap_service_line(line, target) {
                    services.push(service);
                }
            }
        }

        services
    }

    /// Parse individual nmap service line
    fn parse_nmap_service_line(&self, line: &str, target: &str) -> Option<Service> {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 3 {
            return None;
        }

        // Extract port and protocol from "PORT/PROTOCOL" format
        let port_proto_str = parts[0];
        let port_proto_parts: Vec<&str> = port_proto_str.split('/').collect();
        if port_proto_parts.len() != 2 {
            return None;
        }

        let port = port_proto_parts[0].parse::<u16>().ok()?;
        let proto = match port_proto_parts[1] {
            "tcp" => Proto::Tcp,
            "udp" => Proto::Udp,
            _ => Proto::Tcp, // Default to TCP
        };

        // Extract service name (parts[2] is usually "open", parts[3] is service)
        let service_name = if parts.len() > 3 {
            parts[3].to_string()
        } else {
            "unknown".to_string()
        };

        // Check if service is secure (HTTPS, SSH, etc.)
        let secure = service_name.contains("ssl")
            || service_name.contains("https")
            || service_name.contains("ssh")
            || service_name.contains("tls")
            || port == 443
            || port == 22
            || port == 993
            || port == 995;

        Some(Service {
            proto,
            port,
            name: service_name,
            secure,
            address: target.to_string(),
        })
    }

    /// Write comprehensive port scanner results to file
    fn write_results(
        &self,
        rustscan_ports: &[u16],
        nmap_services: &[Service],
        scans_dir: &Path,
        target: &str,
    ) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== Port Scanner Results for {} ===\n", target));
        content.push_str(&format!("Timestamp: {}\n\n", Utc::now()));

        // RustScan Results Section
        content.push_str("=== Phase 1: RustScan Port Discovery ===\n");
        if rustscan_ports.is_empty() {
            content.push_str("No open ports discovered\n");
        } else {
            content.push_str(&format!("Open ports found: {}\n", rustscan_ports.len()));
            for port in rustscan_ports {
                content.push_str(&format!("{}/tcp open\n", port));
            }
        }
        content.push('\n');

        // Nmap Service Detection Section
        content.push_str("=== Phase 2: Nmap Service Detection ===\n");
        if nmap_services.is_empty() {
            content.push_str("No services detected or Nmap phase skipped\n");
        } else {
            content.push_str(&format!("Services detected: {}\n", nmap_services.len()));
            for service in nmap_services {
                let proto_str = match service.proto {
                    Proto::Tcp => "tcp",
                    Proto::Udp => "udp",
                };
                let secure_str = if service.secure { " (secure)" } else { "" };
                content.push_str(&format!(
                    "{}/{} open {} on {}{}\n",
                    service.port, proto_str, service.name, service.address, secure_str
                ));
            }
        }
        content.push('\n');

        // Summary Statistics
        let tcp_services = nmap_services
            .iter()
            .filter(|s| matches!(s.proto, Proto::Tcp))
            .count();
        let udp_services = nmap_services
            .iter()
            .filter(|s| matches!(s.proto, Proto::Udp))
            .count();
        let secure_services = nmap_services.iter().filter(|s| s.secure).count();

        content.push_str("=== Summary Statistics ===\n");
        content.push_str(&format!(
            "Total ports discovered: {}\n",
            rustscan_ports.len()
        ));
        content.push_str(&format!("Services detected: {}\n", nmap_services.len()));
        content.push_str(&format!("TCP services: {}\n", tcp_services));
        content.push_str(&format!("UDP services: {}\n", udp_services));
        content.push_str(&format!("Secure services: {}\n", secure_services));

        if !rustscan_ports.is_empty() {
            content.push_str(&format!(
                "Port range: {}-{}\n",
                rustscan_ports.iter().min().unwrap(),
                rustscan_ports.iter().max().unwrap()
            ));
        }

        let result_file = scans_dir.join("port_scanner_results.txt");
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        Ok(())
    }

    /// Get default port for port scanner discoveries (HTTP as default)
    #[allow(dead_code)]
    fn get_default_port(&self) -> u16 {
        80
    }
}

#[async_trait]
impl PortScan for PortScannerPlugin {
    fn name(&self) -> &'static str {
        "port_scanner"
    }

    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>> {
        let target = &state.target;
        let ui_sender = state
            .ui_sender
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("No UI sender available"))?;
        let dirs = state
            .dirs
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("No directories available"))?;

        // Step 1: Initialization and validation
        self.send_log(
            ui_sender,
            "INFO",
            &format!("Starting two-phase port scanner for target: {}", target),
        );

        if !self.validate_target(target) {
            let error_msg = format!("Invalid target '{}' for port scanning", target);
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }

        // Step 2: Phase 1 - RustScan port discovery
        self.send_log(ui_sender, "INFO", "Starting RustScan port discovery phase");
        let rustscan_ports = match self.execute_rustscan(target, config, ui_sender).await {
            Ok(ports) => {
                for port in &ports {
                    // Send discovered ports to UI results panel
                    let _ = ui_sender.send(UiEvent::PortDiscovered {
                        port: *port,
                        service: format!("port_scanner DISCOVERY - {}:{} open", target, port),
                    });
                }
                ports
            }
            Err(e) => {
                self.send_log(ui_sender, "ERROR", &format!("RustScan failed: {}", e));
                return Err(e);
            }
        };

        // Step 3: Phase 2 - Nmap service detection (only on discovered ports)
        let nmap_services = if !rustscan_ports.is_empty() {
            // Small delay between phases for system resource management
            tokio::time::sleep(tokio::time::Duration::from_millis(2000)).await;

            match self
                .execute_nmap(target, &rustscan_ports, config, ui_sender)
                .await
            {
                Ok(services) => {
                    for service in &services {
                        // Send detailed service information to UI
                        let proto_str = match service.proto {
                            Proto::Tcp => "TCP",
                            Proto::Udp => "UDP",
                        };
                        let secure_str = if service.secure { " (secure)" } else { "" };
                        let _ = ui_sender.send(UiEvent::PortDiscovered {
                            port: service.port,
                            service: format!(
                                "port_scanner {} - {}:{} {}{}",
                                proto_str, target, service.port, service.name, secure_str
                            ),
                        });
                    }
                    services
                }
                Err(_) => {
                    // Even if nmap fails, we still have port discovery results
                    self.send_log(
                        ui_sender,
                        "WARN",
                        "Nmap service detection failed, but port discovery succeeded",
                    );

                    // Create basic services from port discovery for return value
                    rustscan_ports
                        .iter()
                        .map(|&port| Service {
                            proto: Proto::Tcp,
                            port,
                            name: "unknown".to_string(),
                            secure: false,
                            address: target.to_string(),
                        })
                        .collect()
                }
            }
        } else {
            Vec::new()
        };

        // Step 4: File output
        if let Err(e) = self.write_results(&rustscan_ports, &nmap_services, &dirs.scans, target) {
            self.send_log(
                ui_sender,
                "WARN",
                &format!("Failed to write port scanner results: {}", e),
            );
        } else {
            self.send_log(
                ui_sender,
                "INFO",
                "Port scanner results written to scans directory",
            );
        }

        // Step 5: Completion
        if nmap_services.is_empty() && rustscan_ports.is_empty() {
            let error_msg = format!("No open ports found for target: {}", target);
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }

        // If Nmap found no services but RustScan found ports, create basic service entries
        let final_services = if nmap_services.is_empty() && !rustscan_ports.is_empty() {
            self.send_log(
                ui_sender,
                "INFO",
                "Creating basic service entries from discovered ports",
            );
            rustscan_ports
                .iter()
                .map(|&port| Service {
                    proto: Proto::Tcp,
                    port,
                    name: "unknown".to_string(),
                    secure: false,
                    address: target.to_string(),
                })
                .collect()
        } else {
            nmap_services
        };

        // Success message with comprehensive stats
        self.send_log(
            ui_sender,
            "INFO",
            &format!(
                "Port scanner completed successfully. Found {} ports with {} services",
                rustscan_ports.len(),
                final_services.len()
            ),
        );

        Ok(final_services)
    }
}
