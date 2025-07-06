"""
YAML Plugin Integration for IPCrawler

This module provides integration between YAML plugins and the main IPCrawler execution loop,
allowing YAML and Python plugins to work together seamlessly.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

from ipcrawler.config import config
from ipcrawler.yaml_plugins import YamlPluginLoader, PluginType
from ipcrawler.yaml_executor import YamlPluginExecutor  
from ipcrawler.plugin_debugger import PluginDebugger

logger = logging.getLogger(__name__)


class YamlPluginManager:
    """
    Manages YAML plugin integration with the main IPCrawler system.
    
    This manager:
    - Loads YAML plugins on startup
    - Integrates YAML plugins into the main execution loop
    - Provides debugging and performance monitoring
    - Ensures compatibility with existing Python plugins
    """
    
    def __init__(self):
        """Initialize YAML plugin manager."""
        self.loader: Optional[YamlPluginLoader] = None
        self.executor: Optional[YamlPluginExecutor] = None
        self.debugger: Optional[PluginDebugger] = None
        self.initialized = False
        self.performance_stats = {
            'initialization_time': 0,
            'total_plugins_loaded': 0,
            'execution_errors': 0,
            'successful_executions': 0
        }
    
    def initialize(self) -> bool:
        """
        Initialize YAML plugin system.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self.initialized:
            return True
        
        if not config.get('enable_yaml_plugins', False):
            logger.debug("YAML plugins disabled in configuration")
            return False
        
        start_time = time.time()
        
        try:
            # Initialize YAML plugin loader with template directory
            template_dir = config.get('template_dir')
            if not template_dir or not Path(template_dir).exists():
                logger.warning(f"Template directory not found: {template_dir}")
                return False
            
            logger.debug(f"Loading YAML plugins from: {template_dir}")
            self.loader = YamlPluginLoader([template_dir])
            
            # Load YAML plugins
            load_result = self.loader.load_plugins()
            if not load_result:
                logger.error(f"Failed to load YAML plugins: No plugins loaded")
                return False
            
            # Check for validation errors in strict mode
            if self.loader.validation_errors:
                # In template mode, validation errors should cause failure
                if config.get('template_dir'):
                    error_count = len(self.loader.validation_errors)
                    logger.error(f"Template validation failed: {error_count} plugins have validation errors")
                    for plugin_file, errors in self.loader.validation_errors.items():
                        logger.error(f"  {plugin_file}: {errors}")
                    return False
                else:
                    # In legacy mode, just log warnings
                    logger.warning(f"YAML plugin validation warnings: {len(self.loader.validation_errors)} plugins have issues")
            
            # Initialize debugger if debug mode is enabled
            if config.get('debug_yaml_plugins', False):
                self.debugger = PluginDebugger()
                logger.info("YAML plugin debugging enabled")
            
            # Initialize executor
            self.executor = YamlPluginExecutor(self.loader, self.debugger)
            
            # Update performance stats
            self.performance_stats['initialization_time'] = time.time() - start_time
            self.performance_stats['total_plugins_loaded'] = len(self.loader.plugins)
            
            self.initialized = True
            
            logger.info(f"YAML plugin system initialized - loaded {len(self.loader.plugins)} plugins in {self.performance_stats['initialization_time']:.2f}s")
            
            # Log available plugins by type
            if config.get('verbose', 0) >= 1:
                self._log_loaded_plugins()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize YAML plugin system: {e}")
            return False
    
    def _log_loaded_plugins(self):
        """Log details of loaded YAML plugins."""
        if not self.loader:
            return
        
        plugin_counts = {}
        for plugin in self.loader.plugins.values():
            plugin_type = plugin.metadata.type.value
            if plugin_type not in plugin_counts:
                plugin_counts[plugin_type] = 0
            plugin_counts[plugin_type] += 1
        
        logger.info("YAML Plugin Summary:")
        for plugin_type, count in plugin_counts.items():
            logger.info(f"  • {plugin_type}: {count} plugins")
        
        if config.get('debug_yaml_plugins', False):
            logger.debug("YAML Plugin Details:")
            for plugin in self.loader.plugins.values():
                logger.debug(f"  • {plugin.metadata.slug} ({plugin.metadata.type.value}): {plugin.metadata.description}")
    
    def get_yaml_port_scan_plugins(self, target) -> List[Any]:
        """
        Get YAML port scan plugins that should run for a target.
        
        Args:
            target: Target object
            
        Returns:
            List of plugins that should run for the target
        """
        if not self.initialized or not self.executor:
            return []
        
        return self.executor.get_yaml_plugins_for_target(target, PluginType.PORTSCAN)
    
    def get_yaml_service_scan_plugins(self, service) -> List[Any]:
        """
        Get YAML service scan plugins that should run for a service.
        
        Args:
            service: Service object
            
        Returns:
            List of plugins that should run for the service
        """
        if not self.initialized or not self.executor:
            return []
        
        return self.executor.get_yaml_plugins_for_service(service, PluginType.SERVICESCAN)
    
    async def execute_yaml_port_scan(self, plugin, target) -> Dict[str, Any]:
        """
        Execute a YAML port scan plugin.
        
        Args:
            plugin: YAML plugin to execute
            target: Target object
            
        Returns:
            Execution result
        """
        if not self.initialized or not self.executor:
            return {'type': 'port', 'result': [], 'success': False, 'error': 'YAML system not initialized'}
        
        try:
            start_time = time.time()
            
            if self.debugger:
                self.debugger.log_plugin_execution_start(plugin.metadata.slug, target.address)
            
            result = await self.executor.execute_yaml_plugin_for_target(plugin, target)
            
            execution_time = time.time() - start_time
            success = result.get('success', False)
            
            if self.debugger:
                self.debugger.log_plugin_execution_end(plugin.metadata.slug, target.address, success, execution_time)
            
            # Update performance stats
            if success:
                self.performance_stats['successful_executions'] += 1
            else:
                self.performance_stats['execution_errors'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing YAML port scan plugin {plugin.metadata.slug}: {e}")
            
            if self.debugger:
                self.debugger.log_plugin_error(plugin.metadata.slug, target.address, str(e))
            
            self.performance_stats['execution_errors'] += 1
            
            return {
                'type': 'port',
                'result': [],
                'success': False,
                'error': str(e)
            }
    
    async def execute_yaml_service_scan(self, plugin, service) -> Dict[str, Any]:
        """
        Execute a YAML service scan plugin.
        
        Args:
            plugin: YAML plugin to execute
            service: Service object
            
        Returns:
            Execution result
        """
        if not self.initialized or not self.executor:
            return {'type': 'service', 'result': None, 'success': False, 'error': 'YAML system not initialized'}
        
        try:
            start_time = time.time()
            target_service = f"{service.target.address}:{service.port}"
            
            if self.debugger:
                self.debugger.log_plugin_execution_start(plugin.metadata.slug, target_service)
            
            result = await self.executor.execute_yaml_plugin_for_service(plugin, service)
            
            execution_time = time.time() - start_time
            success = result.get('success', False)
            
            if self.debugger:
                self.debugger.log_plugin_execution_end(plugin.metadata.slug, target_service, success, execution_time)
            
            # Update performance stats
            if success:
                self.performance_stats['successful_executions'] += 1
            else:
                self.performance_stats['execution_errors'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing YAML service scan plugin {plugin.metadata.slug}: {e}")
            
            if self.debugger:
                self.debugger.log_plugin_error(plugin.metadata.slug, f"{service.target.address}:{service.port}", str(e))
            
            self.performance_stats['execution_errors'] += 1
            
            return {
                'type': 'service',
                'result': None,
                'success': False,
                'error': str(e)
            }
    
    def should_use_yaml_plugins_only(self) -> bool:
        """
        Check if only YAML plugins should be used (disabling Python plugins).
        
        Returns:
            True if only YAML plugins should be used
        """
        return config.get('yaml_plugins_only', False) and self.initialized
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for YAML plugin system."""
        stats = self.performance_stats.copy()
        
        if self.executor:
            stats.update(self.executor.get_execution_stats())
        
        if self.debugger:
            stats.update(self.debugger.get_session_stats())
        
        return stats
    
    def generate_debug_report(self, target_address: Optional[str] = None) -> Optional[str]:
        """
        Generate debug report if debugger is enabled.
        
        Args:
            target_address: Optional target to filter by
            
        Returns:
            Debug report string or None if debugger not enabled
        """
        if not self.debugger:
            return None
        
        return self.debugger.generate_debug_report(target_address)
    
    def save_debug_report(self, filepath: str, target_address: Optional[str] = None) -> bool:
        """
        Save debug report to file if debugger is enabled.
        
        Args:
            filepath: Path to save report
            target_address: Optional target to filter by
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not self.debugger:
            return False
        
        try:
            self.debugger.save_debug_report(filepath, target_address)
            return True
        except Exception as e:
            logger.error(f"Failed to save debug report: {e}")
            return False


# Global instance for integration with main execution loop
yaml_plugin_manager = YamlPluginManager()


def initialize_yaml_plugins() -> bool:
    """
    Initialize YAML plugin system - called from main execution loop.
    
    Returns:
        True if initialization successful
    """
    return yaml_plugin_manager.initialize()


def get_yaml_port_scan_tasks(target) -> List[Any]:
    """
    Get YAML port scan tasks for a target - integrates with main port scan loop.
    
    Args:
        target: Target object
        
    Returns:
        List of asyncio tasks for YAML port scan plugins
    """
    if not yaml_plugin_manager.initialized:
        return []
    
    yaml_plugins = yaml_plugin_manager.get_yaml_port_scan_plugins(target)
    tasks = []
    
    for plugin in yaml_plugins:
        # Create async task for each YAML plugin
        task = asyncio.create_task(yaml_plugin_manager.execute_yaml_port_scan(plugin, target))
        
        # Add plugin metadata to task for compatibility with existing system
        task.plugin_priority = getattr(plugin.metadata, 'priority', 5)  # Default priority
        task.plugin_name = plugin.metadata.name
        task.plugin_slug = plugin.metadata.slug
        task.plugin_type = 'yaml_portscan'
        
        tasks.append(task)
    
    return tasks


def get_yaml_service_scan_tasks(service) -> List[Any]:
    """
    Get YAML service scan tasks for a service - integrates with main service scan loop.
    
    Args:
        service: Service object
        
    Returns:
        List of asyncio tasks for YAML service scan plugins
    """
    if not yaml_plugin_manager.initialized:
        return []
    
    yaml_plugins = yaml_plugin_manager.get_yaml_service_scan_plugins(service)
    tasks = []
    
    for plugin in yaml_plugins:
        # Create async task for each YAML plugin
        task = asyncio.create_task(yaml_plugin_manager.execute_yaml_service_scan(plugin, service))
        
        # Add plugin metadata to task for compatibility with existing system
        task.plugin_priority = getattr(plugin.metadata, 'priority', 5)  # Default priority
        task.plugin_name = plugin.metadata.name
        task.plugin_slug = plugin.metadata.slug
        task.plugin_type = 'yaml_servicescan'
        
        tasks.append(task)
    
    return tasks


def should_skip_python_plugins() -> bool:
    """
    Check if Python plugins should be skipped (when yaml_plugins_only is enabled).
    
    Returns:
        True if Python plugins should be skipped
    """
    return yaml_plugin_manager.should_use_yaml_plugins_only()


def get_yaml_plugin_performance_stats() -> Dict[str, Any]:
    """Get YAML plugin performance statistics."""
    return yaml_plugin_manager.get_performance_stats()


def generate_yaml_debug_report(target_address: Optional[str] = None) -> Optional[str]:
    """Generate YAML plugin debug report."""
    return yaml_plugin_manager.generate_debug_report(target_address)


def save_yaml_debug_report(filepath: str, target_address: Optional[str] = None) -> bool:
    """Save YAML plugin debug report to file."""
    return yaml_plugin_manager.save_debug_report(filepath, target_address) 