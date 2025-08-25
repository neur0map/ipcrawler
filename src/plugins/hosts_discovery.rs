use crate::config::GlobalConfig;
use crate::core::{
    models::{Proto, Service},
    state::RunState,
};
use crate::plugins::types::PortScan;
use crate::ui::events::UiEvent;
use anyhow::Result;
use async_trait::async_trait;
use chrono::Utc;
use regex::Regex;
use url;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use tokio::sync::mpsc;
use tokio::process::Command;
use std::process::Stdio;
use tokio::io::AsyncWriteExt;

#[derive(Clone)]
pub struct HostsDiscoveryPlugin;

impl HostsDiscoveryPlugin {
    /// Execute command with stdin input
    async fn execute_with_stdin(
        &self,
        command: &str,
        args: &[&str],
        stdin_input: &str,
        timeout_ms: u64,
    ) -> Result<String> {
        let mut cmd = Command::new(command);
        cmd.args(args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        let mut child = cmd.spawn()?;

        // Write to stdin
        if let Some(stdin) = child.stdin.take() {
            let mut stdin = stdin;
            stdin.write_all(stdin_input.as_bytes()).await?;
            stdin.shutdown().await?;
        }

        // Wait for completion with timeout
        let output = tokio::time::timeout(
            tokio::time::Duration::from_millis(timeout_ms),
            child.wait_with_output(),
        )
        .await??;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(anyhow::anyhow!(
                "Command failed with exit code {:?}: {}",
                output.status.code(),
                stderr
            ))
        }
    }

    /// Validate if target is acceptable for this tool
    fn validate_target(&self, target: &str) -> bool {
        // Accept both IP addresses and domain names
        if target.parse::<std::net::IpAddr>().is_ok() {
            return true;
        }

        // Basic domain validation
        !target.is_empty() && !target.contains(' ') && target.contains('.')
    }

    /// Send structured log message to UI
    fn send_log(&self, ui_sender: &mpsc::UnboundedSender<UiEvent>, level: &str, message: &str) {
        let _ = ui_sender.send(UiEvent::LogMessage {
            level: level.to_string(),
            message: message.to_string(),
        });
    }

    /// Check if running with sudo privileges
    fn check_sudo_privileges(&self) -> bool {
        std::env::var("SUDO_USER").is_ok() || unsafe { libc::geteuid() } == 0
    }

    /// Run comprehensive dnsx DNS enumeration
    async fn run_dnsx_comprehensive(
        &self,
        target: &str,
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
        config: &GlobalConfig,
    ) -> Result<Vec<(String, String)>> {
        self.send_log(
            ui_sender,
            "INFO",
            &format!("Running comprehensive DNS enumeration for {}", target),
        );

        let (command, timeout) = if let Some(ref tools) = config.tools {
            if let Some(ref hosts_config) = &tools.hosts_discovery {
                (
                    hosts_config.dnsx.command.clone(),
                    hosts_config.dnsx.timeout_ms,
                )
            } else {
                ("dnsx".to_string(), 30000)
            }
        } else {
            ("dnsx".to_string(), 30000)
        };

        // Comprehensive record types: A, AAAA, CNAME, MX, NS, TXT, SOA
        let args = vec!["-silent", "-resp", "-a", "-aaaa", "-cname", "-mx", "-ns", "-txt", "-soa", "-nc"];

        match self.execute_with_stdin(&command, &args, target, timeout).await {
            Ok(stdout) => {
                let discoveries = self.parse_dnsx_comprehensive_output(&stdout);
                
                // Log detailed record type breakdown
                let mut record_counts = HashMap::new();
                for (_, value) in &discoveries {
                    if value.parse::<std::net::IpAddr>().is_ok() {
                        *record_counts.entry("A/AAAA").or_insert(0) += 1;
                    } else if value.starts_with("CNAME:") {
                        *record_counts.entry("CNAME").or_insert(0) += 1;
                    } else if value.starts_with("MX:") {
                        *record_counts.entry("MX").or_insert(0) += 1;
                    } else if value.starts_with("NS:") {
                        *record_counts.entry("NS").or_insert(0) += 1;
                    } else if value.starts_with("TXT:") {
                        *record_counts.entry("TXT").or_insert(0) += 1;
                    } else if value.starts_with("SOA:") {
                        *record_counts.entry("SOA").or_insert(0) += 1;
                    }
                }
                
                let breakdown: Vec<String> = record_counts
                    .iter()
                    .map(|(record_type, count)| format!("{}: {}", record_type, count))
                    .collect();
                
                self.send_log(
                    ui_sender,
                    "INFO",
                    &format!(
                        "✓ dnsx: Found {} DNS records for {} [{}]",
                        discoveries.len(),
                        target,
                        breakdown.join(", ")
                    ),
                );
                
                // Don't log individual discoveries here - they'll go to Results panel
                
                Ok(discoveries)
            }
            Err(_e) => {
                // Silently handle dnsx failures - tool may not be available
                Ok(vec![])
            }
        }
    }

