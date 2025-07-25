"""Text format reporter for IPCrawler

Generates human-readable text reports using Jinja2 templates.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from ..base.reporter import BaseReporter
from ..templates.engine import get_template_engine
from src.core.ui.console.base import console


class TextReporter(BaseReporter):
    """Generates detailed text reports using Jinja2 templates"""
    
    def __init__(self, output_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize text reporter
        
        Args:
            output_dir: Directory to save reports
            theme: Theme to use (affects formatting preferences)
        """
        super().__init__(output_dir)
        self.theme = theme
        self.template_engine = get_template_engine(theme)
        console.debug(f"Text reporter initialized with theme '{theme}'")
    
    def get_format(self) -> str:
        """Get the report format name"""
        return 'txt'
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate text report
        
        Args:
            data: Scan data to format
            **kwargs: Additional options (target, workflow, timestamp, template)
            
        Returns:
            Path to generated text file
        """
        self.ensure_output_dir()
        
        # Prepare context
        context = self._prepare_context(data, **kwargs)
        
        # Determine template to use
        template_name = kwargs.get('template', 'base/layout.txt.j2')
        
        # Generate filename
        filename = self._generate_filename(data, **kwargs)
        output_path = self.output_dir / filename
        
        try:
            # Render template
            text_content = self.template_engine.render_template(template_name, context)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            console.success(f"Generated text report: {output_path}", internal=True)
            return output_path
            
        except Exception as e:
            console.error(f"Failed to generate text report: {e}", internal=True)
            raise
    
    def _format_text_report(self, target: str, data: Dict[str, Any]) -> str:
        """Format text report content for legacy compatibility
        
        Args:
            target: Target identifier
            data: Scan data to format
            
        Returns:
            Formatted text content as string
        """
        # Prepare context for rendering
        context = self._prepare_context(data, target=target)
        
        # Use base template for legacy formatting
        try:
            return self.template_engine.render_template('base/layout.txt.j2', context)
        except Exception as e:
            console.error(f"Failed to format text report: {e}", internal=True)
            # Fallback to simple text format
            return self._generate_simple_text_report(target, data)
    
    def _generate_simple_text_report(self, target: str, data: Dict[str, Any]) -> str:
        """Generate simple text report as fallback"""
        lines = [
            "=" * 80,
            f"SCAN REPORT FOR {target.upper()}",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Add hosts summary
        if 'hosts' in data and data['hosts']:
            lines.extend([
                "DISCOVERED HOSTS:",
                "-" * 80
            ])
            for host in data['hosts']:
                host_ip = host.get('address', 'Unknown')
                hostname = host.get('hostname', '')
                status = host.get('status', 'unknown')
                
                lines.append(f"Host: {host_ip}")
                if hostname:
                    lines.append(f"  Hostname: {hostname}")
                lines.append(f"  Status: {status}")
                
                # Add ports
                ports = host.get('ports', [])
                if ports:
                    lines.append(f"  Open Ports ({len(ports)}):")
                    for port in ports[:10]:  # Limit to first 10 ports
                        port_num = port.get('port', 'N/A')
                        service = port.get('service', 'unknown')
                        state = port.get('state', 'unknown')
                        lines.append(f"    {port_num}/{port.get('protocol', 'tcp')} - {service} ({state})")
                    
                    if len(ports) > 10:
                        lines.append(f"    ... and {len(ports) - 10} more ports")
                
                lines.append("")
        
        # Add summary
        if 'summary' in data:
            summary = data['summary']
            lines.extend([
                "SUMMARY:",
                "-" * 80,
                f"Total Hosts: {summary.get('total_hosts', 0)}",
                f"Up Hosts: {summary.get('up_hosts', 0)}",
                f"Down Hosts: {summary.get('down_hosts', 0)}",
                ""
            ])
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def _prepare_context(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare context for template rendering"""
        # Base context
        context = {
            'data': data,
            'target': kwargs.get('target', data.get('target', 'Unknown')),
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
    
    def _process_hosts(self, hosts: list) -> list:
        """Process host data for text display"""
        processed_hosts = []
        
        for host in hosts:
            processed_host = host.copy()
            
            # Categorize ports
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
                    services[service].append(str(port['port']))
                
                service_lines = []
                for service, ports in services.items():
                    service_lines.append(f"{service}: {', '.join(ports)}")
                processed_host['service_summary_text'] = '; '.join(service_lines)
            
            processed_hosts.append(processed_host)
        
        return processed_hosts
    
    def _process_http_scan(self, http_scan: Dict[str, Any]) -> Dict[str, Any]:
        """Process HTTP scan data for text display"""
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
        
        # Process services for text display
        if 'services' in http_scan:
            for service in processed['services']:
                # Create technology summary
                if 'technologies' in service and service['technologies']:
                    service['tech_list'] = ', '.join(service['technologies'])
                else:
                    service['tech_list'] = 'None detected'
        
        return processed
    
    def _process_smartlist(self, smartlist: Dict[str, Any]) -> Dict[str, Any]:
        """Process SmartList data for text display"""
        processed = smartlist.copy()
        
        # Add recommendation statistics
        if 'wordlist_recommendations' in smartlist:
            total_wordlists = 0
            confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
            
            for service_rec in smartlist['wordlist_recommendations']:
                if 'top_wordlists' in service_rec:
                    total_wordlists += len(service_rec['top_wordlists'])
                
                confidence = service_rec.get('confidence', 'low').lower()
                if confidence in confidence_counts:
                    confidence_counts[confidence] += 1
            
            processed['stats'] = {
                'total_wordlists': total_wordlists,
                'confidence_counts': confidence_counts,
                'services_analyzed': len(smartlist['wordlist_recommendations'])
            }
        
        return processed
    
    def _process_mini_spider(self, mini_spider: Dict[str, Any]) -> Dict[str, Any]:
        """Process Mini Spider data for text display"""
        processed = mini_spider.copy()
        
        # Calculate URL statistics
        if 'categorized_results' in mini_spider:
            category_stats = {}
            total_urls = 0
            
            for category, urls in mini_spider['categorized_results'].items():
                category_name = category if isinstance(category, str) else str(category)
                url_count = len(urls)
                category_stats[category_name] = url_count
                total_urls += url_count
            
            processed['category_stats'] = category_stats
            processed['total_discovered_urls'] = total_urls
        
        return processed
    
    def _generate_filename(self, data: Dict[str, Any], **kwargs) -> str:
        """Generate appropriate filename for the report"""
        filename = kwargs.get('filename')
        if filename:
            if not filename.endswith('.txt'):
                filename += '.txt'
            return filename
        
        # Generate filename from context
        target = kwargs.get('target', data.get('target', 'unknown'))
        workflow = kwargs.get('workflow', 'scan')
        
        # Sanitize target for filename
        import re
        safe_target = re.sub(r'[<>:"/\\|?*]', '_', target)
        safe_target = re.sub(r'_+', '_', safe_target).strip('_')
        
        return f"{workflow}_report_{safe_target}.txt"
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate that data is suitable for text reporting
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        if not isinstance(data, dict):
            console.error("Report data must be a dictionary")
            return False
        
        # Allow empty reports
        return True