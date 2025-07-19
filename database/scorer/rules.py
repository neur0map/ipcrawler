"""
Scoring rules and rule management for the wordlist scorer.
"""

from typing import List, Dict, Optional, Callable, Tuple, Any
import re
import logging
from datetime import datetime, timedelta
from collections import Counter
from .models import ScoringContext, ScoringRule
from .mappings import (
    TECH_CATEGORY_RULES,
    PORT_CATEGORY_RULES,
    SERVICE_KEYWORD_RULES,
    get_exact_match
)

logger = logging.getLogger(__name__)


class RuleEngine:
    """Engine for applying scoring rules with fallback hierarchy."""
    
    def __init__(self):
        self.rules: List[ScoringRule] = []
        self._compile_patterns()
        self._rule_frequency_cache = {}  # Cache for rule frequency data
        self._last_frequency_update = None
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self.tech_patterns = {}
        for category, config in TECH_CATEGORY_RULES.items():
            if "fallback_pattern" in config:
                self.tech_patterns[category] = re.compile(
                    config["fallback_pattern"], 
                    re.IGNORECASE
                )
    
    def apply_exact_match(self, context: ScoringContext) -> Tuple[List[str], List[str], float]:
        """
        Apply exact tech+port matching rules with frequency-based scoring.
        
        Returns:
            Tuple of (wordlists, matched_rules, score)
        """
        if not context.tech:
            return [], [], 0.0
        
        wordlists = get_exact_match(context.tech, context.port)
        if wordlists:
            rule_name = f"exact:{context.tech}:{context.port}"
            
            # Apply frequency-based scoring adjustment
            base_score = 1.0
            adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
            
            # Add synergy bonus for tech+path combinations
            synergy_bonus = self._calculate_synergy_bonus(context, wordlists)
            final_score = min(1.0, adjusted_score + synergy_bonus)
            
            logger.debug(f"Exact match scoring: base={base_score:.3f}, adjusted={adjusted_score:.3f}, synergy={synergy_bonus:.3f}, final={final_score:.3f}")
            
            return wordlists, [rule_name], final_score
        
        return [], [], 0.0
    
    def apply_tech_category(self, context: ScoringContext) -> Tuple[List[str], List[str], float]:
        """
        Apply technology category rules with pattern fallback and frequency scoring.
        
        Returns:
            Tuple of (wordlists, matched_rules, score)
        """
        wordlists = []
        matched_rules = []
        score = 0.0
        
        # First try exact tech match
        if context.tech:
            for category, config in TECH_CATEGORY_RULES.items():
                if context.tech in config["matches"]:
                    wordlists.extend(config["wordlists"])
                    rule_name = f"tech_category:{category}"
                    matched_rules.append(rule_name)
                    
                    # Apply frequency-based scoring
                    base_score = config["weight"]
                    adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
                    synergy_bonus = self._calculate_synergy_bonus(context, wordlists)
                    score = min(1.0, adjusted_score + synergy_bonus)
                    
                    return wordlists, matched_rules, score
        
        # Fallback to pattern matching on service description
        for category, pattern in self.tech_patterns.items():
            if pattern.search(context.service):
                config = TECH_CATEGORY_RULES[category]
                wordlists.extend(config["wordlists"])
                rule_name = f"tech_pattern:{category}"
                matched_rules.append(rule_name)
                
                # Lower base score for pattern match vs exact match
                base_score = config["weight"] * 0.75
                adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
                synergy_bonus = self._calculate_synergy_bonus(context, wordlists)
                score = min(1.0, adjusted_score + synergy_bonus)
                
                return wordlists, matched_rules, score
        
        return wordlists, matched_rules, score
    
    def apply_port_category(self, context: ScoringContext) -> Tuple[List[str], List[str], float]:
        """
        Apply port-based category rules with frequency scoring.
        
        Returns:
            Tuple of (wordlists, matched_rules, score)
        """
        wordlists = []
        matched_rules = []
        score = 0.0
        
        for category, config in PORT_CATEGORY_RULES.items():
            if context.port in config["ports"]:
                wordlists.extend(config["wordlists"])
                rule_name = f"port:{category}"
                matched_rules.append(rule_name)
                
                # Apply frequency-based scoring
                base_score = config["weight"]
                adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
                synergy_bonus = self._calculate_synergy_bonus(context, wordlists)
                score = min(1.0, adjusted_score + synergy_bonus)
                
                # Don't break - a port might match multiple categories
                # but we'll take the first match for simplicity
                break
        
        return wordlists, matched_rules, score
    
    def apply_service_keywords(self, context: ScoringContext) -> Tuple[List[str], List[str], float]:
        """
        Apply service keyword matching rules with frequency scoring.
        
        Returns:
            Tuple of (wordlists, matched_rules, score)
        """
        wordlists = []
        matched_rules = []
        score = 0.0
        
        service_lower = context.service.lower()
        
        for keyword, lists in SERVICE_KEYWORD_RULES.items():
            if keyword in service_lower:
                wordlists.extend(lists)
                rule_name = f"keyword:{keyword}"
                matched_rules.append(rule_name)
                
                # Apply frequency-based scoring
                base_score = 0.5  # Keyword matches get moderate base score
                adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
                score = max(score, adjusted_score)
        
        return wordlists, matched_rules, score
    
    def get_rule_priority(self, rule_name: str) -> int:
        """
        Get priority for a rule (lower number = higher priority).
        Used for sorting and conflict resolution.
        """
        if rule_name.startswith("exact:"):
            return 1
        elif rule_name.startswith("tech_category:"):
            return 2
        elif rule_name.startswith("tech_pattern:"):
            return 3
        elif rule_name.startswith("port:"):
            return 4
        elif rule_name.startswith("keyword:"):
            return 5
        else:
            return 99  # Generic/unknown
    
    def deduplicate_wordlists(self, wordlists: List[str]) -> List[str]:
        """Remove duplicates while preserving order."""
        seen = set()
        result = []
        for wl in wordlists:
            if wl not in seen:
                seen.add(wl)
                result.append(wl)
        return result
    
    def validate_rules(self) -> Dict[str, List[str]]:
        """
        Validate rule configuration for potential issues.
        
        Returns:
            Dict of warnings/errors found
        """
        issues = {
            "warnings": [],
            "errors": []
        }
        
        # Check for wordlist references
        all_wordlists = set()
        
        # Collect all referenced wordlists
        for wl_list in EXACT_MATCH_RULES.values():
            all_wordlists.update(wl_list)
        
        for config in TECH_CATEGORY_RULES.values():
            all_wordlists.update(config["wordlists"])
        
        for config in PORT_CATEGORY_RULES.values():
            all_wordlists.update(config["wordlists"])
        
        for wl_list in SERVICE_KEYWORD_RULES.values():
            all_wordlists.update(wl_list)
        
        # Check for duplicate wordlist names (potential typos)
        wordlist_counts = {}
        for wl in all_wordlists:
            base_name = wl.lower()
            wordlist_counts[base_name] = wordlist_counts.get(base_name, 0) + 1
        
        for name, count in wordlist_counts.items():
            if count > 1:
                issues["warnings"].append(
                    f"Potential duplicate wordlist variants: {name}"
                )
        
        # Check for overlapping port definitions
        port_usage = {}
        for category, config in PORT_CATEGORY_RULES.items():
            for port in config["ports"]:
                if port in port_usage:
                    issues["warnings"].append(
                        f"Port {port} defined in multiple categories: "
                        f"{port_usage[port]} and {category}"
                    )
                else:
                    port_usage[port] = category
        
        # Check weight values
        for category, config in TECH_CATEGORY_RULES.items():
            if "weight" in config:
                weight = config["weight"]
                if not 0.0 <= weight <= 1.0:
                    issues["errors"].append(
                        f"Invalid weight {weight} in tech category {category}"
                    )
        
        return issues
    
    def _apply_frequency_adjustment(self, rule_name: str, base_score: float) -> float:
        """
        Apply frequency-based scoring adjustment to boost rare signals and penalize common ones.
        
        Args:
            rule_name: Name of the rule being applied
            base_score: Base score before frequency adjustment
            
        Returns:
            Adjusted score
        """
        frequency = self._get_rule_frequency(rule_name)
        
        # Frequency-based adjustments
        if frequency < 0.2:  # Rare signal (< 20% of selections)
            adjustment = 0.1
            logger.debug(f"Rare signal bonus: {rule_name} (freq: {frequency:.3f}) +{adjustment}")
        elif frequency > 0.8:  # Overused signal (> 80% of selections)
            adjustment = -0.1
            logger.debug(f"Overused penalty: {rule_name} (freq: {frequency:.3f}) {adjustment}")
        else:
            adjustment = 0.0
        
        return max(0.1, min(1.0, base_score + adjustment))
    
    def _calculate_synergy_bonus(self, context: ScoringContext, wordlists: List[str]) -> float:
        """
        Calculate bonus for tech+path synergy combinations.
        
        Args:
            context: Scoring context
            wordlists: Recommended wordlists
            
        Returns:
            Synergy bonus (0.0 to 0.05)
        """
        if not context.tech:
            return 0.0
        
        synergy_patterns = {
            "tomcat": ["manager", "servlet", "jsp"],
            "jenkins": ["jenkins", "build", "ci"],
            "gitlab": ["gitlab", "git", "repository"],
            "phpmyadmin": ["pma", "phpmyadmin", "mysql"],
            "wordpress": ["wp-", "wordpress", "blog"],
            "drupal": ["drupal", "node", "module"],
            "grafana": ["grafana", "dashboard", "metrics"]
        }
        
        tech_lower = context.tech.lower()
        if tech_lower in synergy_patterns:
            synergy_terms = synergy_patterns[tech_lower]
            
            # Check if any wordlists contain synergy terms
            for wordlist in wordlists:
                wordlist_lower = wordlist.lower()
                if any(term in wordlist_lower for term in synergy_terms):
                    logger.debug(f"Synergy bonus: {context.tech} + {wordlist}")
                    return 0.05
        
        return 0.0
    
    def _get_rule_frequency(self, rule_name: str) -> float:
        """
        Get frequency of rule usage from cache data.
        
        Args:
            rule_name: Rule name to check frequency for
            
        Returns:
            Frequency as ratio (0.0 to 1.0)
        """
        # Update frequency cache if needed
        self._update_frequency_cache()
        
        return self._rule_frequency_cache.get(rule_name, 0.5)  # Default to middle frequency
    
    def _update_frequency_cache(self):
        """
        Update rule frequency cache from recent selections.
        """
        now = datetime.utcnow()
        
        # Update cache every hour
        if (self._last_frequency_update is None or 
            (now - self._last_frequency_update) > timedelta(hours=1)):
            
            try:
                # Import here to avoid circular imports
                from .cache import cache
                
                # Get recent selections (last 30 days)
                entries = cache.search_selections(days_back=30, limit=500)
                
                if entries:
                    # Count rule usage
                    rule_counts = Counter()
                    total_selections = len(entries)
                    
                    for entry in entries:
                        for rule in entry.result.matched_rules:
                            rule_counts[rule] += 1
                    
                    # Calculate frequencies
                    self._rule_frequency_cache = {
                        rule: count / total_selections
                        for rule, count in rule_counts.items()
                    }
                    
                    logger.debug(f"Updated rule frequency cache with {len(self._rule_frequency_cache)} rules from {total_selections} selections")
                
                self._last_frequency_update = now
                
            except Exception as e:
                logger.warning(f"Failed to update rule frequency cache: {e}")
                # Use default frequencies if cache update fails
                if not self._rule_frequency_cache:
                    self._rule_frequency_cache = {}


# Global rule engine instance
rule_engine = RuleEngine()


def get_rule_frequency_stats() -> Dict[str, Any]:
    """
    Get current rule frequency statistics.
    
    Returns:
        Dict with frequency statistics
    """
    rule_engine._update_frequency_cache()
    
    frequencies = rule_engine._rule_frequency_cache
    if not frequencies:
        return {"total_rules": 0, "most_frequent": [], "least_frequent": []}
    
    sorted_frequencies = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "total_rules": len(frequencies),
        "most_frequent": sorted_frequencies[:5],
        "least_frequent": sorted_frequencies[-5:],
        "average_frequency": sum(frequencies.values()) / len(frequencies)
    }