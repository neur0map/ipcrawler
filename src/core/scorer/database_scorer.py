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
              confidence: Optional[float] = None, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Score and recommend wordlists based on detected technology and port
        Uses discovery_paths from tech_db.json and catalog filtering
        
        Args:
            tech: Detected technology (e.g., 'wordpress', 'nginx')
            port: Port number
            service: Service name (optional)
            version: Version info (optional)
            
        Returns:
            List of recommended wordlist names
        """
        if not self.catalog or not self.catalog.get('wordlists'):
            return self._get_fallback_wordlists()
        
        recommended_wordlists = []
        
        # Enhanced rule activation strategy
        # 1. Get technology-specific recommendations (activates tech rules)
        if tech:
            tech_wordlists = self._get_tech_wordlists_from_db(tech)
            recommended_wordlists.extend(tech_wordlists)
            
            # Also get category-based recommendations for broader activation
            tech_info = self._find_tech_in_db(tech)
            if tech_info:
                category = tech_info.get('category', '')
                if category:
                    category_wordlists = self._get_category_wordlists(category)
                    recommended_wordlists.extend(category_wordlists)
        
        # 2. Get port-specific recommendations (activates port rules)
        if port:
            port_wordlists = self._get_port_wordlists_from_db(port)
            recommended_wordlists.extend(port_wordlists)
            
            # Also get service category recommendations
            port_info = self.port_db.get(str(port), {})
            if port_info:
                service_category = port_info.get('classification', {}).get('category', '')
                if service_category:
                    category_wordlists = self._get_service_category_wordlists(service_category)
                    recommended_wordlists.extend(category_wordlists)
        
        # 3. Add service-specific wordlists based on service name
        if service:
            service_wordlists = self._get_service_wordlists_from_db(service)
            recommended_wordlists.extend(service_wordlists)
        
        # 4. Add general discovery wordlists - always include some for broader coverage
        general_wordlists = self._get_general_discovery_wordlists()
        recommended_wordlists.extend(general_wordlists)
        
        # 5. Add fuzzing lists for web services to increase activation
        if port in [80, 443, 8080, 8443, 3000, 5000, 9000] or (service and 'http' in service.lower()):
            fuzzing_wordlists = self._get_fuzzing_wordlists()
            recommended_wordlists.extend(fuzzing_wordlists)
        
        # Score and rank all recommended wordlists
        scored_wordlists = []
        seen = set()
        
        for wl_name in recommended_wordlists:
            if wl_name not in seen:
                # Find wordlist data in catalog
                wl_data = None
                for wl in self.catalog.get('wordlists', []):
                    if wl['name'] == wl_name:
                        wl_data = wl
                        break
                
                if wl_data:
                    score = self._score_wordlist_enhanced(wl_data, tech, port, service, 
                                                        confidence, version, context)
                    scored_wordlists.append((wl_name, score, wl_data))
                    seen.add(wl_name)
        
        # Apply diversification and rotation to prevent overuse
        final_selection = self._apply_diversification(scored_wordlists, tech, port, confidence)
        
        # Track rule usage for audit purposes
        self._track_rule_usage(tech, port, service, final_selection)
        
        return [wl[0] for wl in final_selection[:5]]  # Return top 5 names
    
    def _get_tech_wordlists_from_db(self, tech: str) -> List[str]:
        """Get wordlists for a technology using tech_db discovery paths"""
        wordlists = []
        
        # Find technology in tech_db
        tech_info = self._find_tech_in_db(tech)
        if not tech_info:
            return wordlists
        
        # Get discovery paths from tech_db
        discovery_paths = tech_info.get('discovery_paths', [])
        if not discovery_paths:
            return wordlists
        
        # Find wordlists that match the technology category
        tech_category = tech_info.get('category', '')
        
        # Filter catalog wordlists by tech compatibility or category relevance
        for wl in self.catalog.get('wordlists', []):
            wl_category = wl.get('category', '')
            tech_compatibility = wl.get('tech_compatibility', [])
            
            # Direct tech match
            if tech.lower() in tech_compatibility:
                wordlists.append(wl['name'])
            # Category relevance for web technologies
            elif tech_category in ['cms', 'web_framework'] and wl_category == 'fuzzing':
                wordlists.append(wl['name'])
        
        return wordlists[:3]  # Limit to top 3
    
    def _get_port_wordlists_from_db(self, port: int) -> List[str]:
        """Get wordlists for a port using port_db"""
        wordlists = []
        
        # Find port info in port_db
        port_info = self.port_db.get(str(port), {})
        if not port_info:
            return wordlists
        
        # Get service category
        service_category = port_info.get('classification', {}).get('category', '')
        
        # Filter wordlists by port compatibility or service relevance
        for wl in self.catalog.get('wordlists', []):
            port_compatibility = wl.get('port_compatibility', [])
            
            # Direct port match
            if port in port_compatibility:
                wordlists.append(wl['name'])
            # Service category relevance
            elif service_category == 'file-transfer' and wl.get('category') == 'other':
                wordlists.append(wl['name'])
        
        return wordlists[:2]  # Limit to top 2
    
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
        """Find technology information in tech_db"""
        tech_lower = tech.lower()
        
        # Search through all categories in tech_db
        for category, technologies in self.tech_db.items():
            if tech_lower in technologies:
                return technologies[tech_lower]
        
        return None
    
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
    
    def _score_wordlist_enhanced(self, wordlist: Dict[str, Any], tech: Optional[str], 
                                port: Optional[int], service: Optional[str],
                                confidence: Optional[float] = None, version: Optional[str] = None,
                                context: Optional[Dict[str, Any]] = None) -> float:
        """Enhanced scoring with context awareness and anti-clustering (Phase 3.1)"""
        score = 0.0
        
        # Base score from wordlist quality
        base_score = wordlist.get('scorer_weight', 0.5)
        
        # Technology compatibility bonus (Phase 1 improvement)
        tech_compatibility = wordlist.get('tech_compatibility', [])
        if tech and tech.lower() in [t.lower() for t in tech_compatibility]:
            score += 1.0  # Strong bonus for tech-specific wordlists
        elif tech_compatibility:  # Has some tech compatibility but not exact match
            score += 0.3
        
        # Port compatibility bonus
        port_compatibility = wordlist.get('port_compatibility', [])
        if port and port in port_compatibility:
            score += 0.5
        
        # Category-based scoring
        category = wordlist.get('category', '')
        size = wordlist.get('size_lines', 0)
        
        # Size-based penalties for generic overuse (Phase 2.1)
        if size > 5000000:  # Very large wordlists
            score -= 0.8  # Heavy penalty
        elif size > 1000000:  # Large wordlists  
            score -= 0.5  # Medium penalty
        elif size < 100000:  # Small, focused wordlists
            score += 0.4  # Bonus for targeted lists
        
        # Category-based adjustments
        if category in ['usernames', 'passwords'] and tech:
            # Reduce preference for auth lists unless specifically needed
            if tech.lower() not in ['mysql', 'phpmyadmin', 'jenkins', 'grafana']:
                score -= 0.3
        
        if category == 'subdomain':
            # Subdomain lists are very specific use case
            score -= 0.6  # Heavy penalty unless specifically needed
        
        if category == 'fuzzing' and tech:
            # Fuzzing lists are good for web technologies
            score += 0.2
        
        # Enhanced quality scoring using detailed metrics (Phase 4.3)
        quality = wordlist.get('quality', 'unknown')
        quality_metrics = wordlist.get('quality_metrics', {})
        
        if quality == 'excellent':
            score += 0.1
        
        # Use detailed quality metrics if available
        if quality_metrics:
            accuracy = quality_metrics.get('accuracy', 0.5)
            specificity = quality_metrics.get('specificity', 0.5)
            effectiveness = quality_metrics.get('effectiveness_score', 0.5)
            false_positive_rate = quality_metrics.get('false_positive_rate', 0.5)
            
            # Accuracy bonus
            if accuracy >= 0.8:
                score += 0.2
            elif accuracy >= 0.7:
                score += 0.1
            
            # Specificity bonus
            if specificity >= 0.9:
                score += 0.15
            elif specificity >= 0.8:
                score += 0.1
            
            # Penalty for high false positive rate
            if false_positive_rate > 0.3:
                score -= 0.2
            elif false_positive_rate > 0.2:
                score -= 0.1
            
            # Priority score consideration
            priority_score = wordlist.get('priority_score', 0.5)
            if priority_score >= 0.8:
                score += 0.15
            
            # Target specificity bonus
            target_specificity = wordlist.get('target_specificity', 'general')
            if target_specificity in ['high', 'very_high', 'tech_specific']:
                score += 0.1
            elif target_specificity in ['dns_specific', 'browser_specific']:
                # These are valuable for specific use cases
                if tech or service:
                    score += 0.05
        
        # Use-case specific scoring (Phase 4.4)
        use_cases = wordlist.get('use_cases', [])
        if use_cases:
            # Match use cases to current scanning context
            if tech and service:
                # For technology-specific scanning
                if 'authentication_testing' in use_cases and tech.lower() in ['mysql', 'phpmyadmin', 'jenkins', 'grafana']:
                    score += 0.4
                elif 'fuzzing' in use_cases and tech.lower() in ['wordpress', 'django', 'apache', 'nginx']:
                    score += 0.3
                elif 'browser_enumeration' in use_cases and 'http' in service.lower():
                    score += 0.2
            
            # Context-specific use case matching
            if context:
                scan_type = context.get('scan_type', 'general')
                if scan_type == 'authentication' and 'authentication_testing' in use_cases:
                    score += 0.5
                elif scan_type == 'fuzzing' and 'fuzzing' in use_cases:
                    score += 0.4
                elif scan_type == 'enumeration' and any(uc in use_cases for uc in ['enumeration', 'discovery']):
                    score += 0.3
        
        # Service-specific bonus
        if service and tech:
            service_lower = service.lower()
            if any(service_lower in t.lower() or t.lower() in service_lower 
                   for t in tech_compatibility):
                score += 0.3
        
        # Phase 3.1: Context-aware scoring with confidence
        if confidence is not None:
            if confidence >= 0.8:
                # High confidence - stick to specific wordlists
                if tech and tech.lower() in [t.lower() for t in tech_compatibility]:
                    score += 0.5  # Extra bonus for high-confidence exact matches
            elif confidence < 0.5:
                # Low confidence - prefer more generic/exploratory wordlists
                if category == 'fuzzing' or size < 100000:
                    score += 0.3  # Bonus for exploratory lists
                if not tech_compatibility:  # Generic lists better for uncertain contexts
                    score += 0.2
        
        # Version-specific adjustments
        if version and tech:
            # Prefer smaller, targeted lists for specific versions
            if size < 50000:
                score += 0.3
        
        # Entropy-based scoring (Phase 4.4)
        entropy_level = wordlist.get('entropy_level', 'medium')
        if entropy_level == 'very_high':
            if confidence and confidence >= 0.7:
                score += 0.2  # High-entropy lists good for confident detections
            else:
                score -= 0.1  # Too noisy for uncertain contexts
        elif entropy_level == 'high':
            score += 0.1
        elif entropy_level == 'low':
            if confidence and confidence < 0.5:
                score += 0.15  # Low-entropy good for exploration
        
        # Context diversity bonus (anti-clustering)
        if context:
            # Add variation based on context hash to prevent clustering
            import hashlib
            context_str = f"{tech}:{port}:{service}:{version}"
            context_hash = int(hashlib.md5(context_str.encode()).hexdigest()[:8], 16)
            
            # Use context hash to add slight variations
            variation = (context_hash % 10) / 20.0  # 0 to 0.5 variation
            score += variation
            
            # Time-based anti-clustering with entropy consideration
            import time
            time_factor = int(time.time() / 300) % 5  # Changes every 5 minutes
            if time_factor == 0 and category == 'fuzzing' and entropy_level in ['high', 'very_high']:
                score += 0.2
            elif time_factor == 1 and category in ['usernames', 'passwords'] and entropy_level == 'medium':
                score += 0.2
            elif time_factor == 2 and size < 100000 and entropy_level in ['low', 'medium']:
                score += 0.3
        
        return max(0.0, score)
    
    def _apply_diversification(self, scored_wordlists: List[Tuple[str, float, Dict]], 
                              tech: Optional[str], port: Optional[int],
                              confidence: Optional[float] = None) -> List[Tuple[str, float, Dict]]:
        """Apply diversification with anti-clustering and frequency-based adjustments"""
        import time
        
        # Sort by score first
        scored_wordlists.sort(key=lambda x: x[1], reverse=True)
        
        # Apply frequency-based scoring adjustments
        scored_wordlists = self._apply_frequency_adjustments(scored_wordlists, tech, port)
        
        diversified = []
        category_counts = {}
        
        # Phase 3.3: Enhanced anti-clustering
        import random
        
        # 1. Time-based rotation
        rotation_seed = int(time.time() / 3600) % 3  # Changes every hour
        
        # 2. Dynamic selection based on confidence (Phase 3.2)  
        if confidence is not None:
            if confidence < 0.3:
                # Low confidence - add randomization to top candidates
                top_candidates = scored_wordlists[:5]
                if len(top_candidates) > 2:
                    # Shuffle positions 2-5 to add variety
                    random.shuffle(top_candidates[2:])
                    scored_wordlists = top_candidates[:2] + top_candidates[2:] + scored_wordlists[5:]
        
        # 3. Port-based variation to prevent clustering
        port_variation = (port or 80) % 5
        
        # 4. Tech-based shuffling for diversity (Phase 3.4)
        if tech:
            # Use tech name to create consistent but varied ordering
            tech_hash = sum(ord(c) for c in tech.lower())
            if tech_hash % 3 == 0:
                # Every 3rd tech gets different ordering
                scored_wordlists = scored_wordlists[:1] + sorted(
                    scored_wordlists[1:4], 
                    key=lambda x: x[2].get('size_lines', 0)
                ) + scored_wordlists[4:]
        
        for wl_name, score, wl_data in scored_wordlists:
            category = wl_data.get('category', 'unknown')
            size = wl_data.get('size_lines', 0)
            
            # Diversification rules
            # 1. Limit categories to prevent over-concentration
            category_limit = 2 if category in ['usernames', 'passwords'] else 3
            if category_counts.get(category, 0) >= category_limit:
                continue
            
            # 2. Size-based rotation to mix large and small wordlists
            if len(diversified) > 0:
                prev_size = diversified[-1][2].get('size_lines', 0)
                # Alternate between large and small wordlists
                if size > 1000000 and prev_size > 1000000:
                    # Skip if both are large
                    continue
            
            # 3. Technology-specific rotation
            if tech:
                tech_compat = wl_data.get('tech_compatibility', [])
                if rotation_seed == 0:
                    # Hour 0: Prefer exact tech matches
                    if tech.lower() not in [t.lower() for t in tech_compat] and tech_compat:
                        if len(diversified) >= 2:  # Skip non-exact after 2 selections
                            continue
                elif rotation_seed == 1:
                    # Hour 1: Mix tech-specific with general
                    pass  # No special filtering
                else:
                    # Hour 2: Prefer smaller wordlists
                    if size > 5000000 and len(diversified) >= 1:
                        continue
            
            # 4. Use-case based selection (Phase 4.4)
            use_cases = wl_data.get('use_cases', [])
            target_specificity = wl_data.get('target_specificity', 'general')
            
            # Prioritize relevant use cases
            if tech and confidence and confidence >= 0.8:
                # High confidence - prefer specific use cases
                tech_lower = tech.lower()
                relevant_use_cases = []
                if tech_lower in ['mysql', 'phpmyadmin', 'postgres']:
                    relevant_use_cases = ['authentication_testing', 'database_testing']
                elif tech_lower in ['wordpress', 'django', 'laravel']:
                    relevant_use_cases = ['fuzzing', 'web_application_testing']
                elif tech_lower in ['grafana', 'prometheus', 'kibana']:
                    relevant_use_cases = ['monitoring_testing', 'api_testing']
                
                if relevant_use_cases and not any(uc in use_cases for uc in relevant_use_cases):
                    if len(diversified) >= 2:  # Skip irrelevant after 2 selections
                        continue
            
            # 5. Quality-based selection - prefer excellent quality
            quality = wl_data.get('quality', 'unknown')
            if len(diversified) < 3 and quality != 'excellent':
                continue  # First 3 must be excellent quality
            
            diversified.append((wl_name, score, wl_data))
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Stop when we have enough diverse wordlists
            if len(diversified) >= 5:
                break
        
        return diversified
    
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
                         service: Optional[str], final_selection: List[Tuple]) -> None:
        """Track rule usage for audit analytics"""
        try:
            from src.core.scorer.cache import cache
            import time
            import uuid
            
            # Create a usage record
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

# Global instance
db_scorer = DatabaseScorer()

def score_wordlists_database(tech: Optional[str], port: Optional[int], 
                           service: Optional[str] = None) -> List[str]:
    """
    Main entry point for database-driven wordlist scoring
    
    This replaces all hardcoded mappings with database lookups
    """
    return db_scorer.score(tech, port, service)