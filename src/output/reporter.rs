use super::parser::Finding;
use crate::config::Severity;
use crate::executor::runner::TaskResult;
use anyhow::Result;
use chrono::Local;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;

pub struct ReportGenerator;

impl ReportGenerator {
    pub fn generate_markdown(
        findings: &[Finding],
        results: &[TaskResult],
        targets: &[String],
        ports: &[u16],
        output_dir: &Path,
    ) -> Result<String> {
        let timestamp = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
        let mut report = String::new();

        // Calculate statistics
        let total_duration = results.iter().filter_map(|r| {
            if let crate::executor::queue::TaskStatus::Completed { duration, .. } = &r.status {
                Some(duration.as_secs_f64())
            } else {
                None
            }
        }).sum::<f64>();

        let open_ports: HashSet<u16> = findings.iter()
            .filter_map(|f| f.port)
            .collect();

        let services: HashSet<String> = findings.iter()
            .filter(|f| f.title.contains("Service:") || f.description.contains("| tcp |"))
            .map(|f| {
                if let Some(pos) = f.description.find(" | tcp | ") {
                    let parts: Vec<&str> = f.description.split(" | ").collect();
                    if parts.len() >= 3 {
                        parts[2].trim().to_string()
                    } else {
                        "unknown".to_string()
                    }
                } else {
                    "unknown".to_string()
                }
            })
            .collect();

        // Header
        report.push_str("# Security Reconnaissance Report\n\n");
        report.push_str(&format!("**Target:** {}\n\n", targets.join(", ")));
        report.push_str(&format!("**Generated:** {}\n\n", timestamp));
        report.push_str(&format!("**Scan Duration:** {:.1}s\n\n", total_duration));

        // Executive Summary
        report.push_str("## 🎯 Executive Summary\n\n");
        report.push_str(&format!("- **Open Ports:** {} ({})\n", open_ports.len(), 
            if open_ports.is_empty() { "None".to_string() } else { 
                let mut ports: Vec<_> = open_ports.iter().copied().collect();
                ports.sort();
                ports.iter().map(|p| p.to_string()).collect::<Vec<_>>().join(", ")
            }));
        report.push_str(&format!("- **Services Detected:** {} ({})\n", services.len(),
            if services.is_empty() { "None".to_string() } else { 
                services.iter().cloned().collect::<Vec<_>>().join(", ")
            }));
        
        // Count findings by severity
        let mut severity_counts = HashMap::new();
        for finding in findings {
            *severity_counts.entry(finding.severity).or_insert(0) += 1;
        }
        
        let total_findings = findings.len();
        report.push_str(&format!("- **Security Issues:** {} total", total_findings));
        if total_findings > 0 {
            let mut severity_parts = Vec::new();
            for (severity, count) in &severity_counts {
                if *count > 0 {
                    severity_parts.push(format!("{} {}", count, severity.as_str()));
                }
            }
            report.push_str(&format!(" ({})", severity_parts.join(", ")));
        }
        report.push_str("\n\n---\n\n");

        // Tool Execution Summary
        Self::add_tool_execution_summary(&mut report, results, ports);

        // Detailed Findings by Severity
        Self::add_detailed_findings(&mut report, findings);

        // Technical Details
        Self::add_technical_details(&mut report, results, findings);

        // Statistics
        Self::add_statistics(&mut report, results, total_duration);

        // Footer
        report.push_str("---\n\n");
        report.push_str("*Full logs available in `logs/` directory*\n");

        let report_path = output_dir.join("report.md");
        fs::write(&report_path, &report)?;

        Ok(report)
    }

