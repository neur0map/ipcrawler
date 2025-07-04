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

from ipcrawler.config import config
from ipcrawler.yaml_plugins import YamlPluginLoader, YamlPlugin, PluginType
from ipcrawler.plugin_debugger import PluginDebugger

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
                
                # Substitute variables in command
                substituted_command = self._substitute_variables(command, env_vars)
                commands_executed.append(substituted_command)
                
                # Execute command
                try:
                    result = await self._execute_command(substituted_command, target.scandir)
                    all_output += result.stdout + result.stderr
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
                
                # For port scan plugins, extract services from matches
                if plugin.metadata.type == PluginType.PORTSCAN:
                    # Note: service detection logic would need to be adapted for YAML plugins
                    if matches:
                        for match in matches:
                            # Parse service information from match - simplified for now
                            service_info = {'match': match, 'pattern': pattern_name}
                            services_found.append(service_info)
            
            execution_time = time.time() - start_time
            
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
                
                # Substitute variables in command
                substituted_command = self._substitute_variables(command, env_vars)
                commands_executed.append(substituted_command)
                
                # Execute command
                try:
                    result = await self._execute_command(substituted_command, scandir)
                    all_output += result.stdout + result.stderr
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
        return {
            'address': target.address,
            'target': target.address,
            'ip': getattr(target, 'ip', target.address),
            'scandir': target.scandir,
            'ipversion': getattr(target, 'ipversion', 'IPv4'),
            'plugin_slug': plugin.metadata.name,
            'plugin_name': plugin.metadata.name,
            'ports_tcp': config.get('ports', {}).get('tcp', ''),
            'ports_udp': config.get('ports', {}).get('udp', ''),
        }
    
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
        
        # Add service-specific variables
        env_vars.update({
            'port': str(service.port),
            'protocol': service.protocol,
            'service': service.name,
            'service_name': service.name,
            'secure': 'true' if service.secure else 'false',
            'http_scheme': 'https' if ('https' in service.name or service.secure) else 'http',
            'url': f"{'https' if ('https' in service.name or service.secure) else 'http'}://{service.target.address}:{service.port}",
        })
        
        return env_vars
    
    def _substitute_variables(self, command: str, env_vars: Dict[str, str]) -> str:
        """
        Substitute variables in command string.
        
        Args:
            command: Command template with variables
            env_vars: Environment variables for substitution
            
        Returns:
            Command with variables substituted
        """
        # Replace {variable} patterns
        for var_name, var_value in env_vars.items():
            command = command.replace(f'{{{var_name}}}', str(var_value))
        
        return command
    
    async def _execute_command(self, command: str, working_dir: str) -> subprocess.CompletedProcess:
        """
        Execute a command asynchronously.
        
        Args:
            command: Command to execute
            working_dir: Working directory for command execution
            
        Returns:
            Completed process result
        """
        # Create the working directory if it doesn't exist
        os.makedirs(working_dir, exist_ok=True)
        
        # Execute the command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir
        )
        
        stdout, stderr = await process.communicate()
        
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
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = self.execution_stats.copy()
        stats['plugins_executed'] = list(stats['plugins_executed'])
        return stats 