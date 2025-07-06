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
                
                # Substitute variables in command
                substituted_command = self._substitute_variables(command, env_vars)
                commands_executed.append(substituted_command)
                
                # Execute command with timeout from YAML
                try:
                    command_timeout = getattr(command_config, 'timeout', None)
                    result = await self._execute_command(substituted_command, target.scandir, timeout=command_timeout)
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
                
                # Substitute variables in command
                substituted_command = self._substitute_variables(command, env_vars)
                commands_executed.append(substituted_command)
                
                # Execute command with timeout from YAML
                try:
                    command_timeout = getattr(command_config, 'timeout', None)
                    result = await self._execute_command(substituted_command, scandir, timeout=command_timeout)
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
        return {
            'address': target.address,
            'target': target.address,
            'ip': getattr(target, 'ip', target.address),
            'scandir': target.scandir,
            'ipversion': getattr(target, 'ipversion', 'IPv4'),
            'plugin_slug': plugin.metadata.name,
            'plugin_name': plugin.metadata.name,
            'ports_tcp': (config.get('ports') or {}).get('tcp', ''),
            'ports_udp': (config.get('ports') or {}).get('udp', ''),
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
        
        # Add wordlist resolution logic
        resolved_wordlists = self._resolve_wordlists(plugin, service)
        env_vars.update(resolved_wordlists)
        
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
    
    async def _execute_command(self, command: str, working_dir: str, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """
        Execute a command asynchronously with optional timeout.
        
        Args:
            command: Command to execute
            working_dir: Working directory for command execution
            timeout: Optional timeout in seconds
            
        Returns:
            Completed process result
        """
        # Create the working directory if it doesn't exist
        os.makedirs(working_dir, exist_ok=True)
        
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
            from ipcrawler.wordlists import init_wordlist_manager
            from ipcrawler.config import config
            
            # Initialize wordlist manager to detect SecLists
            wordlist_manager = init_wordlist_manager(config['config_dir'])
            seclists_path = wordlist_manager.detect_seclists_installation()
            
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
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = self.execution_stats.copy()
        stats['plugins_executed'] = list(stats['plugins_executed'])
        return stats 