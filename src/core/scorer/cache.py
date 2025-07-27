"""Simple cache for scorer results"""

import logging
from typing import Dict, Any, Optional
import json
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleCache:
    """Cache manager for scoring results and outcomes."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache"""
        self._cache[key] = value
    
    def clear(self) -> None:
        """Clear cache"""
        self._cache.clear()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def search_selections(self, days_back: int = 30, limit: int = 100):
        """Search for recent selections from contributions directory"""
        from datetime import datetime, timedelta
        import json
        import os
        
        selections = []
        contributions_dir = Path(__file__).parent.parent.parent.parent / "database" / "scorer" / "contributions" / "selections"
        
        if not contributions_dir.exists():
            return []
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Iterate through date directories
        for date_dir in sorted(contributions_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
                
            # Parse date from directory name
            try:
                dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                if dir_date < cutoff_date:
                    break
            except ValueError:
                continue
            
            # Read JSON files in this date directory
            for json_file in date_dir.glob("*.json"):
                if len(selections) >= limit:
                    break
                    
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        
                    # Extract relevant fields for audit
                    selection = {
                        'timestamp': data.get('timestamp'),
                        'rule_matched': data.get('result', {}).get('matched_rules', ['unknown'])[0],
                        'selected_wordlists': data.get('result', {}).get('wordlists', []),
                        'context': data.get('context', {}),
                        'score': data.get('result', {}).get('score', 0)
                    }
                    selections.append(selection)
                    
                except Exception as e:
                    logger.warning(f"Failed to read {json_file}: {e}")
                    continue
        
        return selections[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics from contributions directory"""
        contributions_dir = Path(__file__).parent.parent.parent.parent / "database" / "scorer" / "contributions" / "selections"
        
        if not contributions_dir.exists():
            return {
                'total_files': 0,
                'date_directories': 0,
                'cache_size': len(self._cache)
            }
        
        total_files = 0
        date_dirs = 0
        
        for date_dir in contributions_dir.iterdir():
            if date_dir.is_dir():
                date_dirs += 1
                total_files += len(list(date_dir.glob("*.json")))
        
        return {
            'total_files': total_files,
            'date_directories': date_dirs,
            'cache_size': len(self._cache)
        }


# Global cache instance
cache = SimpleCache()


def cache_selection(func):
    """Decorator to cache function results"""
    def wrapper(*args, **kwargs):
        key = cache._generate_key(*args, **kwargs)
        result = cache.get(key)
        
        if result is None:
            result = func(*args, **kwargs)
            cache.set(key, result)
        
        return result
    
    return wrapper