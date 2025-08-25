use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::{Service, Proto}, state::RunState};
use crate::plugins::types::PortScan;
use crate::config::GlobalConfig;
use crate::executors::command::execute;
use crate::ui::events::UiEvent;
use tokio::sync::mpsc;
use chrono::Utc;

#[derive(Clone)]
pub struct DigPlugin;

impl DigPlugin {
    /// Check if target is a valid domain name or IP address
    fn validate_target(&self, target: &str) -> bool {
        // Check if it's a valid IP address
        if target.parse::<std::net::IpAddr>().is_ok() {
            return true;
        }
        
        // Check if it's a valid domain name (basic validation)
        if target.contains(' ') || target.is_empty() {
            return false;
        }
        
        // Must contain at least one dot for domain name
        target.contains('.')
    }

    /// Send log message to UI
    fn send_log(&self, ui_sender: &mpsc::UnboundedSender<UiEvent>, level: &str, message: &str) {
        let _ = ui_sender.send(UiEvent::LogMessage {
            level: level.to_string(),
            message: message.to_string(),
        });
    }

    /// Run dig command and return output
    async fn run_dig(&self, target: &str, record_type: &str, ui_sender: &mpsc::UnboundedSender<UiEvent>, config: &GlobalConfig) -> Result<String> {
        self.send_log(ui_sender, "INFO", &format!("Running dig {} query for {}", record_type, target));
        
        let args = if record_type == "PTR" {
            // For reverse DNS, use -x flag with IP
            vec!["-x".to_string(), target.to_string(), "+short".to_string()]
        } else {
            // For forward DNS queries
            vec![target.to_string(), record_type.to_string(), "+short".to_string()]
        };
        
        // Get tool configuration with fallback to defaults
        let (command, base_args, timeout) = if let Some(ref tools) = config.tools {
            (tools.dig.command.clone(), tools.dig.base_args.clone(), tools.dig.limits.timeout_ms)
        } else {
            ("dig".to_string(), vec!["+short".to_string()], 10000)
        };
        
        // Replace +short in args if base_args already contains it
        let mut final_args = args;
        if !base_args.is_empty() {
            // Remove +short from args if base_args will provide it
            final_args.retain(|arg| arg != "+short");
            // Prepend base args
            let mut combined = base_args;
            combined.extend(final_args);
            final_args = combined;
        }
        
        let args_str: Vec<&str> = final_args.iter().map(|s| s.as_str()).collect();
        
        match execute(&command, &args_str, std::path::Path::new("."), Some(timeout)).await {
            Ok(command_result) => {
                if command_result.exit_code == 0 {
                    self.send_log(ui_sender, "INFO", &format!("dig {} query completed for {}", record_type, target));
                    Ok(command_result.stdout)
                } else {
                    let error_msg = format!("dig {} query failed for {} (exit code {}): {}", 
                                          record_type, target, command_result.exit_code, command_result.stderr);
                    self.send_log(ui_sender, "ERROR", &error_msg);
                    Err(anyhow::anyhow!(error_msg))
                }
            }
            Err(e) => {
                let error_msg = format!("dig {} command failed for {}: {}", record_type, target, e);
                self.send_log(ui_sender, "ERROR", &error_msg);
                Err(anyhow::anyhow!(error_msg))
            }
        }
    }

    /// Parse dig output to extract useful information
    fn parse_dig_output(&self, output: &str, record_type: &str, target: &str) -> Vec<String> {
        let mut results = Vec::new();
        
        for line in output.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            
            // dig +short gives clean output, just validate based on record type
            match record_type {
                "A" => {
                    // Should be IPv4 addresses
                    if line.parse::<std::net::Ipv4Addr>().is_ok() {
                        results.push(format!("{} -> {}", target, line));
                    }
                }
                "AAAA" => {
                    // Should be IPv6 addresses
                    if line.parse::<std::net::Ipv6Addr>().is_ok() {
                        results.push(format!("{} -> {}", target, line));
                    }
                }
                "MX" => {
                    // MX records have priority and hostname
                    if line.contains(' ') {
                        results.push(format!("MX: {}", line));
                    }
                }
                "NS" => {
                    // NS records are hostnames
                    if !line.is_empty() {
                        results.push(format!("NS: {}", line));
                    }
                }
                "TXT" => {
                    // TXT records can contain any text
                    if !line.is_empty() {
                        results.push(format!("TXT: {}", line));
                    }
                }
                "CNAME" => {
                    // CNAME records are hostnames
                    if !line.is_empty() {
                        results.push(format!("CNAME: {} -> {}", target, line));
                    }
                }
                "SOA" => {
                    // SOA records contain nameserver and email
                    if !line.is_empty() {
                        results.push(format!("SOA: {}", line));
                    }
                }
                "PTR" => {
                    // Reverse DNS results
                    if !line.is_empty() {
                        results.push(format!("PTR: {} -> {}", target, line));
                    }
                }
                _ => {
                    // Generic handling for other record types
                    if !line.is_empty() {
                        results.push(format!("{}: {}", record_type, line));
                    }
                }
            }
        }
        
