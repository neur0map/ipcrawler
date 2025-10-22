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

        report.push_str("# Penetration Test Report\n\n");
        report.push_str(&format!("**Generated**: {}\n\n", timestamp));

        report.push_str(&format!("**Targets**: {}\n\n", targets.join(", ")));

        report.push_str(&format!(
            "**Ports Scanned**: {}\n\n",
            ports
                .iter()
                .map(|p| p.to_string())
                .collect::<Vec<_>>()
                .join(", ")
        ));

        report.push_str("## Summary\n\n");
        let severity_counts = Self::count_by_severity(findings);
        report.push_str(&format!(
            "- Critical: {}\n",
            severity_counts.get(&Severity::Critical).unwrap_or(&0)
        ));
        report.push_str(&format!(
            "- High: {}\n",
            severity_counts.get(&Severity::High).unwrap_or(&0)
        ));
        report.push_str(&format!(
            "- Medium: {}\n",
            severity_counts.get(&Severity::Medium).unwrap_or(&0)
        ));
        report.push_str(&format!(
            "- Low: {}\n",
            severity_counts.get(&Severity::Low).unwrap_or(&0)
        ));
        report.push_str(&format!(
            "- Info: {}\n\n",
            severity_counts.get(&Severity::Info).unwrap_or(&0)
        ));

        let open_ports = Self::extract_open_ports(findings);
        if !open_ports.is_empty() {
            report.push_str("## Open Ports\n\n");
            report.push_str(&format!(
                "Ports: {}\n\n",
                open_ports
                    .iter()
                    .map(|p| p.to_string())
                    .collect::<Vec<_>>()
                    .join(", ")
            ));
        }

        report.push_str("## Vulnerabilities\n\n");

        for severity in &[
            Severity::Critical,
            Severity::High,
            Severity::Medium,
            Severity::Low,
            Severity::Info,
        ] {
            let severity_findings: Vec<&Finding> = findings
                .iter()
                .filter(|f| &f.severity == severity)
                .collect();

            if !severity_findings.is_empty() {
                report.push_str(&format!("### {}\n\n", severity.as_str()));
                report.push_str("| Target | Port | Vulnerability | Tool | Details |\n");
                report.push_str("|--------|------|---------------|------|---------|\n");

                for finding in severity_findings {
                    let port_str = finding.port.map_or("-".to_string(), |p| p.to_string());
                    let details = finding.description.replace('\n', " ").replace('|', "\\|");
                    report.push_str(&format!(
                        "| {} | {} | {} | {} | {} |\n",
                        finding.target, port_str, finding.title, finding.tool, details
                    ));
                }

                report.push('\n');
            }
        }

        report.push_str("## Tool Execution Log\n\n");
        report.push_str("| Tool | Target | Port | Status | Duration |\n");
        report.push_str("|------|--------|------|--------|----------|\n");

        for result in results {
            let port_str = result.port.map_or("-".to_string(), |p| p.to_string());
            let (status_str, duration_str) = match &result.status {
                crate::executor::queue::TaskStatus::Completed {
                    duration,
                    exit_code,
                } => (
                    format!("Exit {}", exit_code),
                    format!("{:.1}s", duration.as_secs_f64()),
                ),
                crate::executor::queue::TaskStatus::Failed { error } => {
                    (format!("Failed: {}", error), "-".to_string())
                }
                crate::executor::queue::TaskStatus::TimedOut => {
                    ("Timed out".to_string(), "-".to_string())
                }
                _ => ("Unknown".to_string(), "-".to_string()),
            };

            report.push_str(&format!(
                "| {} | {} | {} | {} | {} |\n",
                result.tool_name, result.target, port_str, status_str, duration_str
            ));
        }

        let report_path = output_dir.join("report.md");
        fs::write(&report_path, &report)?;

        Ok(report)
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
        let ports: HashSet<u16> = findings.iter().filter_map(|f| f.port).collect();

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
                raw_output: "test".to_string(),
            },
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(443),
                severity: Severity::High,
                title: "test2".to_string(),
                description: "test".to_string(),
                raw_output: "test".to_string(),
            },
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(22),
                severity: Severity::Low,
                title: "test3".to_string(),
                description: "test".to_string(),
                raw_output: "test".to_string(),
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
                raw_output: "test".to_string(),
            },
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(443),
                severity: Severity::Info,
                title: "test".to_string(),
                description: "test".to_string(),
                raw_output: "test".to_string(),
            },
            Finding {
                tool: "test".to_string(),
                target: "127.0.0.1".to_string(),
                port: Some(80),
                severity: Severity::Info,
                title: "test".to_string(),
                description: "test".to_string(),
                raw_output: "test".to_string(),
            },
        ];

        let ports = ReportGenerator::extract_open_ports(&findings);

        assert_eq!(ports, vec![80, 443]);
    }
}
