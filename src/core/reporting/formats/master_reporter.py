"""Master report generator for IPCrawler

Generates comprehensive master reports (HTML and TXT) combining all workflow results.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from ..base.reporter import BaseReporter
from ..templates.engine import get_template_engine
from src.core.ui.console.base import console


class MasterReporter(BaseReporter):
    """Generates comprehensive master HTML report combining all workflows"""
    
    def __init__(self, output_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize master reporter
        
        Args:
            output_dir: Directory to save master report
            theme: Theme to use for styling
        """
        super().__init__(output_dir)
        self.theme = theme
        self.template_engine = get_template_engine(theme)
        console.debug(f"Master reporter initialized with theme '{theme}'")
    
    def get_format(self) -> str:
        """Get the report format name"""
        return 'master_html'
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate comprehensive master HTML report
        
        Args:
            data: Combined scan data from all workflows
            **kwargs: Additional options (target, timestamp)
            
        Returns:
            Path to generated master HTML report
        """
        self.ensure_output_dir()
        
        # Prepare comprehensive context
        context = self._prepare_master_context(data, **kwargs)
        
        # Generate filename
        target = kwargs.get('target', data.get('target', 'unknown'))
        filename = f"master_report_{self._sanitize_filename(target)}.html"
        output_path = self.output_dir / filename
        
        try:
            # Render comprehensive template
            html_content = self.template_engine.render_template(
                'workflows/comprehensive_report.html.j2', 
                context
            )
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            console.success(f"Generated master HTML report: {output_path}", internal=True)
            return output_path
            
        except Exception as e:
            console.error(f"Failed to generate master HTML report: {e}", internal=True)
            # Fallback to simple master report
            return self._generate_simple_master_report(data, output_path, **kwargs)
    
    def _prepare_master_context(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare comprehensive context for master report"""
        target = kwargs.get('target', data.get('target', 'Unknown'))
        
        # Base context
        context = {
            'data': data,
            'target': target,
            'title': f'IPCrawler Security Assessment - {target}',
            'workflow': 'comprehensive',
            'generated': datetime.now(),
        }
        
        # Aggregate summary from all workflows
        context['summary'] = self._build_comprehensive_summary(data)
        
        # Extract and organize workflow data
        context['hosts'] = data.get('hosts', [])
        context['http_scan'] = data.get('http_scan', {})
        context['mini_spider'] = data.get('mini_spider', {})
        context['smartlist'] = data.get('smartlist', {})
        
        # Add metadata
        context['metadata'] = {
            'generator': 'IPCrawler',
            'timestamp': datetime.now(),
            'target': target,
            'workflows_included': self._get_included_workflows(data)
        }
        
        return context
    
    def _build_comprehensive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive summary from all workflow data"""
        summary = {
            'total_hosts': 0,
            'up_hosts': 0,
            'down_hosts': 0,
            'open_ports': 0,
            'services_detected': 0,
            'http_services': 0,
            'discovered_urls': 0,
            'vulnerabilities': 0,
            'wordlist_recommendations': 0,
            'duration': data.get('total_execution_time', data.get('duration', 0))
        }
        
        # Aggregate from base scan data
        if 'hosts' in data:
            hosts = data['hosts']
            summary['total_hosts'] = len(hosts)
            
            for host in hosts:
                if host.get('status') == 'up':
                    summary['up_hosts'] += 1
                else:
                    summary['down_hosts'] += 1
                
                ports = host.get('ports', [])
                summary['open_ports'] += len(ports)
                summary['services_detected'] += len([p for p in ports if p.get('service')])
        
        # Add HTTP scan data
        if 'http_scan' in data and data['http_scan']:
            http_data = data['http_scan']
            summary['http_services'] = len(http_data.get('services', []))
            summary['vulnerabilities'] += len(http_data.get('vulnerabilities', []))
        
        # Add Mini Spider data
        if 'mini_spider' in data and data['mini_spider']:
            spider_data = data['mini_spider']
            summary['discovered_urls'] = len(spider_data.get('discovered_urls', []))
        
        # Add SmartList data
        if 'smartlist' in data and data['smartlist']:
            smartlist_data = data['smartlist']
            summary['wordlist_recommendations'] = len(smartlist_data.get('wordlist_recommendations', []))
        
        return summary
    
    def _get_included_workflows(self, data: Dict[str, Any]) -> list:
        """Get list of workflows included in the data"""
        workflows = []
        
        if 'hosts' in data:
            workflows.append('nmap_02')
        if 'http_scan' in data:
            workflows.append('http_03')
        if 'mini_spider' in data:
            workflows.append('mini_spider_04')
        if 'smartlist' in data:
            workflows.append('smartlist_05')
            
        return workflows
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility, preserving dots for IPs"""
        import re
        # Replace only truly invalid filesystem characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        return sanitized[:50]  # Limit length
    
    def _generate_simple_master_report(self, data: Dict[str, Any], output_path: Path, **kwargs) -> Path:
        """Generate simple master HTML report as fallback"""
        target = kwargs.get('target', data.get('target', 'unknown'))
        summary = self._build_comprehensive_summary(data)
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>IPCrawler Master Report - {target}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #ecf0f1; padding: 15px; border-radius: 5px; text-align: center; }}
        .summary-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .summary-label {{ color: #7f8c8d; font-size: 0.9em; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #bdc3c7; padding: 10px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        .status-up {{ color: #27ae60; font-weight: bold; }}
        .status-down {{ color: #e74c3c; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>IPCrawler Security Assessment</h1>
        <h2>Target: {target}</h2>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Executive Summary</h2>
        <div class="summary">
            <div class="summary-card">
                <div class="summary-value">{summary['total_hosts']}</div>
                <div class="summary-label">Total Hosts</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{summary['up_hosts']}</div>
                <div class="summary-label">Hosts Up</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{summary['open_ports']}</div>
                <div class="summary-label">Open Ports</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{summary['http_services']}</div>
                <div class="summary-label">HTTP Services</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{summary['discovered_urls']}</div>
                <div class="summary-label">URLs Found</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{summary['wordlist_recommendations']}</div>
                <div class="summary-label">Wordlist Recommendations</div>
            </div>
        </div>
"""

        # Add hosts section
        if 'hosts' in data and data['hosts']:
            html_content += """
        <h2>Discovered Hosts</h2>
        <table>
            <tr><th>Host</th><th>Status</th><th>Hostname</th><th>Open Ports</th></tr>
"""
            for host in data['hosts']:
                host_ip = host.get('address', 'Unknown')
                hostname = host.get('hostname', '')
                status = host.get('status', 'unknown')
                status_class = 'status-up' if status == 'up' else 'status-down'
                port_count = len(host.get('ports', []))
                
                html_content += f"""
            <tr>
                <td>{host_ip}</td>
                <td class="{status_class}">{status.upper()}</td>
                <td>{hostname}</td>
                <td>{port_count}</td>
            </tr>
"""
            html_content += "</table>"

        html_content += """
    </div>
</body>
</html>
"""
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            console.success(f"Generated simple master HTML report: {output_path}", internal=True)
            return output_path
        except Exception as e:
            console.error(f"Failed to generate simple master report: {e}", internal=True)
            raise


class MasterTextReporter(BaseReporter):
    """Generates comprehensive master TXT report combining all workflows"""
    
    def __init__(self, output_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize master text reporter
        
        Args:
            output_dir: Directory to save master report
            theme: Theme to use for formatting
        """
        super().__init__(output_dir)
        self.theme = theme
        self.template_engine = get_template_engine(theme)
        console.debug(f"Master text reporter initialized with theme '{theme}'")
    
    def get_format(self) -> str:
        """Get the report format name"""
        return 'master_txt'
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate comprehensive master TXT report
        
        Args:
            data: Combined scan data from all workflows
            **kwargs: Additional options (target, timestamp)
            
        Returns:
            Path to generated master TXT report
        """
        self.ensure_output_dir()
        
        # Prepare comprehensive context
        context = self._prepare_master_context(data, **kwargs)
        
        # Generate filename
        target = kwargs.get('target', data.get('target', 'unknown'))
        filename = f"master_report_{self._sanitize_filename(target)}.txt"
        output_path = self.output_dir / filename
        
        try:
            # Render comprehensive template
            txt_content = self.template_engine.render_template(
                'workflows/comprehensive_report.txt.j2', 
                context
            )
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(txt_content)
            
            console.success(f"Generated master TXT report: {output_path}", internal=True)
            return output_path
            
        except Exception as e:
            console.error(f"Failed to generate master TXT report: {e}", internal=True)
            # Fallback to simple master report
            return self._generate_simple_master_txt_report(data, output_path, **kwargs)
    
    def _prepare_master_context(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare comprehensive context for master report"""
        target = kwargs.get('target', data.get('target', 'Unknown'))
        
        # Base context
        context = {
            'data': data,
            'target': target,
            'title': f'IPCrawler Security Assessment - {target}',
            'workflow': 'comprehensive',
            'generated': datetime.now(),
        }
        
        # Aggregate summary from all workflows
        context['summary'] = self._build_comprehensive_summary(data)
        
        # Extract and organize workflow data with enhanced processing
        context['hosts'] = self._process_hosts_data(data.get('hosts', []))
        context['http_scan'] = self._process_http_scan_data(data.get('http_scan', {}))
        context['mini_spider'] = self._process_mini_spider_data(data.get('mini_spider', {}))
        context['smartlist'] = self._process_smartlist_data(data.get('smartlist', {}))
        
        # Add metadata
        context['metadata'] = {
            'generator': 'IPCrawler',
            'version': '2.0',
            'template': 'comprehensive_report.txt.j2',
            'timestamp': datetime.now(),
            'target': target,
            'workflows_included': self._get_included_workflows(data)
        }
        
        # Add theme info for template
        context['theme'] = {
            'name': self.theme
        }
        
        return context
    
    def _process_hosts_data(self, hosts: list) -> list:
        """Process and enhance host data for comprehensive reporting"""
        processed_hosts = []
        
        for host in hosts:
            processed_host = host.copy()
            
            # Normalize host data structure
            if 'address' in host:
                processed_host['ip'] = host['address']
            elif 'ip' not in processed_host and 'host' in host:
                processed_host['ip'] = host['host']
            
            # Categorize ports for better display
            if 'ports' in host:
                ports = host['ports']
                processed_host['open_ports'] = [p for p in ports if p.get('state') == 'open']
                processed_host['closed_ports'] = [p for p in ports if p.get('state') == 'closed']
                processed_host['filtered_ports'] = [p for p in ports if p.get('state') == 'filtered']
                
                # Create service summary text
                services = {}
                for port in processed_host['open_ports']:
                    service = port.get('service', 'unknown')
                    if service not in services:
                        services[service] = []
                    services[service].append(str(port.get('port', 'N/A')))
                
                service_lines = []
                for service, ports_list in services.items():
                    service_lines.append(f"{service}: {', '.join(ports_list)}")
                processed_host['service_summary_text'] = '; '.join(service_lines)
            
            processed_hosts.append(processed_host)
        
        return processed_hosts
    
    def _process_http_scan_data(self, http_scan: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance HTTP scan data for comprehensive reporting"""
        if not http_scan:
            return {}
        
        processed = http_scan.copy()
        
        # Create vulnerability summary by severity
        if 'vulnerabilities' in http_scan:
            vuln_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
            
            for vuln in http_scan['vulnerabilities']:
                severity = vuln.get('severity', 'info').lower()
                if severity in vuln_counts:
                    vuln_counts[severity] += 1
            
            processed['vulnerability_summary'] = vuln_counts
            processed['total_vulnerabilities'] = sum(vuln_counts.values())
        
        # Process services for better text display
        if 'services' in http_scan:
            for service in processed['services']:
                # Create technology summary
                if 'technologies' in service and service['technologies']:
                    if isinstance(service['technologies'], list):
                        service['tech_list'] = ', '.join(service['technologies'])
                    else:
                        service['tech_list'] = str(service['technologies'])
                else:
                    service['tech_list'] = 'None detected'
        
        return processed
    
    def _process_mini_spider_data(self, mini_spider: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance Mini Spider data for comprehensive reporting"""
        if not mini_spider:
            return {}
        
        processed = mini_spider.copy()
        
        # Calculate URL statistics
        if 'categorized_results' in mini_spider:
            category_stats = {}
            total_urls = 0
            
            for category, urls in mini_spider['categorized_results'].items():
                category_name = category if isinstance(category, str) else str(category)
                url_count = len(urls) if isinstance(urls, list) else 0
                category_stats[category_name] = url_count
                total_urls += url_count
            
            processed['category_stats'] = category_stats
            processed['total_discovered_urls'] = total_urls
        
        # Process findings by type if available
        if 'findings_by_type' not in processed and 'discovered_urls' in mini_spider:
            # Create basic categorized results from discovered URLs
            processed['total_discovered_urls'] = len(mini_spider['discovered_urls'])
        
        return processed
    
    def _process_smartlist_data(self, smartlist: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance SmartList data for comprehensive reporting"""
        if not smartlist:
            return {}
        
        processed = smartlist.copy()
        
        # Add recommendation statistics
        if 'wordlist_recommendations' in smartlist:
            total_wordlists = 0
            confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
            ports_with_recommendations = set()
            
            for service_rec in smartlist['wordlist_recommendations']:
                # Extract port from service identifier
                service_id = service_rec.get('service', '')
                if ':' in service_id:
                    port = service_id.split(':')[1]
                    ports_with_recommendations.add(port)
                
                if 'top_wordlists' in service_rec:
                    total_wordlists += len(service_rec['top_wordlists'])
                    
                    # Ensure path information is available for each wordlist
                    for wordlist in service_rec['top_wordlists']:
                        if not wordlist.get('path') and wordlist.get('wordlist'):
                            # Add fallback path information
                            wordlist_name = wordlist['wordlist']
                            # Try to infer common SecLists path structure
                            if 'admin' in wordlist_name.lower():
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                            elif 'api' in wordlist_name.lower():
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                            elif 'config' in wordlist_name.lower():
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                            elif 'backup' in wordlist_name.lower():
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                            else:
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                
                confidence = service_rec.get('confidence', 'low').lower()
                if confidence in confidence_counts:
                    confidence_counts[confidence] += 1
            
            processed['stats'] = {
                'total_wordlists': total_wordlists,
                'confidence_counts': confidence_counts,
                'services_analyzed': len(smartlist['wordlist_recommendations']),
                'ports_analyzed': len(ports_with_recommendations),
                'port_list': sorted(list(ports_with_recommendations))
            }
        
        # Enhance summary with port-based organization hints
        if 'summary' in processed and processed['stats']:
            port_count = processed['stats']['ports_analyzed']
            if port_count > 1:
                processed['summary']['organization_note'] = f"Recommendations organized by {port_count} different ports/services"
        
        return processed
    
    def _build_comprehensive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive summary from all workflow data"""
        summary = {
            'total_hosts': 0,
            'up_hosts': 0,
            'down_hosts': 0,
            'total_ports': 0,
            'open_ports': 0,
            'services_detected': 0,
            'http_services': 0,
            'discovered_urls': 0,
            'vulnerabilities': 0,
            'wordlist_recommendations': 0,
            'duration': data.get('total_execution_time', data.get('duration', 0))
        }
        
        # Aggregate from base scan data
        if 'hosts' in data:
            hosts = data['hosts']
            summary['total_hosts'] = len(hosts)
            
            for host in hosts:
                if host.get('status') == 'up':
                    summary['up_hosts'] += 1
                else:
                    summary['down_hosts'] += 1
                
                ports = host.get('ports', [])
                summary['total_ports'] += len(ports)
                open_ports = [p for p in ports if p.get('state') == 'open']
                summary['open_ports'] += len(open_ports)
                summary['services_detected'] += len([p for p in open_ports if p.get('service')])
        
        # Add HTTP scan data
        if 'http_scan' in data and data['http_scan']:
            http_data = data['http_scan']
            summary['http_services'] = len(http_data.get('services', []))
            summary['vulnerabilities'] += len(http_data.get('vulnerabilities', []))
        
        # Add Mini Spider data
        if 'mini_spider' in data and data['mini_spider']:
            spider_data = data['mini_spider']
            summary['discovered_urls'] = len(spider_data.get('discovered_urls', []))
        
        # Add SmartList data
        if 'smartlist' in data and data['smartlist']:
            smartlist_data = data['smartlist']
            summary['wordlist_recommendations'] = len(smartlist_data.get('wordlist_recommendations', []))
        
        return summary
    
    def _get_included_workflows(self, data: Dict[str, Any]) -> list:
        """Get list of workflows included in the data"""
        workflows = []
        
        if 'hosts' in data and data['hosts']:
            workflows.extend(['nmap_fast_01', 'nmap_02'])
        if 'http_scan' in data and data['http_scan']:
            workflows.append('http_03')
        if 'mini_spider' in data and data['mini_spider']:
            workflows.append('mini_spider_04')
        if 'smartlist' in data and data['smartlist']:
            workflows.append('smartlist_05')
            
        return workflows
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility, preserving dots for IPs"""
        import re
        # Replace only truly invalid filesystem characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        return sanitized[:50]  # Limit length
    
    def _generate_simple_master_txt_report(self, data: Dict[str, Any], output_path: Path, **kwargs) -> Path:
        """Generate simple master TXT report as fallback"""
        target = kwargs.get('target', data.get('target', 'unknown'))
        summary = self._build_comprehensive_summary(data)
        
        txt_content = f"""{'=' * 80}
IPCRAWLER MASTER SECURITY ASSESSMENT REPORT
{'=' * 80}
Target: {target}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

EXECUTIVE SUMMARY
{'-' * 80}
Total Hosts Scanned: {summary['total_hosts']}
Hosts Responding: {summary['up_hosts']}
Hosts Down: {summary['down_hosts']}
Total Ports Checked: {summary['total_ports']}
Open Ports Found: {summary['open_ports']}
Services Detected: {summary['services_detected']}
HTTP Services: {summary['http_services']}
Discovered URLs: {summary['discovered_urls']}
Vulnerabilities: {summary['vulnerabilities']}
Wordlist Recommendations: {summary['wordlist_recommendations']}
Scan Duration: {summary['duration']:.2f} seconds

"""

        # Add hosts section
        if 'hosts' in data and data['hosts']:
            txt_content += f"""{'=' * 80}
HOST DISCOVERY RESULTS
{'=' * 80}

Discovered {len(data['hosts'])} host(s) during network reconnaissance:

"""
            for host in data['hosts']:
                host_ip = host.get('address', host.get('ip', 'Unknown'))
                hostname = host.get('hostname', '')
                status = host.get('status', 'unknown')
                
                txt_content += f"{'-' * 80}\n"
                txt_content += f"Host: {host_ip}\n"
                if hostname:
                    txt_content += f"Hostname: {hostname}\n"
                txt_content += f"Status: {status.upper()}\n"
                
                # Add ports
                ports = host.get('ports', [])
                open_ports = [p for p in ports if p.get('state') == 'open']
                if open_ports:
                    txt_content += f"\nOpen Ports ({len(open_ports)}):\n"
                    for port in open_ports[:20]:  # Limit to first 20 ports
                        port_num = port.get('port', 'N/A')
                        service = port.get('service', 'unknown')
                        protocol = port.get('protocol', 'tcp')
                        txt_content += f"  {port_num}/{protocol} - {service}\n"
                        
                        if port.get('version'):
                            txt_content += f"    Version: {port['version']}\n"
                        if port.get('product'):
                            txt_content += f"    Product: {port['product']}\n"
                    
                    if len(open_ports) > 20:
                        txt_content += f"  ... and {len(open_ports) - 20} more ports\n"
                else:
                    txt_content += "\nNo open ports detected on this host.\n"
                
                txt_content += "\n"

        # Add HTTP scan results
        if 'http_scan' in data and data['http_scan']:
            http_data = data['http_scan']
            txt_content += f"""{'=' * 80}
HTTP/HTTPS SECURITY ASSESSMENT
{'=' * 80}

"""
            
            if 'services' in http_data and http_data['services']:
                txt_content += f"HTTP Services Analyzed: {len(http_data['services'])}\n\n"
                
                for service in http_data['services'][:10]:  # Limit to first 10 services
                    txt_content += f"{'-' * 40}\n"
                    txt_content += f"URL: {service.get('url', 'N/A')}\n"
                    txt_content += f"Status Code: {service.get('status_code', 'N/A')}\n"
                    txt_content += f"Server: {service.get('server', 'Unknown')}\n"
                    
                    # Add technologies
                    if 'technologies' in service:
                        tech_list = service['technologies'] if isinstance(service['technologies'], str) else ', '.join(service.get('technologies', []))
                        txt_content += f"Technologies: {tech_list or 'None detected'}\n"
                    
                    # Add discovered paths (limited)
                    if 'discovered_paths' in service and service['discovered_paths']:
                        paths = service['discovered_paths'][:10]
                        txt_content += f"Discovered Paths: {len(service['discovered_paths'])} found\n"
                        for path in paths:
                            txt_content += f"  • {path}\n"
                        if len(service['discovered_paths']) > 10:
                            txt_content += f"  ... and {len(service['discovered_paths']) - 10} more paths\n"
                    
                    txt_content += "\n"
            
            # Add vulnerability summary
            if 'vulnerabilities' in http_data and http_data['vulnerabilities']:
                vuln_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
                for vuln in http_data['vulnerabilities']:
                    severity = vuln.get('severity', 'info').lower()
                    if severity in vuln_counts:
                        vuln_counts[severity] += 1
                
                txt_content += f"\nSecurity Vulnerabilities Summary:\n"
                for severity, count in vuln_counts.items():
                    if count > 0:
                        txt_content += f"  {severity.upper()}: {count}\n"

        # Add Mini Spider results
        if 'mini_spider' in data and data['mini_spider']:
            spider_data = data['mini_spider']
            txt_content += f"""\n{'=' * 80}
MINI SPIDER URL DISCOVERY
{'=' * 80}

"""
            
            if 'discovered_urls' in spider_data:
                txt_content += f"Total URLs Discovered: {len(spider_data['discovered_urls'])}\n\n"
                
                # Show first 20 URLs
                for url in spider_data['discovered_urls'][:20]:
                    if isinstance(url, dict):
                        txt_content += f"  • {url.get('url', str(url))}\n"
                    else:
                        txt_content += f"  • {url}\n"
                
                if len(spider_data['discovered_urls']) > 20:
                    txt_content += f"  ... and {len(spider_data['discovered_urls']) - 20} more URLs\n"

        # Add SmartList results with enhanced port-based organization
        if 'smartlist' in data and data['smartlist']:
            smartlist_data = data['smartlist']
            txt_content += f"""\n{'=' * 80}
SMARTLIST WORDLIST RECOMMENDATIONS
{'=' * 80}

"""
            
            if 'wordlist_recommendations' in smartlist_data:
                # Group recommendations by port
                port_groups = {}
                for service_rec in smartlist_data['wordlist_recommendations']:
                    service_id = service_rec.get('service', 'unknown:unknown')
                    if ':' in service_id:
                        port = service_id.split(':')[1]
                        service_name = service_rec.get('service_name', 'unknown')
                        port_key = f"{port}/{service_name}"
                        
                        if port_key not in port_groups:
                            port_groups[port_key] = []
                        port_groups[port_key].append(service_rec)
                
                txt_content += f"Total Services Analyzed: {len(smartlist_data['wordlist_recommendations'])}\n"
                txt_content += f"Ports with Recommendations: {len(port_groups)}\n\n"
                
                # Display recommendations grouped by port
                for port_key, services in port_groups.items():
                    port_num, service_name = port_key.split('/', 1)
                    txt_content += f"{'=' * 60}\n"
                    txt_content += f"PORT {port_num}/tcp - {service_name.title()} Service\n"
                    txt_content += f"{'=' * 60}\n\n"
                    
                    for service_rec in services:
                        txt_content += f"Target: {service_rec.get('service', 'Unknown')}\n"
                        if service_rec.get('detected_technology'):
                            txt_content += f"Technology: {service_rec['detected_technology']}\n"
                        txt_content += f"Overall Confidence: {service_rec.get('confidence', 'Unknown').upper()}\n\n"
                        
                        if 'top_wordlists' in service_rec and service_rec['top_wordlists']:
                            txt_content += f"PRIORITY WORDLIST RECOMMENDATIONS:\n"
                            txt_content += f"{'-' * 50}\n\n"
                            
                            # Sort wordlists by score (highest first)
                            wordlists = sorted(service_rec['top_wordlists'], 
                                             key=lambda x: x.get('score', 0), reverse=True)
                            
                            for wl in wordlists[:8]:  # Top 8 wordlists
                                score = wl.get('score', 0)
                                confidence = wl.get('confidence', 'low')
                                
                                # Determine priority level
                                if score >= 80 or confidence == 'high':
                                    priority = "CRITICAL"
                                elif score >= 60:
                                    priority = "HIGH"
                                elif score >= 40:
                                    priority = "MEDIUM"
                                else:
                                    priority = "LOW"
                                
                                txt_content += f"{priority}: {wl.get('wordlist', 'N/A')} (Score: {score})\n"
                                
                                # Add path information
                                if wl.get('path'):
                                    txt_content += f"  📁 Path: {wl['path']}\n"
                                else:
                                    txt_content += f"  📁 Path: [Check /usr/share/seclists/ for {wl.get('wordlist', 'file')}]\n"
                                
                                if wl.get('reason'):
                                    txt_content += f"  🎯 Reason: {wl['reason']}\n"
                                
                                if wl.get('category') and wl['category'] != 'none':
                                    txt_content += f"  📂 Category: {wl['category']}\n"
                                
                                txt_content += "\n"
                            
                            # Add usage notes for this service
                            if service_rec.get('context', {}).get('fallback_used'):
                                txt_content += "⚠️  WARNING: Generic fallback was used - consider manual verification\n\n"
                        else:
                            txt_content += "No specific wordlist recommendations available for this service.\n\n"
                    
                    txt_content += "\n"
                
                # Add overall usage notes
                txt_content += f"{'-' * 80}\n"
                txt_content += "💡 USAGE NOTES:\n"
                txt_content += "• Use CRITICAL and HIGH priority wordlists first for maximum efficiency\n"
                txt_content += "• Paths shown are for SecLists installation - adjust for your environment\n"
                txt_content += "• Combine multiple wordlists for comprehensive coverage\n"
                txt_content += "• Consider service-specific context when selecting wordlists\n\n"

        txt_content += f"""\n{'=' * 80}
SCAN METADATA
{'=' * 80}

Target: {target}
Workflow: Comprehensive Security Assessment
Generator: IPCrawler v2.0
Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Duration: {summary['duration']:.2f} seconds

{'=' * 80}
"""
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(txt_content)
            console.success(f"Generated simple master TXT report: {output_path}", internal=True)
            return output_path
        except Exception as e:
            console.error(f"Failed to generate simple master TXT report: {e}", internal=True)
            raise