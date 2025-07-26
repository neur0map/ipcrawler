"""
WordList Catalog Models

This module defines the data models for the wordlist catalog system.
"""

from enum import Enum
from typing import List, Set, Dict, Any, Optional
from datetime import datetime
import json


class WordlistCategory(str, Enum):
    """Categories for wordlist classification."""
    WEB_CONTENT = "web-content"
    CMS = "cms"
    DATABASE = "database"
    API = "api"
    FRAMEWORK = "framework"
    ADMIN_PANEL = "admin-panel"
    AUTHENTICATION = "authentication"
    BACKUP = "backup"
    CONFIG = "config"
    DEVELOPMENT = "development"
    FILE_TRANSFER = "file-transfer"
    MAIL = "mail"
    NETWORK = "network"
    OPERATING_SYSTEM = "operating-system"
    PROTOCOLS = "protocols"
    SERVICES = "services"
    SUBDOMAIN = "subdomain"
    USERNAMES = "usernames"
    PASSWORDS = "passwords"
    FUZZING = "fuzzing"
    MISCONFIGURATION = "misconfiguration"
    VULNERABILITY = "vulnerability"
    OTHER = "other"


class WordlistQuality(str, Enum):
    """Quality ratings for wordlists."""
    EXCELLENT = "excellent"  # >50k entries, well-curated
    GOOD = "good"           # 10k-50k entries, solid coverage
    AVERAGE = "average"     # 1k-10k entries, decent coverage
    SPECIALIZED = "specialized"  # <1k entries, highly focused
    BASIC = "basic"         # <100 entries, very limited


class WordlistSubcategory(str, Enum):
    """Subcategories for more specific classification."""
    GENERAL = "general"
    SPECIFIC = "specific"
    OTHER = "other"
    
    @classmethod
    def from_path(cls, path):
        """Create subcategory from path."""
        return cls.GENERAL


class WordlistEntry:
    """Individual wordlist entry with comprehensive metadata."""
    
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', '')
        self.display_name = kwargs.get('display_name', '')
        self.full_path = kwargs.get('full_path', '')
        self.relative_path = kwargs.get('relative_path', '')
        self.category = kwargs.get('category', WordlistCategory.OTHER)
        self.subcategory = kwargs.get('subcategory', WordlistSubcategory.GENERAL)
        self.tags = kwargs.get('tags', set())
        self.size_lines = kwargs.get('size_lines', 0)
        self.size_bytes = kwargs.get('size_bytes', 0)
        self.quality = kwargs.get('quality', WordlistQuality.BASIC)
        self.tech_compatibility = kwargs.get('tech_compatibility', set())
        self.port_compatibility = kwargs.get('port_compatibility', set())
        self.scorer_weight = kwargs.get('scorer_weight', 1.0)
        self.use_cases = kwargs.get('use_cases', [])
        self.description = kwargs.get('description', '')
        self.sample_entries = kwargs.get('sample_entries', [])
        self.last_modified = kwargs.get('last_modified', datetime.now())
        self.recommended_for_ports = kwargs.get('recommended_for_ports', set())
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'full_path': self.full_path,
            'relative_path': self.relative_path,
            'category': self.category.value if isinstance(self.category, Enum) else self.category,
            'subcategory': self.subcategory.value if isinstance(self.subcategory, Enum) else self.subcategory,
            'tags': list(self.tags),
            'size_lines': self.size_lines,
            'size_bytes': self.size_bytes,
            'quality': self.quality.value if isinstance(self.quality, Enum) else self.quality,
            'tech_compatibility': list(self.tech_compatibility),
            'port_compatibility': list(self.port_compatibility),
            'scorer_weight': self.scorer_weight,
            'use_cases': self.use_cases,
            'description': self.description,
            'sample_entries': self.sample_entries,
            'last_modified': self.last_modified.isoformat() if isinstance(self.last_modified, datetime) else self.last_modified,
            'recommended_for_ports': list(self.recommended_for_ports)
        }


class WordlistCatalog:
    """Complete catalog of wordlists with metadata and indexes."""
    
    def __init__(self, seclists_path: str = ""):
        self.seclists_path = seclists_path
        self.seclists_version = ""
        self.wordlists = []
        self.tech_index = {}
        self.port_index = {}
        self.category_index = {}
        self.tag_index = {}
        self.last_updated = datetime.now()
    
    def add_wordlist(self, wordlist: WordlistEntry):
        """Add a wordlist to the catalog."""
        self.wordlists.append(wordlist)
    
    def model_dump(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'seclists_path': self.seclists_path,
            'seclists_version': self.seclists_version,
            'wordlists': [wl.to_dict() for wl in self.wordlists],
            'tech_index': self.tech_index,
            'port_index': self.port_index,
            'category_index': self.category_index,
            'tag_index': self.tag_index,
            'last_updated': self.last_updated.isoformat()
        }
    
    def get_stats(self):
        """Get basic statistics about the catalog."""
        total_size_bytes = sum(wl.size_bytes for wl in self.wordlists)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        categories = {}
        for wl in self.wordlists:
            cat = wl.category.value if isinstance(wl.category, Enum) else wl.category
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            'total_wordlists': len(self.wordlists),
            'total_size_mb': total_size_mb,
            'categories': categories
        }
