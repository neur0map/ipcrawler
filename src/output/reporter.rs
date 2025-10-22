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
        let _severity_counts = Self::count_by_severity(findings);

        let mut report = String::new();

        // Header
        report.push_str("# Security Reconnaissance Report\n\n");
        report.push_str(&format!("**Generated**: {}\n\n", timestamp));
        report.push_str(&format!("**Target(s)**: {}\n\n", targets.join(", ")));
        report.push_str(&format!(
            "**Ports Scanned**: {} ports\n\n",
            ports.len()
        ));

        report.push_str("---\n\n");

        // Executive Summary
        report.push_str("## Executive Summary\n\n");

        let total_findings = findings.len();
        let tools_used: HashSet<_> = findings.iter().map(|f| &f.tool).collect();
        
        report.push_str(&format!("This reconnaissance examined {} target(s) using {} tool(s) and generated {} findings.\n\n", 
            targets.len(), tools_used.len(), total_findings));

        // Add discovery narrative using helper function
        let open_ports = Self::extract_open_ports(findings);
        Self::add_discovery_narrative(&mut report, findings, &open_ports);
        
        // Add services section using helper function
        Self::add_services_section(&mut report, findings, &open_ports);

        // LLM Analysis Summary (if available)
        let llm_findings: Vec<_> = findings.iter().filter(|f| f.llm_analysis.is_some()).collect();
        if !llm_findings.is_empty() {
            report.push_str("### AI Analysis Summary\n\n");
            for finding in llm_findings {
                if let Some(analysis) = &finding.llm_analysis {
                    report.push_str(&format!("**{} Analysis**:\n{}\n\n", finding.tool, analysis));
                }
            }
            report.push_str("---\n\n");
        }

        // Tool Execution Summary
        report.push_str("## Tool Execution Summary\n\n");
        report.push_str("| Tool | Target | Status | Output Size | Has LLM Analysis |\n");
        report.push_str("|------|--------|--------|-------------|------------------|\n");

        for finding in findings {
            let status = if finding.full_stderr.trim().is_empty() { "[+] Success" } else { "[!] Warnings" };
            let output_size = finding.full_stdout.len();
            let llm_status = if finding.llm_analysis.is_some() { "[+]" } else { "[-]" };
            
            report.push_str(&format!(
                "| {} | {} | {} | {} bytes | {} |\n",
                finding.tool, finding.target, status, output_size, llm_status
            ));
        }
        report.push_str("\n---\n\n");

        // Complete Raw Outputs
        report.push_str("## Complete Tool Outputs\n\n");
        report.push_str("All raw output from security tools is preserved below for complete transparency and analysis.\n\n");

        // Group findings by tool
        let mut tool_groups: std::collections::HashMap<String, Vec<&Finding>> = std::collections::HashMap::new();
        for finding in findings {
            tool_groups.entry(finding.tool.clone()).or_insert_with(Vec::new).push(finding);
        }

        for (tool_name, tool_findings) in tool_groups {
            report.push_str(&format!("### {}\n\n", tool_name));
            
            for (idx, finding) in tool_findings.iter().enumerate() {
                report.push_str(&format!("#### Execution {} - Target: {}\n\n", idx + 1, finding.target));
                
                // Show stderr if present
                if !finding.full_stderr.trim().is_empty() {
                    report.push_str("**Errors/Warnings**:\n```\n");
                    report.push_str(&finding.full_stderr);
                    report.push_str("\n```\n\n");
                }
                
                // Show stdout
                report.push_str("**Standard Output**:\n```\n");
                report.push_str(&finding.full_stdout);
                report.push_str("\n```\n\n");
                
                // Show LLM analysis if available
                if let Some(analysis) = &finding.llm_analysis {
                    report.push_str("**AI Analysis**:\n");
                    report.push_str(analysis);
                    report.push_str("\n\n");
                }
                
                report.push_str("---\n\n");
            }
        }

        // Scan Statistics
        report.push_str("## Scan Statistics\n\n");
        report.push_str("| Tool | Target | Status | Duration |\n");
        report.push_str("|------|--------|--------|----------|\n");

        for result in results {
            let (status_str, duration_str) = match &result.status {
                crate::executor::queue::TaskStatus::Completed {
                    duration,
                    exit_code,
                } => {
                    let status = if *exit_code == 0 { "[+] Success" } else { &format!("[!] Exit {}", exit_code) };
                    (status.to_string(), format!("{:.1}s", duration.as_secs_f64()))
                }
                crate::executor::queue::TaskStatus::Failed { error } => {
                    (format!("[-] Failed: {}", error), "-".to_string())
                }
                crate::executor::queue::TaskStatus::TimedOut => {
                    ("[T] Timeout".to_string(), "-".to_string())
                }
                _ => ("Unknown".to_string(), "-".to_string()),
            };

            report.push_str(&format!(
                "| {} | {} | {} | {} |\n",
                result.tool_name, result.target, status_str, duration_str
            ));
        }

        report.push_str("\n---\n\n");
        report.push_str("*Report generated by IPCrawler*\n");

        let report_path = output_dir.join("report.md");
        fs::write(&report_path, &report)?;

        Ok(report)
    }

    fn add_discovery_narrative(report: &mut String, findings: &[Finding], open_ports: &[u16]) {
        // Generic discovery narrative based on findings data, not specific tool types

        if open_ports.is_empty() {
            report.push_str("The target appears to be offline or heavily filtered. No services were detected on the scanned ports.\n\n");
            return;
        }

        // Open ports narrative
        if open_ports.len() == 1 {
            report.push_str(&format!("We discovered **1 open port** (port {}) on the target.\n\n", open_ports[0]));
        } else {
            report.push_str(&format!(
                "We discovered **{} open ports** on the target: {}.\n\n",
                open_ports.len(),
                open_ports
                    .iter()
                    .map(|p| p.to_string())
                    .collect::<Vec<_>>()
                    .join(", ")
            ));
        }

        // Group findings by severity for narrative
        let high_priority: Vec<_> = findings
            .iter()
            .filter(|f| matches!(f.severity, Severity::Critical | Severity::High))
            .collect();

        let medium_priority: Vec<_> = findings
            .iter()
            .filter(|f| f.severity == Severity::Medium)
            .collect();

        let informational: Vec<_> = findings
            .iter()
            .filter(|f| matches!(f.severity, Severity::Info | Severity::Low))
            .collect();

        // High priority findings
        if !high_priority.is_empty() {
            report.push_str(&format!("**[!] {} High Priority Finding(s)**:\n\n", high_priority.len()));
            for finding in high_priority.iter().take(5) {  // Show top 5
                report.push_str(&format!("- {}: {}\n", finding.title.replace('_', " "), finding.description));
            }
            if high_priority.len() > 5 {
                report.push_str(&format!("- ...and {} more (see detailed findings below)\n", high_priority.len() - 5));
            }
            report.push_str("\n");
        }

        // Medium priority findings
        if !medium_priority.is_empty() {
            report.push_str(&format!("**[*] {} Medium Priority Finding(s)**:\n\n", medium_priority.len()));
            for finding in medium_priority.iter().take(3) {  // Show top 3
                report.push_str(&format!("- {}: {}\n", finding.title.replace('_', " "), finding.description));
            }
            if medium_priority.len() > 3 {
                report.push_str(&format!("- ...and {} more (see detailed findings below)\n", medium_priority.len() - 3));
            }
            report.push_str("\n");
        }

        // Informational summary
        if !informational.is_empty() {
            report.push_str(&format!("Additionally, **{} informational finding(s)** were recorded, including service versions, configurations, and other technical details.\n\n", informational.len()));
        }
    }

    fn add_services_section(report: &mut String, findings: &[Finding], open_ports: &[u16]) {
        // Generic services section - works with any tool's findings
        for port in open_ports {
            report.push_str(&format!("### Port {}\n\n", port));

            // Find all findings related to this port (by port field primarily)
            let port_findings: Vec<_> = findings
                .iter()
                .filter(|f| f.port == Some(*port))
                .collect();

            if port_findings.is_empty() {
                report.push_str("*Port is open but no additional service details were discovered.*\n\n");
                continue;
            }

            // Group findings by severity for better organization
            let critical_high: Vec<_> = port_findings.iter()
                .filter(|f| matches!(f.severity, Severity::Critical | Severity::High))
                .collect();
            let medium: Vec<_> = port_findings.iter()
                .filter(|f| f.severity == Severity::Medium)
                .collect();
            let low_info: Vec<_> = port_findings.iter()
                .filter(|f| matches!(f.severity, Severity::Low | Severity::Info))
                .collect();

            // Display findings by severity
            for finding in critical_high {
                report.push_str(&format!("**{}** ({}): {}\n",
                    finding.title.replace('_', " "),
                    finding.severity.as_str(),
                    finding.description
                ));
            }

            for finding in medium {
                report.push_str(&format!("**{}** ({}): {}\n",
                    finding.title.replace('_', " "),
                    finding.severity.as_str(),
                    finding.description
                ));
            }

            for finding in low_info {
                report.push_str(&format!("- {}: {}\n",
                    finding.title.replace('_', " "),
                    finding.description
                ));
            }

            report.push_str("\n");
        }
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

    fn count_by_severity(findings: &[Finding]) -> HashMap<Severity, usize> {
        let mut counts = HashMap::new();

        for finding in findings {
            *counts.entry(finding.severity).or_insert(0) += 1;
        }

        counts
    }

    fn extract_open_ports(findings: &[Finding]) -> Vec<u16> {
        let mut ports: HashSet<u16> = HashSet::new();

        for finding in findings {
            // Only use ports that are explicitly set in the finding's port field
            // This avoids false positives from parsing descriptions
            if let Some(port) = finding.port {
                ports.insert(port);
            }
        }

        let mut port_list: Vec<u16> = ports.into_iter().collect();
        port_list.sort_unstable();
        port_list
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_count_by_severity() {
        let findings = vec![
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(80),
                severity: Severity::High,
                title: "test".to_string(),
                description: "test".to_string(),
                full_stdout: "test".to_string(),
                full_stderr: String::new(),
                llm_analysis: None,
            },
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(443),
                severity: Severity::High,
                title: "test2".to_string(),
                description: "test".to_string(),
                full_stdout: "test".to_string(),
                full_stderr: String::new(),
                llm_analysis: None,
            },
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(22),
                severity: Severity::Low,
                title: "test3".to_string(),
                description: "test".to_string(),
                full_stdout: "test".to_string(),
                full_stderr: String::new(),
                llm_analysis: None,
            },
        ];

        let counts = ReportGenerator::count_by_severity(&findings);

        assert_eq!(counts.get(&Severity::High), Some(&2));
        assert_eq!(counts.get(&Severity::Low), Some(&1));
    }

    #[test]
    fn test_extract_open_ports() {
        let findings = vec![
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(80),
                severity: Severity::Info,
                title: "test".to_string(),
                description: "test".to_string(),
                full_stdout: "test".to_string(),
                full_stderr: String::new(),
                llm_analysis: None,
            },
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(443),
                severity: Severity::Info,
                title: "test".to_string(),
                description: "test".to_string(),
                full_stdout: "test".to_string(),
                full_stderr: String::new(),
                llm_analysis: None,
            },
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(80),
                severity: Severity::Info,
                title: "test".to_string(),
                description: "test".to_string(),
                full_stdout: "test".to_string(),
                full_stderr: String::new(),
                llm_analysis: None,
            },
        ];

        let ports = ReportGenerator::extract_open_ports(&findings);

        assert_eq!(ports, vec![80, 443]);
    }
}
