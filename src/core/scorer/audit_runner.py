"""Audit runner for SmartList system analysis"""

import subprocess
import sys
from pathlib import Path
from typing import Optional
from src.core.ui.console.base import console


class AuditRunner:
    """Manages execution of SmartList audit processes"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
    
    def run_comprehensive_audit(self, show_details: bool = False) -> int:
        """Run comprehensive SmartList audit using the original 3-part format
        
        Args:
            show_details: Whether to show detailed conflict analysis
            
        Returns:
            Exit code (0 for success, non-zero for issues)
        """
        # Use the legacy audit format which is the established UI
        return self.run_legacy_audit()
    
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