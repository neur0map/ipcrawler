use anyhow::Result;
use colored::Colorize;
use std::process::Command;

pub struct PreflightChecker {
    verbose: bool,
}

#[derive(Debug)]
pub struct ToolStatus {
    pub name: String,
    pub available: bool,
    pub path: Option<String>,
    pub install_suggestion: Option<String>,
}

#[derive(Debug)]
pub struct TargetStatus {
    pub reachable: bool,
    pub icmp_blocked: bool,
    pub open_ports: Vec<u16>,
}

impl PreflightChecker {
    pub fn new(verbose: bool) -> Self {
        Self { verbose }
    }

    pub fn check_tools(&self, tool_names: &[String]) -> Vec<ToolStatus> {
        let mut results = Vec::new();

        for tool_name in tool_names {
            let status = self.check_single_tool(tool_name);
            results.push(status);
        }

        results
    }

    fn check_single_tool(&self, tool_name: &str) -> ToolStatus {
        // Try to find the tool
        let path = if let Ok(output) = Command::new("which").arg(tool_name).output() {
            if output.status.success() {
                Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
            } else {
                None
            }
        } else if let Ok(output) = Command::new("where").arg(tool_name).output() {
            if output.status.success() {
                Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
            } else {
                None
            }
        } else {
            None
        };

        let available = path.is_some();
        let install_suggestion = if !available {
            Some(self.get_install_suggestion(tool_name))
        } else {
            None
        };

        ToolStatus {
            name: tool_name.to_string(),
            available,
            path,
            install_suggestion,
        }
    }

    fn get_install_suggestion(&self, tool_name: &str) -> String {
        match tool_name {
            "nmap" => "brew install nmap (macOS) or apt install nmap (Linux)".to_string(),
            "nuclei" => {
                "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest".to_string()
            }
            "nikto" => "apt install nikto or brew install nikto".to_string(),
            "gobuster" => "go install github.com/OJ/gobuster/v3@latest".to_string(),
            "ffuf" => "go install github.com/ffuf/ffuf/v2@latest".to_string(),
            "whatweb" => "apt install whatweb or brew install whatweb".to_string(),
            "ssh-audit" => "pip install ssh-audit".to_string(),
            "enum4linux-ng" => "pip install enum4linux-ng".to_string(),
            "smbmap" => "pip install smbmap".to_string(),
            "snmpwalk" => "apt install snmp or brew install net-snmp".to_string(),
            "dig" => "apt install dnsutils or brew install bind".to_string(),
            "host" => "apt install bind9-host or brew install bind".to_string(),
            "traceroute" => "apt install traceroute (usually pre-installed)".to_string(),
            _ => format!("Check documentation for {} installation", tool_name),
        }
    }

    pub async fn check_target(&self, target: &str) -> Result<TargetStatus> {
        let mut status = TargetStatus {
            reachable: false,
            icmp_blocked: true,
            open_ports: Vec::new(),
        };

        // Quick ICMP check
        if self.verbose {
            println!("  {} Testing ICMP...", "→".cyan());
        }

        let ping_result = tokio::time::timeout(
            std::time::Duration::from_secs(3),
            tokio::process::Command::new("ping")
                .args(["-c", "1", "-W", "1", target])
                .output(),
        )
        .await;

        if let Ok(Ok(output)) = ping_result {
            if output.status.success() {
                status.reachable = true;
                status.icmp_blocked = false;
            }
        }

        // Quick port scan for common ports
        if self.verbose {
            println!("  {} Testing common ports...", "→".cyan());
        }

        let common_ports = vec![80, 443, 22, 21, 25, 3306, 8080, 8443];
        for port in common_ports {
            if self.is_port_open(target, port).await {
                status.open_ports.push(port);
                status.reachable = true;
            }
        }

        Ok(status)
    }

    async fn is_port_open(&self, target: &str, port: u16) -> bool {
        let addr = format!("{}:{}", target, port);
        tokio::time::timeout(
            std::time::Duration::from_millis(500),
            tokio::net::TcpStream::connect(addr),
        )
        .await
        .is_ok()
    }

    pub fn display_tool_results(&self, results: &[ToolStatus]) {
        println!("\n{}", "Tool Availability Check:".cyan().bold());

        let mut available = 0;
        let mut missing = 0;

        for status in results {
            if status.available {
                available += 1;
                println!(
                    "  {} {} {}",
                    "✓".green(),
                    status.name.green().bold(),
                    status.path.as_ref().unwrap().dimmed()
                );
            } else {
                missing += 1;
                println!("  {} {}", "✗".red(), status.name.red().bold());
                if let Some(suggestion) = &status.install_suggestion {
                    println!("     {} {}", "💡".yellow(), suggestion.dimmed());
                }
            }
        }

        println!(
            "\n  Summary: {} available, {} missing",
            available.to_string().green(),
            missing.to_string().red()
        );
    }

    pub fn display_target_results(&self, target: &str, status: &TargetStatus) {
        println!("\n{}", "Target Reachability Check:".cyan().bold());
        println!("  Target: {}", target.yellow());

        if !status.reachable {
            println!("  {} Host appears unreachable", "✗".red());
            println!(
                "     {} Target may be down or blocking all probes",
                "⚠".yellow()
            );
        } else {
            println!("  {} Host is reachable", "✓".green());

            if status.icmp_blocked {
                println!("  {} ICMP blocked (expected)", "⚠".yellow());
            } else {
                println!("  {} ICMP responding", "✓".green());
            }

            if !status.open_ports.is_empty() {
                println!(
                    "  {} Open ports found: {:?}",
                    "✓".green(),
                    status.open_ports
                );
            }
        }
    }
}
