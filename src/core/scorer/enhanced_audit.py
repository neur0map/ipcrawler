#!/usr/bin/env python3
"""
Enhanced SmartList audit system with comprehensive flaw detection and rich table formatting.

This audit provides detailed analysis across multiple dimensions:
- Rule Quality & Conflicts
- Performance & Efficiency 
- Coverage & Gaps
- Statistical Analysis
- Recommendations

Usage:
    python enhanced_audit.py [--verbose] [--cache-days=30] [--export-json]
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any, Optional
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# Rich imports for beautiful tables
from rich.console import Console
from rich.table import Table, Column
from rich.panel import Panel
from rich.text import Text
from rich.progress import track
from rich import box
from rich.layout import Layout
from rich.align import Align

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .mappings import (
    EXACT_MATCH_RULES, TECH_CATEGORY_RULES, PORT_CATEGORY_RULES, 
    SERVICE_KEYWORD_RULES, GENERIC_FALLBACK
)
from .cache import cache

console = Console()

@dataclass
class AuditFinding:
    """Represents a single audit finding."""
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title: str
    description: str
    affected_items: List[str]
    recommendation: str
    confidence: float  # 0.0 to 1.0
    evidence: Dict[str, Any]

@dataclass 
class AuditMetrics:
    """Overall audit metrics and scores."""
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    overall_score: float  # 0-100
    coverage_score: float
    efficiency_score: float
    quality_score: float


class EnhancedSmartListAuditor:
    """Comprehensive SmartList audit system with advanced flaw detection."""
    
    def __init__(self, verbose: bool = False, cache_days: int = 30):
        self.verbose = verbose
        self.cache_days = cache_days
        self.findings: List[AuditFinding] = []
        self.metrics = AuditMetrics(0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0)
        self.cache_data = []
        
    def run_comprehensive_audit(self) -> Dict[str, Any]:
        """Run the complete enhanced audit."""
        console.print(Panel.fit(
            "[bold cyan]🔍 Enhanced SmartList Comprehensive Audit[/bold cyan]\n"
            "[dim]Advanced flaw detection with statistical analysis[/dim]",
            border_style="cyan"
        ))
        
        # Load cache data once
        self._load_cache_data()
        
        # Run all audit categories
        audit_sections = [
            ("🔧 Rule Architecture Analysis", self._audit_rule_architecture),
            ("⚡ Performance & Efficiency", self._audit_performance),
            ("🎯 Coverage & Gap Analysis", self._audit_coverage_gaps),
            ("📊 Statistical Quality Analysis", self._audit_statistical_quality),
            ("🔄 Redundancy & Optimization", self._audit_redundancy),
            ("🚨 Critical Flaw Detection", self._audit_critical_flaws),
            ("🔍 Pattern Quality Assessment", self._audit_pattern_quality),
            ("📈 Trend & Usage Analysis", self._audit_trends)
        ]
        
        for section_name, audit_func in track(audit_sections, description="Running audit sections..."):
            console.print(f"\n[bold]{section_name}[/bold]")
            console.print("─" * 60)
            try:
                audit_func()
            except Exception as e:
                self._add_finding(
                    "SYSTEM",
                    "HIGH",
                    f"Audit Section Failed: {section_name}",
                    f"Exception during audit: {str(e)}",
                    [],
                    "Investigate audit system integrity",
                    0.9,
                    {"exception": str(e), "section": section_name}
                )
        
        # Calculate final metrics
        self._calculate_metrics()
        
        # Display results
        self._display_results()
        
        return self._export_results()
    
    def _load_cache_data(self):
        """Load and validate cache data."""
        try:
            self.cache_data = cache.search_selections(days_back=self.cache_days, limit=1000)
            console.print(f"[green]✓[/green] Loaded {len(self.cache_data)} cache entries from last {self.cache_days} days")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to load cache data: {e}")
            self.cache_data = []
    
    def _audit_rule_architecture(self):
        """Audit rule architecture for conflicts and inconsistencies."""
        table = Table(
            Column("Issue Type", style="cyan", no_wrap=True),
            Column("Severity", justify="center", style="bold"),
            Column("Count", justify="right", style="cyan"),
            Column("Details", style="dim"),
            title="🔧 Rule Architecture Issues",
            box=box.ROUNDED
        )
        
        # Port conflicts (enhanced analysis)
        port_conflicts = self._analyze_port_conflicts()
        if port_conflicts['conflicts']:
            severity = "HIGH" if len(port_conflicts['conflicts']) > 5 else "MEDIUM"
            table.add_row(
                "Port Conflicts",
                f"[red]{severity}[/red]" if severity == "HIGH" else f"[yellow]{severity}[/yellow]",
                str(len(port_conflicts['conflicts'])),
                f"Ports assigned to multiple categories: {', '.join(map(str, list(port_conflicts['conflicts'].keys())[:3]))}..."
            )
            
            self._add_finding(
                "ARCHITECTURE",
                severity,
                "Port Category Conflicts",
                f"Found {len(port_conflicts['conflicts'])} ports assigned to multiple categories",
                list(map(str, port_conflicts['conflicts'].keys())),
                "Implement port priority system or create composite categories",
                0.8,
                port_conflicts
            )
        
        # Rule overlap analysis (enhanced)
        overlaps = self._analyze_rule_overlaps()
        if overlaps['critical_overlaps']:
            table.add_row(
                "Rule Overlaps",
                "[red]CRITICAL[/red]",
                str(len(overlaps['critical_overlaps'])),
                f"Wordlists appearing in >3 categories"
            )
        
        # Orphaned rules detection
        orphaned = self._detect_orphaned_rules()
        if orphaned['count'] > 0:
            table.add_row(
                "Orphaned Rules",
                "[yellow]MEDIUM[/yellow]",
                str(orphaned['count']),
                "Rules never triggered in cache history"
            )
        
        # Inconsistent naming patterns
        naming_issues = self._analyze_naming_consistency()
        if naming_issues['inconsistent_count'] > 0:
            table.add_row(
                "Naming Inconsistencies",
                "[yellow]LOW[/yellow]",
                str(naming_issues['inconsistent_count']),
                "Inconsistent wordlist naming patterns"
            )
        
        console.print(table)
    
    def _audit_performance(self):
        """Audit performance and efficiency metrics."""
        try:
            table = Table(
                Column("Metric", style="cyan"),
                Column("Current", justify="right", style="green"),
                Column("Target", justify="right", style="dim"),
                Column("Status", justify="center"),
                Column("Impact", style="yellow"),
                title="⚡ Performance Metrics",
                box=box.ROUNDED
            )
            
            # Rule evaluation efficiency
            rule_efficiency = self._calculate_rule_efficiency()
            status = "✓" if rule_efficiency['avg_rules_per_selection'] < 5 else "⚠"
            table.add_row(
                "Avg Rules/Selection",
                f"{rule_efficiency['avg_rules_per_selection']:.1f}",
                "< 5.0",
                status,
                "Selection speed" if rule_efficiency['avg_rules_per_selection'] > 5 else "Optimal"
            )
            
            # Cache hit ratio
            cache_metrics = self._analyze_cache_performance()
            status = "✓" if cache_metrics['hit_ratio'] > 0.7 else "⚠"
            table.add_row(
                "Cache Hit Ratio",
                f"{cache_metrics['hit_ratio']:.1%}",
                "> 70%",
                status,
                "Memory usage"
            )
            
            # Wordlist distribution efficiency
            distribution = self._analyze_wordlist_distribution()
            status = "✓" if distribution['gini_coefficient'] < 0.6 else "⚠"
            table.add_row(
                "Distribution Equity",
                f"{1-distribution['gini_coefficient']:.1%}",
                "> 40%",
                status,
                "Recommendation quality"
            )
            
            console.print(table)
            
            # Add performance findings
            if rule_efficiency['avg_rules_per_selection'] > 8:
                self._add_finding(
                    "PERFORMANCE",
                    "HIGH",
                    "Excessive Rule Evaluation",
                    f"Average {rule_efficiency['avg_rules_per_selection']:.1f} rules evaluated per selection",
                    [],
                    "Optimize rule ordering and add early exit conditions",
                    0.9,
                    rule_efficiency
                )
        except Exception as e:
            console.print(f"[red]Performance audit failed: {e}[/red]")
            self._add_finding(
                "SYSTEM",
                "MEDIUM",
                "Performance Audit Failed",
                f"Could not complete performance analysis: {str(e)}",
                [],
                "Review performance audit implementation",
                0.7,
                {"error": str(e)}
            )
    
    def _audit_coverage_gaps(self):
        """Identify coverage gaps and missing rules."""
        table = Table(
            Column("Gap Type", style="cyan"),
            Column("Missing Items", justify="right", style="red"),
            Column("Coverage", justify="right", style="green"),
            Column("Priority", justify="center", style="bold"),
            title="🎯 Coverage Analysis",
            box=box.ROUNDED
        )
        
        # Technology coverage
        tech_coverage = self._analyze_technology_coverage()
        table.add_row(
            "Technologies",
            str(tech_coverage['missing_count']),
            f"{tech_coverage['coverage_percentage']:.1%}",
            "HIGH" if tech_coverage['coverage_percentage'] < 0.8 else "MEDIUM"
        )
        
        # Port coverage
        port_coverage = self._analyze_port_coverage()
        table.add_row(
            "Common Ports",
            str(port_coverage['uncovered_count']),
            f"{port_coverage['coverage_percentage']:.1%}",
            "MEDIUM"
        )
        
        # Service pattern coverage
        service_coverage = self._analyze_service_coverage()
        table.add_row(
            "Service Patterns",
            str(service_coverage['missing_patterns']),
            f"{service_coverage['pattern_coverage']:.1%}",
            "LOW"
        )
        
        console.print(table)
        
        # Add gap findings
        if tech_coverage['coverage_percentage'] < 0.7:
            self._add_finding(
                "COVERAGE",
                "HIGH",
                "Insufficient Technology Coverage",
                f"Only {tech_coverage['coverage_percentage']:.1%} of detected technologies have specific rules",
                tech_coverage['missing_technologies'][:10],
                "Add rules for frequently encountered technologies",
                0.8,
                tech_coverage
            )
    
    def _audit_statistical_quality(self):
        """Advanced statistical analysis of rule quality."""
        try:
            table = Table(
                Column("Statistical Metric", style="cyan"),
                Column("Value", justify="right", style="green"),
                Column("Quality", justify="center", style="bold"),
                Column("Trend", justify="center"),
                title="📊 Statistical Quality Metrics",
                box=box.ROUNDED
            )
            
            # Shannon entropy of recommendations
            entropy_metrics = self._calculate_recommendation_entropy()
            quality = "GOOD" if entropy_metrics['entropy'] > 3.0 else "POOR"
            table.add_row(
                "Recommendation Entropy",
                f"{entropy_metrics['entropy']:.2f}",
                f"[green]{quality}[/green]" if quality == "GOOD" else f"[red]{quality}[/red]",
                "📈" if entropy_metrics['trend'] > 0 else "📉"
            )
            
            # Prediction accuracy
            accuracy_metrics = self._calculate_prediction_accuracy()
            quality = "EXCELLENT" if accuracy_metrics['accuracy'] > 0.8 else "GOOD" if accuracy_metrics['accuracy'] > 0.6 else "POOR"
            table.add_row(
                "Prediction Accuracy",
                f"{accuracy_metrics['accuracy']:.1%}",
                f"[green]{quality}[/green]" if accuracy_metrics['accuracy'] > 0.6 else f"[red]{quality}[/red]",
                "📈"
            )
            
            # Rule effectiveness correlation
            correlation = self._calculate_rule_effectiveness()
            quality = "STRONG" if abs(correlation['correlation']) > 0.7 else "MODERATE" if abs(correlation['correlation']) > 0.4 else "WEAK"
            table.add_row(
                "Rule-Success Correlation",
                f"{correlation['correlation']:.2f}",
                f"[green]{quality}[/green]" if abs(correlation['correlation']) > 0.4 else f"[red]{quality}[/red]",
                "📊"
            )
            
            console.print(table)
        except Exception as e:
            console.print(f"[red]Statistical analysis failed: {e}[/red]")
            self._add_finding(
                "SYSTEM",
                "MEDIUM",
                "Statistical Analysis Failed",
                f"Could not complete statistical analysis: {str(e)}",
                [],
                "Review statistical analysis implementation",
                0.7,
                {"error": str(e)}
            )
    
    def _audit_redundancy(self):
        """Detect redundancy and optimization opportunities."""
        redundancy_table = Table(
            Column("Redundancy Type", style="cyan"),
            Column("Instances", justify="right", style="yellow"),
            Column("Waste Level", justify="center", style="bold"),
            Column("Potential Savings", style="green"),
            title="🔄 Redundancy Analysis",
            box=box.ROUNDED
        )
        
        # Duplicate wordlist recommendations
        duplicates = self._find_duplicate_recommendations()
        waste_level = "HIGH" if duplicates['percentage'] > 0.3 else "MEDIUM" if duplicates['percentage'] > 0.1 else "LOW"
        redundancy_table.add_row(
            "Duplicate Recommendations",
            str(duplicates['count']),
            f"[red]{waste_level}[/red]" if waste_level == "HIGH" else f"[yellow]{waste_level}[/yellow]",
            f"{duplicates['potential_reduction']:.1%} reduction possible"
        )
        
        # Redundant rules
        redundant_rules = self._find_redundant_rules()
        redundancy_table.add_row(
            "Redundant Rules",
            str(len(redundant_rules['redundant_pairs'])),
            "[yellow]MEDIUM[/yellow]",
            f"{redundant_rules['complexity_reduction']}% complexity reduction"
        )
        
        console.print(redundancy_table)
    
    def _audit_critical_flaws(self):
        """Detect critical flaws that could impact system reliability."""
        critical_table = Table(
            Column("Critical Flaw", style="red", no_wrap=True),
            Column("Risk Level", justify="center", style="bold"),
            Column("Affected Components", style="yellow"),
            Column("Immediate Action", style="cyan"),
            title="🚨 Critical Flaw Detection",
            box=box.HEAVY
        )
        
        # Infinite loop potential
        loop_risks = self._detect_infinite_loop_risks()
        if loop_risks['high_risk_patterns']:
            critical_table.add_row(
                "Infinite Loop Risk",
                "[red]CRITICAL[/red]",
                f"{len(loop_risks['high_risk_patterns'])} patterns",
                "Review regex patterns immediately"
            )
        
        # Memory exhaustion risks
        memory_risks = self._detect_memory_risks()
        if memory_risks['risk_level'] == "HIGH":
            critical_table.add_row(
                "Memory Exhaustion",
                "[red]HIGH[/red]",
                "Rule evaluation engine",
                "Implement resource limits"
            )
        
        # Logic contradictions
        contradictions = self._detect_logic_contradictions()
        if contradictions['contradictory_rules']:
            critical_table.add_row(
                "Logic Contradictions",
                "[red]HIGH[/red]",
                f"{len(contradictions['contradictory_rules'])} rule pairs",
                "Resolve conflicting logic"
            )
        
        if critical_table.rows:
            console.print(critical_table)
        else:
            console.print(Panel("[green]✓ No critical flaws detected[/green]", 
                               title="🚨 Critical Flaw Detection", 
                               border_style="green"))
    
    def _audit_pattern_quality(self):
        """Analyze regex pattern quality and potential issues."""
        pattern_table = Table(
            Column("Pattern Issue", style="cyan"),
            Column("Affected Patterns", justify="right", style="yellow"),
            Column("Severity", justify="center", style="bold"),
            Column("Performance Impact", style="red"),
            title="🔍 Pattern Quality Assessment",
            box=box.ROUNDED
        )
        
        # ReDoS vulnerability detection
        redos_risks = self._detect_redos_vulnerabilities()
        if redos_risks['vulnerable_patterns']:
            pattern_table.add_row(
                "ReDoS Vulnerability",
                str(len(redos_risks['vulnerable_patterns'])),
                "[red]HIGH[/red]",
                "Potential DoS attacks"
            )
        
        # Overly broad patterns
        broad_patterns = self._detect_overly_broad_patterns()
        pattern_table.add_row(
            "Overly Broad Patterns",
            str(len(broad_patterns['broad_patterns'])),
            "[yellow]MEDIUM[/yellow]",
            "False positive increase"
        )
        
        # Inefficient patterns
        inefficient = self._detect_inefficient_patterns()
        pattern_table.add_row(
            "Inefficient Patterns",
            str(len(inefficient['inefficient_patterns'])),
            "[yellow]LOW[/yellow]",
            "Slower evaluation"
        )
        
        console.print(pattern_table)
    
    def _audit_trends(self):
        """Analyze usage trends and prediction accuracy."""
        if len(self.cache_data) < 10:
            console.print(Panel("[yellow]⚠ Insufficient data for trend analysis[/yellow]", 
                               title="📈 Trend Analysis"))
            return
        
        trends_table = Table(
            Column("Trend Metric", style="cyan"),
            Column("Current Period", justify="right", style="green"),
            Column("Previous Period", justify="right", style="dim"),
            Column("Change", justify="center", style="bold"),
            Column("Prediction", style="yellow"),
            title="📈 Usage Trends & Predictions",
            box=box.ROUNDED
        )
        
        # Usage trend analysis
        trends = self._analyze_usage_trends()
        
        for metric_name, trend_data in trends.items():
            change_icon = "📈" if trend_data['change'] > 0 else "📉" if trend_data['change'] < 0 else "➡️"
            change_color = "green" if trend_data['change'] > 0 else "red" if trend_data['change'] < 0 else "yellow"
            
            trends_table.add_row(
                metric_name,
                f"{trend_data['current']:.1f}",
                f"{trend_data['previous']:.1f}",
                f"[{change_color}]{change_icon} {trend_data['change']:+.1%}[/{change_color}]",
                trend_data['prediction']
            )
        
        console.print(trends_table)

    # Helper methods for detailed analysis
    def _analyze_port_conflicts(self) -> Dict[str, Any]:
        """Analyze port conflicts in detail."""
        port_assignments = defaultdict(list)
        
        for category, config in PORT_CATEGORY_RULES.items():
            for port in config["ports"]:
                port_assignments[port].append(category)
        
        conflicts = {port: categories for port, categories in port_assignments.items() 
                    if len(categories) > 1}
        
        return {
            "conflicts": conflicts,
            "total_ports": len(port_assignments),
            "conflict_percentage": len(conflicts) / len(port_assignments) if port_assignments else 0
        }
    
    def _analyze_rule_overlaps(self) -> Dict[str, Any]:
        """Analyze wordlist overlaps across rule categories."""
        wordlist_sources = defaultdict(list)
        
        # Collect all wordlists and their sources
        for key, wordlists in EXACT_MATCH_RULES.items():
            tech, port = key
            source = f"exact:{tech}:{port}"
            for wl in wordlists:
                wordlist_sources[wl].append(source)
        
        for category, config in TECH_CATEGORY_RULES.items():
            source = f"tech_category:{category}"
            for wl in config["wordlists"]:
                wordlist_sources[wl].append(source)
        
        # Analyze overlaps
        critical_overlaps = {wl: sources for wl, sources in wordlist_sources.items() 
                           if len(sources) > 3}
        moderate_overlaps = {wl: sources for wl, sources in wordlist_sources.items() 
                           if len(sources) == 3}
        
        return {
            "critical_overlaps": critical_overlaps,
            "moderate_overlaps": moderate_overlaps,
            "total_wordlists": len(wordlist_sources),
            "overlap_percentage": len(critical_overlaps) / len(wordlist_sources) if wordlist_sources else 0
        }
    
    def _detect_orphaned_rules(self) -> Dict[str, Any]:
        """Detect rules that are never used."""
        if not self.cache_data:
            return {"count": 0, "rules": []}
        
        used_rules = set()
        for entry in self.cache_data:
            used_rules.update(entry.result.matched_rules)
        
        all_rules = set()
        for tech, port in EXACT_MATCH_RULES.keys():
            all_rules.add(f"exact:{tech}:{port}")
        
        for category in TECH_CATEGORY_RULES.keys():
            all_rules.add(f"tech_category:{category}")
        
        orphaned_rules = all_rules - used_rules
        
        return {
            "count": len(orphaned_rules),
            "rules": list(orphaned_rules),
            "usage_percentage": len(used_rules) / len(all_rules) if all_rules else 0
        }
    
    def _analyze_naming_consistency(self) -> Dict[str, Any]:
        """Analyze naming consistency across wordlists."""
        all_wordlists = set()
        
        # Collect all wordlists
        for wordlists in EXACT_MATCH_RULES.values():
            all_wordlists.update(wordlists)
        
        for config in TECH_CATEGORY_RULES.values():
            all_wordlists.update(config["wordlists"])
        
        # Analyze naming patterns
        naming_patterns = defaultdict(list)
        for wl in all_wordlists:
            # Extract base patterns
            if '-' in wl:
                pattern = '-'.join(wl.split('-')[:-1])  # Remove last part
                naming_patterns[pattern].append(wl)
            elif '_' in wl:
                pattern = '_'.join(wl.split('_')[:-1])
                naming_patterns[pattern].append(wl)
        
        inconsistent_count = sum(1 for wordlists in naming_patterns.values() 
                               if len(wordlists) == 1)  # Singleton patterns might be inconsistent
        
        return {
            "total_wordlists": len(all_wordlists),
            "naming_patterns": len(naming_patterns),
            "inconsistent_count": inconsistent_count
        }
    
    def _calculate_rule_efficiency(self) -> Dict[str, Any]:
        """Calculate rule evaluation efficiency metrics."""
        if not self.cache_data:
            return {"avg_rules_per_selection": 0, "max_rules": 0, "efficiency_score": 1.0}
        
        rules_per_selection = [len(entry.result.matched_rules) for entry in self.cache_data]
        
        return {
            "avg_rules_per_selection": sum(rules_per_selection) / len(rules_per_selection),
            "max_rules": max(rules_per_selection),
            "min_rules": min(rules_per_selection),
            "efficiency_score": 1.0 / (sum(rules_per_selection) / len(rules_per_selection))
        }
    
    def _analyze_cache_performance(self) -> Dict[str, Any]:
        """Analyze cache performance metrics."""
        # Simplified cache analysis
        total_requests = len(self.cache_data)
        
        # Handle different context types safely
        unique_contexts = set()
        for entry in self.cache_data:
            context = entry.context
            # Create a context fingerprint that works with both context types
            port = getattr(context, 'port', 0)
            tech = getattr(context, 'tech', '') or ''
            # Use a generic identifier for target if not available
            target = getattr(context, 'target', 'anonymous')
            unique_contexts.add((target, port, tech))
        
        hit_ratio = 1 - (len(unique_contexts) / total_requests) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "unique_contexts": len(unique_contexts),
            "hit_ratio": hit_ratio
        }
    
    def _analyze_wordlist_distribution(self) -> Dict[str, Any]:
        """Analyze wordlist usage distribution."""
        if not self.cache_data:
            return {"gini_coefficient": 0}
        
        wordlist_counts = Counter()
        for entry in self.cache_data:
            for wl in entry.result.wordlists:
                wordlist_counts[wl] += 1
        
        # Calculate Gini coefficient
        counts = sorted(wordlist_counts.values())
        n = len(counts)
        index = range(1, n + 1)
        gini = 2 * sum(index[i] * counts[i] for i in range(n)) / (n * sum(counts)) - (n + 1) / n
        
        return {
            "gini_coefficient": gini,
            "unique_wordlists": len(wordlist_counts),
            "total_recommendations": sum(wordlist_counts.values())
        }
    
    def _analyze_technology_coverage(self) -> Dict[str, Any]:
        """Analyze technology coverage gaps."""
        if not self.cache_data:
            return {"coverage_percentage": 0, "missing_count": 0, "missing_technologies": []}
        
        detected_techs = set()
        covered_techs = set()
        
        # Import TECH_CATEGORY_RULES to check matches
        from .mappings import TECH_CATEGORY_RULES
        
        for entry in self.cache_data:
            # Handle both regular and anonymized contexts
            tech = getattr(entry.context, 'tech', None)
            if tech:
                detected_techs.add(tech.lower())
                
                # Check if tech has specific rules (direct match in rule name)
                is_covered = False
                
                # Check direct appearance in rule names
                if any(tech.lower() in rule for rule in entry.result.matched_rules):
                    is_covered = True
                
                # Check if tech is in matches list of any triggered tech category rule
                for rule in entry.result.matched_rules:
                    if rule.startswith('tech_category:') or rule.startswith('tech_pattern:'):
                        category = rule.replace('tech_category:', '').replace('tech_pattern:', '')
                        if category in TECH_CATEGORY_RULES:
                            matches = TECH_CATEGORY_RULES[category].get('matches', [])
                            if tech.lower() in [match.lower() for match in matches]:
                                is_covered = True
                                break
                
                if is_covered:
                    covered_techs.add(tech.lower())
        
        missing_technologies = detected_techs - covered_techs
        coverage_percentage = len(covered_techs) / len(detected_techs) if detected_techs else 1.0
        
        return {
            "coverage_percentage": coverage_percentage,
            "missing_count": len(missing_technologies),
            "missing_technologies": list(missing_technologies),
            "total_detected": len(detected_techs)
        }
    
    def _analyze_port_coverage(self) -> Dict[str, Any]:
        """Analyze port coverage gaps."""
        common_ports = {80, 443, 22, 21, 25, 53, 110, 143, 993, 995, 3306, 5432, 6379, 8080, 8443}
        
        covered_ports = set()
        for config in PORT_CATEGORY_RULES.values():
            covered_ports.update(config["ports"])
        
        uncovered_ports = common_ports - covered_ports
        
        return {
            "coverage_percentage": len(covered_ports & common_ports) / len(common_ports),
            "uncovered_count": len(uncovered_ports),
            "uncovered_ports": list(uncovered_ports)
        }
    
    def _analyze_service_coverage(self) -> Dict[str, Any]:
        """Analyze service pattern coverage."""
        if not self.cache_data:
            return {"pattern_coverage": 0.0, "missing_patterns": 0}
        
        # Collect unique service patterns from cache
        service_patterns = set()
        covered_patterns = set()
        
        for entry in self.cache_data:
            # Get service info from context
            service = getattr(entry.context, 'service', None) or getattr(entry.context, 'service_fingerprint', '')
            if service:
                # Extract service keywords
                service_lower = str(service).lower()
                for word in service_lower.split():
                    if len(word) > 3:  # Only consider meaningful words
                        service_patterns.add(word)
                        
                        # Check if this service pattern has matching rules
                        if any(word in rule.lower() for rule in entry.result.matched_rules):
                            covered_patterns.add(word)
        
        # Calculate coverage
        total_patterns = len(service_patterns)
        covered_count = len(covered_patterns)
        missing_count = total_patterns - covered_count
        
        pattern_coverage = covered_count / total_patterns if total_patterns > 0 else 1.0
        
        return {
            "pattern_coverage": pattern_coverage,
            "missing_patterns": missing_count
        }
    
    def _calculate_recommendation_entropy(self) -> Dict[str, Any]:
        """Calculate Shannon entropy of recommendations."""
        if not self.cache_data:
            return {"entropy": 0, "trend": 0}
        
        wordlist_counts = Counter()
        for entry in self.cache_data:
            for wl in entry.result.wordlists:
                wordlist_counts[wl] += 1
        
        total = sum(wordlist_counts.values())
        import math
        entropy = -sum((count / total) * math.log2(count / total) 
                      for count in wordlist_counts.values() if count > 0)
        
        # Calculate trend by comparing first half vs second half of data
        trend = 0.0
        if len(self.cache_data) >= 10:
            mid_point = len(self.cache_data) // 2
            first_half = self.cache_data[:mid_point]
            second_half = self.cache_data[mid_point:]
            
            # Calculate entropy for each half
            def calculate_entropy_for_subset(data_subset):
                wl_counts = Counter()
                for entry in data_subset:
                    for wl in entry.result.wordlists:
                        wl_counts[wl] += 1
                total = sum(wl_counts.values())
                if total == 0:
                    return 0
                return -sum((count / total) * math.log2(count / total) 
                           for count in wl_counts.values() if count > 0)
            
            first_entropy = calculate_entropy_for_subset(first_half)
            second_entropy = calculate_entropy_for_subset(second_half)
            
            # Calculate trend (positive = increasing entropy/diversity)
            if first_entropy > 0:
                trend = (second_entropy - first_entropy) / first_entropy
        
        return {
            "entropy": entropy,
            "trend": trend
        }
    
    def _calculate_prediction_accuracy(self) -> Dict[str, Any]:
        """Calculate prediction accuracy metrics based on cache success data."""
        if not self.cache_data:
            return {"accuracy": 0.0}
        
        # Calculate accuracy based on successful vs failed selections
        successful_selections = 0
        total_selections = len(self.cache_data)
        
        for entry in self.cache_data:
            # Consider a selection successful if it has wordlists and rules matched
            if (entry.result.wordlists and 
                len(entry.result.wordlists) > 0 and 
                entry.result.matched_rules and 
                len(entry.result.matched_rules) > 0):
                successful_selections += 1
        
        accuracy = successful_selections / total_selections if total_selections > 0 else 0.0
        
        return {
            "accuracy": accuracy
        }
    
    def _calculate_rule_effectiveness(self) -> Dict[str, Any]:
        """Calculate correlation between rule types and recommendation success."""
        if not self.cache_data or len(self.cache_data) < 5:
            return {"correlation": 0.0}
        
        # Analyze correlation between rule types and wordlist count
        rule_wordlist_pairs = []
        
        for entry in self.cache_data:
            rule_count = len(entry.result.matched_rules)
            wordlist_count = len(entry.result.wordlists)
            rule_wordlist_pairs.append((rule_count, wordlist_count))
        
        # Calculate Pearson correlation coefficient
        if len(rule_wordlist_pairs) < 2:
            return {"correlation": 0.0}
        
        # Extract x and y values
        x_values = [pair[0] for pair in rule_wordlist_pairs]
        y_values = [pair[1] for pair in rule_wordlist_pairs]
        
        # Calculate means
        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(y_values) / len(y_values)
        
        # Calculate correlation
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        x_variance = sum((x - x_mean) ** 2 for x in x_values)
        y_variance = sum((y - y_mean) ** 2 for y in y_values)
        
        if x_variance == 0 or y_variance == 0:
            correlation = 0.0
        else:
            correlation = numerator / (x_variance * y_variance) ** 0.5
        
        return {
            "correlation": correlation
        }
    
    def _find_duplicate_recommendations(self) -> Dict[str, Any]:
        """Find duplicate recommendations."""
        if not self.cache_data:
            return {"count": 0, "percentage": 0, "potential_reduction": 0}
        
        duplicate_count = 0
        total_recommendations = 0
        
        for entry in self.cache_data:
            wordlists = entry.result.wordlists
            total_recommendations += len(wordlists)
            duplicate_count += len(wordlists) - len(set(wordlists))
        
        percentage = duplicate_count / total_recommendations if total_recommendations > 0 else 0
        
        return {
            "count": duplicate_count,
            "percentage": percentage,
            "potential_reduction": percentage * 0.8  # Estimated reduction
        }
    
    def _find_redundant_rules(self) -> Dict[str, Any]:
        """Find redundant rules that produce identical results."""
        if not self.cache_data:
            return {"redundant_pairs": [], "complexity_reduction": 0}
        
        # Group entries by their rule patterns to find redundancy
        rule_patterns = defaultdict(list)
        
        for entry in self.cache_data:
            # Create a signature from the matched rules
            rule_signature = tuple(sorted(entry.result.matched_rules))
            wordlist_signature = tuple(sorted(entry.result.wordlists))
            rule_patterns[rule_signature].append(wordlist_signature)
        
        # Find rules that always produce the same wordlists
        redundant_pairs = []
        total_rules = len(rule_patterns)
        
        for rule_sig, wordlist_sigs in rule_patterns.items():
            unique_wordlists = set(wordlist_sigs)
            if len(unique_wordlists) == 1 and len(wordlist_sigs) > 1:
                # This rule pattern always produces the same result
                redundant_pairs.append({
                    "rules": rule_sig,
                    "always_produces": list(unique_wordlists)[0],
                    "occurrences": len(wordlist_sigs)
                })
        
        # Calculate potential complexity reduction
        redundant_rule_count = len(redundant_pairs)
        complexity_reduction = (redundant_rule_count / total_rules * 100) if total_rules > 0 else 0
        
        return {
            "redundant_pairs": redundant_pairs,
            "complexity_reduction": int(complexity_reduction)
        }
    
    def _detect_infinite_loop_risks(self) -> Dict[str, Any]:
        """Detect patterns that could cause infinite loops."""
        high_risk_patterns = []
        
        for category, config in TECH_CATEGORY_RULES.items():
            if "fallback_pattern" in config:
                pattern = config["fallback_pattern"]
                # Check for risky regex patterns
                if any(risky in pattern for risky in [".*", ".+", "(.)*", "(.)+", "(.*)*"]):
                    high_risk_patterns.append((category, pattern))
        
        return {
            "high_risk_patterns": high_risk_patterns
        }
    
    def _detect_memory_risks(self) -> Dict[str, Any]:
        """Detect potential memory exhaustion risks."""
        # Analyze rule complexity
        total_rules = len(EXACT_MATCH_RULES) + len(TECH_CATEGORY_RULES) + len(PORT_CATEGORY_RULES)
        total_wordlists = len(set().union(*[wls for wls in EXACT_MATCH_RULES.values()]))
        
        risk_level = "HIGH" if total_rules * total_wordlists > 10000 else "MEDIUM" if total_rules * total_wordlists > 1000 else "LOW"
        
        return {
            "risk_level": risk_level,
            "complexity_score": total_rules * total_wordlists
        }
    
    def _detect_logic_contradictions(self) -> Dict[str, Any]:
        """Detect contradictory logic in rules."""
        contradictory_rules = []
        
        # Check for exact match rules that conflict with category rules
        for (tech, port), exact_wordlists in EXACT_MATCH_RULES.items():
            # Find any tech category rules that would also match
            for category, config in TECH_CATEGORY_RULES.items():
                if tech.lower() in [match.lower() for match in config.get("matches", [])]:
                    # Check if they recommend different wordlists
                    category_wordlists = set(config["wordlists"])
                    exact_wordlists_set = set(exact_wordlists)
                    
                    if category_wordlists.isdisjoint(exact_wordlists_set):
                        contradictory_rules.append({
                            "exact_rule": f"exact:{tech}:{port}",
                            "category_rule": f"tech_category:{category}",
                            "conflict": "Recommend different wordlists for same context"
                        })
        
        # Check for port category conflicts with exact rules
        port_conflicts = []
        for (tech, port), exact_wordlists in EXACT_MATCH_RULES.items():
            for category, config in PORT_CATEGORY_RULES.items():
                if port in config.get("ports", []):
                    category_wordlists = set(config["wordlists"])
                    exact_wordlists_set = set(exact_wordlists)
                    
                    # If they don't share any wordlists, it's a potential contradiction
                    if category_wordlists.isdisjoint(exact_wordlists_set):
                        port_conflicts.append({
                            "exact_rule": f"exact:{tech}:{port}",
                            "port_rule": f"port_category:{category}",
                            "conflict": "No wordlist overlap between specific and general rules"
                        })
        
        all_contradictions = contradictory_rules + port_conflicts
        
        return {
            "contradictory_rules": all_contradictions
        }
    
    def _detect_redos_vulnerabilities(self) -> Dict[str, Any]:
        """Detect ReDoS (Regular Expression Denial of Service) vulnerabilities."""
        vulnerable_patterns = []
        
        for category, config in TECH_CATEGORY_RULES.items():
            if "fallback_pattern" in config:
                pattern = config["fallback_pattern"]
                # Check for ReDoS patterns
                if re.search(r'\([^)]*\*[^)]*\)[+*]', pattern) or re.search(r'\([^)]*\+[^)]*\)[+*]', pattern):
                    vulnerable_patterns.append((category, pattern))
        
        return {
            "vulnerable_patterns": vulnerable_patterns
        }
    
    def _detect_overly_broad_patterns(self) -> Dict[str, Any]:
        """Detect overly broad regex patterns."""
        broad_patterns = []
        
        broad_terms = ["admin", "management", "api", "web", "http", "server", "service"]
        
        for category, config in TECH_CATEGORY_RULES.items():
            if "fallback_pattern" in config:
                pattern = config["fallback_pattern"].lower()
                for term in broad_terms:
                    if term in pattern and r'\b' not in pattern:
                        broad_patterns.append((category, config["fallback_pattern"]))
                        break
        
        return {
            "broad_patterns": broad_patterns
        }
    
    def _detect_inefficient_patterns(self) -> Dict[str, Any]:
        """Detect inefficient regex patterns."""
        inefficient_patterns = []
        
        for category, config in TECH_CATEGORY_RULES.items():
            if "fallback_pattern" in config:
                pattern = config["fallback_pattern"]
                # Check for inefficient patterns
                if pattern.count('.*') > 2 or pattern.count('.+') > 2:
                    inefficient_patterns.append((category, pattern))
        
        return {
            "inefficient_patterns": inefficient_patterns
        }
    
    def _analyze_usage_trends(self) -> Dict[str, Any]:
        """Analyze usage trends over time."""
        if len(self.cache_data) < 20:
            return {}
        
        # Split data into two periods
        sorted_data = sorted(self.cache_data, key=lambda x: x.timestamp)
        mid_point = len(sorted_data) // 2
        
        current_period = sorted_data[mid_point:]
        previous_period = sorted_data[:mid_point]
        
        # Calculate metrics for each period
        def calculate_period_metrics(data):
            wordlist_count = sum(len(entry.result.wordlists) for entry in data)
            rule_count = sum(len(entry.result.matched_rules) for entry in data)
            return {
                "avg_wordlists": wordlist_count / len(data) if data else 0,
                "avg_rules": rule_count / len(data) if data else 0
            }
        
        current_metrics = calculate_period_metrics(current_period)
        previous_metrics = calculate_period_metrics(previous_period)
        
        return {
            "Avg Wordlists/Selection": {
                "current": current_metrics["avg_wordlists"],
                "previous": previous_metrics["avg_wordlists"],
                "change": (current_metrics["avg_wordlists"] - previous_metrics["avg_wordlists"]) / previous_metrics["avg_wordlists"] if previous_metrics["avg_wordlists"] > 0 else 0,
                "prediction": "Stable"
            },
            "Avg Rules/Selection": {
                "current": current_metrics["avg_rules"],
                "previous": previous_metrics["avg_rules"],
                "change": (current_metrics["avg_rules"] - previous_metrics["avg_rules"]) / previous_metrics["avg_rules"] if previous_metrics["avg_rules"] > 0 else 0,
                "prediction": "Increasing"
            }
        }
    
    def _add_finding(self, category: str, severity: str, title: str, description: str, 
                    affected_items: List[str], recommendation: str, confidence: float, 
                    evidence: Dict[str, Any]):
        """Add a finding to the audit results."""
        finding = AuditFinding(
            category=category,
            severity=severity,
            title=title,
            description=description,
            affected_items=affected_items,
            recommendation=recommendation,
            confidence=confidence,
            evidence=evidence
        )
        self.findings.append(finding)
    
    def _calculate_metrics(self):
        """Calculate overall audit metrics based on real analysis."""
        severity_counts = Counter(finding.severity for finding in self.findings)
        
        # Calculate real coverage score
        tech_coverage = self._analyze_technology_coverage()
        port_coverage = self._analyze_port_coverage()
        service_coverage = self._analyze_service_coverage()
        coverage_score = (tech_coverage['coverage_percentage'] * 0.5 + 
                         port_coverage['coverage_percentage'] * 0.3 + 
                         service_coverage['pattern_coverage'] * 0.2) * 100
        
        # Calculate real efficiency score
        rule_efficiency = self._calculate_rule_efficiency()
        cache_metrics = self._analyze_cache_performance()
        distribution = self._analyze_wordlist_distribution()
        efficiency_score = ((1 / max(1, rule_efficiency['avg_rules_per_selection'] / 5)) * 0.4 + 
                           cache_metrics['hit_ratio'] * 0.3 + 
                           (1 - distribution['gini_coefficient']) * 0.3) * 100
        
        # Calculate real quality score based on findings and metrics
        entropy_metrics = self._calculate_recommendation_entropy()
        accuracy_metrics = self._calculate_prediction_accuracy()
        
        # Normalize entropy (typical good range is 3-6)
        entropy_normalized = min(1.0, max(0.0, (entropy_metrics['entropy'] - 2) / 4))
        quality_score = (entropy_normalized * 0.4 + 
                        accuracy_metrics['accuracy'] * 0.4 + 
                        (1 - (severity_counts.get("CRITICAL", 0) + severity_counts.get("HIGH", 0)) / max(1, len(self.findings))) * 0.2) * 100
        
        self.metrics = AuditMetrics(
            total_findings=len(self.findings),
            critical_count=severity_counts.get("CRITICAL", 0),
            high_count=severity_counts.get("HIGH", 0),
            medium_count=severity_counts.get("MEDIUM", 0),
            low_count=severity_counts.get("LOW", 0),
            info_count=severity_counts.get("INFO", 0),
            overall_score=max(0, 100 - (severity_counts.get("CRITICAL", 0) * 25 + 
                                       severity_counts.get("HIGH", 0) * 10 + 
                                       severity_counts.get("MEDIUM", 0) * 5 + 
                                       severity_counts.get("LOW", 0) * 2)),
            coverage_score=coverage_score,
            efficiency_score=efficiency_score,
            quality_score=quality_score
        )
    
    def _display_results(self):
        """Display comprehensive audit results."""
        # Overall score panel
        score_color = "green" if self.metrics.overall_score >= 80 else "yellow" if self.metrics.overall_score >= 60 else "red"
        
        score_panel = Panel(
            f"[bold {score_color}]Overall Score: {self.metrics.overall_score:.1f}/100[/bold {score_color}]\n"
            f"[dim]Coverage: {self.metrics.coverage_score:.1f}% | "
            f"Efficiency: {self.metrics.efficiency_score:.1f}% | "
            f"Quality: {self.metrics.quality_score:.1f}%[/dim]",
            title="🎯 Audit Summary",
            border_style=score_color
        )
        console.print(score_panel)
        
        # Findings summary table
        summary_table = Table(
            Column("Severity", style="bold", justify="center"),
            Column("Count", justify="right", style="cyan"),
            Column("Impact", style="yellow"),
            Column("Action Required", style="cyan"),
            title="📋 Findings Summary",
            box=box.ROUNDED
        )
        
        severity_info = [
            ("CRITICAL", self.metrics.critical_count, "System reliability at risk", "Immediate fix required"),
            ("HIGH", self.metrics.high_count, "Significant performance impact", "Fix within 24 hours"),
            ("MEDIUM", self.metrics.medium_count, "Moderate impact", "Fix within 1 week"),
            ("LOW", self.metrics.low_count, "Minor impact", "Fix when convenient"),
            ("INFO", self.metrics.info_count, "Informational", "Consider for optimization")
        ]
        
        for severity, count, impact, action in severity_info:
            if count > 0:
                severity_color = {
                    "CRITICAL": "red", "HIGH": "red", "MEDIUM": "yellow", 
                    "LOW": "blue", "INFO": "dim"
                }[severity]
                summary_table.add_row(
                    f"[{severity_color}]{severity}[/{severity_color}]",
                    str(count),
                    impact,
                    action
                )
        
        console.print(summary_table)
        
        # Detailed findings (top 10 most critical)
        if self.findings:
            critical_findings = sorted(self.findings, 
                                     key=lambda x: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}[x.severity], -x.confidence))[:10]
            
            findings_table = Table(
                Column("Priority", style="bold", justify="center", width=8),
                Column("Category", style="cyan", width=12),
                Column("Issue", style="yellow", width=30),
                Column("Confidence", justify="center", width=10),
                Column("Recommendation", style="green"),
                title="🔍 Top Critical Findings",
                box=box.ROUNDED
            )
            
            for i, finding in enumerate(critical_findings, 1):
                severity_color = {
                    "CRITICAL": "red", "HIGH": "red", "MEDIUM": "yellow", 
                    "LOW": "blue", "INFO": "dim"
                }[finding.severity]
                
                findings_table.add_row(
                    f"[{severity_color}]{i}[/{severity_color}]",
                    finding.category,
                    finding.title[:28] + "..." if len(finding.title) > 28 else finding.title,
                    f"{finding.confidence:.0%}",
                    finding.recommendation[:40] + "..." if len(finding.recommendation) > 40 else finding.recommendation
                )
            
            console.print(findings_table)
        
        # Add detailed conflict analysis if available
        try:
            from .conflict_analyzer import SmartListConflictAnalyzer
            console.print("\n[bold yellow]🔍 Running Detailed Conflict Analysis...[/bold yellow]")
            analyzer = SmartListConflictAnalyzer(verbose=False)
            detailed_results = analyzer.analyze_all_conflicts()
            
            # Show summary of detailed analysis
            summary = detailed_results.get("summary", {})
            total_conflicts = summary.get("total_conflicts", 0)
            high_priority = summary.get("high_priority_issues", 0)
            resolutions = summary.get("resolutions_available", 0)
            
            summary_table = Table(
                title="📊 Detailed Conflict Analysis Summary",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold green"
            )
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Count", style="yellow", justify="right")
            summary_table.add_column("Status", style="white")
            
            summary_table.add_row(
                "Total Conflicts Found",
                str(total_conflicts),
                "[red]REVIEW NEEDED[/red]" if total_conflicts > 0 else "[green]CLEAN[/green]"
            )
            summary_table.add_row(
                "High Priority Issues",
                str(high_priority),
                "[red]CRITICAL[/red]" if high_priority > 0 else "[green]OK[/green]"
            )
            summary_table.add_row(
                "Automated Resolutions",
                str(resolutions),
                "[green]AVAILABLE[/green]" if resolutions > 0 else "[yellow]MANUAL REVIEW[/yellow]"
            )
            
            console.print(summary_table)
            
            if high_priority > 0:
                console.print(Panel.fit(
                    "[bold red]⚠️  HIGH PRIORITY CONFLICTS DETECTED[/bold red]\n\n"
                    f"Found {high_priority} high-priority conflicts that require immediate attention.\n"
                    f"Run [bold cyan]python -m src.core.scorer.conflict_analyzer --detailed[/bold cyan] for full analysis.\n\n"
                    "Quick Actions:\n"
                    "• Port conflicts: Create unified categories with weighted wordlists\n" 
                    "• Logic contradictions: Add shared wordlists or set rule priorities\n"
                    "• Coverage gaps: Generate rules for missing technologies",
                    border_style="red",
                    title="🚨 Action Required"
                ))
            
        except ImportError as e:
            console.print(f"[yellow]⚠️  Detailed conflict analyzer not available: {e}[/yellow]")
        except Exception as e:
            console.print(f"[red]⚠️  Conflict analysis failed: {e}[/red]")
    
    def _export_results(self) -> Dict[str, Any]:
        """Export audit results for programmatic use."""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": asdict(self.metrics),
            "findings": [asdict(finding) for finding in self.findings],
            "summary": {
                "total_rules_analyzed": len(EXACT_MATCH_RULES) + len(TECH_CATEGORY_RULES),
                "cache_entries_analyzed": len(self.cache_data),
                "audit_version": "2.0.0"
            }
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Enhanced SmartList audit system")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Show verbose output")
    parser.add_argument("--cache-days", type=int, default=30,
                       help="Days of cache data to analyze (default: 30)")
    parser.add_argument("--export-json", type=str,
                       help="Export results to JSON file")
    
    args = parser.parse_args()
    
    auditor = EnhancedSmartListAuditor(verbose=args.verbose, cache_days=args.cache_days)
    results = auditor.run_comprehensive_audit()
    
    if args.export_json:
        with open(args.export_json, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        console.print(f"\n[green]✓[/green] Results exported to {args.export_json}")
    
    # Exit with error code based on findings
    if results["metrics"]["critical_count"] > 0:
        sys.exit(2)
    elif results["metrics"]["high_count"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()