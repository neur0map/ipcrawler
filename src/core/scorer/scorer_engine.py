"""IPCrawler scoring engine for wordlist recommendations"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScoringContext:
    """Context for scoring wordlists"""
    target: str
    port: int
    service: str
    tech: Optional[str] = None
    os: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ScoreBreakdown:
    """Breakdown of scoring factors"""
    service_match: float = 0.0
    tech_match: float = 0.0
    port_match: float = 0.0
    popularity: float = 0.0
    total: float = 0.0


@dataclass
class WordlistScore:
    """Score for a specific wordlist"""
    wordlist: str
    score: float
    confidence: str
    breakdown: ScoreBreakdown
    reason: str


@dataclass
class ScoringResult:
    """Result of wordlist scoring"""
    context: ScoringContext
    scores: List[WordlistScore]
    total_wordlists: int
    execution_time: float


def score_wordlists(context: ScoringContext, wordlists: List[str]) -> ScoringResult:
    """Score wordlists based on context"""
    scores = []
    
    for wordlist in wordlists:
        # Simple scoring based on service name matching
        score = 0.5  # Base score
        confidence = "LOW"
        reason = "Basic scoring"
        
        # Boost score if wordlist name contains service
        if context.service and context.service.lower() in wordlist.lower():
            score += 0.3
            confidence = "MEDIUM"
            reason = f"Service match: {context.service}"
        
        # Boost score if wordlist name contains tech
        if context.tech and context.tech.lower() in wordlist.lower():
            score += 0.2
            confidence = "HIGH" if score > 0.7 else "MEDIUM"
            reason = f"Technology match: {context.tech}"
        
        breakdown = ScoreBreakdown(
            service_match=0.3 if context.service and context.service.lower() in wordlist.lower() else 0.0,
            tech_match=0.2 if context.tech and context.tech.lower() in wordlist.lower() else 0.0,
            port_match=0.0,
            popularity=0.5,
            total=score
        )
        
        wordlist_score = WordlistScore(
            wordlist=wordlist,
            score=score,
            confidence=confidence,
            breakdown=breakdown,
            reason=reason
        )
        scores.append(wordlist_score)
    
    # Sort by score descending
    scores.sort(key=lambda x: x.score, reverse=True)
    
    return ScoringResult(
        context=context,
        scores=scores,
        total_wordlists=len(wordlists),
        execution_time=0.1
    )


def score_wordlists_with_catalog(context: ScoringContext) -> ScoringResult:
    """Score wordlists using catalog data"""
    # Fallback wordlists for basic scoring
    default_wordlists = [
        "common.txt",
        "directory-list-2.3-medium.txt",
        "directory-list-2.3-small.txt",
        "raft-medium-directories.txt",
        "raft-medium-files.txt"
    ]
    
    return score_wordlists(context, default_wordlists)


def get_wordlist_paths(wordlist_names: List[str]) -> List[str]:
    """Get full paths for wordlist names"""
    return [f"/usr/share/seclists/Discovery/Web-Content/{name}" for name in wordlist_names]


def get_port_context(port: int, service: str = None) -> Dict[str, Any]:
    """Get context information for a port"""
    return {
        "port": port,
        "service": service or "unknown",
        "common_services": [],
        "technology_stack": []
    }


def explain_scoring(result: ScoringResult) -> str:
    """Explain how scoring was calculated"""
    explanation = f"Scored {result.total_wordlists} wordlists for {result.context.service} on port {result.context.port}\n"
    explanation += f"Top results:\n"
    
    for score in result.scores[:3]:
        explanation += f"- {score.wordlist}: {score.score:.2f} ({score.confidence}) - {score.reason}\n"
    
    return explanation


def get_scoring_stats(result: ScoringResult) -> Dict[str, Any]:
    """Get statistics about scoring results"""
    return {
        "total_wordlists": result.total_wordlists,
        "high_confidence": len([s for s in result.scores if s.confidence == "HIGH"]),
        "medium_confidence": len([s for s in result.scores if s.confidence == "MEDIUM"]),
        "low_confidence": len([s for s in result.scores if s.confidence == "LOW"]),
        "average_score": sum(s.score for s in result.scores) / len(result.scores) if result.scores else 0,
        "execution_time": result.execution_time
    }