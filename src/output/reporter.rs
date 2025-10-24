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
        _ports: &[u16],
        output_dir: &Path,
    ) -> Result<String> {
        let timestamp = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
        let mut report = String::new();

        // Header
        report.push_str("# Security Reconnaissance Summary\n\n");
        report.push_str(&format!("**Generated:** {}\n\n", timestamp));
        report.push_str(&format!("**Target(s):** {}\n\n", targets.join(", ")));
        report.push_str(&format!("**Total Tools Run:** {}\n\n", results.len()));
        report.push_str("---\n\n");

        // Tool Findings Section (main content)
        for result in results {
            Self::add_tool_section(&mut report, result, findings);
        }

        report.push_str("---\n\n");

        // Host Summary
        Self::add_host_summary(&mut report, findings, targets);

        // LLM Analysis (if available)
        Self::add_llm_analysis(&mut report, findings);

        // Footer
        report.push_str("---\n\n");
        report.push_str("*Raw tool logs stored in logs/ directory*\n");

        let report_path = output_dir.join("report.md");
        fs::write(&report_path, &report)?;

        Ok(report)
    }

    fn add_tool_section(report: &mut String, result: &TaskResult, findings: &[Finding]) {
        report.push_str(&format!("### {}\n\n", result.tool_name));

        // Command (use the actual executed command)
        report.push_str(&format!("**Command:** {}\n\n", result.actual_command));

        // Status with duration and error message
        let (status, duration, error) = Self::get_status_info(result);
        if let Some(dur) = duration {
            report.push_str(&format!("**Status:** {} ({:.3}s)\n\n", status, dur));
        } else {
            report.push_str(&format!("**Status:** {}\n\n", status));
        }

        // Show error message if present
        if let Some(err_msg) = error {
            report.push_str(&format!("**Error:** {}\n\n", err_msg));
        }

        // Findings
        report.push_str("**Findings:**\n");
        let tool_findings =
            Self::interpret_findings_for_tool(findings, &result.tool_name, &result.target);

        if tool_findings.is_empty() {
            // No structured findings, but check if there's raw output
            let line_count = result.stdout.lines().count();
            if line_count > 0 {
                if line_count < 100 {
                    // Show actual output for smaller outputs
                    report.push_str("**Output:**\n");
                    report.push_str("```\n");
                    for line in result.stdout.lines().take(50) {
                        // Limit to first 50 lines
                        report.push_str(&format!("{}\n", line));
                    }
                    if result.stdout.lines().count() > 50 {
                        report.push_str("... (truncated, see logs/ for full output)\n");
                    }
                    report.push_str("```\n");
                } else {
                    // Hide large outputs
                    report.push_str(&format!(
                        "- Output captured ({} lines) - see logs/ for details\n",
                        line_count
                    ));
                }
            } else {
                report.push_str("- No output\n");
            }
        } else {
            for finding in tool_findings {
                report.push_str(&format!("- {}\n", finding));
            }
        }

        report.push('\n');
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

    fn interpret_findings_for_tool(
        findings: &[Finding],
        tool_name: &str,
        target: &str,
    ) -> Vec<String> {
        // Filter findings for this specific tool and target
        let tool_findings: Vec<_> = findings
            .iter()
            .filter(|f| f.tool == tool_name && f.target == target)
            .filter(|f| !f.title.contains("execution") && f.title != "Tool output")
            .collect();

        let mut bullets = Vec::new();
        let mut seen_descriptions = std::collections::HashSet::new();

        // Separate port findings for aggregation
        let port_findings: Vec<_> = tool_findings
            .iter()
            .filter(|f| f.port.is_some())
            .copied()
            .collect();

        // Format aggregated port list first (if any)
        if !port_findings.is_empty() {
            let port_bullet = Self::format_ports_bullet(&port_findings);
            if !port_bullet.is_empty() {
                bullets.push(port_bullet);
                // Mark port descriptions as seen to avoid duplication
                for finding in &port_findings {
                    seen_descriptions.insert(finding.description.clone());
                }
            }
        }

        // Process all other findings universally (no categorization, no prefixes)
        for finding in &tool_findings {
            // Skip if already shown in port aggregation
            if seen_descriptions.contains(&finding.description) {
                continue;
            }

            let desc = Self::extract_clean_description(&finding.description);

            // Skip low-value/malformed findings
            if desc.is_empty() || desc.len() < 5 {
                continue;
            }

            // Add severity prefix only for high/critical findings
            let formatted = if matches!(finding.severity, Severity::Critical | Severity::High) {
                format!("[{}] {}", finding.severity.as_str().to_uppercase(), desc)
            } else {
                desc
            };

            // Deduplicate
            if seen_descriptions.insert(formatted.clone()) {
                bullets.push(formatted);
            }
        }

        bullets
    }

    fn format_ports_bullet(port_findings: &[&Finding]) -> String {
        // Group by port number
        let mut port_map: HashMap<u16, Vec<String>> = HashMap::new();

        for finding in port_findings {
            if let Some(port) = finding.port {
                let entry = port_map.entry(port).or_default();

                // Extract service info from description
                let service_info = Self::extract_service_from_description(&finding.description);
                if !service_info.is_empty() {
                    entry.push(service_info);
                }
            }
        }

        // Format as "Ports: 22 (ssh OpenSSH 8.2p1), 80 (http nginx)"
        let mut port_list: Vec<_> = port_map.iter().collect();
        port_list.sort_by_key(|(port, _)| *port);

        let port_strings: Vec<String> = port_list
            .iter()
            .map(|(port, services)| {
                if services.is_empty() {
                    format!("{}", port)
                } else {
                    // Deduplicate and join services
                    let unique_services: HashSet<_> = services.iter().collect();
                    let service_str = unique_services
                        .iter()
                        .map(|s| s.as_str())
                        .collect::<Vec<_>>()
                        .join(", ");
                    format!("{} ({})", port, service_str)
                }
            })
            .collect();

        if port_strings.is_empty() {
            String::new()
        } else {
            format!("Ports: {}", port_strings.join(", "))
        }
    }

    fn extract_service_from_description(desc: &str) -> String {
        // Parse descriptions like "22 | tcp | ssh | OpenSSH 8.2p1 Ubuntu"
        let parts: Vec<&str> = desc.split(" | ").collect();

        if parts.len() >= 4 {
            // Format: port | protocol | service | version
            let service = parts[2].trim();
            let version = parts[3].trim();

            if !service.is_empty() && service.len() > 1 {
                if !version.is_empty() {
                    format!("{} {}", service, version)
                } else {
                    service.to_string()
                }
            } else {
                String::new()
            }
        } else if parts.len() == 3 {
            // Format: port | protocol | service
            let service = parts[2].trim();
            if !service.is_empty() && service.len() > 1 {
                service.to_string()
            } else {
                String::new()
            }
        } else {
            String::new()
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

    fn add_host_summary(report: &mut String, findings: &[Finding], targets: &[String]) {
        report.push_str("## Host Summary\n\n");

        for target in targets {
            let target_findings: Vec<_> = findings
                .iter()
                .filter(|f| f.target == *target && !f.title.contains("execution"))
                .collect();

            if target_findings.is_empty() {
                continue;
            }

            report.push_str(&format!("**{}**\n", target));

            // Ports (universal - deduplicated across all tools)
            let ports = Self::extract_unique_ports(&target_findings);
            if !ports.is_empty() {
                report.push_str(&format!("- Ports: {}\n", ports.join(", ")));
            }

            // Key findings (universal - top findings by severity, deduplicated)
            let key_findings = Self::extract_key_findings(&target_findings);
            if !key_findings.is_empty() {
                for finding in key_findings.iter().take(5) {
                    report.push_str(&format!("- {}\n", finding));
                }
            }

            report.push('\n');
        }

        report.push_str("---\n\n");
    }

    fn extract_unique_ports(findings: &[&Finding]) -> Vec<String> {
        let mut port_service_map: HashMap<u16, HashSet<String>> = HashMap::new();

        for finding in findings {
            if let Some(port) = finding.port {
                let services = port_service_map.entry(port).or_default();

                // Try to extract service name
                let service = Self::extract_service_from_description(&finding.description);
                if !service.is_empty() {
                    // Just get the service name (first word)
                    let service_name = service.split_whitespace().next().unwrap_or("");
                    if !service_name.is_empty() && service_name.len() < 20 {
                        services.insert(service_name.to_string());
                    }
                }
            }
        }

        let mut ports: Vec<_> = port_service_map.iter().collect();
        ports.sort_by_key(|(port, _)| *port);

        ports
            .iter()
            .map(|(port, services)| {
                if services.is_empty() {
                    format!("{}", port)
                } else {
                    let service_list: Vec<_> = services.iter().collect();
                    format!("{}/{}", port, service_list[0])
                }
            })
            .collect()
    }

    fn extract_key_findings(findings: &[&Finding]) -> Vec<String> {
        let mut key_findings: Vec<_> = findings
            .iter()
            .filter(|f| !f.title.contains("execution") && f.title != "Tool output")
            .filter(|f| f.port.is_none()) // Exclude port findings (already shown)
            .collect();

        // Sort by severity (Critical > High > Medium > Low > Info)
        key_findings.sort_by(|a, b| {
            let a_priority = match a.severity {
                Severity::Critical => 0,
                Severity::High => 1,
                Severity::Medium => 2,
                Severity::Low => 3,
                Severity::Info => 4,
            };
            let b_priority = match b.severity {
                Severity::Critical => 0,
                Severity::High => 1,
                Severity::Medium => 2,
                Severity::Low => 3,
                Severity::Info => 4,
            };
            a_priority.cmp(&b_priority)
        });

        // Extract clean descriptions and deduplicate
        let mut seen = HashSet::new();
        let mut results = Vec::new();

        for finding in key_findings {
            let desc = Self::extract_clean_description(&finding.description);

            // Skip low-value findings
            if desc.is_empty() || desc.len() < 5 {
                continue;
            }

            // Add severity prefix for high/critical
            let formatted = if matches!(finding.severity, Severity::Critical | Severity::High) {
                format!("[{}] {}", finding.severity.as_str().to_uppercase(), desc)
            } else {
                desc
            };

            if seen.insert(formatted.clone()) {
                results.push(formatted);
            }
        }

        results
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
