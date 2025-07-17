"""
Pydantic models for the wordlist scorer system.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
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
    
    @validator('*')
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
    
    @validator('total_score')
    def validate_total_score(cls, v):
        """Round total score to 3 decimal places."""
        return round(v, 3)


class ScoringContext(BaseModel):
    """Input context for scoring wordlists."""
    target: str = Field(..., description="Target IP or hostname")
    port: int = Field(..., ge=1, le=65535, description="Port number")
    service: str = Field(..., description="Service description from scan")
    tech: Optional[str] = Field(None, description="Detected technology/software")
    os: Optional[str] = Field(None, description="Detected operating system")
    version: Optional[str] = Field(None, description="Service version")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers if available")
    
    @validator('port')
    def validate_port(cls, v):
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1-65535, got {v}")
        return v
    
    @validator('tech')
    def normalize_tech(cls, v):
        """Normalize technology name to lowercase."""
        return v.lower() if v else None
    
    def get_cache_key(self) -> str:
        """Generate a cache key for this context."""
        import hashlib
        # Create a unique key based on tech, port, and service
        key_parts = [
            self.tech or "unknown",
            str(self.port),
            self.service[:50]  # First 50 chars of service
        ]
        key_str = "_".join(key_parts)
        # Add hash for uniqueness
        hash_suffix = hashlib.md5(f"{self.target}:{self.service}".encode()).hexdigest()[:8]
        return f"{key_str}_{hash_suffix}".replace(" ", "_").replace("/", "_")


class ScoringResult(BaseModel):
    """Complete scoring result with explanation."""
    score: float = Field(..., ge=0.0, le=1.0, description="Highest score achieved")
    explanation: ScoreBreakdown = Field(..., description="Score breakdown")
    wordlists: List[str] = Field(..., description="Recommended wordlists")
    matched_rules: List[str] = Field(..., description="All rules that matched")
    fallback_used: bool = Field(..., description="Whether generic fallback was used")
    cache_key: str = Field(..., description="Cache key for this result")
    confidence: Confidence = Field(..., description="Overall confidence level")
    
    @validator('score')
    def validate_score(cls, v):
        """Round score to 3 decimal places."""
        return round(v, 3)
    
    @validator('confidence', pre=False, always=True)
    def set_confidence(cls, v, values):
        """Set confidence based on score if not provided."""
        if 'score' in values:
            score = values['score']
            if score >= 0.8:
                return Confidence.HIGH
            elif score >= 0.6:
                return Confidence.MEDIUM
            else:
                return Confidence.LOW
        return v


class CacheEntry(BaseModel):
    """Entry for caching scoring results."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this entry was created")
    context: ScoringContext = Field(..., description="Input context")
    result: ScoringResult = Field(..., description="Scoring result")
    outcome: Optional[Dict[str, Any]] = Field(None, description="Actual outcome if tracked")
    
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
    
    @validator('weight')
    def validate_weight(cls, v):
        """Ensure weight is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {v}")
        return v