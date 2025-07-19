"""
Entropy analysis for detecting repetitive wordlist recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import Counter, defaultdict
from dataclasses import dataclass

from .models import ScoringContext, ScoringResult, CacheEntry, AnonymizedCacheEntry, AnonymizedScoringContext
from .cache import cache

logger = logging.getLogger(__name__)


@dataclass
class EntropyMetrics:
    """Entropy analysis results."""
    entropy_score: float  # 0.0 (completely repetitive) to 1.0 (fully diverse)
    total_recommendations: int
    unique_wordlists: int
    most_common_wordlists: List[Tuple[str, int]]
    clustering_percentage: float  # % of recommendations that are duplicates
    context_diversity: float  # How diverse the contexts are
    recommendation_quality: str  # "poor", "acceptable", "good", "excellent"
    warning_message: Optional[str] = None


@dataclass
class ContextCluster:
    """Represents a cluster of similar contexts."""
    tech: Optional[str]
    port_category: str
    count: int
    wordlists: List[str]
    contexts: List[ScoringContext]


class EntropyAnalyzer:
    """Analyzes wordlist recommendation diversity to detect repetitive patterns."""
    
    def __init__(self, warning_threshold: float = 0.7, clustering_threshold: float = 0.3):
        """
        Initialize entropy analyzer.
        
        Args:
            warning_threshold: Entropy below this triggers warnings (0.7 = 70% diversity)
            clustering_threshold: Clustering above this triggers warnings (0.3 = 30% overlap)
        """
        self.warning_threshold = warning_threshold
        self.clustering_threshold = clustering_threshold
    
    def analyze_recent_selections(self, 
                                days_back: int = 7,
                                context: Optional[ScoringContext] = None) -> EntropyMetrics:
        """
        Analyze entropy of recent wordlist selections.
        
        Args:
            days_back: How many days back to analyze
            context: Optional context to focus analysis on similar services
            
        Returns:
            EntropyMetrics with analysis results
        """
        # Get recent cache entries
        entries = self._get_recent_entries(days_back, context)
        
        if len(entries) < 2:
            return EntropyMetrics(
                entropy_score=1.0,
                total_recommendations=len(entries),
                unique_wordlists=len(entries),
                most_common_wordlists=[],
                clustering_percentage=0.0,
                context_diversity=1.0,
                recommendation_quality="insufficient_data"
            )
        
        # Extract wordlists and contexts
        all_wordlists = []
        contexts = []
        
        for entry in entries:
            all_wordlists.extend(entry.result.wordlists)
            contexts.append(entry.context)
        
        # Calculate basic entropy metrics
        wordlist_counter = Counter(all_wordlists)
        total_recs = len(all_wordlists)
        unique_wordlists = len(set(all_wordlists))
        
        # Calculate Shannon entropy
        entropy_score = self._calculate_shannon_entropy(wordlist_counter.values(), total_recs)
        
        # Calculate clustering percentage
        clustering_pct = self._calculate_clustering_percentage(wordlist_counter, total_recs)
        
        # Calculate context diversity
        context_diversity = self._calculate_context_diversity(contexts)
        
        # Determine quality and warnings
        quality, warning = self._assess_quality(entropy_score, clustering_pct, context_diversity)
        
        return EntropyMetrics(
            entropy_score=entropy_score,
            total_recommendations=total_recs,
            unique_wordlists=unique_wordlists,
            most_common_wordlists=wordlist_counter.most_common(10),
            clustering_percentage=clustering_pct,
            context_diversity=context_diversity,
            recommendation_quality=quality,
            warning_message=warning
        )
    
    def detect_context_clusters(self, days_back: int = 30) -> List[ContextCluster]:
        """
        Detect clusters of similar contexts that get identical recommendations.
        
        Args:
            days_back: How many days back to analyze
            
        Returns:
            List of context clusters with their common wordlists
        """
        entries = self._get_recent_entries(days_back, None)
        
        # Group by context similarity
        clusters = defaultdict(list)
        
        for entry in entries:
            # Create cluster key based on tech and port category
            tech = entry.context.tech or "unknown"
            port_cat = self._get_port_category(entry.context.port)
            cluster_key = f"{tech}:{port_cat}"
            
            clusters[cluster_key].append(entry)
        
        # Convert to ContextCluster objects
        result_clusters = []
        
        for cluster_key, cluster_entries in clusters.items():
            if len(cluster_entries) < 2:
                continue  # Skip single-entry clusters
            
            tech, port_cat = cluster_key.split(":", 1)
            tech = None if tech == "unknown" else tech
            
            # Find most common wordlists in this cluster
            all_wordlists = []
            for entry in cluster_entries:
                all_wordlists.extend(entry.result.wordlists)
            
            wordlist_counter = Counter(all_wordlists)
            common_wordlists = [wl for wl, count in wordlist_counter.most_common(5)]
            
            result_clusters.append(ContextCluster(
                tech=tech,
                port_category=port_cat,
                count=len(cluster_entries),
                wordlists=common_wordlists,
                contexts=[entry.context for entry in cluster_entries]
            ))
        
        # Sort by cluster size (largest first)
        result_clusters.sort(key=lambda x: x.count, reverse=True)
        
        return result_clusters
    
    def get_diversification_candidates(self, 
                                     current_wordlists: List[str],
                                     context: ScoringContext,
                                     alternatives_map: Dict[str, List[str]]) -> List[str]:
        """
        Get diversification candidates when entropy is low.
        
        Args:
            current_wordlists: Currently recommended wordlists
            context: Current scoring context
            alternatives_map: Map of wordlist -> alternative wordlists
            
        Returns:
            List of diversified wordlists
        """
        diversified = []
        
        # Check recent usage of each wordlist
        recent_entries = self._get_recent_entries(7, context)
        recent_wordlists = []
        for entry in recent_entries:
            recent_wordlists.extend(entry.result.wordlists)
        
        usage_counter = Counter(recent_wordlists)
        
        for wordlist in current_wordlists:
            usage_count = usage_counter.get(wordlist, 0)
            
            # If this wordlist was used frequently, try to diversify
            if usage_count >= 3 and wordlist in alternatives_map:
                alternatives = alternatives_map[wordlist]
                
                # Pick the least recently used alternative
                best_alternative = min(alternatives, 
                                     key=lambda x: usage_counter.get(x, 0))
                diversified.append(best_alternative)
                
                logger.debug(f"Diversifying {wordlist} -> {best_alternative} "
                           f"(usage: {usage_count} -> {usage_counter.get(best_alternative, 0)})")
            else:
                # Keep original if not overused
                diversified.append(wordlist)
        
        return diversified
    
    def _get_recent_entries(self, 
                          days_back: int, 
                          context: Optional[ScoringContext]) -> List[CacheEntry]:
        """Get recent cache entries, optionally filtered by context similarity."""
        if context:
            # Get entries for similar contexts (same tech or port category)
            similar_entries = []
            
            # Same technology
            if context.tech:
                tech_entries = cache.search_selections(
                    tech=context.tech, 
                    days_back=days_back, 
                    limit=50
                )
                similar_entries.extend(tech_entries)
            
            # Same port category
            port_entries = cache.search_selections(
                port=context.port,
                days_back=days_back,
                limit=50
            )
            similar_entries.extend(port_entries)
            
            # Remove duplicates
            seen_ids = set()
            unique_entries = []
            for entry in similar_entries:
                entry_id = f"{entry.timestamp}:{entry.context.service_fingerprint}"
                if entry_id not in seen_ids:
                    seen_ids.add(entry_id)
                    unique_entries.append(entry)
            
            return unique_entries
        else:
            # Get all recent entries
            return cache.search_selections(days_back=days_back, limit=200)
    
    def _calculate_shannon_entropy(self, counts: List[int], total: int) -> float:
        """Calculate Shannon entropy for wordlist distribution."""
        if total == 0:
            return 1.0
        
        import math
        entropy = 0.0
        for count in counts:
            if count > 0:
                probability = count / total
                entropy -= probability * math.log2(probability)
        
        # Normalize to 0-1 range
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1
        return min(1.0, entropy / max_entropy) if max_entropy > 0 else 1.0
    
    def _calculate_clustering_percentage(self, 
                                       wordlist_counter: Counter, 
                                       total_recs: int) -> float:
        """Calculate what percentage of recommendations are clustering around common wordlists."""
        if total_recs == 0:
            return 0.0
        
        # Count how many recommendations are for the top 3 most common wordlists
        top_3_counts = sum(count for _, count in wordlist_counter.most_common(3))
        return (top_3_counts / total_recs) * 100
    
    def _calculate_context_diversity(self, contexts: List[ScoringContext]) -> float:
        """Calculate diversity of contexts being analyzed."""
        if len(contexts) <= 1:
            return 1.0
        
        # Count unique tech+port combinations
        unique_combinations = set()
        for ctx in contexts:
            tech = ctx.tech or "unknown"
            port_cat = self._get_port_category(ctx.port)
            unique_combinations.add(f"{tech}:{port_cat}")
        
        # Diversity is ratio of unique combinations to total contexts
        return len(unique_combinations) / len(contexts)
    
    def _get_port_category(self, port: int) -> str:
        """Categorize port for clustering analysis."""
        web_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
        db_ports = [3306, 5432, 1433, 27017, 6379]
        admin_ports = [8080, 9090, 10000, 8834, 7001, 4848]
        
        if port in web_ports:
            return "web"
        elif port in db_ports:
            return "database"
        elif port in admin_ports:
            return "admin"
        else:
            return "other"
    
    def _assess_quality(self, 
                       entropy_score: float, 
                       clustering_pct: float, 
                       context_diversity: float) -> Tuple[str, Optional[str]]:
        """Assess overall recommendation quality and generate warnings."""
        warning = None
        
        # Check for entropy problems
        if entropy_score < self.warning_threshold:
            warning = (f"⚠️  Low recommendation diversity (entropy: {entropy_score:.2f}). "
                      f"Wordlists are becoming repetitive.")
        
        # Check for clustering problems  
        if clustering_pct > (self.clustering_threshold * 100):
            clustering_warning = (f"🔄 High clustering detected ({clustering_pct:.1f}% of recommendations "
                                f"use the same few wordlists).")
            warning = warning + " " + clustering_warning if warning else clustering_warning
        
        # Determine overall quality
        if entropy_score >= 0.9 and clustering_pct <= 20:
            quality = "excellent"
        elif entropy_score >= 0.8 and clustering_pct <= 30:
            quality = "good"
        elif entropy_score >= 0.6 and clustering_pct <= 50:
            quality = "acceptable"
        else:
            quality = "poor"
        
        return quality, warning


# Global analyzer instance
analyzer = EntropyAnalyzer()


def analyze_entropy(context: Optional[ScoringContext] = None, 
                   days_back: int = 7) -> EntropyMetrics:
    """
    Convenience function to analyze recommendation entropy.
    
    Args:
        context: Optional context for focused analysis
        days_back: Days to look back for analysis
        
    Returns:
        EntropyMetrics with analysis results
    """
    return analyzer.analyze_recent_selections(days_back, context)


def should_diversify(current_wordlists: List[str], 
                    context: ScoringContext,
                    entropy_threshold: float = 0.7) -> bool:
    """
    Check if current recommendations should be diversified.
    
    Args:
        current_wordlists: Current wordlist recommendations
        context: Scoring context
        entropy_threshold: Threshold below which to diversify
        
    Returns:
        True if diversification is recommended
    """
    metrics = analyze_entropy(context, days_back=7)
    
    # Diversify if entropy is low AND we have enough data
    return (metrics.entropy_score < entropy_threshold and 
            metrics.total_recommendations >= 5)