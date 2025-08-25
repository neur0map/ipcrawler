use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::{Service, Proto}, state::RunState, events::Event};
use crate::plugins::types::PortScan;
use crate::config::GlobalConfig;
use crate::executors::command::execute;
use std::collections::HashSet;

#[derive(Clone)]
pub struct NaabuPortScan;

#[async_trait]
impl PortScan for NaabuPortScan {
    fn name(&self) -> &'static str {
        "naabu_portscan"
    }

    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>> {
        let target = state.target.clone();
        let dirs = state.dirs.as_ref().unwrap().clone();
        
        tracing::info!("Starting naabu port scan for {}", target);
        
        // Naabu command arguments for fast scanning
        let output_file = dirs.scans.join(format!("naabu_{}.txt", target));
        let mut args = vec![
            "-host", &target,
            "-o", output_file.to_str().unwrap(),
            "-silent",
            "-json",
            "-rate", "1000",  // Fast scan rate
            "-c", "50",       // Concurrency
        ];
        
        // Prepare port arguments based on config
        let top_ports_str;
        let port_range_str;
        let port_list_str;
        
        match config.tools.nmap.port_strategy {
            crate::config::types::PortStrategy::Top => {
                let top_ports = config.tools.nmap.ports.top_ports.unwrap_or(1000);
                // Naabu expects specific values: full, 100, 1000
                top_ports_str = match top_ports {
                    x if x >= 1000 => "1000".to_string(),
                    x if x >= 100 => "100".to_string(),
                    _ => "100".to_string(),
                };
                args.extend(vec!["-top-ports", &top_ports_str]);
            }
            crate::config::types::PortStrategy::Range => {
                if let (Some(start), Some(end)) = (config.tools.nmap.ports.range_start, config.tools.nmap.ports.range_end) {
                    port_range_str = format!("{}-{}", start, end);
                    args.extend(vec!["-p", &port_range_str]);
                } else {
                    args.extend(vec!["-top-ports", "1000"]);
                }
            }
            crate::config::types::PortStrategy::List => {
                if let Some(port_list) = &config.tools.nmap.ports.specific_ports {
                    let ports: Vec<String> = port_list
                        .iter()
                        .map(|p| p.to_string())
                        .collect();
                    port_list_str = ports.join(",");
                    args.extend(vec!["-p", &port_list_str]);
                } else {
                    args.extend(vec!["-top-ports", "1000"]);
                }
            }
            _ => {
                args.extend(vec!["-top-ports", "1000"]);
            }
        }
        
        let timeout = Some(config.tools.naabu.limits.timeout_ms);
        
        match execute("naabu", &args, &dirs.scans, timeout).await {
            Ok(_) => {
                tracing::info!("Naabu scan completed for {}", target);
                
                // Parse naabu JSON output
                let services = self.parse_naabu_output(&output_file, &target, state).await?;
                tracing::info!("Naabu found {} open ports", services.len());
                
                Ok(services)
            }
            Err(e) => {
                tracing::error!("Naabu scan failed for {}: {}", target, e);
                Err(anyhow::anyhow!("Naabu scan failed: {}", e))
            }
        }
    }
}

impl NaabuPortScan {
    async fn parse_naabu_output(&self, output_file: &std::path::Path, target: &str, state: &mut RunState) -> Result<Vec<Service>> {
        use std::io::{BufRead, BufReader};
        use std::fs::File;
        
        if !output_file.exists() {
            return Ok(Vec::new());
        }
        
        let file = File::open(output_file)?;
        let reader = BufReader::new(file);
        let mut services = Vec::new();
        let mut seen_ports = HashSet::new();
        
        for line in reader.lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            
            // Parse JSON output from naabu
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&line) {
                if let (Some(host), Some(port)) = (json.get("host"), json.get("port")) {
                    if let (Some(host_str), Some(port_num)) = (host.as_str(), port.as_u64()) {
                        if host_str == target && port_num <= 65535 {
                            let port = port_num as u16;
                            
                            if seen_ports.insert(port) {
                                // Determine service name based on common ports
                                let service_name = match port {
                                    21 => "ftp",
                                    22 => "ssh", 
                                    23 => "telnet",
                                    25 => "smtp",
                                    53 => "dns",
                                    80 => "http",
                                    110 => "pop3",
                                    111 => "rpcbind",
                                    135 => "msrpc",
                                    139 => "netbios-ssn",
                                    143 => "imap",
                                    443 => "https",
                                    993 => "imaps",
                                    995 => "pop3s",
                                    1433 => "mssql",
                                    1723 => "pptp",
                                    3306 => "mysql",
                                    3389 => "rdp",
                                    5432 => "postgresql",
                                    5900 => "vnc",
                                    8080 => "http-proxy",
                                    8443 => "https-alt",
                                    _ => "unknown",
                                };
                                
                                // Emit port discovery event
                                state.on_event(Event::PortDiscovered(port, service_name.to_string()));
                                
                                // Create service object
                                let service = Service {
                                    proto: Proto::Tcp,
                                    port,
                                    name: service_name.to_string(),
                                    secure: port == 443 || port == 993 || port == 995 || port == 8443,
                                    address: target.to_string(),
                                };
                                
                                services.push(service);
                            }
                        }
                    }
                }
            }
        }
        
        Ok(services)
    }
}