    fn add_tool_execution_summary(report: &mut String, results: &[TaskResult], ports: &[u16]) {
        report.push_str("## 🔍 Tool Execution Summary\n\n");
        report.push_str("| Tool | Command | Status | Duration | Key Findings |\n");
        report.push_str("|------|---------|---------|----------|--------------|\n");

        // Group results by tool_name and target to consolidate
        let mut tool_groups: HashMap<(String, String), Vec<&TaskResult>> = HashMap::new();
        for result in results {
            let key = (result.tool_name.clone(), result.target.clone());
            tool_groups.entry(key).or_default().push(result);
        }

        for ((tool_name, target), tool_results) in tool_groups {
            // Get consolidated status and duration
            let total_duration: f64 = tool_results.iter().filter_map(|r| {
                if let crate::executor::queue::TaskStatus::Completed { duration, .. } = &r.status {
                    Some(duration.as_secs_f64())
                } else {
                    None
                }
            }).sum();

            let status = if tool_results.iter().all(|r| {
                matches!(r.status, crate::executor::queue::TaskStatus::Completed { .. })
            }) {
                "✅ Success"
            } else if tool_results.iter().any(|r| {
                matches!(r.status, crate::executor::queue::TaskStatus::Completed { .. })
            }) {
                "⚠️ Partial"
            } else {
                "❌ Failed"
            };

            // Generate clean command (hide ports unless custom)
            let clean_command = Self::generate_clean_command(&tool_name, &target, ports);
            
            // Get key findings summary
            let key_findings = Self::get_key_findings_summary(&tool_results);

            report.push_str(&format!(
                "| {} | `{}` | {} | {:.1}s | {} |\n",
                tool_name,
                clean_command,
                status,
                total_duration,
                key_findings
            ));
        }
        report.push_str("\n");
    }

    fn generate_clean_command(tool_name: &str, target: &str, ports: &[u16]) -> String {
        match tool_name {
            "nmap_comprehensive" => {
                if ports.len() > 50 { // Assume default port list
                    format!("nmap_comprehensive.sh {}", target)
                } else {
                    format!("nmap_comprehensive.sh {} [custom ports]", target)
                }
            }
            "httpx_enumeration" => {
                // Show only for ports that actually had results
                format!("httpx_enumeration.sh {} [web ports]", target)
            }
            "dig" => {
                format!("dig.sh {}", target)
            }
            "traceroute" => {
                format!("traceroute {}", target)
            }
            "whois" => {
                format!("whois {}", target)
            }
            _ => {
                format!("{} {}", tool_name, target)
            }
        }
    }

    fn get_key_findings_summary(tool_results: &[&TaskResult]) -> String {
        let mut summary_parts = Vec::new();
        
        for result in tool_results {
            // Parse JSON output from scripts
            if let Ok(json_data) = serde_json::from_str::<serde_json::Value>(&result.stdout) {
                if let Some(findings_array) = json_data.get("findings").and_then(|f| f.as_array()) {
                    for finding in findings_array {
                        if let Some(title) = finding.get("title").and_then(|t| t.as_str()) {
                            if title.contains("port") {
                                if let Some(port) = finding.get("port").and_then(|p| p.as_u64()) {
                                    if let Some(desc) = finding.get("description").and_then(|d| d.as_str()) {
                                        if desc.contains("ssh") {
                                            summary_parts.push(format!("{} (ssh)", port));
                                        } else if desc.contains("http") {
                                            summary_parts.push(format!("{} (http)", port));
                                        } else {
                                            summary_parts.push(port.to_string());
                                        }
                                    }
                                }
                            } else if title.contains("security") || title.contains("Missing") {
                                summary_parts.push("Security issues".to_string());
                            } else if title.contains("DNS") || title.contains("record") {
                                summary_parts.push("DNS records".to_string());
                            }
                        }
                    }
                }
            } else {
                // Fallback to regex parsing for non-JSON tools
                if result.stdout.contains("open") && result.stdout.contains("tcp") {
                    if result.stdout.contains("ssh") {
                        summary_parts.push("SSH service".to_string());
                    } else if result.stdout.contains("http") {
                        summary_parts.push("HTTP service".to_string());
                    }
                }
                if result.stdout.contains("hops") || result.stdout.contains("traceroute") {
                    summary_parts.push("Route traced".to_string());
                }
                if result.stdout.contains("NetRange") || result.stdout.contains("Organization") {
                    summary_parts.push("Whois info".to_string());
                }
            }
        }

        if summary_parts.is_empty() {
            "No significant findings".to_string()
        } else {
            summary_parts.into_iter().collect::<HashSet<_>>()
                .into_iter().collect::<Vec<_>>()
                .join(", ")
        }
    }

