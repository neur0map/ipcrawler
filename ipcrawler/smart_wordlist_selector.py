"""
Smart Wordlist Selector for ipcrawler

Provides intelligent wordlist selection based on detected technologies
using pre-generated SecLists catalog and technology alias mapping.
"""

import os
import yaml
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

# Module-level cache for performance
_catalog_cache: Optional[Dict] = None
_aliases_cache: Optional[Dict] = None


class SmartWordlistSelector:
    """Intelligent wordlist selection based on technology detection"""
    
    def __init__(self, seclists_base_path: str):
        self.seclists_base_path = seclists_base_path
        self._load_catalog()
        self._load_aliases()
    
    def _load_catalog(self):
        """Load SecLists catalog from cache or file"""
        global _catalog_cache
        
        if _catalog_cache is not None:
            self.catalog = _catalog_cache
            return
        
        # Look for catalog in multiple locations
        catalog_paths = [
            os.path.join(os.path.dirname(__file__), 'data', 'seclists_catalog.yaml'),
            os.path.join(os.path.dirname(__file__), '..', 'data', 'seclists_catalog.yaml'),
            'seclists_catalog.yaml'  # Current directory
        ]
        
        for catalog_path in catalog_paths:
            if os.path.exists(catalog_path):
                try:
                    with open(catalog_path, 'r') as f:
                        _catalog_cache = yaml.safe_load(f)
                    self.catalog = _catalog_cache
                    return
                except Exception as e:
                    print(f"Warning: Could not load catalog from {catalog_path}: {e}")
        
        # No catalog found - try to auto-generate it
        print("⚠️  No SecLists catalog found for smart wordlist selection.")
        if self.seclists_base_path and os.path.exists(self.seclists_base_path):
            print(f"🤖 Auto-generating catalog for {self.seclists_base_path}...")
            try:
                catalog = self._generate_catalog_on_demand()
                if catalog:
                    _catalog_cache = catalog
                    self.catalog = _catalog_cache
                    print("✅ Catalog generated successfully!")
                    return
            except Exception as e:
                print(f"❌ Auto-generation failed: {e}")
        
        print("   Falling back to standard wordlist selection.")
        _catalog_cache = {'wordlists': {}}
        self.catalog = _catalog_cache
    
    def _load_aliases(self):
        """Load technology aliases from cache or file"""
        global _aliases_cache
        
        if _aliases_cache is not None:
            self.aliases = _aliases_cache
            return
        
        aliases_path = os.path.join(os.path.dirname(__file__), 'data', 'technology_aliases.yaml')
        
        try:
            with open(aliases_path, 'r') as f:
                _aliases_cache = yaml.safe_load(f)
            self.aliases = _aliases_cache
        except Exception as e:
            print(f"Warning: Could not load aliases from {aliases_path}: {e}")
            # Minimal fallback aliases
            _aliases_cache = {
                'technology_aliases': {
                    'wordpress': {'aliases': ['wordpress', 'wp'], 'priority': 'high'},
                    'php': {'aliases': ['php'], 'priority': 'medium'}
                },
                'scoring': {'alias_match_weight': 0.7, 'size_penalty_weight': 0.3, 'max_lines_threshold': 100000}
            }
            self.aliases = _aliases_cache
    
    def select_wordlist(self, category: str, detected_technologies: Set[str]) -> Optional[str]:
        """
        Select best wordlist for category based on detected technologies
        
        Args:
            category: Wordlist category (e.g., 'web_directories', 'web_files')
            detected_technologies: Set of detected technology strings
            
        Returns:
            Full path to selected wordlist, or None if no good match found
        """
        if not detected_technologies or not self.catalog.get('wordlists'):
            return None
        
        # Find best technology match using alias mapping
        best_tech = self._find_best_technology_match(detected_technologies)
        if not best_tech:
            return None
        
        # Get candidate wordlists for this technology
        candidates = self._get_candidate_wordlists(best_tech, category)
        if not candidates:
            return None
        
        # Score and select best candidate
        best_wordlist = self._score_and_select_candidates(candidates, best_tech)
        if not best_wordlist:
            return None
        
        # Return full path
        full_path = os.path.join(self.seclists_base_path, best_wordlist)
        return full_path if os.path.exists(full_path) else None
    
    def _find_best_technology_match(self, detected_technologies: Set[str]) -> Optional[str]:
        """Find best technology match using RapidFuzz on aliases"""
        try:
            from rapidfuzz import process, fuzz
        except ImportError:
            print("🔧 RapidFuzz not available - install with: pip install rapidfuzz")
            print("   ↳ Falling back to simple string matching (still functional)")
            return self._simple_technology_match(detected_technologies)
        
        tech_aliases = self.aliases.get('technology_aliases', {})
        best_match = None
        best_score = 0
        
        for tech_key, tech_config in tech_aliases.items():
            aliases = tech_config.get('aliases', [])
            
            # Check each detected technology against this tech's aliases
            for detected in detected_technologies:
                # Find best alias match for this detected technology
                alias_match = process.extractOne(
                    detected.lower(),
                    [alias.lower() for alias in aliases],
                    scorer=fuzz.partial_ratio,
                    score_cutoff=70
                )
                
                if alias_match:
                    score = alias_match[1] / 100.0  # Convert to 0-1 range
                    
                    # Apply priority bonus
                    priority = tech_config.get('priority', 'medium')
                    priority_bonus = self.aliases.get('scoring', {}).get('priority_bonus', {}).get(priority, 0)
                    final_score = score + priority_bonus
                    
                    if final_score > best_score:
                        best_score = final_score
                        best_match = tech_key
        
        return best_match if best_score > 0.6 else None
    
    def _simple_technology_match(self, detected_technologies: Set[str]) -> Optional[str]:
        """Fallback simple string matching when RapidFuzz unavailable"""
        tech_aliases = self.aliases.get('technology_aliases', {})
        
        for tech_key, tech_config in tech_aliases.items():
            aliases = tech_config.get('aliases', [])
            
            for detected in detected_technologies:
                for alias in aliases:
                    if alias.lower() in detected.lower() or detected.lower() in alias.lower():
                        return tech_key
        
        return None
    
    def _get_candidate_wordlists(self, technology: str, category: str) -> List[Tuple[str, Dict]]:
        """Get candidate wordlists for technology and category"""
        candidates = []
        
        # Get wordlists that contain the technology name in their path/filename
        for wordlist_path, wordlist_info in self.catalog['wordlists'].items():
            path_lower = wordlist_path.lower()
            
            # Check if wordlist is relevant to this technology
            if technology in path_lower or any(tag == technology for tag in wordlist_info.get('tags', [])):
                # Check if wordlist is appropriate for the category
                if self._is_appropriate_category(wordlist_info, category):
                    candidates.append((wordlist_path, wordlist_info))
        
        return candidates
    
    def _is_appropriate_category(self, wordlist_info: Dict, category: str) -> bool:
        """Check if wordlist is appropriate for the requested category"""
        wordlist_category = wordlist_info.get('category', 'other')
        
        # Category mapping
        category_mapping = {
            'web_directories': ['web'],
            'web_files': ['web'],
            'usernames': ['usernames'],
            'passwords': ['passwords'],
            'subdomains': ['dns'],
            'vhosts': ['dns'],
            'snmp_communities': ['snmp']
        }
        
        appropriate_categories = category_mapping.get(category, ['other'])
        return wordlist_category in appropriate_categories
    
    def _score_and_select_candidates(self, candidates: List[Tuple[str, Dict]], technology: str) -> Optional[str]:
        """Score candidates and select the best one"""
        if not candidates:
            return None
        
        scoring_config = self.aliases.get('scoring', {})
        alias_weight = scoring_config.get('alias_match_weight', 0.7)
        size_weight = scoring_config.get('size_penalty_weight', 0.3)
        max_lines = scoring_config.get('max_lines_threshold', 100000)
        
        scored_candidates = []
        
        for wordlist_path, wordlist_info in candidates:
            # Alias match score (how well the filename matches the technology)
            alias_score = self._calculate_alias_score(wordlist_path, technology)
            
            # Smart size handling - avoid tiny wordlists for directory enumeration
            lines = wordlist_info.get('lines', 0)
            size_score = self._calculate_size_score(wordlist_path, lines)
            
            # Final score
            final_score = (alias_score * alias_weight) + (size_score * size_weight)
            
            scored_candidates.append((final_score, wordlist_path, wordlist_info))
        
        # Sort by score (descending) and return best
        scored_candidates.sort(reverse=True)
        
        if scored_candidates and scored_candidates[0][0] > 0.3:  # Minimum score threshold
            return scored_candidates[0][1]
        
        return None
    
    def _calculate_size_score(self, wordlist_path: str, lines: int) -> float:
        """Calculate size score - prefer comprehensive wordlists for directory enumeration"""
        path_lower = wordlist_path.lower()
        
        # For directory/web enumeration, we want comprehensive but reasonable wordlists
        if any(term in path_lower for term in ['web-content', 'discovery', 'directory', 'file']):
            # Penalize tiny wordlists heavily for directory enumeration
            if lines < 100:
                return -0.5  # Heavy penalty for tiny lists like joomla-themes.fuzz.txt (30 lines)
            elif lines < 1000:
                return 0.0   # Neutral for small lists
            elif lines < 10000:
                return 0.3   # Good for medium lists
            elif lines < 20000:
                return 0.5   # Best for comprehensive lists (sweet spot)
            else:
                return -0.3  # Penalty for massive wordlists (>20K lines) - too slow
        
        # For other categories (usernames, passwords), prefer smaller targeted lists
        else:
            if lines > 50000:
                return -0.2  # Penalty for huge lists
            elif lines > 10000:
                return 0.0   # Neutral for large lists
            elif lines > 1000:
                return 0.3   # Good for medium lists
            else:
                return 0.5   # Best for small targeted lists
    
    def _calculate_alias_score(self, wordlist_path: str, technology: str) -> float:
        """Calculate how well wordlist path matches technology"""
        path_lower = wordlist_path.lower()
        tech_lower = technology.lower()
        filename = os.path.basename(path_lower)
        
        # Penalize overly specific wordlists for general directory enumeration
        if any(term in filename for term in ['themes', 'plugins', 'extensions', 'modules']):
            # These are too specific for general directory busting
            if any(term in path_lower for term in ['web-content', 'discovery']):
                return 0.2  # Low score for overly specific lists
        
        # Exact match in filename
        if tech_lower in filename:
            # Prefer general wordlists over specific ones
            if any(term in filename for term in ['all-levels', 'comprehensive', 'full']):
                return 1.0  # Best for comprehensive lists
            elif not any(term in filename for term in ['theme', 'plugin', 'extension']):
                return 0.9  # Good for general technology lists
            else:
                return 0.3  # Lower for specific component lists
        
        # Match in directory path
        if tech_lower in path_lower:
            return 0.8
        
        # Partial matches
        tech_aliases = self.aliases.get('technology_aliases', {}).get(technology, {}).get('aliases', [])
        for alias in tech_aliases:
            if alias.lower() in path_lower:
                return 0.7
        
        return 0.0
    
    def get_selection_info(self, wordlist_path: str, technology: str) -> str:
        """Get human-readable info about wordlist selection"""
        if not wordlist_path:
            return "No technology-specific wordlist found"
        
        filename = os.path.basename(wordlist_path)
        wordlist_info = self.catalog['wordlists'].get(
            os.path.relpath(wordlist_path, self.seclists_base_path), {}
        )
        
        lines = wordlist_info.get('lines', 'unknown')
        size_kb = wordlist_info.get('size_kb', 'unknown')
        
        return f"Using {technology} wordlist: {filename} ({lines} lines, {size_kb}KB)"
    
    def _generate_catalog_on_demand(self) -> Optional[Dict]:
        """Generate catalog on-demand when not found"""
        from datetime import datetime
        
        catalog = {
            'metadata': {
                'generator_version': '1.0',
                'seclists_path': self.seclists_base_path,
                'generated_at': datetime.now().isoformat(),
                'total_wordlists': 0
            },
            'wordlists': {}
        }
        
        print(f"🔍 Scanning SecLists directory: {self.seclists_base_path}")
        
        # Walk through all .txt files in SecLists
        wordlist_count = 0
        for root, dirs, files in os.walk(self.seclists_base_path):
            for file in files:
                if file.endswith('.txt') or file.endswith('.fuzz.txt'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.seclists_base_path)
                    
                    # Get file statistics
                    try:
                        stat = os.stat(full_path)
                        size_kb = stat.st_size // 1024
                        
                        # Count lines efficiently (limit to avoid hanging on huge files)
                        line_count = 0
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, _ in enumerate(f):
                                if i > 500000:  # Cap at 500k lines for performance
                                    line_count = f">{i}"
                                    break
                                line_count = i + 1
                        
                        # Categorize wordlist based on path
                        category = self._categorize_wordlist(relative_path)
                        
                        # Extract tags from path/filename
                        tags = self._extract_tags(relative_path.lower())
                        
                        catalog['wordlists'][relative_path] = {
                            'size_kb': size_kb,
                            'lines': line_count,
                            'category': category,
                            'tags': tags
                        }
                        
                        wordlist_count += 1
                        if wordlist_count % 100 == 0:
                            print(f"  📊 Processed {wordlist_count} wordlists...")
                            
                    except Exception as e:
                        print(f"  ⚠️  Skipping {relative_path}: {e}")
                        continue
        
        catalog['metadata']['total_wordlists'] = wordlist_count
        print(f"✅ Cataloged {wordlist_count} wordlists")
        
        # Save catalog to first available location
        catalog_paths = [
            os.path.join(os.path.dirname(__file__), 'data', 'seclists_catalog.yaml'),
            os.path.join(os.path.dirname(__file__), '..', 'data', 'seclists_catalog.yaml'),
            'seclists_catalog.yaml'  # Current directory
        ]
        
        for catalog_path in catalog_paths:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(catalog_path), exist_ok=True)
                
                with open(catalog_path, 'w') as f:
                    yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True)
                print(f"💾 Catalog saved to: {catalog_path}")
                break
            except Exception as e:
                print(f"  ⚠️  Could not save to {catalog_path}: {e}")
                continue
        
        return catalog
    
    def _categorize_wordlist(self, path: str) -> str:
        """Categorize wordlist based on its path"""
        path_lower = path.lower()
        
        if 'web' in path_lower or 'http' in path_lower or 'directory' in path_lower or 'file' in path_lower:
            return 'web'
        elif 'username' in path_lower or 'user' in path_lower:
            return 'usernames'
        elif 'password' in path_lower or 'pass' in path_lower:
            return 'passwords'
        elif 'subdomain' in path_lower or 'dns' in path_lower:
            return 'dns'
        elif 'snmp' in path_lower:
            return 'snmp'
        else:
            return 'other'
    
    def _extract_tags(self, path: str) -> List[str]:
        """Extract technology tags from wordlist path"""
        tags = []
        
        # Common technologies to look for
        tech_keywords = [
            'wordpress', 'wp', 'drupal', 'joomla', 'php', 'asp', 'aspx', 
            'jsp', 'coldfusion', 'perl', 'python', 'rails', 'django',
            'apache', 'nginx', 'iis', 'tomcat', 'jenkins', 'sharepoint'
        ]
        
        for keyword in tech_keywords:
            if keyword in path:
                tags.append(keyword)
        
        return tags


# Convenience function for easy integration
def select_smart_wordlist(category: str, detected_technologies: Set[str], seclists_path: str) -> Optional[str]:
    """
    Convenient function for smart wordlist selection
    
    Args:
        category: Wordlist category
        detected_technologies: Set of detected technology strings  
        seclists_path: Path to SecLists installation
        
    Returns:
        Full path to selected wordlist or None
    """
    if not detected_technologies or not seclists_path:
        return None
    
    selector = SmartWordlistSelector(seclists_path)
    return selector.select_wordlist(category, detected_technologies)