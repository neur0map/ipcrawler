#!/usr/bin/env python3
"""
SmartList Scoring Rules Engine

Clean, database-driven rule engine for wordlist recommendations.
Eliminated hardcoded mappings in favor of database queries.
"""

import logging
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ScoringRule:
    """Represents a scoring rule with metadata"""
    name: str
    category: str  # 'tech_exact', 'tech_category', 'port', 'service'
    patterns: List[str]
    weight: float
    priority: int = 1  # Lower number = higher priority
    conditions: Dict[str, Any] = None


@dataclass
class RuleMatch:
    """Result of rule matching"""
    rule: ScoringRule
    confidence: float
    matched_patterns: List[str]
    context: Dict[str, Any]


class RuleEngine:
    """Clean rule engine for database-driven scoring"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent.parent / "database"
        self.tech_db = None
        self.port_db = None
        self.catalog = None
        self._rule_frequency_cache = {}
        self._last_frequency_update = None
        self._load_databases()
    
    def _load_databases(self):
        """Load database files"""
        try:
            # Load technology database
            tech_db_path = self.db_path / "technologies" / "tech_db.json"
            if tech_db_path.exists():
                with open(tech_db_path, 'r') as f:
                    self.tech_db = json.load(f)
                logger.debug(f"Loaded tech database with {len(self.tech_db)} categories")
            
            # Load port database
            port_db_path = self.db_path / "ports" / "port_db.json"
            if port_db_path.exists():
                with open(port_db_path, 'r') as f:
                    self.port_db = json.load(f)
                logger.debug(f"Loaded port database with {len(self.port_db)} ports")
            
            # Load wordlist catalog
            catalog_path = self.db_path / "wordlists" / "seclists_catalog.json"
            if catalog_path.exists():
                with open(catalog_path, 'r') as f:
                    self.catalog = json.load(f)
                logger.debug(f"Loaded wordlist catalog")
                    
        except Exception as e:
            logger.error(f"Failed to load databases: {e}")
    
    def match_rules(self, tech: Optional[str], port: Optional[int], 
                   service: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> List[RuleMatch]:
        """Match rules against context with database lookups"""
        matches = []
        
        # 1. Exact technology matches from database
        if tech and self.tech_db:
            tech_matches = self._match_tech_rules(tech, context)
            matches.extend(tech_matches)
        
        # 2. Port-based matches from database
        if port and self.port_db:
            port_matches = self._match_port_rules(port, context)
            matches.extend(port_matches)
        
        # 3. Service keyword matches
        if service:
            service_matches = self._match_service_rules(service, context)
            matches.extend(service_matches)
        
        # Sort by priority and confidence
        matches.sort(key=lambda x: (x.rule.priority, -x.confidence))
        
        return matches
    
    def _match_tech_rules(self, tech: str, context: Optional[Dict[str, Any]]) -> List[RuleMatch]:
        """Match technology rules using tech_db"""
        matches = []
        tech_lower = tech.lower()
        
        # Search through all tech categories
        for category, technologies in self.tech_db.items():
            if tech_lower in technologies:
                tech_info = technologies[tech_lower]
                
                # Create rule from database entry
                rule = ScoringRule(
                    name=f"tech_exact:{tech}",
                    category="tech_exact",
                    patterns=tech_info.get('indicators', {}).get('response_patterns', []),
                    weight=0.9,  # High weight for exact matches
                    priority=1
                )
                
                # Calculate confidence based on database weights
                confidence_weights = tech_info.get('confidence_weights', {})
                base_confidence = 0.8
                
                # Adjust confidence if we have response patterns in context
                if context and 'response_content' in context:
                    pattern_matches = 0
                    total_patterns = len(rule.patterns)
                    
                    if total_patterns > 0:
                        content = context['response_content'].lower()
                        for pattern in rule.patterns:
                            if pattern.lower() in content:
                                pattern_matches += 1
                        
                        pattern_confidence = pattern_matches / total_patterns
                        confidence = base_confidence * (0.5 + 0.5 * pattern_confidence)
                    else:
                        confidence = base_confidence
                else:
                    confidence = base_confidence
                
                matches.append(RuleMatch(
                    rule=rule,
                    confidence=confidence,
                    matched_patterns=[tech],
                    context={'tech_category': category, 'tech_info': tech_info}
                ))
                
                # Also add category-based rule for broader matching
                category_rule = ScoringRule(
                    name=f"tech_category:{category}",
                    category="tech_category", 
                    patterns=[],
                    weight=0.6,  # Lower weight for category matches
                    priority=2
                )
                
                matches.append(RuleMatch(
                    rule=category_rule,
                    confidence=0.6,
                    matched_patterns=[category],
                    context={'tech_category': category}
                ))
                
                break  # Found exact match, stop searching
        
        return matches
    
    def _match_port_rules(self, port: int, context: Optional[Dict[str, Any]]) -> List[RuleMatch]:
        """Match port rules using port_db"""
        matches = []
        port_str = str(port)
        
        if port_str in self.port_db:
            port_info = self.port_db[port_str]
            
            # Create rule from port database
            service_category = port_info.get('classification', {}).get('category', 'unknown')
            rule = ScoringRule(
                name=f"port:{port}",
                category="port",
                patterns=[],
                weight=0.7,
                priority=2
            )
            
            # Calculate confidence based on port classification
            risk_level = port_info.get('classification', {}).get('risk_level', 'unknown')
            confidence = 0.7  # Base confidence
            
            if risk_level == 'high':
                confidence = 0.8
            elif risk_level == 'medium':
                confidence = 0.6
            elif risk_level == 'low':
                confidence = 0.5
            
            matches.append(RuleMatch(
                rule=rule,
                confidence=confidence,
                matched_patterns=[port_str],
                context={
                    'port_info': port_info,
                    'service_category': service_category,
                    'risk_level': risk_level
                }
            ))
        
        return matches
    
    def _match_service_rules(self, service: str, context: Optional[Dict[str, Any]]) -> List[RuleMatch]:
        """Match service keyword rules"""
        matches = []
        service_lower = service.lower()
        
        # Simple keyword matching for service names
        service_keywords = ['http', 'https', 'web', 'ftp', 'ssh', 'mysql', 'postgres']
        
        for keyword in service_keywords:
            if keyword in service_lower:
                rule = ScoringRule(
                    name=f"service_keyword:{keyword}",
                    category="service",
                    patterns=[keyword],
                    weight=0.5,
                    priority=3
                )
                
                matches.append(RuleMatch(
                    rule=rule,
                    confidence=0.5,
                    matched_patterns=[keyword],
                    context={'service_keyword': keyword}
                ))
        
        return matches
    
    def get_wordlists_for_rules(self, rule_matches: List[RuleMatch]) -> List[str]:
        """Get recommended wordlists based on rule matches"""
        if not self.catalog:
            return []
        
        recommended = []
        seen = set()
        
        for match in rule_matches:
            rule = match.rule
            context = match.context
            
            # Get wordlists based on rule category
            if rule.category == 'tech_exact':
                wordlists = self._get_tech_wordlists(context)
            elif rule.category == 'tech_category':
                wordlists = self._get_category_wordlists(context)
            elif rule.category == 'port':
                wordlists = self._get_port_wordlists(context)
            elif rule.category == 'service':
                wordlists = self._get_service_wordlists(context)
            else:
                wordlists = []
            
            # Add unique wordlists
            for wl in wordlists:
                if wl not in seen:
                    recommended.append(wl)
                    seen.add(wl)
                    
                    # Limit total recommendations
                    if len(recommended) >= 10:
                        break
            
            if len(recommended) >= 10:
                break
        
        return recommended[:5]  # Return top 5
    
    def _get_tech_wordlists(self, context: Dict[str, Any]) -> List[str]:
        """Get wordlists for specific technology"""
        wordlists = []
        tech_info = context.get('tech_info', {})
        
        # Use discovery_paths from tech_db if available
        discovery_paths = tech_info.get('discovery_paths', [])
        
        # Find wordlists compatible with this technology
        for wl in self.catalog.get('wordlists', []):
            tech_compatibility = wl.get('tech_compatibility', [])
            category = wl.get('category', '')
            
            # Check direct tech compatibility
            tech_category = context.get('tech_category', '')
            if tech_category in ['cms', 'web_framework'] and category == 'fuzzing':
                wordlists.append(wl['name'])
            elif any(tech_category in compat.lower() for compat in tech_compatibility):
                wordlists.append(wl['name'])
        
        return wordlists[:3]
    
    def _get_category_wordlists(self, context: Dict[str, Any]) -> List[str]:
        """Get wordlists for technology category"""
        wordlists = []
        tech_category = context.get('tech_category', '')
        
        category_mapping = {
            'cms': ['fuzzing'],
            'web_framework': ['fuzzing'], 
            'web_server': ['fuzzing', 'other'],
            'database': ['other'],
            'proxy': ['other']
        }
        
        target_categories = category_mapping.get(tech_category, ['fuzzing'])
        
        for wl in self.catalog.get('wordlists', []):
            if wl.get('category') in target_categories:
                wordlists.append(wl['name'])
        
        return wordlists[:2]
    
    def _get_port_wordlists(self, context: Dict[str, Any]) -> List[str]:
        """Get wordlists for port-based service"""
        wordlists = []
        service_category = context.get('service_category', '')
        
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
        
        return wordlists[:2]
    
    def _get_service_wordlists(self, context: Dict[str, Any]) -> List[str]:
        """Get wordlists for service keywords"""
        wordlists = []
        service_keyword = context.get('service_keyword', '')
        
        # Simple mapping for service keywords
        if service_keyword in ['http', 'https', 'web']:
            for wl in self.catalog.get('wordlists', []):
                if wl.get('category') == 'fuzzing':
                    wordlists.append(wl['name'])
        
        return wordlists[:2]
    
    def get_fallback_wordlists(self) -> List[str]:
        """Get fallback wordlists when no rules match"""
        if not self.catalog:
            return []
        
        fallback = []
        
        # Get high-quality general wordlists
        for wl in self.catalog.get('wordlists', []):
            quality = wl.get('quality', '')
            category = wl.get('category', '')
            size = wl.get('size_lines', 0)
            
            # Small, high-quality lists
            if quality == 'excellent' and size < 100000:
                fallback.append(wl['name'])
            elif category == 'fuzzing' and size < 50000:
                fallback.append(wl['name'])
        
        return fallback[:3]
    
    def validate_rules(self) -> Dict[str, List[str]]:
        """Validate rule engine configuration"""
        issues = {
            "warnings": [],
            "errors": []
        }
        
        # Check database availability
        if not self.tech_db:
            issues["errors"].append("Technology database not loaded")
        
        if not self.port_db:
            issues["errors"].append("Port database not loaded")
            
        if not self.catalog:
            issues["errors"].append("Wordlist catalog not loaded")
        
        # Check database integrity
        if self.tech_db:
            for category, technologies in self.tech_db.items():
                for tech, info in technologies.items():
                    if not info.get('discovery_paths'):
                        issues["warnings"].append(f"Technology {tech} missing discovery_paths")
        
        return issues


# Global rule engine instance
rule_engine = RuleEngine()


def get_rule_engine() -> RuleEngine:
    """Get the global rule engine instance"""
    return rule_engine


def validate_rule_engine() -> Dict[str, Any]:
    """Validate the rule engine configuration"""
    return rule_engine.validate_rules()


def get_rule_statistics() -> Dict[str, Any]:
    """Get statistics about rule usage"""
    return {
        "databases_loaded": {
            "tech_db": rule_engine.tech_db is not None,
            "port_db": rule_engine.port_db is not None, 
            "catalog": rule_engine.catalog is not None
        },
        "tech_categories": len(rule_engine.tech_db) if rule_engine.tech_db else 0,
        "total_ports": len(rule_engine.port_db) if rule_engine.port_db else 0,
        "wordlist_count": len(rule_engine.catalog.get('wordlists', [])) if rule_engine.catalog else 0
    }