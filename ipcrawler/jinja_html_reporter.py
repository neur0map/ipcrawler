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
        
        def format_complex_value(value) -> str:
            """Format complex data types (lists, dicts) for HTML display"""
            if isinstance(value, list):
                if not value:
                    return "<em>None</em>"
                
                # Handle lists of dictionaries (like SSH host keys)
                if all(isinstance(item, dict) for item in value):
                    formatted_items = []
                    for item in value:
                        if 'type' in item and 'fingerprint' in item:
                            # SSH host key formatting
                            key_type = item.get('type', 'unknown')
                            bits = item.get('bits', '')
                            fingerprint = item.get('fingerprint', '')[:16] + '...' if len(item.get('fingerprint', '')) > 16 else item.get('fingerprint', '')
                            formatted_items.append(f"<code>{key_type}</code> ({bits} bits) <span style='color: #888;'>{fingerprint}</span>")
                        elif 'name' in item:
                            # SMB shares, file listings, etc.
                            name = item.get('name', '')
                            if 'permissions' in item:
                                perms = item.get('permissions', '')
                                comment = item.get('comment', '')
                                formatted_items.append(f"<code>{name}</code> <span style='color: #4CAF50;'>{perms}</span> <em>{comment}</em>")
                            else:
                                formatted_items.append(f"<code>{name}</code>")
                        else:
                            # Generic dict formatting
                            formatted_items.append(" ".join([f"{k}: {v}" for k, v in item.items() if v]))
                    return "<br>".join(formatted_items)
                else:
                    # Simple list formatting
                    return ", ".join([str(item) for item in value[:10]]) + ("..." if len(value) > 10 else "")
            
            elif isinstance(value, dict):
                if not value:
                    return "<em>None</em>"
                formatted_items = []
                for k, v in value.items():
                    if isinstance(v, (list, dict)):
                        formatted_items.append(f"<strong>{k}:</strong> {format_complex_value(v)}")
                    else:
                        formatted_items.append(f"<strong>{k}:</strong> {v}")
                return "<br>".join(formatted_items)
            
            elif isinstance(value, bool):
                return "✅ Yes" if value else "❌ No"
            
            elif value is None:
                return "<em>None</em>"
            
            else:
                # Simple string/number values
                str_value = str(value)
                if len(str_value) > 100:
                    return str_value[:100] + "..."
                return str_value
        
        def format_ssh_keys(keys) -> str:
            """Format SSH host keys for display"""
            if not keys or not isinstance(keys, list):
                return "<em>No host keys found</em>"
            
            formatted_keys = []
            for key in keys:
                if isinstance(key, dict) and 'type' in key:
                    key_type = key.get('type', 'unknown')
                    bits = key.get('bits', '')
                    fingerprint = key.get('fingerprint', '')
                    # Truncate long fingerprints
                    if len(fingerprint) > 24:
                        fingerprint = fingerprint[:24] + "..."
                    formatted_keys.append(f"<div style='margin: 4px 0;'><code style='color: #4CAF50;'>{key_type}</code> <span style='color: #888;'>({bits} bits)</span><br><span style='font-family: monospace; font-size: 11px; color: #ccc;'>{fingerprint}</span></div>")
            
            return "".join(formatted_keys)
        
        def format_smb_shares(shares) -> str:
            """Format SMB shares for display"""
            if not shares or not isinstance(shares, list):
                return "<em>No shares found</em>"
            
            formatted_shares = []
            for share in shares:
                if isinstance(share, dict):
                    name = share.get('name', 'Unknown')
                    perms = share.get('permissions', '')
                    comment = share.get('comment', '')
                    formatted_shares.append(f"<div style='margin: 4px 0;'><code style='color: #4CAF50;'>{name}</code> <span style='color: #ff6b35;'>{perms}</span> <span style='color: #888; font-style: italic;'>{comment}</span></div>")
            
            return "".join(formatted_shares)
        
        def format_git_security_summary(service) -> str:
            """Format Git security summary for display"""
            if not hasattr(service, 'git_security_summary'):
                return "<em>No Git security scan performed</em>"
            
            summary = service.git_security_summary
            total_issues = summary.get('critical_issues', 0) + summary.get('warnings', 0)
            
            if total_issues == 0:
                return "<span style='color: #28a745;'>✅ No security issues found</span>"
            
            parts = []
            if summary.get('critical_issues', 0) > 0:
                parts.append(f"<span style='color: #dc3545; font-weight: bold;'>{summary['critical_issues']} Critical</span>")
            if summary.get('warnings', 0) > 0:
                parts.append(f"<span style='color: #ffc107;'>{summary['warnings']} Warnings</span>")
            if summary.get('total_repositories', 0) > 0:
                parts.append(f"<span style='color: #17a2b8;'>{summary['total_repositories']} Repos</span>")
            if summary.get('exposed_secrets', 0) > 0:
                parts.append(f"<span style='color: #e83e8c;'>{summary['exposed_secrets']} Secrets</span>")
                
            return " | ".join(parts)
        
        def format_user_list(users) -> str:
            """Format user lists for display"""
            if not users or not isinstance(users, list):
                return "<em>No users found</em>"
            
            # Limit to reasonable number for display
            display_users = users[:15]
            remaining = len(users) - len(display_users)
            
            formatted_users = []
            for user in display_users:
                formatted_users.append(f"<code style='color: #4CAF50;'>{user}</code>")
            
            result = ", ".join(formatted_users)
            if remaining > 0:
                result += f" <span style='color: #888;'>...and {remaining} more</span>"
            
            return result
        
        def format_config_dict(config) -> str:
            """Format configuration dictionaries for display"""
            if not config or not isinstance(config, dict):
                return "<em>No configuration data</em>"
            
            formatted_items = []
            for key, value in list(config.items())[:10]:  # Limit to 10 items
                # Truncate long values
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                formatted_items.append(f"<div style='margin: 2px 0;'><code style='color: #ff6b35;'>{key}:</code> <span style='color: #ccc;'>{value}</span></div>")
            
            remaining = len(config) - len(formatted_items)
            if remaining > 0:
                formatted_items.append(f"<div style='color: #888; font-style: italic; margin-top: 4px;'>...and {remaining} more items</div>")
            
            return "".join(formatted_items)
        
        def format_file_list(files) -> str:
            """Format file lists for display"""
            if not files or not isinstance(files, list):
                return "<em>No files found</em>"
            
            display_files = files[:10]  # Show first 10 files
            remaining = len(files) - len(display_files)
            
            formatted_files = []
            for file in display_files:
                # Distinguish between directories and files
                if isinstance(file, dict):
                    name = file.get('name', str(file))
                    file_type = file.get('type', '')
                    if file_type == 'directory':
                        formatted_files.append(f"<code style='color: #4CAF50;'>📁 {name}/</code>")
                    else:
                        formatted_files.append(f"<code style='color: #ccc;'>📄 {name}</code>")
                else:
                    formatted_files.append(f"<code style='color: #ccc;'>📄 {file}</code>")
            
            result = "<br>".join(formatted_files)
            if remaining > 0:
                result += f"<div style='color: #888; font-style: italic; margin-top: 4px;'>...and {remaining} more files</div>"
            
            return result
        
        self.jinja_env.filters['truncate_version'] = truncate_version
        self.jinja_env.filters['format_port_state'] = format_port_state
        self.jinja_env.filters['format_complex_value'] = format_complex_value
        self.jinja_env.filters['format_ssh_keys'] = format_ssh_keys
        self.jinja_env.filters['format_smb_shares'] = format_smb_shares
        self.jinja_env.filters['format_git_security_summary'] = format_git_security_summary
        self.jinja_env.filters['format_user_list'] = format_user_list
        self.jinja_env.filters['format_config_dict'] = format_config_dict
        self.jinja_env.filters['format_file_list'] = format_file_list
    
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
        
        # Prepare pattern matches and Git services for each target
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
            
            # Prepare Git services data for specialized reporting
            git_services = []
            if hasattr(target_data, 'open_ports'):
                for service in target_data.open_ports:
                    # Check if service has Git-related data
                    if (hasattr(service, 'git_findings') or 
                        hasattr(service, 'git_security_summary') or 
                        service.port == 9418 or 
                        'git' in str(service.service).lower()):
                        git_services.append(service)
            target_data.git_services = git_services
        
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