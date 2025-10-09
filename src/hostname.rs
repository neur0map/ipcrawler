use anyhow::Result;
use std::collections::HashSet;
use std::net::IpAddr;
use std::process::Command;
use tracing::{debug, info, warn};

/// Extracts hostnames from various tool outputs
pub struct HostnameExtractor;

impl HostnameExtractor {
    /// Extract hostnames from nmap output
    pub fn from_nmap(output: &str) -> Vec<String> {
        let mut hostnames = HashSet::new();

        // Extract from SSL certificates (CN and Subject Alternative Names)
        for line in output.lines() {
            // Common Name (CN)
            if let Some(cn) = line.strip_prefix("| Subject: ") {
                if let Some(domain) = Self::extract_cn(cn) {
                    hostnames.insert(domain);
                }
            }
            
            // Subject Alternative Names
            if line.contains("Subject Alternative Name:") || line.contains("DNS:") {
                for domain in Self::extract_sans(line) {
                    hostnames.insert(domain);
                }
            }

            // HTTP Host headers
            if line.contains("Host:") || line.contains("host:") {
                if let Some(host) = Self::extract_http_host(line) {
                    hostnames.insert(host);
                }
            }

            // Reverse DNS
            if line.contains("domain name pointer") {
                if let Some(ptr) = Self::extract_ptr(line) {
                    hostnames.insert(ptr);
                }
            }
        }

        hostnames.into_iter().collect()
    }

    /// Extract hostnames from host/dig output
    pub fn from_reverse_dns(output: &str) -> Vec<String> {
        let mut hostnames = HashSet::new();

        for line in output.lines() {
            let line = line.trim();
            
            // host command: "1.2.3.4.in-addr.arpa domain name pointer example.com."
            if line.contains("domain name pointer") {
                if let Some(ptr) = Self::extract_ptr(line) {
                    hostnames.insert(ptr);
                }
            }
            
            // dig command: PTR records
            if line.contains("PTR") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if let Some(hostname) = parts.last() {
                    let clean = hostname.trim_end_matches('.');
                    if Self::is_valid_hostname(clean) {
                        hostnames.insert(clean.to_string());
                    }
                }
            }
            
            // dig command: A records (for reverse lookup showing original hostname)
            // Example: "example.com.    300    IN    A    93.184.216.34"
            if line.contains(" IN A ") || line.contains(" IN AAAA ") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if let Some(first) = parts.first() {
                    let hostname = first.trim_end_matches('.');
                    if Self::is_valid_hostname(hostname) {
                        hostnames.insert(hostname.to_string());
                    }
                }
            }
            
            // dig command: MX records contain mail server hostnames
            // Example: "example.com.    300    IN    MX    10 mail.example.com."
            if line.contains(" IN MX ") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() >= 5 {
                    // MX record format: domain TTL IN MX priority mailserver
                    if let Some(mailserver) = parts.last() {
                        let hostname = mailserver.trim_end_matches('.');
                        if Self::is_valid_hostname(hostname) {
                            hostnames.insert(hostname.to_string());
                        }
                    }
                }
            }
            
            // dig command: NS records contain nameserver hostnames
            // Example: "example.com.    300    IN    NS    ns1.example.com."
            if line.contains(" IN NS ") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if let Some(nameserver) = parts.last() {
                    let hostname = nameserver.trim_end_matches('.');
                    if Self::is_valid_hostname(hostname) {
                        hostnames.insert(hostname.to_string());
                    }
                }
            }
            
            // dig command: CNAME records
            // Example: "www.example.com.    300    IN    CNAME    example.com."
            if line.contains(" IN CNAME ") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                // Get both source and target of CNAME
                if let Some(first) = parts.first() {
                    let hostname = first.trim_end_matches('.');
                    if Self::is_valid_hostname(hostname) {
                        hostnames.insert(hostname.to_string());
                    }
                }
                if let Some(target) = parts.last() {
                    let hostname = target.trim_end_matches('.');
                    if Self::is_valid_hostname(hostname) {
                        hostnames.insert(hostname.to_string());
                    }
                }
            }
        }

        hostnames.into_iter().collect()
    }

    /// Extract CN from SSL certificate subject
    fn extract_cn(subject: &str) -> Option<String> {
        for part in subject.split(',') {
            let part = part.trim();
            if let Some(cn) = part.strip_prefix("CN=") {
                let cn = cn.trim();
                if Self::is_valid_hostname(cn) {
                    return Some(cn.to_string());
                }
            }
        }
        None
    }

    /// Extract Subject Alternative Names from certificate
    fn extract_sans(line: &str) -> Vec<String> {
        let mut domains = Vec::new();
        
        // Look for DNS: entries
        for part in line.split(',') {
            if let Some(dns) = part.trim().strip_prefix("DNS:") {
                let domain = dns.trim();
                if Self::is_valid_hostname(domain) {
                    domains.push(domain.to_string());
                }
            }
        }
        
        domains
    }

    /// Extract hostname from HTTP Host header
    fn extract_http_host(line: &str) -> Option<String> {
        if let Some(host_part) = line.split("Host:").nth(1) {
            let host = host_part.split_whitespace().next()?.trim();
            // Remove port if present
            let host = host.split(':').next()?;
            if Self::is_valid_hostname(host) {
                return Some(host.to_string());
            }
        }
        None
    }

    /// Extract hostname from PTR record
    fn extract_ptr(line: &str) -> Option<String> {
        if let Some(ptr_part) = line.split("domain name pointer").nth(1) {
            let hostname = ptr_part.trim().trim_end_matches('.');
            if Self::is_valid_hostname(hostname) {
                return Some(hostname.to_string());
            }
        }
        None
    }

    /// Check if string is a valid hostname (not IP, not empty, contains dot)
    fn is_valid_hostname(s: &str) -> bool {
        if s.is_empty() || s.len() > 253 {
            return false;
        }

        // Skip if it's an IP address
        if s.parse::<IpAddr>().is_ok() {
            return false;
        }

        // Should contain at least one dot (domain.tld)
        if !s.contains('.') {
            return false;
        }

        // Basic DNS name validation
        s.chars().all(|c| c.is_alphanumeric() || c == '.' || c == '-' || c == '_' || c == '*')
    }
}