    fn get_status_info(result: &TaskResult) -> (&str, Option<f64>, Option<&str>) {
        match &result.status {
            crate::executor::queue::TaskStatus::Completed {
                exit_code,
                duration,
            } => {
                let status = if *exit_code == 0 {
                    if result.stderr.trim().is_empty() || result.stderr.len() < 50 {
                        "Success"
                    } else {
                        "Partial"
                    }
                } else {
                    "Failed"
                };
                (status, Some(duration.as_secs_f64()), None)
            }
            crate::executor::queue::TaskStatus::Failed { error } => {
                ("Failed", None, Some(error.as_str()))
            }
            crate::executor::queue::TaskStatus::TimedOut => ("Timeout", None, None),
            _ => ("Unknown", None, None),
        }
    }



    fn extract_clean_description(desc: &str) -> String {
        // Extract just the meaningful part before " | Captures:" or " | "
        let cleaned = if let Some(pos) = desc.find(" | Captures:") {
            &desc[..pos]
        } else if let Some(pos) = desc.find(" | ") {
            &desc[..pos]
        } else {
            desc
        };

        // Strip common tool output prefixes (nmap script formatting, etc.)
        let cleaned = cleaned.trim();
        let cleaned = cleaned.strip_prefix("|_").unwrap_or(cleaned);
        let cleaned = cleaned.strip_prefix("| ").unwrap_or(cleaned);
        let cleaned = cleaned.strip_prefix("|").unwrap_or(cleaned);

        cleaned.trim().to_string()
    }

    fn add_detailed_findings(report: &mut String, findings: &[Finding]) {
        report.push_str("## 📊 Detailed Findings\n\n");

        // Group findings by severity
        let mut severity_groups: HashMap<Severity, Vec<&Finding>> = HashMap::new();
        for finding in findings {
            if finding.title.contains("execution") || finding.title == "Tool output" {
                continue;
            }
            severity_groups.entry(finding.severity).or_default().push(finding);
        }

        // Order: Critical -> High -> Medium -> Low -> Info
        let severity_order = [
            Severity::Critical,
            Severity::High, 
            Severity::Medium,
            Severity::Low,
            Severity::Info
        ];

        for severity in &severity_order {
            if let Some(group_findings) = severity_groups.get(severity) {
                let (emoji, title) = match severity {
                    Severity::Critical => ("🚨", "Critical Severity"),
                    Severity::High => ("⚠️", "High Severity"),
                    Severity::Medium => ("⚠️", "Medium Severity"),
                    Severity::Low => ("ℹ️", "Low Severity"),
                    Severity::Info => ("ℹ️", "Informational Findings"),
                };

                report.push_str(&format!("### {} {}\n\n", emoji, title));

                // Sort findings by port then by description
                let mut sorted_findings = group_findings.clone();
                sorted_findings.sort_by(|a, b| {
                    match (a.port, b.port) {
                        (Some(pa), Some(pb)) => pa.cmp(&pb),
                        (Some(_), None) => std::cmp::Ordering::Less,
                        (None, Some(_)) => std::cmp::Ordering::Greater,
                        (None, None) => a.description.cmp(&b.description),
                    }
                });

                for finding in sorted_findings {
                    let clean_desc = Self::extract_clean_description(&finding.description);
                    
                    if finding.port.is_some() {
                        report.push_str(&format!(
                            "- **[{}] {}** (port {})\n",
                            finding.severity.as_str().to_uppercase(),
                            finding.title,
                            finding.port.unwrap()
                        ));
                    } else {
                        report.push_str(&format!(
                            "- **[{}] {}**\n",
                            finding.severity.as_str().to_uppercase(),
                            finding.title
                        ));
                    }
                    
                    if !clean_desc.is_empty() && clean_desc != finding.title {
                        report.push_str(&format!("  - {}\n", clean_desc));
                    }
                }
                report.push('\n');
            }
        }
    }