    /// Run dnsx for reverse DNS lookup
    async fn run_dnsx_reverse(
        &self,
        target: &str,
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
        config: &GlobalConfig,
    ) -> Result<Vec<(String, String)>> {
        // Running reverse DNS lookup

        let (command, timeout) = if let Some(ref tools) = config.tools {
            if let Some(ref hosts_config) = &tools.hosts_discovery {
                (
                    hosts_config.dnsx.command.clone(),
                    hosts_config.dnsx.timeout_ms,
                )
            } else {
                ("dnsx".to_string(), 30000)
            }
        } else {
            ("dnsx".to_string(), 30000)
        };

        let args = vec!["-silent", "-resp", "-ptr", "-nc"]; // -nc disables color

        match self.execute_with_stdin(&command, &args, target, timeout).await {
            Ok(stdout) => {
                let discoveries = self.parse_dnsx_reverse_output(&stdout, target);
                self.send_log(
                    ui_sender,
                    "INFO",
                    &format!(
                        "✓ dnsx: Found {} domains for IP {}",
                        discoveries.len(),
                        target
                    ),
                );
                Ok(discoveries)
            }
            Err(_e) => {
                // Silently handle dnsx reverse lookup failures
                Ok(vec![])
            }
        }
    }

    /// Run comprehensive httpx technology detection and vhost discovery
    async fn run_httpx_comprehensive(
        &self,
        target: &str,
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
        config: &GlobalConfig,
    ) -> Result<Vec<(String, String, String)>> {
        // Running comprehensive HTTP discovery

        let (command, timeout) = if let Some(ref tools) = config.tools {
            if let Some(ref hosts_config) = &tools.hosts_discovery {
                (
                    hosts_config.httpx.command.clone(),
                    hosts_config.httpx.timeout_ms,
                )
            } else {
                // Try to find the Go version of httpx first
                if which::which("httpx").map(|p| p.to_string_lossy().contains("go/bin")).unwrap_or(false) {
                    ("httpx".to_string(), 60000)
                } else if std::path::Path::new(&format!("{}/go/bin/httpx", std::env::var("HOME").unwrap_or_default())).exists() {
                    (format!("{}/go/bin/httpx", std::env::var("HOME").unwrap_or_default()), 60000)
                } else {
                    ("httpx".to_string(), 60000) // Fallback to PATH
                }
            }
        } else {
            // Try to find the Go version of httpx first  
            if which::which("httpx").map(|p| p.to_string_lossy().contains("go/bin")).unwrap_or(false) {
                ("httpx".to_string(), 60000)
            } else if std::path::Path::new(&format!("{}/go/bin/httpx", std::env::var("HOME").unwrap_or_default())).exists() {
                (format!("{}/go/bin/httpx", std::env::var("HOME").unwrap_or_default()), 60000)
            } else {
                ("httpx".to_string(), 60000) // Fallback to PATH
            }
        };

        // Comprehensive httpx flags: vhost, tech detection, titles, CDN detection, status codes
        let args = vec![
            "-silent", "-vhost", "-status-code", "-ip", 
            "-tech-detect", "-title", "-favicon", "-cdn", "-waf",
            "-follow-redirects", "-nc"
        ];
        
        // Prepare input - httpx expects URLs, try both HTTP and HTTPS
        let inputs = if target.starts_with("http") {
            vec![target.to_string()]
        } else {
            vec![format!("http://{}", target), format!("https://{}", target)]
        };

        let mut all_discoveries = Vec::new();
        for input in inputs {
            // Testing HTTP/HTTPS endpoints (reduced verbosity)
            
            match self.execute_with_stdin(&command, &args, &input, timeout).await {
                Ok(stdout) => {
                    let discoveries = self.parse_httpx_comprehensive_output(&stdout);
                    
                    // Don't log individual HTTP discoveries here - they'll go to Results panel
                    
                    all_discoveries.extend(discoveries);
                }
                Err(_e) => {
                    // Silently handle httpx failures - service may not be available
                }
            }
        }

        if all_discoveries.is_empty() {
            self.send_log(
                ui_sender,
                "WARN",
                &format!("httpx: No HTTP services found on {}", target),
            );
        } else {
            self.send_log(
                ui_sender,
                "INFO",
                &format!(
                    "✓ httpx: Discovered {} HTTP services on {}",
                    all_discoveries.len(),
                    target
                ),
            );
        }
        Ok(all_discoveries)
    }

