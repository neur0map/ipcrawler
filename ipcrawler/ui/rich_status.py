"""
Rich TUI status display for ipcrawler.
"""

import sys
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.text import Text
from rich.columns import Columns
from rich.align import Align

from ..models.result import ExecutionResult, ScanResult
from .plugin_tracker import PluginTracker, PluginState


class RichStatusDispatcher:
    """Rich TUI status display with live updates."""
    
    def __init__(self, config: Dict[str, Any], silent: bool = False):
        self.config = config
        self.silent = silent
        self.console = Console()
        self.plugin_tracker = PluginTracker()
        
        # TUI settings
        self.enable_rich_ui = config.get("enable_rich_ui", True)
        self.fullscreen_mode = config.get("fullscreen_mode", False)
        self.refresh_rate = config.get("refresh_rate", 10)
        self.theme = config.get("theme", "minimal")
        
        # Theme configurations
        self.themes = {
            "minimal": {
                "border": "white",
                "header_text": "bright_white",
                "header_secondary": "dim white",
                "progress_text": "bright_white",
                "active_text": "bright_white",
                "success_text": "green",
                "error_text": "red",
                "queued_text": "dim white",
                "info_text": "dim white"
            },
            "dark": {
                "border": "bright_black",
                "header_text": "white",
                "header_secondary": "bright_black",
                "progress_text": "white",
                "active_text": "cyan",
                "success_text": "bright_green",
                "error_text": "bright_red",
                "queued_text": "bright_black",
                "info_text": "bright_black"
            },
            "matrix": {
                "border": "green",
                "header_text": "bright_green",
                "header_secondary": "green",
                "progress_text": "bright_green",
                "active_text": "bright_green",
                "success_text": "bright_green",
                "error_text": "bright_red",
                "queued_text": "green",
                "info_text": "green"
            },
            "cyber": {
                "border": "bright_cyan",
                "header_text": "bright_cyan",
                "header_secondary": "cyan",
                "progress_text": "bright_cyan",
                "active_text": "bright_magenta",
                "success_text": "bright_green",
                "error_text": "bright_red",
                "queued_text": "cyan",
                "info_text": "cyan"
            },
            "hacker": {
                "border": "bright_green",
                "header_text": "bright_green",
                "header_secondary": "green",
                "progress_text": "bright_green",
                "active_text": "bright_yellow",
                "success_text": "bright_green",
                "error_text": "bright_red",
                "queued_text": "green",
                "info_text": "green"
            },
            "corporate": {
                "border": "blue",
                "header_text": "bright_blue",
                "header_secondary": "blue",
                "progress_text": "bright_blue",
                "active_text": "bright_white",
                "success_text": "bright_green",
                "error_text": "bright_red",
                "queued_text": "blue",
                "info_text": "blue"
            }
        }
        
        # Get current theme colors
        self.colors = self.themes.get(self.theme, self.themes["minimal"])
        
        # Layout components
        self.layout = Layout()
        self.live = None
        self.progress = None
        
        # Scan state
        self.scan_active = False
        self.start_time = None
        self.total_templates = 0
        self.completed_templates = 0
        
        # Timer task for live updates
        self._timer_task = None
        self._update_stop_event = None
        
        # Setup layout
        self._setup_layout()
    
    def _setup_layout(self) -> None:
        """Setup the Rich layout structure."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        # Split main area for progress and details
        self.layout["main"].split_column(
            Layout(name="progress", size=6),
            Layout(name="plugins", ratio=1)
        )
    
    def _create_header(self) -> Panel:
        """Create header panel with target info."""
        if not self.scan_active:
            return Panel("ipcrawler - Security Tool Orchestration Framework", style=self.colors["border"])
        
        target_text = Text(f"Target: {self.plugin_tracker.target}", style=self.colors["header_text"])
        elapsed_str = self.plugin_tracker.get_formatted_elapsed_time()
        
        status_text = Text(f"Scanning... | Elapsed: {elapsed_str}", style=self.colors["header_secondary"])
        
        header_content = Columns([target_text, status_text], equal=False, expand=True)
        return Panel(header_content, style=self.colors["border"])
    
    def _create_progress_panel(self) -> Panel:
        """Create progress panel with statistics."""
        if not self.scan_active:
            return Panel("Ready to scan", style=self.colors["border"])
        
        stats = self.plugin_tracker.stats
        progress_pct = self.plugin_tracker.progress_percentage
        
        # Progress bar
        progress_bar = f"[{'▓' * int(progress_pct // 10)}{'░' * (10 - int(progress_pct // 10))}]"
        progress_text = f"{progress_bar} {progress_pct:.1f}% ({stats['completed'] + stats['failed']}/{stats['total']})"
        
        # Statistics
        stats_text = Text()
        stats_text.append(f"Active: {stats['active']}", style=self.colors["active_text"])
        stats_text.append(" | ", style=self.colors["info_text"])
        stats_text.append(f"Queued: {stats['queued']}", style=self.colors["queued_text"])
        stats_text.append(" | ", style=self.colors["info_text"])
        stats_text.append(f"Complete: {stats['completed']}", style=self.colors["success_text"])
        stats_text.append(" | ", style=self.colors["info_text"])
        stats_text.append(f"Failed: {stats['failed']}", style=self.colors["error_text"])
        
        content = Text()
        content.append(f"Progress: {progress_text}\n", style=self.colors["progress_text"])
        content.append(stats_text)
        
        return Panel(content, title="Scan Progress", style=self.colors["border"])
    
    def _create_plugins_panel(self) -> Panel:
        """Create plugins panel with current status."""
        if not self.scan_active:
            return Panel("No active scan", style=self.colors["border"])
        
        # Create table for plugin status
        table = Table(show_header=True, header_style=self.colors["header_text"], box=None, padding=(0, 1))
        table.add_column("Status", style=self.colors["info_text"], width=8)
        table.add_column("Tool", style=self.colors["header_text"], width=12)
        table.add_column("Plugin", style=self.colors["header_text"], no_wrap=True)
        
        # Add active plugins
        active_plugins = self.plugin_tracker.get_active_plugins()
        for plugin in active_plugins:
            table.add_row(
                "running",
                plugin.tool,
                plugin.name,
                style=self.colors["active_text"]
            )
        
        # Add recently completed plugins (last 5)
        completed_plugins = self.plugin_tracker.get_completed_plugins()[-5:]
        for plugin in completed_plugins:
            table.add_row(
                "complete",
                plugin.tool,
                plugin.name,
                style=self.colors["success_text"]
            )
        
        # Add failed plugins
        failed_plugins = self.plugin_tracker.get_failed_plugins()
        for plugin in failed_plugins:
            error_msg = plugin.error_message or "unknown error"
            table.add_row(
                "failed",
                plugin.tool,
                f"{plugin.name} ({error_msg})",
                style=self.colors["error_text"]
            )
        
        # Add queued plugins (first 10)
        queued_plugins = self.plugin_tracker.get_queued_plugins()[:10]
        for plugin in queued_plugins:
            table.add_row(
                "queued",
                plugin.tool,
                plugin.name,
                style=self.colors["queued_text"]
            )
        
        # Show truncation message if there are more queued plugins
        remaining_queued = len(self.plugin_tracker.get_queued_plugins()) - 10
        if remaining_queued > 0:
            table.add_row(
                "...",
                "...",
                f"and {remaining_queued} more queued",
                style=self.colors["queued_text"]
            )
        
        return Panel(table, title="Plugin Status", style=self.colors["border"])
    
    def _create_footer(self) -> Panel:
        """Create footer panel with summary info."""
        if not self.scan_active:
            return Panel("Ready - Use 'python ipcrawler.py -h' for help", style=self.colors["border"])
        
        footer_text = Text(f"Press Ctrl+C to cancel scan", style=self.colors["info_text"])
        return Panel(footer_text, style=self.colors["border"])
    
    def _update_display(self) -> None:
        """Update the display with current state."""
        if not self.enable_rich_ui or self.silent:
            return
        
        self.layout["header"].update(self._create_header())
        self.layout["progress"].update(self._create_progress_panel())
        self.layout["plugins"].update(self._create_plugins_panel())
        self.layout["footer"].update(self._create_footer())
    
    async def _timer_update_loop(self) -> None:
        """Background task to update the display every second."""
        while not self._update_stop_event.is_set():
            try:
                if self.scan_active:
                    self._update_display()
                await asyncio.sleep(1.0)  # Update every second
            except asyncio.CancelledError:
                break
            except Exception:
                # Ignore errors in timer loop to prevent crashes
                pass
    
    @contextmanager
    def live_context(self):
        """Context manager for Live display with timer task."""
        if not self.enable_rich_ui or self.silent:
            yield
            return
        
        try:
            with Live(
                self.layout,
                console=self.console,
                screen=self.fullscreen_mode,
                refresh_per_second=self.refresh_rate
            ) as live:
                self.live = live
                self._update_display()
                yield
        finally:
            self.live = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.enable_rich_ui or self.silent:
            return self
        
        self._update_stop_event = asyncio.Event()
        
        self.live = Live(
            self.layout,
            console=self.console,
            screen=self.fullscreen_mode,
            refresh_per_second=self.refresh_rate
        )
        
        self.live.__enter__()
        self._update_display()
        
        # Start timer task
        self._timer_task = asyncio.create_task(self._timer_update_loop())
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Stop timer task
        if self._update_stop_event:
            self._update_stop_event.set()
        if self._timer_task:
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass
        
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)
            self.live = None
    
    def start_scan(self, target: str, template_count: int, folder: Optional[str] = None) -> None:
        """Start a new scan session."""
        self.start_time = datetime.now()
        self.total_templates = template_count
        self.completed_templates = 0
        self.scan_active = True
        
        # Initialize plugin tracker (we'll update it when templates are available)
        self.plugin_tracker.target = target
        self.plugin_tracker.total_plugins = template_count
        self.plugin_tracker.scan_start_time = self.start_time
        
        if not self.enable_rich_ui or self.silent:
            if folder:
                print(f"Running template flag '{folder}' (folder: {folder}) on target: {target}")
            print(f"Running {template_count} scans concurrently on target: {target}")
        
        self._update_display()
    
    def initialize_plugins(self, templates: List[Any]) -> None:
        """Initialize plugin tracker with template information."""
        template_names = [template.name for template in templates]
        tools = [template.tool for template in templates]
        
        self.plugin_tracker.initialize_scan(
            self.plugin_tracker.target,
            template_names,
            tools
        )
        self._update_display()
    
    def template_starting(self, tool: str, template_name: str, target: str) -> None:
        """Display template starting message."""
        self.plugin_tracker.start_plugin(template_name)
        
        if not self.enable_rich_ui or self.silent:
            print(f"[→] {tool} ({template_name}) on {target}...")
        
        self._update_display()
    
    def template_completed(self, result: ExecutionResult) -> None:
        """Display template completion message."""
        error_msg = None
        if not result.success and result.return_code is not None:
            error_msg = f"exit code {result.return_code}"
        
        self.plugin_tracker.complete_plugin(
            result.template_name,
            success=result.success,
            error=error_msg
        )
        
        if not self.enable_rich_ui or self.silent:
            status = "✓" if result.success else "✗"
            if result.success:
                print(f"[{status}] {result.tool} ({result.template_name}) completed successfully")
            else:
                print(f"[{status}] {result.tool} ({result.template_name}) failed (exit code {result.return_code})")
        
        self._update_display()
    
    def update_progress(self, result: ExecutionResult) -> None:
        """Update progress with a completed result."""
        self.completed_templates += 1
        self.template_completed(result)
    
    def finish_scan(self, scan_result: ScanResult) -> None:
        """Finish scan and display summary."""
        self.scan_active = False
        
        if not self.enable_rich_ui or self.silent:
            print()
            print("--- Scan Summary ---")
            print(f"Total scans: {scan_result.total_templates}")
            print(f"Successful: {scan_result.successful_templates}")
            print(f"Failed: {scan_result.failed_templates}")
        else:
            # Display final summary in Rich format
            summary = self.plugin_tracker.get_summary()
            
            summary_table = Table(show_header=False, box=None, padding=(0, 1))
            summary_table.add_column("Metric", style=self.colors["header_text"])
            summary_table.add_column("Value", style=self.colors["progress_text"])
            
            summary_table.add_row("Total scans:", str(summary["total_plugins"]))
            summary_table.add_row("Successful:", str(summary["completed"]), style=self.colors["success_text"])
            summary_table.add_row("Failed:", str(summary["failed"]), style=self.colors["error_text"])
            summary_table.add_row("Success rate:", f"{summary['success_rate']:.1f}%")
            
            elapsed = summary["elapsed_time"]
            elapsed_str = f"{elapsed.seconds//60:02d}:{elapsed.seconds%60:02d}"
            summary_table.add_row("Elapsed time:", elapsed_str)
            
            self.console.print()
            self.console.print(Panel(summary_table, title="Scan Summary", style=self.colors["border"]))
    
    # Maintain compatibility with existing StatusDispatcher interface
    def display_results(self, results: list) -> None:
        """Display scan results."""
        if not self.silent:
            print(f"\\nFound {len(results)} results:")
            for result in results:
                status = "✓" if result.success else "✗"
                print(f"  {status} {result.template_name} - {result.tool}")
    
    def display_templates(self, templates: list) -> None:
        """Display available templates."""
        if not self.silent:
            print(f"\\nAvailable templates ({len(templates)}):")
            for template in templates:
                print(f"  - {template.name}: {template.description or 'No description'}")
    
    def display_config(self, config: Dict[str, Any]) -> None:
        """Display configuration."""
        if not self.silent:
            print("\\nConfiguration:")
            self._print_dict(config, indent=2)
    
    def display_schema(self, schema: str) -> None:
        """Display JSON schema."""
        if not self.silent:
            print("\\nTemplate JSON Schema:")
            print(schema)
    
    def display_error(self, message: str) -> None:
        """Display error message."""
        if self.enable_rich_ui and not self.silent:
            self.console.print(f"[red]Error:[/red] {message}")
        else:
            print(f"Error: {message}", file=sys.stderr)
    
    def display_warning(self, message: str) -> None:
        """Display warning message."""
        if not self.silent:
            if self.enable_rich_ui:
                self.console.print(f"[yellow]Warning:[/yellow] {message}")
            else:
                print(f"Warning: {message}", file=sys.stderr)
    
    def display_info(self, message: str) -> None:
        """Display info message."""
        if not self.silent:
            if self.enable_rich_ui:
                self.console.print(f"[blue]Info:[/blue] {message}")
            else:
                print(f"Info: {message}")
    
    def _print_dict(self, data: Dict[str, Any], indent: int = 0) -> None:
        """Print dictionary with indentation."""
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{' ' * indent}{key}:")
                self._print_dict(value, indent + 2)
            else:
                print(f"{' ' * indent}{key}: {value}")
    
    def set_silent(self, silent: bool) -> None:
        """Enable or disable silent mode."""
        self.silent = silent