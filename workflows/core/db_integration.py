"""
Database integration helper for workflows
Provides centralized access to database-driven port and technology data
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class WorkflowDatabaseHelper:
    """Centralized database helper for workflow components"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / "database"
        self._tech_db = None
        self._port_db = None
        self._load_databases()
    
    def _load_databases(self):
        """Load technology and port databases with error handling"""
        try:
            # Load tech_db.json
            tech_db_path = self.db_path / "technologies" / "tech_db.json"
            if tech_db_path.exists():
                with open(tech_db_path, 'r') as f:
                    self._tech_db = json.load(f)
                logger.debug(f"Loaded tech database with {len(self._tech_db)} categories")
            else:
                logger.warning(f"Tech database not found at {tech_db_path}")
                self._tech_db = {}
            
            # Load port_db.json
            port_db_path = self.db_path / "ports" / "port_db.json"
            if port_db_path.exists():
                with open(port_db_path, 'r') as f:
                    self._port_db = json.load(f)
                logger.debug(f"Loaded port database with {len(self._port_db)} ports")
            else:
                logger.warning(f"Port database not found at {port_db_path}")
                self._port_db = {}
                
        except Exception as e:
            logger.error(f"Failed to load databases: {e}")
            self._tech_db = {}
            self._port_db = {}
    
    @lru_cache(maxsize=1)
    def get_common_http_ports(self) -> List[int]:
        """Get common HTTP ports from database, with fallback"""
        http_ports = set()
        
        # Extract HTTP-related ports from database
        for port_str, port_info in self._port_db.items():
            try:
                port = int(port_str)
                classification = port_info.get('classification', {})
                
                # Include web, web_secure, and common development ports
                if classification.get('category') in ['web', 'web_secure', 'development']:
                    http_ports.add(port)
                
                # Include common HTTP ports regardless of classification
                if port in [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000, 4200, 3001]:
                    http_ports.add(port)
                    
            except (ValueError, TypeError):
                continue
        
        # Fallback to known common ports if database is empty
        if not http_ports:
            http_ports = {80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000, 4200, 3001}
        
        return sorted(list(http_ports))
    
    @lru_cache(maxsize=10)
    def get_port_category_ports(self, category: str) -> List[int]:
        """Get all ports for a specific category"""
        category_ports = []
        
        for port_str, port_info in self._port_db.items():
            try:
                port = int(port_str)
                classification = port_info.get('classification', {})
                
                if classification.get('category') == category:
                    category_ports.append(port)
                    
            except (ValueError, TypeError):
                continue
        
        return sorted(category_ports)
    
    @lru_cache(maxsize=1)
    def get_technology_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get all technology detection patterns from database"""
        patterns = {}
        
        for category, technologies in self._tech_db.items():
            for tech_name, tech_info in technologies.items():
                indicators = tech_info.get('indicators', {})
                patterns[tech_name] = {
                    'name': tech_info.get('name', tech_name),
                    'category': tech_info.get('category', category),
                    'response_patterns': indicators.get('response_patterns', []),
                    'header_patterns': indicators.get('header_patterns', []),
                    'path_patterns': indicators.get('path_patterns', []),
                    'file_extensions': indicators.get('file_extensions', []),
                    'fuzzy_keywords': indicators.get('fuzzy_keywords', []),
                    'confidence_weights': tech_info.get('confidence_weights', {}),
                    'discovery_paths': tech_info.get('discovery_paths', [])
                }
        
        return patterns
    
    def get_tech_discovery_paths(self, tech: str) -> List[str]:
        """Get discovery paths for a specific technology"""
        tech_lower = tech.lower()
        
        for category, technologies in self._tech_db.items():
            if tech_lower in technologies:
                return technologies[tech_lower].get('discovery_paths', [])
        
        return []
    
    def get_tech_indicators(self, tech: str) -> Dict[str, Any]:
        """Get all indicators for a specific technology"""
        tech_lower = tech.lower()
        
        for category, technologies in self._tech_db.items():
            if tech_lower in technologies:
                return technologies[tech_lower].get('indicators', {})
        
        return {}
    
    def get_technology_by_pattern(self, pattern_type: str, pattern_value: str) -> Optional[str]:
        """Find technology by matching a specific pattern"""
        for category, technologies in self._tech_db.items():
            for tech_name, tech_info in technologies.items():
                indicators = tech_info.get('indicators', {})
                patterns = indicators.get(pattern_type, [])
                
                for pattern in patterns:
                    if pattern.lower() in pattern_value.lower():
                        return tech_name
        
        return None
    
    @lru_cache(maxsize=1)
    def get_server_specific_paths(self) -> Dict[str, List[str]]:
        """Get server-specific paths organized by server type"""
        server_paths = {}
        
        # Extract server-specific discovery paths
        for category, technologies in self._tech_db.items():
            for tech_name, tech_info in technologies.items():
                tech_category = tech_info.get('category', '')
                
                if tech_category in ['web_server', 'web_framework']:
                    discovery_paths = tech_info.get('discovery_paths', [])
                    if discovery_paths:
                        server_paths[tech_name] = discovery_paths
        
        return server_paths
    
    @lru_cache(maxsize=1)
    def get_monitoring_technologies(self) -> Dict[str, Dict[str, Any]]:
        """Get all monitoring/dashboard technologies"""
        monitoring_techs = {}
        
        for category, technologies in self._tech_db.items():
            for tech_name, tech_info in technologies.items():
                tech_category = tech_info.get('category', '')
                
                if tech_category in ['monitoring', 'analytics']:
                    monitoring_techs[tech_name] = tech_info
        
        return monitoring_techs
    
    def get_fallback_patterns(self) -> Dict[str, str]:
        """Get minimal fallback patterns for when database is unavailable"""
        return {
            'WordPress': r'wp-content|wp-includes|wordpress',
            'Django': r'csrfmiddlewaretoken|django',
            'Grafana': r'grafana|Grafana',
            'Prometheus': r'prometheus|/metrics',
            'Apache': r'Apache|apache',
            'Nginx': r'nginx|Nginx',
            'Jenkins': r'jenkins|Jenkins',
            'MySQL': r'mysql|MySQL',
            'PostgreSQL': r'postgresql|PostgreSQL'
        }
    
    def is_database_available(self) -> Dict[str, bool]:
        """Check which databases are available"""
        return {
            'tech_db': bool(self._tech_db),
            'port_db': bool(self._port_db),
            'tech_count': len(self._tech_db) if self._tech_db else 0,
            'port_count': len(self._port_db) if self._port_db else 0
        }


# Global instance for workflows
workflow_db = WorkflowDatabaseHelper()


def get_workflow_database() -> WorkflowDatabaseHelper:
    """Get the global workflow database helper instance"""
    return workflow_db


# Convenience functions for common operations
def get_common_http_ports() -> List[int]:
    """Get common HTTP ports"""
    return workflow_db.get_common_http_ports()


def get_technology_patterns() -> Dict[str, Dict[str, Any]]:
    """Get all technology patterns"""
    return workflow_db.get_technology_patterns()


def get_tech_discovery_paths(tech: str) -> List[str]:
    """Get discovery paths for a technology"""
    return workflow_db.get_tech_discovery_paths(tech)