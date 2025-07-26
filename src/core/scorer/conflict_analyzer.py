#!/usr/bin/env python3
"""


"""


# Rich imports for beautiful output

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent

)

console = Console()

@dataclass
    """Represents a port conflict with detailed analysis."""

@dataclass
    """Represents a logic contradiction between rules."""

@dataclass
    """Represents a coverage gap in the rule system."""

@dataclass
    """Represents a proposed resolution for conflicts."""


    """Advanced conflict analyzer with detailed explanations and resolution tools."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.port_conflicts: List[PortConflict] = []
        self.logic_contradictions: List[LogicContradiction] = []
        self.coverage_gaps: List[CoverageGap] = []
        self.resolutions: List[ConflictResolution] = []
        
        """Run comprehensive conflict analysis."""
            "[bold red]🔍 SmartList Conflict Analysis[/bold red]\n"
            "[dim]Detailed analysis of rule conflicts with resolution suggestions[/dim]",
            border_style="red"
        ))
        
        # Analyze different types of conflicts
        
        # Display results
        
    
        """Analyze port conflicts in detail."""
        
        # Group ports by categories
        port_to_categories = defaultdict(list)
        port_to_wordlists = defaultdict(dict)
        
                port_to_wordlists[port][category] = config["wordlists"]
        
        # Identify conflicts
                # Analyze severity
                severity = self._assess_port_conflict_severity(port, categories, port_to_wordlists[port])
                
                conflict = PortConflict(
                    port=port,
                    categories=categories,
                    wordlists_by_category=port_to_wordlists[port],
                    conflict_severity=severity,
                    impact_description=self._generate_port_impact_description(port, categories),
                    resolution_suggestions=self._generate_port_resolution_suggestions(port, categories),
                    examples=self._generate_port_conflict_examples(port, categories)
                )
                
    
        """Analyze logic contradictions between rule types."""
        
        # Check exact rules vs tech category rules
        for (tech, port), exact_wordlists in track(EXACT_MATCH_RULES.items(), description="Analyzing exact vs tech rules..."):
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
                            )
                        )
        
        # Check exact rules vs port category rules
        for (tech, port), exact_wordlists in track(EXACT_MATCH_RULES.items(), description="Analyzing exact vs port rules..."):
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
                            )
                        )
    
        """Analyze coverage gaps with specific recommendations."""
        
            cache_data = cache.search_selections(days_back=30, limit=500)
            
            # Analyze missing technologies
            detected_techs = Counter()
            covered_techs = set()
            
                tech = getattr(entry.context, 'tech', None)
                    detected_techs[tech.lower()] += 1
                    
                    # Check if tech has specific rules (enhanced logic)
                    is_covered = False
                    
                    # Check direct appearance in rule names
                        is_covered = True
                    
                    # Check if tech is in matches list of any triggered tech category rule
                            category = rule.replace('tech_category:', '').replace('tech_pattern:', '')
                                matches = TECH_CATEGORY_RULES[category].get('matches', [])
                                    is_covered = True
                    
            
            # Identify missing technologies
                    gap = CoverageGap(
                        gap_type="technology",
                        missing_item=tech,
                        frequency=frequency,
                        suggested_wordlists=self._suggest_wordlists_for_tech(tech),
                        rule_template=self._generate_tech_rule_template(tech),
                        priority="HIGH" if frequency > 5 else "MEDIUM" if frequency > 2 else "LOW"
                    )
                    
            
        # Analyze common ports without rules
        common_ports = {80, 443, 22, 21, 25, 53, 110, 143, 993, 995, 3306, 5432, 6379, 8080, 8443}
        covered_ports = set()
        
            gap = CoverageGap(
                gap_type="port",
                missing_item=str(port),
                frequency=1,  # Estimated
                suggested_wordlists=self._suggest_wordlists_for_port(port),
                rule_template=self._generate_port_rule_template(port),
                priority="MEDIUM"
            )
    
        """Generate automated resolution suggestions."""
        
        # Port conflict resolutions
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
        
        # Logic contradiction resolutions
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
                            )
                        }
                    ],
                    expected_outcome="Reduced contradiction through shared wordlists",
                    risk_level="MEDIUM"
                )
        
        # Coverage gap resolutions
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
    
        """Display detailed port conflict analysis."""
            
        
            tree = Tree(f"[bold red]Port {conflict.port}[/bold red] - {conflict.conflict_severity} Severity")
            
            # Add categories
            categories_branch = tree.add("[cyan]Categories in Conflict[/cyan]")
                cat_branch = categories_branch.add(f"[yellow]{category}[/yellow]")
                wordlists = conflict.wordlists_by_category[category]
            
            # Add impact
            impact_branch = tree.add("[red]Impact Analysis[/red]")
            
            # Add resolutions
            resolution_branch = tree.add("[green]Resolution Suggestions[/green]")
            
            # Add examples
                examples_branch = tree.add("[blue]Examples[/blue]")
            
    
        """Display detailed logic contradiction analysis."""
            
        
        # Group by severity
        by_severity = defaultdict(list)
        
                
            
            table = Table(
                Column("Rule 1", style="cyan", width=20),
                Column("Rule 2", style="yellow", width=20),
                Column("Context", style="blue", width=25),
                Column("Resolution", style="green"),
                title=f"{severity} Logic Contradictions",
                box=box.ROUNDED
            )
            
                )
            
    
        """Display coverage gap analysis."""
            
        
        # Group by type and priority
        by_type = defaultdict(lambda: defaultdict(list))
        
            
                    
                gaps = by_type[gap_type][priority]
                
    
        """Display resolution summary."""
            
        
        resolution_table = Table(
            Column("Conflict ID", style="cyan"),
            Column("Type", style="yellow"),
            Column("Risk", justify="center", style="bold"),
            Column("Expected Outcome", style="green"),
            title="🔧 Available Resolutions",
            box=box.ROUNDED
        )
        
            risk_color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red"}.get(resolution.risk_level, "white")
            )
        
    
    # Helper methods for analysis
        """Assess the severity of a port conflict."""
        total_wordlists = sum(len(wl) for wl in wordlists.values())
        unique_wordlists = len(set().union(*wordlists.values()))
        overlap_ratio = 1 - (unique_wordlists / total_wordlists) if total_wordlists > 0 else 0
        
    
        """Generate impact description for port conflict."""
    
        """Generate resolution suggestions for port conflicts."""
            "Consider splitting port into specific use cases"
        ]
    
        """Generate examples of port conflicts."""
        ]
    
        """Generate resolution for rule contradictions."""
    
        """Generate resolution for port-specific contradictions."""
    
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
        
    
        """Suggest wordlists for missing port."""
        port_suggestions = {
            53: ["dns-common.txt", "dns-records.txt"],
            25: ["smtp-commands.txt", "mail-common.txt"],
            110: ["pop3-commands.txt", "mail-common.txt"],
            143: ["imap-commands.txt", "mail-common.txt"],
            993: ["imap-ssl.txt", "mail-secure.txt"],
            995: ["pop3-ssl.txt", "mail-secure.txt"]
        }
        
    
        """Generate rule template for missing technology."""
            "type": "exact_match",
            "tech": tech,
            "common_ports": [80, 443],
            "wordlists": self._suggest_wordlists_for_tech(tech),
            "weight": 1.0
        }
    
        """Generate rule template for missing port."""
            "type": "port_category",
            "port": port,
            "category": f"port_{port}",
            "wordlists": self._suggest_wordlists_for_port(port),
            "weight": 0.6
        }
    
        """Merge wordlists from multiple categories intelligently."""
        all_wordlists = []
        
        # Remove duplicates while preserving order
        merged = []
        seen = set()
        
    
        """Calculate optimal weights for conflicting categories."""
        # Simple equal weighting for now
        weight = 1.0 / len(categories)
    
        """Find bridge wordlists that could connect contradictory rules."""
        # Find semantic similarities or suggest generic bridges
        bridge_candidates = [
            "common.txt", "dirs.txt", "files.txt", "paths.txt",
            "generic.txt", "discovery.txt"
        ]
        
        # Return bridges that aren't already in either list
        bridges = []
        existing = set(list1 + list2)
        
    
        """Export analysis results."""
            "port_conflicts": [asdict(conflict) for conflict in self.port_conflicts],
            "logic_contradictions": [asdict(contradiction) for contradiction in self.logic_contradictions],
            "coverage_gaps": [asdict(gap) for gap in self.coverage_gaps],
            "resolutions": [asdict(resolution) for resolution in self.resolutions],
            "summary": {
                "total_conflicts": len(self.port_conflicts) + len(self.logic_contradictions) + len(self.coverage_gaps),
                "resolutions_available": len(self.resolutions),
                "high_priority_issues": len([c for c in self.port_conflicts if c.conflict_severity in ["HIGH", "CRITICAL"]]) +
                                      len([c for c in self.coverage_gaps if c.priority == "HIGH"])
            }
        }


    """Main entry point."""
    
    parser = argparse.ArgumentParser(description="Analyze SmartList rule conflicts")
    parser.add_argument("--detailed", action="store_true", help="Show detailed analysis")
    parser.add_argument("--export", type=str, help="Export analysis to JSON file")
    
    args = parser.parse_args()
    
    analyzer = SmartListConflictAnalyzer(verbose=args.detailed)
    results = analyzer.analyze_all_conflicts()
    
            json.dump(results, f, indent=2, default=str)
    
    # Return exit code based on issues found
    high_priority = results["summary"]["high_priority_issues"]


if __name__ == "__main__":