    /// Parse comprehensive dnsx output for all DNS record types
    fn parse_dnsx_comprehensive_output(&self, output: &str) -> Vec<(String, String)> {
        let mut results = Vec::new();
        
        // Regex patterns for different DNS record types
        let a_regex = Regex::new(r"^([^\s]+)\s+\[A\]\s+\[([^\]]+)\]").unwrap();
        let aaaa_regex = Regex::new(r"^([^\s]+)\s+\[AAAA\]\s+\[([^\]]+)\]").unwrap();
        let cname_regex = Regex::new(r"^([^\s]+)\s+\[CNAME\]\s+\[([^\]]+)\]").unwrap();
        let mx_regex = Regex::new(r"^([^\s]+)\s+\[MX\]\s+\[([^\]]+)\]").unwrap();
        let ns_regex = Regex::new(r"^([^\s]+)\s+\[NS\]\s+\[([^\]]+)\]").unwrap();
        let txt_regex = Regex::new(r"^([^\s]+)\s+\[TXT\]\s+\[([^\]]+)\]").unwrap();
        let soa_regex = Regex::new(r"^([^\s]+)\s+\[SOA\]\s+\[([^\]]+)\]").unwrap();

        for line in output.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            // Parse A records - extract IP for host mapping
            if let Some(captures) = a_regex.captures(line) {
                let domain = captures.get(1).unwrap().as_str().to_string();
                let ip = captures.get(2).unwrap().as_str().to_string();
                results.push((domain, ip));
            }
            // Parse AAAA records - extract IPv6 for host mapping
            else if let Some(captures) = aaaa_regex.captures(line) {
                let domain = captures.get(1).unwrap().as_str().to_string();
                let ipv6 = captures.get(2).unwrap().as_str().to_string();
                results.push((domain, ipv6));
            }
            // Parse CNAME records - resolve canonical names
            else if let Some(captures) = cname_regex.captures(line) {
                let domain = captures.get(1).unwrap().as_str().to_string();
                let canonical = captures.get(2).unwrap().as_str().trim_end_matches('.');
                // For CNAME, we'll try to resolve the canonical name later
                // For now, just store the mapping
                results.push((domain, format!("CNAME:{}", canonical)));
            }
            // Parse MX records - mail servers might have A records
            else if let Some(captures) = mx_regex.captures(line) {
                let domain = captures.get(1).unwrap().as_str().to_string();
                let mx_record = captures.get(2).unwrap().as_str();
                // Extract hostname from MX record (format: "priority hostname")
                if let Some(hostname) = mx_record.split_whitespace().nth(1) {
                    let hostname = hostname.trim_end_matches('.');
                    results.push((domain, format!("MX:{}", hostname)));
                }
            }
            // Parse NS records - nameservers
            else if let Some(captures) = ns_regex.captures(line) {
                let domain = captures.get(1).unwrap().as_str().to_string();
                let nameserver = captures.get(2).unwrap().as_str().trim_end_matches('.');
                results.push((domain, format!("NS:{}", nameserver)));
            }
            // Parse TXT records for subdomain hints
            else if let Some(captures) = txt_regex.captures(line) {
                let domain = captures.get(1).unwrap().as_str().to_string();
                let txt_data = captures.get(2).unwrap().as_str();
                // Look for subdomain hints in TXT records
                if txt_data.contains("v=spf1") || txt_data.contains("google-site-verification") {
                    results.push((domain, format!("TXT:{}", txt_data)));
                }
            }
            // Parse SOA records
            else if let Some(captures) = soa_regex.captures(line) {
                let domain = captures.get(1).unwrap().as_str().to_string();
                let soa_data = captures.get(2).unwrap().as_str();
                results.push((domain, format!("SOA:{}", soa_data)));
            }
        }
        results
    }

    /// Parse dnsx reverse DNS output
    fn parse_dnsx_reverse_output(&self, output: &str, target_ip: &str) -> Vec<(String, String)> {
        let mut results = Vec::new();
        let ptr_regex = Regex::new(r"^[^\s]+\s+\[PTR\]\s+(.+)$").unwrap();

        for line in output.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            if let Some(captures) = ptr_regex.captures(line) {
                let domain = captures.get(1).unwrap().as_str().trim_end_matches('.');
                results.push((domain.to_string(), target_ip.to_string()));
            }
        }
        results
    }

    /// Parse comprehensive httpx output with technology detection
    fn parse_httpx_comprehensive_output(&self, output: &str) -> Vec<(String, String, String)> {
        let mut results = Vec::new();
        
        // Enhanced regex to capture URL, IP, status, title, and tech
        let httpx_regex = Regex::new(r"(https?://[^\s\[]+)(?:\s+\[([^\]]+)\])?(?:\s+\[(\d+)\])?(?:\s+\[([^\]]+)\])?(?:\s+\[([^\]]+)\])?.*").unwrap();
        
        for line in output.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            if let Some(captures) = httpx_regex.captures(line) {
                let url = captures.get(1).unwrap().as_str();
                
                // Extract hostname from URL
                if let Ok(parsed_url) = url::Url::parse(url) {
                    if let Some(host) = parsed_url.host_str() {
                        let mut ip = String::new();
                        let mut tech_info = String::new();
                        
                        // Parse captured groups for IP and tech info
                        for i in 2..=5 {
                            if let Some(group) = captures.get(i) {
                                let group_str = group.as_str();
                                
                                // Check if it's an IP address
                                if group_str.parse::<std::net::IpAddr>().is_ok() {
                                    ip = group_str.to_string();
                                }
                                // Check if it contains technology info
                                else if group_str.contains(":") || 
                                       group_str.to_lowercase().contains("apache") ||
                                       group_str.to_lowercase().contains("nginx") ||
                                       group_str.to_lowercase().contains("cloudflare") {
                                    if !tech_info.is_empty() {
                                        tech_info.push_str(", ");
                                    }
                                    tech_info.push_str(group_str);
                                }
                                // HTTP status codes
                                else if group_str.parse::<u16>().is_ok() {
                                    if !tech_info.is_empty() {
                                        tech_info.push_str(", ");
                                    }
                                    tech_info.push_str(&format!("Status:{}", group_str));
                                }
                            }
                        }
                        
                        results.push((host.to_string(), ip, tech_info));
                    }
                }
            }
        }
        results
    }

    /// Create backup of /etc/hosts file
    fn backup_hosts_file(&self, ui_sender: &mpsc::UnboundedSender<UiEvent>) -> Result<String> {
        let backup_dir = dirs::config_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("~"))
            .join("ipcrawler")
            .join("backups");

        std::fs::create_dir_all(&backup_dir)?;

        let timestamp = Utc::now().format("%Y-%m-%d-%H-%M-%S");
        let backup_path = backup_dir.join(format!("hosts.backup.{}", timestamp));

        fs::copy("/etc/hosts", &backup_path)?;

        let backup_path_str = backup_path.to_string_lossy().to_string();
        self.send_log(
            ui_sender,
            "INFO",
            &format!("Created hosts backup: {}", backup_path_str),
        );
        Ok(backup_path_str)
    }

    /// Write discovered hosts to /etc/hosts file
    fn write_to_hosts_file(
        &self,
        discoveries: &[(String, String)],
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
    ) -> Result<()> {
        if discoveries.is_empty() {
            return Ok(());
        }

        // Create backup first
        let backup_path = self.backup_hosts_file(ui_sender)?;

        // Read existing hosts file
        let hosts_content = fs::read_to_string("/etc/hosts")?;
        let existing_domains: HashSet<String> = hosts_content
            .lines()
            .filter_map(|line| {
                if !line.trim().is_empty() && !line.trim().starts_with('#') {
                    line.split_whitespace().nth(1).map(|s| s.to_string())
                } else {
                    None
                }
            })
            .collect();

        // Prepare new entries
        let mut new_entries = Vec::new();
        for (domain, ip) in discoveries {
            if !existing_domains.contains(domain) && !domain.is_empty() && !ip.is_empty() {
                new_entries.push(format!("{:<15} {}", ip, domain));
            }
        }

        if new_entries.is_empty() {
            self.send_log(
                ui_sender,
                "INFO",
                "No new hosts to add - all discoveries already exist",
            );
            return Ok(());
        }

        // Append new entries to hosts file
        let mut updated_content = hosts_content;
        updated_content.push_str("\n# IPCrawler discoveries\n");
        for entry in &new_entries {
            updated_content.push_str(&format!("{}\n", entry));
        }

        fs::write("/etc/hosts", updated_content)?;

        self.send_log(
            ui_sender,
            "INFO",
            &format!(
                "✓ Added {} entries to /etc/hosts (backup: {})",
                new_entries.len(),
                backup_path
            ),
        );

        Ok(())
    }

    /// Display discoveries in UI when no sudo privileges
    fn display_discoveries(
        &self,
        discoveries: &[(String, String)],
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
    ) {
        if discoveries.is_empty() {
            self.send_log(ui_sender, "INFO", "No hosts discovered");
            return;
        }

        self.send_log(
            ui_sender,
            "WARN",
            "⚠ No sudo privileges - displaying discovered hosts:",
        );

        self.send_log(
            ui_sender,
            "INFO",
            "📋 Discovered Hosts (add manually to /etc/hosts):",
        );

        for (domain, ip) in discoveries {
            self.send_log(ui_sender, "INFO", &format!("{:<15} {}", ip, domain));
        }
    }

    /// Run wildcard detection for domain enumeration
    async fn run_wildcard_detection(
        &self,
        target: &str,
        ui_sender: &mpsc::UnboundedSender<UiEvent>,
        config: &GlobalConfig,
    ) -> Result<bool> {
        self.send_log(
            ui_sender,
            "INFO",
            &format!("Checking for wildcard DNS on {}", target),
        );

        let (command, timeout) = if let Some(ref tools) = config.tools {
            if let Some(ref hosts_config) = &tools.hosts_discovery {
                (
                    hosts_config.dnsx.command.clone(),
                    hosts_config.dnsx.timeout_ms,
                )
            } else {
                ("dnsx".to_string(), 15000)
            }
        } else {
            ("dnsx".to_string(), 15000)
        };

        // Test random subdomains to detect wildcards
        let random_subdomains = vec![
            format!("randomtest12345.{}", target),
            format!("nonexistentabcd.{}", target),
            format!("shouldnotexist9999.{}", target),
        ];

        let args = vec!["-silent", "-resp", "-a", "-nc"];
        let test_input = random_subdomains.join("\n");

        match self.execute_with_stdin(&command, &args, &test_input, timeout).await {
            Ok(stdout) => {
                let has_wildcard = !stdout.trim().is_empty();
                if has_wildcard {
                    self.send_log(
                        ui_sender,
                        "WARN",
                        &format!("⚠ Wildcard DNS detected on {} - results may include false positives", target),
                    );
                } else {
                    self.send_log(
                        ui_sender,
                        "INFO",
                        &format!("✓ No wildcard DNS detected on {}", target),
                    );
                }
                Ok(has_wildcard)
            }
            Err(_) => {
                self.send_log(
                    ui_sender,
                    "INFO",
                    &format!("Wildcard detection inconclusive for {}", target),
                );
                Ok(false)
            }
        }
    }

    /// Write comprehensive plugin results to file
    fn write_comprehensive_results(
        &self,
        discoveries: &[(String, String)],
        http_tech_discoveries: &[(String, String, String)],
        scans_dir: &Path,
        target: &str,
        has_wildcard: bool,
    ) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== Comprehensive Hosts Discovery Results for {} ===\n", target));
        content.push_str(&format!("Timestamp: {}\n", Utc::now()));
        content.push_str(&format!("Wildcard DNS detected: {}\n\n", if has_wildcard { "YES" } else { "NO" }));

        if discoveries.is_empty() && http_tech_discoveries.is_empty() {
            content.push_str("No hosts or services discovered\n");
        } else {
            // DNS Discoveries section
            if !discoveries.is_empty() {
                content.push_str("=== DNS Discoveries ===\n");
                let mut a_records = Vec::new();
                let mut aaaa_records = Vec::new();
                let mut cname_records = Vec::new();
                let mut mx_records = Vec::new();
                let mut ns_records = Vec::new();
                let mut txt_records = Vec::new();
                let mut soa_records = Vec::new();
                let mut ptr_records = Vec::new();
                
                for (domain, value) in discoveries {
                    if value.parse::<std::net::Ipv4Addr>().is_ok() {
                        a_records.push((domain, value));
                    } else if value.parse::<std::net::Ipv6Addr>().is_ok() {
                        aaaa_records.push((domain, value));
                    } else if value.starts_with("CNAME:") {
                        cname_records.push((domain, value.strip_prefix("CNAME:").unwrap()));
                    } else if value.starts_with("MX:") {
                        mx_records.push((domain, value.strip_prefix("MX:").unwrap()));
                    } else if value.starts_with("NS:") {
                        ns_records.push((domain, value.strip_prefix("NS:").unwrap()));
                    } else if value.starts_with("TXT:") {
                        txt_records.push((domain, value.strip_prefix("TXT:").unwrap()));
                    } else if value.starts_with("SOA:") {
                        soa_records.push((domain, value.strip_prefix("SOA:").unwrap()));
                    } else {
                        ptr_records.push((domain, value));
                    }
                }
                
                if !a_records.is_empty() {
                    content.push_str(&format!("\nA Records ({}):\n", a_records.len()));
                    for (domain, ip) in a_records {
                        content.push_str(&format!("{:<30} -> {}\n", domain, ip));
                    }
                }
                
                if !aaaa_records.is_empty() {
                    content.push_str(&format!("\nAAAA Records ({}):\n", aaaa_records.len()));
                    for (domain, ip) in aaaa_records {
                        content.push_str(&format!("{:<30} -> {}\n", domain, ip));
                    }
                }
                
                if !cname_records.is_empty() {
                    content.push_str(&format!("\nCNAME Records ({}):\n", cname_records.len()));
                    for (domain, canonical) in cname_records {
                        content.push_str(&format!("{:<30} -> {}\n", domain, canonical));
                    }
                }
                
                if !mx_records.is_empty() {
                    content.push_str(&format!("\nMX Records ({}):\n", mx_records.len()));
                    for (domain, mx) in mx_records {
                        content.push_str(&format!("{:<30} -> {}\n", domain, mx));
                    }
                }
                
                if !ns_records.is_empty() {
                    content.push_str(&format!("\nNS Records ({}):\n", ns_records.len()));
                    for (domain, ns) in ns_records {
                        content.push_str(&format!("{:<30} -> {}\n", domain, ns));
                    }
                }
                
                if !txt_records.is_empty() {
                    content.push_str(&format!("\nTXT Records ({}):\n", txt_records.len()));
                    for (domain, txt) in txt_records {
                        content.push_str(&format!("{:<30} -> {}\n", domain, txt));
                    }
                }
                
                if !soa_records.is_empty() {
                    content.push_str(&format!("\nSOA Records ({}):\n", soa_records.len()));
                    for (domain, soa) in soa_records {
                        content.push_str(&format!("{:<30} -> {}\n", domain, soa));
                    }
                }
                
                if !ptr_records.is_empty() {
                    content.push_str(&format!("\nPTR Records ({}):\n", ptr_records.len()));
                    for (domain, ip) in ptr_records {
                        content.push_str(&format!("{:<30} -> {}\n", domain, ip));
                    }
                }
            }
            
            // HTTP Technology Discoveries section
            if !http_tech_discoveries.is_empty() {
                content.push_str(&format!("\n=== HTTP Technology Discoveries ({}) ===\n", http_tech_discoveries.len()));
                for (host, ip, tech) in http_tech_discoveries {
                    content.push_str(&format!("{:<30} -> {}", host, ip));
                    if !tech.is_empty() {
                        content.push_str(&format!(" [{}]", tech));
                    }
                    content.push('\n');
                }
            }
            
            content.push_str(&format!("\n=== Summary ===\n"));
            content.push_str(&format!("Total DNS records: {}\n", discoveries.len()));
            content.push_str(&format!("Total HTTP services: {}\n", http_tech_discoveries.len()));
            content.push_str(&format!("Wildcard DNS: {}\n", if has_wildcard { "Detected" } else { "Not detected" }));
        }

        let result_file = scans_dir.join("hosts_discovery_comprehensive.txt");
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        Ok(())
    }
}

