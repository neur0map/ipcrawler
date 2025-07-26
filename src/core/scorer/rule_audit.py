#!/usr/bin/env python3
"""
SmartList Rule Auditor

Audits SmartList mapping rules for quality and conflicts.

Usage:
    python rule_audit.py [--verbose] [--cache-days=30]
"""

import sys
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.scorer.rules import (
    EXACT_MATCH_RULES, TECH_CATEGORY_RULES, PORT_CATEGORY_RULES,
    SERVICE_KEYWORD_RULES, GENERIC_FALLBACK_RULES
)
from src.core.scorer.cache import cache

class RuleAuditor:
    """Audits SmartList mapping rules for quality and conflicts."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.issues = []
        self.warnings = []
        self.stats = {}
    
    def run_full_audit(self, cache_days: int = 30) -> Dict[str, Any]:
        """Run complete audit of mapping rules."""
        print("=" * 50)
        
        # 1. Analyze wordlist overlaps
        overlap_issues = self.analyze_wordlist_overlaps()
        
        # 2. Analyze rule usage from cache
        usage_issues = self.analyze_rule_usage(cache_days)
        
        # 3. Analyze repetitive patterns
        repetition_issues = self.analyze_repetitive_patterns()
        
        # 4. Analyze port conflicts
        port_issues = self.analyze_port_conflicts()
        
        # 5. Analyze pattern quality
        pattern_issues = self.analyze_pattern_quality()
        
        # Summary
        return {
            "overlap_issues": overlap_issues,
            "usage_issues": usage_issues,
            "repetition_issues": repetition_issues,
            "port_issues": port_issues,
            "pattern_issues": pattern_issues,
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings)
        }
    
    def analyze_wordlist_overlaps(self):
        """Detect wordlists that appear in multiple rule categories."""
        wordlist_sources = defaultdict(list)
        
        # Collect all wordlists and their sources
        
        # Exact match rules
        for key, wordlists in EXACT_MATCH_RULES.items():
            tech, port = key
            source = f"exact:{tech}:{port}"
            for wl in wordlists:
                wordlist_sources[wl].append(source)
        
        # Tech category rules
        for category, config in TECH_CATEGORY_RULES.items():
            source = f"tech_category:{category}"
            for wl in config.get('wordlists', []):
                wordlist_sources[wl].append(source)
        
        # Port category rules
        for category, config in PORT_CATEGORY_RULES.items():
            source = f"port_category:{category}"
            for wl in config.get('wordlists', []):
                wordlist_sources[wl].append(source)
        
        # Service keyword rules
        for keyword, wordlists in SERVICE_KEYWORD_RULES.items():
            source = f"keyword:{keyword}"
            for wl in wordlists:
                wordlist_sources[wl].append(source)
        
        # Generic fallback
        for wl in GENERIC_FALLBACK_RULES:
            wordlist_sources[wl].append("generic_fallback")
        
        # Find overlaps
        overlap_issues = []
        for wordlist, sources in wordlist_sources.items():
            if len(sources) > 1:
                severity = "ERROR" if len(sources) > 3 else "WARNING"
                issue = {
                    "wordlist": wordlist,
                    "sources": sources,
                    "count": len(sources),
                    "severity": severity
                }
                overlap_issues.append(issue)
                
                if severity == "ERROR":
                    self.issues.append(issue)
                else:
                    self.warnings.append(issue)
        
        # Print results
        if overlap_issues:
            print("\n📋 Wordlist Overlap Analysis:")
            overlap_issues.sort(key=lambda x: x["count"], reverse=True)
            for issue in overlap_issues[:10]:  # Top 10
                icon = "❌" if issue["severity"] == "ERROR" else "⚠️ "
                print(f"   {icon} {issue['wordlist']}: {issue['count']} sources")
        
        return overlap_issues
    
    def analyze_rule_usage(self, days_back: int = 30):
        """Analyze rule usage patterns from cache data."""
        try:
            entries = cache.search_selections(days_back=days_back, limit=500)
        except Exception:
            return []
        
        # Count rule usage
        rule_usage = Counter()
        wordlist_usage = Counter()
        
        for entry in entries:
            rule = entry.get('rule_matched', 'unknown')
            wordlists = entry.get('selected_wordlists', [])
            
            rule_usage[rule] += 1
            for wl in wordlists:
                wordlist_usage[wl] += 1
        
        total_selections = len(entries)
        usage_issues = []
        
        if total_selections == 0:
            return usage_issues
        
        # Find overused rules/wordlists (>80% of selections)
        overuse_threshold = total_selections * 0.8
        for item, count in wordlist_usage.most_common(5):
            if count > overuse_threshold:
                percentage = (count / total_selections) * 100
                issue = {
                    "type": "overused_wordlist",
                    "item": item,
                    "count": count,
                    "percentage": percentage,
                    "severity": "WARNING"
                }
                usage_issues.append(issue)
                self.warnings.append(issue)
        
        # Find unused exact rules
        used_exact_rules = {rule for rule in rule_usage.keys() if rule.startswith("exact:")}
        all_exact_rules = {f"exact:{tech}:{port}" for (tech, port) in EXACT_MATCH_RULES.keys()}
        unused_exact = all_exact_rules - used_exact_rules
        
        for rule in list(unused_exact)[:5]:  # Limit to 5
            issue = {
                "type": "unused_exact_rule",
                "item": rule,
                "count": 0,
                "severity": "INFO"
            }
            usage_issues.append(issue)
        
        # Print top usage
        if total_selections > 0:
            print("\n📊 Rule Usage Analysis:")
            for item, count in wordlist_usage.most_common(3):
                percentage = (count / total_selections) * 100
                icon = "🔥" if percentage > 50 else "📈"
                print(f"   {icon} {item}: {count} times ({percentage:.1f}%)")
        
        return usage_issues
        
    
    def analyze_repetitive_patterns(self):
        """Find rules that always recommend the same wordlists."""
        repetitive_issues = []
        
        # Check tech categories for repetitive patterns
        for category, config in TECH_CATEGORY_RULES.items():
            wordlists = config["wordlists"]
            if len(set(wordlists)) <= 3 and len(wordlists) >= 3:
                # Same 3 or fewer wordlists repeated
                issue = {
                    "type": "repetitive_tech_category",
                    "category": category,
                    "wordlists": wordlists,
                    "unique_count": len(set(wordlists)),
                    "severity": "WARNING"
                }
                repetitive_issues.append(issue)
                self.warnings.append(issue)
        
        # Check port categories
        for category, config in PORT_CATEGORY_RULES.items():
            wordlists = config["wordlists"]
            if len(set(wordlists)) <= 3 and len(wordlists) >= 3:
                issue = {
                    "type": "repetitive_port_category", 
                    "category": category,
                    "wordlists": wordlists,
                    "unique_count": len(set(wordlists)),
                    "severity": "WARNING"
                }
                repetitive_issues.append(issue)
                self.warnings.append(issue)
        
        # Print results
        if repetitive_issues:
            print("\n🔄 Repetitive Pattern Analysis:")
            for issue in repetitive_issues[:5]:
                print(f"   ⚠️  {issue['category']}: {issue['unique_count']} unique wordlists")
        
        return repetitive_issues
        
    
    def analyze_port_conflicts(self):
        """Detect ports that appear in multiple exclusive categories."""
        port_assignments = defaultdict(list)
        
        # Collect port assignments
        for category, config in PORT_CATEGORY_RULES.items():
            for port in config.get('ports', []):
                port_assignments[port].append(category)
        
        # Find conflicts
        port_issues = []
        for port, categories in port_assignments.items():
            if len(categories) > 1:
                issue = {
                    "port": port,
                    "categories": categories,
                    "count": len(categories),
                    "severity": "WARNING"
                }
                port_issues.append(issue)
                self.warnings.append(issue)
        
        # Print results
        if port_issues:
            print("\n🔍 Port Conflict Analysis:")
            for issue in port_issues[:5]:
                print(f"   ⚠️  Port {issue['port']}: {issue['count']} categories")
        
        return port_issues
        
    
    def analyze_pattern_quality(self):
        """Analyze regex pattern quality for potential issues."""
        pattern_issues = []
        
        for category, config in TECH_CATEGORY_RULES.items():
            if 'fallback_pattern' not in config:
                continue
                
            pattern = config["fallback_pattern"]
            
            # Check for overly broad patterns
            broad_patterns = [
                ".*", ".+", "\\w+", "\\S+", "[^\\s]+"
            ]
            
            for broad in broad_patterns:
                if broad in pattern:
                    issue = {
                        "type": "broad_pattern",
                        "category": category,
                        "pattern": pattern,
                        "broad_term": broad,
                        "severity": "WARNING"
                    }
                    pattern_issues.append(issue)
                    self.warnings.append(issue)
            
            # Check for missing word boundaries
            if not ("\\b" in pattern or "^" in pattern or "$" in pattern):
                issue = {
                    "type": "missing_word_boundary",
                    "category": category,
                    "pattern": pattern,
                    "severity": "INFO"
                }
                pattern_issues.append(issue)
        
        # Print results
        if pattern_issues:
            print("\n🎯 Pattern Quality Analysis:")
            for issue in pattern_issues[:5]:
                if issue["severity"] == "WARNING":
                    print(f"   ⚠️  {issue['category']}: {issue['type']}")
        
        return pattern_issues
        
    
    def print_summary(self):
        """Print audit summary."""
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        
        print("\n" + "=" * 50)
        print("📋 AUDIT SUMMARY")
        print("=" * 50)
        
        if total_issues == 0 and total_warnings == 0:
            print("✅ No issues found - rules look good!")
        elif total_issues == 0:
            print(f"⚠️  {total_warnings} warnings found (no critical issues)")
        else:
            print(f"❌ {total_issues} issues and {total_warnings} warnings found")
        
        # Top priority fixes
        if total_issues > 0:
            print("\n🚨 Top Priority Fixes:")
            for issue in self.issues[:3]:
                print(f"   • {issue}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if total_issues == 0 and total_warnings == 0:
            print("   • Rules are well-configured")
            print("   • Consider running audit regularly")
        else:
            print("   • Review wordlist overlaps to reduce conflicts")
            print("   • Consider consolidating repetitive rules")
            print("   • Monitor rule usage patterns")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Audit SmartList mapping rules")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Show detailed output")
    parser.add_argument("--cache-days", type=int, default=30,
                       help="Days of cache data to analyze (default: 30)")
    
    args = parser.parse_args()
    
    auditor = RuleAuditor(verbose=args.verbose)
    results = auditor.run_full_audit(cache_days=args.cache_days)
    
    # Exit with error code if critical issues found
    return 1 if len(auditor.issues) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