        results
    }

    /// Write plugin results to scans directory
    fn write_plugin_results(&self, results: &[(String, Vec<String>)], scans_dir: &std::path::Path, target: &str) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== dig DNS Results for {} ===\n", target));
        content.push_str(&format!("Timestamp: {}\n\n", Utc::now()));
        
        let mut total_records = 0;
        for (record_type, records) in results {
            if !records.is_empty() {
                content.push_str(&format!("=== {} Records ===\n", record_type));
                for record in records {
                    content.push_str(&format!("{}\n", record));
                    total_records += 1;
                }
                content.push_str("\n");
            }
        }
        
        content.push_str(&format!("Total DNS records found: {}\n", total_records));
        
        let result_file = scans_dir.join(format!("dig_results.txt"));
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        Ok(())
    }
}

#[async_trait]
impl PortScan for DigPlugin {
    fn name(&self) -> &'static str {
        "dig"
    }

    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>> {
        let target = &state.target;
        let ui_sender = state.ui_sender.as_ref().ok_or_else(|| anyhow::anyhow!("No UI sender available"))?;
        let dirs = state.dirs.as_ref().ok_or_else(|| anyhow::anyhow!("No directories available"))?;
        
        self.send_log(ui_sender, "INFO", &format!("Starting dig DNS queries for target: {}", target));
        
        // Validate target
        if !self.validate_target(target) {
            let error_msg = format!("Invalid target '{}': must be a valid domain name or IP address", target);
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }

        let mut services = Vec::new();
        let mut all_results = Vec::new();
        
        // Check if target is an IP address
        let is_ip = target.parse::<std::net::IpAddr>().is_ok();
        
        let record_types = if is_ip {
            // For IP addresses, only do reverse DNS (PTR) lookup
            self.send_log(ui_sender, "INFO", "Target is an IP address, performing reverse DNS lookup");
            vec!["PTR"]
        } else {
            // Use config record types if available, otherwise use defaults
            if let Some(ref tools) = config.tools {
                tools.dig.options.record_types.iter().map(|s| s.as_str()).collect()
            } else {
                vec!["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]
            }
        };
        
        self.send_log(ui_sender, "INFO", &format!("Running {} DNS record type queries", record_types.len()));
        
        for record_type in &record_types {
            match self.run_dig(target, record_type, ui_sender, config).await {
                Ok(output) => {
                    let parsed_results = self.parse_dig_output(&output, record_type, target);
                    
                    if parsed_results.is_empty() {
                        self.send_log(ui_sender, "WARN", &format!("No {} records found for {}", record_type, target));
                    } else {
                        for result in &parsed_results {
                            // Send to logs
                            self.send_log(ui_sender, "INFO", &format!("{} record: {}", record_type, result));
                            
                            // Send to Results panel as discovered service with dig prefix
                            let _ = ui_sender.send(UiEvent::PortDiscovered {
                                port: 53, // DNS port
                                service: format!("dig {} - {}", record_type, result),
                            });
                        }
                        
                        // Store results for file output
                        all_results.push((record_type.to_string(), parsed_results));
                        
                        // Create a service entry for successful DNS lookups
                        let service = Service {
                            proto: Proto::Udp, // DNS is primarily UDP
                            port: 53, // DNS port
                            name: format!("DNS_{}", record_type),
                            secure: false,
                            address: target.to_string(),
                        };
                        
                        services.push(service);
                    }
                }
                Err(_e) => {
                    // Error already logged in run_dig
                    self.send_log(ui_sender, "WARN", &format!("Continuing with remaining record types after {} failure", record_type));
                }
            }
            
            // Small delay between queries to be nice to DNS servers
            let delay = if let Some(ref tools) = config.tools {
                tools.dig.options.delay_between_queries_ms
            } else {
                250
            };
            tokio::time::sleep(tokio::time::Duration::from_millis(delay)).await;
        }
        
        // Write results to scans directory
        if !all_results.is_empty() {
            if let Err(e) = self.write_plugin_results(&all_results, &dirs.scans, target) {
                self.send_log(ui_sender, "WARN", &format!("Failed to write dig results to file: {}", e));
            } else {
                self.send_log(ui_sender, "INFO", "dig results written to scans directory");
            }
        }
        
        if services.is_empty() {
            let error_msg = format!("All dig queries failed for target: {}", target);
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }
        
        self.send_log(ui_sender, "INFO", &format!("dig completed successfully. Found {} DNS record types", services.len()));
        Ok(services)
    }
}