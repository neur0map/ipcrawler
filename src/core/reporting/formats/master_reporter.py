"""Master report generator for IPCrawler

Generates a single comprehensive HTML report combining all workflow results.
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
        """Sanitize filename for filesystem compatibility"""
        import re
        # Replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        sanitized = sanitized.replace('.', '_').replace(':', '_')
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