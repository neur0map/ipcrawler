"""
Pydantic models for the wordlist scorer system.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class Confidence(str, Enum):
    """Confidence levels for scoring results."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of scoring components."""
    exact_match: float = Field(0.0, ge=0.0, le=1.0, description="Score from exact tech+port match")
    tech_category: float = Field(0.0, ge=0.0, le=1.0, description="Score from tech category match")
    port_context: float = Field(0.0, ge=0.0, le=1.0, description="Score from port category match")
    service_keywords: float = Field(0.0, ge=0.0, le=1.0, description="Score from service keyword match")
    generic_fallback: float = Field(0.0, ge=0.0, le=1.0, description="Score from generic fallback")
    
    @field_validator('*')
    @classmethod
    def validate_scores(cls, v):
        """Ensure all scores are between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {v}")
        return round(v, 3)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for easy serialization."""
        return {
            "exact_match": self.exact_match,
            "tech_category": self.tech_category,
            "port_context": self.port_context,
            "service_keywords": self.service_keywords,
            "generic_fallback": self.generic_fallback
        }


class WordlistScore(BaseModel):
    """Individual wordlist with its score and reasoning."""
    wordlist: str = Field(..., description="Wordlist filename")
    total_score: float = Field(..., ge=0.0, le=1.0, description="Combined score for this wordlist")
    breakdown: ScoreBreakdown = Field(..., description="Score component breakdown")
    matched_rules: List[str] = Field(default_factory=list, description="Rules that matched")
    confidence: Confidence = Field(..., description="Confidence level based on score")
    
    @field_validator('total_score')
    @classmethod
    def validate_total_score(cls, v):
        """Round total score to 3 decimal places."""
        return round(v, 3)


class ScoringContext(BaseModel):
    """Input context for scoring wordlists."""
    target: str = Field(..., description="Target IP or hostname")
    port: int = Field(..., ge=1, le=65535, description="Port number")
    service: Optional[str] = Field(None, description="Service description from scan")
    tech: Optional[str] = Field(None, description="Detected technology/software")
    os: Optional[str] = Field(None, description="Detected operating system")
    version: Optional[str] = Field(None, description="Service version")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers if available")
    spider_data: Optional[Dict[str, Any]] = Field(None, description="Spider intelligence data from mini_spider_04")
    
    def get_cache_key(self) -> str:
        """Generate a cache key for this scoring context."""
        # Create anonymized context and use its cache key
        anon_context = AnonymizedScoringContext.from_scoring_context(self)
        return anon_context.get_cache_key()


