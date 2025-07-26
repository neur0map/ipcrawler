"""
"""



logger = logging.getLogger(__name__)


    """Resolves wordlist recommendations to actual file paths using SecLists catalog."""
    
    def __init__(self, catalog_path: Optional[Path] = None):
        """
        
        """
            # Default catalog location
            project_root = Path(__file__).parent.parent.parent.parent.parent
            self.catalog_path = project_root / "database" / "wordlists" / "seclists_catalog.json"
            self.catalog_path = Path(catalog_path)
        
        self.catalog: Optional[WordlistCatalog] = None
        self.catalog_loaded_at: Optional[datetime] = None
        
    
        """Load wordlist catalog from JSON file."""
            
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
            
            self.catalog = WordlistCatalog(**catalog_data)
            self.catalog_loaded_at = datetime.utcnow()
            
            
            self.catalog = None
    
        """Check if catalog is available and loaded."""
    
        """Reload catalog from disk."""
    
                                     tech: Optional[str] = None,
                                     port: Optional[int] = None,
                                     max_results: int = 10) -> List[WordlistEntry]:
        """
        
            
        """
        
        resolved_entries = []
        
            # Try exact match first
            
            # Try fuzzy matching for similar names
            fuzzy_matches = self._fuzzy_match_wordlist(wordlist_name)
        
        # Score and rank entries
        scored_entries = []
            relevance_score = entry.get_relevance_score(tech, port)
        
        # Sort by relevance score (descending)
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
    
        """Find wordlists with similar names."""
        
        # Remove common extensions and normalize
        clean_name = wordlist_name.lower().replace('.txt', '').replace('-', '').replace('_', '')
        
        matches = []
            entry_clean = entry.name.lower().replace('.txt', '').replace('-', '').replace('_', '')
            
            # Check for substring matches
            
            # Check tags for matches
        
    
                                tech: Optional[str] = None,
                                port: Optional[int] = None,
                                category: Optional[WordlistCategory] = None,
                                min_quality: Optional[str] = None,
                                max_results: int = 10) -> List[WordlistEntry]:
        """
        
            
        """
        
        # Build filter
        filters = WordlistFilter()
        
            filters.tech_compatibility = [tech]
        
            filters.port_compatibility = [port]
        
            filters.categories = [category]
        
            quality_map = {
                'basic': WordlistQuality.BASIC,
                'average': WordlistQuality.AVERAGE,
                'good': WordlistQuality.GOOD,
                'excellent': WordlistQuality.EXCELLENT
            }
            filters.min_quality = quality_map.get(min_quality.lower())
        
        # Search catalog
        results = self.catalog.search(filters)
        
        # Score by relevance
        scored_results = []
            relevance_score = entry.get_relevance_score(tech, port)
        
        # Sort and return
        scored_results.sort(key=lambda x: x[1], reverse=True)
    
    def get_wordlists_by_category(self, category: WordlistCategory, limit: int = 20) -> List[WordlistEntry]:
        """Get wordlists by category."""
        
    
    def get_wordlists_by_tech(self, tech: str, limit: int = 20) -> List[WordlistEntry]:
        """Get wordlists by technology."""
        
    
    def get_wordlists_by_port(self, port: int, limit: int = 20) -> List[WordlistEntry]:
        """Get wordlists by port."""
        
    
    def search_wordlists(self, query: str, max_results: int = 20) -> List[WordlistEntry]:
        """
        
            
        """
        
        query_lower = query.lower()
        matches = []
        
            score = 0.0
            
            # Name matches (highest weight)
                score += 10.0
            
            # Display name matches
                score += 8.0
            
            # Tag matches
                    score += 5.0
            
            # Description matches
                score += 3.0
            
            # Technology matches
                    score += 6.0
            
        
        # Sort by score and return
        matches.sort(key=lambda x: x[1], reverse=True)
    
        """Get catalog statistics."""
        
        stats = self.catalog.get_stats()
        stats['catalog_loaded_at'] = self.catalog_loaded_at.isoformat() if self.catalog_loaded_at else None
        stats['catalog_path'] = str(self.catalog_path)
        
    
        """
        
        """
        
        found = []
        missing = []
        
        
            "found": found,
            "missing": missing,
            "total": len(self.catalog.wordlists),
            "missing_count": len(missing),
            "found_count": len(found)
        }
    
    def get_top_wordlists(self, category: Optional[WordlistCategory] = None, 
                         limit: int = 10) -> List[WordlistEntry]:
        """
        
            
        """
        
        wordlists = list(self.catalog.wordlists.values())
        
        # Filter by category if specified
            wordlists = [wl for wl in wordlists if wl.category == category]
        
        # Score by combined quality and scorer weight
        scored_wordlists = []
            # Quality scoring
            quality_scores = {
                'excellent': 4,
                'good': 3,
                'average': 2,
                'basic': 1,
                'unknown': 0
            }
            quality_score = quality_scores.get(wl.quality.value, 0)
            
            # Combined score
            combined_score = (quality_score * 0.5) + (wl.scorer_weight * 0.5)
        
        # Sort and return
        scored_wordlists.sort(key=lambda x: x[1], reverse=True)


# Global resolver instance
resolver = WordlistResolver()


def get_wordlists_for_context(tech: Optional[str] = None,
                            port: Optional[int] = None,
                            category: Optional[WordlistCategory] = None,
                            max_results: int = 10) -> List[WordlistEntry]:
    """Convenience function to get wordlists for context."""
    return resolver.get_wordlists_for_context(tech, port, category, max_results=max_results)


                                 tech: Optional[str] = None,
                                 port: Optional[int] = None,
                                 max_results: int = 10) -> List[WordlistEntry]:
    """Convenience function to resolve scorer recommendations."""
