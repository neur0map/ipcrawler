"""
Consolidated result management for IPCrawler.
Handles saving scan results in multiple formats (JSON, TXT, HTML) to workspaces.
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod


class BaseFormatter(ABC):
    """Abstract base class for result formatters."""
    
    @abstractmethod
    def format(self, target: str, data: Dict) -> str:
        """Format scan data into the specific output format."""
        pass


class JSONFormatter(BaseFormatter):
    """Formats scan results as JSON."""
    
    def format(self, target: str, data: Dict) -> str:
        """Format scan data as JSON string."""
        return json.dumps(data, indent=2)


class TextFormatter(BaseFormatter):
    """Formats scan results as human-readable text report."""
    
    def format(self, target: str, data: Dict) -> str:
        """Generate detailed text report."""
        report = []
        report.append("IP CRAWLER SCAN REPORT")
        report.append(f"Target: {target}")
        report.append(f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Command: {data.get('command', 'N/A')}")
        report.append(f"Duration: {data.get('duration', 0):.2f} seconds")
        report.append(f"Hosts: {data.get('total_hosts', 0)} total, {data.get('up_hosts', 0)} up, {data.get('down_hosts', 0)} down")
        report.append("=" * 80)
        
        for host in data.get('hosts', []):
            report.append(f"\nHost: {host['ip']}")
            if host.get('hostname'):
                report.append(f"Hostname: {host['hostname']}")
            if host.get('os'):
                report.append(f"OS: {host['os']} (Accuracy: {host.get('os_accuracy', 'N/A')}%)")
            if host.get('mac_address'):
                report.append(f"MAC: {host['mac_address']} ({host.get('mac_vendor', 'Unknown vendor')})")
            
            # Open ports
            open_ports = [p for p in host.get('ports', []) if p.get('state') == 'open']
            if open_ports:
                report.append(f"\nOpen Ports: {len(open_ports)}")
                for port in open_ports:
                    report.append(f"  {port['port']}/{port['protocol']} - {port.get('service', 'unknown')}")
                    if port.get('version'):
                        report.append(f"    Version: {port['version']}")
                    if port.get('product'):
                        report.append(f"    Product: {port['product']}")
                    
                    # Script results
                    if port.get('scripts'):
                        for script in port['scripts']:
                            report.append(f"    Script: {script['id']}")
                            for line in script['output'].strip().split('\n'):
                                report.append(f"      {line}")
            
            report.append("-" * 80)
        
        # Add HTTP scan results if available
        if 'http_scan' in data:
            http_data = data['http_scan']
            report.append("\n" + "=" * 80)
            report.append("HTTP/HTTPS SCAN RESULTS")
            report.append("=" * 80)
            
            # Check if HTTP scan has any data
            has_data = any([
                http_data.get('services'),
                http_data.get('vulnerabilities'),
                http_data.get('dns_records'),
                http_data.get('subdomains')
            ])
            
            if not has_data:
                # Check if this was a fallback mode scan
                if http_data.get('fallback_mode'):
                    report.append("\nHTTP scan completed using fallback mode (curl+nslookup).")
                    report.append("No HTTP services found or target not responding to HTTP requests.")
                else:
                    report.append("\nNo HTTP scan data collected. This may be due to:")
                    report.append("  • Target not responding to HTTP requests")
                    report.append("  • Scanner configuration issues")
                    report.append("  • Network connectivity problems")
            else:
                # Add scan engine info if available
                scan_engine = http_data.get('scan_engine', 'unknown')
                if http_data.get('fallback_mode'):
                    report.append(f"\nHTTP scan completed using fallback mode ({scan_engine})")
                else:
                    report.append(f"\nHTTP scan completed using {scan_engine}")
            
            # HTTP Services
            services = http_data.get('services', [])
            if services:
                report.append(f"\nHTTP Services Found: {len(services)}")
                for service in services:
                    report.append(f"\n  {service.get('url', 'Unknown URL')}")
                    report.append(f"    Status: {service.get('status_code', 'N/A')}")
                    report.append(f"    Server: {service.get('server', 'Unknown')}")
                    if service.get('technologies'):
                        report.append(f"    Technologies: {', '.join(service['technologies'])}")
                    if service.get('discovered_paths'):
                        report.append(f"    Discovered Paths: {len(service['discovered_paths'])}")
                        # Show all paths in saved results, but terminal output is limited elsewhere
                        for path in service['discovered_paths']:
                            report.append(f"      • {path}")
            
            # Vulnerabilities
            vulns = http_data.get('vulnerabilities', [])
            if vulns:
                report.append(f"\nHTTP Vulnerabilities: {len(vulns)}")
                severity_order = ['critical', 'high', 'medium', 'low']
                for severity in severity_order:
                    severity_vulns = [v for v in vulns if v.get('severity') == severity]
                    if severity_vulns:
                        report.append(f"\n  {severity.upper()} ({len(severity_vulns)})")
                        for vuln in severity_vulns[:3]:  # Show first 3 of each severity
                            report.append(f"    • {vuln.get('description', 'N/A')}")
                            if vuln.get('evidence'):
                                report.append(f"      Evidence: {vuln['evidence']}")
            
            # DNS and Subdomains
            subdomains = http_data.get('subdomains', [])
            if subdomains:
                report.append(f"\nDiscovered Subdomains: {len(subdomains)}")
                for subdomain in subdomains[:10]:
                    report.append(f"  • {subdomain}")
            
            dns_records = http_data.get('dns_records', [])
            if dns_records:
                report.append(f"\nDNS Records: {len(dns_records)}")
                for record in dns_records[:10]:
                    report.append(f"  {record.get('type', 'N/A')}: {record.get('value', 'N/A')}")
        
        return "\n".join(report)


class HTMLFormatter(BaseFormatter):
    """Formats scan results as HTML report."""
    
    def format(self, target: str, data: Dict) -> str:
        """Generate HTML report with inline CSS."""
        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html>')
        html.append('<head>')
        html.append('<meta charset="UTF-8">')
        html.append(f'<title>IPCrawler Scan Report - {target}</title>')
        html.append('<style>')
        html.append('''
            body {
                font-family: 'Courier New', monospace;
                background-color: #0a0a0a;
                color: #00ff00;
                padding: 20px;
                line-height: 1.6;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1, h2, h3 {
                color: #00ff00;
                text-shadow: 0 0 10px #00ff00;
            }
            .header {
                border-bottom: 2px solid #00ff00;
                margin-bottom: 20px;
                padding-bottom: 10px;
            }
            .summary {
                background-color: #0f0f0f;
                border: 1px solid #00ff00;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .host {
                background-color: #0f0f0f;
                border: 1px solid #00ff00;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .port {
                margin-left: 20px;
                margin-bottom: 10px;
                padding: 10px;
                background-color: #1a1a1a;
                border-left: 3px solid #00ff00;
            }
            .script-output {
                background-color: #000;
                padding: 10px;
                margin-top: 5px;
                border: 1px solid #333;
                white-space: pre-wrap;
                font-size: 0.9em;
            }
            .open { color: #00ff00; }
            .closed { color: #ff0000; }
            .filtered { color: #ffff00; }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }
            th, td {
                border: 1px solid #00ff00;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #0f0f0f;
            }
            .vulnerability {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
            }
            .critical { background-color: #330000; border: 1px solid #ff0000; }
            .high { background-color: #331100; border: 1px solid #ff6600; }
            .medium { background-color: #333300; border: 1px solid #ffff00; }
            .low { background-color: #003300; border: 1px solid #00ff00; }
        ''')
        html.append('</style>')
        html.append('</head>')
        html.append('<body>')
        html.append('<div class="container">')
        
        # Header
        html.append('<div class="header">')
        html.append('<h1>IPCrawler Scan Report</h1>')
        html.append(f'<p>Target: {target}</p>')
        html.append(f'<p>Scan Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
        html.append('</div>')
        
        # Summary
        html.append('<div class="summary">')
        html.append('<h2>Scan Summary</h2>')
        html.append(f'<p>Command: {data.get("command", "N/A")}</p>')
        html.append(f'<p>Duration: {data.get("duration", 0):.2f} seconds</p>')
        html.append(f'<p>Total Hosts: {data.get("total_hosts", 0)}</p>')
        html.append(f'<p>Hosts Up: {data.get("up_hosts", 0)}</p>')
        html.append(f'<p>Hosts Down: {data.get("down_hosts", 0)}</p>')
        html.append('</div>')
        
        # Hosts
        html.append('<h2>Host Details</h2>')
        for host in data.get('hosts', []):
            html.append('<div class="host">')
            html.append(f'<h3>Host: {host["ip"]}</h3>')
            if host.get('hostname'):
                html.append(f'<p>Hostname: {host["hostname"]}</p>')
            if host.get('os'):
                html.append(f'<p>OS: {host["os"]} (Accuracy: {host.get("os_accuracy", "N/A")}%)</p>')
            if host.get('mac_address'):
                html.append(f'<p>MAC: {host["mac_address"]} ({host.get("mac_vendor", "Unknown vendor")})</p>')
            
            # Ports
            ports = host.get('ports', [])
            if ports:
                html.append('<h4>Ports</h4>')
                for port in ports:
                    state_class = port.get('state', 'closed').lower()
                    html.append(f'<div class="port">')
                    html.append(f'<p class="{state_class}">Port {port["port"]}/{port["protocol"]} - {port.get("state", "unknown")}</p>')
                    if port.get('service'):
                        html.append(f'<p>Service: {port["service"]}</p>')
                    if port.get('version'):
                        html.append(f'<p>Version: {port["version"]}</p>')
                    if port.get('product'):
                        html.append(f'<p>Product: {port["product"]}</p>')
                    
                    # Scripts
                    if port.get('scripts'):
                        for script in port['scripts']:
                            html.append(f'<p>Script: {script["id"]}</p>')
                            html.append(f'<div class="script-output">{script["output"]}</div>')
                    html.append('</div>')
            html.append('</div>')
        
        # HTTP Scan Results
        if 'http_scan' in data:
            http_data = data['http_scan']
            html.append('<div class="summary">')
            html.append('<h2>HTTP/HTTPS Scan Results</h2>')
            
            # Check if HTTP scan has any data
            has_data = any([
                http_data.get('services'),
                http_data.get('vulnerabilities'),
                http_data.get('dns_records'),
                http_data.get('subdomains')
            ])
            
            if not has_data:
                # Check if this was a fallback mode scan
                if http_data.get('fallback_mode'):
                    html.append('<p style="color: #ffff00;">ℹ HTTP scan completed using fallback mode (curl+nslookup).</p>')
                    html.append('<p>No HTTP services found or target not responding to HTTP requests.</p>')
                else:
                    html.append('<p style="color: #ffff00;">⚠ No HTTP scan data collected. This may be due to:</p>')
                    html.append('<ul>')
                    html.append('<li>Target not responding to HTTP requests</li>')
                    html.append('<li>Scanner configuration issues</li>')
                    html.append('<li>Network connectivity problems</li>')
                    html.append('</ul>')
            else:
                # Add scan engine info if available
                scan_engine = http_data.get('scan_engine', 'unknown')
                if http_data.get('fallback_mode'):
                    html.append(f'<p style="color: #00ff00;">✓ HTTP scan completed using fallback mode ({scan_engine})</p>')
                else:
                    html.append(f'<p style="color: #00ff00;">✓ HTTP scan completed using {scan_engine}</p>')
            
            # Services
            services = http_data.get('services', [])
            if services:
                html.append(f'<h3>HTTP Services ({len(services)} found)</h3>')
                html.append('<table>')
                html.append('<tr><th>URL</th><th>Status</th><th>Server</th><th>Technologies</th></tr>')
                for service in services:
                    html.append('<tr>')
                    html.append(f'<td>{service.get("url", "N/A")}</td>')
                    html.append(f'<td>{service.get("status_code", "N/A")}</td>')
                    html.append(f'<td>{service.get("server", "Unknown")}</td>')
                    html.append(f'<td>{", ".join(service.get("technologies", []))}</td>')
                    html.append('</tr>')
                html.append('</table>')
            
            # Vulnerabilities
            vulns = http_data.get('vulnerabilities', [])
            if vulns:
                html.append(f'<h3>Vulnerabilities ({len(vulns)} found)</h3>')
                for vuln in vulns:
                    severity = vuln.get('severity', 'low')
                    html.append(f'<div class="vulnerability {severity}">')
                    html.append(f'<strong>{severity.upper()}</strong>: {vuln.get("description", "N/A")}')
                    if vuln.get('evidence'):
                        html.append(f'<br>Evidence: {vuln["evidence"]}')
                    html.append('</div>')
            
            html.append('</div>')
        
        html.append('</div>')
        html.append('</body>')
        html.append('</html>')
        
        return '\n'.join(html)


class ResultManager:
    """Manages scan result saving and formatting."""
    
    def __init__(self):
        self.formatters = {
            'json': JSONFormatter(),
            'txt': TextFormatter(),
            'html': HTMLFormatter()
        }
    
    @staticmethod
    def create_workspace(target: str) -> Path:
        """Create workspace directory for scan results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workspace_name = f"scan_{target.replace('.', '_')}_{timestamp}"
        
        # Create workspaces directory with proper ownership
        base_path = Path("workspaces")
        workspace_path = base_path / workspace_name
        
        # Create directories
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # If running as sudo, change ownership to the real user
        if os.geteuid() == 0:  # Running as root
            # Get the real user ID from SUDO_UID environment variable
            sudo_uid = os.environ.get('SUDO_UID')
            sudo_gid = os.environ.get('SUDO_GID')
            
            if sudo_uid and sudo_gid:
                # Change ownership of workspaces directory and all subdirectories
                subprocess.run(['chown', '-R', f'{sudo_uid}:{sudo_gid}', str(base_path)], 
                              capture_output=True, check=False)
        
        return workspace_path
    
    @staticmethod
    def finalize_scan_data(data: Dict) -> Dict:
        """Finalize scan data by sorting ports and removing internal indexes."""
        # Sort ports for each host
        for host in data.get("hosts", []):
            if "ports" in host and host["ports"]:
                host["ports"].sort(key=lambda p: p.get("port", 0))
        
        # Remove internal index
        if "hosts_index" in data:
            del data["hosts_index"]
        
        return data
    
    def save_results(self, workspace: Path, target: str, data: Dict, 
                    formats: Optional[List[str]] = None) -> None:
        """Save scan results in specified formats."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 save_results called:")
        logger.info(f"  📂 Workspace: {workspace}")
        logger.info(f"  🎯 Target: {target}")
        logger.info(f"  📊 Data keys: {list(data.keys()) if data else 'None'}")
        logger.info(f"  📝 Formats: {formats}")
        
        # Default to all formats if none specified
        if formats is None:
            formats = ['json', 'txt', 'html']
        
        # Finalize data before saving
        data = self.finalize_scan_data(data)
        logger.info(f"  ✅ Data finalized, keys: {list(data.keys()) if data else 'None'}")
        
        # Determine file prefix
        prefix = "scan_"
        
        # Save in each requested format
        files_created = []
        for fmt in formats:
            if fmt not in self.formatters:
                logger.warning(f"  ❌ Unknown format: {fmt}")
                continue
            
            # Determine filename
            if fmt == 'json':
                filename = f"{prefix}results.json"
            elif fmt == 'txt':
                filename = f"{prefix}report.txt"
            elif fmt == 'html':
                filename = f"{prefix}report.html"
            else:
                logger.warning(f"  ❌ Unhandled format: {fmt}")
                continue
            
            filepath = workspace / filename
            logger.info(f"  📄 Creating {fmt}: {filepath}")
            
            try:
                # Format data
                formatted_content = self.formatters[fmt].format(target, data)
                logger.info(f"  📏 {fmt} content length: {len(formatted_content)} chars")
                
                # Write file with UTF-8 encoding
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)
                
                files_created.append(filepath)
                logger.info(f"  ✅ Successfully created: {filepath}")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to create {fmt} file: {e}")
                import traceback
                logger.error(f"  📍 Traceback: {traceback.format_exc()}")
        
        logger.info(f"  🎉 Total files created: {len(files_created)}")
        
        # Fix file permissions if running as sudo
        if os.geteuid() == 0:  # Running as root
            sudo_uid = os.environ.get('SUDO_UID')
            sudo_gid = os.environ.get('SUDO_GID')
            
            if sudo_uid and sudo_gid:
                logger.info(f"  🔐 Fixing permissions for sudo user {sudo_uid}:{sudo_gid}")
                # Change ownership of all created files
                for file in files_created:
                    try:
                        result = subprocess.run(['chown', f'{sudo_uid}:{sudo_gid}', str(file)], 
                                      capture_output=True, check=False)
                        if result.returncode != 0:
                            logger.warning(f"  ⚠️ chown failed for {file}: {result.stderr}")
                    except Exception as e:
                        logger.error(f"  ❌ Permission fix failed for {file}: {e}")
            else:
                logger.info(f"  ℹ️ No SUDO_UID/SUDO_GID found, skipping permission fix")
        else:
            logger.info(f"  ℹ️ Not running as root, no permission fix needed")
    
    async def save_results_async(self, workspace: Path, target: str, data: Dict, 
                               formats: Optional[List[str]] = None) -> None:
        """Asynchronously save scan results (wrapper for compatibility)."""
        # For now, just call the sync version
        # This can be enhanced later to use true async I/O if needed
        self.save_results(workspace, target, data, formats)


# Create global instance for convenience
result_manager = ResultManager()