#!/usr/bin/env python3
"""

    python rule_audit.py [--verbose] [--cache-days=30]
"""


# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent

)


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
        
            "overlap_issues": overlap_issues,
            "usage_issues": usage_issues,
            "repetition_issues": repetition_issues,
            "port_issues": port_issues,
            "pattern_issues": pattern_issues,
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings)
        }
    
        """Detect wordlists that appear in multiple rule categories."""
        wordlist_sources = defaultdict(list)
        
        # Collect all wordlists and their sources
        
        # Exact match rules
            tech, port = key
            source = f"exact:{tech}:{port}"
        
        # Tech category rules
            source = f"tech_category:{category}"
        
        # Port category rules
            source = f"port_category:{category}"
        
        # Service keyword rules
            source = f"keyword:{keyword}"
        
        # Generic fallback
        
        # Find overlaps
        overlap_issues = []
                severity = "ERROR" if len(sources) > 3 else "WARNING"
                issue = {
                    "wordlist": wordlist,
                    "sources": sources,
                    "count": len(sources),
                    "severity": severity
                }
                
                if severity == "ERROR":
        
        # Print results
            overlap_issues.sort(key=lambda x: x["count"], reverse=True)
                icon = "❌" if issue["severity"] == "ERROR" else "⚠️ "
        
    
        """Analyze rule usage patterns from cache data."""
            entries = cache.search_selections(days_back=days_back, limit=500)
        
        
        # Count rule usage
        rule_usage = Counter()
        wordlist_usage = Counter()
        
                rule_usage[rule] += 1
                wordlist_usage[wl] += 1
        
        total_selections = len(entries)
        usage_issues = []
        
        # Find overused rules/wordlists (>80% of selections)
        overuse_threshold = total_selections * 0.8
                percentage = (count / total_selections) * 100
                issue = {
                    "type": "overused_wordlist",
                    "item": item,
                    "count": count,
                    "percentage": percentage,
                    "severity": "WARNING"
                }
        
        # Find unused exact rules
        used_exact_rules = {rule for rule in rule_usage.keys() if rule.startswith("exact:")}
        all_exact_rules = {f"exact:{tech}:{port}" for (tech, port) in EXACT_MATCH_RULES.keys()}
        unused_exact = all_exact_rules - used_exact_rules
        
            issue = {
                "type": "unused_exact_rule",
                "item": rule,
                "count": 0,
                "severity": "INFO"
            }
        
        # Print top usage
            percentage = (count / total_selections) * 100
            icon = "🔥" if percentage > 50 else "📈"
        
        
    
        """Find rules that always recommend the same wordlists."""
        repetitive_issues = []
        
        # Check tech categories for repetitive patterns
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
        
        # Check port categories
            wordlists = config["wordlists"]
            if len(set(wordlists)) <= 3 and len(wordlists) >= 3:
                issue = {
                    "type": "repetitive_port_category", 
                    "category": category,
                    "wordlists": wordlists,
                    "unique_count": len(set(wordlists)),
                    "severity": "WARNING"
                }
        
        # Print results
        
    
        """Detect ports that appear in multiple exclusive categories."""
        port_assignments = defaultdict(list)
        
        # Collect port assignments
        
        # Find conflicts
        port_issues = []
                issue = {
                    "port": port,
                    "categories": categories,
                    "count": len(categories),
                    "severity": "WARNING"
                }
        
        # Print results
        
    
        """Analyze regex pattern quality for potential issues."""
        pattern_issues = []
        
            
            pattern = config["fallback_pattern"]
            
            # Check for overly broad patterns
            broad_patterns = [
            ]
            
                    issue = {
                        "type": "broad_pattern",
                        "category": category,
                        "pattern": pattern,
                        "broad_term": broad,
                        "severity": "WARNING"
                    }
            
            # Check for missing word boundaries
                issue = {
                    "type": "missing_word_boundary",
                    "category": category,
                    "pattern": pattern,
                    "severity": "INFO"
                }
        
        # Print results
                if issue["severity"] == "WARNING":
        
    
        """Print audit summary."""
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        
        
        if total_issues == 0 and total_warnings == 0:
        elif total_issues == 0:
        
        # Top priority fixes
        
        # Recommendations


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


if __name__ == "__main__":