    fn add_technical_details(report: &mut String, results: &[TaskResult], findings: &[Finding]) {
        report.push_str("## 🔧 Technical Details\n\n");

        // Group by tool for detailed sections
        let mut tool_groups: HashMap<String, Vec<&TaskResult>> = HashMap::new();
        for result in results {
            tool_groups.entry(result.tool_name.clone()).or_default().push(result);
        }

        for (tool_name, tool_results) in tool_groups {
            match tool_name.as_str() {
                "nmap_comprehensive" => {
                    Self::add_nmap_details(report, &tool_results, findings);
                }
                "httpx_enumeration" => {
                    Self::add_httpx_details(report, &tool_results, findings);
                }
                "dig" => {
                    Self::add_dig_details(report, &tool_results, findings);
                }
                "traceroute" => {
                    Self::add_traceroute_details(report, &tool_results);
                }
                "whois" => {
                    Self::add_whois_details(report, &tool_results);
                }
                _ => {
                    // Generic tool details
                    report.push_str(&format!("### {}\n\n", tool_name));
                    for result in tool_results {
                        report.push_str(&format!("**Command:** {}\n\n", result.actual_command));
                        if !result.stdout.is_empty() {
                            report.push_str("**Output:**\n```\n");
                            for line in result.stdout.lines().take(20) {
                                report.push_str(&format!("{}\n", line));
                            }
                            if result.stdout.lines().count() > 20 {
                                report.push_str("... (truncated)\n");
                            }
                            report.push_str("```\n\n");
                        }
                    }
                }
            }
        }
    }

    fn add_nmap_details(report: &mut String, results: &[&TaskResult], findings: &[Finding]) {
        report.push_str("### Nmap Comprehensive Scan\n\n");
        report.push_str("**Commands Executed:**\n");
        report.push_str("1. `nmap -sS -T4 --open <target> -p <ports>` - Port discovery\n");
        report.push_str("2. `nmap -sV -sC -T4 <target> -p <open_ports>` - Service detection\n");
        report.push_str("3. `nmap -O -A --osscan-guess --version-intensity 9 <target> -p <open_ports>` - OS detection\n\n");

        // Extract nmap findings
        let nmap_findings: Vec<_> = findings.iter()
            .filter(|f| f.tool == "nmap_comprehensive")
            .collect();

        if !nmap_findings.is_empty() {
            report.push_str("**Results:**\n");
            
            // Port findings
            let port_findings: Vec<_> = nmap_findings.iter()
                .filter(|f| f.title.contains("Open port"))
                .collect();
            
            if !port_findings.is_empty() {
                report.push_str("- **Phase 1:** Discovered open ports: ");
                let ports: Vec<String> = port_findings.iter()
                    .filter_map(|f| f.port.map(|p| p.to_string()))
                    .collect();
                report.push_str(&ports.join(", "));
                report.push_str("\n");
            }

            // Service findings
            let service_findings: Vec<_> = nmap_findings.iter()
                .filter(|f| f.description.contains("| tcp |"))
                .collect();
            
            if !service_findings.is_empty() {
                report.push_str("- **Phase 2:** Service detection completed\n");
                for finding in service_findings {
                    if let Some(port) = finding.port {
                        let desc = Self::extract_clean_description(&finding.description);
                        report.push_str(&format!("  - Port {}: {}\n", port, desc));
                    }
                }
            }

            // OS detection
            let os_findings: Vec<_> = nmap_findings.iter()
                .filter(|f| f.title.to_lowercase().contains("os") || f.description.to_lowercase().contains("linux"))
                .collect();
            
            if !os_findings.is_empty() {
                report.push_str("- **Phase 3:** OS detection completed\n");
                for finding in os_findings {
                    let desc = Self::extract_clean_description(&finding.description);
                    if !desc.is_empty() {
                        report.push_str(&format!("  - {}\n", desc));
                    }
                }
            }
        }
        report.push('\n');
    }

