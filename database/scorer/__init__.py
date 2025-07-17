"""
Wordlist Scorer System for IPCrawler

A rule-based scoring engine for recommending wordlists based on service context.
Features hierarchical rules with graceful fallbacks and transparent scoring.
"""

from .scorer_engine import (
    score_wordlists, 
    score_wordlists_with_catalog,
    get_wordlist_paths,
    explain_scoring, 
    get_scoring_stats
)
from .models import ScoringResult, WordlistScore, ScoreBreakdown, ScoringContext
from .cache import cache_selection, cache

__version__ = "1.0.0"

__all__ = [
    "score_wordlists",
    "score_wordlists_with_catalog",
    "get_wordlist_paths",
    "explain_scoring", 
    "get_scoring_stats",
    "ScoringContext", 
    "ScoringResult",
    "WordlistScore",
    "ScoreBreakdown",
    "cache_selection",
    "cache"
]