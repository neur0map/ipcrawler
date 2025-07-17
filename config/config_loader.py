import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration manager for IP Crawler"""
    
    def __init__(self, config_path: str = "config.yaml"):
        # If relative path, make it relative to project root (parent of config dir)
        if not Path(config_path).is_absolute():
            project_root = Path(__file__).parent.parent
            self.config_path = project_root / config_path
        else:
            self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            # Return default config if file doesn't exist
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config or self._get_default_config()
        except Exception:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "version": "1.0.0",
            "scan": {
                "fast_port_discovery": True,
                "max_detailed_ports": 1000
            },
            "privileges": {
                "prompt_for_sudo": True,
                "auto_escalate": False
            },
            "parallel": {
                "batch_size": 10,
                "ports_per_batch": 6553
            },
            "output": {
                "save_raw_xml": False,
                "verbose": False,
                "raw_output": False,
                "real_time_save": True
            },
            "tools": {
                "nmap_path": "",
                "nuclei_path": ""
            },
            "fuzzing": {
                "enable_ffuf": True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def fast_port_discovery(self) -> bool:
        """Check if fast port discovery is enabled"""
        return self.get("scan.fast_port_discovery", True)
    
    
    @property
    def batch_size(self) -> int:
        """Get batch size for parallel scanning"""
        return self.get("parallel.batch_size", 10)
    
    @property
    def ports_per_batch(self) -> int:
        """Get ports per batch"""
        return self.get("parallel.ports_per_batch", 6553)
    
    @property
    def max_detailed_ports(self) -> int:
        """Get maximum ports for detailed scanning"""
        return self.get("scan.max_detailed_ports", 1000)
    
    @property
    def raw_output(self) -> bool:
        """Check if raw output is enabled"""
        return self.get("output.raw_output", False)
    
    @property
    def real_time_save(self) -> bool:
        """Check if real-time file saving is enabled"""
        return self.get("output.real_time_save", True)

    # Privilege settings
    @property
    def prompt_for_sudo(self) -> bool:
        """Whether to prompt for sudo escalation"""
        return self._config.get("privileges", {}).get("prompt_for_sudo", True)
    
    @property
    def auto_escalate(self) -> bool:
        """Whether to automatically escalate to sudo"""
        return self._config.get("privileges", {}).get("auto_escalate", False)
    
    @property
    def version(self) -> str:
        """Get application version"""
        return self.get("version", "1.0.0")
    
    @property
    def enable_ffuf(self) -> bool:
        """Check if ffuf fuzzing is enabled"""
        return self.get("fuzzing.enable_ffuf", True)


# Global config instance
config = Config()