    fn add_httpx_details(report: &mut String, results: &[&TaskResult], findings: &[Finding]) {
        report.push_str("### HTTP Enumeration\n\n");
        
        // Get successful HTTP scans
        let successful_scans: Vec<_> = results.iter()
            .filter(|r| matches!(r.status, crate::executor::queue::TaskStatus::Completed { .. }))
            .filter(|r| !r.stdout.is_empty())
            .collect();

        if successful_scans.is_empty() {
            report.push_str("No successful HTTP scans completed.\n\n");
            return;
        }

        report.push_str("**Command:** `httpx -u <url> -json -status-code -title -content-length -server -tech-detect -ip -cname -location -response-time -websocket -favicon -hash sha256 -cdn -method -tls-grab -probe -no-fallback -threads 10 -timeout 30 -retries 2 -silent`\n\n");

        // Extract HTTP findings
        let http_findings: Vec<_> = findings.iter()
            .filter(|f| f.tool == "httpx_enumeration")
            .collect();

        if !http_findings.is_empty() {
            report.push_str("**Security Issues:**\n");
            for finding in http_findings {
                if finding.title.contains("security") || finding.title.contains("Missing") {
                    report.push_str(&format!("- **[{}] {}**\n", 
                        finding.severity.as_str().to_uppercase(), finding.title));
                    let desc = Self::extract_clean_description(&finding.description);
                    if !desc.is_empty() && desc != finding.title {
                        report.push_str(&format!("  - {}\n", desc));
                    }
                    if let Some(port) = finding.port {
                        report.push_str(&format!("  - **Port:** {}\n", port));
                    }
                }
            }
        }
        report.push('\n');
    }

    fn add_dig_details(report: &mut String, results: &[&TaskResult], findings: &[Finding]) {
        report.push_str("### DNS Analysis\n\n");
        report.push_str("**Commands:** Multiple dig queries (A, AAAA, MX, NS, TXT, SOA, CNAME, SRV, CAA, PTR, ANY)\n\n");

        let dig_findings: Vec<_> = findings.iter()
            .filter(|f| f.tool == "dig")
            .collect();

        if dig_findings.is_empty() {
            report.push_str("**Result:** No DNS records found (IP address lookup)\n\n");
        } else {
            report.push_str("**Records Found:**\n");
            for finding in dig_findings {
                if finding.title.contains("record") {
                    report.push_str(&format!("- {}: {}\n", finding.title, 
                        Self::extract_clean_description(&finding.description)));
                }
            }
            report.push('\n');
        }
    }

    fn add_traceroute_details(report: &mut String, results: &[&TaskResult]) {
        report.push_str("### Network Path Analysis\n\n");
        
        for result in results {
            report.push_str(&format!("**Command:** `{}`\n\n", result.actual_command));
            
            if !result.stdout.is_empty() {
                report.push_str("**Route:**\n");
                for line in result.stdout.lines().take(10) {
                    if line.trim().is_empty() || line.starts_with("traceroute to") {
                        continue;
                    }
                    report.push_str(&format!("  {}\n", line.trim()));
                }
                report.push('\n');
            }
        }
    }

    fn add_whois_details(report: &mut String, results: &[&TaskResult]) {
        report.push_str("### WHOIS Information\n\n");
        
        for result in results {
            report.push_str(&format!("**Command:** `{}`\n\n", result.actual_command));
            
            if !result.stdout.is_empty() {
                // Extract key WHOIS info
                for line in result.stdout.lines() {
                    if line.starts_with("NetRange:") || line.starts_with("CIDR:") ||
                       line.starts_with("Organization:") || line.starts_with("OrgName:") ||
                       line.starts_with("Country:") || line.starts_with("NetType:") {
                        report.push_str(&format!("  {}\n", line.trim()));
                    }
                }
                report.push('\n');
            }
        }
    }

