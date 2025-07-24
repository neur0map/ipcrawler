"""
Wordlist resolver that integrates SecLists catalog with the scorer system.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime

from .models import WordlistCatalog, WordlistEntry, WordlistFilter, WordlistCategory

logger = logging.getLogger(__name__)


class WordlistResolver:
    """Resolves wordlist recommendations to actual file paths using SecLists catalog."""
    
    def __init__(self, catalog_path: Optional[Path] = None):
        """
        Initialize wordlist resolver.
        
        Args:
            catalog_path: Path to catalog JSON file. If None, uses default location.
        """
        if catalog_path is None:
            # Default catalog location
            project_root = Path(__file__).parent.parent.parent
            self.catalog_path = project_root / "database" / "wordlists" / "seclists_catalog.json"
        else:
            self.catalog_path = Path(catalog_path)
        
        self.catalog: Optional[WordlistCatalog] = None
        self.catalog_loaded_at: Optional[datetime] = None
        
        # Load catalog
        self._load_catalog()
    
    def _load_catalog(self) -> bool:
        """Load wordlist catalog from JSON file."""
        try:
            if not self.catalog_path.exists():
                logger.warning(f"Catalog not found at {self.catalog_path}")
                return False
            
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
            
            self.catalog = WordlistCatalog(**catalog_data)
            self.catalog_loaded_at = datetime.utcnow()
            
            logger.info(f"Loaded catalog with {len(self.catalog.wordlists)} wordlists")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            self.catalog = None
            return False
    
    def is_available(self) -> bool:
        """Check if catalog is available and loaded."""
        return self.catalog is not None
    
    def reload_catalog(self) -> bool:
        """Reload catalog from disk."""
        return self._load_catalog()
    
    def resolve_scorer_recommendations(self, 
                                     scorer_wordlists: List[str],
                                     tech: Optional[str] = None,
                                     port: Optional[int] = None,
                                     max_results: int = 10) -> List[WordlistEntry]:
        """
        Resolve scorer wordlist recommendations to actual WordlistEntry objects.
        
        Args:
            scorer_wordlists: List of wordlist names from scorer
            tech: Technology context for relevance scoring
            port: Port context for relevance scoring
            max_results: Maximum number of results to return
            
        Returns:
            List of WordlistEntry objects sorted by relevance
        """
        if not self.catalog:
            logger.debug("Catalog not available - cannot resolve wordlists")
            return []
        
        resolved_entries = []
        
        for wordlist_name in scorer_wordlists:
            # Try exact match first
            if wordlist_name in self.catalog.wordlists:
                resolved_entries.append(self.catalog.wordlists[wordlist_name])
                continue
            
            # Try fuzzy matching for similar names
            fuzzy_matches = self._fuzzy_match_wordlist(wordlist_name)
            resolved_entries.extend(fuzzy_matches[:2])  # Top 2 fuzzy matches
        
        # Score and rank entries
        scored_entries = []
        for entry in resolved_entries:
            relevance_score = entry.get_relevance_score(tech, port)
            scored_entries.append((entry, relevance_score))
        
        # Sort by relevance score (descending)
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
        return [entry for entry, score in scored_entries[:max_results]]
    
    def _fuzzy_match_wordlist(self, wordlist_name: str) -> List[WordlistEntry]:
        """Find wordlists with similar names."""
        if not self.catalog:
            return []
        
        # Remove common extensions and normalize
        clean_name = wordlist_name.lower().replace('.txt', '').replace('-', '').replace('_', '')
        
        matches = []
        for entry in self.catalog.wordlists.values():
            entry_clean = entry.name.lower().replace('.txt', '').replace('-', '').replace('_', '')
            
            # Check for substring matches
            if clean_name in entry_clean or entry_clean in clean_name:
                matches.append(entry)
            
            # Check tags for matches
            elif any(clean_name in tag or tag in clean_name for tag in entry.tags):
                matches.append(entry)
        
        return matches
    
    def get_wordlists_for_context(self,
                                tech: Optional[str] = None,
                                port: Optional[int] = None,
                                category: Optional[WordlistCategory] = None,
                                min_quality: Optional[str] = None,
                                max_results: int = 10) -> List[WordlistEntry]:
        """
        Get wordlists for specific context without scorer input.
        
        Args:
            tech: Technology filter
            port: Port filter  
            category: Category filter
            min_quality: Minimum quality filter
            max_results: Maximum results to return
            
        Returns:
            List of relevant WordlistEntry objects
        """
        if not self.catalog:
            return []
        
        # Build filter
        filters = WordlistFilter()
        
        if tech:
            filters.tech_compatibility = [tech]
        
        if port:
            filters.port_compatibility = [port]
        
        if category:
            filters.categories = [category]
        
        if min_quality:
            from .models import WordlistQuality
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
        for entry in results:
            relevance_score = entry.get_relevance_score(tech, port)
            scored_results.append((entry, relevance_score))
        
        # Sort and return
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, score in scored_results[:max_results]]
    
    def get_wordlists_by_category(self, category: WordlistCategory, limit: int = 20) -> List[WordlistEntry]:
        """Get wordlists by category."""
        if not self.catalog:
            return []
        
        return self.catalog.get_by_category(category)[:limit]
    
    def get_wordlists_by_tech(self, tech: str, limit: int = 20) -> List[WordlistEntry]:
        """Get wordlists by technology."""
        if not self.catalog:
            return []
        
        return self.catalog.get_by_tech(tech)[:limit]
    
    def get_wordlists_by_port(self, port: int, limit: int = 20) -> List[WordlistEntry]:
        """Get wordlists by port."""
        if not self.catalog:
            return []
        
        return self.catalog.get_by_port(port)[:limit]
    
    def search_wordlists(self, query: str, max_results: int = 20) -> List[WordlistEntry]:
        """
        Search wordlists by query string.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of matching WordlistEntry objects
        """
        if not self.catalog:
            return []
        
        query_lower = query.lower()
        matches = []
        
        for entry in self.catalog.wordlists.values():
            score = 0.0
            
            # Name matches (highest weight)
            if query_lower in entry.name.lower():
                score += 10.0
            
            # Display name matches
            if query_lower in entry.display_name.lower():
                score += 8.0
            
            # Tag matches
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 5.0
            
            # Description matches
            if query_lower in entry.description.lower():
                score += 3.0
            
            # Technology matches
            for tech in entry.tech_compatibility:
                if query_lower in tech.lower():
                    score += 6.0
            
            if score > 0:
                matches.append((entry, score))
        
        # Sort by score and return
        matches.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, score in matches[:max_results]]
    
    def get_catalog_stats(self) -> Dict:
        """Get catalog statistics."""
        if not self.catalog:
            return {"error": "Catalog not available"}
        
        stats = self.catalog.get_stats()
        stats['catalog_loaded_at'] = self.catalog_loaded_at.isoformat() if self.catalog_loaded_at else None
        stats['catalog_path'] = str(self.catalog_path)
        
        return stats
    
    def validate_wordlist_paths(self) -> Dict[str, List[str]]:
        """
        Validate that wordlist files actually exist.
        
        Returns:
            Dict with 'found' and 'missing' lists
        """
        if not self.catalog:
            return {"error": "Catalog not available"}
        
        found = []
        missing = []
        
        for entry in self.catalog.wordlists.values():
            if Path(entry.full_path).exists():
                found.append(entry.name)
            else:
                missing.append(entry.name)
        
        return {
            "found": found,
            "missing": missing,
            "total": len(self.catalog.wordlists),
            "missing_count": len(missing),
            "found_count": len(found)
        }
    
    def get_top_wordlists(self, category: Optional[WordlistCategory] = None, 
                         limit: int = 10) -> List[WordlistEntry]:
        """
        Get top wordlists by quality and scorer weight.
        
        Args:
            category: Optional category filter
            limit: Number of results to return
            
        Returns:
            List of top-rated wordlists
        """
        if not self.catalog:
            return []
        
        wordlists = list(self.catalog.wordlists.values())
        
        # Filter by category if specified
        if category:
            wordlists = [wl for wl in wordlists if wl.category == category]
        
        # Score by combined quality and scorer weight
        scored_wordlists = []
        for wl in wordlists:
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
            scored_wordlists.append((wl, combined_score))
        
        # Sort and return
        scored_wordlists.sort(key=lambda x: x[1], reverse=True)
        return [wl for wl, score in scored_wordlists[:limit]]


# Global resolver instance
resolver = WordlistResolver()


def get_wordlists_for_context(tech: Optional[str] = None,
                            port: Optional[int] = None,
                            category: Optional[WordlistCategory] = None,
                            max_results: int = 10) -> List[WordlistEntry]:
    """Convenience function to get wordlists for context."""
    return resolver.get_wordlists_for_context(tech, port, category, max_results=max_results)


def resolve_scorer_recommendations(scorer_wordlists: List[str],
                                 tech: Optional[str] = None,
                                 port: Optional[int] = None,
                                 max_results: int = 10) -> List[WordlistEntry]:
    """Convenience function to resolve scorer recommendations."""
    return resolver.resolve_scorer_recommendations(scorer_wordlists, tech, port, max_results)