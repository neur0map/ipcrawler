"""HTML format reporter for IPCrawler

Provides HTML output formatting using Jinja2 templates with professional styling.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..base.reporter import BaseReporter
from ..templates.engine import get_template_engine
from src.core.ui.console.base import console


class HTMLReporter(BaseReporter):
    """HTML format reporter with Jinja2 template system"""
    
    def __init__(self, output_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize HTML reporter
        
        Args:
            output_dir: Directory to save reports  
            theme: Theme to use for styling
        """
        super().__init__(output_dir)
        self.theme = theme
        self.template_engine = get_template_engine(theme)
        console.debug(f"HTML reporter initialized with theme '{theme}'")
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate HTML report from data
        
        Args:
            data: Data to generate report from
            **kwargs: Additional options (filename, target, title, template)
            
        Returns:
            Path to generated HTML file
        """
        self.ensure_output_dir()
        
        # Prepare context
        context = self._prepare_context(data, **kwargs)
        
        # Determine template to use
        template_name = kwargs.get('template', 'base/layout.html.j2')
        
        # Generate filename
        filename = self._generate_filename(data, **kwargs)
        output_path = self.output_dir / filename
        
        try:
            # Render template
            html_content = self.template_engine.render_template(template_name, context)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            console.success(f"Generated HTML report: {output_path}", internal=True)
            return output_path
            
        except Exception as e:
            console.error(f"Failed to generate HTML report: {e}", internal=True)
            raise
    
    def _format_html_content(self, target: str, data: Dict[str, Any]) -> str:
        """Format HTML report content for legacy compatibility
        
        Args:
            target: Target identifier
            data: Scan data to format
            
        Returns:
            Formatted HTML content as string
        """
        # Prepare context for rendering
        context = self._prepare_context(data, target=target, title=f"Scan Report - {target}")
        
        # Use base template for legacy formatting
        try:
            return self.template_engine.render_template('base/layout.html.j2', context)
        except Exception as e:
            console.error(f"Failed to format HTML report: {e}", internal=True)
            # Fallback to simple HTML format
            return self._generate_simple_html_report(target, data)
    
    def _generate_simple_html_report(self, target: str, data: Dict[str, Any]) -> str:
        """Generate simple HTML report as fallback"""
        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            f'<title>Scan Report - {target}</title>',
            '<style>',
            'body { font-family: Arial, sans-serif; margin: 20px; }',
            'h1, h2 { color: #333; }',
            'table { border-collapse: collapse; width: 100%; margin: 10px 0; }',
            'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }',
            'th { background-color: #f2f2f2; }',
            '.summary { background-color: #f9f9f9; padding: 15px; margin: 10px 0; }',
            '</style>',
            '</head>',
            '<body>',
            f'<h1>Scan Report for {target}</h1>',
            f'<p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
        ]
        
        # Add summary section
        if 'summary' in data:
            summary = data['summary']
            html_parts.extend([
                '<div class="summary">',
                '<h2>Summary</h2>',
                f'<p><strong>Total Hosts:</strong> {summary.get("total_hosts", 0)}</p>',
                f'<p><strong>Up Hosts:</strong> {summary.get("up_hosts", 0)}</p>',
                f'<p><strong>Down Hosts:</strong> {summary.get("down_hosts", 0)}</p>',
                '</div>'
            ])
        
        # Add hosts section
        if 'hosts' in data and data['hosts']:
            html_parts.extend([
                '<h2>Discovered Hosts</h2>'
            ])
            
            for host in data['hosts']:
                host_ip = host.get('address', 'Unknown')
                hostname = host.get('hostname', '')
                status = host.get('status', 'unknown')
                
                html_parts.extend([
                    f'<h3>Host: {host_ip}</h3>',
                    f'<p><strong>Status:</strong> {status}</p>'
                ])
                
                if hostname:
                    html_parts.append(f'<p><strong>Hostname:</strong> {hostname}</p>')
                
                # Add ports table
                ports = host.get('ports', [])
                if ports:
                    html_parts.extend([
                        f'<h4>Open Ports ({len(ports)})</h4>',
                        '<table>',
                        '<tr><th>Port</th><th>Protocol</th><th>Service</th><th>State</th></tr>'
                    ])
                    
                    for port in ports[:20]:  # Limit to first 20 ports
                        port_num = port.get('port', 'N/A')
                        protocol = port.get('protocol', 'tcp')
                        service = port.get('service', 'unknown')
                        state = port.get('state', 'unknown')
                        html_parts.append(f'<tr><td>{port_num}</td><td>{protocol}</td><td>{service}</td><td>{state}</td></tr>')
                    
                    html_parts.append('</table>')
                    
                    if len(ports) > 20:
                        html_parts.append(f'<p><em>... and {len(ports) - 20} more ports</em></p>')
        
        html_parts.extend([
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def get_format(self) -> str:
        """Get the report format name"""
        return "html"
    
    def _prepare_context(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare comprehensive context for template rendering"""
        # Base context
        context = {
            'data': data,
            'target': kwargs.get('target', data.get('target', 'Unknown')),
            'title': kwargs.get('title', 'IPCrawler Security Report'),
            'workflow': kwargs.get('workflow', 'scan'),
        }
        
        # Add summary statistics
        context['summary'] = self._generate_summary(data)
        
        # Add processed data sections
        if 'hosts' in data:
            context['hosts'] = self._process_hosts(data['hosts'])
        
        if 'http_scan' in data:
            context['http_scan'] = self._process_http_scan(data['http_scan'])
        
        if 'smartlist' in data:
            context['smartlist'] = self._process_smartlist(data['smartlist'])
        
        if 'mini_spider' in data:
            context['mini_spider'] = self._process_mini_spider(data['mini_spider'])
        
        return context
    
    def _generate_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for the report"""
        summary = {
            'total_hosts': data.get('total_hosts', 0),
            'up_hosts': data.get('up_hosts', 0),
            'down_hosts': data.get('down_hosts', 0),
            'total_ports': 0,
            'open_ports': 0,
            'services_detected': 0,
            'vulnerabilities': 0,
            'duration': data.get('duration', 0)
        }
        
        # Count ports and services
        if 'hosts' in data:
            for host in data['hosts']:
                if 'ports' in host:
                    summary['total_ports'] += len(host['ports'])
                    open_ports = [p for p in host['ports'] if p.get('state') == 'open']
                    summary['open_ports'] += len(open_ports)
                    
                    # Count unique services
                    services = {p.get('service', 'unknown') for p in open_ports if p.get('service')}
                    summary['services_detected'] += len(services)
        
        # Count vulnerabilities
        if 'http_scan' in data and 'vulnerabilities' in data['http_scan']:
            summary['vulnerabilities'] = len(data['http_scan']['vulnerabilities'])
        
        return summary
    
    def _process_hosts(self, hosts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process host data for template rendering"""
        processed_hosts = []
        
        for host in hosts:
            processed_host = host.copy()
            
            # Categorize ports
            if 'ports' in host:
                ports = host['ports']
                processed_host['open_ports'] = [p for p in ports if p.get('state') == 'open']
                processed_host['closed_ports'] = [p for p in ports if p.get('state') == 'closed']
                processed_host['filtered_ports'] = [p for p in ports if p.get('state') == 'filtered']
                
                # Add service summary
                services = {}
                for port in processed_host['open_ports']:
                    service = port.get('service', 'unknown')
                    if service not in services:
                        services[service] = []
                    services[service].append(port['port'])
                
                processed_host['service_summary'] = services
            
            processed_hosts.append(processed_host)
        
        return processed_hosts
    
    def _process_http_scan(self, http_scan: Dict[str, Any]) -> Dict[str, Any]:
        """Process HTTP scan data for template rendering"""
        processed = http_scan.copy()
        
        # Categorize vulnerabilities by severity
        if 'vulnerabilities' in http_scan:
            vulns_by_severity = {
                'critical': [],
                'high': [],
                'medium': [],
                'low': [],
                'info': []
            }
            
            for vuln in http_scan['vulnerabilities']:
                severity = vuln.get('severity', 'info').lower()
                if severity in vulns_by_severity:
                    vulns_by_severity[severity].append(vuln)
            
            processed['vulnerabilities_by_severity'] = vulns_by_severity
            processed['vulnerability_counts'] = {
                k: len(v) for k, v in vulns_by_severity.items()
            }
        
        # Process services for better display
        if 'services' in http_scan:
            for service in processed['services']:
                # Add technology summary
                if 'technologies' in service and service['technologies']:
                    service['tech_summary'] = ', '.join(service['technologies'][:5])
                    if len(service['technologies']) > 5:
                        service['tech_summary'] += f" (+{len(service['technologies']) - 5} more)"
        
        return processed
    
    def _process_smartlist(self, smartlist: Dict[str, Any]) -> Dict[str, Any]:
        """Process SmartList data for template rendering"""
        processed = smartlist.copy()
        
        # Add recommendation summary
        if 'wordlist_recommendations' in smartlist:
            total_wordlists = 0
            confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
            
            for service_rec in smartlist['wordlist_recommendations']:
                if 'top_wordlists' in service_rec:
                    total_wordlists += len(service_rec['top_wordlists'])
                
                confidence = service_rec.get('confidence', 'low').lower()
                if confidence in confidence_counts:
                    confidence_counts[confidence] += 1
            
            processed['recommendation_summary'] = {
                'total_wordlists': total_wordlists,
                'confidence_counts': confidence_counts,
                'services_analyzed': len(smartlist['wordlist_recommendations'])
            }
        
        return processed
    
    def _process_mini_spider(self, mini_spider: Dict[str, Any]) -> Dict[str, Any]:
        """Process Mini Spider data for template rendering"""
        processed = mini_spider.copy()
        
        # Categorize URLs
        if 'categorized_results' in mini_spider:
            category_stats = {}
            total_urls = 0
            
            for category, urls in mini_spider['categorized_results'].items():
                category_name = category if isinstance(category, str) else str(category)
                url_count = len(urls)
                category_stats[category_name] = {
                    'count': url_count,
                    'urls': urls[:10]  # Limit for display
                }
                total_urls += url_count
            
            processed['category_stats'] = category_stats
            processed['total_discovered_urls'] = total_urls
        
        # Process interesting findings
        if 'interesting_findings' in mini_spider:
            findings_by_type = {}
            for finding in mini_spider['interesting_findings']:
                finding_type = finding.get('type', 'general')
                if finding_type not in findings_by_type:
                    findings_by_type[finding_type] = []
                findings_by_type[finding_type].append(finding)
            
            processed['findings_by_type'] = findings_by_type
        
        return processed
    
    def _generate_filename(self, data: Dict[str, Any], **kwargs) -> str:
        """Generate appropriate filename for the report"""
        filename = kwargs.get('filename')
        if filename:
            if not filename.endswith('.html'):
                filename += '.html'
            return filename
        
        # Generate filename from context
        target = kwargs.get('target', data.get('target', 'unknown'))
        workflow = kwargs.get('workflow', 'scan')
        
        # Sanitize target for filename
        import re
        safe_target = re.sub(r'[<>:"/\\|?*]', '_', target)
        safe_target = re.sub(r'_+', '_', safe_target).strip('_')
        
        return f"{workflow}_report_{safe_target}.html"
    
    def set_theme(self, theme: str):
        """Change the theme for the reporter
        
        Args:
            theme: New theme name
        """
        self.theme = theme
        self.template_engine.set_theme(theme)
        console.debug(f"HTML reporter theme changed to '{theme}'")
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate that data is suitable for HTML reporting
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        if not isinstance(data, dict):
            console.error("Report data must be a dictionary")
            return False
        
        # Check for minimum required data
        if not data:
            console.warning("Report data is empty")
            return True  # Allow empty reports
        
        return True