use async_trait::async_trait;
use anyhow::Result;
use crate::core::{models::{Service, Proto}, state::RunState, events::Event};
use crate::plugins::types::PortScan;
use crate::config::GlobalConfig;
use crate::executors::command::execute;
use std::collections::HashSet;

#[derive(Clone)]
pub struct DnsEnum;

#[async_trait]
impl PortScan for DnsEnum {
    fn name(&self) -> &'static str {
        "dns_enum"
    }

    async fn run(&self, state: &mut RunState, config: &GlobalConfig) -> Result<Vec<Service>> {
        let target = state.target.clone();
        let dirs = state.dirs.as_ref().unwrap().clone();
        
        tracing::info!("Starting DNS enumeration for {}", target);
        
        let mut services = Vec::new();
        let mut discovered_hosts = HashSet::new();
        
        // First, try basic DNS lookups
        services.extend(self.basic_dns_lookup(&target, state, config, &dirs.scans).await?);
        
        // Then try subdomain enumeration if enabled
        if config.tools.dns_enum.options.subdomain_enum {
            services.extend(self.subdomain_enumeration(&target, state, config, &dirs.scans, &mut discovered_hosts).await?);
        }
        
        // Try zone transfer if enabled
        if config.tools.dns_enum.options.zone_transfer {
            services.extend(self.zone_transfer_attempt(&target, state, config, &dirs.scans).await?);
        }
        
        Ok(services)
    }
}

impl DnsEnum {
    async fn basic_dns_lookup(&self, target: &str, state: &mut RunState, config: &GlobalConfig, scans_dir: &std::path::Path) -> Result<Vec<Service>> {
        let mut services = Vec::new();
        let _output_file = scans_dir.join(format!("dns_basic_{}.txt", target));
        
        // DNS record types to query
        let record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"];
        
        for record_type in &record_types {
            let args = vec![
                "+short",
                "-t", record_type,
                target,
            ];
            
            let timeout = Some(config.tools.dns_enum.limits.timeout_ms);
            
            match execute("dig", &args, scans_dir, timeout).await {
                Ok(_) => {
                    tracing::debug!("DNS {} lookup successful for {}", record_type, target);
                }
                Err(e) => {
                    tracing::debug!("DNS {} lookup failed for {}: {}", record_type, target, e);
                }
            }
        }
        
        // Check if port 53 is open (DNS service)
        let dns_server = format!("@{}", target);
        let dns_check_args = vec![
            "+short",
            "+time=3",
            "+tries=1",
            dns_server.as_str(),
            "google.com",
        ];
        let timeout = Some(5000); // 5 second timeout for DNS check
        
        match execute("dig", &dns_check_args, scans_dir, timeout).await {
            Ok(_) => {
                // DNS server responded, port 53 is likely open
                state.on_event(Event::PortDiscovered(53, "dns".to_string()));
                
                let service = Service {
                    proto: Proto::Udp,
                    port: 53,
                    name: "dns".to_string(),
                    secure: false,
                    address: target.to_string(),
                };
                services.push(service);
                
                tracing::info!("DNS service detected on port 53 for {}", target);
            }
            Err(_) => {
                tracing::debug!("No DNS service detected on port 53 for {}", target);
            }
        }
        
        Ok(services)
    }
    
    async fn subdomain_enumeration(&self, target: &str, _state: &mut RunState, _config: &GlobalConfig, scans_dir: &std::path::Path, discovered_hosts: &mut HashSet<String>) -> Result<Vec<Service>> {
        let services = Vec::new();
        let _output_file = scans_dir.join(format!("dns_subdomains_{}.txt", target));
        
        // Common subdomains for CTF
        let subdomains = [
            "www", "mail", "ftp", "admin", "test", "dev", "staging", "api", 
            "app", "web", "secure", "login", "portal", "dashboard", "panel",
            "m", "mobile", "cdn", "static", "img", "images", "upload", "uploads",
            "blog", "forum", "shop", "store", "payment", "pay", "billing",
            "support", "help", "docs", "documentation", "wiki", "kb",
            "internal", "intranet", "extranet", "vpn", "remote", "ssh",
            "git", "svn", "jenkins", "ci", "build", "deploy", "prod", "production"
        ];
        
        for subdomain in &subdomains {
            let full_domain = format!("{}.{}", subdomain, target);
            
            let args = vec![
                "+short",
                "+time=2",
                "+tries=1",
                &full_domain,
            ];
            
            let timeout = Some(3000); // 3 second timeout per subdomain
            
            match execute("dig", &args, scans_dir, timeout).await {
                Ok(_) => {
                    if discovered_hosts.insert(full_domain.clone()) {
                        tracing::info!("Discovered subdomain: {}", full_domain);
                        
                        // Create a DNS result entry (not port services - those will be scanned later)
                        // This is just DNS enumeration, not port scanning
                        tracing::debug!("Found subdomain {} - will be scanned separately", full_domain);
                    }
                }
                Err(_) => {
                    // Subdomain doesn't exist, which is normal
                }
            }
        }
        
        Ok(services)
    }
    
    async fn zone_transfer_attempt(&self, target: &str, _state: &mut RunState, config: &GlobalConfig, scans_dir: &std::path::Path) -> Result<Vec<Service>> {
        let _output_file = scans_dir.join(format!("dns_zonetransfer_{}.txt", target));
        
        let dns_server = format!("@{}", target);
        let args = vec![
            "axfr",
            target,
            dns_server.as_str(),
        ];
        
        let timeout = Some(config.tools.dns_enum.limits.timeout_ms);
        
        match execute("dig", &args, scans_dir, timeout).await {
            Ok(_) => {
                tracing::info!("Zone transfer succeeded for {} (potential misconfiguration!)", target);
            }
            Err(_) => {
                tracing::debug!("Zone transfer failed for {} (expected behavior)", target);
            }
        }
        
        // Zone transfer doesn't typically create new services, but logs the attempt
        Ok(Vec::new())
    }
}
