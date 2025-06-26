"""
Jinja2-based HTML Report Generator for ipcrawler

This module provides a template-based approach to generating HTML reports
using Jinja2 templates instead of hardcoded HTML strings.
"""

import os
from datetime import datetime
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path


class Jinja2HTMLReporter:
    """Jinja2-based HTML report generator"""
    
    def __init__(self, template_dir: str = None):
        """Initialize the Jinja2 HTML reporter
        
        Args:
            template_dir: Path to templates directory. If None, uses default location.
        """
        # Determine template directory
        if template_dir is None:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent.parent
            template_dir = script_dir / "templates"
        
        self.template_dir = Path(template_dir)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self._add_custom_filters()
    
    def _add_custom_filters(self):
        """Add custom Jinja2 filters"""
        
        def truncate_version(version: str, max_length: int = 50) -> str:
            """Truncate version string if too long"""
            if len(version) <= max_length:
                return version
            return version[:max_length] + "..."
        
        def format_port_state(state: str) -> str:
            """Format port state with appropriate styling"""
            return state.lower()
        
        self.jinja_env.filters['truncate_version'] = truncate_version
        self.jinja_env.filters['format_port_state'] = format_port_state
    
    def generate_report(self, targets: Dict[str, Any], partial: bool = False, 
                       static_mode: bool = False, daemon_mode: bool = False,
                       watch_mode: bool = False, update_interval: int = 600) -> str:
        """Generate HTML report using Jinja2 templates
        
        Args:
            targets: Dictionary of target results
            partial: Whether this is a partial report
            static_mode: Whether to generate static report (no auto-refresh)
            daemon_mode: Whether running in daemon mode
            watch_mode: Whether running in watch mode
            update_interval: Auto-refresh interval in seconds
            
        Returns:
            Generated HTML report as string
        """
        
        # Prepare template context
        context = self._prepare_template_context(
            targets, partial, static_mode, daemon_mode, watch_mode, update_interval
        )
        
        # Load and render the base template
        template = self.jinja_env.get_template('base.html.j2')
        return template.render(context)
    
    def _prepare_template_context(self, targets: Dict[str, Any], partial: bool,
                                 static_mode: bool, daemon_mode: bool, 
                                 watch_mode: bool, update_interval: int) -> Dict[str, Any]:
        """Prepare context data for Jinja2 templates"""
        
        # Calculate summary statistics
        total_targets = len(targets)
        total_open_ports = sum(len(target.open_ports) for target in targets.values())
        total_services = total_open_ports  # Each open port is a service
        total_web_services = sum(len(target.web_services) for target in targets.values())
        total_vulnerabilities = sum(len(target.vulnerabilities) for target in targets.values())
        total_manual_commands = sum(len(target.manual_commands) for target in targets.values())
        
        # Count critical findings (pattern matches with vulnerability indicators)
        critical_findings = 0
        for target in targets.values():
            critical_findings += len([p for p in target.patterns if any(
                keyword in p.lower() for keyword in ['vuln', 'exploit', 'cve', 'critical', 'high']
            )])
        
        # Generate timestamps
        generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_year = datetime.now().year
        
        # Determine auto-refresh settings
        auto_refresh = False
        if not static_mode:
            if daemon_mode or watch_mode:
                auto_refresh = True
        
        # Determine live status
        is_live = daemon_mode and not static_mode
        
        # Prepare quick access data
        quick_access = self._prepare_quick_access_data(targets)
        
        # Prepare pattern matches for each target
        for target_name, target_data in targets.items():
            if hasattr(target_data, 'patterns') and target_data.patterns:
                # Convert patterns to structured format if needed
                pattern_matches = []
                for i, pattern in enumerate(target_data.patterns):
                    pattern_matches.append({
                        'plugin_name': f'Pattern Match {i+1}',
                        'target': target_name,
                        'port': 'N/A',
                        'match_text': pattern
                    })
                target_data.pattern_matches = pattern_matches
            else:
                target_data.pattern_matches = []
        
        return {
            'targets': targets,
            'is_partial': partial,
            'auto_refresh': auto_refresh,
            'is_live': is_live,
            'metadata': {
                'generated_time': generated_time,
                'target_count': total_targets,
                'total_open_ports': total_open_ports,
                'total_services': total_services,
                'year': current_year,
                'scan_duration': None  # Could be calculated if needed
            },
            'summary': {
                'total_targets': total_targets,
                'total_open_ports': total_open_ports,
                'total_services': total_services,
                'total_web_services': total_web_services,
                'critical_findings': critical_findings,
                'total_manual_commands': total_manual_commands
            },
            'quick_access': quick_access
        }
    
    def _prepare_quick_access_data(self, targets: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        """Prepare quick access data for templates"""
        
        web_services = []
        common_services = []
        vulnerabilities = []
        credentials = []
        
        for target_name, target_data in targets.items():
            # Collect web services
            for web_service in target_data.web_services:
                web_services.append({
                    'url': web_service.url,
                    'title': web_service.title,
                    'status_code': web_service.status_code
                })
            
            # Collect common services
            for service in target_data.open_ports:
                if service.service in ['ssh', 'ftp', 'smtp', 'dns', 'mysql', 'postgres', 'redis']:
                    common_services.append({
                        'target': target_name,
                        'port': service.port,
                        'service': service.service,
                        'version': service.version
                    })
            
            # Collect vulnerabilities
            for vuln in target_data.vulnerabilities:
                vulnerabilities.append({
                    'target': target_name,
                    'description': vuln
                })
            
            # Look for credentials in access_info
            for service in target_data.open_ports:
                if service.access_info:
                    for key, value in service.access_info.items():
                        if 'username' in key.lower() or 'password' in key.lower() or 'credential' in key.lower():
                            credentials.append({
                                'service': f"{target_name}:{service.port}",
                                'username': key,
                                'password': str(value)
                            })
        
        return {
            'web_services': web_services[:10],  # Limit to top 10
            'common_services': common_services[:10],
            'vulnerabilities': vulnerabilities[:10],
            'credentials': credentials[:10]
        }
    
    def get_template_path(self, template_name: str) -> str:
        """Get full path to a template file"""
        return str(self.template_dir / template_name)
    
    def template_exists(self, template_name: str) -> bool:
        """Check if a template file exists"""
        return (self.template_dir / template_name).exists()