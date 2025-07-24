"""
Pydantic models for wordlist catalog system.
"""

from typing import List, Dict, Optional, Set, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from enum import Enum
from pathlib import Path
import re


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
    GOOD = "good"           # 10k-50k entries, good coverage
    AVERAGE = "average"     # 1k-10k entries, decent
    BASIC = "basic"         # <1k entries, specialized
    UNKNOWN = "unknown"     # Unable to determine


class WordlistEntry(BaseModel):
    """Individual wordlist entry with comprehensive metadata."""
    
    # Basic identification
    name: str = Field(..., description="Filename of the wordlist")
    display_name: str = Field(..., description="Human-readable name")
    full_path: str = Field(..., description="Absolute path to wordlist file")
    relative_path: str = Field(..., description="Path relative to SecLists root")
    
    # Classification
    category: WordlistCategory = Field(..., description="Primary category")
    subcategory: str = Field("", description="Subcategory within main category")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    
    # Content metrics
    size_lines: int = Field(0, ge=0, description="Number of lines/entries")
    size_bytes: int = Field(0, ge=0, description="File size in bytes")
    quality: WordlistQuality = Field(WordlistQuality.UNKNOWN, description="Quality rating")
    
    # Compatibility and scoring
    tech_compatibility: List[str] = Field(default_factory=list, description="Compatible technologies")
    port_compatibility: List[int] = Field(default_factory=list, description="Relevant port numbers")
    scorer_weight: float = Field(0.5, ge=0.0, le=1.0, description="Base scoring weight")
    confidence_multiplier: float = Field(1.0, ge=0.1, le=2.0, description="Confidence adjustment")
    
    # Usage metadata
    use_cases: List[str] = Field(default_factory=list, description="Specific use cases")
    description: str = Field("", description="Detailed description")
    sample_entries: List[str] = Field(default_factory=list, description="Sample wordlist entries")
    
    # File metadata
    file_encoding: str = Field("utf-8", description="File encoding")
    last_modified: Optional[datetime] = Field(None, description="File last modified time")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Catalog entry update time")
    
    # Performance hints
    recommended_for_ports: List[int] = Field(default_factory=list, description="Recommended for specific ports")
    not_recommended_for: List[str] = Field(default_factory=list, description="What to avoid this for")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure name is not empty and is a valid filename."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        
        # Check for invalid filename characters
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, v):
            raise ValueError(f"Name contains invalid characters: {v}")
        
        return v.strip()
    
    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v):
        """Ensure display name is meaningful."""
        if not v or len(v.strip()) < 3:
            raise ValueError("Display name must be at least 3 characters")
        return v.strip()
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Normalize and validate tags."""
        normalized_tags = []
        for tag in v:
            if isinstance(tag, str) and tag.strip():
                # Normalize to lowercase, replace spaces with hyphens
                normalized_tag = re.sub(r'\s+', '-', tag.strip().lower())
                if normalized_tag not in normalized_tags:
                    normalized_tags.append(normalized_tag)
        return normalized_tags
    
    @field_validator('tech_compatibility')
    @classmethod
    def validate_tech_compatibility(cls, v):
        """Normalize technology names."""
        return [tech.lower().strip() for tech in v if tech.strip()]
    
    @field_validator('port_compatibility')
    @classmethod
    def validate_port_compatibility(cls, v):
        """Validate port numbers."""
        valid_ports = []
        for port in v:
            if isinstance(port, int) and 1 <= port <= 65535:
                valid_ports.append(port)
        return sorted(list(set(valid_ports)))  # Remove duplicates and sort
    
    @model_validator(mode='after')
    def validate_quality_consistency(self):
        """Ensure quality rating matches size metrics."""
        size_lines = self.size_lines
        quality = self.quality
        
        # Auto-assign quality if unknown
        if quality == WordlistQuality.UNKNOWN and size_lines > 0:
            if size_lines >= 50000:
                self.quality = WordlistQuality.EXCELLENT
            elif size_lines >= 10000:
                self.quality = WordlistQuality.GOOD
            elif size_lines >= 1000:
                self.quality = WordlistQuality.AVERAGE
            else:
                self.quality = WordlistQuality.BASIC
        
        return self
    
    def get_relevance_score(self, tech: Optional[str] = None, port: Optional[int] = None) -> float:
        """
        Calculate relevance score for given tech/port context.
        
        Args:
            tech: Technology context
            port: Port context
            
        Returns:
            Relevance score (0.0-1.0)
        """
        score = self.scorer_weight
        
        # Tech compatibility boost
        if tech and tech.lower() in self.tech_compatibility:
            score *= 1.3
        
        # Port compatibility boost
        if port and port in self.port_compatibility:
            score *= 1.2
        
        # Quality adjustment
        quality_multipliers = {
            WordlistQuality.EXCELLENT: 1.2,
            WordlistQuality.GOOD: 1.1,
            WordlistQuality.AVERAGE: 1.0,
            WordlistQuality.BASIC: 0.9,
            WordlistQuality.UNKNOWN: 0.8
        }
        score *= quality_multipliers.get(self.quality, 1.0)
        
        # Apply confidence multiplier
        score *= self.confidence_multiplier
        
        # Ensure score is within bounds
        return min(1.0, max(0.0, score))
    
    def has_tag(self, tag: str) -> bool:
        """Check if wordlist has a specific tag."""
        return tag.lower() in self.tags
    
    def is_compatible_with_tech(self, tech: str) -> bool:
        """Check if wordlist is compatible with technology."""
        return tech.lower() in self.tech_compatibility
    
    def is_suitable_for_port(self, port: int) -> bool:
        """Check if wordlist is suitable for port."""
        return port in self.port_compatibility or port in self.recommended_for_ports
    
    class Config:
        use_enum_values = True


class WordlistFilter(BaseModel):
    """Filter criteria for wordlist searches."""
    categories: Optional[List[WordlistCategory]] = None
    tags: Optional[List[str]] = None
    tech_compatibility: Optional[List[str]] = None
    port_compatibility: Optional[List[int]] = None
    min_quality: Optional[WordlistQuality] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    min_scorer_weight: Optional[float] = None
    use_cases: Optional[List[str]] = None
    
    class Config:
        use_enum_values = True


class WordlistCatalog(BaseModel):
    """Complete catalog of available wordlists."""
    
    # Metadata
    catalog_version: str = Field("1.0.0", description="Catalog format version")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Catalog generation time")
    seclists_path: str = Field("", description="Path to SecLists installation")
    seclists_version: Optional[str] = Field(None, description="SecLists version/commit")
    
    # Wordlist entries
    wordlists: Dict[str, WordlistEntry] = Field(default_factory=dict, description="Wordlist entries by name")
    
    # Index for fast lookups
    by_category: Dict[str, List[str]] = Field(default_factory=dict, description="Index by category")
    by_tech: Dict[str, List[str]] = Field(default_factory=dict, description="Index by technology")
    by_port: Dict[str, List[str]] = Field(default_factory=dict, description="Index by port")
    by_tags: Dict[str, List[str]] = Field(default_factory=dict, description="Index by tags")
    
    # Statistics
    stats: Dict[str, Any] = Field(default_factory=dict, description="Catalog statistics")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_wordlist(self, wordlist: WordlistEntry):
        """Add a wordlist to the catalog and update indexes."""
        self.wordlists[wordlist.name] = wordlist
        self._update_indexes(wordlist)
    
    def _update_indexes(self, wordlist: WordlistEntry):
        """Update search indexes for a wordlist."""
        # Category index
        category = wordlist.category if isinstance(wordlist.category, str) else wordlist.category.value
        if category not in self.by_category:
            self.by_category[category] = []
        if wordlist.name not in self.by_category[category]:
            self.by_category[category].append(wordlist.name)
        
        # Technology index
        for tech in wordlist.tech_compatibility:
            if tech not in self.by_tech:
                self.by_tech[tech] = []
            if wordlist.name not in self.by_tech[tech]:
                self.by_tech[tech].append(wordlist.name)
        
        # Port index
        for port in wordlist.port_compatibility:
            port_str = str(port)
            if port_str not in self.by_port:
                self.by_port[port_str] = []
            if wordlist.name not in self.by_port[port_str]:
                self.by_port[port_str].append(wordlist.name)
        
        # Tags index
        for tag in wordlist.tags:
            if tag not in self.by_tags:
                self.by_tags[tag] = []
            if wordlist.name not in self.by_tags[tag]:
                self.by_tags[tag].append(wordlist.name)
    
    def rebuild_indexes(self):
        """Rebuild all indexes from current wordlists."""
        self.by_category.clear()
        self.by_tech.clear()
        self.by_port.clear()
        self.by_tags.clear()
        
        for wordlist in self.wordlists.values():
            self._update_indexes(wordlist)
    
    def get_by_category(self, category: WordlistCategory) -> List[WordlistEntry]:
        """Get all wordlists in a category."""
        names = self.by_category.get(category.value, [])
        return [self.wordlists[name] for name in names if name in self.wordlists]
    
    def get_by_tech(self, tech: str) -> List[WordlistEntry]:
        """Get wordlists compatible with technology."""
        names = self.by_tech.get(tech.lower(), [])
        return [self.wordlists[name] for name in names if name in self.wordlists]
    
    def get_by_port(self, port: int) -> List[WordlistEntry]:
        """Get wordlists suitable for port."""
        names = self.by_port.get(str(port), [])
        return [self.wordlists[name] for name in names if name in self.wordlists]
    
    def get_by_tag(self, tag: str) -> List[WordlistEntry]:
        """Get wordlists with specific tag."""
        names = self.by_tags.get(tag.lower(), [])
        return [self.wordlists[name] for name in names if name in self.wordlists]
    
    def search(self, filters: WordlistFilter) -> List[WordlistEntry]:
        """Search wordlists using filter criteria."""
        results = list(self.wordlists.values())
        
        # Apply category filter
        if filters.categories:
            category_names = {cat.value for cat in filters.categories}
            results = [wl for wl in results if wl.category.value in category_names]
        
        # Apply tag filter
        if filters.tags:
            tag_set = {tag.lower() for tag in filters.tags}
            results = [wl for wl in results if any(tag in tag_set for tag in wl.tags)]
        
        # Apply tech compatibility filter
        if filters.tech_compatibility:
            tech_set = {tech.lower() for tech in filters.tech_compatibility}
            results = [wl for wl in results if any(tech in tech_set for tech in wl.tech_compatibility)]
        
        # Apply port compatibility filter
        if filters.port_compatibility:
            port_set = set(filters.port_compatibility)
            results = [wl for wl in results if any(port in port_set for port in wl.port_compatibility)]
        
        # Apply quality filter
        if filters.min_quality:
            quality_order = {
                WordlistQuality.BASIC: 1,
                WordlistQuality.AVERAGE: 2,
                WordlistQuality.GOOD: 3,
                WordlistQuality.EXCELLENT: 4
            }
            min_quality_value = quality_order.get(filters.min_quality, 0)
            results = [wl for wl in results if quality_order.get(wl.quality, 0) >= min_quality_value]
        
        # Apply size filters
        if filters.min_size is not None:
            results = [wl for wl in results if wl.size_lines >= filters.min_size]
        
        if filters.max_size is not None:
            results = [wl for wl in results if wl.size_lines <= filters.max_size]
        
        # Apply scorer weight filter
        if filters.min_scorer_weight is not None:
            results = [wl for wl in results if wl.scorer_weight >= filters.min_scorer_weight]
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        total_wordlists = len(self.wordlists)
        
        # Category distribution
        category_dist = {}
        for category, names in self.by_category.items():
            category_dist[category] = len(names)
        
        # Quality distribution
        quality_dist = {}
        for wordlist in self.wordlists.values():
            quality = wordlist.quality if isinstance(wordlist.quality, str) else wordlist.quality.value
            quality_dist[quality] = quality_dist.get(quality, 0) + 1
        
        # Size statistics
        sizes = [wl.size_lines for wl in self.wordlists.values() if wl.size_lines > 0]
        
        stats = {
            "total_wordlists": total_wordlists,
            "categories": len(self.by_category),
            "technologies": len(self.by_tech),
            "ports_covered": len(self.by_port),
            "unique_tags": len(self.by_tags),
            "category_distribution": category_dist,
            "quality_distribution": quality_dist,
            "size_stats": {
                "min": min(sizes) if sizes else 0,
                "max": max(sizes) if sizes else 0,
                "avg": int(sum(sizes) / len(sizes)) if sizes else 0,
                "total_entries": sum(sizes) if sizes else 0
            }
        }
        
        self.stats = stats
        return stats