"""IPCrawler scoring system for wordlist recommendations"""

from .scorer_engine import (
    score_wordlists,
    score_wordlists_with_catalog,
    get_wordlist_paths,
    get_port_context,
    explain_scoring,
    get_scoring_stats,
    ScoringContext,
    ScoringResult,
    WordlistScore,
    ScoreBreakdown
)
from .cache import cache_selection, cache

__version__ = "1.0.0"

__all__ = [
    "score_wordlists",
    "score_wordlists_with_catalog",
    "get_wordlist_paths",
    "get_port_context",
    "explain_scoring", 
    "get_scoring_stats",
    "ScoringContext", 
    "ScoringResult",
    "WordlistScore",
    "ScoreBreakdown",
    "cache_selection",
    "cache"
]