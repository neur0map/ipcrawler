use async_trait::async_trait;
use anyhow::Result;
use regex::Regex;
use crate::core::{models::{Service, Proto}, state::RunState};
use crate::executors::command::execute;
use crate::plugins::types::PortScan;
use crate::config::{GlobalConfig, PortStrategy};

#[derive(Clone)]
pub struct NmapPortScan;

impl NmapPortScan {
    fn write_plugin_results(&self, results: &[(Service, (u16, String))], scans_dir: &std::path::Path) -> Result<()> {
        let mut content = String::new();
        content.push_str(&format!("=== {} Results ===\n", self.name()));
        content.push_str(&format!("Found {} open ports:\n\n", results.len()));
        
        for (service, (port, name)) in results {
            content.push_str(&format!(
                "Port {}: {} ({:?}){}\n",
                port,
                name,
                service.proto,
                if service.secure { " [SSL/TLS]" } else { "" }
            ));
        }
        
        content.push_str(&format!("\nTimestamp: {}\n", chrono::Utc::now()));
        
        let result_file = scans_dir.join("nmap_results.txt");
        crate::utils::fs::atomic_write(result_file, content.as_bytes())?;
        
        Ok(())
    }
}

#[async_trait]
impl crate::plugins::types::PortScan for NmapPortScan {
    fn name(&self) -> &'static str {
        "nmap_portscan"
    }

    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>> {
        let target = &state.target;
        let dirs = state.dirs.as_ref().unwrap();
        let output_file = dirs.scans.join("nmap.xml");
        
        // Create the output file path relative to the working directory
        let mut args = config.tools.nmap.base_args.clone();
        
        // Add port specification based on strategy
        match config.tools.nmap.port_strategy {
            PortStrategy::Top => {
                if let Some(top_ports) = config.tools.nmap.ports.top_ports {
                    args.extend(vec![
                        "--top-ports".to_string(),
                        top_ports.to_string(),
                    ]);
                }
            },
            PortStrategy::Range => {
                if let (Some(start), Some(end)) = (config.tools.nmap.ports.range_start, config.tools.nmap.ports.range_end) {
                    args.extend(vec![
                        "-p".to_string(),
                        format!("{}-{}", start, end),
                    ]);
                }
            },
            PortStrategy::List => {
                if let Some(ports) = &config.tools.nmap.ports.specific_ports {
                    let port_list = ports.iter()
                        .map(|p| p.to_string())
                        .collect::<Vec<_>>()
                        .join(",");
                    args.extend(vec![
                        "-p".to_string(),
                        port_list,
                    ]);
                }
            },
            PortStrategy::Default => {
                // Use nmap's default port selection
            }
        }
        
        // Add timing template
        args.push(format!("-{}", config.tools.nmap.options.timing_template));
        
        // Add output format
        if config.tools.nmap.options.output_format == "xml" {
            args.extend(vec!["-oX".to_string(), "nmap.xml".to_string()]);
        }
        
        // Add optional features
        if config.tools.nmap.options.os_detection {
            args.push("-O".to_string());
        }
        
        if config.tools.nmap.options.script_scan {
            args.push("-sC".to_string());
        }
        
        // Use stealth mode if configured and available
        if config.tools.nmap.options.stealth_mode {
            // Replace -sT with -sS if stealth mode is requested
            if let Some(pos) = args.iter().position(|x| x == "-sT") {
                args[pos] = "-sS".to_string();
                tracing::warn!("Stealth mode (-sS) requires root privileges");
            }
        }
        
        args.push(target.to_string());
        
        // Convert to &str for execute function
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        let command = &config.tools.nmap.command;
        let timeout = Some(config.tools.nmap.limits.timeout_ms);
        let _result = execute(command, &args_str, &dirs.scans, timeout).await?;
        
        // Parse XML output and generate per-plugin results
        let xml_content = std::fs::read_to_string(&output_file)?;
        let results = parse_nmap_xml(&xml_content, target)?;
        
        // Write individual plugin result file
        self.write_plugin_results(&results, &dirs.scans)?;
        
        let mut services = Vec::new();
        for (service, (port, name)) in results {
            // Trigger PortDiscovered event
            use crate::core::events::Event;
            state.on_event(Event::PortDiscovered(port, name));
            services.push(service);
        }
        
        Ok(services)
    }
}

fn parse_nmap_xml(xml: &str, target: &str) -> Result<Vec<(Service, (u16, String))>> {
    let mut services = Vec::new();
    
    // Parse open ports with regex - handle multiline XML
    let port_re = Regex::new(r#"(?s)<port protocol="(\w+)" portid="(\d+)">.*?<state state="open".*?(?:<service name="([^"]+)".*?)?</port>"#)?;
    
    for cap in port_re.captures_iter(xml) {
        let proto = match &cap[1] {
            "tcp" => Proto::Tcp,
            "udp" => Proto::Udp,
            _ => continue,
        };
        
        let port: u16 = cap[2].parse()?;
        let name = cap.get(3)
            .map(|m| m.as_str().to_string())
            .unwrap_or_else(|| format!("port-{}", port));
        
        let secure = name.ends_with("s") || name.contains("ssl") || 
                     name.contains("tls") || port == 443 || port == 8443;
        
        let service = Service {
            proto,
            port,
            name: name.clone(),
            secure,
            address: target.to_string(),
        };
        
        let port_info = (port, name);
        
        services.push((service, port_info));
    }
    
    Ok(services)
}
