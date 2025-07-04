"""
YAML Plugin System for IPCrawler

This module provides functionality to load, validate, and manage YAML-based plugins
that can replace the current Python plugin system with enhanced debugging capabilities.
"""

import os
import re
import yaml
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, ValidationError, Field
from enum import Enum

import logging
from ipcrawler.config import config

# Set up basic logging for the YAML plugin system
logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """Plugin types supported by the system"""
    PORTSCAN = "portscan"
    SERVICESCAN = "servicescan"
    BRUTEFORCE = "bruteforce"
    REPORTING = "reporting"


class Severity(str, Enum):
    """Finding severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptionType(str, Enum):
    """Plugin option types"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CHOICE = "choice"


@dataclass
class YamlPluginMetadata:
    """Plugin metadata information"""
    name: str
    description: str
    version: str = "1.0"
    author: str = ""
    priority: int = 50
    type: PluginType = PluginType.SERVICESCAN
    
    @property
    def slug(self) -> str:
        """Generate a slug from the plugin name"""
        import re
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '-', self.name.lower())
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')


@dataclass
class YamlPluginConditions:
    """Plugin execution conditions"""
    services_include: List[str] = field(default_factory=list)
    services_exclude: List[str] = field(default_factory=list)
    ports_include: List[int] = field(default_factory=list)
    ports_exclude: List[int] = field(default_factory=list)
    port_ranges: List[str] = field(default_factory=list)
    protocols_include: List[str] = field(default_factory=list)
    protocols_exclude: List[str] = field(default_factory=list)
    ssl_required: Optional[bool] = None
    ip_version: List[str] = field(default_factory=list)
    has_hostname: Optional[bool] = None
    custom_condition: Optional[str] = None
    max_instances: Optional[int] = None
    run_once: bool = False
    timeout: Optional[int] = None


@dataclass
class YamlPluginOption:
    """Plugin configuration option"""
    name: str
    type: OptionType
    default: Any = None
    help: str = ""
    choices: List[str] = field(default_factory=list)
    required: bool = False


@dataclass
class YamlPluginCommand:
    """Plugin command definition"""
    name: str
    command: str
    condition: Optional[str] = None
    timeout: Optional[int] = None
    background: bool = False
    output_file: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    working_directory: Optional[str] = None


@dataclass
class YamlPluginManualCommand:
    """Manual command for user reference"""
    description: str
    command: str
    condition: Optional[str] = None


@dataclass
class YamlPluginPattern:
    """Output pattern for finding extraction"""
    pattern: str
    description: str
    severity: Severity = Severity.INFO
    category: str = "general"
    condition: Optional[str] = None


@dataclass
class YamlPluginServiceDetection:
    """Service detection pattern"""
    pattern: str
    service_name: str
    port_override: Optional[int] = None


@dataclass
class YamlPluginTechnologyDetection:
    """Technology detection pattern"""
    pattern: str
    technology: str
    version_group: Optional[int] = None


@dataclass
class YamlPluginRequirement:
    """Plugin requirement (tool, file, permission)"""
    name: str
    check_command: Optional[str] = None
    install_hint: Optional[str] = None
    path: Optional[str] = None
    description: str = ""
    type: Optional[str] = None


@dataclass
class YamlPluginDebug:
    """Plugin debugging configuration"""
    log_level: str = "info"
    trace_decisions: bool = False
    show_command_output: bool = False


@dataclass
class YamlPlugin:
    """Complete YAML plugin definition"""
    metadata: YamlPluginMetadata
    conditions: YamlPluginConditions = field(default_factory=YamlPluginConditions)
    options: List[YamlPluginOption] = field(default_factory=list)
    commands: List[YamlPluginCommand] = field(default_factory=list)
    manual_commands: List[YamlPluginManualCommand] = field(default_factory=list)
    patterns: List[YamlPluginPattern] = field(default_factory=list)
    service_detection: List[YamlPluginServiceDetection] = field(default_factory=list)
    technology_detection: List[YamlPluginTechnologyDetection] = field(default_factory=list)
    requirements: List[YamlPluginRequirement] = field(default_factory=list)
    debug: YamlPluginDebug = field(default_factory=YamlPluginDebug)
    
    # Runtime data
    plugin_file: Optional[Path] = None
    validation_errors: List[str] = field(default_factory=list)


