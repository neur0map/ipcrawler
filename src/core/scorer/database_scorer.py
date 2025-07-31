"""
Database-driven SmartList scoring engine
No hardcoded mappings - everything from database
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WordlistRecommendation:
    """Represents a wordlist recommendation with metadata"""
    name: str
    score: float
    source: str  # 'tech_primary', 'port_primary', 'category', etc.
    reason: str

class DatabaseScorer:
    """Database-driven scoring engine for SmartList recommendations"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent.parent / "database"
        self.mappings = None
        self.tech_db = None
        self.port_db = None
        self.catalog = None
        # Smart caching
        self._tech_cache = {}
        self._port_cache = {}
        self._wordlist_cache = {}
        self._cache_stats = {'hits': 0, 'misses': 0}
        self._load_databases()
    
    def _load_databases(self):
        """Load all required databases"""
        try:
            # Load technology database
            tech_db_path = self.db_path / "technologies" / "tech_db.json"
            if tech_db_path.exists():
                with open(tech_db_path, 'r') as f:
                    self.tech_db = json.load(f)
            else:
                logger.warning(f"Technology database not found at {tech_db_path}")
                self.tech_db = {}
            
            # Load port database
            port_db_path = self.db_path / "ports" / "port_db.json"
            if port_db_path.exists():
                with open(port_db_path, 'r') as f:
                    self.port_db = json.load(f)
            else:
                logger.warning(f"Port database not found at {port_db_path}")
                self.port_db = {}
            
            # Load wordlist catalog
            catalog_path = self.db_path / "wordlists" / "seclists_catalog.json"
            if catalog_path.exists():
                with open(catalog_path, 'r') as f:
                    self.catalog = json.load(f)
            else:
                logger.warning(f"Wordlist catalog not found at {catalog_path}")
                self.catalog = {}
                    
        except Exception as e:
            logger.error(f"Failed to load databases: {e}")
    
    def score(self, tech: Optional[str], port: Optional[int], 
              service: Optional[str] = None, version: Optional[str] = None,
              confidence: Optional[float] = None, context: Optional[Dict[str, Any]] = None,
              workflow_results: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Simplified scoring with 5 key factors:
        1. Technology match (tech_db)
        2. Port classification (port_db) 
        3. Service compatibility
        4. Quality & size balance
        5. Usage frequency adjustment
        
        Args:
            tech: Detected technology (e.g., 'wordpress', 'nginx')
            port: Port number
            service: Service name (optional)
            version: Version info (optional)
            confidence: Detection confidence (optional)
            context: Additional context (optional)
            
        Returns:
            List of recommended wordlist names
        """
        if not self.catalog or not self.catalog.get('wordlists'):
            return self._get_fallback_wordlists()
        
        # Use new rules engine for cleaner logic
        from .rules import rule_engine
        
        # Enhance context with workflow feedback
        enhanced_context = context or {}
        if workflow_results:
            from .workflow_feedback import enhance_scoring_context
            enhanced_context = enhance_scoring_context(enhanced_context, workflow_results)
            
            # Override tech/version with workflow discoveries if more confident
            if 'primary_technology' in enhanced_context:
                workflow_tech = enhanced_context['primary_technology']
                workflow_confidence = enhanced_context.get('tech_confidence', 0.0)
                
                if not tech or (confidence and workflow_confidence > confidence):
                    tech = workflow_tech
                    confidence = workflow_confidence
                    logger.debug(f"Using workflow-discovered tech: {tech} (confidence: {confidence})")
            
            if 'version' in enhanced_context and not version:
                version = enhanced_context['version']
                logger.debug(f"Using workflow-discovered version: {version}")
        
        # Build context for rules engine
        rule_context = enhanced_context
        if 'response_content' not in rule_context:
            rule_context['response_content'] = rule_context.get('headers', {}).get('server', '')
        
        # Get rule matches
        rule_matches = rule_engine.match_rules(tech, port, service, rule_context)
        
        if rule_matches:
            # Get wordlists from rule matches
            recommended_wordlists = rule_engine.get_wordlists_for_rules(rule_matches)
        else:
            # Fallback to basic logic if no rules match
            recommended_wordlists = self._get_basic_recommendations(tech, port, service)
        
        # Score and filter wordlists with simplified scoring
        scored_wordlists = []
        seen = set()
        
        for wl_name in recommended_wordlists:
            if wl_name not in seen:
                # Find wordlist data in catalog
                wl_data = self._find_wordlist_in_catalog(wl_name)
                
                if wl_data:
                    score = self._score_wordlist_simplified(wl_data, tech, port, service, confidence, enhanced_context)
                    scored_wordlists.append((wl_name, score, wl_data))
                    seen.add(wl_name)
        
        # Apply frequency adjustments and simple diversification
        final_selection = self._apply_simplified_selection(scored_wordlists, tech, port)
        
        # Track usage for analytics including workflow feedback
        self._track_rule_usage(tech, port, service, final_selection, enhanced_context)
        
        return [wl[0] for wl in final_selection[:5]]  # Return top 5 names
    
    def _get_tech_wordlists_from_db(self, tech: str) -> List[str]:
        """Get wordlists using tech_db discovery_paths and confidence_weights"""
        wordlists = []
        
        # Find technology in tech_db
        tech_info = self._find_tech_in_db(tech)
        if not tech_info:
            return wordlists
        
        # Use discovery_paths for path-aware wordlist selection
        discovery_paths = tech_info.get('discovery_paths', [])
        confidence_weights = tech_info.get('confidence_weights', {})
        tech_category = tech_info.get('category', '')
        
        # Score wordlists based on tech_db information
        scored_wordlists = []
        
        for wl in self.catalog.get('wordlists', []):
            score = 0.0
            wl_name = wl.get('name', '')
            tech_compatibility = wl.get('tech_compatibility', [])
            
            # Direct tech match gets highest score
            if tech.lower() in [t.lower() for t in tech_compatibility]:
                score += 1.0
            
            # Category-based scoring using tech_db category
            if tech_category == 'cms' and wl.get('category') == 'fuzzing':
                score += 0.8
            elif tech_category == 'web_framework' and wl.get('category') == 'fuzzing':
                score += 0.7
            elif tech_category == 'database' and wl.get('category') in ['other', 'usernames']:
                score += 0.6
            
            # Use confidence weights from tech_db if available
            if confidence_weights:
                # Boost score based on pattern confidence weights
                response_weight = confidence_weights.get('response_patterns', 0.5)
                path_weight = confidence_weights.get('path_patterns', 0.5)
                
                # Apply weights to score
                if response_weight > 0.8:
                    score += 0.3  # High confidence in response patterns
                if path_weight > 0.7:
                    score += 0.2  # High confidence in path patterns
            
            # Discovery paths influence - prefer wordlists that might find these paths
            if discovery_paths and len(discovery_paths) > 0:
                # More discovery paths = higher potential value
                path_bonus = min(0.2, len(discovery_paths) * 0.05)
                score += path_bonus
            
            if score > 0:
                scored_wordlists.append((wl_name, score))
        
        # Sort by score and return top names
        scored_wordlists.sort(key=lambda x: x[1], reverse=True)
        return [wl[0] for wl in scored_wordlists[:3]]
    
    def _get_port_wordlists_from_db(self, port: int) -> List[str]:
        """Get wordlists using port_db classification and risk assessment"""
        wordlists = []
        
        # Find port info in port_db
        port_info = self.port_db.get(str(port), {})
        if not port_info:
            return wordlists
        
        # Extract rich port information
        classification = port_info.get('classification', {})
        service_category = classification.get('category', '')
        risk_level = classification.get('risk_level', 'unknown')
        tech_indicators = port_info.get('indicators', {}).get('tech_indicators', [])
        
        # Score wordlists based on port database information
        scored_wordlists = []
        
        for wl in self.catalog.get('wordlists', []):
            score = 0.0
            wl_name = wl.get('name', '')
            wl_category = wl.get('category', '')
            port_compatibility = wl.get('port_compatibility', [])
            
            # Direct port compatibility
            if port in port_compatibility:
                score += 1.0
            
            # Service category mapping from port_db
            if service_category == 'web-service' and wl_category == 'fuzzing':
                score += 0.8
            elif service_category == 'file-transfer' and wl_category == 'other':
                score += 0.7
            elif service_category == 'database' and wl_category in ['other', 'usernames', 'passwords']:
                score += 0.6
            elif service_category == 'remote-access' and wl_category == 'other':
                score += 0.5
            
            # Risk level influence
            if risk_level == 'high':
                score += 0.2  # High-risk ports deserve more attention
            elif risk_level == 'medium':
                score += 0.1
            
            # Technology indicators from port_db
            if tech_indicators:
                tech_compatibility = wl.get('tech_compatibility', [])
                for tech_indicator in tech_indicators:
                    if any(tech_indicator.lower() in compat.lower() for compat in tech_compatibility):
                        score += 0.3
                        break
            
            if score > 0:
                scored_wordlists.append((wl_name, score))
        
        # Sort by score and return top names
        scored_wordlists.sort(key=lambda x: x[1], reverse=True)
        return [wl[0] for wl in scored_wordlists[:2]]
    
    def _get_service_wordlists_from_db(self, service: str) -> List[str]:
        """Get wordlists for a service using compatibility mappings"""
        wordlists = []
        service_lower = service.lower()
        
        # Filter wordlists by service compatibility
        for wl in self.catalog.get('wordlists', []):
            tech_compatibility = wl.get('tech_compatibility', [])
            
            # Check if service matches any compatible technologies
            if any(service_lower in tech.lower() or tech.lower() in service_lower 
                   for tech in tech_compatibility):
                wordlists.append(wl['name'])
        
        return wordlists[:2]  # Limit to top 2
    
    def _get_general_discovery_wordlists(self) -> List[str]:
        """Get general discovery wordlists when no specific matches"""
        wordlists = []
        
        # Prefer smaller, general-purpose wordlists
        for wl in self.catalog.get('wordlists', []):
            category = wl.get('category', '')
            size = wl.get('size_lines', 0)
            name = wl.get('name', '')
            
            # Small fuzzing lists are good for general discovery
            if category == 'fuzzing' and size < 100000:
                wordlists.append(name)
            # Other small general lists
            elif category == 'other' and size < 50000:
                wordlists.append(name)
            # Include common, high-quality wordlists regardless of size
            elif any(keyword in name.lower() for keyword in ['common', 'dirs', 'directory', 'web-content']):
                wordlists.append(name)
        
        # If no small lists found, include medium-sized quality lists
        if not wordlists:
            for wl in self.catalog.get('wordlists', []):
                quality = wl.get('quality', '')
                category = wl.get('category', '')
                if quality in ['excellent', 'good'] and category in ['fuzzing', 'other']:
                    wordlists.append(wl['name'])
        
        return wordlists[:3]  # Increased to top 3 for better coverage
    
    def _find_tech_in_db(self, tech: str) -> Optional[Dict[str, Any]]:
        """Find technology information in tech_db with caching"""
        tech_lower = tech.lower()
        
        # Check cache first
        if tech_lower in self._tech_cache:
            self._cache_stats['hits'] += 1
            return self._tech_cache[tech_lower]
        
        self._cache_stats['misses'] += 1
        
        # Search through all categories in tech_db
        result = None
        for category, technologies in self.tech_db.items():
            if tech_lower in technologies:
                result = technologies[tech_lower]
                break
        
        # Cache the result (including None)
        self._tech_cache[tech_lower] = result
        
        return result
    
    def _score_wordlist(self, wordlist: Dict[str, Any], tech: Optional[str], 
                       port: Optional[int], service: Optional[str]) -> float:
        """Score a wordlist based on context relevance"""
        score = 0.0
        
        # Base score from wordlist quality
        base_score = wordlist.get('scorer_weight', 0.5)
        
        # Technology-specific scoring
        if tech and self.mappings:
            tech_config = self.mappings.get('technology_mappings', {}).get(tech.lower(), {})
            if tech_config:
                # Check if wordlist category matches tech preference
                wl_category = wordlist.get('category', '')
                if wl_category not in tech_config.get('exclude_categories', []):
                    score += base_score + tech_config.get('priority_boost', 0.0)
                else:
                    return 0.0  # Excluded category
        
        # Port-specific scoring
        if port:
            port_categories = {
                80: ['fuzzing', 'other'],
                443: ['fuzzing', 'other'], 
                21: ['other'],
                22: ['other'],
                3306: ['other']
            }
            if port in port_categories:
                wl_category = wordlist.get('category', '')
                if wl_category in port_categories[port]:
                    score += 0.3
        
        # Prefer smaller, more focused wordlists for web technologies
        if tech and wordlist.get('size_lines', 0) < 10000:
            score += 0.2
        
        # Penalize very large wordlists unless specifically needed
        if wordlist.get('size_lines', 0) > 1000000:
            score -= 0.3
        
        return max(0.0, score)
    
    def _score_wordlist_simplified(self, wordlist: Dict[str, Any], tech: Optional[str], 
                                  port: Optional[int], service: Optional[str],
                                  confidence: Optional[float] = None, 
                                  context: Optional[Dict[str, Any]] = None) -> float:
        """Simplified scoring with 5 key factors"""
        score = 0.0
        
        # Factor 1: Technology match (0.0-1.0)
        tech_compatibility = wordlist.get('tech_compatibility', [])
        if tech and tech.lower() in [t.lower() for t in tech_compatibility]:
            score += 1.0  # Perfect tech match
        elif tech_compatibility:
            score += 0.3  # Has tech compatibility but not exact
        
        # Factor 2: Port classification (0.0-0.5) 
        port_compatibility = wordlist.get('port_compatibility', [])
        if port and port in port_compatibility:
            score += 0.5
        
        # Factor 3: Service compatibility (0.0-0.3)
        if service:
            service_lower = service.lower()
            if any(service_lower in t.lower() or t.lower() in service_lower 
                   for t in tech_compatibility):
                score += 0.3
        
        # Factor 4: Quality & size balance (0.0-0.4)
        quality = wordlist.get('quality', 'unknown')
        size = wordlist.get('size_lines', 0)
        
        if quality == 'excellent':
            score += 0.2
        elif quality == 'good':
            score += 0.1
        
        # Size scoring: prefer focused lists
        if size < 50000:  # Small, focused
            score += 0.2
        elif size > 5000000:  # Very large
            score -= 0.3
        
        # Factor 5: Category appropriateness using port_db and workflow feedback (0.0-0.4)
        category = wordlist.get('category', '')
        
        # Use port database to determine service category
        is_web_service = False
        if port and self.port_db:
            port_info = self.port_db.get(str(port), {})
            service_category = port_info.get('classification', {}).get('category', '')
            is_web_service = service_category in ['web-service', 'web']
        
        # Apply category scoring based on database classification
        if category == 'fuzzing' and (is_web_service or (service and 'http' in service.lower())):
            score += 0.2
        elif category in ['usernames', 'passwords'] and not tech:
            score -= 0.2  # Penalize auth lists without tech context
        
        # Workflow feedback bonus (Factor 6: Workflow integration)
        if context:
            # Path discovery feedback
            discovered_paths = context.get('discovered_paths', [])
            if discovered_paths and category == 'fuzzing':
                # Bonus for fuzzing lists when paths were successfully discovered
                path_success_bonus = min(0.2, len(discovered_paths) * 0.02)
                score += path_success_bonus
            
            # Spider insights
            spider_data = context.get('spider_data', {})
            if spider_data:
                # Bonus for wordlists that align with spider discoveries
                if spider_data.get('has_admin_interface') and 'admin' in wordlist.get('name', '').lower():
                    score += 0.1
                if spider_data.get('has_api_endpoints') and 'api' in wordlist.get('name', '').lower():
                    score += 0.1
            
            # Response pattern alignment
            response_patterns = context.get('response_patterns', [])
            if response_patterns:
                wordlist_name_lower = wordlist.get('name', '').lower()
                for pattern in response_patterns:
                    if any(keyword in wordlist_name_lower for keyword in pattern.split(':')[-1].split()):
                        score += 0.05  # Small bonus for pattern alignment
                        break
        
        # Advanced context-aware adjustments
        if context and tech:
            score += self._apply_context_aware_scoring(wordlist, tech, context, confidence)
        
        return max(0.0, score)
    
    def _apply_context_aware_scoring(self, wordlist: Dict[str, Any], tech: str, 
                                   context: Dict[str, Any], confidence: Optional[float]) -> float:
        """Apply advanced context-aware scoring adjustments"""
        bonus = 0.0
        
        # Version-specific scoring
        version = context.get('version')
        if version:
            wordlist_name = wordlist.get('name', '').lower()
            
            # Direct version match in wordlist name
            if version in wordlist_name:
                bonus += 0.3  # Strong bonus for version-specific wordlists
            
            # Version-aware tech scoring
            tech_lower = tech.lower()
            if tech_lower == 'wordpress' and version:
                # WordPress version-specific paths
                if 'wp' in wordlist_name and any(v in wordlist_name for v in ['4.', '5.', '6.']):
                    bonus += 0.2
            elif tech_lower == 'drupal' and version:
                # Drupal version-specific paths
                if 'drupal' in wordlist_name and version.split('.')[0] in wordlist_name:
                    bonus += 0.2
        
        # Technology confidence-based adjustments
        tech_confidence = context.get('tech_confidence', 0.5)
        if tech_confidence > 0.8:
            # High confidence: prefer specific wordlists
            tech_compatibility = wordlist.get('tech_compatibility', [])
            if tech.lower() in [t.lower() for t in tech_compatibility]:
                bonus += 0.2  # Extra bonus for high-confidence exact matches
        elif tech_confidence < 0.4:
            # Low confidence: prefer exploratory wordlists
            category = wordlist.get('category', '')
            size = wordlist.get('size_lines', 0)
            if category == 'fuzzing' and size < 100000:
                bonus += 0.15  # Bonus for small exploratory lists
        
        # Response pattern alignment scoring
        response_patterns = context.get('response_patterns', [])
        if response_patterns:
            wordlist_name_lower = wordlist.get('name', '').lower()
            pattern_matches = 0
            
            for pattern in response_patterns:
                # Extract technology and pattern from format "tech:pattern"
                if ':' in pattern:
                    pattern_tech, pattern_text = pattern.split(':', 1)
                    
                    # Check if pattern aligns with wordlist
                    if pattern_tech.lower() == tech.lower():
                        # Check if wordlist name contains pattern keywords
                        pattern_keywords = pattern_text.lower().split()
                        for keyword in pattern_keywords:
                            if len(keyword) > 3 and keyword in wordlist_name_lower:
                                pattern_matches += 1
                                break
            
            if pattern_matches > 0:
                # Bonus proportional to pattern matches
                bonus += min(0.2, pattern_matches * 0.1)
        
        # Discovered paths influence
        discovered_paths = context.get('discovered_paths', [])
        if discovered_paths:
            # Analyze path patterns to infer appropriate wordlists
            path_analysis = self._analyze_discovered_paths(discovered_paths)
            
            # Admin interface detection
            if path_analysis.get('has_admin_paths') and 'admin' in wordlist.get('name', '').lower():
                bonus += 0.15
            
            # API endpoint detection
            if path_analysis.get('has_api_paths') and 'api' in wordlist.get('name', '').lower():
                bonus += 0.15
            
            # Deep directory structure detected
            if path_analysis.get('deep_structure') and wordlist.get('category') == 'fuzzing':
                bonus += 0.1
        
        return bonus
    
    def _analyze_discovered_paths(self, paths: List[str]) -> Dict[str, bool]:
        """Analyze discovered paths to infer characteristics"""
        analysis = {
            'has_admin_paths': False,
            'has_api_paths': False,
            'deep_structure': False,
            'has_uploads': False,
            'has_config': False
        }
        
        admin_indicators = ['admin', 'manage', 'control', 'dashboard', 'cp']
        api_indicators = ['api', 'rest', 'graphql', 'json', 'xml']
        upload_indicators = ['upload', 'file', 'media', 'assets']
        config_indicators = ['config', 'settings', 'conf', '.env']
        
        for path in paths:
            path_lower = path.lower()
            
            # Check for admin paths
            if any(indicator in path_lower for indicator in admin_indicators):
                analysis['has_admin_paths'] = True
            
            # Check for API paths
            if any(indicator in path_lower for indicator in api_indicators):
                analysis['has_api_paths'] = True
            
            # Check for upload paths
            if any(indicator in path_lower for indicator in upload_indicators):
                analysis['has_uploads'] = True
            
            # Check for config paths
            if any(indicator in path_lower for indicator in config_indicators):
                analysis['has_config'] = True
            
            # Check for deep directory structure
            if path.count('/') > 3:
                analysis['deep_structure'] = True
        
        return analysis
    
    def _apply_simplified_selection(self, scored_wordlists: List[Tuple[str, float, Dict]], 
                                   tech: Optional[str], port: Optional[int]) -> List[Tuple[str, float, Dict]]:
        """Simplified selection with session-based variety and basic diversification"""
        # Apply frequency adjustments
        scored_wordlists = self._apply_frequency_adjustments(scored_wordlists, tech, port)
        
        # Sort by adjusted score
        scored_wordlists.sort(key=lambda x: x[1], reverse=True)
        
        # Apply session-based variety
        scored_wordlists = self._apply_session_variety(scored_wordlists, tech, port)
        
        selected = []
        category_counts = {}
        
        for wl_name, score, wl_data in scored_wordlists:
            category = wl_data.get('category', 'unknown')
            
            # Simple diversification: limit 2 per category
            if category_counts.get(category, 0) >= 2:
                continue
            
            # Prefer high-quality wordlists in first 3 positions
            quality = wl_data.get('quality', 'unknown')
            if len(selected) < 3 and quality not in ['excellent', 'good']:
                continue
            
            selected.append((wl_name, score, wl_data))
            category_counts[category] = category_counts.get(category, 0) + 1
            
            if len(selected) >= 5:
                break
        
        return selected
    
    def _apply_session_variety(self, scored_wordlists: List[Tuple[str, float, Dict]], 
                              tech: Optional[str], port: Optional[int]) -> List[Tuple[str, float, Dict]]:
        """Apply simple session-based variety to prevent same selections every time"""
        if len(scored_wordlists) <= 5:
            return scored_wordlists  # Not enough options to vary
        
        import hashlib
        import random
        
        # Create session seed based on tech and port
        session_key = f"{tech or 'none'}:{port or 0}"
        session_hash = int(hashlib.md5(session_key.encode()).hexdigest()[:8], 16)
        
        # Use session hash as random seed for consistent but varied selection
        random.seed(session_hash)
        
        # Keep top 2 wordlists (highest scores) always
        top_wordlists = scored_wordlists[:2]
        remaining_wordlists = scored_wordlists[2:]
        
        # Add some randomization to the remaining wordlists
        if len(remaining_wordlists) > 5:
            # Randomly select from top 50% of remaining wordlists
            selection_pool = remaining_wordlists[:len(remaining_wordlists)//2]
            random.shuffle(selection_pool)
            remaining_wordlists = selection_pool + remaining_wordlists[len(remaining_wordlists)//2:]
        
        # Restore random seed to avoid affecting other code
        random.seed()
        
        return top_wordlists + remaining_wordlists
    
    def _apply_frequency_adjustments(self, scored_wordlists: List[Tuple[str, float, Dict]], 
                                   tech: Optional[str], port: Optional[int]) -> List[Tuple[str, float, Dict]]:
        """Apply frequency-based scoring adjustments using contribution data"""
        try:
            from src.core.scorer.cache import cache
            
            # Get recent selections for frequency analysis
            recent_entries = cache.search_selections(days_back=7, limit=100)
            
            if not recent_entries:
                return scored_wordlists  # No adjustment if no data
            
            # Count wordlist usage frequency
            wordlist_usage = {}
            total_selections = 0
            
            for entry in recent_entries:
                wordlists = entry.get('selected_wordlists', [])
                total_selections += len(wordlists)
                
                for wl in wordlists:
                    wordlist_usage[wl] = wordlist_usage.get(wl, 0) + 1
            
            if total_selections == 0:
                return scored_wordlists
            
            # Apply frequency-based adjustments
            adjusted_wordlists = []
            
            for wl_name, score, wl_data in scored_wordlists:
                usage_count = wordlist_usage.get(wl_name, 0)
                usage_rate = usage_count / total_selections if total_selections > 0 else 0
                
                # Calculate frequency penalty/bonus
                frequency_adjustment = 0.0
                
                if usage_rate > 0.3:  # Overused (>30% of selections)
                    frequency_adjustment = -0.4  # Heavy penalty
                elif usage_rate > 0.2:  # Frequently used (>20%)
                    frequency_adjustment = -0.2  # Medium penalty
                elif usage_rate > 0.1:  # Moderately used (>10%)
                    frequency_adjustment = -0.1  # Light penalty
                elif usage_rate == 0:  # Never used
                    frequency_adjustment = 0.2   # Bonus for unused wordlists
                else:  # Lightly used (<10%)
                    frequency_adjustment = 0.1   # Small bonus
                
                # Context-specific adjustments
                if tech and port:
                    # Check usage in similar contexts
                    similar_context_usage = 0
                    similar_contexts = 0
                    
                    for entry in recent_entries:
                        entry_context = entry.get('context', {})
                        if (entry_context.get('tech') == tech or 
                            entry_context.get('port') == port):
                            similar_contexts += 1
                            if wl_name in entry.get('selected_wordlists', []):
                                similar_context_usage += 1
                    
                    if similar_contexts > 0:
                        context_usage_rate = similar_context_usage / similar_contexts
                        if context_usage_rate > 0.5:  # Overused in this context
                            frequency_adjustment -= 0.3
                        elif context_usage_rate == 0:  # Never used in this context
                            frequency_adjustment += 0.3
                
                # Apply adjustment
                adjusted_score = max(0.0, score + frequency_adjustment)
                adjusted_wordlists.append((wl_name, adjusted_score, wl_data))
                
                # Log significant adjustments
                if abs(frequency_adjustment) > 0.1:
                    logger.debug(f"Frequency adjustment for {wl_name}: {frequency_adjustment:.2f} "
                               f"(usage: {usage_rate:.1%}, new score: {adjusted_score:.2f})")
            
            # Re-sort by adjusted scores
            adjusted_wordlists.sort(key=lambda x: x[1], reverse=True)
            return adjusted_wordlists
            
        except Exception as e:
            logger.debug(f"Could not apply frequency adjustments: {e}")
            return scored_wordlists  # Return original on error
    
    def _filter_wordlists(self, scored_wordlists: List[Tuple[str, float, Dict]], 
                         tech: Optional[str], port: Optional[int]) -> List[Tuple[str, float, Dict]]:
        """Filter wordlists to avoid irrelevant ones"""
        filtered = []
        
        for name, score, wl_data in scored_wordlists:
            # Skip if score too low
            if score < 0.1:
                continue
                
            # Skip username/password lists for web scanning
            category = wl_data.get('category', '')
            if category in ['usernames', 'passwords'] and tech:
                continue
            
            # Skip subdomain lists for port scanning
            if 'subdomain' in name.lower() and port:
                continue
                
            filtered.append((name, score, wl_data))
        
        return filtered
    
    def _get_category_wordlists(self, category: str) -> List[str]:
        """Get wordlists for a technology category"""
        wordlists = []
        
        category_mapping = {
            'cms': ['fuzzing', 'other'],
            'web_framework': ['fuzzing'],
            'web_server': ['fuzzing', 'other'],
            'database': ['other'],
            'proxy': ['other']
        }
        
        relevant_categories = category_mapping.get(category, ['fuzzing'])
        
        for wl in self.catalog.get('wordlists', []):
            if wl.get('category') in relevant_categories:
                wordlists.append(wl['name'])
        
        return wordlists[:2]  # Limit to top 2
    
    def _get_service_category_wordlists(self, service_category: str) -> List[str]:
        """Get wordlists for a service category"""
        wordlists = []
        
        # Map service categories to wordlist categories
        if service_category in ['web-service', 'web']:
            target_categories = ['fuzzing']
        elif service_category == 'file-transfer':
            target_categories = ['other']
        elif service_category == 'database':
            target_categories = ['other', 'usernames', 'passwords']
        else:
            target_categories = ['fuzzing', 'other']
        
        for wl in self.catalog.get('wordlists', []):
            if wl.get('category') in target_categories:
                wordlists.append(wl['name'])
        
        return wordlists[:2]  # Limit to top 2
    
    def _get_fuzzing_wordlists(self) -> List[str]:
        """Get fuzzing wordlists for web services"""
        wordlists = []
        
        for wl in self.catalog.get('wordlists', []):
            if wl.get('category') == 'fuzzing':
                # Prefer smaller, focused fuzzing lists
                size = wl.get('size_lines', 0)
                if size < 500000:  # Under 500k lines
                    wordlists.append(wl['name'])
        
        return wordlists[:3]  # Limit to top 3
    
    def _track_rule_usage(self, tech: Optional[str], port: Optional[int], 
                         service: Optional[str], final_selection: List[Tuple],
                         context: Optional[Dict[str, Any]] = None) -> None:
        """Track rule usage for audit analytics including workflow feedback"""
        try:
            from src.core.scorer.cache import cache
            import time
            import uuid
            
            # Create enhanced usage record with workflow feedback
            usage_record = {
                'timestamp': time.time(),
                'context': {
                    'tech': tech,
                    'port': port,
                    'service': service
                },
                'selected_wordlists': [sel[0] for sel in final_selection],
                'rule_matched': self._determine_rule_matched(tech, port, service),
                'session_id': str(uuid.uuid4())[:8]
            }
            
            # Add workflow feedback data
            if context:
                workflow_data = {
                    'discovered_paths_count': len(context.get('discovered_paths', [])),
                    'has_spider_data': bool(context.get('spider_data')),
                    'response_patterns_count': len(context.get('response_patterns', [])),
                    'workflow_tech_confidence': context.get('tech_confidence', 0.0),
                    'version_detected': bool(context.get('version'))
                }
                usage_record['workflow_feedback'] = workflow_data
            
            # Store in cache for audit analysis
            cache.store_selection(usage_record)
            
        except Exception as e:
            logger.debug(f"Could not track rule usage: {e}")
    
    def _determine_rule_matched(self, tech: Optional[str], port: Optional[int], 
                               service: Optional[str]) -> str:
        """Determine which rule was matched for tracking"""
        if tech and port:
            return f"database:{tech}:{port}"
        elif tech:
            return f"database:{tech}"
        elif port:
            return f"database:port:{port}"
        elif service:
            return f"database:service:{service}"
        else:
            return "database:fallback"
    
    def _get_fallback_wordlists(self) -> List[str]:
        """Return fallback wordlists when catalog unavailable"""
        return ['common.txt', 'directory-list-small.txt']
    
    def _find_wordlist_in_catalog(self, wl_name: str) -> Optional[Dict[str, Any]]:
        """Find wordlist data in catalog with caching"""
        if not self.catalog:
            return None
        
        # Check cache first
        if wl_name in self._wordlist_cache:
            self._cache_stats['hits'] += 1
            return self._wordlist_cache[wl_name]
        
        self._cache_stats['misses'] += 1
        
        # Search in catalog
        result = None
        for wl in self.catalog.get('wordlists', []):
            if wl.get('name') == wl_name:
                result = wl
                break
        
        # Cache the result
        self._wordlist_cache[wl_name] = result
        
        return result
    
    def _get_basic_recommendations(self, tech: Optional[str], port: Optional[int], 
                                  service: Optional[str]) -> List[str]:
        """Basic wordlist recommendations when rules engine fails"""
        recommendations = []
        
        # Technology-based recommendations
        if tech:
            tech_lower = tech.lower()
            for wl in self.catalog.get('wordlists', []):
                tech_compatibility = wl.get('tech_compatibility', [])
                if any(tech_lower in t.lower() for t in tech_compatibility):
                    recommendations.append(wl['name'])
        
        # Port-based recommendations using port_db classification
        if port and self.port_db:
            port_info = self.port_db.get(str(port), {})
            service_category = port_info.get('classification', {}).get('category', '')
            
            if service_category in ['web-service', 'web']:
                for wl in self.catalog.get('wordlists', []):
                    if wl.get('category') == 'fuzzing':
                        recommendations.append(wl['name'])
                        if len(recommendations) >= 3:
                            break
        
        # Add general high-quality wordlists if needed
        if len(recommendations) < 3:
            for wl in self.catalog.get('wordlists', []):
                if wl.get('quality') == 'excellent' and wl.get('size_lines', 0) < 100000:
                    recommendations.append(wl['name'])
                    if len(recommendations) >= 5:
                        break
        
        return recommendations[:5]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics"""
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = self._cache_stats['hits'] / total_requests if total_requests > 0 else 0.0
        
        return {
            'cache_hits': self._cache_stats['hits'],
            'cache_misses': self._cache_stats['misses'],
            'hit_rate': round(hit_rate * 100, 2),
            'cached_techs': len(self._tech_cache),
            'cached_ports': len(self._port_cache),
            'cached_wordlists': len(self._wordlist_cache)
        }
    
    def clear_cache(self):
        """Clear all caches"""
        self._tech_cache.clear()
        self._port_cache.clear()
        self._wordlist_cache.clear()
        self._cache_stats = {'hits': 0, 'misses': 0}

# Global instance
db_scorer = DatabaseScorer()

def score_wordlists_database(tech: Optional[str], port: Optional[int], 
                           service: Optional[str] = None, version: Optional[str] = None,
                           confidence: Optional[float] = None, context: Optional[Dict[str, Any]] = None,
                           workflow_results: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Main entry point for enhanced database-driven wordlist scoring
    
    Integrates all database resources and workflow feedback for intelligent recommendations
    """
    return db_scorer.score(tech, port, service, version, confidence, context, workflow_results)


def get_scorer_cache_stats() -> Dict[str, Any]:
    """Get caching statistics from the database scorer"""
    return db_scorer.get_cache_stats()


def clear_scorer_cache():
    """Clear the database scorer cache"""
    db_scorer.clear_cache()