"""
Plugin Debugger for IPCrawler

This module provides comprehensive debugging capabilities for plugin selection and execution,
making it easy to understand why plugins run or don't run for specific targets and services.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ipcrawler.config import config

logger = logging.getLogger(__name__)


@dataclass
class PluginDecision:
    """Records a plugin selection decision"""
    plugin_slug: str
    target_service: str  # Target address or service address:port
    selected: bool
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    plugin_type: str = "unknown"
    execution_time: Optional[float] = None
    error: Optional[str] = None


@dataclass
class DebugSession:
    """Tracks debugging information for a scan session"""
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    decisions: List[PluginDecision] = field(default_factory=list)
    execution_stats: Dict[str, Any] = field(default_factory=dict)
    end_time: Optional[datetime] = None


class PluginDebugger:
    """
    Provides detailed debugging for plugin selection and execution.
    
    This debugger helps answer questions like:
    - Why didn't my Git tools run when I found a Git service?
    - Which conditions caused a plugin to be skipped?
    - What's the execution order and timing of plugins?
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize plugin debugger.
        
        Args:
            session_id: Optional session identifier
        """
        self.session_id = session_id or f"debug_{int(time.time())}"
        self.current_session = DebugSession(self.session_id)
        self.verbose_mode = config.get('debug_yaml_plugins', False)
        
        # Initialize logging if verbose mode is enabled
        if self.verbose_mode:
            self._setup_debug_logging()
    
    def _setup_debug_logging(self):
        """Setup detailed debug logging."""
        debug_logger = logging.getLogger('ipcrawler.plugin_debug')
        debug_logger.setLevel(logging.DEBUG)
        
        # Add console handler for immediate feedback
        if not debug_logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '🔧 [PLUGIN DEBUG] %(asctime)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            debug_logger.addHandler(console_handler)
    
    def log_plugin_selection(self, plugin_slug: str, target_service: str, selected: bool, reason: str, plugin_type: str = "unknown"):
        """
        Log a plugin selection decision.
        
        Args:
            plugin_slug: Plugin identifier
            target_service: Target address or service address:port
            selected: Whether plugin was selected
            reason: Reason for selection/rejection
            plugin_type: Type of plugin (portscan, servicescan, etc.)
        """
        decision = PluginDecision(
            plugin_slug=plugin_slug,
            target_service=target_service,
            selected=selected,
            reason=reason,
            plugin_type=plugin_type
        )
        
        self.current_session.decisions.append(decision)
        
        # Log to console if verbose mode is enabled
        if self.verbose_mode:
            status_icon = "✅" if selected else "❌"
            debug_logger = logging.getLogger('ipcrawler.plugin_debug')
            debug_logger.debug(f"{status_icon} [{plugin_type}] {plugin_slug} → {target_service}: {reason}")
        
        # Also log important decisions at info level
        status_text = "SELECTED" if selected else "SKIPPED"
        logger.info(f"Plugin {plugin_slug} {status_text} for {target_service}: {reason}")
    
    def log_plugin_execution_start(self, plugin_slug: str, target_service: str):
        """
        Log when a plugin starts executing.
        
        Args:
            plugin_slug: Plugin identifier
            target_service: Target address or service address:port
        """
        if self.verbose_mode:
            debug_logger = logging.getLogger('ipcrawler.plugin_debug')
            debug_logger.debug(f"🚀 EXECUTING {plugin_slug} → {target_service}")
    
    def log_plugin_execution_end(self, plugin_slug: str, target_service: str, success: bool, execution_time: float):
        """
        Log when a plugin finishes executing.
        
        Args:
            plugin_slug: Plugin identifier
            target_service: Target address or service address:port
            success: Whether execution was successful
            execution_time: Time taken in seconds
        """
        # Update the most recent decision for this plugin
        for decision in reversed(self.current_session.decisions):
            if decision.plugin_slug == plugin_slug and decision.target_service == target_service:
                decision.execution_time = execution_time
                break
        
        if self.verbose_mode:
            status_icon = "✅" if success else "❌"
            debug_logger = logging.getLogger('ipcrawler.plugin_debug')
            debug_logger.debug(f"{status_icon} COMPLETED {plugin_slug} → {target_service} ({execution_time:.2f}s)")
    
    def log_plugin_error(self, plugin_slug: str, target_service: str, error: str):
        """
        Log a plugin execution error.
        
        Args:
            plugin_slug: Plugin identifier
            target_service: Target address or service address:port
            error: Error message
        """
        # Update the most recent decision for this plugin
        for decision in reversed(self.current_session.decisions):
            if decision.plugin_slug == plugin_slug and decision.target_service == target_service:
                decision.error = error
                break
        
        debug_logger = logging.getLogger('ipcrawler.plugin_debug')
        debug_logger.error(f"❌ ERROR in {plugin_slug} → {target_service}: {error}")
    
    def log_condition_evaluation(self, plugin_slug: str, target_service: str, condition: str, result: bool, details: str = ""):
        """
        Log detailed condition evaluation.
        
        Args:
            plugin_slug: Plugin identifier
            target_service: Target address or service address:port
            condition: Condition being evaluated
            result: Result of condition evaluation
            details: Additional details about the evaluation
        """
        if self.verbose_mode:
            status_icon = "✅" if result else "❌"
            debug_logger = logging.getLogger('ipcrawler.plugin_debug')
            detail_text = f" ({details})" if details else ""
            debug_logger.debug(f"  {status_icon} Condition '{condition}' → {result}{detail_text}")
    
    def get_decisions_for_target(self, target_address: str) -> List[PluginDecision]:
        """
        Get all plugin decisions for a specific target.
        
        Args:
            target_address: Target address
            
        Returns:
            List of plugin decisions for the target
        """
        return [
            decision for decision in self.current_session.decisions
            if decision.target_service.startswith(target_address)
        ]
    
    def get_decisions_for_plugin(self, plugin_slug: str) -> List[PluginDecision]:
        """
        Get all decisions for a specific plugin.
        
        Args:
            plugin_slug: Plugin identifier
            
        Returns:
            List of decisions for the plugin
        """
        return [
            decision for decision in self.current_session.decisions
            if decision.plugin_slug == plugin_slug
        ]
    
    def get_skipped_plugins(self) -> List[PluginDecision]:
        """Get all plugins that were skipped."""
        return [
            decision for decision in self.current_session.decisions
            if not decision.selected
        ]
    
    def get_selected_plugins(self) -> List[PluginDecision]:
        """Get all plugins that were selected."""
        return [
            decision for decision in self.current_session.decisions
            if decision.selected
        ]
    
    def generate_debug_report(self, target_address: Optional[str] = None) -> str:
        """
        Generate a comprehensive debug report.
        
        Args:
            target_address: Optional target to filter by
            
        Returns:
            Formatted debug report
        """
        decisions = self.current_session.decisions
        if target_address:
            decisions = self.get_decisions_for_target(target_address)
        
        if not decisions:
            return "No plugin decisions recorded."
        
        # Group decisions by target/service
        targets = {}
        for decision in decisions:
            target_key = decision.target_service
            if target_key not in targets:
                targets[target_key] = []
            targets[target_key].append(decision)
        
        report_lines = [
            "=" * 70,
            f"PLUGIN DEBUG REPORT - Session: {self.session_id}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 70,
            ""
        ]
        
        # Summary statistics
        total_decisions = len(decisions)
        selected_count = len(self.get_selected_plugins())
        skipped_count = len(self.get_skipped_plugins())
        
        report_lines.extend([
            "📊 SUMMARY:",
            f"  • Total Plugin Evaluations: {total_decisions}",
            f"  • Plugins Selected: {selected_count}",
            f"  • Plugins Skipped: {skipped_count}",
            f"  • Selection Rate: {(selected_count/total_decisions*100):.1f}%",
            ""
        ])
        
        # Detailed breakdown by target
        for target_key, target_decisions in targets.items():
            report_lines.extend([
                f"🎯 TARGET: {target_key}",
                f"   Plugins evaluated: {len(target_decisions)}",
                ""
            ])
            
            # Group by plugin type
            plugin_types = {}
            for decision in target_decisions:
                plugin_type = decision.plugin_type
                if plugin_type not in plugin_types:
                    plugin_types[plugin_type] = []
                plugin_types[plugin_type].append(decision)
            
            for plugin_type, type_decisions in plugin_types.items():
                report_lines.append(f"   📁 {plugin_type.upper()} PLUGINS:")
                
                for decision in type_decisions:
                    status_icon = "✅" if decision.selected else "❌"
                    time_info = f" ({decision.execution_time:.2f}s)" if decision.execution_time else ""
                    error_info = f" [ERROR: {decision.error}]" if decision.error else ""
                    
                    report_lines.append(
                        f"     {status_icon} {decision.plugin_slug}: {decision.reason}{time_info}{error_info}"
                    )
                
                report_lines.append("")
        
        # Common skip reasons analysis
        skip_reasons = {}
        for decision in decisions:
            if not decision.selected:
                reason = decision.reason
                if reason not in skip_reasons:
                    skip_reasons[reason] = 0
                skip_reasons[reason] += 1
        
        if skip_reasons:
            report_lines.extend([
                "🔍 MOST COMMON SKIP REASONS:",
                ""
            ])
            
            # Sort by frequency
            sorted_reasons = sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_reasons[:10]:  # Top 10
                report_lines.append(f"   {count:2d}x {reason}")
            
            report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "💡 DEBUGGING RECOMMENDATIONS:",
            ""
        ])
        
        if skipped_count > selected_count:
            report_lines.append("   • High skip rate detected - review plugin conditions")
        
        if any("doesn't match include patterns" in d.reason for d in decisions if not d.selected):
            report_lines.append("   • Many service pattern mismatches - check service regex patterns")
        
        if any("not in included ports" in d.reason for d in decisions if not d.selected):
            report_lines.append("   • Port restrictions causing skips - review port inclusion rules")
        
        if any("Custom condition" in d.reason for d in decisions if not d.selected):
            report_lines.append("   • Custom conditions failing - review condition logic")
        
        report_lines.extend([
            "",
            "=" * 70
        ])
        
        return "\n".join(report_lines)
    
    def save_debug_report(self, filepath: str, target_address: Optional[str] = None):
        """
        Save debug report to file.
        
        Args:
            filepath: Path to save report
            target_address: Optional target to filter by
        """
        report = self.generate_debug_report(target_address)
        
        try:
            with open(filepath, 'w') as f:
                f.write(report)
            logger.info(f"Debug report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save debug report: {e}")
    
    def clear_session(self):
        """Clear current debugging session."""
        self.current_session = DebugSession(f"debug_{int(time.time())}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for current session."""
        decisions = self.current_session.decisions
        
        return {
            'session_id': self.session_id,
            'total_decisions': len(decisions),
            'selected_plugins': len([d for d in decisions if d.selected]),
            'skipped_plugins': len([d for d in decisions if not d.selected]),
            'errors': len([d for d in decisions if d.error]),
            'average_execution_time': sum(
                d.execution_time for d in decisions 
                if d.execution_time is not None
            ) / max(1, len([d for d in decisions if d.execution_time is not None])),
            'start_time': self.current_session.start_time.isoformat()
        } 