/// Manages /etc/hosts file updates
pub struct HostsFileManager;

impl HostsFileManager {
    /// Add hostname entries to /etc/hosts
    pub fn add_entries(ip: &str, hostnames: &[String]) -> Result<()> {
        if hostnames.is_empty() {
            debug!("No hostnames to add to /etc/hosts");
            return Ok(());
        }

        // Check if we have sudo privileges
        let is_root = unsafe { libc::geteuid() == 0 };
        
        if !is_root {
            info!("Not running as root - skipping /etc/hosts update");
            info!("Discovered hostnames: {}", hostnames.join(", "));
            info!("To enable automatic /etc/hosts updates, run with sudo");
            return Ok(());
        }

        info!("Adding {} hostname(s) to /etc/hosts: {}", hostnames.len(), hostnames.join(", "));

        // Create backup
        let backup_cmd = Command::new("cp")
            .args(&["/etc/hosts", "/etc/hosts.ipcrawler.bak"])
            .output();
        
        if let Err(e) = backup_cmd {
            warn!("Failed to backup /etc/hosts: {}", e);
        }

        // Read current /etc/hosts
        let current = std::fs::read_to_string("/etc/hosts")
            .unwrap_or_default();

        // Check if entries already exist
        let marker = format!("# IPCrawler - {}", ip);
        let mut entries_to_add = Vec::new();
        
        for hostname in hostnames {
            // Check if hostname already exists in hosts file
            let already_exists = current.lines().any(|line| {
                !line.trim().starts_with('#') && line.contains(hostname)
            });

            if !already_exists {
                entries_to_add.push(hostname.clone());
            } else {
                debug!("Hostname '{}' already in /etc/hosts", hostname);
            }
        }

        if entries_to_add.is_empty() {
            debug!("All hostnames already in /etc/hosts");
            return Ok(());
        }

        // Append new entries
        let entry = format!("\n{}\t{}\t{}\n", marker, ip, entries_to_add.join(" "));
        
        let output = Command::new("sh")
            .arg("-c")
            .arg(format!("echo '{}' >> /etc/hosts", entry.replace('\'', "'\\''")))
            .output()?;

        if output.status.success() {
            info!("Successfully added {} hostname(s) to /etc/hosts", entries_to_add.len());
        } else {
            warn!("Failed to update /etc/hosts: {}", String::from_utf8_lossy(&output.stderr));
        }

        Ok(())
    }

    /// Remove IPCrawler entries from /etc/hosts
    pub fn cleanup(ip: &str) -> Result<()> {
        let is_root = unsafe { libc::geteuid() == 0 };
        
        if !is_root {
            return Ok(());
        }

        let marker = format!("# IPCrawler - {}", ip);
        let current = std::fs::read_to_string("/etc/hosts")?;
        
        let cleaned: Vec<&str> = current
            .lines()
            .filter(|line| !line.contains(&marker) && !line.trim().is_empty())
            .collect();

        std::fs::write("/etc/hosts", cleaned.join("\n") + "\n")?;
        info!("Cleaned up /etc/hosts entries for {}", ip);

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_cn() {
        let subject = "C=US, ST=California, O=Example Inc, CN=example.com";
        assert_eq!(
            HostnameExtractor::extract_cn(subject),
            Some("example.com".to_string())
        );
    }

    #[test]
    fn test_extract_sans() {
        let line = "| Subject Alternative Name: DNS:example.com, DNS:www.example.com, DNS:api.example.com";
        let sans = HostnameExtractor::extract_sans(line);
        assert_eq!(sans.len(), 3);
        assert!(sans.contains(&"example.com".to_string()));
    }

    #[test]
    fn test_is_valid_hostname() {
        assert!(HostnameExtractor::is_valid_hostname("example.com"));
        assert!(HostnameExtractor::is_valid_hostname("sub.example.com"));
        assert!(HostnameExtractor::is_valid_hostname("*.example.com"));
        assert!(!HostnameExtractor::is_valid_hostname("192.168.1.1"));
        assert!(!HostnameExtractor::is_valid_hostname("localhost"));
        assert!(!HostnameExtractor::is_valid_hostname(""));
    }
}
