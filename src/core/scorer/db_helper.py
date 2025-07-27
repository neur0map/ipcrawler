"""
Database helper for loading tech and port categories
Replaces hardcoded mappings in models.py
"""

import json
import logging
from pathlib import Path
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)

class DatabaseHelper:
    """Helper class to load categories from database files"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent.parent / "database"
        self._tech_db = None
        self._port_db = None
        self._load_databases()
    
    def _load_databases(self):
        """Load technology and port databases"""
        try:
            # Load tech_db.json
            tech_db_path = self.db_path / "technologies" / "tech_db.json"
            if tech_db_path.exists():
                with open(tech_db_path, 'r') as f:
                    self._tech_db = json.load(f)
            else:
                logger.warning(f"Tech database not found at {tech_db_path}")
                self._tech_db = {}
            
            # Load port_db.json
            port_db_path = self.db_path / "ports" / "port_db.json"
            if port_db_path.exists():
                with open(port_db_path, 'r') as f:
                    self._port_db = json.load(f)
            else:
                logger.warning(f"Port database not found at {port_db_path}")
                self._port_db = {}
                
        except Exception as e:
            logger.error(f"Failed to load databases: {e}")
            self._tech_db = {}
            self._port_db = {}
    
    def get_port_categories(self) -> Dict[str, Set[int]]:
        """Get port categories from port_db.json"""
        categories = {}
        
        for port_str, port_info in self._port_db.items():
            try:
                port = int(port_str)
                classification = port_info.get('classification', {})
                category = classification.get('category', 'other')
                
                if category not in categories:
                    categories[category] = set()
                categories[category].add(port)
                
            except (ValueError, TypeError):
                continue
        
        return categories
    
    def get_tech_families(self) -> Dict[str, Set[str]]:
        """Get technology families from tech_db.json"""
        families = {}
        
        for category, technologies in self._tech_db.items():
            for tech_name, tech_info in technologies.items():
                tech_category = tech_info.get('category', category)
                
                if tech_category not in families:
                    families[tech_category] = set()
                families[tech_category].add(tech_name)
        
        return families
    
    def get_port_category(self, port: int) -> str:
        """Get category for a specific port"""
        port_info = self._port_db.get(str(port), {})
        classification = port_info.get('classification', {})
        return classification.get('category', 'other')
    
    def get_tech_family(self, tech: Optional[str]) -> str:
        """Get family for a specific technology"""
        if not tech:
            return "unknown"
        
        tech_lower = tech.lower()
        
        for category, technologies in self._tech_db.items():
            if tech_lower in technologies:
                tech_info = technologies[tech_lower]
                return tech_info.get('category', category)
        
        return "other"

# Global instance
db_helper = DatabaseHelper()