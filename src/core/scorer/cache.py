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