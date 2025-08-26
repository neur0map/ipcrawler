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
use std::path::Path;
use tokio::sync::mpsc;

#[derive(Clone)]
pub struct NslookupPlugin;

impl NslookupPlugin {
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

    /// Run nslookup command and return output
    async fn run_nslookup(
        &self,
        target: &str,
        record_type: &str,
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
        config: &GlobalConfig,
    ) -> Result<String> {
        self.send_log(
            ui_sender,
            "INFO",
            &format!("Running nslookup {} for {}", record_type, target),
        );

        let args = if record_type == "PTR" {
            // For reverse DNS, just use the IP directly
            vec![target.to_string()]
        } else {
            vec![format!("-type={}", record_type), target.to_string()]
        };
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();

        // Get tool configuration with fallback to defaults
        let (command, timeout) = if let Some(ref tools) = config.tools {
            if let Some(ref nslookup_config) = tools.nslookup {
                (
                    nslookup_config.command.clone(),
                    nslookup_config.limits.timeout_ms,
                )
            } else {
                (
                    "nslookup".to_string(),
                    10000,
                )
            }
        } else {
            ("nslookup".to_string(), 10000)
        };

        match execute(
            &command,
            &args_str,
            std::path::Path::new("."),
            Some(timeout),
        )
        .await
        {
            Ok(command_result) => {
                if command_result.exit_code == 0 {
                    self.send_log(
                        ui_sender,
                        "INFO",
                        &format!("nslookup {} completed for {}", record_type, target),
                    );
                    Ok(command_result.stdout)
                } else {
                    let error_msg = format!(
                        "nslookup {} failed for {} (exit code {}): {}",
                        record_type, target, command_result.exit_code, command_result.stderr
                    );
                    self.send_log(ui_sender, "ERROR", &error_msg);
                    Err(anyhow::anyhow!(error_msg))
                }
            }
            Err(e) => {
                let error_msg = format!(
                    "nslookup {} command failed for {}: {}",
                    record_type, target, e
                );
                self.send_log(ui_sender, "ERROR", &error_msg);
                Err(anyhow::anyhow!(error_msg))
            }
        }
    }

    /// Parse nslookup output to extract useful information
    fn parse_nslookup_output(&self, output: &str, record_type: &str) -> Vec<String> {
        let mut results = Vec::new();

        for line in output.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with("Server:") || line.starts_with("Address:") {
                continue;
            }

            // Look for actual DNS records
            match record_type {
                "A" => {
                    if line.contains("Address:") && !line.contains("#") {
                        results.push(line.to_string());
                    }
                }
                "AAAA" => {
                    if line.contains("AAAA") || (line.contains("Address:") && line.contains(":")) {
                        results.push(line.to_string());
                    }
                }
                "MX" => {
                    if line.contains("mail exchanger") {
                        results.push(line.to_string());
                    }
                }
                "NS" => {
                    if line.contains("nameserver") {
                        results.push(line.to_string());
                    }
                }
                "TXT" => {
                    if line.contains("text =") {
                        results.push(line.to_string());
                    }
                }
                "PTR" => {
                    if line.contains("name =") || line.contains("pointer") {
                        results.push(line.to_string());
                    }
                }
                _ => {
                    if !line.starts_with("Non-authoritative") && line.len() > 10 {
                        results.push(line.to_string());
                    }
                }
            }
        }

        results
    }

    /// Write nslookup results to file in scans directory
    fn write_results_to_file(
        &self,
        target: &str,
        results: &[(String, Vec<String>)], // (record_type, parsed_results)
        scans_dir: &Path,
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
    ) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== nslookup Results for {} ===\n", target));
        content.push_str(&format!("Timestamp: {}\n\n", Utc::now()));

        if results.is_empty() {
            content.push_str("No DNS records found\n");
        } else {
            for (record_type, parsed_results) in results {
                if !parsed_results.is_empty() {
                    content.push_str(&format!("=== {} Records ({}) ===\n", record_type, parsed_results.len()));
                    for result in parsed_results {
                        content.push_str(&format!("{}\n", result));
                    }
                    content.push('\n');
                }
            }

            content.push_str(&format!("=== Summary ===\n"));
            let total_records: usize = results.iter().map(|(_, r)| r.len()).sum();
            content.push_str(&format!("Total DNS records found: {}\n", total_records));
            content.push_str(&format!("Record types queried: {}\n", results.len()));
        }

        let result_file = scans_dir.join("nslookup_results.txt");
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        
        self.send_log(
            ui_sender,
            "INFO",
            "nslookup results written to scans/nslookup_results.txt",
        );
        
        Ok(())
    }
}