    fn add_statistics(report: &mut String, results: &[TaskResult], total_duration: f64) {
        report.push_str("## 📈 Statistics\n\n");
        
        let successful = results.iter().filter(|r| 
            matches!(r.status, crate::executor::queue::TaskStatus::Completed { .. })).count();
        let failed = results.iter().filter(|r| 
            matches!(r.status, crate::executor::queue::TaskStatus::Failed { .. })).count();
        let timed_out = results.iter().filter(|r| 
            matches!(r.status, crate::executor::queue::TaskStatus::TimedOut)).count();
        
        report.push_str(&format!("- **Total Commands Executed:** {}\n", results.len()));
        report.push_str(&format!("- **Successful:** {} | **Partial:** {} | **Failed:** {} | **Timed Out:** {}\n", 
            successful, results.len() - successful - failed - timed_out, failed, timed_out));
        report.push_str(&format!("- **Execution Time:** {:.1} seconds\n", total_duration));
        
        let total_output_size: usize = results.iter()
            .map(|r| r.stdout.len() + r.stderr.len())
            .sum();
        report.push_str(&format!("- **Data Collected:** {}KB raw output\n\n", total_output_size / 1024));
    }



    fn add_llm_analysis(report: &mut String, findings: &[Finding]) {
        let llm_findings: Vec<_> = findings
            .iter()
            .filter(|f| f.llm_analysis.is_some())
            .collect();

        if llm_findings.is_empty() {
            return;
        }

        report.push_str("## AI Analysis\n\n");

        for finding in llm_findings {
            if let Some(analysis) = &finding.llm_analysis {
                report.push_str(&format!("### {} Analysis\n\n", finding.tool));
                report.push_str(analysis);
                report.push_str("\n\n"); // Keep as is - need two newlines
            }
        }

        report.push_str("---\n\n");
    }

    pub fn save_json(
        findings: &[Finding],
        results: &[TaskResult],
        output_dir: &Path,
    ) -> Result<()> {
        let json_data = serde_json::json!({
            "findings": findings,
            "results": results.iter().map(|r| {
                serde_json::json!({
                    "tool": r.tool_name,
                    "target": r.target,
                    "port": r.port,
                    "status": format!("{:?}", r.status),
                })
            }).collect::<Vec<_>>(),
        });

        let json_path = output_dir.join("results.json");
        let json_str = serde_json::to_string_pretty(&json_data)?;
        fs::write(json_path, json_str)?;

        Ok(())
    }

    pub fn save_individual_logs(results: &[TaskResult], output_dir: &Path) -> Result<()> {
        let logs_dir = output_dir.join("logs");
        fs::create_dir_all(&logs_dir)?;

        for result in results {
            let port_str = result.port.map_or("none".to_string(), |p| p.to_string());
            let filename = format!(
                "{}_{}_{}.log",
                result.tool_name,
                result.target.replace(['.', ':'], "_"),
                port_str
            );

            let log_path = logs_dir.join(filename);

            let mut content = String::new();
            content.push_str(&format!("Tool: {}\n", result.tool_name));
            content.push_str(&format!("Target: {}\n", result.target));
            content.push_str(&format!(
                "Port: {}\n",
                result.port.map_or("N/A".to_string(), |p| p.to_string())
            ));
            content.push_str(&format!("Status: {:?}\n\n", result.status));
            content.push_str("=== STDOUT ===\n");
            content.push_str(&result.stdout);
            content.push_str("\n\n=== STDERR ===\n");
            content.push_str(&result.stderr);

            fs::write(log_path, content)?;
        }

        Ok(())
    }
}
