"""
Scoring rules and rule management for the wordlist scorer.
"""

from typing import List, Dict, Optional, Callable, Tuple
import re
from .models import ScoringContext, ScoringRule
from .mappings import (
    TECH_CATEGORY_RULES,
    PORT_CATEGORY_RULES,
    SERVICE_KEYWORD_RULES,
    get_exact_match
)


class RuleEngine:
    """Engine for applying scoring rules with fallback hierarchy."""
    
    def __init__(self):
        self.rules: List[ScoringRule] = []
        self._compile_patterns()
    
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
        Apply exact tech+port matching rules.
        
        Returns:
            Tuple of (wordlists, matched_rules, score)
        """
        if not context.tech:
            return [], [], 0.0
        
        wordlists = get_exact_match(context.tech, context.port)
        if wordlists:
            rule_name = f"exact:{context.tech}:{context.port}"
            return wordlists, [rule_name], 1.0
        
        return [], [], 0.0
    
    def apply_tech_category(self, context: ScoringContext) -> Tuple[List[str], List[str], float]:
        """
        Apply technology category rules with pattern fallback.
        
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
                    matched_rules.append(f"tech_category:{category}")
                    score = config["weight"]
                    return wordlists, matched_rules, score
        
        # Fallback to pattern matching on service description
        for category, pattern in self.tech_patterns.items():
            if pattern.search(context.service):
                config = TECH_CATEGORY_RULES[category]
                wordlists.extend(config["wordlists"])
                matched_rules.append(f"tech_pattern:{category}")
                # Lower score for pattern match vs exact match
                score = config["weight"] * 0.75
                return wordlists, matched_rules, score
        
        return wordlists, matched_rules, score
    
    def apply_port_category(self, context: ScoringContext) -> Tuple[List[str], List[str], float]:
        """
        Apply port-based category rules.
        
        Returns:
            Tuple of (wordlists, matched_rules, score)
        """
        wordlists = []
        matched_rules = []
        score = 0.0
        
        for category, config in PORT_CATEGORY_RULES.items():
            if context.port in config["ports"]:
                wordlists.extend(config["wordlists"])
                matched_rules.append(f"port:{category}")
                score = config["weight"]
                # Don't break - a port might match multiple categories
                # but we'll take the first match for simplicity
                break
        
        return wordlists, matched_rules, score
    
    def apply_service_keywords(self, context: ScoringContext) -> Tuple[List[str], List[str], float]:
        """
        Apply service keyword matching rules.
        
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
                matched_rules.append(f"keyword:{keyword}")
                score = max(score, 0.5)  # Keyword matches get moderate score
        
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


# Global rule engine instance
rule_engine = RuleEngine()