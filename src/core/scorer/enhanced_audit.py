#!/usr/bin/env python3
"""

- Rule Quality & Conflicts
- Performance & Efficiency 
- Coverage & Gaps
- Statistical Analysis
- Recommendations

    python enhanced_audit.py [--verbose] [--cache-days=30] [--export-json]
"""


# Rich imports for beautiful tables

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent

)

console = Console()

@dataclass
    """Represents a single audit finding."""

@dataclass 
    """Overall audit metrics and scores."""


    """Comprehensive SmartList audit system with advanced flaw detection."""
    
    def __init__(self, verbose: bool = False, cache_days: int = 30):
        self.verbose = verbose
        self.cache_days = cache_days
        self.findings: List[AuditFinding] = []
        self.metrics = AuditMetrics(0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0)
        self.cache_data = []
        
        """Run the complete enhanced audit."""
            "[bold cyan]🔍 Enhanced SmartList Comprehensive Audit[/bold cyan]\n"
            "[dim]Advanced flaw detection with statistical analysis[/dim]",
            border_style="cyan"
        ))
        
        
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
                    "SYSTEM",
                    "HIGH",
                    [],
                    "Investigate audit system integrity",
                    0.9,
                    {"exception": str(e), "section": section_name}
                )
        
        # Calculate final metrics
        
        # Display results
        
    
        """Load and validate cache data."""
            self.cache_data = cache.search_selections(days_back=self.cache_days, limit=1000)
            self.cache_data = []
    
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
            severity = "HIGH" if len(port_conflicts['conflicts']) > 5 else "MEDIUM"
                "Port Conflicts",
                f"[red]{severity}[/red]" if severity == "HIGH" else f"[yellow]{severity}[/yellow]",
            )
            
                "ARCHITECTURE",
                "Port Category Conflicts",
                "Implement port priority system or create composite categories",
                0.8,
            )
        
        # Rule overlap analysis (enhanced)
        overlaps = self._analyze_rule_overlaps()
                "Rule Overlaps",
                "[red]CRITICAL[/red]",
            )
        
        # Orphaned rules detection
        orphaned = self._detect_orphaned_rules()
                "Orphaned Rules",
                "[yellow]MEDIUM[/yellow]",
                "Rules never triggered in cache history"
            )
        
        # Inconsistent naming patterns
        naming_issues = self._analyze_naming_consistency()
                "Naming Inconsistencies",
                "[yellow]LOW[/yellow]",
                "Inconsistent wordlist naming patterns"
            )
        
    
        """Audit performance and efficiency metrics."""
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
                "Avg Rules/Selection",
                "< 5.0",
                "Selection speed" if rule_efficiency['avg_rules_per_selection'] > 5 else "Optimal"
            )
            
            # Cache hit ratio
            cache_metrics = self._analyze_cache_performance()
            status = "✓" if cache_metrics['hit_ratio'] > 0.7 else "⚠"
                "Cache Hit Ratio",
                "> 70%",
                "Memory usage"
            )
            
            # Wordlist distribution efficiency
            distribution = self._analyze_wordlist_distribution()
            status = "✓" if distribution['gini_coefficient'] < 0.6 else "⚠"
                "Distribution Equity",
                "> 40%",
                "Recommendation quality"
            )
            
            
            # Add performance findings
                    "PERFORMANCE",
                    "HIGH",
                    "Excessive Rule Evaluation",
                    [],
                    "Optimize rule ordering and add early exit conditions",
                    0.9,
                )
                "SYSTEM",
                "MEDIUM",
                "Performance Audit Failed",
                [],
                "Review performance audit implementation",
                0.7,
                {"error": str(e)}
            )
    
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
            "Technologies",
            "HIGH" if tech_coverage['coverage_percentage'] < 0.8 else "MEDIUM"
        )
        
        # Port coverage
        port_coverage = self._analyze_port_coverage()
            "Common Ports",
            "MEDIUM"
        )
        
        # Service pattern coverage
        service_coverage = self._analyze_service_coverage()
            "Service Patterns",
            "LOW"
        )
        
        
        # Add gap findings
                "COVERAGE",
                "HIGH",
                "Insufficient Technology Coverage",
                "Add rules for frequently encountered technologies",
                0.8,
            )
    
        """Advanced statistical analysis of rule quality."""
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
                "Recommendation Entropy",
                f"[green]{quality}[/green]" if quality == "GOOD" else f"[red]{quality}[/red]",
                "📈" if entropy_metrics['trend'] > 0 else "📉"
            )
            
            # Prediction accuracy
            accuracy_metrics = self._calculate_prediction_accuracy()
            quality = "EXCELLENT" if accuracy_metrics['accuracy'] > 0.8 else "GOOD" if accuracy_metrics['accuracy'] > 0.6 else "POOR"
                "Prediction Accuracy",
                "📈"
            )
            
            # Rule effectiveness correlation
            correlation = self._calculate_rule_effectiveness()
            quality = "STRONG" if abs(correlation['correlation']) > 0.7 else "MODERATE" if abs(correlation['correlation']) > 0.4 else "WEAK"
                "Rule-Success Correlation",
                "📊"
            )
            
                "SYSTEM",
                "MEDIUM",
                "Statistical Analysis Failed",
                [],
                "Review statistical analysis implementation",
                0.7,
                {"error": str(e)}
            )
    
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
            "Duplicate Recommendations",
            f"[red]{waste_level}[/red]" if waste_level == "HIGH" else f"[yellow]{waste_level}[/yellow]",
        )
        
        # Redundant rules
        redundant_rules = self._find_redundant_rules()
            "Redundant Rules",
            "[yellow]MEDIUM[/yellow]",
        )
        
    
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
                "Infinite Loop Risk",
                "[red]CRITICAL[/red]",
                "Review regex patterns immediately"
            )
        
        # Memory exhaustion risks
        memory_risks = self._detect_memory_risks()
        if memory_risks['risk_level'] == "HIGH":
                "Memory Exhaustion",
                "[red]HIGH[/red]",
                "Rule evaluation engine",
                "Implement resource limits"
            )
        
        # Logic contradictions
        contradictions = self._detect_logic_contradictions()
                "Logic Contradictions",
                "[red]HIGH[/red]",
                "Resolve conflicting logic"
            )
        
                               title="🚨 Critical Flaw Detection", 
                               border_style="green"))
    
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
                "ReDoS Vulnerability",
                "[red]HIGH[/red]",
                "Potential DoS attacks"
            )
        
        # Overly broad patterns
        broad_patterns = self._detect_overly_broad_patterns()
            "Overly Broad Patterns",
            "[yellow]MEDIUM[/yellow]",
            "False positive increase"
        )
        
        # Inefficient patterns
        inefficient = self._detect_inefficient_patterns()
            "Inefficient Patterns",
            "[yellow]LOW[/yellow]",
            "Slower evaluation"
        )
        
    
        """Analyze usage trends and prediction accuracy."""
                               title="📈 Trend Analysis"))
        
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
        
            change_icon = "📈" if trend_data['change'] > 0 else "📉" if trend_data['change'] < 0 else "➡️"
            change_color = "green" if trend_data['change'] > 0 else "red" if trend_data['change'] < 0 else "yellow"
            
            )
        

    # Helper methods for detailed analysis
        """Analyze port conflicts in detail."""
        port_assignments = defaultdict(list)
        
        
        conflicts = {port: categories for port, categories in port_assignments.items() 
        
            "conflicts": conflicts,
            "total_ports": len(port_assignments),
            "conflict_percentage": len(conflicts) / len(port_assignments) if port_assignments else 0
        }
    
        """Analyze wordlist overlaps across rule categories."""
        wordlist_sources = defaultdict(list)
        
        # Collect all wordlists and their sources
            tech, port = key
            source = f"exact:{tech}:{port}"
        
            source = f"tech_category:{category}"
        
        # Analyze overlaps
        critical_overlaps = {wl: sources for wl, sources in wordlist_sources.items() 
        moderate_overlaps = {wl: sources for wl, sources in wordlist_sources.items() 
                           if len(sources) == 3}
        
            "critical_overlaps": critical_overlaps,
            "moderate_overlaps": moderate_overlaps,
            "total_wordlists": len(wordlist_sources),
            "overlap_percentage": len(critical_overlaps) / len(wordlist_sources) if wordlist_sources else 0
        }
    
        """Detect rules that are never used."""
        
        used_rules = set()
        
        all_rules = set()
        
        
        orphaned_rules = all_rules - used_rules
        
            "count": len(orphaned_rules),
            "rules": list(orphaned_rules),
            "usage_percentage": len(used_rules) / len(all_rules) if all_rules else 0
        }
    
        """Analyze naming consistency across wordlists."""
        all_wordlists = set()
        
        # Collect all wordlists
        
        
        # Analyze naming patterns
        naming_patterns = defaultdict(list)
            # Extract base patterns
                pattern = '-'.join(wl.split('-')[:-1])  # Remove last part
                pattern = '_'.join(wl.split('_')[:-1])
        
        inconsistent_count = sum(1 for wordlists in naming_patterns.values() 
                               if len(wordlists) == 1)  # Singleton patterns might be inconsistent
        
            "total_wordlists": len(all_wordlists),
            "naming_patterns": len(naming_patterns),
            "inconsistent_count": inconsistent_count
        }
    
        """Calculate rule evaluation efficiency metrics."""
        
        rules_per_selection = [len(entry.result.matched_rules) for entry in self.cache_data]
        
            "avg_rules_per_selection": sum(rules_per_selection) / len(rules_per_selection),
            "max_rules": max(rules_per_selection),
            "min_rules": min(rules_per_selection),
            "efficiency_score": 1.0 / (sum(rules_per_selection) / len(rules_per_selection))
        }
    
        """Analyze cache performance metrics."""
        # Simplified cache analysis
        total_requests = len(self.cache_data)
        
        unique_contexts = set()
            context = entry.context
            port = getattr(context, 'port', 0)
            tech = getattr(context, 'tech', '') or ''
            # Use a generic identifier for target if not available
            target = getattr(context, 'target', 'anonymous')
        
        hit_ratio = 1 - (len(unique_contexts) / total_requests) if total_requests > 0 else 0
        
            "total_requests": total_requests,
            "unique_contexts": len(unique_contexts),
            "hit_ratio": hit_ratio
        }
    
        """Analyze wordlist usage distribution."""
        
        wordlist_counts = Counter()
                wordlist_counts[wl] += 1
        
        # Calculate Gini coefficient
        counts = sorted(wordlist_counts.values())
        n = len(counts)
        index = range(1, n + 1)
        gini = 2 * sum(index[i] * counts[i] for i in range(n)) / (n * sum(counts)) - (n + 1) / n
        
            "gini_coefficient": gini,
            "unique_wordlists": len(wordlist_counts),
            "total_recommendations": sum(wordlist_counts.values())
        }
    
        """Analyze technology coverage gaps."""
        
        detected_techs = set()
        covered_techs = set()
        
        # Import TECH_CATEGORY_RULES to check matches
        
            tech = getattr(entry.context, 'tech', None)
                
                # Check if tech has specific rules (direct match in rule name)
                is_covered = False
                
                # Check direct appearance in rule names
                    is_covered = True
                
                # Check if tech is in matches list of any triggered tech category rule
                        category = rule.replace('tech_category:', '').replace('tech_pattern:', '')
                            matches = TECH_CATEGORY_RULES[category].get('matches', [])
                                is_covered = True
                
        
        missing_technologies = detected_techs - covered_techs
        coverage_percentage = len(covered_techs) / len(detected_techs) if detected_techs else 1.0
        
            "coverage_percentage": coverage_percentage,
            "missing_count": len(missing_technologies),
            "missing_technologies": list(missing_technologies),
            "total_detected": len(detected_techs)
        }
    
        """Analyze port coverage gaps."""
        common_ports = {80, 443, 22, 21, 25, 53, 110, 143, 993, 995, 3306, 5432, 6379, 8080, 8443}
        
        covered_ports = set()
        
        uncovered_ports = common_ports - covered_ports
        
            "coverage_percentage": len(covered_ports & common_ports) / len(common_ports),
            "uncovered_count": len(uncovered_ports),
            "uncovered_ports": list(uncovered_ports)
        }
    
        """Analyze service pattern coverage."""
        
        # Collect unique service patterns from cache
        service_patterns = set()
        covered_patterns = set()
        
            # Get service info from context
            service = getattr(entry.context, 'service', None) or getattr(entry.context, 'service_fingerprint', '')
                # Extract service keywords
                service_lower = str(service).lower()
                        
                        # Check if this service pattern has matching rules
        
        # Calculate coverage
        total_patterns = len(service_patterns)
        covered_count = len(covered_patterns)
        missing_count = total_patterns - covered_count
        
        pattern_coverage = covered_count / total_patterns if total_patterns > 0 else 1.0
        
            "pattern_coverage": pattern_coverage,
            "missing_patterns": missing_count
        }
    
        """Calculate Shannon entropy of recommendations."""
        
        wordlist_counts = Counter()
                wordlist_counts[wl] += 1
        
        total = sum(wordlist_counts.values())
        entropy = -sum((count / total) * math.log2(count / total) 
        
        # Calculate trend by comparing first half vs second half of data
        trend = 0.0
        if len(self.cache_data) >= 10:
            mid_point = len(self.cache_data) // 2
            first_half = self.cache_data[:mid_point]
            second_half = self.cache_data[mid_point:]
            
            # Calculate entropy for each half
                wl_counts = Counter()
                        wl_counts[wl] += 1
                total = sum(wl_counts.values())
                if total == 0:
            
            first_entropy = calculate_entropy_for_subset(first_half)
            second_entropy = calculate_entropy_for_subset(second_half)
            
            # Calculate trend (positive = increasing entropy/diversity)
                trend = (second_entropy - first_entropy) / first_entropy
        
            "entropy": entropy,
            "trend": trend
        }
    
        """Calculate prediction accuracy metrics based on cache success data."""
        
        # Calculate accuracy based on successful vs failed selections
        successful_selections = 0
        total_selections = len(self.cache_data)
        
            # Consider a selection successful if it has wordlists and rules matched
                successful_selections += 1
        
        accuracy = successful_selections / total_selections if total_selections > 0 else 0.0
        
            "accuracy": accuracy
        }
    
        """Calculate correlation between rule types and recommendation success."""
        
        # Analyze correlation between rule types and wordlist count
        rule_wordlist_pairs = []
        
            rule_count = len(entry.result.matched_rules)
            wordlist_count = len(entry.result.wordlists)
        
        # Calculate Pearson correlation coefficient
        
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
            correlation = numerator / (x_variance * y_variance) ** 0.5
        
            "correlation": correlation
        }
    
        """Find duplicate recommendations."""
        
        duplicate_count = 0
        total_recommendations = 0
        
            wordlists = entry.result.wordlists
            total_recommendations += len(wordlists)
            duplicate_count += len(wordlists) - len(set(wordlists))
        
        percentage = duplicate_count / total_recommendations if total_recommendations > 0 else 0
        
            "count": duplicate_count,
            "percentage": percentage,
            "potential_reduction": percentage * 0.8  # Estimated reduction
        }
    
        """Find redundant rules that produce identical results."""
        
        # Group entries by their rule patterns to find redundancy
        rule_patterns = defaultdict(list)
        
            rule_signature = tuple(sorted(entry.result.matched_rules))
            wordlist_signature = tuple(sorted(entry.result.wordlists))
        
        # Find rules that always produce the same wordlists
        redundant_pairs = []
        total_rules = len(rule_patterns)
        
            unique_wordlists = set(wordlist_sigs)
            if len(unique_wordlists) == 1 and len(wordlist_sigs) > 1:
                # This rule pattern always produces the same result
                    "rules": rule_sig,
                    "always_produces": list(unique_wordlists)[0],
                    "occurrences": len(wordlist_sigs)
                })
        
        # Calculate potential complexity reduction
        redundant_rule_count = len(redundant_pairs)
        complexity_reduction = (redundant_rule_count / total_rules * 100) if total_rules > 0 else 0
        
            "redundant_pairs": redundant_pairs,
            "complexity_reduction": int(complexity_reduction)
        }
    
        """Detect patterns that could cause infinite loops."""
        high_risk_patterns = []
        
                pattern = config["fallback_pattern"]
                # Check for risky regex patterns
        
            "high_risk_patterns": high_risk_patterns
        }
    
        """Detect potential memory exhaustion risks."""
        # Analyze rule complexity
        total_rules = len(EXACT_MATCH_RULES) + len(TECH_CATEGORY_RULES) + len(PORT_CATEGORY_RULES)
        total_wordlists = len(set().union(*[wls for wls in EXACT_MATCH_RULES.values()]))
        
        risk_level = "HIGH" if total_rules * total_wordlists > 10000 else "MEDIUM" if total_rules * total_wordlists > 1000 else "LOW"
        
            "risk_level": risk_level,
            "complexity_score": total_rules * total_wordlists
        }
    
        """Detect contradictory logic in rules."""
        contradictory_rules = []
        
        # Check for exact match rules that conflict with category rules
            # Find any tech category rules that would also match
                    # Check if they recommend different wordlists
                    category_wordlists = set(config["wordlists"])
                    exact_wordlists_set = set(exact_wordlists)
                    
                            "exact_rule": f"exact:{tech}:{port}",
                            "category_rule": f"tech_category:{category}",
                            "conflict": "Recommend different wordlists for same context"
                        })
        
        # Check for port category conflicts with exact rules
        port_conflicts = []
                    category_wordlists = set(config["wordlists"])
                    exact_wordlists_set = set(exact_wordlists)
                    
                    # If they don't share any wordlists, it's a potential contradiction
                            "exact_rule": f"exact:{tech}:{port}",
                            "port_rule": f"port_category:{category}",
                            "conflict": "No wordlist overlap between specific and general rules"
                        })
        
        all_contradictions = contradictory_rules + port_conflicts
        
            "contradictory_rules": all_contradictions
        }
    
        """Detect ReDoS (Regular Expression Denial of Service) vulnerabilities."""
        vulnerable_patterns = []
        
                pattern = config["fallback_pattern"]
                # Check for ReDoS patterns
        
            "vulnerable_patterns": vulnerable_patterns
        }
    
        """Detect overly broad regex patterns."""
        broad_patterns = []
        
        broad_terms = ["admin", "management", "api", "web", "http", "server", "service"]
        
                pattern = config["fallback_pattern"].lower()
        
            "broad_patterns": broad_patterns
        }
    
        """Detect inefficient regex patterns."""
        inefficient_patterns = []
        
                pattern = config["fallback_pattern"]
                # Check for inefficient patterns
        
            "inefficient_patterns": inefficient_patterns
        }
    
        """Analyze usage trends over time."""
        
        # Split data into two periods
        sorted_data = sorted(self.cache_data, key=lambda x: x.timestamp)
        mid_point = len(sorted_data) // 2
        
        current_period = sorted_data[mid_point:]
        previous_period = sorted_data[:mid_point]
        
        # Calculate metrics for each period
            wordlist_count = sum(len(entry.result.wordlists) for entry in data)
            rule_count = sum(len(entry.result.matched_rules) for entry in data)
                "avg_wordlists": wordlist_count / len(data) if data else 0,
                "avg_rules": rule_count / len(data) if data else 0
            }
        
        current_metrics = calculate_period_metrics(current_period)
        previous_metrics = calculate_period_metrics(previous_period)
        
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
    
        """Calculate overall audit metrics based on real analysis."""
        severity_counts = Counter(finding.severity for finding in self.findings)
        
        # Calculate real coverage score
        tech_coverage = self._analyze_technology_coverage()
        port_coverage = self._analyze_port_coverage()
        service_coverage = self._analyze_service_coverage()
        coverage_score = (tech_coverage['coverage_percentage'] * 0.5 + 
        
        # Calculate real efficiency score
        rule_efficiency = self._calculate_rule_efficiency()
        cache_metrics = self._analyze_cache_performance()
        distribution = self._analyze_wordlist_distribution()
        efficiency_score = ((1 / max(1, rule_efficiency['avg_rules_per_selection'] / 5)) * 0.4 + 
                           (1 - distribution['gini_coefficient']) * 0.3) * 100
        
        # Calculate real quality score based on findings and metrics
        entropy_metrics = self._calculate_recommendation_entropy()
        accuracy_metrics = self._calculate_prediction_accuracy()
        
        # Normalize entropy (typical good range is 3-6)
        entropy_normalized = min(1.0, max(0.0, (entropy_metrics['entropy'] - 2) / 4))
        quality_score = (entropy_normalized * 0.4 + 
                        (1 - (severity_counts.get("CRITICAL", 0) + severity_counts.get("HIGH", 0)) / max(1, len(self.findings))) * 0.2) * 100
        
        self.metrics = AuditMetrics(
            total_findings=len(self.findings),
            critical_count=severity_counts.get("CRITICAL", 0),
            high_count=severity_counts.get("HIGH", 0),
            medium_count=severity_counts.get("MEDIUM", 0),
            low_count=severity_counts.get("LOW", 0),
            info_count=severity_counts.get("INFO", 0),
            overall_score=max(0, 100 - (severity_counts.get("CRITICAL", 0) * 25 + 
            coverage_score=coverage_score,
            efficiency_score=efficiency_score,
            quality_score=quality_score
        )
    
        """Display comprehensive audit results."""
        # Overall score panel
        score_color = "green" if self.metrics.overall_score >= 80 else "yellow" if self.metrics.overall_score >= 60 else "red"
        
        score_panel = Panel(
            title="🎯 Audit Summary",
            border_style=score_color
        )
        
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
        
                severity_color = {
                    "CRITICAL": "red", "HIGH": "red", "MEDIUM": "yellow", 
                    "LOW": "blue", "INFO": "dim"
                }[severity]
                )
        
        
        # Detailed findings (top 10 most critical)
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
            
                severity_color = {
                    "CRITICAL": "red", "HIGH": "red", "MEDIUM": "yellow", 
                    "LOW": "blue", "INFO": "dim"
                }[finding.severity]
                
                )
            
        
        # Add detailed conflict analysis if available
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
            
                "Total Conflicts Found",
                "[red]REVIEW NEEDED[/red]" if total_conflicts > 0 else "[green]CLEAN[/green]"
            )
                "High Priority Issues",
                "[red]CRITICAL[/red]" if high_priority > 0 else "[green]OK[/green]"
            )
                "Automated Resolutions",
                "[green]AVAILABLE[/green]" if resolutions > 0 else "[yellow]MANUAL REVIEW[/yellow]"
            )
            
            
                    "[bold red]⚠️  HIGH PRIORITY CONFLICTS DETECTED[/bold red]\n\n"
                    "Quick Actions:\n"
                    "• Port conflicts: Create unified categories with weighted wordlists\n" 
                    "• Logic contradictions: Add shared wordlists or set rule priorities\n"
                    "• Coverage gaps: Generate rules for missing technologies",
                    border_style="red",
                    title="🚨 Action Required"
                ))
            
    
        """Export audit results for programmatic use."""
            "timestamp": datetime.now().isoformat(),
            "metrics": asdict(self.metrics),
            "findings": [asdict(finding) for finding in self.findings],
            "summary": {
                "total_rules_analyzed": len(EXACT_MATCH_RULES) + len(TECH_CATEGORY_RULES),
                "cache_entries_analyzed": len(self.cache_data),
                "audit_version": "2.0.0"
            }
        }


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
    
            json.dump(results, f, indent=2, default=str)
    
    # Exit with error code based on findings


if __name__ == "__main__":
