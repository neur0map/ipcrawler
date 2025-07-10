"""
Executive Dashboard Layout - Modern split panel design for Rich TUI.
"""

from typing import Dict, Any, List, Optional
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.rule import Rule
from rich.box import ROUNDED, MINIMAL, DOUBLE
from .layout_base import BaseLayoutRenderer
from .plugin_tracker import PluginState


class ExecutiveDashboardLayout(BaseLayoutRenderer):
    """Executive Dashboard - Modern split panel design with metrics focus."""
    
    def get_layout_name(self) -> str:
        return "Executive Dashboard"
    
    def _setup_layout(self) -> None:
        """Setup executive dashboard layout structure."""
        # Main split: left sidebar (30%) and right content (70%)
        self.layout.split_row(
            Layout(name="sidebar", size=40),
            Layout(name="main_content", ratio=1)
        )
        
        # Left sidebar: metrics and summary
        self.layout["sidebar"].split_column(
            Layout(name="header_info", size=5),
            Layout(name="metrics", size=8),
            Layout(name="status_summary", ratio=1)
        )
        
        # Right content: split between plugin activity and results
        self.layout["main_content"].split_column(
            Layout(name="activity_header", size=3),
            Layout(name="plugin_activity", ratio=2),
            Layout(name="results_header", size=3),
            Layout(name="results_display", ratio=1)
        )
    
    def update_display(self) -> None:
        """Update the executive dashboard display."""
        self.layout["header_info"].update(self._create_header_info())
        self.layout["metrics"].update(self._create_metrics_panel())
        self.layout["status_summary"].update(self._create_status_summary())
        self.layout["activity_header"].update(self._create_activity_header())
        self.layout["plugin_activity"].update(self._create_plugin_activity())
        self.layout["results_header"].update(self._create_results_header())
        self.layout["results_display"].update(self._create_results_display())
    
    def _create_header_info(self) -> Panel:
        """Create header info panel."""
        if not self.scan_active:
            title_text = Text("IPCRAWLER", style=f"bold {self.colors['header_text']}")
            subtitle_text = Text("Security Tool Orchestration", style=self.colors['header_secondary'])
            content = Align.center(f"{title_text}\n{subtitle_text}")
        else:
            target_text = Text(f"TARGET: {self.plugin_tracker.target}", style=f"bold {self.colors['header_text']}")
            elapsed = self.plugin_tracker.get_formatted_elapsed_time()
            time_text = Text(f"ELAPSED: {elapsed}", style=self.colors['header_secondary'])
            content = Align.center(f"{target_text}\n{time_text}")
        
        return Panel(
            content,
            box=ROUNDED,
            style=self.colors["border"],
            padding=(1, 2)
        )
    
    def _create_metrics_panel(self) -> Panel:
        """Create metrics panel with key performance indicators."""
        if not self.scan_active:
            return Panel(
                Align.center(Text("Ready for Scan", style=self.colors["info_text"])),
                title="METRICS",
                box=MINIMAL,
                style=self.colors["border"]
            )
        
        stats = self.get_progress_stats()
        
        # Create metrics table
        metrics_table = Table(show_header=False, box=None, padding=(0, 1))
        metrics_table.add_column("Metric", style=f"bold {self.colors['info_text']}", width=12)
        metrics_table.add_column("Value", style=f"bold {self.colors['progress_text']}", width=8)
        metrics_table.add_column("Bar", width=15)
        
        # Progress bar visualization
        progress_bar = self._create_mini_progress_bar(stats["percentage"])
        metrics_table.add_row("PROGRESS", f"{stats['percentage']:.1f}%", progress_bar)
        
        # Success rate
        success_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        success_bar = self._create_mini_progress_bar(success_rate, color=self.colors["success_text"])
        metrics_table.add_row("SUCCESS", f"{success_rate:.1f}%", success_bar)
        
        # Active count
        active_indicator = "●" * min(stats["active"], 10) + "○" * (10 - min(stats["active"], 10))
        metrics_table.add_row("ACTIVE", str(stats["active"]), Text(active_indicator, style=self.colors["active_text"]))
        
        # Throughput (completed per minute)
        elapsed_min = max(1, self.plugin_tracker.elapsed_time.total_seconds() / 60)
        throughput = stats["completed"] / elapsed_min
        metrics_table.add_row("RATE", f"{throughput:.1f}/min", "")
        
        return Panel(
            metrics_table,
            title="[bold]METRICS[/bold]",
            box=MINIMAL,
            style=self.colors["border"]
        )
    
    def _create_status_summary(self) -> Panel:
        """Create status summary panel."""
        if not self.scan_active:
            return Panel(
                Align.center(Text("No Active Scan", style=self.colors["info_text"])),
                title="STATUS",
                box=MINIMAL,
                style=self.colors["border"]
            )
        
        stats = self.get_progress_stats()
        
        # Create status breakdown
        status_table = Table(show_header=False, box=None, padding=(0, 1))
        status_table.add_column("Status", style=f"bold {self.colors['info_text']}", width=10)
        status_table.add_column("Count", style=f"bold {self.colors['progress_text']}", width=6)
        status_table.add_column("Indicator", width=12)
        
        # Status indicators
        total_width = 20
        completed_width = int((stats["completed"] / stats["total"]) * total_width) if stats["total"] > 0 else 0
        failed_width = int((stats["failed"] / stats["total"]) * total_width) if stats["total"] > 0 else 0
        active_width = int((stats["active"] / stats["total"]) * total_width) if stats["total"] > 0 else 0
        queued_width = total_width - completed_width - failed_width - active_width
        
        status_table.add_row(
            "COMPLETE", 
            str(stats["completed"]), 
            Text("█" * completed_width, style=self.colors["success_text"])
        )
        status_table.add_row(
            "FAILED", 
            str(stats["failed"]), 
            Text("█" * failed_width, style=self.colors["error_text"])
        )
        status_table.add_row(
            "ACTIVE", 
            str(stats["active"]), 
            Text("█" * active_width, style=self.colors["active_text"])
        )
        status_table.add_row(
            "QUEUED", 
            str(stats["queued"]), 
            Text("█" * queued_width, style=self.colors["queued_text"])
        )
        
        return Panel(
            status_table,
            title="[bold]STATUS[/bold]",
            box=MINIMAL,
            style=self.colors["border"]
        )
    
    def _create_activity_header(self) -> Panel:
        """Create activity section header."""
        if not self.scan_active:
            return Panel(
                Align.center(Text("Plugin Activity", style=self.colors["header_text"])),
                style=self.colors["border"]
            )
        
        stats = self.get_progress_stats()
        activity_text = Text("PLUGIN ACTIVITY", style=f"bold {self.colors['header_text']}")
        stats_text = Text(f"({stats['active']} active • {stats['completed']} complete)", 
                         style=self.colors['header_secondary'])
        
        return Panel(
            Columns([activity_text, stats_text], equal=False, expand=True),
            style=self.colors["border"]
        )
    
    def _create_plugin_activity(self) -> Panel:
        """Create plugin activity panel."""
        if not self.scan_active:
            return Panel(
                Align.center(Text("No Active Plugins", style=self.colors["info_text"])),
                box=MINIMAL,
                style=self.colors["border"]
            )
        
        # Create activity table
        activity_table = Table(show_header=True, header_style=f"bold {self.colors['header_text']}", box=None)
        activity_table.add_column("STATUS", style=self.colors["info_text"], width=10)
        activity_table.add_column("TOOL", style=self.colors["accent"], width=12)
        activity_table.add_column("PLUGIN", style=self.colors["progress_text"], no_wrap=True)
        activity_table.add_column("DURATION", style=self.colors["info_text"], width=10)
        
        # Add active plugins
        active_plugins = self.plugin_tracker.get_active_plugins()
        for plugin in active_plugins[:8]:  # Show top 8 active
            duration = ""
            if plugin.start_time:
                elapsed = (self.plugin_tracker.scan_start_time or plugin.start_time) - plugin.start_time
                duration = f"{int(elapsed.total_seconds())}s"
            
            activity_table.add_row(
                "🔄 RUNNING",
                plugin.tool.upper(),
                plugin.name,
                duration,
                style=self.colors["active_text"]
            )
        
        # Add recently completed
        completed_plugins = self.plugin_tracker.get_completed_plugins()[-5:]
        for plugin in completed_plugins:
            duration = ""
            if plugin.duration:
                duration = f"{plugin.duration.total_seconds():.1f}s"
            
            activity_table.add_row(
                "✅ COMPLETE",
                plugin.tool.upper(),
                plugin.name,
                duration,
                style=self.colors["success_text"]
            )
        
        # Add failed plugins
        failed_plugins = self.plugin_tracker.get_failed_plugins()[-3:]
        for plugin in failed_plugins:
            error_msg = plugin.error_message or "error"
            activity_table.add_row(
                "❌ FAILED",
                plugin.tool.upper(),
                f"{plugin.name} ({error_msg})",
                "",
                style=self.colors["error_text"]
            )
        
        return Panel(
            activity_table,
            box=MINIMAL,
            style=self.colors["border"]
        )
    
    def _create_results_header(self) -> Panel:
        """Create results section header."""
        return Panel(
            Align.center(Text("SCAN RESULTS", style=f"bold {self.colors['header_text']}")),
            style=self.colors["border"]
        )
    
    def _create_results_display(self) -> Panel:
        """Create results display panel."""
        if not self.scan_active:
            return Panel(
                Align.center(Text("Results will appear here during scan", style=self.colors["info_text"])),
                box=MINIMAL,
                style=self.colors["border"]
            )
        
        # Show summary of results
        stats = self.get_progress_stats()
        
        results_text = Text()
        results_text.append(f"Scan Progress: {stats['completed'] + stats['failed']}/{stats['total']} templates\n\n", 
                          style=self.colors["progress_text"])
        
        if stats["completed"] > 0:
            results_text.append(f"✅ {stats['completed']} successful scans\n", style=self.colors["success_text"])
        
        if stats["failed"] > 0:
            results_text.append(f"❌ {stats['failed']} failed scans\n", style=self.colors["error_text"])
        
        if stats["active"] > 0:
            results_text.append(f"🔄 {stats['active']} scans in progress\n", style=self.colors["active_text"])
        
        if stats["queued"] > 0:
            results_text.append(f"⏳ {stats['queued']} scans queued\n", style=self.colors["queued_text"])
        
        return Panel(
            results_text,
            box=MINIMAL,
            style=self.colors["border"]
        )
    
    def _create_mini_progress_bar(self, percentage: float, color: Optional[str] = None) -> Text:
        """Create a mini progress bar."""
        if color is None:
            color = self.colors["progress_text"]
        
        width = 12
        filled = int((percentage / 100) * width)
        bar = "█" * filled + "░" * (width - filled)
        return Text(bar, style=color)