class AnonymizedScoringContext(BaseModel):
    """Privacy-focused scoring context without sensitive target information."""
    port_category: str = Field(..., description="Port category (web, database, admin, etc.)")
    port: int = Field(..., ge=1, le=65535, description="Port number")
    service_fingerprint: str = Field(..., description="Hash of service details (no target info)")
    service_length: int = Field(..., description="Length of service description for similarity")
    tech_family: str = Field(..., description="Technology family (web_server, cms, etc.)")
    tech: Optional[str] = Field(None, description="Detected technology/software")
    os_family: Optional[str] = Field(None, description="OS family (linux, windows, etc.)")
    version: Optional[str] = Field(None, description="Service version")
    has_headers: bool = Field(False, description="Whether HTTP headers were present")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1-65535, got {v}")
        return v
    
    @field_validator('tech')
    @classmethod
    def normalize_tech(cls, v):
        """Normalize technology name to lowercase."""
        return v.lower() if v else None
    
    @classmethod
    def from_scoring_context(cls, context: ScoringContext) -> 'AnonymizedScoringContext':
        """Create anonymized context from regular scoring context."""
        import hashlib
        
        # Generate service fingerprint without target info
        service_data = f"{context.service}:{context.tech or ''}:{context.version or ''}"
        service_fingerprint = hashlib.md5(service_data.encode()).hexdigest()[:8]
        
        # Determine categories
        port_category = cls._get_port_category(context.port)
        tech_family = cls._get_tech_family(context.tech)
        os_family = cls._get_os_family(context.os) if context.os else None
        
        return cls(
            port_category=port_category,
            port=context.port,
            service_fingerprint=service_fingerprint,
            service_length=len(context.service) if context.service else 0,
            tech_family=tech_family,
            tech=context.tech,
            os_family=os_family,
            version=context.version,
            has_headers=bool(context.headers)
        )
    
    @staticmethod
    def _get_port_category(port: int) -> str:
        """Categorize port for privacy-safe grouping."""
        categories = {
            "web": [80, 8080, 8000, 8888, 3000, 5000, 9000, 4200, 3001],
            "web_secure": [443, 8443, 9443, 4443],
            "database": [3306, 5432, 1433, 27017, 6379, 5984, 9200, 7474, 8529],
            "admin": [8080, 9090, 10000, 8834, 7001, 4848, 8161, 9990],
            "mail": [25, 465, 587, 110, 995, 143, 993, 2525],
            "file_transfer": [21, 22, 873, 445, 139, 2049, 111],
            "remote_access": [22, 23, 3389, 5900, 5901, 1194, 4444],
            "proxy": [3128, 8118, 8123, 1080, 9050],
            "development": [3000, 4200, 5000, 8000, 9000, 3001, 5001, 8001]
        }
        
        for category, ports in categories.items():
            if port in ports:
                return category
        return "other"
    
    @staticmethod
    def _get_tech_family(tech: Optional[str]) -> str:
        """Categorize technology into families."""
        if not tech:
            return "unknown"
        
        tech_lower = tech.lower()
        
        families = {
            "web_server": ["apache", "nginx", "iis", "lighttpd", "caddy", "tomcat", "jetty"],
            "cms": ["wordpress", "drupal", "joomla", "typo3", "magento", "shopify"],
            "database": ["mysql", "postgresql", "mongodb", "redis", "cassandra", "oracle"],
            "framework": ["django", "flask", "rails", "laravel", "symfony", "express"],
            "admin_panel": ["phpmyadmin", "adminer", "webmin", "cpanel", "plesk"],
            "mail_server": ["postfix", "exim", "sendmail", "exchange", "zimbra"],
            "monitoring": ["nagios", "zabbix", "prometheus", "grafana", "kibana"],
            "ci_cd": ["jenkins", "gitlab", "github", "bitbucket", "bamboo"],
            "container": ["docker", "kubernetes", "openshift", "rancher"]
        }
        
        for family, techs in families.items():
            if any(t in tech_lower for t in techs):
                return family
        
        return "other"
    
    @staticmethod
    def _get_os_family(os: str) -> str:
        """Categorize OS into families."""
        if not os:
            return "other"
        
        os_lower = os.lower()
        
        if any(x in os_lower for x in ["windows", "win"]):
            return "windows"
        elif any(x in os_lower for x in ["linux", "ubuntu", "debian", "centos", "redhat"]):
            return "linux"
        elif any(x in os_lower for x in ["mac", "osx", "darwin"]):
            return "macos"
        elif any(x in os_lower for x in ["bsd", "freebsd", "openbsd"]):
            return "bsd"
        else:
            return "other"
    
    def get_cache_key(self) -> str:
        """Generate a privacy-safe cache key."""
        # Use only non-sensitive information
        key_parts = [
            self.tech_family,
            self.port_category,
            str(self.port),
            self.service_fingerprint
        ]
        return "_".join(key_parts)
    


class ScoringResult(BaseModel):
    """Complete scoring result with explanation."""
    score: float = Field(..., ge=0.0, le=1.0, description="Highest score achieved")
    explanation: ScoreBreakdown = Field(..., description="Score breakdown")
    wordlists: List[str] = Field(..., description="Recommended wordlists")
    matched_rules: List[str] = Field(..., description="All rules that matched")
    fallback_used: bool = Field(..., description="Whether generic fallback was used")
    cache_key: str = Field(..., description="Cache key for this result")
    confidence: Confidence = Field(..., description="Overall confidence level")
    
    # Entropy-related fields
    entropy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Entropy score for recommendation diversity")
    diversification_applied: bool = Field(False, description="Whether diversification was applied")
    frequency_adjustments: Optional[Dict[str, float]] = Field(None, description="Rule frequency adjustments applied")
    synergy_bonuses: Optional[Dict[str, float]] = Field(None, description="Tech+path synergy bonuses applied")
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v):
        """Round score to 3 decimal places."""
        return round(v, 3)
    
    @field_validator('confidence')
    @classmethod
    def set_confidence(cls, v, info):
        """Set confidence based on score if not provided."""
        if hasattr(info, 'data') and 'score' in info.data:
            score = info.data['score']
            if score >= 0.8:
                return Confidence.HIGH
            elif score >= 0.6:
                return Confidence.MEDIUM
            else:
                return Confidence.LOW
        return v
    
    def get_entropy_summary(self) -> Dict[str, Any]:
        """Get summary of entropy-related information."""
        return {
            "entropy_score": self.entropy_score,
            "diversification_applied": self.diversification_applied,
            "frequency_adjustments_count": len(self.frequency_adjustments or {}),
            "synergy_bonuses_count": len(self.synergy_bonuses or {}),
            "quality_indicators": {
                "has_entropy_data": self.entropy_score is not None,
                "is_diversified": self.diversification_applied,
                "has_frequency_boost": bool(self.frequency_adjustments),
                "has_synergy": bool(self.synergy_bonuses)
            }
        }


