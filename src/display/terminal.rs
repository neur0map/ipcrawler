use crate::parser::ExtractedEntities;
use colored::Colorize;

pub struct TerminalDisplay;

impl TerminalDisplay {
    pub fn display_entities(entities: &ExtractedEntities, target: &str) {
        println!("\n{}", "=".repeat(60).cyan());
        println!("{} {}", "Scan Results for".cyan().bold(), target.yellow().bold());
        println!("{}", "=".repeat(60).cyan());

        Self::display_ips(&entities.ips);
        Self::display_domains(&entities.domains);
        Self::display_urls(&entities.urls);
        Self::display_ports(&entities.ports);
        Self::display_vulnerabilities(&entities.vulnerabilities);
        Self::display_findings(&entities.findings);

        println!("{}\n", "=".repeat(60).cyan());
    }

    fn display_ips(ips: &[String]) {
        if ips.is_empty() {
            return;
        }

        println!("\n{}", "[IP Addresses]".green().bold());
        println!("{}", "-".repeat(60).dimmed());
        for (i, ip) in ips.iter().enumerate() {
            println!("  {}. {}", i + 1, ip.bright_white());
        }
    }

    fn display_domains(domains: &[String]) {
        if domains.is_empty() {
            return;
        }

        println!("\n{}", "[Domains]".green().bold());
        println!("{}", "-".repeat(60).dimmed());
        for (i, domain) in domains.iter().enumerate() {
            println!("  {}. {}", i + 1, domain.bright_white());
        }
    }

    fn display_urls(urls: &[String]) {
        if urls.is_empty() {
            return;
        }

        println!("\n{}", "[URLs Found]".green().bold());
        println!("{}", "-".repeat(60).dimmed());
        for (i, url) in urls.iter().enumerate() {
            println!("  {}. {}", i + 1, url.cyan().underline());
        }
    }

    fn display_ports(ports: &[crate::parser::PortInfo]) {
        if ports.is_empty() {
            return;
        }

        println!("\n{}", "[Open Ports]".green().bold());
        println!("{}", "-".repeat(60).dimmed());
        for port_info in ports {
            let service = port_info.service.as_deref().unwrap_or("unknown");
            let version = port_info.version.as_deref().unwrap_or("");
            
            println!(
                "  {} {}  {} {}",
                format!("{}", port_info.port).bright_yellow().bold(),
                format!("({})", port_info.protocol).dimmed(),
                service.bright_cyan(),
                version.dimmed()
            );
        }
    }

    fn display_vulnerabilities(vulns: &[crate::parser::Vulnerability]) {
        if vulns.is_empty() {
            println!("\n{}", "[No vulnerabilities detected]".green().bold());
            return;
        }

        println!("\n{}", "[Vulnerabilities Found]".red().bold());
        println!("{}", "-".repeat(60).dimmed());
        
        for (i, vuln) in vulns.iter().enumerate() {
            let severity_colored = match vuln.severity.to_lowercase().as_str() {
                "critical" => vuln.severity.red().bold(),
                "high" => vuln.severity.bright_red().bold(),
                "medium" => vuln.severity.yellow().bold(),
                "low" => vuln.severity.bright_yellow(),
                _ => vuln.severity.normal(),
            };

            println!("\n  {}. {} [{}]",
                i + 1,
                vuln.name.bright_white().bold(),
                severity_colored
            );
            println!("     {}", vuln.description.dimmed());
        }
    }

    fn display_findings(findings: &[String]) {
        if findings.is_empty() {
            return;
        }

        println!("\n{}", "[Other Findings]".green().bold());
        println!("{}", "-".repeat(60).dimmed());
        for (i, finding) in findings.iter().enumerate() {
            println!("  {}. {}", i + 1, finding.bright_white());
        }
    }

    pub fn display_summary(
        target: &str,
        duration: u64,
        total_tools: usize,
        successful: usize,
        entities: &ExtractedEntities,
    ) {
        println!("\n{}", "=".repeat(60).cyan());
        println!("{}", "[Scan Summary]".cyan().bold());
        println!("{}", "=".repeat(60).cyan());
        
        println!("\n  {} {}", "Target:".bold(), target.yellow());
        println!("  {} {}s", "Duration:".bold(), duration);
        println!("  {} {}/{}", "Tools:".bold(), successful.to_string().green(), total_tools);
        
        println!("\n  {}", "Discovered:".bold());
        println!("    - {} IPs", entities.ips.len());
        println!("    - {} Domains", entities.domains.len());
        println!("    - {} URLs", entities.urls.len());
        println!("    - {} Open Ports", entities.ports.len());
        
        if entities.vulnerabilities.is_empty() {
            println!("    - {} {}", entities.vulnerabilities.len(), "Vulnerabilities".green());
        } else {
            println!("    - {} {}", entities.vulnerabilities.len(), "Vulnerabilities".red().bold());
        }
        
        println!("    - {} Findings", entities.findings.len());
        
        println!();
    }
}