#[async_trait]
impl PortScan for NslookupPlugin {
    fn name(&self) -> &'static str {
        "nslookup"
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

        self.send_log(
            ui_sender,
            "INFO",
            &format!("Starting nslookup scans for target: {}", target),
        );

        // Validate target
        if !self.validate_target(target) {
            let error_msg = format!(
                "Invalid target '{}': must be a valid domain name or IP address",
                target
            );
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }

        let mut services = Vec::new();
        let mut all_results = Vec::new(); // Collect all results for file output

        // Check if target is an IP address
        let is_ip = target.parse::<std::net::IpAddr>().is_ok();

        let record_types = if is_ip {
            // For IP addresses, only do reverse DNS (PTR) lookup
            self.send_log(
                ui_sender,
                "INFO",
                "Target is an IP address, performing reverse DNS lookup",
            );
            vec!["PTR"]
        } else {
            // Use config record types if available, otherwise use defaults
            if let Some(ref tools) = config.tools {
                if let Some(ref nslookup_config) = tools.nslookup {
                    nslookup_config
                        .options
                        .record_types
                        .iter()
                        .map(|s| s.as_str())
                        .collect()
                } else {
                    vec!["A", "AAAA", "MX", "NS", "TXT"]
                }
            } else {
                vec!["A", "AAAA", "MX", "NS", "TXT"]
            }
        };

        self.send_log(
            ui_sender,
            "INFO",
            &format!("Running {} DNS record type queries", record_types.len()),
        );

        for record_type in &record_types {
            match self
                .run_nslookup(target, record_type, ui_sender, config)
                .await
            {
                Ok(output) => {
                    let parsed_results = self.parse_nslookup_output(&output, record_type);

                    // Always collect results for file output (even if empty)
                    all_results.push((record_type.to_string(), parsed_results.clone()));

                    if parsed_results.is_empty() {
                        self.send_log(
                            ui_sender,
                            "WARN",
                            &format!("No {} records found for {}", record_type, target),
                        );
                    } else {
                        for result in &parsed_results {
                            // Send to logs
                            self.send_log(
                                ui_sender,
                                "INFO",
                                &format!("{} record: {}", record_type, result),
                            );

                            // Send to Results panel as discovered service with nslookup prefix
                            let _ = ui_sender.send(UiEvent::PortDiscovered {
                                port: 53, // DNS port
                                service: format!("nslookup {} - {}", record_type, result),
                            });
                        }

                        // Create a service entry for successful DNS lookups
                        let service = Service {
                            proto: Proto::Tcp,
                            port: 53, // DNS port
                            name: format!("DNS_{}", record_type),
                            secure: false,
                            address: target.to_string(),
                        };

                        services.push(service);
                    }
                }
                Err(_e) => {
                    // Error already logged in run_nslookup
                    self.send_log(
                        ui_sender,
                        "WARN",
                        &format!(
                            "Continuing with remaining record types after {} failure",
                            record_type
                        ),
                    );
                }
            }

            // Small delay between queries to be nice to DNS servers
            let delay = if let Some(ref tools) = config.tools {
                if let Some(ref nslookup_config) = tools.nslookup {
                    nslookup_config.options.delay_between_queries_ms
                } else {
                    500
                }
            } else {
                500
            };
            tokio::time::sleep(tokio::time::Duration::from_millis(delay)).await;
        }

        // Write results to file
        if let Err(e) = self.write_results_to_file(target, &all_results, &dirs.scans, ui_sender) {
            self.send_log(
                ui_sender,
                "WARN",
                &format!("Failed to write nslookup results to file: {}", e),
            );
        }

        if services.is_empty() {
            let error_msg = format!("All nslookup queries failed for target: {}", target);
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }

        self.send_log(
            ui_sender,
            "INFO",
            &format!(
                "nslookup completed successfully. Found {} DNS record types",
                services.len()
            ),
        );
        Ok(services)
    }
}
