"""
Rich TUI status display for ipcrawler using Executive Dashboard layout.
"""

import sys
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from ..models.result import ExecutionResult, ScanResult
from .plugin_tracker import PluginTracker, PluginState
from .layout_executive import ExecutiveDashboardLayout


class RichStatusDispatcher:
    """Rich TUI status display with Executive Dashboard layout."""
    
    def __init__(self, config: Dict[str, Any], silent: bool = False):
        self.config = config
        self.silent = silent
        self.console = Console()
        self.plugin_tracker = PluginTracker()
        
        # TUI settings
        self.enable_rich_ui = config.get("enable_rich_ui", True)
        self.fullscreen_mode = config.get("fullscreen_mode", False)
        self.refresh_rate = config.get("refresh_rate", 2)
        self.theme = config.get("theme", "minimal")
        
        # Executive Dashboard Layout
        self.executive_layout = ExecutiveDashboardLayout(config, self.plugin_tracker)
        self.layout = self.executive_layout.get_layout()
        
        # Live display
        self.live = None
        
        # Scan state
        self.scan_active = False
        self.start_time = None
        self.total_templates = 0
        self.completed_templates = 0
        
        # Timer task for live updates
        self._timer_task = None
        self._update_stop_event = None
    
    def _update_display(self) -> None:
        """Update the display with current state."""
        if not self.enable_rich_ui or self.silent:
            return
        
        # Update executive layout
        self.executive_layout.set_scan_active(self.scan_active)
        self.executive_layout.update_display()
    
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
        
        # Initialize plugin tracker
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
            summary_table.add_column("Metric", style="bright_white")
            summary_table.add_column("Value", style="bright_white")
            
            summary_table.add_row("Total scans:", str(summary["total_plugins"]))
            summary_table.add_row("Successful:", str(summary["completed"]), style="green")
            summary_table.add_row("Failed:", str(summary["failed"]), style="red")
            summary_table.add_row("Success rate:", f"{summary['success_rate']:.1f}%")
            
            elapsed = summary["elapsed_time"]
            elapsed_str = f"{elapsed.seconds//60:02d}:{elapsed.seconds%60:02d}"
            summary_table.add_row("Elapsed time:", elapsed_str)
            
            self.console.print()
            self.console.print(Panel(summary_table, title="Scan Summary", style="white"))
    
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

    def display_version(self, version: str, app_name: str = "ipcrawler") -> None:
        """Display Rich version information."""
        if self.silent:
            return
        
        # Create version info table
        version_table = Table(show_header=False, box=None, padding=(0, 1))
        version_table.add_column("Property", style="bright_white", width=20)
        version_table.add_column("Value", style="bright_white")
        
        version_table.add_row("Application:", app_name)
        version_table.add_row("Version:", version)
        version_table.add_row("Type:", "Security Tool Orchestration Framework")
        version_table.add_row("License:", "Open Source")
        version_table.add_row("Copyright:", "2024")
        
        # Create features table
        features_table = Table(show_header=False, box=None, padding=(0, 1))
        features_table.add_column("Feature", style="green", width=20)
        features_table.add_column("Status", style="bright_white")
        
        features_table.add_row("Rich TUI:", "✓ Enabled" if self.enable_rich_ui else "✗ Disabled")
        features_table.add_row("Layout:", "✓ Executive Dashboard")
        features_table.add_row("Theme:", f"✓ {self.theme.title()}")
        features_table.add_row("Fullscreen:", "✓ Enabled" if self.fullscreen_mode else "✗ Disabled")
        features_table.add_row("Async Execution:", "✓ Enabled")
        features_table.add_row("Preset System:", "✓ Enabled")
        
        # Display version panel
        version_panel = Panel(
            version_table,
            title=f"[bright_white]{app_name} Version Information[/bright_white]",
            style="white"
        )
        
        # Display features panel
        features_panel = Panel(
            features_table,
            title=f"[bright_white]Features[/bright_white]",
            style="white"
        )
        
        self.console.print()
        self.console.print(version_panel)
        self.console.print(features_panel)

    def display_help(self, app_name: str = "ipcrawler") -> None:
        """Display Rich help information."""
        if self.silent:
            return
        
        # Create header
        header_text = Text(f"{app_name} - Security Tool Orchestration Framework", style="bright_white")
        header_panel = Panel(
            Align.center(header_text),
            style="white"
        )
        
        # Create commands table
        commands_table = Table(show_header=True, header_style="bright_white", box=None, padding=(0, 1))
        commands_table.add_column("Command", style="bright_white", width=25)
        commands_table.add_column("Description", style="white")
        
        commands_table.add_row("run TEMPLATE TARGET", "Run a specific template")
        commands_table.add_row("scan-folder FOLDER TARGET", "Run all templates in a folder")
        commands_table.add_row("scan-all TARGET", "Run all templates")
        commands_table.add_row("list [--category CAT]", "List available templates")
        commands_table.add_row("results TARGET", "Show results for a target")
        commands_table.add_row("export TARGET", "Export results")
        commands_table.add_row("config", "Show configuration")
        commands_table.add_row("schema", "Show template JSON schema")
        commands_table.add_row("validate", "Validate templates")
        
        # Create shortcuts table
        shortcuts_table = Table(show_header=True, header_style="bright_white", box=None, padding=(0, 1))
        shortcuts_table.add_column("Shortcut", style="green", width=25)
        shortcuts_table.add_column("Description", style="white")
        
        shortcuts_table.add_row("-default TARGET", "Run default templates")
        shortcuts_table.add_row("-recon TARGET", "Run reconnaissance templates")
        shortcuts_table.add_row("-custom TARGET", "Run custom templates")
        shortcuts_table.add_row("-htb TARGET", "Run HTB/CTF templates")
        
        # Create options table
        options_table = Table(show_header=True, header_style="bright_white", box=None, padding=(0, 1))
        options_table.add_column("Option", style="bright_white", width=25)
        options_table.add_column("Description", style="white")
        
        options_table.add_row("-debug, --debug", "Enable debug mode")
        options_table.add_row("--version", "Show version information")
        options_table.add_row("-h, --help", "Show this help message")
        
        # Create examples table
        examples_table = Table(show_header=True, header_style="bright_white", box=None, padding=(0, 1))
        examples_table.add_column("Example", style="dim white")
        
        examples_table.add_row("python ipcrawler.py list")
        examples_table.add_row("python ipcrawler.py run custom/robots-txt-fetch example.com")
        examples_table.add_row("python ipcrawler.py -recon example.com")
        examples_table.add_row("python ipcrawler.py -debug scan-all example.com")
        
        # Display all panels
        self.console.print()
        self.console.print(header_panel)
        
        commands_panel = Panel(
            commands_table,
            title=f"[bright_white]Commands[/bright_white]",
            style="white"
        )
        self.console.print(commands_panel)
        
        shortcuts_panel = Panel(
            shortcuts_table,
            title=f"[bright_white]Category Shortcuts[/bright_white]",
            style="white"
        )
        self.console.print(shortcuts_panel)
        
        options_panel = Panel(
            options_table,
            title=f"[bright_white]Options[/bright_white]",
            style="white"
        )
        self.console.print(options_panel)
        
        examples_panel = Panel(
            examples_table,
            title=f"[bright_white]Examples[/bright_white]",
            style="white"
        )
        self.console.print(examples_panel)