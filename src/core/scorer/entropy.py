#!/usr/bin/env python3
"""
SmartList Entropy Analysis

Analyzes wordlist recommendation diversity to detect repetitive patterns
and clustering issues that could indicate poor rule quality.

Usage:
    from src.core.scorer.entropy import analyzer
    metrics = analyzer.analyze_recent_selections(days_back=7)
"""

import math
import logging
from dataclasses import dataclass
from collections import Counter, defaultdict
from typing import List, Optional, Dict, Any, Set
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.scorer.models import ScoringContext
from src.core.scorer.cache import cache

logger = logging.getLogger(__name__)


@dataclass
class EntropyMetrics:
    """Entropy analysis results."""
    entropy_score: float
    total_recommendations: int
    unique_wordlists: int
    most_common_wordlists: List[tuple]
    clustering_percentage: float
    context_diversity: float
    recommendation_quality: str
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
        Analyze recent wordlist selections for entropy and clustering patterns.
        
        Args:
            days_back: Number of days of data to analyze
            context: Optional context filter for analysis
            
        Returns:
            EntropyMetrics with analysis results
        """
        entries = self._get_recent_entries(days_back, context)
        
        if len(entries) < 3:
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
            all_wordlists.extend(entry.get('selected_wordlists', []))
            if 'context' in entry:
                contexts.append(entry['context'])
        
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
        Detect clusters of similar contexts that tend to get the same recommendations.
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            List of detected clusters sorted by size
        """
        entries = self._get_recent_entries(days_back, None)
        
        # Group by context similarity
        clusters = defaultdict(list)
        
        for entry in entries:
            if 'context' not in entry:
                continue
            ctx = entry['context']
            tech = ctx.get('tech') or "unknown"
            port_cat = self._get_port_category(ctx.get('port', 80))
            cluster_key = f"{tech}:{port_cat}"
            clusters[cluster_key].append(entry)
        
        # Convert to ContextCluster objects
        result_clusters = []
        
        for cluster_key, cluster_entries in clusters.items():
            if len(cluster_entries) < 2:
                continue
                
            tech, port_cat = cluster_key.split(":", 1)
            tech = None if tech == "unknown" else tech
            
            # Find most common wordlists in this cluster
            all_wordlists = []
            for entry in cluster_entries:
                all_wordlists.extend(entry.get('selected_wordlists', []))
            
            wordlist_counter = Counter(all_wordlists)
            common_wordlists = [wl for wl, count in wordlist_counter.most_common(5)]
            
            result_clusters.append(ContextCluster(
                tech=tech,
                port_category=port_cat,
                count=len(cluster_entries),
                wordlists=common_wordlists,
                contexts=[entry.get('context', {}) for entry in cluster_entries]
            ))
        
        # Sort by cluster size (largest first)
        result_clusters.sort(key=lambda x: x.count, reverse=True)
        
        return result_clusters
    
    def diversify_recommendations(self, 
                                wordlists: List[str], 
                                context: Optional[ScoringContext] = None,
                                alternatives_map: Optional[Dict[str, List[str]]] = None) -> List[str]:
        """
        Apply diversification to reduce repetitive recommendations.
        
        Args:
            wordlists: Original wordlist recommendations
            context: Current scoring context
            alternatives_map: Map of wordlist -> alternative wordlists
            
        Returns:
            Diversified wordlist recommendations
        """
        if not alternatives_map:
            return wordlists
            
        diversified = []
        
        # Check recent usage of each wordlist
        recent_entries = self._get_recent_entries(7, context)
        recent_wordlists = []
        for entry in recent_entries:
            recent_wordlists.extend(entry.get('selected_wordlists', []))
        
        usage_counter = Counter(recent_wordlists)
        
        for wordlist in wordlists:
            usage_count = usage_counter.get(wordlist, 0)
            
            # If this wordlist was used frequently, try to diversify
            if usage_count >= 3 and wordlist in alternatives_map:
                alternatives = alternatives_map[wordlist]
                
                # Pick the least recently used alternative
                best_alternative = min(alternatives, 
                                     key=lambda x: usage_counter.get(x, 0))
                diversified.append(best_alternative)
            else:
                # Keep original if not overused
                diversified.append(wordlist)
        
        return diversified
    
    def _get_recent_entries(self, days_back: int, context: Optional[ScoringContext] = None):
        """Get recent cache entries, optionally filtered by context similarity."""
        try:
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
                    entry_id = f"{entry.get('timestamp', 0)}:{entry.get('context', {}).get('service_fingerprint', '')}"
                    if entry_id not in seen_ids:
                        seen_ids.add(entry_id)
                        unique_entries.append(entry)
                
                return unique_entries
            else:
                # Get all recent entries
                return cache.search_selections(days_back=days_back, limit=200)
        except Exception as e:
            logger.warning(f"Failed to get cache entries: {e}")
            return []
    
    def _calculate_shannon_entropy(self, counts, total):
        """Calculate Shannon entropy for wordlist distribution."""
        if total == 0:
            return 1.0
        
        entropy = 0.0
        for count in counts:
            if count > 0:
                probability = count / total
                entropy -= probability * math.log2(probability)
        
        # Normalize to 0-1 range
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1
        return entropy / max_entropy if max_entropy > 0 else 1.0
    
    def _calculate_clustering_percentage(self, wordlist_counter, total_recs):
        """Calculate what percentage of recommendations are clustering around common wordlists."""
        if total_recs == 0:
            return 0.0
        
        # Count how many recommendations are for the top 3 most common wordlists
        top_3_counts = sum(count for _, count in wordlist_counter.most_common(3))
        return (top_3_counts / total_recs) * 100
    
    def _calculate_context_diversity(self, contexts):
        """Calculate diversity of contexts being analyzed."""
        if len(contexts) <= 1:
            return 1.0
        
        # Count unique tech+port combinations
        unique_combinations = set()
        for ctx in contexts:
            tech = ctx.get('tech') or "unknown"
            port_cat = self._get_port_category(ctx.get('port', 80))
            unique_combinations.add(f"{tech}:{port_cat}")
        
        # Diversity is ratio of unique combinations to total contexts
        return len(unique_combinations) / len(contexts)
    
    def _get_port_category(self, port):
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
        elif port < 1024:
            return "system"
        else:
            return "user"
    
    def _assess_quality(self, entropy_score, clustering_pct, context_diversity):
        """Assess overall recommendation quality and generate warnings."""
        warning = None
        
        # Check for entropy problems
        if entropy_score < self.warning_threshold:
            warning = (f"⚠️  Low recommendation diversity (entropy: {entropy_score:.2f}). "
                      "Consider adding more wordlist alternatives.")
        
        # Check for clustering problems  
        if clustering_pct > (self.clustering_threshold * 100):
            clustering_warning = (f"🔄 High clustering detected ({clustering_pct:.1f}% of recommendations "
                                "focus on top wordlists). Review rule specificity.")
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
    Convenience function to analyze entropy for a given context.
    
    Args:
        context: Optional scoring context to filter analysis
        days_back: Number of days of data to analyze
        
    Returns:
        EntropyMetrics with analysis results
    """
    return analyzer.analyze_recent_selections(days_back, context)


def should_diversify_recommendations(context: Optional[ScoringContext] = None,
                                   days_back: int = 7,
                                   entropy_threshold: float = 0.7) -> bool:
    """
    Determine if recommendations should be diversified based on recent entropy.
    
    Args:
        context: Optional scoring context
        days_back: Number of days to analyze
        entropy_threshold: Entropy threshold below which diversification is recommended
        
    Returns:
        True if diversification is recommended
    """
    metrics = analyze_entropy(context, days_back=7)
    
    # Diversify if entropy is low AND we have enough data
    return (metrics.entropy_score < entropy_threshold and 
            metrics.total_recommendations >= 5)