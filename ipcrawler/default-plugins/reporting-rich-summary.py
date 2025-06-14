from ipcrawler.plugins import Report
from ipcrawler.config import config
import os, glob, re, time, html
from datetime import datetime


class RichSummary(Report):
    def __init__(self):
        super().__init__()
        self.name = "Rich Summary"
        self.slug = "rich-summary"
        self.description = "Comprehensive HTML summary report with all findings and results"
        self.tags = ["default", "report", "summary", "safe", "quick"]

    async def run(self, targets):
        for target in targets:
            # Generate individual target summary
            await self.generate_target_summary(target)

        # If multiple targets, also generate combined summary
        if len(targets) > 1:
            await self.generate_combined_summary(targets)

    async def generate_target_summary(self, target):
        """Generate comprehensive HTML summary for a single target"""

        # Create summary in the target's report directory
        summary_file = os.path.join(target.reportdir, "Full_Report.html")

        # Collect all scan results
        scan_data = await self.collect_scan_data(target)

        # Generate HTML content
        html_content = self.generate_html_report(target, scan_data, single_target=True)

        # Write the report
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"📋 Rich Summary Report generated: {summary_file}")

    async def generate_combined_summary(self, targets):
        """Generate combined HTML summary for multiple targets"""

        summary_file = os.path.join(config["output"], "Combined_Report.html")

        # Collect data for all targets
        all_data = {}
        for target in targets:
            all_data[target.address] = await self.collect_scan_data(target)

        # Generate combined HTML
        html_content = self.generate_combined_html_report(targets, all_data)

        # Write the report
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"📋 Combined Rich Summary Report generated: {summary_file}")

    async def collect_scan_data(self, target):
        """Collect all scan data for a target"""

        data = {
            "target_info": {
                "address": target.address,
                "ip": target.ip,
                "ipversion": target.ipversion,
                "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "basedir": target.basedir,
            },
            "discovered_services": target.services,
            "port_scans": {},
            "service_scans": {},
            "special_files": {},
            "file_results": {},
        }

        # Collect port scan results
        if target.scans.get("ports"):
            for scan_slug, scan_info in target.scans["ports"].items():
                if scan_info["commands"]:
                    data["port_scans"][scan_slug] = {
                        "plugin_name": scan_info["plugin"].name,
                        "commands": scan_info["commands"],
                    }

        # Collect service scan results
        if target.scans.get("services"):
            for service, service_scans in target.scans["services"].items():
                service_tag = service.tag() if hasattr(service, "tag") else str(service)
                data["service_scans"][service_tag] = {}

                for plugin_slug, plugin_info in service_scans.items():
                    if plugin_info["commands"]:
                        data["service_scans"][service_tag][plugin_slug] = {
                            "plugin_name": plugin_info["plugin"].name,
                            "commands": plugin_info["commands"],
                        }

        # Collect special files
        special_files = {
            "_manual_commands.txt": "Manual Commands",
            "_patterns.log": "Pattern Matches",
            "_commands.log": "All Commands",
            "_errors.log": "Errors & Issues",
        }

        for filename, display_name in special_files.items():
            file_path = os.path.join(target.scandir, filename)
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    data["special_files"][display_name] = f.read()

        # Collect scan result files
        if os.path.exists(target.scandir):
            for root, dirs, files in os.walk(target.scandir):
                for file in files:
                    if file.endswith((".txt", ".html", ".xml", ".json", ".log")):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, target.scandir)

                        # Skip already processed special files
                        if file in special_files:
                            continue

                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                if content.strip():  # Only include non-empty files
                                    data["file_results"][rel_path] = content
                        except Exception:
                            pass  # Skip files that can't be read

        return data

    def generate_html_report(self, target, data, single_target=True):
        """Generate the main HTML report"""

        title = f"ipcrawler Report - {target.address}" if single_target else "ipcrawler Combined Report"

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {self.get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {self.generate_header(target, data)}
        {self.generate_key_findings_section(target, data)}
        {self.generate_executive_summary(target, data)}
        {self.generate_services_section(data)}
        {self.generate_scan_results_section(data)}
        {self.generate_commands_reference_section(data)}
        {self.generate_special_files_section(data)}
        {self.generate_footer()}
    </div>
    
    <script>
        {self.get_javascript()}
    </script>
</body>
</html>"""

        return html_doc

    def generate_combined_html_report(self, targets, all_data):
        """Generate combined report for multiple targets"""

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ipcrawler Combined Report - {len(targets)} Targets</title>
    <style>
        {self.get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {self.generate_combined_header(targets)}
        {self.generate_combined_overview(targets, all_data)}
        
        <div class="targets-section">
            <h2>📋 Individual Target Reports</h2>
"""

        # Add each target as a collapsible section
        for target in targets:
            data = all_data[target.address]
            html_doc += f"""
            <div class="target-section">
                <h3 onclick="toggleSection('target-{target.address.replace(".", "-")}')" class="collapsible">
                    🎯 {target.address} {data["target_info"]["ip"]}
                </h3>
                <div id="target-{target.address.replace(".", "-")}" class="collapsible-content">
                    {self.generate_executive_summary(target, data)}
                    {self.generate_services_section(data)}
                    {self.generate_port_scans_section(data)}
                    {self.generate_service_scans_section(data)}
                    {self.generate_special_files_section(data)}
                </div>
            </div>
"""

        html_doc += f"""
        </div>
        {self.generate_footer()}
    </div>
    
    <script>
        {self.get_javascript()}
    </script>
</body>
</html>"""

        return html_doc

    def generate_header(self, target, data):
        """Generate the report header"""
        return f"""
        <div class="header">
            <h1>🕷️ ipcrawler Rich Summary Report</h1>
            <div class="target-info">
                <h2>🎯 Target: {target.address}</h2>
                <div class="info-grid">
                    <div class="info-item"><strong>IP Address:</strong> {data["target_info"]["ip"]}</div>
                    <div class="info-item"><strong>IP Version:</strong> {data["target_info"]["ipversion"]}</div>
                    <div class="info-item"><strong>Scan Time:</strong> {data["target_info"]["scan_time"]}</div>
                    <div class="info-item"><strong>Report Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
                </div>
            </div>
        </div>
        """

    def extract_key_findings(self, target, data):
        """Extract key findings from scan results"""
        findings = {
            "urls": set(),
            "domains": set(),
            "vulnerabilities": [],
            "credentials": [],
            "interesting_files": [],
            "technologies": set(),
            "cms_versions": [],
            "open_ports": [],
        }

        # Extract from discovered services
        for service in data["discovered_services"]:
            if "/" in service:
                parts = service.split("/")
                if len(parts) >= 2:
                    protocol = parts[0].upper()
                    port = parts[1]
                    service_name = parts[2] if len(parts) > 2 else "unknown"
                    findings["open_ports"].append(f"{protocol}/{port} ({service_name})")

        # Process all file results to extract findings
        all_content = ""
        for content in data["file_results"].values():
            all_content += content + "\n"
        for content in data["special_files"].values():
            all_content += content + "\n"

        # Extract URLs and domains
        import re

        # URLs
        url_patterns = [
            r'https?://[^\s<>"]+',
            r'http://[^\s<>"]+',
            r'https://[^\s<>"]+',
        ]
        for pattern in url_patterns:
            urls = re.findall(pattern, all_content, re.IGNORECASE)
            findings["urls"].update(urls)

        # Domain patterns
        domain_patterns = [
            r"([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\.htb",
            r"([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\.local",
            r"([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\.thm",
            r"[a-zA-Z0-9][a-zA-Z0-9\-]*\.htb",
            r"[a-zA-Z0-9][a-zA-Z0-9\-]*\.local",
            r"[a-zA-Z0-9][a-zA-Z0-9\-]*\.thm",
        ]
        for pattern in domain_patterns:
            domains = re.findall(pattern, all_content, re.IGNORECASE)
            findings["domains"].update([d[0] if isinstance(d, tuple) else d for d in domains])

        # Extract technologies and versions
        tech_patterns = [
            r"Server:\s*([^\r\n]+)",
            r"X-Powered-By:\s*([^\r\n]+)",
            r"Apache/([0-9.]+)",
            r"nginx/([0-9.]+)",
            r"PHP/([0-9.]+)",
            r"WordPress\s*([0-9.]+)",
            r"Drupal\s*([0-9.]+)",
            r"Joomla\s*([0-9.]+)",
        ]
        for pattern in tech_patterns:
            matches = re.findall(pattern, all_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    findings["technologies"].add(match[0])
                else:
                    findings["technologies"].add(match)

        # Extract vulnerabilities
        vuln_patterns = [
            r"CVE-\d{4}-\d{4,7}",
            r"VULNERABLE[^\r\n]*",
            r"State:\s*VULNERABLE[^\r\n]*",
            r"Exploit available[^\r\n]*",
        ]
        for pattern in vuln_patterns:
            vulns = re.findall(pattern, all_content, re.IGNORECASE)
            findings["vulnerabilities"].extend(vulns)

        # Extract credentials
        cred_patterns = [
            r"username[^\r\n]*:\s*([^\s\r\n]+)",
            r"password[^\r\n]*:\s*([^\s\r\n]+)",
            r"admin:([^\s\r\n]+)",
            r"root:([^\s\r\n]+)",
        ]
        for pattern in cred_patterns:
            creds = re.findall(pattern, all_content, re.IGNORECASE)
            findings["credentials"].extend(creds)

        # Extract interesting files
        file_patterns = [
            r"/[a-zA-Z0-9_\-./]*\.(?:txt|log|conf|config|xml|json|sql|db|backup|bak)(?:\s|$)",
            r"/admin[^\s]*",
            r"/backup[^\s]*",
            r"/config[^\s]*",
            r"/uploads[^\s]*",
        ]
        for pattern in file_patterns:
            files = re.findall(pattern, all_content, re.IGNORECASE)
            findings["interesting_files"].extend(files)

        # Clean up findings
        findings["urls"] = sorted(list(findings["urls"]))[:20]  # Limit to top 20
        findings["domains"] = sorted(list(findings["domains"]))
        findings["technologies"] = sorted(list(findings["technologies"]))
        findings["vulnerabilities"] = list(set(findings["vulnerabilities"]))[:10]
        findings["credentials"] = list(set(findings["credentials"]))[:10]
        findings["interesting_files"] = list(set(findings["interesting_files"]))[:15]

        return findings

    def generate_key_findings_section(self, target, data):
        """Generate key findings section at the top"""
        findings = self.extract_key_findings(target, data)

        html_content = """
        <div class="section key-findings">
            <h2 onclick="toggleSection('key-findings')" class="collapsible">🎯 Key Findings</h2>
            <div id="key-findings" class="collapsible-content">
                <div class="findings-grid">
"""

        # URLs Section
        if findings["urls"]:
            html_content += f"""
                    <div class="finding-card">
                        <h3>🌐 URLs Discovered</h3>
                        <div class="finding-list">
"""
            for url in findings["urls"]:
                html_content += f'<div class="finding-item url-item"><a href="{html.escape(url)}" target="_blank">{html.escape(url)}</a></div>'
            html_content += """
                        </div>
                    </div>
"""

        # Domains Section
        if findings["domains"]:
            html_content += f"""
                    <div class="finding-card">
                        <h3>🏷️ Domains & Subdomains</h3>
                        <div class="finding-list">
"""
            for domain in findings["domains"]:
                html_content += f'<div class="finding-item domain-item">{html.escape(domain)}</div>'
            html_content += """
                        </div>
                    </div>
"""

        # Vulnerabilities Section
        if findings["vulnerabilities"]:
            html_content += f"""
                    <div class="finding-card vuln-card">
                        <h3>🚨 Vulnerabilities</h3>
                        <div class="finding-list">
"""
            for vuln in findings["vulnerabilities"]:
                html_content += f'<div class="finding-item vuln-item">{html.escape(vuln)}</div>'
            html_content += """
                        </div>
                    </div>
"""

        # Technologies Section
        if findings["technologies"]:
            html_content += f"""
                    <div class="finding-card">
                        <h3>🔧 Technologies</h3>
                        <div class="finding-list">
"""
            for tech in findings["technologies"]:
                html_content += f'<div class="finding-item tech-item">{html.escape(tech)}</div>'
            html_content += """
                        </div>
                    </div>
"""

        # Interesting Files Section
        if findings["interesting_files"]:
            html_content += f"""
                    <div class="finding-card">
                        <h3>📁 Interesting Files</h3>
                        <div class="finding-list">
"""
            for file in findings["interesting_files"]:
                html_content += f'<div class="finding-item file-item">{html.escape(file.strip())}</div>'
            html_content += """
                        </div>
                    </div>
"""

        # Credentials Section
        if findings["credentials"]:
            html_content += f"""
                    <div class="finding-card cred-card">
                        <h3>🔑 Potential Credentials</h3>
                        <div class="finding-list">
"""
            for cred in findings["credentials"]:
                html_content += f'<div class="finding-item cred-item">{html.escape(cred)}</div>'
            html_content += """
                        </div>
                    </div>
"""

        html_content += """
                </div>
            </div>
        </div>
        """

        return html_content

    def generate_combined_header(self, targets):
        """Generate header for combined report"""
        return f"""
        <div class="header">
            <h1>🕷️ ipcrawler Combined Report</h1>
            <div class="combined-info">
                <h2>📊 Scanning Summary</h2>
                <div class="info-grid">
                    <div class="info-item"><strong>Total Targets:</strong> {len(targets)}</div>
                    <div class="info-item"><strong>Targets:</strong> {", ".join([t.address for t in targets])}</div>
                    <div class="info-item"><strong>Report Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
                </div>
            </div>
        </div>
        """

    def generate_executive_summary(self, target, data):
        """Generate executive summary section"""

        total_services = len(data["discovered_services"])
        total_port_scans = len(data["port_scans"])
        total_service_scans = sum(len(scans) for scans in data["service_scans"].values())
        total_files = len(data["file_results"])

        services_list = ", ".join(data["discovered_services"]) if data["discovered_services"] else "None discovered"

        return f"""
        <div class="section">
            <h2 onclick="toggleSection('executive-summary')" class="collapsible">📊 Executive Summary</h2>
            <div id="executive-summary" class="collapsible-content">
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="summary-number">{total_services}</div>
                        <div class="summary-label">Services Discovered</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-number">{total_port_scans}</div>
                        <div class="summary-label">Port Scans Executed</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-number">{total_service_scans}</div>
                        <div class="summary-label">Service Scans Executed</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-number">{total_files}</div>
                        <div class="summary-label">Result Files Generated</div>
                    </div>
                </div>
                
                <div class="services-discovered">
                    <h3>🔍 Discovered Services</h3>
                    <div class="services-list">{services_list}</div>
                </div>
            </div>
        </div>
        """

    def generate_combined_overview(self, targets, all_data):
        """Generate overview for combined report"""

        total_services = sum(len(data["discovered_services"]) for data in all_data.values())
        all_services = set()
        for data in all_data.values():
            all_services.update(data["discovered_services"])

        unique_services = len(all_services)

        html_overview = f"""
        <div class="section">
            <h2 onclick="toggleSection('combined-overview')" class="collapsible">📊 Combined Overview</h2>
            <div id="combined-overview" class="collapsible-content">
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="summary-number">{len(targets)}</div>
                        <div class="summary-label">Total Targets</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-number">{total_services}</div>
                        <div class="summary-label">Total Services Found</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-number">{unique_services}</div>
                        <div class="summary-label">Unique Services</div>
                    </div>
                </div>
                
                <div class="targets-overview">
                    <h3>🎯 Targets Overview</h3>
                    <table class="results-table">
                        <thead>
                            <tr>
                                <th>Target</th>
                                <th>IP Address</th>
                                <th>Services Found</th>
                                <th>Key Services</th>
                            </tr>
                        </thead>
                        <tbody>
"""

        for target in targets:
            data = all_data[target.address]
            services_count = len(data["discovered_services"])
            key_services = ", ".join(data["discovered_services"][:5])  # Show first 5
            if len(data["discovered_services"]) > 5:
                key_services += f" (+{len(data['discovered_services']) - 5} more)"

            html_overview += f"""
                            <tr>
                                <td><strong>{target.address}</strong></td>
                                <td>{data["target_info"]["ip"]}</td>
                                <td>{services_count}</td>
                                <td>{key_services or "None"}</td>
                            </tr>
"""

        html_overview += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """

        return html_overview

    def generate_services_section(self, data):
        """Generate discovered services section"""

        if not data["discovered_services"]:
            return '<div class="section"><h2>🔍 No Services Discovered</h2></div>'

        html_content = f"""
        <div class="section">
            <h2 onclick="toggleSection('services')" class="collapsible">🔍 Discovered Services ({len(data["discovered_services"])})</h2>
            <div id="services" class="collapsible-content">
                <div class="services-grid">
"""

        for service in data["discovered_services"]:
            # Parse service for better display
            parts = service.split("/")
            if len(parts) >= 3:
                protocol = parts[0]
                port = parts[1]
                service_name = parts[2]

                html_content += f"""
                    <div class="service-card">
                        <div class="service-port">{protocol.upper()}/{port}</div>
                        <div class="service-name">{service_name}</div>
                    </div>
"""
            else:
                html_content += f"""
                    <div class="service-card">
                        <div class="service-name">{service}</div>
                    </div>
"""

        html_content += """
                </div>
            </div>
        </div>
        """

        return html_content

    def generate_scan_results_section(self, data):
        """Generate scan results section - focuses on findings, not commands"""

        if not data["file_results"]:
            return ""

        html_content = f"""
        <div class="section">
            <h2 onclick="toggleSection('scan-results')" class="collapsible">📊 Scan Results & Findings ({len(data["file_results"])} files)</h2>
            <div id="scan-results" class="collapsible-content">
"""

        # Group files by directory
        file_groups = {}
        for file_path, content in data["file_results"].items():
            dir_name = os.path.dirname(file_path) or "root"
            if dir_name not in file_groups:
                file_groups[dir_name] = []
            file_groups[dir_name].append((file_path, content))

        for dir_name, files in file_groups.items():
            dir_id = dir_name.replace("/", "-").replace(" ", "-")
            html_content += f"""
                <div class="results-group">
                    <h3 onclick="toggleSection('results-{dir_id}')" class="results-header">
                        📁 {dir_name}/ Results ({len(files)} files)
                    </h3>
                    <div id="results-{dir_id}" class="results-content">
"""

            for file_path, content in files:
                file_name = os.path.basename(file_path)
                file_id = file_path.replace("/", "-").replace(".", "-")

                # Extract key findings from this file
                key_lines = self.extract_interesting_lines(content)

                html_content += f"""
                        <div class="result-file">
                            <h4 onclick="toggleSection('result-{file_id}')" class="file-header">
                                📄 {file_name} - Key Findings
                            </h4>
                            <div id="result-{file_id}" class="file-content">
"""

                if key_lines:
                    html_content += '<div class="key-findings-box">'
                    for line in key_lines[:20]:  # Show top 20 interesting lines
                        escaped_line = html.escape(line.strip())
                        html_content += f'<div class="key-line">{escaped_line}</div>'
                    html_content += "</div>"

                html_content += f"""
                                <div class="full-output-toggle">
                                    <button onclick="toggleFullOutput('full-{file_id}')" class="toggle-btn">
                                        📄 Show Full Output ({len(content.splitlines())} lines)
                                    </button>
                                    <div id="full-{file_id}" class="full-output" style="display: none;">
                                        <pre class="file-text">{html.escape(content)}</pre>
                                    </div>
                                </div>
                            </div>
                        </div>
"""

            html_content += """
                    </div>
                </div>
"""

        html_content += """
            </div>
        </div>
        """

        return html_content

    def extract_interesting_lines(self, content):
        """Extract the most interesting lines from scan output"""
        lines = content.splitlines()
        interesting = []

        # Patterns for interesting information
        patterns = [
            r"http[s]?://[^\s]+",  # URLs
            r"\d+/tcp\s+open",  # Open ports
            r"\d+/udp\s+open",  # Open UDP ports
            r"CVE-\d{4}-\d{4,7}",  # CVEs
            r"VULNERABLE",  # Vulnerabilities
            r"Server:\s*[^\r\n]+",  # Server headers
            r"Location:\s*[^\r\n]+",  # Redirects
            r"Title:\s*[^\r\n]+",  # Page titles
            r"/[a-zA-Z0-9_\-/]+\.(php|asp|aspx|jsp|cgi|pl)",  # Interesting files
            r"admin|login|password|config|backup",  # Interesting keywords
            r"Directory listing|Index of",  # Directory listings
            r"Error|Exception|Warning.*:",  # Errors that might reveal info
            r"SQL|MySQL|PostgreSQL|Oracle",  # Database info
            r"WordPress|Drupal|Joomla",  # CMS detection
        ]

        for line in lines:
            line = line.strip()
            if len(line) < 5:  # Skip very short lines
                continue

            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    interesting.append(line)
                    break

        # Also include lines with specific keywords
        keyword_lines = []
        keywords = ["discovered", "found", "detected", "identified", "vulnerable", "exploit", "shell", "flag"]
        for line in lines:
            if any(keyword in line.lower() for keyword in keywords):
                keyword_lines.append(line.strip())

        interesting.extend(keyword_lines)

        # Remove duplicates and return
        return list(dict.fromkeys(interesting))

    def generate_commands_reference_section(self, data):
        """Generate commands reference section - moved to bottom"""

        if not data["port_scans"] and not data["service_scans"]:
            return ""

        total_commands = len(data["port_scans"]) + sum(len(scans) for scans in data["service_scans"].values())

        html_content = f"""
        <div class="section commands-section">
            <h2 onclick="toggleSection('commands-ref')" class="collapsible">⚡ Commands Reference ({total_commands} scans)</h2>
            <div id="commands-ref" class="collapsible-content" style="display: none;">
                <p class="section-note">📝 This section shows the exact commands that were executed during the scan.</p>
"""

        # Port scans
        if data["port_scans"]:
            html_content += f"""
                <div class="commands-group">
                    <h3 onclick="toggleSection('port-commands')" class="commands-header">
                        🔍 Port Scan Commands ({len(data["port_scans"])})
                    </h3>
                    <div id="port-commands" class="commands-content" style="display: none;">
"""

            for scan_slug, scan_info in data["port_scans"].items():
                html_content += f"""
                        <div class="command-item">
                            <h4>{scan_info["plugin_name"]} ({scan_slug})</h4>
"""

                for command in scan_info["commands"]:
                    cmd_text = html.escape(command[0]) if command[0] else "No command recorded"
                    html_content += f'<div class="command"><code>{cmd_text}</code></div>'

                html_content += "</div>"

            html_content += "</div></div>"

        # Service scans
        if data["service_scans"]:
            total_service_scans = sum(len(scans) for scans in data["service_scans"].values())
            html_content += f"""
                <div class="commands-group">
                    <h3 onclick="toggleSection('service-commands')" class="commands-header">
                        🔧 Service Scan Commands ({total_service_scans})
                    </h3>
                    <div id="service-commands" class="commands-content" style="display: none;">
"""

            for service_tag, service_scans in data["service_scans"].items():
                html_content += f"""
                        <div class="service-commands">
                            <h4>{service_tag} Commands</h4>
"""

                for plugin_slug, plugin_info in service_scans.items():
                    html_content += f"""
                            <div class="command-item">
                                <h5>{plugin_info["plugin_name"]} ({plugin_slug})</h5>
"""

                    for command in plugin_info["commands"]:
                        cmd_text = html.escape(command[0]) if command[0] else "No command recorded"
                        html_content += f'<div class="command"><code>{cmd_text}</code></div>'

                    html_content += "</div>"

                html_content += "</div>"

            html_content += "</div></div>"

        html_content += """
            </div>
        </div>
        """

        return html_content

    def generate_special_files_section(self, data):
        """Generate special files section"""

        if not data["special_files"]:
            return ""

        html_content = f"""
        <div class="section">
            <h2 onclick="toggleSection('special-files')" class="collapsible">📋 Key Files & Logs ({len(data["special_files"])})</h2>
            <div id="special-files" class="collapsible-content">
"""

        for display_name, content in data["special_files"].items():
            content_escaped = html.escape(content)

            html_content += f"""
                <div class="special-file">
                    <h3 onclick="toggleSection('file-{display_name.replace(" ", "-").lower()}')" class="file-header">
                        📄 {display_name} ({len(content.splitlines())} lines)
                    </h3>
                    <div id="file-{display_name.replace(" ", "-").lower()}" class="file-content">
                        <pre class="file-text">{content_escaped}</pre>
                    </div>
                </div>
"""

        html_content += """
            </div>
        </div>
        """

        return html_content

    def generate_detailed_results_section(self, data):
        """Generate detailed scan results section"""

        if not data["file_results"]:
            return ""

        html_content = f"""
        <div class="section">
            <h2 onclick="toggleSection('detailed-results')" class="collapsible">📁 Detailed Scan Results ({len(data["file_results"])} files)</h2>
            <div id="detailed-results" class="collapsible-content">
                <div class="files-grid">
"""

        # Group files by directory
        file_groups = {}
        for file_path, content in data["file_results"].items():
            dir_name = os.path.dirname(file_path) or "root"
            if dir_name not in file_groups:
                file_groups[dir_name] = []
            file_groups[dir_name].append((file_path, content))

        for dir_name, files in file_groups.items():
            dir_id = dir_name.replace("/", "-").replace(" ", "-")
            html_content += f"""
                <div class="file-group">
                    <h3 onclick="toggleSection('dir-{dir_id}')" class="dir-header">
                        📁 {dir_name}/ ({len(files)} files)
                    </h3>
                    <div id="dir-{dir_id}" class="dir-content">
"""

            for file_path, content in files:
                file_name = os.path.basename(file_path)
                file_id = file_path.replace("/", "-").replace(".", "-")
                content_escaped = html.escape(content)

                html_content += f"""
                        <div class="result-file">
                            <h4 onclick="toggleSection('file-{file_id}')" class="file-header">
                                📄 {file_name} ({len(content)} chars)
                            </h4>
                            <div id="file-{file_id}" class="file-content">
                                <div class="file-info">
                                    <strong>Path:</strong> {file_path}<br>
                                    <strong>Size:</strong> {len(content)} characters, {len(content.splitlines())} lines
                                </div>
                                <pre class="file-text">{content_escaped}</pre>
                            </div>
                        </div>
"""

            html_content += """
                    </div>
                </div>
"""

        html_content += """
                </div>
            </div>
        </div>
        """

        return html_content

    def generate_footer(self):
        """Generate report footer"""
        return f"""
        <div class="footer">
            <hr>
            <p>📋 Generated by <strong>ipcrawler Rich Summary</strong> plugin on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")}</p>
            <p>🔍 Based on AutoRecon by Tib3rius | Enhanced for OSCP & CTF environments</p>
        </div>
        """

    def get_css_styles(self):
        """Return CSS styles for the HTML report"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            border-radius: 10px;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header h2 {
            font-size: 1.5em;
            margin-bottom: 20px;
            opacity: 0.9;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .info-item {
            background: rgba(255,255,255,0.1);
            padding: 10px 15px;
            border-radius: 5px;
            backdrop-filter: blur(10px);
        }
        
        .section {
            margin-bottom: 30px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .collapsible {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            cursor: pointer;
            padding: 18px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 1.2em;
            font-weight: bold;
            transition: background 0.3s;
            margin: 0;
        }
        
        .collapsible:hover {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .collapsible-content {
            padding: 20px;
            display: block;
            background: #f9f9f9;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 4px solid #4facfe;
        }
        
        .summary-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #4facfe;
            margin-bottom: 5px;
        }
        
        .summary-label {
            color: #666;
            font-weight: 500;
        }
        
        .services-discovered {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .services-discovered h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .services-list {
            background: #f0f8ff;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #4facfe;
            font-family: 'Courier New', monospace;
        }
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .service-card {
            background: white;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #00c851;
            text-align: center;
        }
        
        .service-port {
            font-size: 1.1em;
            font-weight: bold;
            color: #00c851;
            margin-bottom: 5px;
        }
        
        .service-name {
            color: #666;
            font-size: 0.9em;
        }
        
        .scan-item, .service-group, .special-file, .file-group, .result-file {
            background: white;
            border-radius: 6px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .scan-header, .service-header, .file-header, .dir-header {
            background: #f8f9fa;
            padding: 12px 15px;
            cursor: pointer;
            border-bottom: 1px solid #e0e0e0;
            font-size: 1.1em;
            color: #333;
            transition: background 0.3s;
        }
        
        .scan-header:hover, .service-header:hover, .file-header:hover, .dir-header:hover {
            background: #e9ecef;
        }
        
        .scan-content, .service-scans-content, .file-content, .dir-content {
            padding: 15px;
        }
        
        .commands-executed h4, .commands-executed h5 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .command {
            background: #2d3748;
            color: #e2e8f0;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 8px;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
        }
        
        .command code {
            background: none;
            color: inherit;
            padding: 0;
        }
        
        .file-text {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.4;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .file-info {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 10px;
            font-size: 0.9em;
            color: #666;
        }
        
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: white;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .results-table th {
            background: #4facfe;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        
        .results-table td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .results-table tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        .results-table tr:hover {
            background: #e3f2fd;
        }
        
        .target-section {
            margin-bottom: 40px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }
        
        .footer {
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 40px;
            padding: 20px;
        }
        
        .footer hr {
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, #ddd, transparent);
            margin-bottom: 20px;
        }
        
        /* Key Findings Styles */
        .key-findings {
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
            border: 2px solid #ff6b6b;
        }
        
        .findings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .finding-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #4facfe;
        }
        
        .finding-card.vuln-card {
            border-left-color: #ff4757;
            background: linear-gradient(135deg, #fff 0%, #ffebee 100%);
        }
        
        .finding-card.cred-card {
            border-left-color: #ffa726;
            background: linear-gradient(135deg, #fff 0%, #fff3e0 100%);
        }
        
        .finding-card h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.2em;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }
        
        .finding-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .finding-item {
            background: #f8f9fa;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 3px solid #4facfe;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .finding-item.url-item {
            border-left-color: #2ecc71;
        }
        
        .finding-item.url-item a {
            color: #2ecc71;
            text-decoration: none;
            font-weight: bold;
        }
        
        .finding-item.url-item a:hover {
            text-decoration: underline;
        }
        
        .finding-item.domain-item {
            border-left-color: #3498db;
            color: #2980b9;
            font-weight: bold;
        }
        
        .finding-item.vuln-item {
            border-left-color: #e74c3c;
            background: #fff5f5;
            color: #c53030;
            font-weight: bold;
        }
        
        .finding-item.tech-item {
            border-left-color: #9b59b6;
            color: #8e44ad;
        }
        
        .finding-item.file-item {
            border-left-color: #f39c12;
            color: #d68910;
        }
        
        .finding-item.cred-item {
            border-left-color: #ff6348;
            background: #fff8f5;
            color: #d63031;
            font-weight: bold;
        }
        
        /* Scan Results Styles */
        .results-group, .commands-group {
            background: white;
            border-radius: 6px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .results-header, .commands-header {
            background: #e3f2fd;
            padding: 12px 15px;
            cursor: pointer;
            border-bottom: 1px solid #e0e0e0;
            font-size: 1.1em;
            color: #1976d2;
            transition: background 0.3s;
        }
        
        .results-header:hover, .commands-header:hover {
            background: #bbdefb;
        }
        
        .results-content, .commands-content {
            padding: 15px;
        }
        
        .key-findings-box {
            background: linear-gradient(135deg, #e8f5e8 0%, #f0fff0 100%);
            border: 2px solid #4caf50;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .key-line {
            background: white;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 4px;
            border-left: 4px solid #4caf50;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #2e7d32;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .full-output-toggle {
            margin-top: 15px;
        }
        
        .toggle-btn {
            background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s;
        }
        
        .toggle-btn:hover {
            background: linear-gradient(135deg, #495057 0%, #343a40 100%);
            transform: translateY(-1px);
        }
        
        .full-output {
            margin-top: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: #f8f9fa;
        }
        
        .commands-section {
            opacity: 0.8;
        }
        
        .section-note {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-style: italic;
        }
        
        .command-item {
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #6c757d;
        }
        
        .command-item h4, .command-item h5 {
            color: #495057;
            margin-bottom: 10px;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                padding: 15px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .info-grid {
                grid-template-columns: 1fr;
            }
            
            .summary-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
            
            .services-grid {
                grid-template-columns: 1fr;
            }
        }
        
        /* Print styles */
        @media print {
            body {
                background: white;
            }
            
            .container {
                box-shadow: none;
                margin: 0;
            }
            
            .collapsible-content {
                display: block !important;
            }
        }
        """

    def get_javascript(self):
        """Return JavaScript for interactive features"""
        return """
        function toggleSection(sectionId) {
            const content = document.getElementById(sectionId);
            if (content) {
                if (content.style.display === 'none') {
                    content.style.display = 'block';
                } else {
                    content.style.display = 'none';
                }
            }
        }
        
        function toggleFullOutput(outputId) {
            const output = document.getElementById(outputId);
            const button = event.target;
            
            if (output.style.display === 'none') {
                output.style.display = 'block';
                button.textContent = button.textContent.replace('Show', 'Hide');
            } else {
                output.style.display = 'none';
                button.textContent = button.textContent.replace('Hide', 'Show');
            }
        }
        
        // Initialize sections - Key findings expanded, others based on importance
        document.addEventListener('DOMContentLoaded', function() {
            // Always expand key findings
            const keyFindings = document.getElementById('key-findings');
            if (keyFindings) {
                keyFindings.style.display = 'block';
            }
            
            // Expand executive summary and services
            const important = ['executive-summary', 'services', 'scan-results'];
            important.forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    element.style.display = 'block';
                }
            });
            
            // Keep commands section collapsed by default (less important)
            const commandsRef = document.getElementById('commands-ref');
            if (commandsRef) {
                commandsRef.style.display = 'none';
            }
            
            // Keep special files expanded
            const specialFiles = document.getElementById('special-files');
            if (specialFiles) {
                specialFiles.style.display = 'block';
            }
        });
        """