class YamlPluginLoader:
    """Loads and manages YAML plugins"""
    
    def __init__(self, plugin_directories: List[str] = None):
        self.plugin_directories = plugin_directories or [
            "ipcrawler/yaml-plugins"
        ]
        self.plugins: Dict[str, YamlPlugin] = {}
        self.validation_errors: Dict[str, List[str]] = {}
    
    def discover_plugins(self) -> List[Path]:
        """Discover all YAML plugin files"""
        plugin_files = []
        
        for directory in self.plugin_directories:
            plugin_dir = Path(directory)
            if not plugin_dir.exists():
                logger.warning(f"Plugin directory does not exist: {directory}")
                continue
            
            # Ensure we only search within our plugin directories
            if not str(plugin_dir).endswith(('yaml-plugins', 'plugins')):
                logger.warning(f"Skipping non-plugin directory: {directory}")
                continue
            
            try:
                # Use safer directory traversal to avoid macOS filesystem issues
                # Limit depth to avoid system directory issues
                for ext in ['*.yaml', '*.yml']:
                    # First try non-recursive search
                    for file_path in plugin_dir.glob(ext):
                        if self._is_likely_plugin_file(file_path):
                            plugin_files.append(file_path)
                    
                    # Then search one level deep
                    for subdir in plugin_dir.glob('*/'):
                        if subdir.is_dir() and not subdir.name.startswith('.'):
                            for file_path in subdir.glob(ext):
                                if self._is_likely_plugin_file(file_path):
                                    plugin_files.append(file_path)
                            
                            # Search two levels deep
                            for sub_subdir in subdir.glob('*/'):
                                if sub_subdir.is_dir() and not sub_subdir.name.startswith('.'):
                                    for file_path in sub_subdir.glob(ext):
                                        if self._is_likely_plugin_file(file_path):
                                            plugin_files.append(file_path)
                                    
            except (OSError, PermissionError) as e:
                logger.warning(f"Error accessing directory {directory}: {e}")
                continue
        
        logger.info(f"Discovered {len(plugin_files)} YAML plugin files")
        return plugin_files
    
    def _is_likely_plugin_file(self, file_path: Path) -> bool:
        """Check if a YAML file is likely to be a plugin file"""
        # Skip common non-plugin files
        excluded_names = ['compose.yml', 'docker-compose.yml', '.github', 'config.yml', 'ci.yml']
        if file_path.name in excluded_names:
            return False
        
        # Skip files in excluded directories
        excluded_dirs = {'.git', '.github', 'node_modules', '__pycache__'}
        if any(part in excluded_dirs for part in file_path.parts):
            return False
        
        # Skip files outside our plugin directory structure
        path_str = str(file_path)
        if '/opt/' in path_str or '/usr/' in path_str or '/var/' in path_str:
            return False
        
        return True
    
    def validate_plugin_data(self, plugin_data: Dict[str, Any], plugin_file: Path) -> List[str]:
        """Validate plugin data structure"""
        errors = []
        
        # Check required top-level sections
        if 'metadata' not in plugin_data:
            errors.append("Missing required 'metadata' section")
        else:
            metadata = plugin_data['metadata']
            if 'name' not in metadata:
                errors.append("Missing required 'metadata.name'")
            if 'description' not in metadata:
                errors.append("Missing required 'metadata.description'")
        
        # Validate execution section if present
        if 'execution' in plugin_data:
            execution = plugin_data['execution']
            if 'commands' in execution:
                if not isinstance(execution['commands'], list):
                    errors.append("'execution.commands' must be a list")
                else:
                    for i, cmd in enumerate(execution['commands']):
                        if not isinstance(cmd, dict):
                            errors.append(f"Command {i} must be a dictionary")
                        elif 'command' not in cmd:
                            errors.append(f"Command {i} missing required 'command' field")
        
        # Validate condition patterns
        if 'conditions' in plugin_data:
            conditions = plugin_data['conditions']
            if 'services' in conditions:
                services = conditions['services']
                if 'include' in services:
                    for pattern in services['include']:
                        try:
                            re.compile(pattern)
                        except re.error as e:
                            errors.append(f"Invalid regex in services.include: {pattern} - {e}")
        
        return errors
    
    def parse_plugin(self, plugin_file: Path) -> Optional[YamlPlugin]:
        """Parse a single YAML plugin file"""
        try:
            with open(plugin_file, 'r', encoding='utf-8') as f:
                plugin_data = yaml.safe_load(f)
            
            if not plugin_data:
                logger.warning(f"Empty plugin file: {plugin_file}")
                return None
            
            # Validate plugin structure
            validation_errors = self.validate_plugin_data(plugin_data, plugin_file)
            if validation_errors:
                self.validation_errors[str(plugin_file)] = validation_errors
                logger.error(f"Validation errors in {plugin_file}: {validation_errors}")
                return None
            
            # Parse metadata
            metadata_data = plugin_data.get('metadata', {})
            metadata = YamlPluginMetadata(
                name=metadata_data['name'],
                description=metadata_data['description'],
                version=metadata_data.get('version', '1.0'),
                author=metadata_data.get('author', ''),
                priority=metadata_data.get('priority', 50),
                type=PluginType(metadata_data.get('type', 'servicescan'))
            )
            
            # Parse conditions
            conditions_data = plugin_data.get('conditions', {})
            conditions = YamlPluginConditions(
                services_include=conditions_data.get('services', {}).get('include', []),
                services_exclude=conditions_data.get('services', {}).get('exclude', []),
                ports_include=conditions_data.get('ports', {}).get('include', []),
                ports_exclude=conditions_data.get('ports', {}).get('exclude', []),
                port_ranges=conditions_data.get('ports', {}).get('ranges', []),
                protocols_include=conditions_data.get('protocols', {}).get('include', []),
                protocols_exclude=conditions_data.get('protocols', {}).get('exclude', []),
                ssl_required=conditions_data.get('when', {}).get('ssl_required'),
                ip_version=conditions_data.get('when', {}).get('ip_version', []),
                has_hostname=conditions_data.get('when', {}).get('has_hostname'),
                custom_condition=conditions_data.get('when', {}).get('custom_condition'),
                max_instances=conditions_data.get('targets', {}).get('max_instances'),
                run_once=conditions_data.get('targets', {}).get('run_once', False),
                timeout=conditions_data.get('targets', {}).get('timeout')
            )
            
            # Parse options
            options = []
            for opt_data in plugin_data.get('options', []):
                option = YamlPluginOption(
                    name=opt_data['name'],
                    type=OptionType(opt_data['type']),
                    default=opt_data.get('default'),
                    help=opt_data.get('help', ''),
                    choices=opt_data.get('choices', []),
                    required=opt_data.get('required', False)
                )
                options.append(option)
            
            # Parse commands
            commands = []
            execution_data = plugin_data.get('execution', {})
            for cmd_data in execution_data.get('commands', []):
                command = YamlPluginCommand(
                    name=cmd_data.get('name', 'default'),
                    command=cmd_data['command'],
                    condition=cmd_data.get('condition'),
                    timeout=cmd_data.get('timeout'),
                    background=cmd_data.get('background', False),
                    output_file=cmd_data.get('output_file'),
                    environment=cmd_data.get('environment', {}),
                    working_directory=cmd_data.get('working_directory')
                )
                commands.append(command)
            
            # Parse manual commands
            manual_commands = []
            for manual_data in execution_data.get('manual_commands', []):
                manual_cmd = YamlPluginManualCommand(
                    description=manual_data['description'],
                    command=manual_data['command'],
                    condition=manual_data.get('condition')
                )
                manual_commands.append(manual_cmd)
            
            # Parse output patterns
            patterns = []
            output_data = plugin_data.get('output', {})
            for pattern_data in output_data.get('patterns', []):
                pattern = YamlPluginPattern(
                    pattern=pattern_data['pattern'],
                    description=pattern_data['description'],
                    severity=Severity(pattern_data.get('severity', 'info')),
                    category=pattern_data.get('category', 'general'),
                    condition=pattern_data.get('condition')
                )
                patterns.append(pattern)
            
            # Parse service detection
            service_detection = []
            for sd_data in output_data.get('service_detection', []):
                service_det = YamlPluginServiceDetection(
                    pattern=sd_data['pattern'],
                    service_name=sd_data['service_name'],
                    port_override=sd_data.get('port_override')
                )
                service_detection.append(service_det)
            
            # Parse technology detection
            technology_detection = []
            for td_data in output_data.get('technology_detection', []):
                tech_det = YamlPluginTechnologyDetection(
                    pattern=td_data['pattern'],
                    technology=td_data['technology'],
                    version_group=td_data.get('version_group')
                )
                technology_detection.append(tech_det)
            
            # Parse requirements
            requirements = []
            req_data = plugin_data.get('requirements', {})
            for tool_data in req_data.get('tools', []):
                requirement = YamlPluginRequirement(
                    name=tool_data['name'],
                    check_command=tool_data.get('check_command'),
                    install_hint=tool_data.get('install_hint'),
                    type='tool'
                )
                requirements.append(requirement)
            
            for file_data in req_data.get('files', []):
                requirement = YamlPluginRequirement(
                    name=file_data['path'],
                    path=file_data['path'],
                    description=file_data.get('description', ''),
                    type='file'
                )
                requirements.append(requirement)
            
            # Parse debug configuration
            debug_data = plugin_data.get('debug', {})
            debug = YamlPluginDebug(
                log_level=debug_data.get('log_level', 'info'),
                trace_decisions=debug_data.get('trace_decisions', False),
                show_command_output=debug_data.get('show_command_output', False)
            )
            
            # Create plugin object
            plugin = YamlPlugin(
                metadata=metadata,
                conditions=conditions,
                options=options,
                commands=commands,
                manual_commands=manual_commands,
                patterns=patterns,
                service_detection=service_detection,
                technology_detection=technology_detection,
                requirements=requirements,
                debug=debug,
                plugin_file=plugin_file
            )
            
            return plugin
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {plugin_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing plugin {plugin_file}: {e}")
            return None
    
    def load_plugins(self) -> Dict[str, YamlPlugin]:
        """Load all YAML plugins from configured directories"""
        logger.info("Loading YAML plugins...")
        
        plugin_files = self.discover_plugins()
        
        for plugin_file in plugin_files:
            plugin = self.parse_plugin(plugin_file)
            if plugin:
                plugin_id = f"{plugin.metadata.name}_{plugin_file.stem}"
                self.plugins[plugin_id] = plugin
                logger.debug(f"Loaded YAML plugin: {plugin.metadata.name} from {plugin_file}")
        
        logger.info(f"Loaded {len(self.plugins)} YAML plugins")
        return self.plugins
    
    def get_plugin(self, plugin_id: str) -> Optional[YamlPlugin]:
        """Get a specific plugin by ID"""
        return self.plugins.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[YamlPlugin]:
        """Get all plugins of a specific type"""
        return [plugin for plugin in self.plugins.values() 
                if plugin.metadata.type == plugin_type]
    
    def validate_all_plugins(self) -> Dict[str, List[str]]:
        """Validate all loaded plugins and return errors"""
        return self.validation_errors


# Global plugin loader instance
yaml_plugin_loader = YamlPluginLoader() 