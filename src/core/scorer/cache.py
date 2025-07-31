"""Simple cache for scorer results"""

import logging
from typing import Dict, Any, Optional
import json
import hashlib
from pathlib import Path
from datetime import datetime

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
    
    def store_selection(self, usage_record: Dict[str, Any]) -> str:
        """Store selection record to contributions directory
        
        Args:
            usage_record: Dictionary containing timestamp, context, selected_wordlists, rule_matched, session_id
            
        Returns:
            Entry ID for the stored selection
        """
        from datetime import datetime
        import os
        
        contributions_dir = Path(__file__).parent.parent.parent.parent / "database" / "scorer" / "contributions" / "selections"
        
        # Ensure base directory exists
        contributions_dir.mkdir(parents=True, exist_ok=True)
        
        # Create anonymized entry from usage record
        timestamp = datetime.now()
        context = usage_record.get('context', {})
        
        # Create anonymized context for privacy
        anon_context = {
            'port_category': self._get_port_category(context.get('port', 80)),
            'port': context.get('port', 80),
            'service_fingerprint': self._generate_service_fingerprint(context),
            'service_length': len(context.get('service', '')),
            'tech_family': self._get_tech_family(context.get('tech')),
            'tech': context.get('tech'),
            'os_family': context.get('os_family'),
            'version': context.get('version'),
            'has_headers': bool(context.get('headers'))
        }
        
        # Generate scoring result from usage record
        result = {
            'score': 1.0,  # Default high score for successful selections
            'explanation': {
                'exact_match': 1.0 if context.get('tech') else 0.0,
                'tech_category': 0.9 if context.get('tech') else 0.0,
                'port_context': 0.8,
                'service_keywords': 0.5,
                'generic_fallback': 0.0
            },
            'wordlists': usage_record.get('selected_wordlists', []),
            'matched_rules': [usage_record.get('rule_matched', 'unknown')],
            'fallback_used': 'fallback' in usage_record.get('rule_matched', ''),
            'cache_key': f"{context.get('tech', 'unknown')}_{context.get('port', 80)}_{usage_record.get('session_id', 'unknown')}",
            'confidence': 'high',
            'entropy_score': None,
            'diversification_applied': False,
            'frequency_adjustments': None,
            'synergy_bonuses': None
        }
        
        # Create the complete entry
        entry = {
            'timestamp': timestamp.isoformat(),
            'context': anon_context,
            'result': result,
            'outcome': None
        }
        
        # Create date directory
        date_str = timestamp.strftime('%Y-%m-%d')
        date_dir = contributions_dir / date_str
        date_dir.mkdir(exist_ok=True)
        
        # Generate filename: tech_port_time_hash.json
        tech = context.get('tech', 'unknown')
        port = context.get('port', 80)
        time_str = timestamp.strftime('%H%M%S')
        service_hash = anon_context['service_fingerprint']
        
        filename = f"{tech}_{port}_{time_str}_{service_hash}.json"
        filepath = date_dir / filename
        
        # Write the file
        try:
            with open(filepath, 'w') as f:
                json.dump(entry, f, indent=2)
            
            # Update index
            self._update_contributions_index()
            
            entry_id = f"{date_str}_{filename[:-5]}"  # Remove .json extension
            logger.debug(f"Stored selection: {entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Failed to store selection: {e}")
            return f"error_{usage_record.get('session_id', 'unknown')}"
    
    def save_selection(self, context: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Save selection with context and result (for test compatibility)
        
        Args:
            context: Scoring context
            result: Scoring result
            
        Returns:
            Entry ID for the saved selection
        """
        # Convert to usage record format
        usage_record = {
            'timestamp': datetime.now().timestamp(),
            'context': context,
            'selected_wordlists': result.get('wordlists', []),
            'rule_matched': result.get('matched_rules', ['unknown'])[0] if result.get('matched_rules') else 'unknown',
            'session_id': result.get('cache_key', 'test_session')
        }
        
        return self.store_selection(usage_record)
    
    def get_selection(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get selection by entry ID
        
        Args:
            entry_id: Entry ID returned by store_selection/save_selection
            
        Returns:
            Selection data or None if not found
        """
        try:
            # Parse entry ID: date_tech_port_time_hash
            parts = entry_id.split('_')
            if len(parts) < 5:
                return None
                
            date_str = parts[0]
            filename = '_'.join(parts[1:]) + '.json'
            
            contributions_dir = Path(__file__).parent.parent.parent.parent / "database" / "scorer" / "contributions" / "selections"
            filepath = contributions_dir / date_str / filename
            
            if filepath.exists():
                with open(filepath, 'r') as f:
                    return json.load(f)
                    
        except Exception as e:
            logger.debug(f"Could not get selection {entry_id}: {e}")
            
        return None
    
    def _generate_service_fingerprint(self, context: Dict[str, Any]) -> str:
        """Generate anonymized service fingerprint"""
        service_data = f"{context.get('service', '')}:{context.get('tech', '')}:{context.get('version', '')}"
        return hashlib.md5(service_data.encode()).hexdigest()[:8]
    
    def _get_port_category(self, port: int) -> str:
        """Categorize port for anonymization"""
        web_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
        db_ports = [3306, 5432, 1433, 27017, 6379]
        
        if port in [80, 8080, 8000, 8888, 3000, 5000, 9000]:
            return "web"
        elif port in [443, 8443]:
            return "web_secure"
        elif port in db_ports:
            return "database"
        else:
            return "other"
    
    def _get_tech_family(self, tech: Optional[str]) -> str:
        """Categorize technology for anonymization"""
        if not tech:
            return "unknown"
            
        tech_lower = tech.lower()
        
        if tech_lower in ['wordpress', 'drupal', 'joomla']:
            return "cms"
        elif tech_lower in ['apache', 'nginx', 'iis']:
            return "web_server"
        elif tech_lower in ['mysql', 'postgres', 'mongodb']:
            return "database"
        elif tech_lower in ['jenkins', 'grafana', 'prometheus']:
            return "monitoring"
        else:
            return "other"
    
    def _update_contributions_index(self):
        """Update the contributions index file"""
        try:
            contributions_dir = Path(__file__).parent.parent.parent.parent / "database" / "scorer" / "contributions"
            index_file = contributions_dir / "index.json"
            
            # Count current selections
            selections_dir = contributions_dir / "selections"
            if not selections_dir.exists():
                return
                
            total_selections = 0
            by_tech = {}
            by_port = {'web': 0, 'database': 0, 'other': 0}
            fallback_count = 0
            
            for date_dir in selections_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                    
                for json_file in date_dir.glob("*.json"):
                    total_selections += 1
                    
                    # Extract tech from filename
                    tech = json_file.stem.split('_')[0]
                    by_tech[tech] = by_tech.get(tech, 0) + 1
                    
                    # Try to read file for port category
                    try:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                            port_cat = data.get('context', {}).get('port_category', 'other')
                            by_port[port_cat] = by_port.get(port_cat, 0) + 1
                            
                            if data.get('result', {}).get('fallback_used', False):
                                fallback_count += 1
                    except:
                        by_port['other'] += 1
            
            # Create index data
            index_data = {
                'total_selections': total_selections,
                'by_tech': by_tech,
                'by_port': by_port,
                'fallback_usage': {
                    'count': fallback_count,
                    'percentage': round((fallback_count / total_selections * 100), 2) if total_selections > 0 else 0
                },
                'last_updated': datetime.now().isoformat()
            }
            
            # Write index file
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Could not update contributions index: {e}")

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