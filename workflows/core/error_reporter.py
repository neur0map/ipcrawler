"""
Error reporting and analysis features for IPCrawler workspaces.

This module provides comprehensive error reporting capabilities including
workspace error summaries, trend analysis, and actionable error reports.
"""

import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict

from .error_collector import get_error_collector, ErrorStats
from .exceptions import ErrorSeverity, ErrorCategory


class ErrorReporter:
    """
    Advanced error reporting and analysis system.
    
    Provides detailed error analysis, trends, and actionable insights
    for IPCrawler workspace error management.
    """
    
    def __init__(self, workspace_dir: str = "workspaces"):
        self.workspace_dir = Path(workspace_dir)
        self.collector = get_error_collector()
    
    def generate_workspace_summary(self) -> Dict[str, Any]:
        """Generate comprehensive workspace error summary"""
        stats = self.collector.get_stats()
        
        # Calculate error trends
        recent_24h = stats.recent_errors(24)
        recent_7d = stats.recent_errors(24 * 7)
        
        summary = {
            "generated_at": datetime.datetime.now().isoformat(),
            "summary": {
                "total_unique_errors": stats.total_errors,
                "total_occurrences": stats.total_occurrences,
                "critical_errors": len(stats.critical_errors()),
                "recent_24h": len(recent_24h),
                "recent_7d": len(recent_7d)
            },
            "severity_breakdown": self._analyze_severity_trends(stats),
            "category_analysis": self._analyze_category_trends(stats),
            "workflow_impact": self._analyze_workflow_impact(stats),
            "most_frequent_errors": stats.most_frequent_errors(10),
            "error_patterns": self._identify_error_patterns(stats),
            "recommendations": self._generate_recommendations(stats)
        }
        
        return summary
    
    def _analyze_severity_trends(self, stats: ErrorStats) -> Dict[str, Any]:
        """Analyze error severity trends"""
        by_severity = stats.by_severity()
        total = sum(by_severity.values()) or 1
        
        return {
            "distribution": by_severity,
            "percentages": {
                severity: round((count / total) * 100, 1)
                for severity, count in by_severity.items()
            },
            "critical_rate": by_severity.get(ErrorSeverity.CRITICAL.value, 0),
            "error_rate": by_severity.get(ErrorSeverity.ERROR.value, 0),
            "warning_rate": by_severity.get(ErrorSeverity.WARNING.value, 0)
        }
    
    def _analyze_category_trends(self, stats: ErrorStats) -> Dict[str, Any]:
        """Analyze error category trends"""
        by_category = stats.by_category()
        total = sum(by_category.values()) or 1
        
        # Identify top problem categories
        sorted_categories = sorted(
            by_category.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "distribution": by_category,
            "percentages": {
                category: round((count / total) * 100, 1)
                for category, count in by_category.items()
            },
            "top_problems": sorted_categories[:5],
            "focus_areas": [
                cat for cat, count in sorted_categories[:3] 
                if count > total * 0.1  # Categories with >10% of errors
            ]
        }
    
    def _analyze_workflow_impact(self, stats: ErrorStats) -> Dict[str, Any]:
        """Analyze error impact by workflow"""
        by_workflow = stats.by_workflow()
        total = sum(by_workflow.values()) or 1
        
        # Calculate error rates per workflow
        workflow_analysis = {}
        for workflow, error_count in by_workflow.items():
            workflow_errors = [
                e for e in stats.errors 
                if e.error.context.workflow_name == workflow
            ]
            
            # Analyze severity distribution for this workflow
            severity_dist = defaultdict(int)
            for error_entry in workflow_errors:
                severity_dist[error_entry.error.severity.value] += error_entry.occurrence_count
            
            workflow_analysis[workflow] = {
                "total_errors": error_count,
                "error_rate": round((error_count / total) * 100, 1),
                "severity_distribution": dict(severity_dist),
                "most_common_error": self._get_most_common_error_for_workflow(workflow_errors),
                "reliability_score": self._calculate_reliability_score(workflow_errors)
            }
        
        return {
            "by_workflow": workflow_analysis,
            "most_problematic": max(by_workflow.items(), key=lambda x: x[1]) if by_workflow else None,
            "most_reliable": min(by_workflow.items(), key=lambda x: x[1]) if by_workflow else None
        }
    
    def _get_most_common_error_for_workflow(self, workflow_errors: List) -> Optional[Dict[str, Any]]:
        """Get the most common error for a specific workflow"""
        if not workflow_errors:
            return None
        
        # Find error with highest occurrence count
        most_common = max(workflow_errors, key=lambda e: e.occurrence_count)
        
        return {
            "error_code": most_common.error.error_code,
            "message": most_common.error.message,
            "occurrences": most_common.occurrence_count,
            "category": most_common.error.category.value
        }
    
    def _calculate_reliability_score(self, workflow_errors: List) -> float:
        """Calculate a reliability score for a workflow (0-100)"""
        if not workflow_errors:
            return 100.0
        
        # Base score starts at 100
        score = 100.0
        
        # Reduce score based on error severity and frequency
        for error_entry in workflow_errors:
            severity_penalty = {
                ErrorSeverity.CRITICAL.value: 20,
                ErrorSeverity.ERROR.value: 10,
                ErrorSeverity.WARNING.value: 2,
                ErrorSeverity.INFO.value: 0.5
            }.get(error_entry.error.severity.value, 5)
            
            # Apply penalty based on occurrences (logarithmic to avoid extreme penalties)
            import math
            occurrence_multiplier = math.log(error_entry.occurrence_count + 1)
            score -= severity_penalty * occurrence_multiplier
        
        return max(0.0, min(100.0, score))
    
    def _identify_error_patterns(self, stats: ErrorStats) -> Dict[str, Any]:
        """Identify common error patterns and trends"""
        patterns = {
            "recurring_errors": [],
            "error_clusters": [],
            "time_patterns": {},
            "correlation_analysis": {}
        }
        
        # Find recurring errors (high occurrence count)
        for error_entry in stats.errors:
            if error_entry.occurrence_count >= 5:
                patterns["recurring_errors"].append({
                    "error_code": error_entry.error.error_code,
                    "message": error_entry.error.message,
                    "occurrences": error_entry.occurrence_count,
                    "workflow": error_entry.error.context.workflow_name,
                    "first_seen": error_entry.first_seen.isoformat(),
                    "last_seen": error_entry.last_seen.isoformat()
                })
        
        # Identify error clusters (same category + workflow combinations)
        clusters = defaultdict(list)
        for error_entry in stats.errors:
            cluster_key = f"{error_entry.error.category.value}_{error_entry.error.context.workflow_name}"
            clusters[cluster_key].append(error_entry)
        
        for cluster_key, cluster_errors in clusters.items():
            if len(cluster_errors) >= 3:  # At least 3 different errors in same category/workflow
                category, workflow = cluster_key.split('_', 1)
                patterns["error_clusters"].append({
                    "category": category,
                    "workflow": workflow,
                    "error_count": len(cluster_errors),
                    "total_occurrences": sum(e.occurrence_count for e in cluster_errors)
                })
        
        return patterns
    
    def _generate_recommendations(self, stats: ErrorStats) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on error analysis"""
        recommendations = []
        
        # High-level recommendations based on error patterns
        by_category = stats.by_category()
        by_severity = stats.by_severity()
        
        # Critical error recommendations
        if by_severity.get(ErrorSeverity.CRITICAL.value, 0) > 0:
            recommendations.append({
                "priority": "critical",
                "title": "Address Critical Errors Immediately",
                "description": f"You have {by_severity[ErrorSeverity.CRITICAL.value]} critical errors that need immediate attention.",
                "actions": [
                    "Review all critical errors in the error log",
                    "Fix root causes before continuing workflows",
                    "Consider implementing error recovery mechanisms"
                ]
            })
        
        # Network error recommendations
        network_errors = by_category.get(ErrorCategory.NETWORK.value, 0)
        if network_errors > stats.total_occurrences * 0.3:  # >30% network errors
            recommendations.append({
                "priority": "high",
                "title": "Network Connectivity Issues",
                "description": f"Network errors account for {network_errors} occurrences. This suggests connectivity problems.",
                "actions": [
                    "Check network connectivity to target hosts",
                    "Verify DNS resolution is working",
                    "Consider implementing retry mechanisms for network operations",
                    "Check firewall and security settings"
                ]
            })
        
        # Tool execution recommendations
        tool_errors = by_category.get(ErrorCategory.TOOL.value, 0)
        if tool_errors > 0:
            recommendations.append({
                "priority": "medium",
                "title": "Tool Execution Problems",
                "description": f"External tool execution failed {tool_errors} times.",
                "actions": [
                    "Verify all required tools are installed and accessible",
                    "Check tool permissions and PATH configuration",
                    "Validate tool versions and compatibility",
                    "Consider implementing tool availability checks"
                ]
            })
        
        # Parsing error recommendations  
        parsing_errors = by_category.get(ErrorCategory.PARSING.value, 0)
        if parsing_errors > 0:
            recommendations.append({
                "priority": "medium",
                "title": "Data Parsing Issues",
                "description": f"Data parsing failed {parsing_errors} times, indicating output format issues.",
                "actions": [
                    "Review tool output formats for changes",
                    "Update parsing logic to handle edge cases",
                    "Implement more robust error handling in parsers",
                    "Add output validation before parsing"
                ]
            })
        
        # Workflow reliability recommendations
        workflow_analysis = self._analyze_workflow_impact(stats)
        for workflow, analysis in workflow_analysis["by_workflow"].items():
            if analysis["reliability_score"] < 70:  # Low reliability
                recommendations.append({
                    "priority": "medium",
                    "title": f"Improve {workflow} Workflow Reliability",
                    "description": f"The {workflow} workflow has a reliability score of {analysis['reliability_score']:.1f}%.",
                    "actions": [
                        f"Review and fix common errors in {workflow} workflow",
                        "Add input validation and error recovery",
                        "Implement progressive retry mechanisms",
                        "Consider workflow redesign for better error handling"
                    ]
                })
        
        return recommendations
    
    def save_workspace_report(self, output_file: Optional[Path] = None) -> Path:
        """Save comprehensive workspace error report"""
        if output_file is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.workspace_dir / f"error_report_{timestamp}.json"
        
        summary = self.generate_workspace_summary()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
            
            return output_file
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not save error report to {output_file}: {e}")
            return None
    
    def generate_human_readable_report(self) -> str:
        """Generate human-readable error report"""
        summary = self.generate_workspace_summary()
        
        lines = []
        lines.append("# IPCrawler Workspace Error Analysis Report")
        lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        s = summary["summary"]
        lines.append(f"- **Total Errors**: {s['total_unique_errors']} unique errors, {s['total_occurrences']} total occurrences")
        lines.append(f"- **Critical Issues**: {s['critical_errors']} critical errors requiring immediate attention")
        lines.append(f"- **Recent Activity**: {s['recent_24h']} errors in last 24 hours, {s['recent_7d']} in last 7 days")
        lines.append("")
        
        # Severity Analysis
        lines.append("## Error Severity Analysis")
        severity = summary["severity_breakdown"]
        for sev, count in severity["distribution"].items():
            percentage = severity["percentages"].get(sev, 0)
            lines.append(f"- **{sev.upper()}**: {count} errors ({percentage}%)")
        lines.append("")
        
        # Category Analysis
        lines.append("## Error Category Breakdown")
        category = summary["category_analysis"]
        lines.append("**Top Problem Areas:**")
        for cat, count in category["top_problems"][:5]:
            percentage = category["percentages"].get(cat, 0)
            lines.append(f"- {cat}: {count} errors ({percentage}%)")
        lines.append("")
        
        # Workflow Impact
        lines.append("## Workflow Reliability Analysis")
        workflow = summary["workflow_impact"]
        for wf_name, wf_data in workflow["by_workflow"].items():
            reliability = wf_data["reliability_score"]
            status = "🟢 Excellent" if reliability >= 90 else "🟡 Good" if reliability >= 70 else "🔴 Needs Attention"
            lines.append(f"- **{wf_name}**: {reliability:.1f}% reliability {status}")
        lines.append("")
        
        # Most Frequent Errors
        lines.append("## Most Frequent Errors")
        for i, error in enumerate(summary["most_frequent_errors"][:5], 1):
            lines.append(f"{i}. **[{error['error_code']}]** {error['message']}")
            lines.append(f"   - Workflow: {error['workflow']}")
            lines.append(f"   - Occurrences: {error['occurrences']}")
            lines.append(f"   - Severity: {error['severity']}")
            lines.append("")
        
        # Recommendations
        lines.append("## Recommendations")
        for i, rec in enumerate(summary["recommendations"], 1):
            priority_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "📋",
                "low": "💡"
            }.get(rec["priority"], "📋")
            
            lines.append(f"### {priority_emoji} {rec['title']} ({rec['priority'].upper()} Priority)")
            lines.append(rec["description"])
            lines.append("")
            lines.append("**Action Items:**")
            for action in rec["actions"]:
                lines.append(f"- {action}")
            lines.append("")
        
        return "\n".join(lines)
    
    def save_human_readable_report(self, output_file: Optional[Path] = None) -> Path:
        """Save human-readable error report"""
        if output_file is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.workspace_dir / f"error_analysis_{timestamp}.md"
        
        report_content = self.generate_human_readable_report()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return output_file
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not save readable report to {output_file}: {e}")
            return None


def generate_workspace_error_summary() -> Dict[str, Any]:
    """Convenience function to generate workspace error summary"""
    reporter = ErrorReporter()
    return reporter.generate_workspace_summary()


def save_error_analysis_report(output_dir: Optional[str] = None) -> Dict[str, Path]:
    """
    Save both JSON and human-readable error analysis reports.
    
    Returns:
        Dict with 'json' and 'markdown' keys containing file paths
    """
    reporter = ErrorReporter(output_dir or "workspaces")
    
    results = {}
    
    # Save JSON report
    json_file = reporter.save_workspace_report()
    if json_file:
        results['json'] = json_file
    
    # Save human-readable report
    md_file = reporter.save_human_readable_report()
    if md_file:
        results['markdown'] = md_file
    
    return results