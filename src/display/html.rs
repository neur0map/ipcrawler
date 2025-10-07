use crate::parser::ExtractedEntities;
use crate::storage::{OutputManager, ScanReport};
use anyhow::Result;
use tokio::fs;

pub struct HtmlReport;

impl HtmlReport {
    pub async fn generate(
        report: &ScanReport,
        entities: &ExtractedEntities,
        output_manager: &OutputManager,
    ) -> Result<()> {
        let html = Self::build_html(report, entities);
        let report_path = output_manager.get_html_report_file();

        fs::write(&report_path, html).await?;

        println!("HTML report saved: {}", report_path.display());
        Ok(())
    }

    fn build_html(report: &ScanReport, entities: &ExtractedEntities) -> String {
        format!(
            r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPCrawler Scan Report - {target}</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="container">
        {header}
        {summary}
        {entities_section}
        {tools_section}
        {footer}
    </div>
</body>
</html>"#,
            target = report.target,
            css = Self::get_css(),
            header = Self::build_header(&report.target),
            summary = Self::build_summary(report),
            entities_section = Self::build_entities(entities),
            tools_section = Self::build_tools(&report.tools_executed),
            footer = Self::build_footer(),
        )
    }

    fn get_css() -> &'static str {
        r#"
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .header h1 { color: white; font-size: 2.5em; margin-bottom: 10px; }
        .header .target { color: #fbbf24; font-size: 1.3em; font-weight: 500; }
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        .card h2 {
            color: #58a6ff;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #30363d;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .stat-box {
            background: #0d1117;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #58a6ff;
        }
        .stat-box.critical { border-left-color: #f85149; }
        .stat-box.success { border-left-color: #3fb950; }
        .stat-label { font-size: 0.9em; color: #8b949e; margin-bottom: 5px; }
        .stat-value { font-size: 2em; font-weight: bold; color: #c9d1d9; }
        .list-section { margin: 20px 0; }
        .list-section h3 { color: #79c0ff; margin-bottom: 15px; font-size: 1.3em; }
        .item {
            background: #0d1117;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 3px solid #30363d;
        }
        .item.vuln-critical { border-left-color: #f85149; background: rgba(248, 81, 73, 0.1); }
        .item.vuln-high { border-left-color: #ff7b72; background: rgba(255, 123, 114, 0.1); }
        .item.vuln-medium { border-left-color: #d29922; background: rgba(210, 153, 34, 0.1); }
        .item.vuln-low { border-left-color: #9e6a03; background: rgba(158, 106, 3, 0.1); }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }
        .badge.critical { background: #f85149; color: white; }
        .badge.high { background: #ff7b72; color: white; }
        .badge.medium { background: #d29922; color: white; }
        .badge.low { background: #9e6a03; color: white; }
        .badge.success { background: #3fb950; color: white; }
        .badge.error { background: #f85149; color: white; }
        .port-list { display: flex; flex-wrap: wrap; gap: 15px; }
        .port-item {
            background: #0d1117;
            padding: 15px 20px;
            border-radius: 6px;
            border: 1px solid #30363d;
            min-width: 200px;
        }
        .port-number { font-size: 1.5em; color: #fbbf24; font-weight: bold; }
        .port-service { color: #79c0ff; font-size: 1.1em; }
        .port-version { color: #8b949e; font-size: 0.9em; }
        .url-link { color: #58a6ff; text-decoration: none; word-break: break-all; }
        .url-link:hover { text-decoration: underline; }
        .footer {
            text-align: center;
            padding: 30px;
            color: #8b949e;
            font-size: 0.9em;
            border-top: 1px solid #30363d;
            margin-top: 40px;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #8b949e;
            font-style: italic;
        }
        "#
    }

    fn build_header(target: &str) -> String {
        format!(
            r#"
        <div class="header">
            <h1>🎯 IPCrawler Security Scan</h1>
            <div class="target">Target: {}</div>
        </div>
        "#,
            target
        )
    }

    fn build_summary(report: &ScanReport) -> String {
        let vuln_class = if report.summary.total_vulnerabilities > 0 {
            "critical"
        } else {
            "success"
        };

        format!(
            r#"
        <div class="card">
            <h2>📊 Summary</h2>
            <div class="summary-grid">
                <div class="stat-box">
                    <div class="stat-label">Duration</div>
                    <div class="stat-value">{}s</div>
                </div>
                <div class="stat-box success">
                    <div class="stat-label">Tools Executed</div>
                    <div class="stat-value">{}/{}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">IPs Found</div>
                    <div class="stat-value">{}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Domains Found</div>
                    <div class="stat-value">{}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">URLs Found</div>
                    <div class="stat-value">{}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Open Ports</div>
                    <div class="stat-value">{}</div>
                </div>
                <div class="stat-box {}">
                    <div class="stat-label">Vulnerabilities</div>
                    <div class="stat-value">{}</div>
                </div>
            </div>
        </div>
        "#,
            report.duration,
            report.summary.successful_tools,
            report.summary.total_tools,
            report.summary.total_ips,
            report.summary.total_domains,
            report.summary.total_urls,
            report.summary.total_ports,
            vuln_class,
            report.summary.total_vulnerabilities,
        )
    }

    fn build_entities(entities: &ExtractedEntities) -> String {
        let mut html = String::new();

        // Vulnerabilities
        html.push_str(&Self::build_vulnerabilities(&entities.vulnerabilities));

        // Ports
        html.push_str(&Self::build_ports(&entities.ports));

        // URLs
        html.push_str(&Self::build_urls(&entities.urls));

        // IPs and Domains
        html.push_str(&Self::build_ips_domains(&entities.ips, &entities.domains));

        // Findings
        html.push_str(&Self::build_findings(&entities.findings));

        html
    }

    fn build_vulnerabilities(vulns: &[crate::parser::Vulnerability]) -> String {
        if vulns.is_empty() {
            return r#"
        <div class="card">
            <h2>✅ Vulnerabilities</h2>
            <div class="empty-state">No vulnerabilities detected</div>
        </div>
        "#
            .to_string();
        }

        let mut items = String::new();
        for vuln in vulns {
            let class = match vuln.severity.to_lowercase().as_str() {
                "critical" => "vuln-critical",
                "high" => "vuln-high",
                "medium" => "vuln-medium",
                "low" => "vuln-low",
                _ => "",
            };

            items.push_str(&format!(
                r#"
            <div class="item {}">
                <strong>{}</strong>
                <span class="badge {}">{}</span>
                <p style="margin-top: 10px; color: #8b949e;">{}</p>
            </div>
            "#,
                class,
                vuln.name,
                vuln.severity.to_lowercase(),
                vuln.severity.to_uppercase(),
                vuln.description
            ));
        }

        format!(
            r#"
        <div class="card">
            <h2>⚠️ Vulnerabilities ({})</h2>
            {}
        </div>
        "#,
            vulns.len(),
            items
        )
    }

    fn build_ports(ports: &[crate::parser::PortInfo]) -> String {
        if ports.is_empty() {
            return String::new();
        }

        let mut items = String::new();
        for port in ports {
            let service = port.service.as_deref().unwrap_or("unknown");
            let version = port.version.as_deref().unwrap_or("").to_string();

            items.push_str(&format!(
                r#"
            <div class="port-item">
                <div class="port-number">{}</div>
                <div class="port-service">{}</div>
                <div class="port-version">{}</div>
            </div>
            "#,
                port.port, service, version
            ));
        }

        format!(
            r#"
        <div class="card">
            <h2>🔌 Open Ports ({})</h2>
            <div class="port-list">
                {}
            </div>
        </div>
        "#,
            ports.len(),
            items
        )
    }

    fn build_urls(urls: &[String]) -> String {
        if urls.is_empty() {
            return String::new();
        }

        let mut items = String::new();
        for url in urls {
            items.push_str(&format!(
                r#"
            <div class="item">
                <a href="{}" class="url-link" target="_blank">{}</a>
            </div>
            "#,
                url, url
            ));
        }

        format!(
            r#"
        <div class="card">
            <h2>🌍 URLs Found ({})</h2>
            {}
        </div>
        "#,
            urls.len(),
            items
        )
    }

    fn build_ips_domains(ips: &[String], domains: &[String]) -> String {
        let mut html = String::new();

        if !ips.is_empty() {
            let mut items = String::new();
            for ip in ips {
                items.push_str(&format!(r#"<div class="item">{}</div>"#, ip));
            }
            html.push_str(&format!(
                r#"
        <div class="card">
            <h2>🌐 IP Addresses ({})</h2>
            {}
        </div>
        "#,
                ips.len(),
                items
            ));
        }

        if !domains.is_empty() {
            let mut items = String::new();
            for domain in domains {
                items.push_str(&format!(r#"<div class="item">{}</div>"#, domain));
            }
            html.push_str(&format!(
                r#"
        <div class="card">
            <h2>🔗 Domains ({})</h2>
            {}
        </div>
        "#,
                domains.len(),
                items
            ));
        }

        html
    }

    fn build_findings(findings: &[String]) -> String {
        if findings.is_empty() {
            return String::new();
        }

        let mut items = String::new();
        for finding in findings {
            items.push_str(&format!(r#"<div class="item">{}</div>"#, finding));
        }

        format!(
            r#"
        <div class="card">
            <h2>📋 Other Findings ({})</h2>
            {}
        </div>
        "#,
            findings.len(),
            items
        )
    }

    fn build_tools(tools: &[crate::storage::ToolExecution]) -> String {
        let mut items = String::new();
        for tool in tools {
            let badge_class = if tool.success { "success" } else { "error" };
            let badge_text = if tool.success { "SUCCESS" } else { "FAILED" };

            items.push_str(&format!(
                r#"
            <div class="item">
                <strong>{}</strong>
                <span class="badge {}">{}</span>
                <span style="color: #8b949e; margin-left: 15px;">{:.2}s</span>
            </div>
            "#,
                tool.name, badge_class, badge_text, tool.duration_secs
            ));
        }

        format!(
            r#"
        <div class="card">
            <h2>🔧 Tools Executed</h2>
            {}
        </div>
        "#,
            items
        )
    }

    fn build_footer() -> &'static str {
        r#"
        <div class="footer">
            Generated by IPCrawler • Intelligent Penetration Testing Scanner
        </div>
        "#
    }
}
