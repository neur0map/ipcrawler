#!/usr/bin/env python3
"""
Advanced conflict analyzer for SmartList rule system with detailed explanations and resolution tools.

This module provides comprehensive analysis of rule conflicts, port overlaps, and logic contradictions
with specific examples, impact analysis, and automated resolution suggestions.

Usage:
    python conflict_analyzer.py [--detailed] [--auto-fix] [--export-fixes]
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, asdict

# Rich imports for beautiful output
from rich.console import Console
from rich.table import Table, Column
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich import box
from rich.progress import track

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .mappings import (
    EXACT_MATCH_RULES, TECH_CATEGORY_RULES, PORT_CATEGORY_RULES, 
    SERVICE_KEYWORD_RULES, GENERIC_FALLBACK
)

console = Console()

@dataclass
class PortConflict:
    """Represents a port conflict with detailed analysis."""
    port: int
    categories: List[str]
    wordlists_by_category: Dict[str, List[str]]
    conflict_severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    impact_description: str
    resolution_suggestions: List[str]
    examples: List[str]

@dataclass
class LogicContradiction:
    """Represents a logic contradiction between rules."""
    rule1_type: str
    rule1_id: str
    rule1_wordlists: List[str]
    rule2_type: str
    rule2_id: str
    rule2_wordlists: List[str]
    overlap_count: int
    contradiction_severity: str
    context_example: str
    resolution_suggestion: str

@dataclass
class CoverageGap:
    """Represents a coverage gap in the rule system."""
    gap_type: str  # technology, port, service_pattern
    missing_item: str
    frequency: int
    suggested_wordlists: List[str]
    rule_template: Dict[str, Any]
    priority: str

@dataclass
class ConflictResolution:
    """Represents a proposed resolution for conflicts."""
    conflict_id: str
    resolution_type: str  # merge, prioritize, split, create_new
    actions: List[Dict[str, Any]]
    expected_outcome: str
    risk_level: str


class SmartListConflictAnalyzer:
    """Advanced conflict analyzer with detailed explanations and resolution tools."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.port_conflicts: List[PortConflict] = []
        self.logic_contradictions: List[LogicContradiction] = []
        self.coverage_gaps: List[CoverageGap] = []
        self.resolutions: List[ConflictResolution] = []
        
    def analyze_all_conflicts(self) -> Dict[str, Any]:
        """Run comprehensive conflict analysis."""
        console.print(Panel.fit(
            "[bold red]🔍 SmartList Conflict Analysis[/bold red]\n"
            "[dim]Detailed analysis of rule conflicts with resolution suggestions[/dim]",
            border_style="red"
        ))
        
        # Analyze different types of conflicts
        self._analyze_port_conflicts()
        self._analyze_logic_contradictions()
        self._analyze_coverage_gaps()
        self._generate_resolutions()
        
        # Display results
        self._display_port_conflicts()
        self._display_logic_contradictions()
        self._display_coverage_gaps()
        self._display_resolution_summary()
        
        return self._export_analysis()
    
    def _analyze_port_conflicts(self):
        """Analyze port conflicts in detail."""
        console.print("\n[bold cyan]🔧 Analyzing Port Conflicts...[/bold cyan]")
        
        # Group ports by categories
        port_to_categories = defaultdict(list)
        port_to_wordlists = defaultdict(dict)
        
        for category, config in PORT_CATEGORY_RULES.items():
            for port in config["ports"]:
                port_to_categories[port].append(category)
                port_to_wordlists[port][category] = config["wordlists"]
        
        # Identify conflicts
        for port, categories in port_to_categories.items():
            if len(categories) > 1:
                # Analyze severity
                severity = self._assess_port_conflict_severity(port, categories, port_to_wordlists[port])
                
                # Create detailed conflict analysis
                conflict = PortConflict(
                    port=port,
                    categories=categories,
                    wordlists_by_category=port_to_wordlists[port],
                    conflict_severity=severity,
                    impact_description=self._generate_port_impact_description(port, categories),
                    resolution_suggestions=self._generate_port_resolution_suggestions(port, categories),
                    examples=self._generate_port_conflict_examples(port, categories)
                )
                
                self.port_conflicts.append(conflict)
    
    def _analyze_logic_contradictions(self):
        """Analyze logic contradictions between rule types."""
        console.print("[bold cyan]🔍 Analyzing Logic Contradictions...[/bold cyan]")
        
        # Check exact rules vs tech category rules
        for (tech, port), exact_wordlists in track(EXACT_MATCH_RULES.items(), description="Analyzing exact vs tech rules..."):
            for category, config in TECH_CATEGORY_RULES.items():
                if tech.lower() in [match.lower() for match in config.get("matches", [])]:
                    category_wordlists = config["wordlists"]
                    overlap = len(set(exact_wordlists) & set(category_wordlists))
                    total_unique = len(set(exact_wordlists) | set(category_wordlists))
                    
                    if overlap == 0:  # No overlap = contradiction
                        contradiction = LogicContradiction(
                            rule1_type="exact_match",
                            rule1_id=f"{tech}:{port}",
                            rule1_wordlists=exact_wordlists,
                            rule2_type="tech_category",
                            rule2_id=category,
                            rule2_wordlists=category_wordlists,
                            overlap_count=overlap,
                            contradiction_severity="HIGH" if total_unique > 8 else "MEDIUM",
                            context_example=f"Service: {tech} on port {port}",
                            resolution_suggestion=self._generate_contradiction_resolution(
                                exact_wordlists, category_wordlists, tech, category
                            )
                        )
                        self.logic_contradictions.append(contradiction)
        
        # Check exact rules vs port category rules
        for (tech, port), exact_wordlists in track(EXACT_MATCH_RULES.items(), description="Analyzing exact vs port rules..."):
            for category, config in PORT_CATEGORY_RULES.items():
                if port in config.get("ports", []):
                    category_wordlists = config["wordlists"]
                    overlap = len(set(exact_wordlists) & set(category_wordlists))
                    
                    if overlap == 0:  # No overlap = contradiction
                        contradiction = LogicContradiction(
                            rule1_type="exact_match",
                            rule1_id=f"{tech}:{port}",
                            rule1_wordlists=exact_wordlists,
                            rule2_type="port_category",
                            rule2_id=category,
                            rule2_wordlists=category_wordlists,
                            overlap_count=overlap,
                            contradiction_severity="MEDIUM",
                            context_example=f"Service: {tech} on port {port}",
                            resolution_suggestion=self._generate_port_contradiction_resolution(
                                exact_wordlists, category_wordlists, tech, port, category
                            )
                        )
                        self.logic_contradictions.append(contradiction)
    
    def _analyze_coverage_gaps(self):
        """Analyze coverage gaps with specific recommendations."""
        console.print("[bold cyan]📊 Analyzing Coverage Gaps...[/bold cyan]")
        
        # Load cache data to identify missing technologies
        try:
            from .cache import cache
            cache_data = cache.search_selections(days_back=30, limit=500)
            
            # Analyze missing technologies
            detected_techs = Counter()
            covered_techs = set()
            
            for entry in cache_data:
                tech = getattr(entry.context, 'tech', None)
                if tech:
                    detected_techs[tech.lower()] += 1
                    
                    # Check if tech has specific rules (enhanced logic)
                    is_covered = False
                    
                    # Check direct appearance in rule names
                    if any(tech.lower() in rule for rule in entry.result.matched_rules):
                        is_covered = True
                    
                    # Check if tech is in matches list of any triggered tech category rule
                    from .mappings import TECH_CATEGORY_RULES
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
            
            # Identify missing technologies
            for tech, frequency in detected_techs.most_common():
                if tech not in covered_techs:
                    gap = CoverageGap(
                        gap_type="technology",
                        missing_item=tech,
                        frequency=frequency,
                        suggested_wordlists=self._suggest_wordlists_for_tech(tech),
                        rule_template=self._generate_tech_rule_template(tech),
                        priority="HIGH" if frequency > 5 else "MEDIUM" if frequency > 2 else "LOW"
                    )
                    self.coverage_gaps.append(gap)
                    
        except Exception as e:
            console.print(f"[yellow]Warning: Could not analyze cache data: {e}[/yellow]")
            
        # Analyze common ports without rules
        common_ports = {80, 443, 22, 21, 25, 53, 110, 143, 993, 995, 3306, 5432, 6379, 8080, 8443}
        covered_ports = set()
        for config in PORT_CATEGORY_RULES.values():
            covered_ports.update(config["ports"])
        
        for port in common_ports - covered_ports:
            gap = CoverageGap(
                gap_type="port",
                missing_item=str(port),
                frequency=1,  # Estimated
                suggested_wordlists=self._suggest_wordlists_for_port(port),
                rule_template=self._generate_port_rule_template(port),
                priority="MEDIUM"
            )
            self.coverage_gaps.append(gap)
    
    def _generate_resolutions(self):
        """Generate automated resolution suggestions."""
        console.print("[bold cyan]🔧 Generating Resolution Suggestions...[/bold cyan]")
        
        # Port conflict resolutions
        for conflict in self.port_conflicts:
            if conflict.conflict_severity in ["HIGH", "CRITICAL"]:
                resolution = ConflictResolution(
                    conflict_id=f"port_{conflict.port}",
                    resolution_type="merge",
                    actions=[
                        {
                            "action": "create_composite_category",
                            "port": conflict.port,
                            "new_category": f"port_{conflict.port}_composite",
                            "wordlists": self._merge_wordlists(conflict.wordlists_by_category),
                            "weights": self._calculate_optimal_weights(conflict.categories)
                        }
                    ],
                    expected_outcome=f"Unified wordlist for port {conflict.port} with contextual weighting",
                    risk_level="LOW"
                )
                self.resolutions.append(resolution)
        
        # Logic contradiction resolutions
        for contradiction in self.logic_contradictions:
            if contradiction.contradiction_severity == "HIGH":
                resolution = ConflictResolution(
                    conflict_id=f"logic_{contradiction.rule1_id}_{contradiction.rule2_id}",
                    resolution_type="prioritize",
                    actions=[
                        {
                            "action": "add_shared_wordlists",
                            "rule1": contradiction.rule1_id,
                            "rule2": contradiction.rule2_id,
                            "shared_wordlists": self._find_bridge_wordlists(
                                contradiction.rule1_wordlists, contradiction.rule2_wordlists
                            )
                        }
                    ],
                    expected_outcome="Reduced contradiction through shared wordlists",
                    risk_level="MEDIUM"
                )
                self.resolutions.append(resolution)
        
        # Coverage gap resolutions
        for gap in self.coverage_gaps:
            if gap.priority == "HIGH":
                resolution = ConflictResolution(
                    conflict_id=f"gap_{gap.gap_type}_{gap.missing_item}",
                    resolution_type="create_new",
                    actions=[
                        {
                            "action": "add_rule",
                            "rule_type": gap.gap_type,
                            "template": gap.rule_template,
                            "wordlists": gap.suggested_wordlists
                        }
                    ],
                    expected_outcome=f"Coverage for {gap.missing_item}",
                    risk_level="LOW"
                )
                self.resolutions.append(resolution)
    
    def _display_port_conflicts(self):
        """Display detailed port conflict analysis."""
        if not self.port_conflicts:
            console.print("[green]✓ No port conflicts detected[/green]")
            return
            
        console.print(f"\n[bold red]🚨 Port Conflicts Detected: {len(self.port_conflicts)}[/bold red]")
        
        for conflict in self.port_conflicts:
            # Create a tree for each conflict
            tree = Tree(f"[bold red]Port {conflict.port}[/bold red] - {conflict.conflict_severity} Severity")
            
            # Add categories
            categories_branch = tree.add("[cyan]Categories in Conflict[/cyan]")
            for category in conflict.categories:
                cat_branch = categories_branch.add(f"[yellow]{category}[/yellow]")
                wordlists = conflict.wordlists_by_category[category]
                for wl in wordlists:
                    cat_branch.add(f"[dim]• {wl}[/dim]")
            
            # Add impact
            impact_branch = tree.add("[red]Impact Analysis[/red]")
            impact_branch.add(conflict.impact_description)
            
            # Add resolutions
            resolution_branch = tree.add("[green]Resolution Suggestions[/green]")
            for suggestion in conflict.resolution_suggestions:
                resolution_branch.add(f"[green]• {suggestion}[/green]")
            
            # Add examples
            if conflict.examples:
                examples_branch = tree.add("[blue]Examples[/blue]")
                for example in conflict.examples:
                    examples_branch.add(f"[blue]• {example}[/blue]")
            
            console.print(tree)
            console.print()
    
    def _display_logic_contradictions(self):
        """Display detailed logic contradiction analysis."""
        if not self.logic_contradictions:
            console.print("[green]✓ No logic contradictions detected[/green]")
            return
            
        console.print(f"\n[bold red]🔍 Logic Contradictions: {len(self.logic_contradictions)}[/bold red]")
        
        # Group by severity
        by_severity = defaultdict(list)
        for contradiction in self.logic_contradictions:
            by_severity[contradiction.contradiction_severity].append(contradiction)
        
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if severity not in by_severity:
                continue
                
            console.print(f"\n[bold]{severity} Severity: {len(by_severity[severity])} contradictions[/bold]")
            
            table = Table(
                Column("Rule 1", style="cyan", width=20),
                Column("Rule 2", style="yellow", width=20),
                Column("Context", style="blue", width=25),
                Column("Resolution", style="green"),
                title=f"{severity} Logic Contradictions",
                box=box.ROUNDED
            )
            
            for contradiction in by_severity[severity][:10]:  # Show top 10
                table.add_row(
                    f"{contradiction.rule1_type}\n{contradiction.rule1_id}",
                    f"{contradiction.rule2_type}\n{contradiction.rule2_id}",
                    contradiction.context_example,
                    contradiction.resolution_suggestion
                )
            
            console.print(table)
    
    def _display_coverage_gaps(self):
        """Display coverage gap analysis."""
        if not self.coverage_gaps:
            console.print("[green]✓ No coverage gaps detected[/green]")
            return
            
        console.print(f"\n[bold yellow]📊 Coverage Gaps: {len(self.coverage_gaps)}[/bold yellow]")
        
        # Group by type and priority
        by_type = defaultdict(lambda: defaultdict(list))
        for gap in self.coverage_gaps:
            by_type[gap.gap_type][gap.priority].append(gap)
        
        for gap_type in by_type:
            console.print(f"\n[bold]{gap_type.upper()} Gaps:[/bold]")
            
            for priority in ["HIGH", "MEDIUM", "LOW"]:
                if priority not in by_type[gap_type]:
                    continue
                    
                gaps = by_type[gap_type][priority]
                console.print(f"  [bold {priority.lower()}]{priority}: {len(gaps)} items[/bold {priority.lower()}]")
                
                for gap in gaps[:5]:  # Show top 5
                    console.print(f"    • [cyan]{gap.missing_item}[/cyan] (freq: {gap.frequency})")
                    console.print(f"      Suggested: {', '.join(gap.suggested_wordlists[:3])}...")
    
    def _display_resolution_summary(self):
        """Display resolution summary."""
        if not self.resolutions:
            console.print("[yellow]No automated resolutions available[/yellow]")
            return
            
        console.print(f"\n[bold green]🔧 Automated Resolutions Available: {len(self.resolutions)}[/bold green]")
        
        resolution_table = Table(
            Column("Conflict ID", style="cyan"),
            Column("Type", style="yellow"),
            Column("Risk", justify="center", style="bold"),
            Column("Expected Outcome", style="green"),
            title="🔧 Available Resolutions",
            box=box.ROUNDED
        )
        
        for resolution in self.resolutions:
            risk_color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red"}.get(resolution.risk_level, "white")
            resolution_table.add_row(
                resolution.conflict_id,
                resolution.resolution_type,
                f"[{risk_color}]{resolution.risk_level}[/{risk_color}]",
                resolution.expected_outcome
            )
        
        console.print(resolution_table)
    
    # Helper methods for analysis
    def _assess_port_conflict_severity(self, port: int, categories: List[str], wordlists: Dict[str, List[str]]) -> str:
        """Assess the severity of a port conflict."""
        total_wordlists = sum(len(wl) for wl in wordlists.values())
        unique_wordlists = len(set().union(*wordlists.values()))
        overlap_ratio = 1 - (unique_wordlists / total_wordlists) if total_wordlists > 0 else 0
        
        if overlap_ratio < 0.2:  # Less than 20% overlap
            return "CRITICAL"
        elif overlap_ratio < 0.5:
            return "HIGH"
        elif overlap_ratio < 0.8:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_port_impact_description(self, port: int, categories: List[str]) -> str:
        """Generate impact description for port conflict."""
        return f"Port {port} recommendations vary significantly between {', '.join(categories)} categories, " \
               f"potentially causing inconsistent wordlist selection based on rule evaluation order."
    
    def _generate_port_resolution_suggestions(self, port: int, categories: List[str]) -> List[str]:
        """Generate resolution suggestions for port conflicts."""
        return [
            f"Create unified category for port {port} with merged wordlists",
            f"Implement priority weighting between {', '.join(categories)}",
            f"Add contextual rules to disambiguate between categories",
            "Consider splitting port into specific use cases"
        ]
    
    def _generate_port_conflict_examples(self, port: int, categories: List[str]) -> List[str]:
        """Generate examples of port conflicts."""
        return [
            f"Apache on port {port} could match both 'web' and 'admin' categories",
            f"Different services on port {port} receive different wordlist recommendations",
            f"Rule evaluation order affects which wordlists are selected"
        ]
    
    def _generate_contradiction_resolution(self, exact_wl: List[str], cat_wl: List[str], tech: str, category: str) -> str:
        """Generate resolution for rule contradictions."""
        return f"Add bridge wordlists between {tech} exact rules and {category} category, " \
               f"or create technology-specific variants in {category} category"
    
    def _generate_port_contradiction_resolution(self, exact_wl: List[str], cat_wl: List[str], tech: str, port: int, category: str) -> str:
        """Generate resolution for port-specific contradictions."""
        return f"Merge common wordlists between {tech}:{port} exact rule and {category} port category, " \
               f"or add {tech}-specific wordlists to port category"
    
    def _suggest_wordlists_for_tech(self, tech: str) -> List[str]:
        """Suggest wordlists for missing technology."""
        # Common wordlist patterns
        base_suggestions = [f"{tech}-common.txt", f"{tech}-paths.txt", "common.txt"]
        
        # Technology-specific suggestions
        tech_specific = {
            "react": ["react-routes.txt", "javascript-common.txt", "spa-paths.txt"],
            "vue": ["vue-routes.txt", "javascript-common.txt", "spa-paths.txt"],
            "docker": ["docker-api.txt", "container-paths.txt", "docker-compose.txt"],
            "kubernetes": ["k8s-api.txt", "kubectl-paths.txt", "k8s-dashboard.txt"],
            "elasticsearch": ["elasticsearch-api.txt", "elastic-indices.txt", "kibana-paths.txt"],
            "grafana": ["grafana-api.txt", "grafana-dashboards.txt", "monitoring-paths.txt"]
        }
        
        return tech_specific.get(tech.lower(), base_suggestions)
    
    def _suggest_wordlists_for_port(self, port: int) -> List[str]:
        """Suggest wordlists for missing port."""
        port_suggestions = {
            53: ["dns-common.txt", "dns-records.txt"],
            25: ["smtp-commands.txt", "mail-common.txt"],
            110: ["pop3-commands.txt", "mail-common.txt"],
            143: ["imap-commands.txt", "mail-common.txt"],
            993: ["imap-ssl.txt", "mail-secure.txt"],
            995: ["pop3-ssl.txt", "mail-secure.txt"]
        }
        
        return port_suggestions.get(port, ["common.txt", f"port-{port}.txt"])
    
    def _generate_tech_rule_template(self, tech: str) -> Dict[str, Any]:
        """Generate rule template for missing technology."""
        return {
            "type": "exact_match",
            "tech": tech,
            "common_ports": [80, 443],
            "wordlists": self._suggest_wordlists_for_tech(tech),
            "weight": 1.0
        }
    
    def _generate_port_rule_template(self, port: int) -> Dict[str, Any]:
        """Generate rule template for missing port."""
        return {
            "type": "port_category",
            "port": port,
            "category": f"port_{port}",
            "wordlists": self._suggest_wordlists_for_port(port),
            "weight": 0.6
        }
    
    def _merge_wordlists(self, wordlists_by_category: Dict[str, List[str]]) -> List[str]:
        """Merge wordlists from multiple categories intelligently."""
        all_wordlists = []
        for wordlists in wordlists_by_category.values():
            all_wordlists.extend(wordlists)
        
        # Remove duplicates while preserving order
        merged = []
        seen = set()
        for wl in all_wordlists:
            if wl not in seen:
                merged.append(wl)
                seen.add(wl)
        
        return merged
    
    def _calculate_optimal_weights(self, categories: List[str]) -> Dict[str, float]:
        """Calculate optimal weights for conflicting categories."""
        # Simple equal weighting for now
        weight = 1.0 / len(categories)
        return {category: weight for category in categories}
    
    def _find_bridge_wordlists(self, list1: List[str], list2: List[str]) -> List[str]:
        """Find bridge wordlists that could connect contradictory rules."""
        # Find semantic similarities or suggest generic bridges
        bridge_candidates = [
            "common.txt", "dirs.txt", "files.txt", "paths.txt",
            "generic.txt", "discovery.txt"
        ]
        
        # Return bridges that aren't already in either list
        bridges = []
        existing = set(list1 + list2)
        for candidate in bridge_candidates:
            if candidate not in existing:
                bridges.append(candidate)
        
        return bridges[:3]  # Return top 3 bridge candidates
    
    def _export_analysis(self) -> Dict[str, Any]:
        """Export analysis results."""
        return {
            "port_conflicts": [asdict(conflict) for conflict in self.port_conflicts],
            "logic_contradictions": [asdict(contradiction) for contradiction in self.logic_contradictions],
            "coverage_gaps": [asdict(gap) for gap in self.coverage_gaps],
            "resolutions": [asdict(resolution) for resolution in self.resolutions],
            "summary": {
                "total_conflicts": len(self.port_conflicts) + len(self.logic_contradictions) + len(self.coverage_gaps),
                "resolutions_available": len(self.resolutions),
                "high_priority_issues": len([c for c in self.port_conflicts if c.conflict_severity in ["HIGH", "CRITICAL"]]) +
                                      len([c for c in self.logic_contradictions if c.contradiction_severity in ["HIGH", "CRITICAL"]]) +
                                      len([c for c in self.coverage_gaps if c.priority == "HIGH"])
            }
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze SmartList rule conflicts")
    parser.add_argument("--detailed", action="store_true", help="Show detailed analysis")
    parser.add_argument("--export", type=str, help="Export analysis to JSON file")
    
    args = parser.parse_args()
    
    analyzer = SmartListConflictAnalyzer(verbose=args.detailed)
    results = analyzer.analyze_all_conflicts()
    
    if args.export:
        with open(args.export, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        console.print(f"\n[green]✓[/green] Analysis exported to {args.export}")
    
    # Return exit code based on issues found
    high_priority = results["summary"]["high_priority_issues"]
    if high_priority > 0:
        console.print(f"\n[red]⚠[/red] Found {high_priority} high-priority issues")
        return 1
    else:
        console.print(f"\n[green]✓[/green] No high-priority issues found")
        return 0


if __name__ == "__main__":
    sys.exit(main())