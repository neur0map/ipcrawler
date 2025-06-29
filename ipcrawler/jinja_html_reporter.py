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
import re


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
        
        # Load and render the security analysis template
        template = self.jinja_env.get_template('security_analysis_base.html.j2')
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
        total_manual_commands = sum(len(target.manual_commands) if hasattr(target.manual_commands, '__len__') else 0 for target in targets.values())
        
        # Calculate directories and files found
        total_directories = 0
        total_files = 0
        for target in targets.values():
            if hasattr(target, 'web_services'):
                for web_service in target.web_services:
                    if hasattr(web_service, 'directories'):
                        total_directories += len(web_service.directories)
                    if hasattr(web_service, 'files'):
                        total_files += len(web_service.files)
        
        # Count critical findings (pattern matches with vulnerability indicators)
        critical_findings = 0
        for target in targets.values():
            if hasattr(target, 'patterns'):
                for p in target.patterns:
                    pattern_text = str(p).lower() if hasattr(p, 'lower') else str(p).lower()
                    if any(keyword in pattern_text for keyword in ['vuln', 'exploit', 'cve', 'critical', 'high']):
                        critical_findings += 1
        
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
        
        # Transform target data to match template expectations
        for target_name, target_data in targets.items():
            # Transform data structure to match professional template expectations
            transformed_data = self._transform_target_data(target_name, target_data)
            targets[target_name] = transformed_data
        
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
                'total_web_services': total_web_services,
                'total_directories': total_directories,
                'total_files': total_files,
                'year': current_year,
                'scan_duration': None  # Could be calculated if needed
            },
            'summary': {
                'total_targets': total_targets,
                'total_open_ports': total_open_ports,
                'total_services': total_services,
                'total_web_services': total_web_services,
                'total_directories': total_directories,
                'total_files': total_files,
                'critical_findings': critical_findings,
                'total_manual_commands': total_manual_commands
            },
            'quick_access': quick_access
        }
    
    def _transform_target_data(self, target_name: str, target_data: Any) -> Any:
        """Transform TargetResults object to match security analysis template structure"""
        # Create a new object with template-compatible structure
        class TransformedTarget:
            def __init__(self):
                pass

        transformed = TransformedTarget()

        # Copy basic attributes
        if hasattr(target_data, 'hostname'):
            transformed.hostname = target_data.hostname
        if hasattr(target_data, 'status'):
            transformed.status = target_data.status
        else:
            transformed.status = 'complete'

        # Add ip_address attribute (required by consolidator)
        if hasattr(target_data, 'ip_address') and target_data.ip_address:
            transformed.ip_address = target_data.ip_address
        elif hasattr(target_data, 'ip') and target_data.ip:
            transformed.ip_address = target_data.ip
        else:
            transformed.ip_address = target_name  # Fallback to target name

        # Transform open ports with proper structure expected by security template
        transformed.open_ports = self._transform_open_ports(target_data)
        
        # Transform services with proper structure
        transformed.services = self._transform_services(target_data)
        
        # Transform patterns with security-focused structure
        transformed.patterns = self._transform_security_patterns(target_data)
        
        # Transform web services with enhanced security data
        transformed.web_services = self._transform_web_services_security(target_data)
        
        # Transform manual commands with proper grouping
        transformed.manual_commands = self._transform_manual_commands_security(target_data)
        
        # Transform output files for security analysis
        transformed.output_files = self._transform_output_files(target_name, target_data)
        
        # Extract vulnerabilities
        transformed.vulnerabilities = self._extract_vulnerabilities(target_data)
        
        # Legacy compatibility - preserve original attributes
        if hasattr(target_data, 'scans'):
            transformed.scans = target_data.scans
        else:
            transformed.scans = {}
        
        return transformed
    
    def _transform_open_ports(self, target_data: Any) -> list:
        """Transform open ports for security analysis template"""
        open_ports = []
        
        if hasattr(target_data, 'open_ports'):
            for port_info in target_data.open_ports:
                port_data = type('Port', (), {
                    'port': getattr(port_info, 'port', 0),
                    'protocol': getattr(port_info, 'protocol', 'tcp'),
                    'service_name': getattr(port_info, 'service', 'unknown'),
                    'version': getattr(port_info, 'version', ''),
                    'secure': getattr(port_info, 'secure', False),
                    'state': getattr(port_info, 'state', 'open')
                })()
                open_ports.append(port_data)
        
        return open_ports
    
    def _transform_services(self, target_data: Any) -> list:
        """Transform services for security analysis template"""
        services = []
        
        if hasattr(target_data, 'open_ports'):
            for port_info in target_data.open_ports:
                service_data = type('Service', (), {
                    'port': getattr(port_info, 'port', 0),
                    'protocol': getattr(port_info, 'protocol', 'tcp'),
                    'service_name': getattr(port_info, 'service', 'unknown'),
                    'version': getattr(port_info, 'version', ''),
                    'secure': getattr(port_info, 'secure', False)
                })()
                services.append(service_data)
        
        return services
    
    def _transform_security_patterns(self, target_data: Any) -> list:
        """Transform patterns with security analysis focus"""
        patterns = []
        
        if hasattr(target_data, 'patterns'):
            for pattern in target_data.patterns:
                # Extract security level from pattern description
                pattern_text = str(pattern)
                description = pattern_text
                
                # Try to extract structured information from pattern
                if ':' in pattern_text and len(pattern_text.split(':')) >= 2:
                    parts = pattern_text.split(':', 1)
                    description = parts[1].strip()
                
                pattern_data = type('Pattern', (), {
                    'description': description,
                    'original': pattern_text
                })()
                patterns.append(pattern_data)
        
        return patterns
    
    def _transform_web_services_security(self, target_data: Any) -> list:
        """Transform web services with security analysis focus"""
        web_services = []
        
        if hasattr(target_data, 'web_services'):
            for web_service in target_data.web_services:
                # Extract directories and files from web service
                directories = []
                files = []
                
                if hasattr(web_service, 'directories'):
                    for directory in web_service.directories:
                        if isinstance(directory, dict):
                            dir_data = type('Directory', (), {
                                'path': directory.get('path', ''),
                                'status': directory.get('status', ''),
                                'size': directory.get('size', '')
                            })()
                        else:
                            dir_data = type('Directory', (), {
                                'path': str(directory),
                                'status': '',
                                'size': ''
                            })()
                        directories.append(dir_data)
                
                if hasattr(web_service, 'files'):
                    for file in web_service.files:
                        if isinstance(file, dict):
                            file_data = type('File', (), {
                                'path': file.get('path', ''),
                                'status': file.get('status', ''),
                                'size': file.get('size', '')
                            })()
                        else:
                            file_data = type('File', (), {
                                'path': str(file),
                                'status': '',
                                'size': ''
                            })()
                        files.append(file_data)
                
                ws_data = type('WebService', (), {
                    'url': getattr(web_service, 'url', ''),
                    'port': getattr(web_service, 'port', 80),
                    'title': getattr(web_service, 'title', ''),
                    'server': getattr(web_service, 'server', ''),
                    'cms': getattr(web_service, 'cms', ''),
                    'technologies': getattr(web_service, 'technologies', []),
                    'directories': directories,
                    'files': files
                })()
                web_services.append(ws_data)
        
        return web_services
    
    def _transform_manual_commands_security(self, target_data: Any) -> list:
        """Transform manual commands with security analysis focus"""
        manual_commands = []
        
        if hasattr(target_data, 'manual_commands'):
            current_group = None
            commands_in_group = []
            
            for command in target_data.manual_commands:
                command_text = str(command)
                
                # Try to extract title and commands from the manual command
                if ':' in command_text:
                    parts = command_text.split(':', 1)
                    title = parts[0].strip()
                    remaining = parts[1].strip() if len(parts) > 1 else ''
                    
                    # If we have a new title, finish the previous group
                    if current_group and current_group != title:
                        if commands_in_group:
                            group_data = type('CommandGroup', (), {
                                'title': current_group,
                                'commands': commands_in_group.copy()
                            })()
                            manual_commands.append(group_data)
                        commands_in_group = []
                    
                    current_group = title
                    if remaining:
                        commands_in_group.append(remaining)
                else:
                    # No title, add to current group or create default group
                    if not current_group:
                        current_group = "Manual Commands"
                    commands_in_group.append(command_text)
            
            # Add the final group
            if current_group and commands_in_group:
                group_data = type('CommandGroup', (), {
                    'title': current_group,
                    'commands': commands_in_group
                })()
                manual_commands.append(group_data)
        
        return manual_commands
    
    def _transform_output_files(self, target_name: str, target_data: Any) -> list:
        """Transform output files for security analysis"""
        output_files = []
        
        try:
            import os
            import time
            # Construct path to target's scan directory
            results_base = os.path.join(os.getcwd(), 'results', target_name, 'scans')
            
            if os.path.exists(results_base):
                for root, dirs, files in os.walk(results_base):
                    for filename in files:
                        if not filename.startswith('.') and not filename.startswith('_'):
                            file_path = os.path.join(root, filename)
                            try:
                                stat = os.stat(file_path)
                                size = self._format_file_size(stat.st_size)
                                modified = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
                                
                                # Try to extract plugin name from filename
                                plugin = 'unknown'
                                if '_' in filename:
                                    parts = filename.split('_')
                                    if len(parts) >= 3:
                                        plugin = parts[2]  # Usually format: protocol_port_plugin_*
                                
                                file_data = type('OutputFile', (), {
                                    'name': filename,
                                    'size': size,
                                    'modified': modified,
                                    'plugin': plugin
                                })()
                                output_files.append(file_data)
                            except (OSError, IndexError):
                                continue
        except Exception:
            pass
        
        return output_files
    
    
    def _transform_pattern_matches(self, target_name: str, target_data: Any) -> list:
        """Transform pattern matches with rich context and plugin information"""
        pattern_matches = []
        
        if hasattr(target_data, 'patterns') and target_data.patterns:
            for pattern in target_data.patterns:
                # Parse pattern for plugin information and severity
                plugin_name = "Unknown Plugin"
                description = pattern
                matched_text = ""
                file_path = ""
                
                # Try to extract plugin and severity information
                if ':' in pattern:
                    parts = pattern.split(':', 1)
                    if len(parts) == 2:
                        potential_plugin = parts[0].strip()
                        description = parts[1].strip()
                        
                        # Check if first part looks like a plugin name (common tool names or patterns)
                        plugin_names = ['nikto', 'nmap', 'feroxbuster', 'gobuster', 'dirsearch', 'ssh', 'smb', 'http', 'ssl', 'ftp', 'snmp', 'mysql', 'ldap', 'dns', 'git']
                        pattern_types = ['technology stack', 'server banner', 'directory', 'file', 'service', 'version']
                        
                        if (any(plugin in potential_plugin.lower() for plugin in plugin_names) or
                            any(keyword in potential_plugin.lower() for keyword in ['scan', 'enum', 'test', 'check', 'probe']) or
                            any(ptype in potential_plugin.lower() for ptype in pattern_types)):
                            plugin_name = potential_plugin
                        else:
                            description = pattern
                
                # Extract matched text if available
                if ' - ' in description:
                    desc_parts = description.split(' - ', 1)
                    matched_text = desc_parts[0]
                    description = desc_parts[1] if len(desc_parts) > 1 else description
                
                match_data = {
                    'plugin_name': plugin_name,
                    'description': description,
                    'matched_text': matched_text,
                    'file_path': file_path,
                    'target': target_name
                }
                pattern_matches.append(type('PatternMatch', (), match_data)())
        
        return pattern_matches
    
    
    def _extract_vulnerabilities(self, target_data: Any) -> list:
        """Extract all vulnerabilities from target data"""
        vulnerabilities = []
        
        if hasattr(target_data, 'vulnerabilities'):
            for vuln in target_data.vulnerabilities:
                vuln_data = {
                    'title': getattr(vuln, 'title', 'Unknown Vulnerability'),
                    'severity': getattr(vuln, 'severity', 'medium'),
                    'description': getattr(vuln, 'description', ''),
                    'plugin_name': getattr(vuln, 'plugin_name', 'Unknown')
                }
                vulnerabilities.append(type('Vulnerability', (), vuln_data)())
        
        return vulnerabilities
    
    def _extract_raw_files(self, target_name: str, target_data: Any) -> list:
        """Extract raw scan files for display"""
        raw_files = []
        
        try:
            import os
            import re
            # Construct path to target's scan directory
            results_base = os.path.join(os.getcwd(), 'results', target_name, 'scans')
            
            if os.path.exists(results_base):
                # Scan all port directories for output files
                for port_dir in os.listdir(results_base):
                    port_path = os.path.join(results_base, port_dir)
                    if os.path.isdir(port_path):
                        for filename in os.listdir(port_path):
                            file_path = os.path.join(port_path, filename)
                            if os.path.isfile(file_path) and not filename.startswith('.'):
                                # Get file size
                                size = os.path.getsize(file_path)
                                size_str = self._format_file_size(size)
                                
                                # Check if this is a wordlist result file that needs parsing
                                content = ""
                                if self._is_wordlist_result_file(filename):
                                    # Parse wordlist result files to extract only positive findings
                                    content = self._parse_wordlist_result_file(file_path, filename, size_str)
                                elif size < 50000:  # Only read small files directly
                                    try:
                                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                            content = f.read()
                                    except:
                                        content = "Binary file or read error"
                                else:
                                    content = f"File too large ({size_str}) - not displayed"
                                
                                file_data = {
                                    'name': filename,
                                    'path': file_path,
                                    'size': size_str,
                                    'content': content
                                }
                                raw_files.append(type('RawFile', (), file_data)())
        except Exception as e:
            # If file reading fails, return empty list
            pass
        
        return raw_files
    
    def _is_wordlist_result_file(self, filename: str) -> bool:
        """Check if this file is a wordlist result file that should be parsed"""
        wordlist_patterns = [
            'vhosts', 'vhost', 'subdomain', 'directory', 'directories', 'dirbuster', 
            'feroxbuster', 'gobuster', 'ffuf', 'enhanced_vhosts', 'subdomains'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in wordlist_patterns)
    
    def _parse_wordlist_result_file(self, file_path: str, filename: str, size_str: str) -> str:
        """Parse wordlist result files to extract only positive findings"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            positive_findings = []
            filename_lower = filename.lower()
            
            # Parse based on file type
            if 'vhost' in filename_lower or 'subdomain' in filename_lower:
                positive_findings = self._parse_vhost_findings(content)
            elif 'director' in filename_lower or 'dirbuster' in filename_lower or 'feroxbuster' in filename_lower:
                directories, files = self._parse_directory_findings(content)
                positive_findings = directories + files
            else:
                # Generic parsing for other wordlist result files
                positive_findings = self._parse_generic_findings(content)
            
            if positive_findings:
                findings_text = "\n".join(positive_findings[:50])  # Limit to first 50 findings
                total_findings = len(positive_findings)
                
                if total_findings > 50:
                    findings_text += f"\n\n... and {total_findings - 50} more findings"
                
                return f"📊 Wordlist Results ({size_str}) - {total_findings} positive findings:\n\n{findings_text}"
            else:
                # Check if this is a raw wordlist file (no positive findings)
                if content.count('\n') > 100 and not any(char in content[:1000] for char in [',', 'http', '://', 'Status:']):
                    return f"📊 Wordlist Results ({size_str}) - No positive findings (raw wordlist file)"
                else:
                    return f"📊 Wordlist Results ({size_str}) - No positive findings found"
                    
        except Exception as e:
            return f"📊 Wordlist Results ({size_str}) - Error parsing file: {e}"
    
    def _parse_vhost_findings(self, content: str) -> list:
        """Parse virtual host/subdomain enumeration results"""
        findings = []
        
        # Check if this is CSV format (ffuf output)
        if 'url,redirectlocation,position,status_code,content_length,content_words,content_lines,content_type,duration' in content:
            # Parse CSV format
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('url,'):  # Skip header and empty lines
                    continue
                
                try:
                    parts = line.split(',')
                    if len(parts) >= 4:
                        url = parts[0]
                        status_code = parts[3]
                        
                        # Only include successful responses
                        if status_code in ['200', '301', '302', '303', '403', '401']:
                            findings.append(f"{url} [{status_code}]")
                except (IndexError, ValueError):
                    continue
        else:
            # Parse other formats
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Look for lines with good status codes
                if re.search(r'\b(200|301|302|403)\b', line) and not re.search(r'\b(404|500|502|503)\b', line):
                    findings.append(line)
                # Check if this line looks like a direct subdomain
                elif re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z0-9.-]+$', line) and len(line.split('.')) >= 2:
                    findings.append(line)
        
        return findings
    
    def _parse_directory_findings(self, content: str) -> tuple:
        """Parse directory/file enumeration results"""
        directories = []
        files = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Look for successful directory/file discoveries
            if re.search(r'\b(200|301|302|403)\b', line):
                # Extract path from the line
                path_match = re.search(r'(https?://[^\s]+|/[^\s]*)', line)
                if path_match:
                    path = path_match.group(1)
                    if path.endswith('/'):
                        directories.append(line)
                    else:
                        files.append(line)
        
        return directories, files
    
    def _parse_generic_findings(self, content: str) -> list:
        """Parse generic wordlist result files"""
        findings = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Look for lines with successful status codes
            if re.search(r'\b(200|301|302|403)\b', line) and not re.search(r'\b(404|500|502|503)\b', line):
                findings.append(line)
        
        return findings
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def _extract_notes(self, target_data: Any) -> list:
        """Extract notes and observations"""
        notes = []
        
        if hasattr(target_data, 'notes'):
            for note in target_data.notes:
                note_data = {
                    'plugin_name': getattr(note, 'plugin_name', 'General'),
                    'content': getattr(note, 'content', str(note)),
                    'timestamp': getattr(note, 'timestamp', '')
                }
                notes.append(type('Note', (), note_data)())
        
        return notes
    
    def _prepare_quick_access_data(self, targets: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        """Prepare quick access data for templates"""
        
        web_services = []
        common_services = []
        vulnerabilities = []
        credentials = []
        
        for target_name, target_data in targets.items():
            # Collect web services
            if hasattr(target_data, 'web_services'):
                for web_service in target_data.web_services:
                    web_services.append({
                        'url': getattr(web_service, 'url', ''),
                        'title': getattr(web_service, 'title', ''),
                        'status_code': getattr(web_service, 'status_code', 200)
                    })
            
            # Collect common services  
            if hasattr(target_data, 'open_ports'):
                for service in target_data.open_ports:
                    service_name = getattr(service, 'service', 'unknown')
                    if service_name in ['ssh', 'ftp', 'smtp', 'dns', 'mysql', 'postgres', 'redis']:
                        common_services.append({
                            'target': target_name,
                            'port': getattr(service, 'port', 0),
                            'service': service_name,
                            'version': getattr(service, 'version', '')
                        })
            
            # Collect vulnerabilities
            if hasattr(target_data, 'vulnerabilities'):
                for vuln in target_data.vulnerabilities:
                    vulnerabilities.append({
                        'target': target_name,
                        'description': str(vuln)
                    })
            
            # Look for credentials in access_info
            if hasattr(target_data, 'open_ports'):
                for service in target_data.open_ports:
                    if hasattr(service, 'access_info') and service.access_info:
                        for key, value in service.access_info.items():
                            if 'username' in key.lower() or 'password' in key.lower() or 'credential' in key.lower():
                                credentials.append({
                                    'service': f"{target_name}:{getattr(service, 'port', 0)}",
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