class CacheEntry(BaseModel):
    """Entry for caching scoring results."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this entry was created")
    context: ScoringContext = Field(..., description="Input context")
    result: ScoringResult = Field(..., description="Scoring result")
    outcome: Optional[Dict[str, Any]] = Field(None, description="Actual outcome if tracked")


class AnonymizedCacheEntry(BaseModel):
    """Privacy-focused cache entry without sensitive information."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this entry was created")
    context: AnonymizedScoringContext = Field(..., description="Anonymized context")
    result: ScoringResult = Field(..., description="Scoring result")
    outcome: Optional[Dict[str, Any]] = Field(None, description="Actual outcome if tracked")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def from_cache_entry(cls, entry: CacheEntry) -> 'AnonymizedCacheEntry':
        """Create anonymized cache entry from regular entry."""
        anon_context = AnonymizedScoringContext.from_scoring_context(entry.context)
        return cls(
            timestamp=entry.timestamp,
            context=anon_context,
            result=entry.result,
            outcome=entry.outcome
        )
    
    def get_entropy_data(self) -> Dict[str, Any]:
        """Extract entropy-related data from this cache entry."""
        return {
            "timestamp": self.timestamp,
            "wordlists": self.result.wordlists,
            "matched_rules": self.result.matched_rules,
            "context_key": f"{self.context.tech or 'unknown'}:{self.context.port}",
            "entropy_score": self.result.entropy_score,
            "diversification_applied": self.result.diversification_applied
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CacheIndex(BaseModel):
    """Index for the cache system."""
    total_selections: int = Field(0, description="Total number of selections cached")
    by_tech: Dict[str, int] = Field(default_factory=dict, description="Selections by technology")
    by_port: Dict[str, int] = Field(default_factory=dict, description="Selections by port category")
    fallback_usage: Dict[str, Any] = Field(
        default_factory=lambda: {"count": 0, "percentage": 0.0},
        description="Fallback usage statistics"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def update_stats(self, entry: CacheEntry):
        """Update index statistics with a new entry."""
        self.total_selections += 1
        
        # Update tech stats
        tech = entry.context.tech or "unknown"
        self.by_tech[tech] = self.by_tech.get(tech, 0) + 1
        
        # Update port category stats
        port_category = self._get_port_category(entry.context.port)
        self.by_port[port_category] = self.by_port.get(port_category, 0) + 1
        
        # Update fallback stats
        if entry.result.fallback_used:
            self.fallback_usage["count"] += 1
        
        # Recalculate percentage
        if self.total_selections > 0:
            self.fallback_usage["percentage"] = round(
                (self.fallback_usage["count"] / self.total_selections) * 100, 2
            )
        
        self.last_updated = datetime.utcnow()
    
    def _get_port_category(self, port: int) -> str:
        """Determine port category."""
        web_ports = [80, 443, 8080, 8443, 8000, 8888]
        db_ports = [3306, 5432, 1433, 27017, 6379]
        admin_ports = [8080, 9090, 10000, 8834, 8443]
        
        if port in web_ports:
            return "web"
        elif port in db_ports:
            return "database"
        elif port in admin_ports:
            return "admin"
        else:
            return "other"


class ScoringRule(BaseModel):
    """Individual scoring rule."""
    name: str = Field(..., description="Rule name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Rule weight")
    description: str = Field(..., description="Rule description")
    category: str = Field(..., description="Rule category (exact, tech, port, generic)")
    
    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v):
        """Ensure weight is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {v}")
        return v