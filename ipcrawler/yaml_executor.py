"""
YAML Plugin Executor for IPCrawler

This module provides the execution engine for YAML-based plugins, integrating seamlessly
with the existing Python plugin system while providing enhanced debugging capabilities.
"""

import os
import re
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging

# Add audit logging
audit_logger = logging.getLogger('yaml_audit')

# Removed alive_progress integration to avoid conflicts with existing user_display system

from ipcrawler.config import config
from ipcrawler.yaml_plugins import YamlPluginLoader, YamlPlugin, PluginType
from ipcrawler.plugin_debugger import PluginDebugger
from ipcrawler.targets import Service
from ipcrawler.user_display import user_display

logger = logging.getLogger(__name__)


@dataclass
class YamlExecutionResult:
    """Result of YAML plugin execution"""
    type: str  # 'port', 'service', 'report'
    plugin_slug: str
    success: bool
    result: Any
    error: Optional[str] = None
    commands_executed: List[str] = None
    patterns_matched: Dict[str, List[str]] = None
    execution_time: float = 0.0


class YamlPluginExecutor:
    """
    Executes YAML-based plugins with the same interface as Python plugins.
    
    This executor:
    - Evaluates service conditions for plugin selection
    - Executes commands with proper variable substitution
    - Processes output with pattern matching
    - Integrates with existing plugin debugging system
    """
    
    def __init__(self, loader: YamlPluginLoader, debugger: Optional[PluginDebugger] = None):
        """
        Initialize YAML plugin executor.
        
        Args:
            loader: YAML plugin loader instance
            debugger: Optional plugin debugger instance
        """
        self.loader = loader
        self.debugger = debugger
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time': 0.0,
            'plugins_executed': set()
        }
    
    def get_yaml_plugins_for_target(self, target, plugin_type: PluginType) -> List[YamlPlugin]:
        """
        Get YAML plugins that should run for a target.
        
        Args:
            target: Target object
            plugin_type: Type of plugins to filter by
            
        Returns:
            List of YAML plugins that should run for the target
        """
        matching_plugins = []
        
        for plugin in self.loader.plugins.values():
            if plugin.metadata.type != plugin_type:
                continue
            
            # For port scan plugins, check general target conditions
            should_run = self._evaluate_target_conditions(plugin, target)
            
            reason = f"Target conditions {'passed' if should_run else 'failed'}"
            
            if self.debugger:
                self.debugger.log_plugin_selection(
                    plugin.metadata.name,
                    target.address,
                    should_run,
                    reason,
                    plugin_type.value
                )
            
            if should_run:
                matching_plugins.append(plugin)
        
        return matching_plugins
    
    def get_yaml_plugins_for_service(self, service, plugin_type: PluginType) -> List[YamlPlugin]:
        """
        Get YAML plugins that should run for a service.
        
        Args:
            service: Service object
            plugin_type: Type of plugins to filter by
            
        Returns:
            List of YAML plugins that should run for the service
        """
        matching_plugins = []
        target_service = f"{service.target.address}:{service.port}"
        
        for plugin in self.loader.plugins.values():
            if plugin.metadata.type != plugin_type:
                continue
            
            # Evaluate service conditions
            should_run, reason = self._evaluate_service_conditions(plugin, service)
            
            if self.debugger:
                self.debugger.log_plugin_selection(
                    plugin.metadata.name,
                    target_service,
                    should_run,
                    reason,
                    plugin_type.value
                )
            
            if should_run:
                matching_plugins.append(plugin)
        
        return matching_plugins
    
    def _evaluate_target_conditions(self, plugin: YamlPlugin, target) -> bool:
        """
        Evaluate if a plugin should run for a target based on conditions.
        
        Args:
            plugin: YAML plugin to evaluate
            target: Target object
            
        Returns:
            True if plugin should run for target
        """
        conditions = plugin.conditions
        
        # For now, port scan plugins run on all targets
        # Future: Add target-specific conditions like IP range checks
        return True
    
    def _evaluate_service_conditions(self, plugin: YamlPlugin, service) -> tuple[bool, str]:
        """
        Evaluate if a plugin should run for a service based on conditions.
        
        Args:
            plugin: YAML plugin to evaluate
            service: Service object
            
        Returns:
            Tuple of (should_run, reason)
        """
        conditions = plugin.conditions
        
        # Check service patterns (include/exclude)
        service_include = conditions.services_include
        service_exclude = conditions.services_exclude
        
        if self.debugger:
            target_service = f"{service.target.address}:{service.port}"
            self.debugger.log_condition_evaluation(
                plugin.metadata.slug,
                target_service,
                f"Evaluating service '{service.name}' against patterns",
                True,
                f"include: {service_include}, exclude: {service_exclude}"
            )
        
        # Check include patterns
        if service_include:
            service_matched = False
            for pattern in service_include:
                if re.search(pattern, service.name, re.IGNORECASE):
                    service_matched = True
                    break
            
            if not service_matched:
                return False, f"Service '{service.name}' did not match any include patterns: {service_include}"
        
        # Check exclude patterns
        if service_exclude:
            for pattern in service_exclude:
                if re.search(pattern, service.name, re.IGNORECASE):
                    return False, f"Service '{service.name}' matched exclude pattern: {pattern}"
        
        # Check port conditions
        port_include = conditions.ports_include
        port_exclude = conditions.ports_exclude
        
        if port_include and service.port not in port_include:
            return False, f"Port {service.port} not in allowed ports: {port_include}"
        
        if port_exclude and service.port in port_exclude:
            return False, f"Port {service.port} in excluded ports: {port_exclude}"
        
        # Check protocol conditions
        protocol_include = conditions.protocols_include
        protocol_exclude = conditions.protocols_exclude
        
        if protocol_include and service.protocol not in protocol_include:
            return False, f"Protocol '{service.protocol}' not in allowed protocols: {protocol_include}"
        
        if protocol_exclude and service.protocol in protocol_exclude:
            return False, f"Protocol '{service.protocol}' in excluded protocols: {protocol_exclude}"
        
        # Check SSL/secure conditions
        require_ssl = conditions.ssl_required
        
        if require_ssl and not service.secure:
            return False, "Plugin requires SSL but service is not secure"
        
        if require_ssl is False and service.secure:
            return False, "Plugin excludes SSL but service is secure"
        
        return True, f"Service '{service.name}' on {service.protocol}/{service.port} matches all conditions"
    
    async def execute_yaml_plugin_for_target(self, plugin: YamlPlugin, target) -> Dict[str, Any]:
        """
        Execute a YAML plugin for a target (port scan).
        
        Args:
            plugin: YAML plugin to execute
            target: Target object
            
        Returns:
            Execution result dictionary
        """
        import time
        start_time = time.time()
        
        # Show plugin start message
        user_display.plugin_start(target.address, plugin.metadata.name)
        
        try:
            # Prepare execution environment
            env_vars = self._prepare_target_environment(plugin, target)
            
            # Execute commands
            commands_executed = []
            all_output = ""
            
            commands = plugin.commands
            
            for command_config in commands:
                command = command_config.command
                if not command:
                    continue
                
                # Process environment variables from command config
                command_env = self._process_command_environment(command_config, env_vars)
                
                # Substitute variables in command
                substituted_command = self._substitute_variables(command, command_env)
                
                # Apply sudo if required and enabled
                final_command = self._apply_sudo_if_required(substituted_command, plugin)
                commands_executed.append(final_command)
                
                # Debug: Log the actual command being executed
                logger.debug(f"Executing YAML plugin command: {final_command}")
                
                # Execute command with timeout from YAML
                try:
                    command_timeout = getattr(command_config, 'timeout', None)
                    result = await self._execute_command(final_command, target.scandir, timeout=command_timeout)
                    all_output += result.stdout + result.stderr
                    
                    # Save output to file if specified in YAML
                    output_file = getattr(command_config, 'output_file', None)
                    if output_file:
                        # Substitute variables in output filename
                        output_filename = self._substitute_variables(output_file, command_env)
                        output_path = os.path.join(target.scandir, output_filename)
                        
                        # Save stdout to the specified file
                        try:
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(result.stdout)
                            logger.debug(f"Saved output to: {output_path}")
                        except Exception as file_error:
                            logger.warning(f"Failed to save output file {output_path}: {file_error}")
                
                except Exception as e:
                    logger.error(f"Command execution failed: {e}")
                    return {
                        'type': 'port',
                        'result': [],
                        'success': False,
                        'error': f"Command execution failed: {e}",
                        'execution_time': time.time() - start_time
                    }
            
            # Process output patterns
            patterns_matched = {}
            services_found = []
            
            patterns = plugin.patterns
            
            for pattern_config in patterns:
                pattern_name = pattern_config.description  # Use description as name
                pattern_regex = pattern_config.pattern
                
                if not pattern_regex:
                    continue
                
                matches = re.findall(pattern_regex, all_output, re.MULTILINE | re.IGNORECASE)
                patterns_matched[pattern_name] = matches
                
                # For port scan plugins, patterns are for information only
                # Service detection is handled separately below
            
            # Process service detection patterns for port scan plugins
            if plugin.metadata.type == PluginType.PORTSCAN and plugin.service_detection:
                for service_det in plugin.service_detection:
                    pattern_regex = service_det.pattern
                    service_name_template = service_det.service_name
                    port_override = service_det.port_override
                    
                    if not pattern_regex:
                        continue
                    
                    matches = re.findall(pattern_regex, all_output, re.MULTILINE | re.IGNORECASE)
                    
                    for match in matches:
                        try:
                            # Handle both tuple and string matches
                            if isinstance(match, tuple):
                                # For regex groups like (port, protocol, service)
                                if len(match) >= 3:
                                    port_str, protocol, detected_service = match[0], match[1], match[2]
                                else:
                                    continue
                            else:
                                # Single match - need to parse differently
                                continue
                            
                            # Use port override if specified, otherwise extract from match
                            port = int(port_override) if port_override else int(port_str)
                            
                            # Resolve service name template with match groups
                            service_name = service_name_template
                            for i, group in enumerate(match):
                                service_name = service_name.replace(f"{{match{i+1}}}", str(group))
                            
                            # Special case: if service_name still has template vars, use detected_service
                            if "{match" in service_name:
                                service_name = detected_service
                                
                            # Determine if service is secure
                            secure = 'ssl' in detected_service.lower() or 'tls' in detected_service.lower() or 'https' in detected_service.lower()
                            
                            # Clean service name (remove ssl/ prefix if present)
                            if service_name.startswith('ssl/'):
                                service_name = service_name[4:]
                            elif service_name.startswith('tls/'):
                                service_name = service_name[4:]
                            
                            # Create Service object
                            service_obj = Service(protocol.lower(), port, service_name, secure)
                            # Set target reference (will be set properly by main.py)
                            service_obj.target = target
                            
                            services_found.append(service_obj)
                            
                        except (ValueError, IndexError) as e:
                            logger.debug(f"Failed to parse service from match {match}: {e}")
                            continue
            
            execution_time = time.time() - start_time
            
            # Show plugin completion message
            duration = f"{execution_time:.1f}s"
            user_display.plugin_complete(target.address, plugin.metadata.name, duration, success=True)
            
            # Update execution stats
            self.execution_stats['total_executions'] += 1
            self.execution_stats['successful_executions'] += 1
            self.execution_stats['total_execution_time'] += execution_time
            self.execution_stats['plugins_executed'].add(plugin.metadata.name)
            
            return {
                'type': 'port',
                'result': services_found,
                'success': True,
                'commands_executed': commands_executed,
                'patterns_matched': patterns_matched,
                'execution_time': execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Show plugin failure message
            duration = f"{execution_time:.1f}s"
            user_display.plugin_complete(target.address, plugin.metadata.name, duration, success=False)
            
            self.execution_stats['total_executions'] += 1
            self.execution_stats['failed_executions'] += 1
            self.execution_stats['total_execution_time'] += execution_time
            
            logger.error(f"YAML plugin {plugin.metadata.name} execution failed: {e}")
            return {
                'type': 'port',
                'result': [],
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            }
    
    async def execute_yaml_plugin_for_service(self, plugin: YamlPlugin, service) -> Dict[str, Any]:
        """
        Execute a YAML plugin for a service (service scan).
        
        Args:
            plugin: YAML plugin to execute
            service: Service object
            
        Returns:
            Execution result dictionary
        """
        import time
        start_time = time.time()
        
        # Show plugin start message
        target_service = f"{service.target.address}:{service.port}"
        user_display.plugin_start(target_service, plugin.metadata.name)
        
        try:
            # Prepare execution environment
            env_vars = self._prepare_service_environment(plugin, service)
            
            # Execute commands
            commands_executed = []
            all_output = ""
            
            commands = plugin.commands
            
            # Determine scan directory
            scandir = service.target.scandir
            if not config.get('no_port_dirs', False):
                scandir = os.path.join(scandir, f"{service.protocol}{service.port}")
                os.makedirs(scandir, exist_ok=True)
                os.makedirs(os.path.join(scandir, 'xml'), exist_ok=True)
            
            for command_config in commands:
                command = command_config.command
                if not command:
                    continue
                
                # Process environment variables from command config
                command_env = self._process_command_environment(command_config, env_vars)
                
                # Substitute variables in command
                substituted_command = self._substitute_variables(command, command_env)
                
                # Apply sudo if required and enabled
                final_command = self._apply_sudo_if_required(substituted_command, plugin)
                commands_executed.append(final_command)
                
                # Execute command with timeout from YAML
                try:
                    command_timeout = getattr(command_config, 'timeout', None)
                    result = await self._execute_command(final_command, scandir, timeout=command_timeout)
                    all_output += result.stdout + result.stderr
                    
                    # Save output to file if specified in YAML
                    output_file = getattr(command_config, 'output_file', None)
                    if output_file:
                        # Substitute variables in output filename
                        output_filename = self._substitute_variables(output_file, command_env)
                        output_path = os.path.join(scandir, output_filename)
                        
                        # Save stdout to the specified file
                        try:
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(result.stdout)
                            logger.debug(f"Saved output to: {output_path}")
                        except Exception as file_error:
                            logger.warning(f"Failed to save output file {output_path}: {file_error}")
                
                except Exception as e:
                    logger.error(f"Command execution failed: {e}")
                    return {
                        'type': 'service',
                        'result': None,
                        'success': False,
                        'error': f"Command execution failed: {e}",
                        'execution_time': time.time() - start_time
                    }
            
            # Process output patterns
            patterns_matched = {}
            findings = []
            
            patterns = plugin.patterns
            
            for pattern_config in patterns:
                pattern_name = pattern_config.description  # Use description as name
                pattern_regex = pattern_config.pattern
                
                if not pattern_regex:
                    continue
                
                matches = re.findall(pattern_regex, all_output, re.MULTILINE | re.IGNORECASE)
                patterns_matched[pattern_name] = matches
                
                # Extract findings from matches
                if matches:
                    # Simplified finding extraction for YAML plugins
                    for match in matches:
                        finding = {
                            'pattern': pattern_name,
                            'match': match,
                            'severity': pattern_config.severity.value,
                            'category': pattern_config.category
                        }
                        findings.append(finding)
            
            execution_time = time.time() - start_time
            
            # Show plugin completion message
            target_service = f"{service.target.address}:{service.port}"
            duration = f"{execution_time:.1f}s"
            user_display.plugin_complete(target_service, plugin.metadata.name, duration, success=True)
            
            # Update execution stats
            self.execution_stats['total_executions'] += 1
            self.execution_stats['successful_executions'] += 1
            self.execution_stats['total_execution_time'] += execution_time
            self.execution_stats['plugins_executed'].add(plugin.metadata.name)
            
            return {
                'type': 'service',
                'result': findings,
                'success': True,
                'commands_executed': commands_executed,
                'patterns_matched': patterns_matched,
                'execution_time': execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Show plugin failure message
            target_service = f"{service.target.address}:{service.port}"
            duration = f"{execution_time:.1f}s"
            user_display.plugin_complete(target_service, plugin.metadata.name, duration, success=False)
            
            self.execution_stats['total_executions'] += 1
            self.execution_stats['failed_executions'] += 1
            self.execution_stats['total_execution_time'] += execution_time
            
            logger.error(f"YAML plugin {plugin.metadata.name} execution failed: {e}")
            return {
                'type': 'service',
                'result': None,
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            }
    
    def _prepare_target_environment(self, plugin: YamlPlugin, target) -> Dict[str, str]:
        """
        Prepare environment variables for target-based execution.
        
        Args:
            plugin: YAML plugin
            target: Target object
            
        Returns:
            Dictionary of environment variables
        """
        # Load global variables and merge with plugin-specific variables
        env_vars = self._load_environment_variables(plugin, target)
        
        # Debug: Log environment variables
        logger.debug(f"Target environment variables: {env_vars}")
        
        return env_vars
    
    def _load_environment_variables(self, plugin: YamlPlugin, target=None, service=None) -> Dict[str, str]:
        """
        Load environment variables from global config and plugin-specific definitions.
        
        Args:
            plugin: YAML plugin with variable definitions
            target: Target object (for target-based plugins)
            service: Service object (for service-based plugins)
            
        Returns:
            Dictionary of environment variables
        """
        # Start with base target/service variables
        env_vars = {}
        
        if target:
            # Get hostname from target's hostname discovery
            hostname = target.get_best_hostname()
            all_hostnames = target.get_all_hostnames()
            
            env_vars.update({
                'address': target.address,
                'target': target.address,
                'ip': getattr(target, 'ip', target.address),
                'scandir': target.scandir,
                'ipversion': getattr(target, 'ipversion', 'IPv4'),
                'hostname': hostname,
                'best_hostname': hostname,  # Alias for hostname
                'smart_hostnames': ' '.join(all_hostnames[:3]),  # Top 3 hostnames for smart scanning
                'all_hostnames': ' '.join(all_hostnames),  # Space-separated for bash loops
                'all_hostnames_comma': ','.join(all_hostnames),  # Comma-separated for other uses
                'hostname_label': hostname.replace('.', '_').replace(':', '_'),
                'hostname_safe': hostname.replace('.', '-').replace(':', '-'),
                'hostname_clean': ''.join(c for c in hostname if c.isalnum() or c in '.-'),
                'target_type': target.type if hasattr(target, 'type') else 'ip',
            })
        
        if service:
            # Get hostname from target's hostname discovery
            hostname = service.target.get_best_hostname()
            all_hostnames = service.target.get_all_hostnames()
            
            env_vars.update({
                'port': str(service.port),
                'protocol': service.protocol,
                'service': service.name,
                'service_name': service.name,
                'secure': 'true' if service.secure else 'false',
                'http_scheme': 'https' if ('https' in service.name or service.secure) else 'http',
                'url': f"{'https' if ('https' in service.name or service.secure) else 'http'}://{hostname}:{service.port}",
                'hostname': hostname,
                'best_hostname': hostname,  # Alias for hostname
                'smart_hostnames': ' '.join(all_hostnames[:3]),  # Top 3 hostnames for smart scanning
                'all_hostnames': ' '.join(all_hostnames),  # Space-separated for bash loops
                'all_hostnames_comma': ','.join(all_hostnames),  # Comma-separated for other uses
                'hostname_label': hostname.replace('.', '_').replace(':', '_'),
                'hostname_safe': hostname.replace('.', '-').replace(':', '-'),
                'hostname_clean': ''.join(c for c in hostname if c.isalnum() or c in '.-'),
                'target_type': target.type if hasattr(target, 'type') else 'ip',
            })
        
        # Add plugin metadata
        env_vars.update({
            'plugin_slug': plugin.metadata.name,
            'plugin_name': plugin.metadata.name,
        })
        
        # Add config-based variables
        env_vars.update({
            'ports_tcp': (config.get('ports') or {}).get('tcp', ''),
            'ports_udp': (config.get('ports') or {}).get('udp', ''),
            'target_ports_tcp': (config.get('ports') or {}).get('tcp', '-'),
            'target_ports_udp': (config.get('ports') or {}).get('udp', '53,67,68,123,161,162,500,514,1194,1701,4500'),
        })
        
        # Add commonly used variables from global configuration
        env_vars.update({
            # Performance/timing variables (more reasonable defaults)
            'timeout': str(config.get('timeout') or 600),  # Increased default timeout
            'min_rate': str(config.get('min_rate') or 1000),
            'max_rate': str(config.get('max_rate') or 4000),
            'timing_template': str(config.get('timing_template') or 4),
            'threads': str(config.get('threads') or 20),
            'aggression': str(config.get('aggression') or 1),
            
            # HTTP-specific variables with more granular timeouts
            'http_timeout': str(config.get('http_timeout') or 30),
            'git_timeout': str(config.get('git_timeout') or 120),  # Git operations need more time
            'bruteforce_timeout': str(config.get('bruteforce_timeout') or 900),  # 15 minutes for bruteforce
            'directory_timeout': str(config.get('directory_timeout') or 600),  # 10 minutes for directory scans
            
            # Directory/file enumeration variables
            'recursive_flag': '-r' if config.get('recursive', True) else '',
            'ext': config.get('extensions') or 'php,html,txt,asp,aspx,jsp,js,css,json,xml',
            'extras': config.get('extras') or '',
            
            # Numeric timeout values (for backward compatibility)
            '300': '300',
            '600': '600',
            '1000': '1000',
            '4000': '4000',
            
            # Service-specific options
            'service_opts': config.get('service_opts') or '',
            'timing_opts': config.get('timing_opts') or '',
            
            # Web enumeration variables
            'status_codes': config.get('status_codes') or '200,204,301,302,307,403,500',
            'follow_flag': 'L' if config.get('follow_redirects', False) else '',
            'vhost_mode': config.get('vhost_mode') or 'auto',
        })
        
        # Load global variables from global.toml
        global_vars = self._load_global_variables()
        env_vars.update(global_vars)
        
        # Pre-compute conditional variables to replace Jinja2 conditionals
        env_vars = self._prepare_conditional_environment_variables(env_vars)
        
        # Plugin-specific variables override global ones
        if plugin.variables:
            # Process plugin variables with legacy substitution
            for var_name, var_value in plugin.variables.items():
                env_vars[var_name] = str(var_value)
        
        # Also process plugin options as variables (for backward compatibility)
        if hasattr(plugin, 'options') and plugin.options:
            for option in plugin.options:
                if hasattr(option, 'name') and hasattr(option, 'default'):
                    var_name = option.name
                    var_value = option.default
                    # Only add if not already set by variables section
                    if var_name not in env_vars:
                        env_vars[var_name] = str(var_value)
        
        return env_vars
    
    def _prepare_conditional_environment_variables(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """
        Pre-compute conditional values to replace Jinja2 conditionals with simple variables.
        All tool flags are now YAML-driven - no hardcoded flags in Python code.
        
        Args:
            env_vars: Base environment variables
            
        Returns:
            Environment variables with conditional values pre-computed
        """
        # Check if proxychains is enabled
        proxychains_enabled = env_vars.get('proxychains', 'false').lower() == 'true'
        
        # Check if sudo is enabled for privileged operations
        sudo_enabled = config.get('enable_sudo', False)
        
        # Pre-compute conditional variables based on config and environment
        conditional_vars = {
            # Service scanning options (YAML-driven, no hardcoded flags)
            'service_opts': self._get_service_opts(proxychains_enabled, sudo_enabled),
            
            # Timing options (YAML-driven)
            'timing_opts': self._get_timing_opts(env_vars, proxychains_enabled),
            
            # OS detection (YAML-driven, conditional on sudo)
            'os_detection': self._get_os_detection_opts(proxychains_enabled, sudo_enabled),
            
            # Stealth options
            'stealth_opts': '-f -D' if proxychains_enabled else '',
        }
        
        # Update environment with pre-computed conditionals
        env_vars.update(conditional_vars)
        
        return env_vars
    
    def _get_service_opts(self, proxychains_enabled: bool, sudo_enabled: bool) -> str:
        """Get service detection options based on configuration."""
        if proxychains_enabled:
            return '-sV'  # Simple version detection for proxychains
        else:
            return '-sV -sC'  # Version detection + safe scripts (no root required)
    
    def _get_timing_opts(self, env_vars: Dict[str, str], proxychains_enabled: bool) -> str:
        """Get timing options based on configuration."""
        timing_template = env_vars.get("timing_template", "4")
        min_rate = env_vars.get("min_rate", "1000")
        
        if proxychains_enabled:
            return f'-T{timing_template} --min-rate={min_rate}'
        else:
            max_rate = env_vars.get("max_rate", "4000")
            return f'-T{timing_template} --min-rate={min_rate} --max-rate={max_rate}'
    
    def _get_os_detection_opts(self, proxychains_enabled: bool, sudo_enabled: bool) -> str:
        """Get OS detection options based on configuration."""
        if proxychains_enabled:
            return ''  # No OS detection through proxychains
        elif sudo_enabled:
            return ' -A --osscan-guess'  # Full aggressive scan with sudo
        else:
            return ''  # No OS detection without sudo (requires root)
    
    def _load_global_variables(self) -> Dict[str, str]:
        """
        Load global variable defaults from global.toml.
        
        Returns:
            Dictionary of global variables
        """
        try:
            import toml
            from pathlib import Path
            
            # Find global.toml relative to this file
            global_toml_path = Path(__file__).parent / 'global.toml'
            
            if global_toml_path.exists():
                with open(global_toml_path, 'r') as f:
                    global_config = toml.load(f)
                    
                # Extract global variables
                global_vars = global_config.get('global', {}).get('variables', {})
                
                # Convert all values to strings
                return {k: str(v) for k, v in global_vars.items()}
            else:
                logger.warning(f"Global config file not found: {global_toml_path}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to load global variables: {e}")
            return {}
    
    def _prepare_service_environment(self, plugin: YamlPlugin, service) -> Dict[str, str]:
        """
        Prepare environment variables for service-based execution.
        
        Args:
            plugin: YAML plugin
            service: Service object
            
        Returns:
            Dictionary of environment variables
        """
        env_vars = self._prepare_target_environment(plugin, service.target)
        
        # Add service-specific variables (using hostname from service environment)
        service_hostname = env_vars.get('hostname', service.target.address)
        env_vars.update({
            'port': str(service.port),
            'protocol': service.protocol,
            'service': service.name,
            'service_name': service.name,
            'secure': 'true' if service.secure else 'false',
            'http_scheme': 'https' if ('https' in service.name or service.secure) else 'http',
            'url': f"{'https' if ('https' in service.name or service.secure) else 'http'}://{service_hostname}:{service.port}",
        })
        
        # Add wordlist resolution logic
        resolved_wordlists = self._resolve_wordlists(plugin, service)
        env_vars.update(resolved_wordlists)
        
        # Add common wordlist variables (with aliases for compatibility)
        username_wl = self._get_wordlist_path('usernames')
        password_wl = self._get_wordlist_path('passwords')
        env_vars.update({
            'wordlist_users': username_wl,  # Alias for username_wordlist
            'wordlist_passwords': password_wl,  # Alias for password_wordlist
            'wordlist_common_users': self._get_wordlist_path('common_users'),
            'username_wordlist': username_wl,
            'password_wordlist': password_wl,
            'wordlist_name': self._get_wordlist_name(resolved_wordlists.get('wordlist')),
        })
        
        return env_vars
    
    def _substitute_variables(self, command: str, env_vars: Dict[str, str]) -> str:
        """
        Substitute variables in command string using legacy variable substitution.
        
        Args:
            command: Command template with variables
            env_vars: Environment variables for substitution
            
        Returns:
            Command with variables substituted
        """
        original_command = command
        audit_logger.debug(f"🔀 STAGE 4 - Variable Substitution (Legacy):")
        audit_logger.debug(f"   Original command: {repr(original_command[:150])}")
        audit_logger.debug(f"   Available variables: {list(env_vars.keys())}")
        
        # Handle dot notation variables first (target.ports.tcp, etc.)
        command = self._resolve_dot_notation_variables(command, env_vars)
        
        # Handle simple {variable} substitution
        for var_name, var_value in env_vars.items():
            var_pattern = f'{{{var_name}}}'
            if var_pattern in command:
                audit_logger.debug(f"   🔄 Substituting {var_pattern} → {repr(var_value)}")
                command = command.replace(var_pattern, str(var_value))
        
        audit_logger.debug(f"   Final command: {repr(command[:150])}")
        
        # Check for remaining unsubstituted variables
        import re
        remaining_legacy = re.findall(r'\{([^}]+)\}', command)
        if remaining_legacy:
            audit_logger.debug(f"   ❌ UNSUBSTITUTED variables: {remaining_legacy}")
        
        return command
    
    def _resolve_dot_notation_variables(self, command: str, env_vars: Dict[str, str]) -> str:
        """
        Resolve dot notation variables like {target.ports.tcp} from environment.
        
        Args:
            command: Command with potential dot notation variables
            env_vars: Environment variables dictionary
            
        Returns:
            Command with dot notation variables resolved
        """
        import re
        
        # Find all dot notation patterns: {target.ports.tcp}
        dot_patterns = re.findall(r'\{([^}]+\.[^}]+)\}', command)
        
        for dot_pattern in dot_patterns:
            resolved_value = self._resolve_dot_notation_path(dot_pattern, env_vars)
            if resolved_value is not None:
                audit_logger.debug(f"   🎯 Dot notation {{{dot_pattern}}} → {repr(resolved_value)}")
                command = command.replace(f'{{{dot_pattern}}}', str(resolved_value))
            else:
                audit_logger.debug(f"   ❌ Failed to resolve dot notation: {{{dot_pattern}}}")
        
        return command
    
    def _resolve_dot_notation_path(self, path: str, env_vars: Dict[str, str]) -> str:
        """
        Resolve a dot notation path like 'target.ports.tcp' from environment variables.
        
        Args:
            path: Dot notation path (e.g., 'target.ports.tcp')
            env_vars: Environment variables dictionary
            
        Returns:
            Resolved value or None if path not found
        """
        parts = path.split('.')
        
        # Handle special cases for target object properties
        if len(parts) >= 3 and parts[0] == 'target' and parts[1] == 'ports':
            port_type = parts[2]  # tcp or udp
            var_name = f'target_ports_{port_type}'
            return env_vars.get(var_name, '')
        
        # Handle config object properties
        if len(parts) >= 2 and parts[0] == 'config':
            config_key = '.'.join(parts[1:])
            return env_vars.get(config_key, '')
        
        # Handle general nested object access
        value = env_vars
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return str(value) if value is not None else None
    
    def _process_command_environment(self, command_config, base_env_vars: Dict[str, str]) -> Dict[str, str]:
        """
        Process command-specific environment variables with legacy variable substitution.
        
        Args:
            command_config: Command configuration object
            base_env_vars: Base environment variables
            
        Returns:
            Combined environment variables with command-specific additions
        """
        audit_logger.debug(f"🔧 STAGE 3 - Processing Command Environment:")
        audit_logger.debug(f"   Available env_vars keys: {list(base_env_vars.keys())}")
        
        # Start with base environment
        env_vars = base_env_vars.copy()
        
        # Process command environment if present
        if hasattr(command_config, 'environment') and command_config.environment:
            for env_name, env_value in command_config.environment.items():
                audit_logger.debug(f"   Processing env {env_name}: {repr(env_value)}")
                
                if isinstance(env_value, str):
                    # Handle conditional pre-computation and variable substitution
                    processed_value = self._process_conditional_variables(env_value, env_vars)
                    audit_logger.debug(f"   🔧 Processed value for {env_name}: {repr(processed_value)}")
                    env_vars[env_name] = processed_value
                else:
                    env_vars[env_name] = str(env_value)
        
        return env_vars
    
    def _process_conditional_variables(self, template: str, env_vars: Dict[str, str]) -> str:
        """
        Process conditional logic by pre-computing values based on environment variables.
        
        Args:
            template: Template string that may contain conditional logic
            env_vars: Environment variables for context
            
        Returns:
            Processed template string with conditionals resolved
        """
        audit_logger.debug(f"🎨 Conditional Processing:")
        audit_logger.debug(f"   Template: {repr(template)}")
        
        # Handle proxychains conditional pattern
        if '{% if not config.proxychains %}' in template:
            audit_logger.debug(f"   🎯 Processing proxychains conditional")
            # Check if proxychains is enabled in config
            proxychains_enabled = env_vars.get('proxychains', 'false').lower() == 'true'
            
            import re
            match = re.search(r'{% if not config\.proxychains %}(.+?){% endif %}', template)
            if match and not proxychains_enabled:
                result = match.group(1).strip()
                audit_logger.debug(f"   ✅ Proxychains disabled, using: {repr(result)}")
                return result
            else:
                audit_logger.debug(f"   ✅ Proxychains enabled or pattern failed, returning empty")
                return ""
        
        # Handle other conditional patterns here as needed
        
        # No conditionals found, return as-is
        audit_logger.debug(f"   📝 No conditionals found, returning unchanged")
        return template
    

    async def _execute_command(self, command: str, working_dir: str, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """
        Execute a command asynchronously with 100% live progress tracking.

        Args:
            command: Command to execute
            working_dir: Working directory for command execution
            timeout: Optional timeout in seconds
            
        Returns:
            Completed process result
        """
        # Create the working directory if it doesn't exist
        os.makedirs(working_dir, exist_ok=True)
        
        # Check if live progress is enabled in config
        live_progress_enabled = config.get('live-progress', True)
        
        if live_progress_enabled:
            # Show command execution start with live progress
            user_display.status_info(f"🚀 Starting: {command[:80]}{'...' if len(command) > 80 else ''}")
            return await self._execute_command_with_live_tracking(command, working_dir, timeout)
        else:
            # Use basic execution without live tracking
            return await self._execute_command_basic(command, working_dir, timeout)
    
    async def _execute_command_with_live_tracking(self, command: str, working_dir: str, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """
        Execute command with real-time progress tracking and live status updates.
        
        Args:
            command: Command to execute
            working_dir: Working directory for command execution
            timeout: Optional timeout in seconds
            
        Returns:
            Completed process result
        """
        import time
        start_time = time.time()
        
        # Start the process
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir
        )
        
        # Show live process status
        user_display.status_info(f"⚡ Running PID {process.pid}: {command.split()[0]}")
        
        # Track process with live status updates
        stdout_chunks = []
        stderr_chunks = []
        last_status_time = start_time
        
        async def read_stream(stream, chunks_list, stream_name):
            """Read from stream and track activity"""
            nonlocal last_status_time  # Declare nonlocal at the beginning
            while True:
                try:
                    chunk = await stream.read(1024)  # Read in small chunks for responsiveness
                    if not chunk:
                        break
                    chunks_list.append(chunk)
                    
                    # Show activity indicator based on config interval (default 2 seconds)
                    current_time = time.time()
                    progress_interval = float(config.get('progress-update-interval', 2))
                    if current_time - last_status_time >= progress_interval:
                        elapsed = current_time - start_time
                        user_display.status_info(f"🔄 Active: {command.split()[0]} [{elapsed:.1f}s] - {stream_name} activity")
                        # Update last status time (shared across streams)
                        last_status_time = current_time
                        
                except Exception as e:
                    logger.debug(f"Stream reading error: {e}")
                    break
        
        # Read both stdout and stderr concurrently with live tracking
        try:
            if timeout:
                # Run with timeout
                await asyncio.wait_for(asyncio.gather(
                    read_stream(process.stdout, stdout_chunks, "stdout"),
                    read_stream(process.stderr, stderr_chunks, "stderr"),
                    process.wait()
                ), timeout=timeout)
            else:
                # Run without timeout
                await asyncio.gather(
                    read_stream(process.stdout, stdout_chunks, "stdout"),
                    read_stream(process.stderr, stderr_chunks, "stderr"),
                    process.wait()
                )
        except asyncio.TimeoutError:
            # Kill the process if it times out
            user_display.status_warning(f"⏰ Timeout after {timeout}s, killing: {command.split()[0]}")
            process.kill()
            await process.wait()
            raise Exception(f"Command timed out after {timeout} seconds: {command}")
        
        # Show completion status
        execution_time = time.time() - start_time
        if process.returncode == 0:
            user_display.status_info(f"✅ Completed: {command.split()[0]} [{execution_time:.1f}s] - Exit code 0")
        else:
            user_display.status_warning(f"❌ Failed: {command.split()[0]} [{execution_time:.1f}s] - Exit code {process.returncode}")
        
        # Combine output chunks
        stdout = b''.join(stdout_chunks)
        stderr = b''.join(stderr_chunks)
        
        # Create result object
        class AsyncResult:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout.decode('utf-8', errors='ignore') if stdout else ''
                self.stderr = stderr.decode('utf-8', errors='ignore') if stderr else ''
        
        return AsyncResult(process.returncode, stdout, stderr)
    
    async def _execute_command_basic(self, command: str, working_dir: str, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Execute command without progress tracking (fallback method)."""
        # Execute the command with timeout
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir
        )
        
        try:
            if timeout:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            else:
                stdout, stderr = await process.communicate()
        except asyncio.TimeoutError:
            # Kill the process if it times out
            process.kill()
            await process.wait()
            raise Exception(f"Command timed out after {timeout} seconds: {command}")
        
        # Create a result object similar to subprocess.CompletedProcess
        class AsyncResult:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout.decode('utf-8', errors='ignore') if stdout else ''
                self.stderr = stderr.decode('utf-8', errors='ignore') if stderr else ''
        
        return AsyncResult(process.returncode, stdout, stderr)
    
    
    def _parse_service_from_match(self, match: Union[str, tuple], pattern_config: Dict[str, Any]) -> Optional[Any]:
        """
        Parse service information from pattern match.
        
        Args:
            match: Regex match result
            pattern_config: Pattern configuration
            
        Returns:
            Service object or None
        """
        # This would create Service objects from pattern matches
        # For now, return a simple representation
        return {
            'match': match,
            'type': 'service_discovery',
            'pattern': pattern_config.get('name', 'unknown')
        }
    
    def _parse_finding_from_match(self, matches: List[Any], pattern_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse findings from pattern matches.
        
        Args:
            matches: List of regex matches
            pattern_config: Pattern configuration
            
        Returns:
            List of finding dictionaries
        """
        findings = []
        
        for match in matches:
            finding = {
                'type': pattern_config.get('type', 'info'),
                'description': pattern_config.get('description', ''),
                'match': str(match),
                'pattern_name': pattern_config.get('name', 'unknown'),
                'severity': pattern_config.get('severity', 'low')
            }
            findings.append(finding)
        
        return findings
    
    def _resolve_wordlists(self, plugin: YamlPlugin, service) -> Dict[str, str]:
        """
        Resolve wordlist paths for a plugin based on auto-selection or custom paths.
        
        Args:
            plugin: YAML plugin that may have wordlist options
            service: Service object for context
            
        Returns:
            Dictionary of resolved wordlist variables for command substitution
        """
        wordlist_vars = {}
        
        # Check if plugin has wordlist options
        wordlist_option = None
        for option in plugin.options:
            if option.name == "wordlist":
                wordlist_option = option
                break
        
        if not wordlist_option:
            # No wordlist option defined, return empty
            return wordlist_vars
        
        # Get the wordlist value from plugin configuration (default to 'auto' if not specified)
        # In the future, this could be overridden by user configuration or template options
        wordlist_value = getattr(wordlist_option, 'default', 'auto')
        
        if wordlist_value == "auto":
            # Use intelligent wordlist selection
            resolved_path = self._auto_select_wordlist(service)
            if resolved_path:
                wordlist_vars['resolved_wordlist'] = resolved_path
                wordlist_vars['wordlist'] = resolved_path  # Backward compatibility
        else:
            # Custom wordlist path specified
            resolved_path = self._validate_custom_wordlist(wordlist_value)
            if resolved_path:
                wordlist_vars['resolved_wordlist'] = resolved_path
                wordlist_vars['wordlist'] = resolved_path  # Backward compatibility
            else:
                # Fail fast on missing custom wordlist
                raise Exception(f"Custom wordlist not found or invalid: {wordlist_value}")
        
        return wordlist_vars
    
    def _auto_select_wordlist(self, service) -> Optional[str]:
        """
        Auto-select appropriate wordlist using Smart Wordlist Selector.
        
        Args:
            service: Service object for context
            
        Returns:
            Path to selected wordlist or None
        """
        try:
            from ipcrawler.smart_wordlist_selector import SmartWordlistSelector
            import os
            
            # Direct SecLists detection without obsolete wordlist manager
            seclists_search_paths = [
                '/usr/share/seclists',
                '/usr/share/SecLists', 
                '/opt/SecLists',
                '/opt/seclists',
                '/usr/share/wordlists/seclists',
                '/home/kali/SecLists',
                os.path.expanduser('~/tools/wordlists/seclists'),
                os.path.expanduser('~/tools/wordlists/SecLists'),
                os.path.expanduser('~/SecLists'),
                os.path.expanduser('~/tools/SecLists')
            ]
            
            seclists_path = None
            for path in seclists_search_paths:
                if os.path.isdir(path):
                    # Verify it's actually SecLists by checking for key files
                    test_file = os.path.join(path, 'Usernames/top-usernames-shortlist.txt')
                    if os.path.exists(test_file):
                        seclists_path = path
                        break
            
            if not seclists_path:
                logger.warning("SecLists not found - auto wordlist selection unavailable")
                return None
            
            # Initialize smart selector
            selector = SmartWordlistSelector(seclists_path)
            
            # Determine category based on service type
            if 'http' in service.name.lower():
                category = 'directories'  # Most common web enumeration
            else:
                category = 'generic'
            
            # For now, use empty technology set - in future this could be enhanced
            # to detect technologies from previous scan results
            detected_technologies = set()
            
            # Select wordlist
            selected_path = selector.select_wordlist(category, detected_technologies)
            
            if selected_path and os.path.exists(selected_path):
                logger.debug(f"Auto-selected wordlist: {selected_path}")
                return selected_path
            else:
                logger.warning(f"Auto-selected wordlist not found: {selected_path}")
                return None
                
        except Exception as e:
            logger.error(f"Auto wordlist selection failed: {e}")
            return None
    
    def _validate_custom_wordlist(self, wordlist_path: str) -> Optional[str]:
        """
        Validate custom wordlist path.
        
        Args:
            wordlist_path: Path to custom wordlist file
            
        Returns:
            Absolute path to wordlist if valid, None otherwise
        """
        import os
        
        # Convert to absolute path
        if not os.path.isabs(wordlist_path):
            # Relative to current working directory
            wordlist_path = os.path.abspath(wordlist_path)
        
        # Check if file exists and is readable
        if os.path.exists(wordlist_path) and os.path.isfile(wordlist_path):
            try:
                with open(wordlist_path, 'r') as f:
                    # Just check if we can read the first line
                    f.readline()
                logger.debug(f"Custom wordlist validated: {wordlist_path}")
                return wordlist_path
            except Exception as e:
                logger.error(f"Custom wordlist not readable: {wordlist_path} - {e}")
                return None
        else:
            logger.error(f"Custom wordlist not found: {wordlist_path}")
            return None
    
    def _get_wordlist_path(self, wordlist_type: str) -> str:
        """
        Get path to a specific wordlist type.
        
        Args:
            wordlist_type: Type of wordlist (users, passwords, common_users, etc.)
            
        Returns:
            Path to wordlist file or empty string if not found
        """
        # Common wordlist paths based on SecLists structure
        wordlist_paths = {
            'users': [
                '/usr/share/seclists/Usernames/top-usernames-shortlist.txt',
                '/usr/share/SecLists/Usernames/top-usernames-shortlist.txt',
                '/opt/SecLists/Usernames/top-usernames-shortlist.txt',
            ],
            'usernames': [
                '/usr/share/seclists/Usernames/Names/names.txt',
                '/usr/share/SecLists/Usernames/Names/names.txt',
                '/opt/SecLists/Usernames/Names/names.txt',
            ],
            'passwords': [
                '/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt',
                '/usr/share/SecLists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt',
                '/opt/SecLists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt',
            ],
            'common_users': [
                '/usr/share/seclists/Usernames/top-usernames-shortlist.txt',
                '/usr/share/SecLists/Usernames/top-usernames-shortlist.txt',
                '/opt/SecLists/Usernames/top-usernames-shortlist.txt',
            ],
        }
        
        if wordlist_type in wordlist_paths:
            for path in wordlist_paths[wordlist_type]:
                if os.path.exists(path):
                    return path
        
        # Return empty string if not found
        return ''
    
    def _get_wordlist_name(self, wordlist_path: Optional[str]) -> str:
        """
        Get the name of a wordlist from its path.
        
        Args:
            wordlist_path: Path to wordlist file
            
        Returns:
            Name of wordlist or empty string
        """
        if not wordlist_path:
            return ''
        
        # Extract filename without extension
        import os
        filename = os.path.basename(wordlist_path)
        name = os.path.splitext(filename)[0]
        return name
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = self.execution_stats.copy()
        stats['plugins_executed'] = list(stats['plugins_executed'])
        return stats 

    def _apply_sudo_if_required(self, command: str, plugin: YamlPlugin) -> str:
        """
        Apply sudo if required and enabled based on plugin permissions and config.
        
        Args:
            command: Command to execute
            plugin: YAML plugin
            
        Returns:
            Command with sudo prepended if required
        """
        # Check if sudo is enabled in global configuration
        sudo_enabled = config.get('enable_sudo', False)
        
        if not sudo_enabled:
            return command
        
        # Check if plugin requires root permissions
        sudo_required = self._check_sudo_required(command, plugin)
        
        if sudo_required:
            # Prepend sudo without timeout (some systems don't allow timeout setting)
            return f"sudo {command}"
        else:
            return command
    
    def _check_sudo_required(self, command: str, plugin: YamlPlugin) -> bool:
        """
        Check if a command requires sudo based on plugin permissions and command content.
        
        Args:
            command: Command to execute
            plugin: YAML plugin
            
        Returns:
            True if sudo is required
        """
        # Check plugin permissions requirements
        if hasattr(plugin, 'requirements') and plugin.requirements:
            if hasattr(plugin.requirements, 'permissions') and plugin.requirements.permissions:
                for perm in plugin.requirements.permissions:
                    if hasattr(perm, 'type') and perm.type == 'root':
                        return True
        
        # Check for common privileged command patterns
        privileged_patterns = [
            r'\bnmap\s+.*-sU',          # UDP scans
            r'\bnmap\s+.*-A\b',         # Aggressive scans with OS detection
            r'\bnmap\s+.*--osscan-guess', # OS detection
            r'\bnmap\s+.*-sS\b',        # SYN stealth scans
            r'\bnmap\s+.*-sV.*-A',      # Service detection with aggressive
        ]
        
        for pattern in privileged_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        
        return False
    