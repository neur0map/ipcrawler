"""
Cache system for tracking wordlist selections and outcomes.
"""

import json
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import logging

from .models import CacheEntry, CacheIndex, ScoringContext, ScoringResult, AnonymizedCacheEntry, AnonymizedScoringContext

logger = logging.getLogger(__name__)


class ScorerCache:
    """Cache manager for scoring results and outcomes."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Cache directory path. If None, uses default.
        """
        if cache_dir is None:
            # Default to database/scorer/contributions
            project_root = Path(__file__).parent.parent.parent.parent
            self.cache_dir = project_root / "database" / "scorer" / "contributions"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.selections_dir = self.cache_dir / "selections"
        self.index_file = self.cache_dir / "index.json"
        
        # Ensure directories exist
        self.cache_dir.mkdir(exist_ok=True)
        self.selections_dir.mkdir(exist_ok=True)
        
        # Load or create index
        self.index = self._load_index()
    
    def _load_index(self) -> CacheIndex:
        """Load cache index from file or create new one."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    data = json.load(f)
                    return CacheIndex(**data)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                return CacheIndex()
        else:
            return CacheIndex()
    
    def _save_index(self):
        """Save cache index to file."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index.model_dump(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")
    
    def _get_date_dir(self, timestamp: datetime) -> Path:
        """Get directory for a specific date."""
        date_str = timestamp.strftime("%Y-%m-%d")
        return self.selections_dir / date_str
    
    def _generate_filename(self, context: AnonymizedScoringContext, timestamp: datetime) -> str:
        """Generate privacy-safe filename for cache entry."""
        time_str = timestamp.strftime("%H%M%S")
        tech_family = context.tech_family.replace("/", "_").replace(" ", "_")
        return f"{tech_family}_{context.port_category}_{time_str}_{context.service_fingerprint}.json"
    
    def save_selection(self, context: ScoringContext, result: ScoringResult, 
                      outcome: Optional[Dict[str, Any]] = None) -> str:
        """
        Save a wordlist selection to cache with privacy protection.
        
        Args:
            context: Scoring context (will be anonymized)
            result: Scoring result
            outcome: Optional outcome data (findings, success, etc.)
            
        Returns:
            Cache entry ID
        """
        timestamp = datetime.utcnow()
        
        # Create regular cache entry first
        entry = CacheEntry(
            timestamp=timestamp,
            context=context,
            result=result,
            outcome=outcome
        )
        
        # Convert to anonymized version for storage
        anon_entry = AnonymizedCacheEntry.from_cache_entry(entry)
        
        # Create date directory
        date_dir = self._get_date_dir(timestamp)
        date_dir.mkdir(exist_ok=True)
        
        # Generate filename using anonymized context
        filename = self._generate_filename(anon_entry.context, timestamp)
        file_path = date_dir / filename
        
        # Save anonymized entry
        try:
            with open(file_path, 'w') as f:
                json.dump(anon_entry.model_dump(), f, indent=2, default=str)
            
            # Update index with original entry for stats
            self.index.update_stats(entry)
            self._save_index()
            
            entry_id = f"{timestamp.strftime('%Y-%m-%d')}/{filename}"
            logger.debug(f"Saved anonymized cache entry: {entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Failed to save cache entry: {e}")
            raise
    
    def get_selection(self, entry_id: str) -> Optional[AnonymizedCacheEntry]:
        """
        Get a cached selection by ID.
        
        Args:
            entry_id: Cache entry ID (date/filename)
            
        Returns:
            AnonymizedCacheEntry if found, None otherwise
        """
        try:
            file_path = self.selections_dir / entry_id
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Handle both old and new formats
                if 'context' in data and 'target' in data['context']:
                    # Old format - convert to anonymized
                    old_entry = CacheEntry(**data)
                    return AnonymizedCacheEntry.from_cache_entry(old_entry)
                else:
                    # New anonymized format
                    return AnonymizedCacheEntry(**data)
                
        except Exception as e:
            logger.error(f"Failed to load cache entry {entry_id}: {e}")
            return None
    
    def update_outcome(self, entry_id: str, outcome: Dict[str, Any]) -> bool:
        """
        Update the outcome for a cached selection.
        
        Args:
            entry_id: Cache entry ID
            outcome: Outcome data to add/update
            
        Returns:
            True if successful, False otherwise
        """
        entry = self.get_selection(entry_id)
        if not entry:
            return False
        
        # Update outcome
        if entry.outcome:
            entry.outcome.update(outcome)
        else:
            entry.outcome = outcome
        
        # Save back to file
        try:
            file_path = self.selections_dir / entry_id
            with open(file_path, 'w') as f:
                json.dump(entry.model_dump(), f, indent=2, default=str)
            
            logger.debug(f"Updated outcome for {entry_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update outcome for {entry_id}: {e}")
            return False
    
    def search_selections(self, 
                         tech: Optional[str] = None,
                         port: Optional[int] = None,
                         days_back: int = 30,
                         limit: int = 100) -> List[AnonymizedCacheEntry]:
        """
        Search cached selections by criteria.
        
        Args:
            tech: Technology filter
            port: Port filter
            days_back: How many days back to search
            limit: Maximum results to return
            
        Returns:
            List of matching CacheEntry objects
        """
        results = []
        cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).date()
        
        # Iterate through date directories
        for date_dir in sorted(self.selections_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            
            try:
                dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d").date()
                if dir_date < cutoff_date:
                    break  # Too old
            except ValueError:
                continue  # Invalid date format
            
            # Search files in this date
            for file_path in date_dir.glob("*.json"):
                if len(results) >= limit:
                    break
                
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        # Handle both old and new formats
                        if 'context' in data and 'target' in data['context']:
                            # Old format - convert to anonymized
                            old_entry = CacheEntry(**data)
                            entry = AnonymizedCacheEntry.from_cache_entry(old_entry)
                        else:
                            # New anonymized format
                            entry = AnonymizedCacheEntry(**data)
                    
                    # Apply filters
                    if tech and (not entry.context.tech or entry.context.tech != tech):
                        continue
                    
                    if port and entry.context.port != port:
                        continue
                    
                    results.append(entry)
                    
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")
                    continue
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        return {
            "index": self.index.model_dump(),
            "cache_dir": str(self.cache_dir),
            "total_files": sum(1 for _ in self.selections_dir.rglob("*.json")),
            "date_directories": len([d for d in self.selections_dir.iterdir() if d.is_dir()])
        }
    
    def get_successful_patterns(self, min_findings: int = 5) -> List[Dict[str, Any]]:
        """
        Get patterns of successful wordlist selections.
        
        Args:
            min_findings: Minimum findings to consider successful
            
        Returns:
            List of successful pattern summaries
        """
        patterns = []
        
        # Search recent successful entries
        entries = self.search_selections(days_back=90, limit=500)
        
        for entry in entries:
            if not entry.outcome:
                continue
            
            findings = entry.outcome.get("findings", 0)
            if findings >= min_findings:
                patterns.append({
                    "tech": entry.context.tech,
                    "port": entry.context.port,
                    "service": entry.context.service[:50],
                    "wordlists_used": entry.outcome.get("wordlists_used", []),
                    "findings": findings,
                    "score": entry.result.score,
                    "rules": entry.result.matched_rules,
                    "timestamp": entry.timestamp
                })
        
        # Sort by findings (most successful first)
        patterns.sort(key=lambda x: x["findings"], reverse=True)
        
        return patterns
    
    def cleanup_old_entries(self, days_to_keep: int = 90):
        """
        Clean up old cache entries.
        
        Args:
            days_to_keep: Number of days to keep
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days_to_keep)).date()
        removed_count = 0
        
        for date_dir in self.selections_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            try:
                dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d").date()
                if dir_date < cutoff_date:
                    # Remove entire directory
                    import shutil
                    shutil.rmtree(date_dir)
                    removed_count += 1
                    logger.info(f"Removed old cache directory: {date_dir.name}")
            except ValueError:
                continue
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old cache directories")


# Global cache instance
cache = ScorerCache()


def cache_selection(context: ScoringContext, result: ScoringResult, 
                   outcome: Optional[Dict[str, Any]] = None) -> str:
    """
    Convenience function to cache a selection.
    
    Args:
        context: Scoring context
        result: Scoring result
        outcome: Optional outcome data
        
    Returns:
        Cache entry ID
    """
    return cache.save_selection(context, result, outcome)