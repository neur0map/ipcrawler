"""
Configuration management module.
"""

import sys
import toml
from pathlib import Path
from typing import Dict, Any
from ..models.config import AppConfig


class ConfigManager:
    """Handles TOML configuration file management."""
    
    def __init__(self, config_path: str = "config.toml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """Load configuration from TOML file."""
        if not self.config_path.exists():
            return self._create_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = toml.load(f)
            
            # Validate and parse with Pydantic
            return AppConfig(**config_data)
            
        except (toml.TomlDecodeError, FileNotFoundError) as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
            return self._create_default_config()
    
    def _create_default_config(self) -> AppConfig:
        """Create default configuration."""
        default_config = {
            "templates": {
                "recon": "recon",
                "default": "default"
            },
            "settings": {
                "concurrent_limit": 10,
                "default_timeout": 60,
                "max_output_size": 1048576  # 1MB
            },
            "logging": {
                "silent": True
            },
            "retry": {
                "max_attempts": 3,
                "wait_multiplier": 1.0,
                "wait_max": 60
            }
        }
        
        # Save default config
        try:
            with open(self.config_path, 'w') as f:
                toml.dump(default_config, f)
        except Exception as e:
            print(f"Warning: Could not save default config: {e}", file=sys.stderr)
        
        return AppConfig(**default_config)
    
    def get_template_folder(self, flag: str) -> str:
        """Get template folder for a given flag."""
        return self.config.templates.get(flag, flag)
    
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.config.dict()