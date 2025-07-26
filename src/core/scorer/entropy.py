"""
"""



logger = logging.getLogger(__name__)


@dataclass
    """Entropy analysis results."""
    warning_message: Optional[str] = None


@dataclass
    """Represents a cluster of similar contexts."""


    """Analyzes wordlist recommendation diversity to detect repetitive patterns."""
    
    def __init__(self, warning_threshold: float = 0.7, clustering_threshold: float = 0.3):
        """
        
            warning_threshold: Entropy below this triggers warnings (0.7 = 70% diversity)
            clustering_threshold: Clustering above this triggers warnings (0.3 = 30% overlap)
        """
        self.warning_threshold = warning_threshold
        self.clustering_threshold = clustering_threshold
    
                                days_back: int = 7,
                                context: Optional[ScoringContext] = None) -> EntropyMetrics:
        """
        
            
        """
        # Get recent cache entries
        entries = self._get_recent_entries(days_back, context)
        
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
        
            
        """
        entries = self._get_recent_entries(days_back, None)
        
        # Group by context similarity
        clusters = defaultdict(list)
        
            tech = entry.context.tech or "unknown"
            port_cat = self._get_port_category(entry.context.port)
            cluster_key = f"{tech}:{port_cat}"
            
        
        # Convert to ContextCluster objects
        result_clusters = []
        
            
            tech, port_cat = cluster_key.split(":", 1)
            tech = None if tech == "unknown" else tech
            
            # Find most common wordlists in this cluster
            all_wordlists = []
            
            wordlist_counter = Counter(all_wordlists)
            common_wordlists = [wl for wl, count in wordlist_counter.most_common(5)]
            
                tech=tech,
                port_category=port_cat,
                count=len(cluster_entries),
                wordlists=common_wordlists,
                contexts=[entry.context for entry in cluster_entries]
            ))
        
        # Sort by cluster size (largest first)
        result_clusters.sort(key=lambda x: x.count, reverse=True)
        
    
        """
        
            
        """
        diversified = []
        
        # Check recent usage of each wordlist
        recent_entries = self._get_recent_entries(7, context)
        recent_wordlists = []
        
        usage_counter = Counter(recent_wordlists)
        
            usage_count = usage_counter.get(wordlist, 0)
            
            # If this wordlist was used frequently, try to diversify
            if usage_count >= 3 and wordlist in alternatives_map:
                alternatives = alternatives_map[wordlist]
                
                # Pick the least recently used alternative
                best_alternative = min(alternatives, 
                                     key=lambda x: usage_counter.get(x, 0))
                
                # Keep original if not overused
        
    
        """Get recent cache entries, optionally filtered by context similarity."""
            # Get entries for similar contexts (same tech or port category)
            similar_entries = []
            
            # Same technology
                tech_entries = cache.search_selections(
                    tech=context.tech, 
                    days_back=days_back, 
                    limit=50
                )
            
            # Same port category
            port_entries = cache.search_selections(
                port=context.port,
                days_back=days_back,
                limit=50
            )
            
            # Remove duplicates
            seen_ids = set()
            unique_entries = []
                entry_id = f"{entry.timestamp}:{entry.context.service_fingerprint}"
            
            # Get all recent entries
            return cache.search_selections(days_back=days_back, limit=200)
    
        """Calculate Shannon entropy for wordlist distribution."""
        if total == 0:
        
        entropy = 0.0
                probability = count / total
                entropy -= probability * math.log2(probability)
        
        # Normalize to 0-1 range
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1
    
        """Calculate what percentage of recommendations are clustering around common wordlists."""
        if total_recs == 0:
        
        # Count how many recommendations are for the top 3 most common wordlists
        top_3_counts = sum(count for _, count in wordlist_counter.most_common(3))
    
        """Calculate diversity of contexts being analyzed."""
        if len(contexts) <= 1:
        
        # Count unique tech+port combinations
        unique_combinations = set()
            tech = ctx.tech or "unknown"
            port_cat = self._get_port_category(ctx.port)
        
        # Diversity is ratio of unique combinations to total contexts
    
        """Categorize port for clustering analysis."""
        web_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
        db_ports = [3306, 5432, 1433, 27017, 6379]
        admin_ports = [8080, 9090, 10000, 8834, 7001, 4848]
        
    
        """Assess overall recommendation quality and generate warnings."""
        warning = None
        
        # Check for entropy problems
            warning = (f"⚠️  Low recommendation diversity (entropy: {entropy_score:.2f}). "
        
        # Check for clustering problems  
            clustering_warning = (f"🔄 High clustering detected ({clustering_pct:.1f}% of recommendations "
            warning = warning + " " + clustering_warning if warning else clustering_warning
        
        # Determine overall quality
        if entropy_score >= 0.9 and clustering_pct <= 20:
            quality = "excellent"
        elif entropy_score >= 0.8 and clustering_pct <= 30:
            quality = "good"
        elif entropy_score >= 0.6 and clustering_pct <= 50:
            quality = "acceptable"
            quality = "poor"
        


# Global analyzer instance
analyzer = EntropyAnalyzer()


def analyze_entropy(context: Optional[ScoringContext] = None, 
                   days_back: int = 7) -> EntropyMetrics:
    """
    
        
    """


                    entropy_threshold: float = 0.7) -> bool:
    """
    
        
    """
    metrics = analyze_entropy(context, days_back=7)
    
    # Diversify if entropy is low AND we have enough data
            metrics.total_recommendations >= 5)