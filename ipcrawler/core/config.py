"""
Enhanced configuration management module with multi-file support.
"""

import sys
import toml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from ..models.config import AppConfig


class ConfigManager:
    """Enhanced TOML configuration manager with multi-file support."""
    
    def __init__(self, config_path: str = "config.toml", config_dir: str = "configs"):
        self.config_path = Path(config_path)
        self.config_dir = Path(config_dir)
        self.config = self._load_config()
        
        # Load additional configuration files
        self.presets_config = self._load_config_file("presets.toml", default={})
        self.templates_config = self._load_config_file("templates.toml", default={})
        self.workflows_config = self._load_config_file("workflows.toml", default={})
        self.security_config = self._load_config_file("security.toml", default={})
        self.output_config = self._load_config_file("output.toml", default={})
    
    def _load_config(self) -> AppConfig:
        """Load main configuration from TOML file."""
        if not self.config_path.exists():
            return self._create_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = toml.load(f)
            
            # Handle backwards compatibility for old config format
            if "presets" in config_data and not self.config_dir.exists():
                # Old format - migrate presets to new structure
                self._migrate_old_config(config_data)
            
            # Extract templates mapping for backwards compatibility
            if "templates" in config_data:
                templates_mapping = config_data.pop("templates")
                # Merge with new templates config if it exists
                self._ensure_templates_config(templates_mapping)
            
            # Validate and parse with Pydantic
            return AppConfig(**config_data)
            
        except (toml.TomlDecodeError, FileNotFoundError) as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
            return self._create_default_config()
    
    def _load_config_file(self, filename: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load a specific configuration file from the configs directory."""
        config_file = self.config_dir / filename
        
        if not config_file.exists():
            return default or {}
        
        try:
            with open(config_file, 'r') as f:
                return toml.load(f)
        except (toml.TomlDecodeError, FileNotFoundError) as e:
            print(f"Warning: Error loading {filename}: {e}", file=sys.stderr)
            return default or {}
    
    def _migrate_old_config(self, config_data: Dict[str, Any]) -> None:
        """Migrate old config format to new multi-file structure."""
        print("Migrating old configuration format to new structure...", file=sys.stderr)
        
        # Create configs directory
        self.config_dir.mkdir(exist_ok=True)
        
        # Extract and save presets
        if "presets" in config_data:
            presets_data = config_data.pop("presets")
            presets_file = self.config_dir / "presets.toml"
            try:
                with open(presets_file, 'w') as f:
                    toml.dump(presets_data, f)
                print(f"Migrated presets to {presets_file}", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Could not save presets config: {e}", file=sys.stderr)
        
        # Save updated main config without presets
        try:
            with open(self.config_path, 'w') as f:
                toml.dump(config_data, f)
            print("Updated main configuration file", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not update main config: {e}", file=sys.stderr)
    
    def _ensure_templates_config(self, templates_mapping: Dict[str, str]) -> None:
        """Ensure templates configuration exists with provided mapping."""
        templates_file = self.config_dir / "templates.toml"
        
        if not templates_file.exists():
            # Create default templates config with provided mapping
            templates_config = {
                "categories": templates_mapping,
                "metadata": {
                    "scan_depth": 3,
                    "auto_discover": True,
                    "cache_templates": True
                },
                "validation": {
                    "require_description": True,
                    "require_tags": True,
                    "validate_syntax": True,
                    "validate_security": True
                }
            }
            
            try:
                with open(templates_file, 'w') as f:
                    toml.dump(templates_config, f)
                print(f"Created templates configuration: {templates_file}", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Could not create templates config: {e}", file=sys.stderr)
    
    def _get_version_from_config(self) -> str:
        """Get version from config.toml if it exists."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = toml.load(f)
                    return config_data.get("application", {}).get("version", "2.0.0")
        except Exception:
            pass
        return "2.0.0"
    
    def _create_default_config(self) -> AppConfig:
        """Create default configuration."""
        default_config = {
            "application": {
                "name": "ipcrawler",
                "version": self._get_version_from_config(),
                "debug": False
            },
            "performance": {
                "concurrent_limit": 10,
                "default_timeout": 60,
                "max_output_size": 1048576,
                "memory_limit": 512
            },
            "security": {
                "enforce_validation": True,
                "allow_shell_commands": False,
                "max_template_size": 1048576
            },
            "system": {
                "config_dir": "configs",
                "templates_dir": "templates", 
                "results_dir": "results",
                "cache_dir": ".cache"
            },
            "logging": {
                "silent": True,
                "level": "INFO",
                "file_rotation": True,
                "max_log_size": 10485760
            },
            "retry": {
                "count": 3,
                "backoff_multiplier": 2,
                "max_wait_time": 60
            }
        }
        
        # Save default config
        try:
            with open(self.config_path, 'w') as f:
                toml.dump(default_config, f)
        except Exception as e:
            print(f"Warning: Could not save default config: {e}", file=sys.stderr)
        
        return AppConfig(**self._flatten_config(default_config))
    
    def _flatten_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested config for backwards compatibility."""
        flattened = {}
        
        # Map new structure to old structure expected by AppConfig
        if "performance" in config_data:
            flattened["settings"] = {
                "concurrent_limit": config_data["performance"].get("concurrent_limit", 10),
                "default_timeout": config_data["performance"].get("default_timeout", 60),
                "max_output_size": config_data["performance"].get("max_output_size", 1048576)
            }
        
        if "logging" in config_data:
            flattened["logging"] = {
                "silent": config_data["logging"].get("silent", True)
            }
        
        if "retry" in config_data:
            flattened["retry"] = {
                "max_attempts": config_data["retry"].get("count", 3),
                "wait_multiplier": config_data["retry"].get("backoff_multiplier", 2),
                "wait_max": config_data["retry"].get("max_wait_time", 60)
            }
        
        # Add templates from templates config if available
        if hasattr(self, 'templates_config') and self.templates_config:
            flattened["templates"] = self.templates_config.get("categories", {})
        
        return flattened
    
    def get_template_folder(self, flag: str) -> str:
        """Get template folder for a given flag."""
        # Check new templates config first
        if self.templates_config and "categories" in self.templates_config:
            return self.templates_config["categories"].get(flag, flag)
        
        # Fallback to old config format
        return self.config.templates.get(flag, flag) if hasattr(self.config, 'templates') else flag
    
    def get_concurrent_limit(self) -> int:
        """Get concurrent execution limit."""
        return self.config.settings.concurrent_limit
    
    def get_default_timeout(self) -> int:
        """Get default timeout."""
        return self.config.settings.default_timeout
    
    def is_silent_mode(self) -> bool:
        """Check if silent mode is enabled."""
        return self.config.logging.silent
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration."""
        return {
            "max_attempts": self.config.retry.max_attempts,
            "wait_multiplier": self.config.retry.wait_multiplier,
            "wait_max": self.config.retry.wait_max
        }
    
    def get_preset(self, preset_name: str) -> Optional[List[str]]:
        """Get preset arguments by name (supports tool.preset_name format)."""
        # Check new presets config first
        if self.presets_config:
            return self._get_preset_from_new_config(preset_name)
        
        # Fallback to old config format
        if not self.config.presets:
            return None
            
        # Handle tool.preset_name format
        if '.' in preset_name:
            tool_name, preset_key = preset_name.split('.', 1)
            tool_presets = self.config.presets.get(tool_name, {})
            return tool_presets.get(preset_key)
        
        # Handle global presets
        return self.config.presets.get(preset_name)
    
    def _get_preset_from_new_config(self, preset_name: str) -> Optional[List[str]]:
        """Get preset from new presets configuration."""
        if '.' in preset_name:
            tool_name, preset_key = preset_name.split('.', 1)
            
            # Check tool-specific presets
            if tool_name in self.presets_config:
                return self.presets_config[tool_name].get(preset_key)
            
            # Check global presets with tool prefix
            if "global" in self.presets_config:
                return self.presets_config["global"].get(preset_name)
        
        # Check global presets
        if "global" in self.presets_config:
            return self.presets_config["global"].get(preset_name)
        
        # Check direct preset name
        return self.presets_config.get(preset_name)
    
    def get_all_presets(self) -> Dict[str, Any]:
        """Get all available presets."""
        if self.presets_config:
            return self.presets_config
        return self.config.presets or {}
    
    def list_presets_for_tool(self, tool_name: str) -> Dict[str, List[str]]:
        """List all presets available for a specific tool."""
        if self.presets_config and tool_name in self.presets_config:
            return self.presets_config[tool_name]
        
        if not self.config.presets:
            return {}
        return self.config.presets.get(tool_name, {})
    
    def get_templates_config(self) -> Dict[str, Any]:
        """Get templates configuration."""
        return self.templates_config
    
    def get_workflows_config(self) -> Dict[str, Any]:
        """Get workflows configuration."""
        return self.workflows_config
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration."""
        return self.security_config
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.output_config
    
    def get_config_value(self, config_type: str, key_path: str, default=None) -> Any:
        """Get a configuration value from any config file using dot notation."""
        config_map = {
            "main": self.config.dict() if hasattr(self.config, 'dict') else {},
            "presets": self.presets_config,
            "templates": self.templates_config,
            "workflows": self.workflows_config,
            "security": self.security_config,
            "output": self.output_config
        }
        
        config = config_map.get(config_type, {})
        if not config:
            return default
        
        # Navigate through nested keys
        keys = key_path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all configurations to dictionary."""
        return {
            "main": self.config.dict() if hasattr(self.config, 'dict') else {},
            "presets": self.presets_config,
            "templates": self.templates_config,
            "workflows": self.workflows_config,
            "security": self.security_config,
            "output": self.output_config
        }
    
    def reload_configs(self) -> None:
        """Reload all configuration files."""
        self.config = self._load_config()
        self.presets_config = self._load_config_file("presets.toml", default={})
        self.templates_config = self._load_config_file("templates.toml", default={})
        self.workflows_config = self._load_config_file("workflows.toml", default={})
        self.security_config = self._load_config_file("security.toml", default={})
        self.output_config = self._load_config_file("output.toml", default={})
    
    def validate_all_configs(self) -> Dict[str, Any]:
        """Validate all configuration files."""
        validation_results = {
            "main": {"valid": True, "errors": []},
            "presets": {"valid": True, "errors": []},
            "templates": {"valid": True, "errors": []},
            "workflows": {"valid": True, "errors": []},
            "security": {"valid": True, "errors": []},
            "output": {"valid": True, "errors": []}
        }
        
        # Basic validation - check if configs loaded successfully
        configs = {
            "main": self.config,
            "presets": self.presets_config,
            "templates": self.templates_config,
            "workflows": self.workflows_config,
            "security": self.security_config,
            "output": self.output_config
        }
        
        for config_name, config_data in configs.items():
            if not config_data:
                validation_results[config_name]["valid"] = False
                validation_results[config_name]["errors"].append("Configuration not loaded or empty")
        
        return validation_results