#!/usr/bin/env python3
"""
SmartList Scoring Models

Data models for the SmartList scoring system including contexts, results, and cache entries.
"""

import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class Confidence(str, Enum):
    """Confidence levels for scoring results."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of scoring components."""
    exact_match: float = 0.0
    tech_category: float = 0.0
    port_context: float = 0.0
    service_keywords: float = 0.0
    generic_fallback: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for easy serialization."""
        return {
            "exact_match": self.exact_match,
            "tech_category": self.tech_category,
            "port_context": self.port_context,
            "service_keywords": self.service_keywords,
            "generic_fallback": self.generic_fallback
        }


@dataclass
class WordlistScore:
    """Individual wordlist with its score and reasoning."""
    wordlist: str
    total_score: float
    breakdown: ScoreBreakdown
    matched_rules: List[str]
    confidence: Confidence
    
    def __post_init__(self):
        """Round total score to 3 decimal places."""
        self.total_score = round(self.total_score, 3)


@dataclass
class ScoringContext:
    """Input context for scoring wordlists."""
    target: str
    port: int
    service: Optional[str] = None
    tech: Optional[str] = None
    os: Optional[str] = None
    version: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    spider_data: Optional[Dict[str, Any]] = None
    
    def get_cache_key(self) -> str:
        """Generate a cache key for this scoring context."""
        anon_context = AnonymizedScoringContext.from_scoring_context(self)
        return anon_context.get_cache_key()


@dataclass
class AnonymizedScoringContext:
    """Privacy-focused scoring context without sensitive target information."""
    port_category: str
    port: int
    service_fingerprint: str
    service_length: int
    tech_family: str
    tech: Optional[str] = None
    os_family: Optional[str] = None
    version: Optional[str] = None
    has_headers: bool = False
    
    @classmethod
    def from_scoring_context(cls, context: ScoringContext) -> 'AnonymizedScoringContext':
        """Create anonymized context from regular scoring context."""
        
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
        """Categorize port using database lookup."""
        from src.core.scorer.db_helper import db_helper
        return db_helper.get_port_category(port)
    
    @staticmethod
    def _get_tech_family(tech: Optional[str]) -> str:
        """Categorize technology using database lookup."""
        from src.core.scorer.db_helper import db_helper
        return db_helper.get_tech_family(tech)
    
    @staticmethod
    def _get_os_family(os: str) -> str:
        """Categorize OS into families."""
        if not os:
            return "unknown"
        
        os_lower = os.lower()
        
        if any(term in os_lower for term in ["windows", "win32", "microsoft"]):
            return "windows"
        elif any(term in os_lower for term in ["linux", "ubuntu", "debian", "centos", "rhel", "fedora"]):
            return "linux"
        elif any(term in os_lower for term in ["unix", "bsd", "aix", "solaris"]):
            return "unix"
        elif any(term in os_lower for term in ["mac", "darwin", "osx"]):
            return "macos"
        else:
            return "other"
    
    def get_cache_key(self) -> str:
        """Generate a privacy-safe cache key."""
        # Use only non-sensitive information
        key_parts = [
            self.port_category,
            str(self.port),
            self.service_fingerprint,
            self.tech_family,
            self.tech or "none",
            self.os_family or "none"
        ]
        return ":".join(key_parts)


@dataclass
class ScoringResult:
    """Complete scoring result with explanation."""
    score: float
    explanation: ScoreBreakdown
    wordlists: List[str]
    matched_rules: List[str]
    fallback_used: bool
    cache_key: str
    confidence: Confidence
    
    # Entropy-related fields
    entropy_score: Optional[float] = None
    diversification_applied: bool = False
    frequency_adjustments: Optional[Dict[str, float]] = None
    synergy_bonuses: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        """Round score to 3 decimal places and set confidence."""
        self.score = round(self.score, 3)
        
        # Set confidence based on score if not provided
        if self.score >= 0.8:
            self.confidence = Confidence.HIGH
        elif self.score >= 0.6:
            self.confidence = Confidence.MEDIUM
        else:
            self.confidence = Confidence.LOW
    
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


@dataclass
class CacheEntry:
    """Entry for caching scoring results."""
    timestamp: datetime
    context: ScoringContext
    result: ScoringResult
    outcome: Optional[Dict[str, Any]] = None
    
    def __init__(self, context: ScoringContext, result: ScoringResult, outcome: Optional[Dict[str, Any]] = None):
        self.timestamp = datetime.utcnow()
        self.context = context
        self.result = result
        self.outcome = outcome


@dataclass
class AnonymizedCacheEntry:
    """Privacy-focused cache entry without sensitive information."""
    timestamp: datetime
    context: AnonymizedScoringContext
    result: ScoringResult
    outcome: Optional[Dict[str, Any]] = None
    
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


@dataclass
class CacheIndex:
    """Index for the cache system."""
    total_selections: int = 0
    by_tech: Dict[str, int] = None
    by_port: Dict[str, int] = None
    fallback_usage: Dict[str, Any] = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.by_tech is None:
            self.by_tech = {}
        if self.by_port is None:
            self.by_port = {}
        if self.fallback_usage is None:
            self.fallback_usage = {"count": 0, "percentage": 0.0}
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()
    
    def update_with_entry(self, entry: AnonymizedCacheEntry):
        """Update index statistics with a new entry."""
        self.total_selections += 1
        
        tech = entry.context.tech or "unknown"
        self.by_tech[tech] = self.by_tech.get(tech, 0) + 1
        
        port_category = self._get_port_category(entry.context.port)
        self.by_port[port_category] = self.by_port.get(port_category, 0) + 1
        
        if entry.result.fallback_used:
            self.fallback_usage["count"] += 1
        
        # Recalculate percentage
        if self.total_selections > 0:
            self.fallback_usage["percentage"] = round(
                (self.fallback_usage["count"] / self.total_selections) * 100, 2
            )
        
        self.last_updated = datetime.utcnow()
    
    def _get_port_category(self, port: int) -> str:
        """Determine port category using database lookup."""
        from src.core.scorer.db_helper import db_helper
        return db_helper.get_port_category(port)


@dataclass
class ScoringRule:
    """Individual scoring rule."""
    name: str
    weight: float
    description: str
    category: str
    
    def __post_init__(self):
        """Ensure weight is between 0 and 1."""
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Rule weight must be between 0 and 1, got {self.weight}")