#[async_trait]
impl PortScan for HostsDiscoveryPlugin {
    fn name(&self) -> &'static str {
        "hosts_discovery"
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
            &format!("Starting hosts discovery for target: {}", target),
        );

        if !self.validate_target(target) {
            let error_msg = format!("Invalid target '{}' for hosts discovery", target);
            self.send_log(ui_sender, "ERROR", &error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }

        let mut all_discoveries = Vec::new();
        let is_ip = target.parse::<std::net::IpAddr>().is_ok();

        // Run comprehensive discovery tools based on target type
        let mut http_tech_discoveries = Vec::new();
        
        if is_ip {
            // For IP targets: comprehensive reverse DNS + HTTP discovery
            
            let reverse_results = self.run_dnsx_reverse(target, ui_sender, config).await?;
            all_discoveries.extend(reverse_results.clone());

            let http_results = self.run_httpx_comprehensive(target, ui_sender, config).await?;
            for (host, ip, tech) in http_results {
                all_discoveries.push((host.clone(), ip.clone()));
                http_tech_discoveries.push((host, ip, tech));
            }
            
            // Try to resolve any discovered hostnames for comprehensive DNS enum
            for (domain, _) in &reverse_results {
                if !domain.contains("CNAME:") && !domain.contains("MX:") && !domain.contains("NS:") {
                    // Running DNS enum on discovered domain
                    let dns_results = self.run_dnsx_comprehensive(domain, ui_sender, config).await?;
                    all_discoveries.extend(dns_results);
                }
            }
        } else {
            // For domain targets: comprehensive DNS enumeration + HTTP discovery
            
            let dns_results = self.run_dnsx_comprehensive(target, ui_sender, config).await?;
            
            // Separate A/AAAA records (real IPs) from other records
            let mut real_ips = HashSet::new();
            let mut dns_mappings = Vec::new();
            
            for (domain, value) in dns_results {
                if value.parse::<std::net::IpAddr>().is_ok() {
                    // Real IP address mapping
                    real_ips.insert(value.clone());
                    dns_mappings.push((domain.clone(), value.clone()));
                } else if value.starts_with("CNAME:") {
                    // Follow CNAME chains
                    let canonical = value.strip_prefix("CNAME:").unwrap();
                    let cname_results = self.run_dnsx_comprehensive(canonical, ui_sender, config).await?;
                    dns_mappings.extend(cname_results);
                } else if value.starts_with("MX:") || value.starts_with("NS:") {
                    // Resolve MX and NS hostnames
                    let hostname = value.split(':').nth(1).unwrap_or("");
                    if !hostname.is_empty() {
                        let mx_results = self.run_dnsx_comprehensive(hostname, ui_sender, config).await?;
                        dns_mappings.extend(mx_results);
                    }
                }
                // Store all discoveries
                all_discoveries.push((domain, value));
            }
            
            all_discoveries.extend(dns_mappings);
            
            // Run HTTP discovery on all discovered IPs and the original target
            let mut targets_to_scan = vec![target.to_string()];
            targets_to_scan.extend(real_ips.into_iter());
            
            for scan_target in targets_to_scan {
                let http_results = self.run_httpx_comprehensive(&scan_target, ui_sender, config).await?;
                for (host, ip, tech) in http_results {
                    all_discoveries.push((host.clone(), ip.clone()));
                    http_tech_discoveries.push((host, ip, tech));
                }
            }
        }

        // Remove duplicates and log discovery summary
        let mut unique_discoveries = Vec::new();
        let mut seen = HashSet::new();
        for (domain, ip) in all_discoveries {
            let key = format!("{}:{}", domain, ip);
            if !seen.contains(&key) {
                seen.insert(key);
                unique_discoveries.push((domain, ip));
            }
        }
        
        self.send_log(
            ui_sender,
            "INFO",
            &format!(
                "Discovery phase completed: {} unique DNS records, {} HTTP tech discoveries",
                unique_discoveries.len(),
                http_tech_discoveries.len()
            ),
        );

        // Handle discoveries based on sudo privileges
        if self.check_sudo_privileges() {
            if let Err(e) = self.write_to_hosts_file(&unique_discoveries, ui_sender) {
                self.send_log(
                    ui_sender,
                    "ERROR",
                    &format!("Failed to write to /etc/hosts: {}", e),
                );
                self.display_discoveries(&unique_discoveries, ui_sender);
            }
        } else {
            self.display_discoveries(&unique_discoveries, ui_sender);
        }

        // Check for wildcard DNS if target is a domain
        let has_wildcard = if !is_ip {
            self.run_wildcard_detection(target, ui_sender, config).await.unwrap_or(false)
        } else {
            false
        };
        
        // Write comprehensive results to scan files
        if let Err(e) = self.write_comprehensive_results(&unique_discoveries, &http_tech_discoveries, &dirs.scans, target, has_wildcard) {
            self.send_log(
                ui_sender,
                "WARN",
                &format!("Failed to write comprehensive hosts discovery results: {}", e),
            );
        }

        // Create service objects for discovered hosts and send enhanced results to UI
        let mut services = Vec::new();
        let mut processed_hosts = HashSet::new();
        
        // Process regular host discoveries
        for (domain, ip) in &unique_discoveries {
            let host_key = format!("{}:{}", domain, ip);
            if processed_hosts.contains(&host_key) {
                continue;
            }
            processed_hosts.insert(host_key.clone());
            
            // Skip non-IP mappings for service creation
            if ip.parse::<std::net::IpAddr>().is_err() && 
               !ip.starts_with("CNAME:") && !ip.starts_with("MX:") && 
               !ip.starts_with("NS:") && !ip.starts_with("TXT:") && 
               !ip.starts_with("SOA:") {
                continue;
            }
            
            // Determine service type and create display info matching dig/nslookup format
            let (port, service_name, result_display) = if ip.starts_with("CNAME:") {
                let canonical = ip.strip_prefix("CNAME:").unwrap();
                (53, format!("DNS_CNAME_{}", domain.to_uppercase()), format!("hosts_discovery CNAME - {} -> {}", domain, canonical))
            } else if ip.starts_with("MX:") {
                let mx_server = ip.strip_prefix("MX:").unwrap();
                (25, format!("MAIL_{}", domain.to_uppercase()), format!("hosts_discovery MX - {} -> {}", domain, mx_server))
            } else if ip.starts_with("NS:") {
                let nameserver = ip.strip_prefix("NS:").unwrap();
                (53, format!("DNS_NS_{}", domain.to_uppercase()), format!("hosts_discovery NS - {} -> {}", domain, nameserver))
            } else if ip.starts_with("TXT:") {
                let txt_content = ip.strip_prefix("TXT:").unwrap();
                let truncated_txt = if txt_content.len() > 50 {
                    format!("{}...", &txt_content[..47])
                } else {
                    txt_content.to_string()
                };
                (53, format!("DNS_TXT_{}", domain.to_uppercase()), format!("hosts_discovery TXT - {}: {}", domain, truncated_txt))
            } else if ip.starts_with("SOA:") {
                let soa_content = ip.strip_prefix("SOA:").unwrap();
                let truncated_soa = if soa_content.len() > 50 {
                    format!("{}...", &soa_content[..47])
                } else {
                    soa_content.to_string()
                };
                (53, format!("DNS_SOA_{}", domain.to_uppercase()), format!("hosts_discovery SOA - {}: {}", domain, truncated_soa))
            } else {
                (80, format!("HOST_{}", domain.to_uppercase()), format!("hosts_discovery A - {} -> {}", domain, ip))
            };
            
            let service = Service {
                proto: if port == 53 { Proto::Udp } else { Proto::Tcp },
                port,
                name: service_name,
                secure: false,
                address: if ip.parse::<std::net::IpAddr>().is_ok() { ip.clone() } else { domain.clone() },
            };
            services.push(service);

            // Send to Results panel with proper formatting
            let _ = ui_sender.send(UiEvent::PortDiscovered {
                port,
                service: result_display,
            });
        }
        
        // Process HTTP technology discoveries with enhanced information
        for (host, ip, tech) in &http_tech_discoveries {
            if ip.is_empty() {
                continue;
            }
            
            let host_key = format!("{}:{}:tech", host, ip);
            if processed_hosts.contains(&host_key) {
                continue;
            }
            processed_hosts.insert(host_key);
            
            let service = Service {
                proto: Proto::Tcp,
                port: 443, // HTTPS for technology detection
                name: format!("HTTP_TECH_{}", host.to_uppercase()),
                secure: true,
                address: ip.clone(),
            };
            services.push(service);

            // Format HTTP tech info for Results panel matching other plugins
            let result_display = if tech.is_empty() {
                format!("hosts_discovery HTTP - {} -> {}", host, ip)
            } else {
                format!("hosts_discovery HTTP - {} -> {} [{}]", host, ip, tech)
            };
            
            let _ = ui_sender.send(UiEvent::PortDiscovered {
                port: 443,
                service: result_display,
            });
        }

        if unique_discoveries.is_empty() && http_tech_discoveries.is_empty() {
            self.send_log(ui_sender, "WARN", "No hosts or services discovered");
        } else {
            self.send_log(
                ui_sender,
                "INFO",
                &format!(
                    "Comprehensive discovery completed. Found {} DNS records, {} HTTP services{}",
                    unique_discoveries.len(),
                    http_tech_discoveries.len(),
                    if has_wildcard { " (wildcard DNS detected)" } else { "" }
                ),
            );
        }

        Ok(services)
    }
}
