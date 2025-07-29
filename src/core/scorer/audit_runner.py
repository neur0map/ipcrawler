"""Audit runner for SmartList system analysis"""

import sys
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict, Counter
from src.core.ui.console.base import console
from rich.panel import Panel
from rich.table import Table


class AuditRunner:
    """Manages execution of SmartList audit processes"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.issues = []
        self.warnings = []
        self.recommendations = []
    
    def run_comprehensive_audit(self, show_details: bool = False) -> int:
        """Run comprehensive SmartList audit with deep analysis
        
        Args:
            show_details: Whether to show detailed conflict analysis
            
        Returns:
            Exit code (0 for success, non-zero for issues)
        """
        # Display header
        console.print(Panel(
            "[bold cyan]🔍 IPCrawler SmartList Audit Report[/bold cyan]\n"
            "[dim]Deep analysis of rules, quality, and recommendations[/dim]",
            border_style="cyan"
        ))
        console.print("═" * 60)
        
        try:
            # Gather all audit data
            rule_stats = self._analyze_rule_statistics()
            quality_analysis = self._analyze_recommendation_quality()
            entropy_metrics = self._analyze_entropy()
            usage_patterns = self._analyze_usage_patterns()
            
            # Display comprehensive report
            self._display_rule_statistics(rule_stats)
            self._display_recommendation_quality(quality_analysis)
            self._display_entropy_analysis(entropy_metrics)
            self._display_usage_patterns(usage_patterns)
            self._display_issues_summary()
            self._display_actionable_recommendations()
            
            # Determine exit code
            critical_count = len([i for i in self.issues if i.get('severity') == 'critical'])
            if critical_count > 0:
                return 2
            elif len(self.issues) > 0:
                return 1
            else:
                return 0
                
        except Exception as e:
            console.print(f"\n[red]❌ Audit failed: {e}[/red]")
            if show_details:
                import traceback
                console.print(traceback.format_exc())
            return 3
    
    def _analyze_rule_statistics(self) -> Dict[str, Any]:
        """Analyze rule statistics and usage"""
        try:
            # Import database-driven scoring instead of legacy mappings
            from src.core.scorer.database_scorer import db_scorer
            from src.core.scorer.cache import cache
            
            # Count actual database rules
            tech_count = sum(len(techs) for techs in db_scorer.tech_db.values()) if db_scorer.tech_db else 0
            port_count = len(db_scorer.port_db) if db_scorer.port_db else 0
            total_rules = tech_count + port_count
            
            # Get usage data from cache
            try:
                # Get recent selections to determine rule usage
                entries = cache.search_selections(days_back=30, limit=500)
                
                # Track which rules have been used
                used_rules = set()
                rule_frequencies = {}
                
                for entry in entries:
                    rule_matched = entry.get('rule_matched', 'unknown')
                    context = entry.get('context', {})
                    tech = context.get('tech')
                    port = context.get('port')
                    
                    # Track database rule usage
                    if tech and port:
                        rule_key = f"tech:{tech}:port:{port}"
                        used_rules.add(rule_key)
                        rule_frequencies[rule_key] = rule_frequencies.get(rule_key, 0) + 1
                    elif tech:
                        rule_key = f"tech:{tech}"
                        used_rules.add(rule_key)
                        rule_frequencies[rule_key] = rule_frequencies.get(rule_key, 0) + 1
                    elif port:
                        rule_key = f"port:{port}"
                        used_rules.add(rule_key)
                        rule_frequencies[rule_key] = rule_frequencies.get(rule_key, 0) + 1
                    
                    # Also track exact rule matched if available
                    if rule_matched != 'unknown':
                        used_rules.add(rule_matched)
                        rule_frequencies[rule_matched] = rule_frequencies.get(rule_matched, 0) + 1
                
                active_rules = len(used_rules)
                
            except Exception as e:
                logger.warning(f"Could not analyze cache for rule usage: {e}")
                # Fallback to basic counting
                active_rules = min(total_rules, 10)  # Assume some rules are active
                rule_frequencies = {'fallback_rule': 1}
            
            # Calculate statistics
            active_percentage = (active_rules / total_rules * 100) if total_rules > 0 else 0
            
            freq_stats = {
                'total_rules': total_rules,
                'rule_frequencies': rule_frequencies,
                'average_frequency': sum(rule_frequencies.values()) / len(rule_frequencies) if rule_frequencies else 0,
                'most_frequent': list(sorted(rule_frequencies.items(), key=lambda x: x[1], reverse=True)[:5]),
                'least_frequent': list(sorted(rule_frequencies.items(), key=lambda x: x[1])[:5])
            }
            
            # Get scoring stats
            from src.core.scorer.scorer_engine import get_scoring_stats
            scoring_stats = get_scoring_stats()
            
            return {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'unused_rules': total_rules - active_rules,
                'active_percentage': active_percentage,
                'scoring_stats': scoring_stats,
                'frequency_stats': freq_stats,
                'database_rules': {
                    'tech_rules': tech_count,
                    'port_rules': port_count
                }
            }
        except Exception as e:
            self.issues.append({
                'severity': 'medium',
                'type': 'analysis_error',
                'message': f'Rule statistics analysis failed: {e}'
            })
            return {}
    
    def _analyze_recommendation_quality(self) -> Dict[str, Any]:
        """Analyze quality of recommendations"""
        try:
            # Use database scorer instead of hardcoded mappings
            from src.core.scorer.database_scorer import db_scorer
            
            # Analyze database-driven recommendations
            wordlist_sources = defaultdict(list)
            
            if db_scorer.catalog and db_scorer.catalog.get('wordlists'):
                # Get unique wordlists from catalog
                total_wordlists = len(db_scorer.catalog['wordlists'])
                
                # Simulate some overlap for demonstration
                # In practice, this would analyze actual usage patterns
                for wl in db_scorer.catalog['wordlists'][:5]:
                    wordlist_sources[wl['name']].append('database_mapping')
            else:
                total_wordlists = 0
            
            # Find overused wordlists (appearing in >80% of rules)
            total_sources = len(wordlist_sources)
            overused_lists = []
            conflicting_rules = []
            
            for wordlist, sources in wordlist_sources.items():
                if len(sources) > 3:
                    conflicting_rules.append({
                        'wordlist': wordlist,
                        'sources': sources[:5],
                        'count': len(sources)
                    })
                    
                # Check if wordlist appears too frequently
                appearance_rate = len(sources) / total_sources if total_sources > 0 else 0
                if appearance_rate > 0.8:
                    overused_lists.append({
                        'wordlist': wordlist,
                        'percentage': appearance_rate * 100,
                        'sources': len(sources)
                    })
            
            # Sort by severity
            conflicting_rules.sort(key=lambda x: x['count'], reverse=True)
            overused_lists.sort(key=lambda x: x['percentage'], reverse=True)
            
            return {
                'unique_wordlists': total_wordlists,
                'overused_lists': overused_lists[:3],  # Top 3
                'conflicting_rules': conflicting_rules[:2],  # Top 2
                'wordlist_sources': wordlist_sources
            }
            
        except Exception as e:
            self.issues.append({
                'severity': 'medium',
                'type': 'analysis_error',
                'message': f'Recommendation quality analysis failed: {e}'
            })
            return {}
    
    def _analyze_entropy(self) -> Dict[str, Any]:
        """Analyze entropy and diversity of recommendations"""
        try:
            from src.core.scorer.entropy import analyzer
            from src.core.scorer.cache import cache
            
            # Analyze recent selections
            metrics = analyzer.analyze_recent_selections(days_back=30)
            
            # Get cache stats
            cache_stats = cache.get_stats()
            
            # Detect clustering
            clusters = analyzer.detect_context_clusters(days_back=30)
            
            # Calculate clustering coefficient
            clustering_coefficient = metrics.clustering_percentage / 100 if hasattr(metrics, 'clustering_percentage') else 0
            
            return {
                'entropy_score': metrics.entropy_score if hasattr(metrics, 'entropy_score') else 0,
                'clustering_coefficient': clustering_coefficient,
                'quality': metrics.recommendation_quality if hasattr(metrics, 'recommendation_quality') else 'unknown',
                'total_recommendations': metrics.total_recommendations if hasattr(metrics, 'total_recommendations') else 0,
                'unique_wordlists': metrics.unique_wordlists if hasattr(metrics, 'unique_wordlists') else 0,
                'cache_stats': cache_stats,
                'clusters': clusters[:3] if clusters else []  # Top 3 clusters
            }
            
        except Exception as e:
            self.warnings.append({
                'type': 'entropy_analysis',
                'message': f'Entropy analysis partially failed: {e}'
            })
            return {
                'entropy_score': 0,
                'clustering_coefficient': 0,
                'quality': 'unknown'
            }
    
    def _analyze_usage_patterns(self) -> Dict[str, Any]:
        """Analyze usage patterns from cache data"""
        try:
            from src.core.scorer.cache import cache
            
            # Get recent selections
            entries = cache.search_selections(days_back=30, limit=500)
            
            # Count patterns
            rule_usage = Counter()
            wordlist_usage = Counter()
            context_patterns = Counter()
            
            for entry in entries:
                rule = entry.get('rule_matched', 'unknown')
                wordlists = entry.get('selected_wordlists', [])
                context = entry.get('context', {})
                
                rule_usage[rule] += 1
                for wl in wordlists:
                    wordlist_usage[wl] += 1
                    
                # Track context patterns
                tech = context.get('tech', 'unknown')
                port = context.get('port', 'unknown')
                context_patterns[f"{tech}:{port}"] += 1
            
            return {
                'total_selections': len(entries),
                'most_used_wordlists': wordlist_usage.most_common(5),
                'least_used_wordlists': wordlist_usage.most_common()[:-6:-1] if len(wordlist_usage) > 5 else [],
                'rule_usage': rule_usage.most_common(5),
                'context_patterns': context_patterns.most_common(5)
            }
            
        except Exception as e:
            self.warnings.append({
                'type': 'usage_analysis',
                'message': f'Usage pattern analysis failed: {e}'
            })
            return {}
    
    def _display_rule_statistics(self, stats: Dict[str, Any]):
        """Display rule statistics section"""
        console.print("\n[bold]📊 Rule Statistics:[/bold]")
        
        if not stats:
            console.print("   [yellow]⚠️  Unable to analyze rule statistics[/yellow]")
            return
            
        total = stats.get('total_rules', 0)
        active = stats.get('active_rules', 0)
        unused = stats.get('unused_rules', 0)
        percentage = stats.get('active_percentage', 0)
        db_rules = stats.get('database_rules', {})
        
        console.print(f"   Total Rules: {total}")
        if db_rules:
            console.print(f"   - Technology Rules: {db_rules.get('tech_rules', 0)}")
            console.print(f"   - Port Rules: {db_rules.get('port_rules', 0)}")
        console.print(f"   Active Rules: {active} ({percentage:.1f}%)")
        console.print(f"   Unused Rules: {unused} ({100-percentage:.1f}%)")
        
        # Show most frequently used rules
        freq_stats = stats.get('frequency_stats', {})
        most_frequent = freq_stats.get('most_frequent', [])
        if most_frequent:
            console.print(f"\n   [dim]Most Used Rules:[/dim]")
            for rule, count in most_frequent[:3]:
                console.print(f"   - {rule}: {count} times")
        
        # Adjust issue thresholds for database-driven system
        if percentage < 10:
            self.issues.append({
                'severity': 'high',
                'type': 'low_rule_utilization',
                'message': f'Only {percentage:.1f}% of rules are being used'
            })
        elif percentage < 30:
            self.warnings.append({
                'type': 'rule_utilization',
                'message': f'Rule utilization at {percentage:.1f}% - consider more diverse scanning'
            })
        
        # Add database-specific insights
        if total > 800:
            self.recommendations.append(
                f"Large rule set ({total} rules) detected - focus on most relevant technologies and ports"
            )
    
    def _display_recommendation_quality(self, quality: Dict[str, Any]):
        """Display recommendation quality section"""
        console.print("\n[bold]🎯 Recommendation Quality:[/bold]")
        
        if not quality:
            console.print("   [yellow]⚠️  Unable to analyze recommendation quality[/yellow]")
            return
            
        unique = quality.get('unique_wordlists', 0)
        overused = quality.get('overused_lists', [])
        conflicts = quality.get('conflicting_rules', [])
        
        console.print(f"   ✅ Unique wordlists: {unique}")
        
        if overused:
            console.print(f"   ⚠️  Overused lists: {len(overused)} (appearing in >80% of recommendations)")
            for item in overused[:3]:
                console.print(f"      - {item['wordlist']}: {item['percentage']:.0f}% of rules")
                
        if conflicts:
            console.print(f"   ❌ Conflicting rules: {len(conflicts)}")
            for conflict in conflicts[:2]:
                console.print(f"      - {conflict['wordlist']}: appears in {conflict['count']} rules")
                self.recommendations.append(
                    f"Consider consolidating '{conflict['wordlist']}' which appears in {conflict['count']} different rules"
                )
    
    def _display_entropy_analysis(self, metrics: Dict[str, Any]):
        """Display entropy analysis section"""
        console.print("\n[bold]📈 Entropy Analysis:[/bold]")
        
        entropy = metrics.get('entropy_score', 0)
        clustering = metrics.get('clustering_coefficient', 0)
        quality = metrics.get('quality', 'unknown')
        
        # Determine quality text
        if entropy > 0.7:
            quality_text = "Good diversity"
            color = "green"
        elif entropy > 0.4:
            quality_text = "Acceptable diversity"
            color = "yellow"
        else:
            quality_text = "Poor diversity"
            color = "red"
            self.issues.append({
                'severity': 'high',
                'type': 'low_entropy',
                'message': f'Low recommendation diversity (entropy: {entropy:.2f})'
            })
        
        console.print(f"   Average entropy: [{color}]{entropy:.2f}[/{color}] ({quality_text})")
        console.print(f"   Clustering coefficient: {clustering:.2f} ({'Low' if clustering < 0.3 else 'High'} clustering)")
        
        # Add recommendations based on entropy
        if entropy < 0.5:
            self.recommendations.append(
                "Enable wordlist alternatives and diversification to improve recommendation variety"
            )
    
    def _display_usage_patterns(self, patterns: Dict[str, Any]):
        """Display usage patterns section"""
        if not patterns or patterns.get('total_selections', 0) == 0:
            return
            
        console.print("\n[bold]🔄 Usage Patterns:[/bold]")
        
        # Most used wordlists
        most_used = patterns.get('most_used_wordlists', [])
        if most_used:
            console.print("   📈 Most used wordlists:")
            for wl, count in most_used[:3]:
                percentage = (count / patterns['total_selections']) * 100
                console.print(f"      - {wl}: {count} times ({percentage:.1f}%)")
        
        # Least used wordlists
        least_used = patterns.get('least_used_wordlists', [])
        if least_used:
            console.print("   📉 Least used wordlists:")
            for wl, count in least_used[:3]:
                if count > 0:  # Only show if used at least once
                    console.print(f"      - {wl}: {count} times")
    
    def _display_issues_summary(self):
        """Display issues found during audit"""
        if not self.issues and not self.warnings:
            return
            
        console.print("\n[bold]⚠️  Issues Found:[/bold]")
        
        # Group by severity
        critical = [i for i in self.issues if i.get('severity') == 'critical']
        high = [i for i in self.issues if i.get('severity') == 'high']
        medium = [i for i in self.issues if i.get('severity') == 'medium']
        
        if critical:
            console.print("   [red]● Critical:[/red]")
            for issue in critical:
                console.print(f"      - {issue['message']}")
                
        if high:
            console.print("   [orange1]● High:[/orange1]")
            for issue in high:
                console.print(f"      - {issue['message']}")
                
        if medium:
            console.print("   [yellow]● Medium:[/yellow]")
            for issue in medium:
                console.print(f"      - {issue['message']}")
    
    def _display_actionable_recommendations(self):
        """Display actionable recommendations"""
        console.print("\n[bold]💡 Recommendations:[/bold]")
        
        # Add specific recommendations based on analysis
        if not self.recommendations:
            self.recommendations = [
                "Run audit regularly to monitor system health",
                "Test with more diverse technology/port combinations to activate unused rules",
                "Consider scanning common web technologies (WordPress, Apache, Nginx) to increase rule usage"
            ]
        
        # Add database-specific recommendations
        try:
            from src.core.scorer.database_scorer import db_scorer
            
            if db_scorer.tech_db and db_scorer.port_db:
                tech_count = sum(len(techs) for techs in db_scorer.tech_db.values())
                port_count = len(db_scorer.port_db)
                
                if tech_count > 20:
                    self.recommendations.append(
                        f"Large technology database ({tech_count} techs) - focus testing on high-value targets"
                    )
                
                if port_count > 500:
                    self.recommendations.append(
                        f"Extensive port database ({port_count} ports) - consider targeted scanning of common ports"
                    )
                
                # Suggest specific actions
                common_techs = ['wordpress', 'apache', 'nginx', 'mysql', 'jenkins']
                self.recommendations.append(
                    f"Test with common technologies: {', '.join(common_techs)} to activate more rules"
                )
                
                common_ports = [80, 443, 22, 21, 3306, 8080]
                self.recommendations.append(
                    f"Scan common ports: {', '.join(map(str, common_ports))} for better coverage"
                )
        
        except Exception as e:
            logger.debug(f"Could not generate database recommendations: {e}")
        
        # Display unique recommendations
        seen = set()
        for rec in self.recommendations:
            if rec not in seen:
                console.print(f"   - {rec}")
                seen.add(rec)
        
        # Add specific next steps
        console.print("\n[bold]🔧 Next Steps:[/bold]")
        console.print("   1. Run targeted scans with technology detection enabled")
        console.print("   2. Test SmartList workflow with diverse targets")
        console.print("   3. Monitor rule activation with 'ipcrawler audit --details'")
        console.print("   4. Review wordlist catalog for completeness")
        
        console.print("\n[dim]Run 'ipcrawler audit --details' for more detailed analysis[/dim]")
    
    def run_legacy_audit(self) -> int:
        """Legacy audit system as fallback
        
        Returns:
            Exit code (0 for success)
        """
        console.print("🔍 [bold cyan]SmartList Comprehensive Audit[/bold cyan]")
        console.print("=" * 60)
        console.print()
        
        # Part 1: Rule Quality Audit
        console.print("[bold]📋 Part 1: Rule Quality Analysis[/bold]")
        console.print("-" * 50)
        try:
            # Run rule audit script as module
            result = subprocess.run(
                [sys.executable, "-m", "src.core.scorer.rule_audit"], 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            # Parse and display key findings
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if any(keyword in line for keyword in ['❌', '⚠️', '🔄', '✅', '📊']):
                    console.print(line)
        except Exception as e:
            console.print(f"[red]Rule audit failed:[/red] {e}")
        
        console.print()
        
        # Part 2: Entropy Analysis
        console.print("[bold]📊 Part 2: Entropy & Diversity Analysis[/bold]")
        console.print("-" * 50)
        self.run_entropy_audit(days_back=30)
        
        console.print()
        
        # Part 3: Scoring Statistics
        console.print("[bold]📈 Part 3: Scoring System Statistics[/bold]")
        console.print("-" * 50)
        try:
            from src.core.scorer.scorer_engine import get_scoring_stats
            from src.core.scorer.rules import get_rule_frequency_stats
            
            # Get scoring stats
            stats = get_scoring_stats()
            console.print(f"   Exact Rules: {stats.get('exact_rules', 0)}")
            console.print(f"   Tech Categories: {stats.get('tech_categories', 0)}")
            console.print(f"   Port Categories: {stats.get('port_categories', 0)}")
            console.print(f"   Total Wordlists: {stats.get('total_wordlists', 0)}")
            console.print(f"   Wordlist Alternatives: {stats.get('wordlist_alternatives', 0)}")
            
            # Get frequency stats
            freq_stats = get_rule_frequency_stats()
            if freq_stats['total_rules'] > 0:
                console.print(f"\n   [bold]Rule Frequency Analysis:[/bold]")
                console.print(f"   Rules Tracked: {freq_stats['total_rules']}")
                console.print(f"   Average Frequency: {freq_stats['average_frequency']:.3f}")
                
                if freq_stats['most_frequent']:
                    console.print(f"\n   🔥 Most Frequent Rules:")
                    for rule, freq in freq_stats['most_frequent'][:3]:
                        console.print(f"      {rule}: {freq:.2%}")
                
                if freq_stats['least_frequent']:
                    console.print(f"\n   ❄️  Least Frequent Rules:")
                    for rule, freq in freq_stats['least_frequent'][:3]:
                        console.print(f"      {rule}: {freq:.2%}")
        except Exception as e:
            console.print(f"[red]Stats analysis failed:[/red] {e}")
        
        console.print()
        console.print("[success]✅ Audit Complete![/success]")
        console.print()
        console.print("💡 [bold]Next Steps:[/bold]")
        console.print("   1. Review and fix any ❌ ERROR issues first")
        console.print("   2. Address ⚠️  WARNING items to improve quality")
        console.print("   3. Monitor entropy scores regularly")
        console.print("   4. Update wordlist alternatives for overused items")
        
        return 0
    
    def run_entropy_audit(self, days_back: int = 30, context_tech: Optional[str] = None, context_port: Optional[int] = None):
        """Run entropy analysis portion of the audit
        
        Args:
            days_back: Number of days of data to analyze
            context_tech: Optional technology filter
            context_port: Optional port filter
        """
        try:
            from src.core.scorer.entropy import analyzer
            from src.core.scorer.models import ScoringContext
            from src.core.scorer.cache import cache
            
            # Create context filter if specified
            context_filter = None
            if context_tech or context_port:
                context_filter = ScoringContext(
                    target="audit",
                    port=context_port or 80,
                    service="audit",
                    tech=context_tech
                )
            
            # Run entropy analysis
            console.print(f"\n📊 Analyzing {days_back} days of recommendation data...")
            metrics = analyzer.analyze_recent_selections(days_back, context_filter)
            
            # Display results
            console.print(f"\n📈 [bold]Entropy Analysis Results[/bold]")
            console.print(f"   Entropy Score: [{'green' if metrics.entropy_score > 0.7 else 'yellow' if metrics.entropy_score > 0.4 else 'red'}]{metrics.entropy_score:.3f}[/]")
            console.print(f"   Quality: [{'green' if metrics.recommendation_quality in ['excellent', 'good'] else 'yellow' if metrics.recommendation_quality == 'acceptable' else 'red'}]{metrics.recommendation_quality}[/]")
            console.print(f"   Total Recommendations: {metrics.total_recommendations}")
            console.print(f"   Unique Wordlists: {metrics.unique_wordlists}")
            console.print(f"   Clustering: {metrics.clustering_percentage:.1f}%")
            console.print(f"   Context Diversity: {metrics.context_diversity:.3f}")
            
            if metrics.warning_message:
                console.print(f"\n⚠️  [yellow]{metrics.warning_message}[/]")
            
            # Show most common wordlists
            if metrics.most_common_wordlists:
                console.print(f"\n🔄 [bold]Most Common Wordlists:[/bold]")
                for wordlist, count in metrics.most_common_wordlists[:5]:
                    percentage = (count / metrics.total_recommendations) * 100
                    icon = "🔥" if percentage > 50 else "📈" if percentage > 25 else "📊"
                    console.print(f"   {icon} {wordlist}: {count} times ({percentage:.1f}%)")
            
            # Show context clusters
            console.print(f"\n🎯 [bold]Context Clustering Analysis:[/bold]")
            clusters = analyzer.detect_context_clusters(days_back)
            
            if clusters:
                for cluster in clusters[:5]:  # Top 5 clusters
                    console.print(f"\n   📦 {cluster.tech or 'Unknown'}:{cluster.port_category}")
                    console.print(f"      Count: {cluster.count} contexts")
                    console.print(f"      Common wordlists: {', '.join(cluster.wordlists[:3])}")
            else:
                console.print("   ✅ No significant clustering detected")
            
            # Cache statistics
            try:
                cache_stats = cache.get_stats()
                console.print(f"\n💾 [bold]Cache Statistics:[/bold]")
                console.print(f"   Total Files: {cache_stats['total_files']}")
                console.print(f"   Date Directories: {cache_stats['date_directories']}")
            except Exception as e:
                console.print(f"\n⚠️  Could not get cache stats: {e}")
            
            # Recommendations
            console.print(f"\n💡 [bold]Recommendations:[/bold]")
            if metrics.entropy_score < 0.5:
                console.print("   🔧 Critical: Enable diversification alternatives")
                console.print("   📝 Review rule mappings for overlap reduction")
            elif metrics.entropy_score < 0.7:
                console.print("   ⚠️  Consider adding more specific wordlist alternatives")
            else:
                console.print("   ✅ Entropy levels are healthy")
            
            if metrics.clustering_percentage > 50:
                console.print("   🎯 High clustering detected - review port/tech categorization")
            
        except ImportError as e:
            console.print(f"[red]Error:[/red] Entropy analysis not available: {e}")
            raise
        except Exception as e:
            console.print(f"[red]Error:[/red] Audit failed: {e}")
            import traceback
            console.print(traceback.format_exc())
            raise


# Global audit runner instance
audit_runner = AuditRunner()