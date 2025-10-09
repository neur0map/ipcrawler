use crate::parser::ExtractedEntities;
use colored::Colorize;

pub struct TerminalDisplay;

impl TerminalDisplay {
    fn get_terminal_width() -> usize {
        match terminal_size::terminal_size() {
            Some((terminal_size::Width(w), _)) => w as usize,
            None => 80, // Default fallback
        }
    }

    pub fn display_entities(entities: &ExtractedEntities, target: &str) {
        let width = Self::get_terminal_width();
        let separator = "=".repeat(width.saturating_sub(5).max(20));

        println!("\n{}", separator.cyan());
        println!(
            "{} {}",
            "Scan Results for".cyan().bold(),
            target.yellow().bold()
        );
        println!("{}", separator.cyan());

        Self::display_ips(&entities.ips);
        Self::display_domains(&entities.domains);
        Self::display_urls(&entities.urls);
        Self::display_ports(&entities.ports);
        Self::display_vulnerabilities(&entities.vulnerabilities);
        Self::display_findings(&entities.findings);

        println!("{}\n", "=".repeat(width.saturating_sub(5).max(20)).cyan());
    }

    fn display_ips(ips: &[String]) {
        if ips.is_empty() {
            return;
        }

        let width = Self::get_terminal_width();
        let separator = "-".repeat(width.saturating_sub(10).max(15));

        println!("\n{}", "[IP Addresses]".green().bold());
        println!("{}", separator.dimmed());
        for (i, ip) in ips.iter().enumerate() {
            println!("  {}. {}", i + 1, ip.bright_white());
        }
    }

    fn display_domains(domains: &[String]) {
        if domains.is_empty() {
            return;
        }

        let width = Self::get_terminal_width();
        let separator = "-".repeat(width.saturating_sub(10).max(15));

        println!("\n{}", "[Domains]".green().bold());
        println!("{}", separator.dimmed());
        for (i, domain) in domains.iter().enumerate() {
            println!("  {}. {}", i + 1, domain.bright_white());
        }
    }

    fn display_urls(urls: &[String]) {
        if urls.is_empty() {
            return;
        }

        let width = Self::get_terminal_width();
        let separator = "-".repeat(width.saturating_sub(10).max(15));

        println!("\n{}", "[URLs Found]".green().bold());
        println!("{}", separator.dimmed());
        for (i, url) in urls.iter().enumerate() {
            println!("  {}. {}", i + 1, url.cyan().underline());
        }
    }

    fn display_ports(ports: &[crate::parser::PortInfo]) {
        if ports.is_empty() {
            return;
        }

        let width = Self::get_terminal_width();
        let separator = "-".repeat(width.saturating_sub(10).max(15));

        println!("\n{}", "[Open Ports]".green().bold());
        println!("{}", separator.dimmed());
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

        let width = Self::get_terminal_width();
        let separator = "-".repeat(width.saturating_sub(10).max(15));

        println!("\n{}", "[Vulnerabilities Found]".red().bold());
        println!("{}", separator.dimmed());

        for (i, vuln) in vulns.iter().enumerate() {
            let severity_colored = match vuln.severity.to_lowercase().as_str() {
                "critical" => vuln.severity.red().bold(),
                "high" => vuln.severity.bright_red().bold(),
                "medium" => vuln.severity.yellow().bold(),
                "low" => vuln.severity.bright_yellow(),
                _ => vuln.severity.normal(),
            };

            println!(
                "\n  {}. {} [{}]",
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

        let width = Self::get_terminal_width();
        let separator = "-".repeat(width.saturating_sub(10).max(15));

        println!("\n{}", "[Other Findings]".green().bold());
        println!("{}", separator.dimmed());
        for (i, finding) in findings.iter().enumerate() {
            println!("  {}. {}", i + 1, finding.bright_white());
        }
    }

    pub fn display_summary(
        _target: &str,
        _duration: u64,
        _total_tools: usize,
        _successful: usize,
        _entities: &ExtractedEntities,
    ) {
        // Summary removed per user request - only show scan results
    }
}
