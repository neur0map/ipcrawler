"""
Configuration and dependency management for HTTP scanner workflow.

This module handles all configuration loading, database initialization, 
and dependency validation for the HTTP scanner.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from src.core.utils.debugging import debug_print


def check_dependencies() -> bool:
    """Check if HTTP scanner dependencies are available at runtime"""
    try:
        import httpx
        import dns.resolver
        import dns.zone
        import dns.query
        return True
    except ImportError:
        return False


class HTTPScannerConfig:
    """Configuration manager for HTTP scanner with database integration"""
    
    def __init__(self):
        self.config = {}
        self.port_database = None
        self.technology_database = None
        self.technology_matcher = None
        self.scanner_config_manager = None
        
        # Dependency availability flags
        self.deps_available = False
        self.port_db_available = False
        self.tech_db_available = False
        self.smartlist_available = False
        
        self._check_all_dependencies()
        self._load_configuration()
        self._load_all_databases()
    
    def _check_all_dependencies(self) -> None:
        """Check availability of all optional dependencies"""
        # Core HTTP dependencies
        try:
            import httpx
            import dns.resolver
            import dns.zone
            import dns.query
            self.deps_available = True
        except ImportError:
            self.deps_available = False
        
        # Port database
        try:
            from database.ports import load_port_database
            self.port_db_available = True
        except ImportError:
            self.port_db_available = False
        
        # Technology database
        try:
            from database.technologies import (
                load_technology_database_from_file,
                TechnologyMatcher,
                ScannerConfigManager
            )
            self.tech_db_available = True
        except ImportError:
            self.tech_db_available = False
        
        # SmartList integration
        try:
            from src.core.scorer import (
                score_wordlists_with_catalog,
                score_wordlists,
                get_wordlist_paths,
                ScoringContext
            )
            self.smartlist_available = True
        except ImportError:
            self.smartlist_available = False
            debug_print("SmartList components not available", level="WARNING")
    
    def _load_configuration(self) -> None:
        """Load configuration from config.yaml"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            debug_print("Configuration loaded successfully")
        except Exception as e:
            debug_print(f"Could not load config.yaml: {e}", level="WARNING")
            self.config = {}
    
    def _load_all_databases(self) -> None:
        """Load all available databases"""
        self._load_port_database()
        self._load_technology_database()
        self._load_scanner_configuration()
    
    def _load_port_database(self) -> None:
        """Load port database for service-specific path discovery"""
        if not self.port_db_available or self.port_database is not None:
            return
        
        try:
            from database.ports import load_port_database
            db_path = Path(__file__).parent.parent.parent / "database" / "ports" / "port_db.json"
            with open(db_path, 'r') as f:
                db_data = json.load(f)
            self.port_database = load_port_database(db_data)
            debug_print("Port database loaded successfully")
        except Exception as e:
            debug_print(f"Could not load port database: {e}", level="WARNING")
            self.port_database = {}
    
    def _load_technology_database(self) -> None:
        """Load technology database for intelligent detection"""
        if not self.tech_db_available or self.technology_database is not None:
            return
        
        try:
            from database.technologies import (
                load_technology_database_from_file,
                TechnologyMatcher
            )
            db_path = Path(__file__).parent.parent.parent / "database" / "technologies" / "tech_db.json"
            self.technology_database = load_technology_database_from_file(db_path)
            self.technology_matcher = TechnologyMatcher(self.technology_database)
            debug_print("Technology database loaded successfully")
        except Exception as e:
            debug_print(f"Could not load technology database: {e}", level="WARNING")
            self.technology_database = None
            self.technology_matcher = None
    
    def _load_scanner_configuration(self) -> None:
        """Load scanner configuration database"""
        if not self.tech_db_available or self.scanner_config_manager is not None:
            return
        
        try:
            from database.technologies import ScannerConfigManager
            config_path = Path(__file__).parent.parent.parent / "database" / "technologies" / "scanner_config.json"
            self.scanner_config_manager = ScannerConfigManager(config_path)
            debug_print("Scanner configuration loaded successfully")
        except Exception as e:
            debug_print(f"Could not load scanner configuration: {e}", level="WARNING")
            self.scanner_config_manager = None
    
    def get_service_specific_paths(self, port: int) -> list:
        """Get service-specific paths from port database"""
        if not self.port_database:
            return []
        
        try:
            port_entry = self.port_database.ports.get(str(port)) if hasattr(self.port_database, 'ports') else None
            if port_entry and hasattr(port_entry, 'indicators') and port_entry.indicators and hasattr(port_entry.indicators, 'paths'):
                paths = port_entry.indicators.paths or []
                debug_print(f"Found {len(paths)} database paths for port {port}: {paths}")
                return paths
        except Exception as e:
            debug_print(f"Error getting service paths for port {port}: {e}", level="WARNING")
        
        return []
    
    def get_discovery_config(self) -> Dict[str, Any]:
        """Get discovery configuration settings"""
        return self.config.get('discovery', {})
    
    def is_enhanced_discovery_enabled(self) -> bool:
        """Check if enhanced discovery is enabled"""
        discovery_config = self.get_discovery_config()
        return discovery_config.get('enhanced', True)
    
    def is_smartlist_enabled(self) -> bool:
        """Check if SmartList is available and enabled"""
        return self.is_enhanced_discovery_enabled() and self.smartlist_available
    
    def get_common_ports(self) -> list:
        """Get common HTTP ports to scan"""
        return [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
    
    def get_user_agents(self) -> list:
        """Get user agent strings for HTTP requests"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ]
    
    def get_timeout_settings(self) -> Dict[str, int]:
        """Get timeout settings for HTTP operations"""
        return {
            'connect': 5,
            'read': 10,
            'write': 5,
            'pool': 5,
            'dns': 5
        }
    
    def get_concurrency_limits(self) -> Dict[str, int]:
        """Get concurrency limits for HTTP operations"""
        return {
            'max_concurrent': 20,
            'max_keepalive_connections': 5,
            'max_connections': 10,
            'max_paths_per_wordlist': 100,
            'max_wordlists': 3
        }
    
    def validate_runtime_dependencies(self) -> Tuple[bool, list]:
        """Validate that required dependencies are available"""
        missing = []
        
        if not self.deps_available:
            missing.append("httpx and dnspython required for full functionality")
        
        return len(missing) == 0, missing


# Global configuration instance
_config_instance: Optional[HTTPScannerConfig] = None


def get_scanner_config() -> HTTPScannerConfig:
    """Get the global scanner configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = HTTPScannerConfig()
    return _config_instance


def reload_config() -> HTTPScannerConfig:
    """Reload the configuration (useful for testing)"""
    global _config_instance
    _config_instance = HTTPScannerConfig()
    return _config_instance