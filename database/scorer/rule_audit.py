#!/usr/bin/env python3
"""
Rule audit tool for analyzing SmartList mapping quality and detecting problems.

Usage:
    python rule_audit.py [--verbose] [--cache-days=30]
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.scorer.mappings import (
    EXACT_MATCH_RULES, TECH_CATEGORY_RULES, PORT_CATEGORY_RULES, 
    SERVICE_KEYWORD_RULES, GENERIC_FALLBACK
)
from database.scorer.cache import cache


class RuleAuditor:
    """Audits SmartList mapping rules for quality and conflicts."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.issues = []
        self.warnings = []
        self.stats = {}
    
    def run_full_audit(self, cache_days: int = 30) -> Dict[str, Any]:
        """Run complete audit of mapping rules."""
        print("🔍 SmartList Rule Audit Report")
        print("=" * 50)
        
        # 1. Analyze wordlist overlaps
        print("\n📊 WORDLIST OVERLAP ANALYSIS")
        overlap_issues = self.analyze_wordlist_overlaps()
        
        # 2. Analyze rule usage from cache
        print("\n📈 RULE USAGE ANALYSIS")
        usage_issues = self.analyze_rule_usage(cache_days)
        
        # 3. Analyze repetitive patterns
        print("\n🔄 REPETITION ANALYSIS") 
        repetition_issues = self.analyze_repetitive_patterns()
        
        # 4. Analyze port conflicts
        print("\n⚠️  PORT CONFLICT ANALYSIS")
        port_issues = self.analyze_port_conflicts()
        
        # 5. Analyze pattern quality
        print("\n🎯 PATTERN QUALITY ANALYSIS")
        pattern_issues = self.analyze_pattern_quality()
        
        # Summary
        print("\n📋 AUDIT SUMMARY")
        self.print_summary()
        
        return {
            "overlap_issues": overlap_issues,
            "usage_issues": usage_issues,
            "repetition_issues": repetition_issues,
            "port_issues": port_issues,
            "pattern_issues": pattern_issues,
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings)
        }
    
    def analyze_wordlist_overlaps(self) -> List[Dict[str, Any]]:
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
            for wl in config["wordlists"]:
                wordlist_sources[wl].append(source)
        
        # Port category rules
        for category, config in PORT_CATEGORY_RULES.items():
            source = f"port_category:{category}"
            for wl in config["wordlists"]:
                wordlist_sources[wl].append(source)
        
        # Service keyword rules
        for keyword, wordlists in SERVICE_KEYWORD_RULES.items():
            source = f"keyword:{keyword}"
            for wl in wordlists:
                wordlist_sources[wl].append(source)
        
        # Generic fallback
        for wl in GENERIC_FALLBACK:
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
                    self.issues.append(f"❌ OVERLAP: '{wordlist}' appears in {len(sources)} categories: {', '.join(sources)}")
                else:
                    self.warnings.append(f"⚠️  OVERLAP: '{wordlist}' appears in {len(sources)} categories: {', '.join(sources)}")
        
        # Print results
        if overlap_issues:
            overlap_issues.sort(key=lambda x: x["count"], reverse=True)
            for issue in overlap_issues[:10]:  # Top 10
                icon = "❌" if issue["severity"] == "ERROR" else "⚠️ "
                print(f"{icon} '{issue['wordlist']}' in {issue['count']} categories")
                if self.verbose:
                    for source in issue["sources"]:
                        print(f"    - {source}")
        else:
            print("✅ No wordlist overlaps detected")
        
        return overlap_issues
    
    def analyze_rule_usage(self, days_back: int) -> List[Dict[str, Any]]:
        """Analyze rule usage patterns from cache data."""
        try:
            entries = cache.search_selections(days_back=days_back, limit=500)
        except Exception as e:
            print(f"⚠️  Could not access cache data: {e}")
            return []
        
        if not entries:
            print("⚠️  No cache data available for analysis")
            return []
        
        # Count rule usage
        rule_usage = Counter()
        wordlist_usage = Counter()
        
        for entry in entries:
            for rule in entry.result.matched_rules:
                rule_usage[rule] += 1
            for wl in entry.result.wordlists:
                wordlist_usage[wl] += 1
        
        total_selections = len(entries)
        usage_issues = []
        
        # Find overused rules/wordlists (>80% of selections)
        overuse_threshold = total_selections * 0.8
        for item, count in wordlist_usage.most_common():
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
                self.warnings.append(f"⚠️  OVERUSED: '{item}' appears in {percentage:.1f}% of selections")
        
        # Find unused exact rules
        used_exact_rules = {rule for rule in rule_usage.keys() if rule.startswith("exact:")}
        all_exact_rules = {f"exact:{tech}:{port}" for (tech, port) in EXACT_MATCH_RULES.keys()}
        unused_exact = all_exact_rules - used_exact_rules
        
        for rule in unused_exact:
            issue = {
                "type": "unused_exact_rule",
                "item": rule,
                "count": 0,
                "severity": "INFO"
            }
            usage_issues.append(issue)
            if self.verbose:
                print(f"ℹ️  UNUSED: '{rule}' - 0 matches in {days_back} days")
        
        # Print top usage
        print(f"📊 Analysis of {total_selections} selections over {days_back} days:")
        print("\nMost used wordlists:")
        for wl, count in wordlist_usage.most_common(5):
            percentage = (count / total_selections) * 100
            icon = "🔥" if percentage > 50 else "📈"
            print(f"{icon} {wl}: {count} times ({percentage:.1f}%)")
        
        print(f"\nUnused exact rules: {len(unused_exact)}")
        
        return usage_issues
    
    def analyze_repetitive_patterns(self) -> List[Dict[str, Any]]:
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
                self.warnings.append(f"🔄 REPETITIVE: tech_category '{category}' always recommends same {len(set(wordlists))} wordlists")
        
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
                self.warnings.append(f"🔄 REPETITIVE: port_category '{category}' always recommends same {len(set(wordlists))} wordlists")
        
        # Print results
        if repetitive_issues:
            print(f"Found {len(repetitive_issues)} repetitive patterns:")
            for issue in repetitive_issues:
                if self.verbose:
                    print(f"🔄 {issue['type']}: {issue['category']} -> {issue['wordlists']}")
        else:
            print("✅ No repetitive patterns detected")
        
        return repetitive_issues
    
    def analyze_port_conflicts(self) -> List[Dict[str, Any]]:
        """Detect ports that appear in multiple exclusive categories."""
        port_assignments = defaultdict(list)
        
        # Collect port assignments
        for category, config in PORT_CATEGORY_RULES.items():
            for port in config["ports"]:
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
                self.warnings.append(f"⚠️  PORT CONFLICT: Port {port} in categories: {', '.join(categories)}")
        
        # Print results
        if port_issues:
            print(f"Found {len(port_issues)} port conflicts:")
            for issue in port_issues:
                print(f"⚠️  Port {issue['port']}: {', '.join(issue['categories'])}")
        else:
            print("✅ No port conflicts detected")
        
        return port_issues
    
    def analyze_pattern_quality(self) -> List[Dict[str, Any]]:
        """Analyze regex pattern quality for potential issues."""
        pattern_issues = []
        
        for category, config in TECH_CATEGORY_RULES.items():
            if "fallback_pattern" not in config:
                continue
            
            pattern = config["fallback_pattern"]
            
            # Check for overly broad patterns
            broad_patterns = [
                r"admin", r"management", r"api", r"web", r"http"
            ]
            
            for broad in broad_patterns:
                if broad in pattern.lower():
                    issue = {
                        "type": "broad_pattern",
                        "category": category,
                        "pattern": pattern,
                        "broad_term": broad,
                        "severity": "WARNING"
                    }
                    pattern_issues.append(issue)
                    self.warnings.append(f"⚠️  BROAD PATTERN: '{category}' pattern contains '{broad}' - may match too widely")
            
            # Check for missing word boundaries
            if r"\b" not in pattern:
                issue = {
                    "type": "missing_word_boundary",
                    "category": category,
                    "pattern": pattern,
                    "severity": "INFO"
                }
                pattern_issues.append(issue)
                if self.verbose:
                    print(f"ℹ️  PATTERN: '{category}' could benefit from word boundaries (\\b)")
        
        # Print results
        print(f"Analyzed {len(TECH_CATEGORY_RULES)} patterns:")
        if pattern_issues:
            for issue in pattern_issues:
                if issue["severity"] == "WARNING":
                    print(f"⚠️  {issue['category']}: {issue.get('broad_term', 'issue detected')}")
        else:
            print("✅ No major pattern issues detected")
        
        return pattern_issues
    
    def print_summary(self):
        """Print audit summary."""
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        
        print(f"\n🎯 AUDIT RESULTS:")
        print(f"   Issues (❌): {total_issues}")
        print(f"   Warnings (⚠️ ): {total_warnings}")
        
        if total_issues == 0 and total_warnings == 0:
            print("✅ All rules passed audit!")
        elif total_issues == 0:
            print("✅ No critical issues found")
        else:
            print("❌ Critical issues need attention")
        
        # Top priority fixes
        if self.issues:
            print(f"\n🔥 TOP PRIORITY FIXES:")
            for issue in self.issues[:5]:
                print(f"   {issue}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if total_issues > 0:
            print("   1. Fix wordlist overlaps to improve specificity")
        if total_warnings > 5:
            print("   2. Consider narrowing broad patterns")
        if any("OVERUSED" in w for w in self.warnings):
            print("   3. Add alternative wordlists for overused items")
        if any("PORT CONFLICT" in w for w in self.warnings):
            print("   4. Implement port priority system")


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
    if results["total_issues"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()