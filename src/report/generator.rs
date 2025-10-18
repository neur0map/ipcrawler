use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use chrono::{DateTime, Utc};
use crate::providers::ParsedResult;

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanReport {
    pub scan_info: ScanInfo,
    pub targets: Vec<TargetReport>,
    pub summary: ScanSummary,
    pub findings: Vec<Finding>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanInfo {
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub duration_seconds: u64,
    pub ipcrawler_version: String,
    pub total_targets: usize,
    pub tools_used: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TargetReport {
    pub target: String,
    pub results: Vec<ParsedResult>,
    pub summary: TargetSummary,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TargetSummary {
    pub tools_executed: usize,
    pub total_findings: usize,
    pub open_ports: Vec<PortInfo>,
    pub services: Vec<ServiceInfo>,
    pub dns_records: Vec<DNSInfo>,
    pub vulnerabilities: Vec<VulnerabilityInfo>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PortInfo {
    pub port: u16,
    pub protocol: String,
    pub state: String,
    pub service: Option<String>,
    pub version: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ServiceInfo {
    pub name: String,
    pub port: u16,
    pub protocol: String,
    pub version: Option<String>,
    pub product: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DNSInfo {
    pub record_type: String,
    pub name: String,
    pub value: String,
    pub ttl: Option<u32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VulnerabilityInfo {
    pub name: String,
    pub severity: String,
    pub description: Option<String>,
    pub cvss_score: Option<f64>,
    pub references: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub id: String,
    pub target: String,
    pub tool: String,
    pub finding_type: String,
    pub severity: String,
    pub data: serde_json::Value,
    pub timestamp: DateTime<Utc>,
    pub confidence: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanSummary {
    pub total_findings: usize,
    pub findings_by_type: HashMap<String, usize>,
    pub findings_by_severity: HashMap<String, usize>,
    pub unique_targets: usize,
    pub tools_executed: usize,
    pub total_execution_time: u64,
    pub high_risk_findings: usize,
}

pub struct ReportGenerator {
    output_dir: String,
}

impl ReportGenerator {
    pub fn new(output_dir: &str) -> Result<Self> {
        Ok(Self {
            output_dir: output_dir.to_string(),
        })
    }

    pub fn generate_json_report(&self, results: &[ParsedResult]) -> Result<String> {
        let report = self.create_scan_report(results)?;
        serde_json::to_string_pretty(&report)
            .context("Failed to serialize JSON report")
    }

    pub fn generate_markdown_report(&self, results: &[ParsedResult]) -> Result<String> {
        let report = self.create_scan_report(results)?;
        self.format_markdown_report(&report)
    }

    fn create_scan_report(&self, results: &[ParsedResult]) -> Result<ScanReport> {
        let start_time = results
            .iter()
            .map(|r| DateTime::parse_from_rfc3339(&r.timestamp).unwrap_or_else(|_| DateTime::from_timestamp(0, 0).unwrap().into()))
            .min()
            .unwrap_or_else(|| DateTime::from_timestamp(0, 0).unwrap().into())
            .with_timezone(&Utc);

        let end_time = results
            .iter()
            .map(|r| DateTime::parse_from_rfc3339(&r.timestamp).unwrap_or_else(|_| DateTime::from_timestamp(0, 0).unwrap().into()))
            .max()
            .unwrap_or_else(|| DateTime::from_timestamp(0, 0).unwrap().into())
            .with_timezone(&Utc);

        let duration_seconds = (end_time - start_time).num_seconds() as u64;

        let tools_used: HashSet<String> = results
            .iter()
            .map(|r| r.tool_name.clone())
            .collect();

        let targets: HashSet<String> = results
            .iter()
            .map(|r| r.target.clone())
            .collect();

        let target_reports = self.create_target_reports(&targets, results)?;
        let findings = self.extract_findings(results)?;
        let summary = self.create_scan_summary(&findings, &targets, &tools_used, duration_seconds);

        Ok(ScanReport {
            scan_info: ScanInfo {
                start_time,
                end_time,
                duration_seconds,
                ipcrawler_version: env!("CARGO_PKG_VERSION").to_string(),
                total_targets: targets.len(),
                tools_used: tools_used.into_iter().collect(),
            },
            targets: target_reports,
            summary,
            findings,
        })
    }

    fn create_target_reports(&self, targets: &HashSet<String>, results: &[ParsedResult]) -> Result<Vec<TargetReport>> {
        let mut target_reports = Vec::new();

        for target in targets {
            let target_results: Vec<ParsedResult> = results
                .iter()
                .filter(|r| r.target == *target)
                .cloned()
                .collect();

            let summary = self.create_target_summary(&target_results);

            target_reports.push(TargetReport {
                target: target.clone(),
                results: target_results,
                summary,
            });
        }

        Ok(target_reports)
    }

    fn create_target_summary(&self, results: &[ParsedResult]) -> TargetSummary {
        let mut open_ports = Vec::new();
        let mut services = Vec::new();
        let mut dns_records = Vec::new();
        let mut vulnerabilities = Vec::new();

        for result in results {
            if let Some(findings_array) = result.findings["findings"].as_array() {
                for finding in findings_array {
                    if let (Some(finding_type), Some(data)) = (
                        finding["type"].as_str(),
                        finding.get("data")
                    ) {
                        match finding_type {
                            "port" => {
                                if let Some(port) = self.extract_port_info(data) {
                                    open_ports.push(port);
                                }
                            }
                            "service" => {
                                if let Some(service) = self.extract_service_info(data) {
                                    services.push(service);
                                }
                            }
                            "dns" => {
                                if let Some(dns) = self.extract_dns_info(data) {
                                    dns_records.push(dns);
                                }
                            }
                            "vulnerability" => {
                                if let Some(vuln) = self.extract_vulnerability_info(data) {
                                    vulnerabilities.push(vuln);
                                }
                            }
                            _ => {}
                        }
                    }
                }
            }
        }

        let total_findings = open_ports.len() + services.len() + dns_records.len() + vulnerabilities.len();

        TargetSummary {
            tools_executed: results.len(),
            total_findings,
            open_ports,
            services,
            dns_records,
            vulnerabilities,
        }
    }

    fn extract_port_info(&self, data: &serde_json::Value) -> Option<PortInfo> {
        Some(PortInfo {
            port: data["port"].as_u64()? as u16,
            protocol: data["protocol"].as_str().unwrap_or("tcp").to_string(),
            state: data["state"].as_str().unwrap_or("unknown").to_string(),
            service: data["service"].as_str().map(|s| s.to_string()),
            version: data["version"].as_str().map(|s| s.to_string()),
        })
    }

    fn extract_service_info(&self, data: &serde_json::Value) -> Option<ServiceInfo> {
        Some(ServiceInfo {
            name: data["name"].as_str()?.to_string(),
            port: data["port"].as_u64()? as u16,
            protocol: data["protocol"].as_str().unwrap_or("tcp").to_string(),
            version: data["version"].as_str().map(|s| s.to_string()),
            product: data["product"].as_str().map(|s| s.to_string()),
        })
    }

    fn extract_dns_info(&self, data: &serde_json::Value) -> Option<DNSInfo> {
        Some(DNSInfo {
            record_type: data["record_type"].as_str()?.to_string(),
            name: data["name"].as_str()?.to_string(),
            value: data["value"].as_str()?.to_string(),
            ttl: data["ttl"].as_u64().map(|t| t as u32),
        })
    }

    fn extract_vulnerability_info(&self, data: &serde_json::Value) -> Option<VulnerabilityInfo> {
        Some(VulnerabilityInfo {
            name: data["name"].as_str()?.to_string(),
            severity: data["severity"].as_str().unwrap_or("unknown").to_string(),
            description: data["description"].as_str().map(|s| s.to_string()),
            cvss_score: data["cvss_score"].as_f64(),
            references: data["references"]
                .as_array()
                .map(|arr| arr.iter()
                    .filter_map(|v| v.as_str())
                    .map(|s| s.to_string())
                    .collect())
                .unwrap_or_default(),
        })
    }

    fn extract_findings(&self, results: &[ParsedResult]) -> Result<Vec<Finding>> {
        let mut findings = Vec::new();
        let mut counter = 0;

        for result in results {
            if let Some(findings_array) = result.findings["findings"].as_array() {
                for finding in findings_array {
                    counter += 1;
                    
                    let finding = Finding {
                        id: format!("finding-{:04}", counter),
                        target: result.target.clone(),
                        tool: result.tool_name.clone(),
                        finding_type: finding["type"].as_str().unwrap_or("unknown").to_string(),
                        severity: finding["severity"].as_str().unwrap_or("info").to_string(),
                        data: finding.get("data").cloned().unwrap_or_default(),
                        timestamp: DateTime::parse_from_rfc3339(&result.timestamp)
                            .unwrap_or_else(|_| DateTime::from_timestamp(0, 0).unwrap().into())
                            .with_timezone(&Utc),
                        confidence: result.confidence,
                    };
                    
                    findings.push(finding);
                }
            }
        }

        Ok(findings)
    }

    fn create_scan_summary(
        &self,
        findings: &[Finding],
        targets: &HashSet<String>,
        tools_used: &HashSet<String>,
        duration_seconds: u64,
    ) -> ScanSummary {
        let mut findings_by_type = HashMap::new();
        let mut findings_by_severity = HashMap::new();
        let mut high_risk_findings = 0;

        for finding in findings {
            *findings_by_type.entry(finding.finding_type.clone()).or_insert(0) += 1;
            *findings_by_severity.entry(finding.severity.clone()).or_insert(0) += 1;
            
            if matches!(finding.severity.as_str(), "high" | "critical") {
                high_risk_findings += 1;
            }
        }

        ScanSummary {
            total_findings: findings.len(),
            findings_by_type,
            findings_by_severity,
            unique_targets: targets.len(),
            tools_executed: tools_used.len(),
            total_execution_time: duration_seconds,
            high_risk_findings,
        }
    }

    fn format_markdown_report(&self, report: &ScanReport) -> Result<String> {
        let mut markdown = String::new();

        // Title and overview
        markdown.push_str("# IPCrawler Scan Report\n\n");
        
        markdown.push_str("## Scan Overview\n\n");
        markdown.push_str(&format!("- **Start Time**: {}\n", report.scan_info.start_time.format("%Y-%m-%d %H:%M:%S UTC")));
        markdown.push_str(&format!("- **Duration**: {} seconds\n", report.scan_info.duration_seconds));
        markdown.push_str(&format!("- **Targets Scanned**: {}\n", report.scan_info.total_targets));
        markdown.push_str(&format!("- **Tools Used**: {}\n", report.scan_info.tools_used.join(", ")));
        markdown.push_str(&format!("- **Total Findings**: {}\n", report.summary.total_findings));
        markdown.push_str(&format!("- **High Risk Findings**: {}\n\n", report.summary.high_risk_findings));

        // Executive summary
        markdown.push_str("## Executive Summary\n\n");
        if report.summary.high_risk_findings > 0 {
            markdown.push_str(&format!("⚠️ **{} high-risk findings** were discovered that require immediate attention.\n\n", report.summary.high_risk_findings));
        } else {
            markdown.push_str("✅ No high-risk findings were discovered.\n\n");
        }

        // Findings by severity
        markdown.push_str("### Findings by Severity\n\n");
        for (severity, count) in &report.summary.findings_by_severity {
            let emoji = match severity.as_str() {
                "critical" => "🔴",
                "high" => "🟠",
                "medium" => "🟡",
                "low" => "🟢",
                _ => "⚪",
            };
            markdown.push_str(&format!("- {} {}: {}\n", emoji, severity, count));
        }
        markdown.push_str("\n");

        // Target details
        markdown.push_str("## Target Details\n\n");
        for target_report in &report.targets {
            markdown.push_str(&format!("### {}\n\n", target_report.target));
            
            if !target_report.summary.open_ports.is_empty() {
                markdown.push_str("#### Open Ports\n\n");
                markdown.push_str("| Port | Protocol | State | Service | Version |\n");
                markdown.push_str("|------|----------|-------|---------|----------|\n");
                
                for port in &target_report.summary.open_ports {
                    markdown.push_str(&format!(
                        "| {} | {} | {} | {} | {} |\n",
                        port.port,
                        port.protocol,
                        port.state,
                        port.service.as_ref().unwrap_or(&"-".to_string()),
                        port.version.as_ref().unwrap_or(&"-".to_string())
                    ));
                }
                markdown.push_str("\n");
            }

            if !target_report.summary.services.is_empty() {
                markdown.push_str("#### Services\n\n");
                for service in &target_report.summary.services {
                    markdown.push_str(&format!(
                        "- **{}** ({}:{}) - {}\n",
                        service.name,
                        service.port,
                        service.protocol,
                        service.version.as_ref().unwrap_or(&"version unknown".to_string())
                    ));
                }
                markdown.push_str("\n");
            }

            if !target_report.summary.dns_records.is_empty() {
                markdown.push_str("#### DNS Records\n\n");
                markdown.push_str("| Type | Name | Value | TTL |\n");
                markdown.push_str("|------|------|-------|-----|\n");
                
                for dns in &target_report.summary.dns_records {
                    markdown.push_str(&format!(
                        "| {} | {} | {} | {} |\n",
                        dns.record_type,
                        dns.name,
                        dns.value,
                        dns.ttl.map_or("-".to_string(), |t| t.to_string())
                    ));
                }
                markdown.push_str("\n");
            }
        }

        // Detailed findings
        if !report.findings.is_empty() {
            markdown.push_str("## Detailed Findings\n\n");
            
            let mut findings_by_severity = report.findings.clone();
            findings_by_severity.sort_by(|a, b| {
                let severity_order = |s: &str| match s {
                    "critical" => 0,
                    "high" => 1,
                    "medium" => 2,
                    "low" => 3,
                    _ => 4,
                };
                severity_order(&a.severity).cmp(&severity_order(&b.severity))
            });

            for finding in &findings_by_severity {
                let severity_emoji = match finding.severity.as_str() {
                    "critical" => "🔴",
                    "high" => "🟠",
                    "medium" => "🟡",
                    "low" => "🟢",
                    _ => "⚪",
                };

                markdown.push_str(&format!(
                    "### {} {} - {}\n\n",
                    severity_emoji,
                    finding.severity.to_uppercase(),
                    finding.finding_type.to_uppercase()
                ));
                
                markdown.push_str(&format!("- **Target**: {}\n", finding.target));
                markdown.push_str(&format!("- **Tool**: {}\n", finding.tool));
                markdown.push_str(&format!("- **Confidence**: {:.1}%\n", finding.confidence * 100.0));
                markdown.push_str(&format!("- **Time**: {}\n", finding.timestamp.format("%Y-%m-%d %H:%M:%S UTC")));
                
                if !finding.data.is_null() {
                    markdown.push_str("- **Details**:\n");
                    markdown.push_str("```json\n");
                    markdown.push_str(&serde_json::to_string_pretty(&finding.data).unwrap_or_default());
                    markdown.push_str("\n```\n");
                }
                
                markdown.push_str("\n");
            }
        }

        // Recommendations
        markdown.push_str("## Recommendations\n\n");
        if report.summary.high_risk_findings > 0 {
            markdown.push_str("1. **Immediate Action Required**: Address all high and critical severity findings.\n");
            markdown.push_str("2. **Patch Management**: Update services to their latest secure versions.\n");
            markdown.push_str("3. **Network Segmentation**: Consider isolating critical services.\n");
        } else {
            markdown.push_str("1. **Regular Monitoring**: Continue periodic security assessments.\n");
            markdown.push_str("2. **Keep Updated**: Maintain current versions of all services.\n");
        }
        markdown.push_str("4. **Access Control**: Review and restrict unnecessary service exposure.\n");
        markdown.push_str("5. **Monitoring**: Implement security monitoring for detected services.\n\n");

        // Footer
        markdown.push_str("---\n");
        markdown.push_str(&format!(
            "*Report generated by IPCrawler v{} on {}*\n",
            report.scan_info.ipcrawler_version,
            Utc::now().format("%Y-%m-%d %H:%M:%S UTC")
        ));

        Ok(markdown)
    }
}