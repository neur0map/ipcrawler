#!/usr/bin/env python3
"""
Single Rich-based User Output System for IPCrawler

This module provides a unified, clean interface for all user-facing output.
Designed to be easily replaceable with TUI interface later.
"""

from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich import box
from rich.live import Live
from typing import List, Dict, Any, Optional
import time
import threading

# ASCII art imports
try:
    import pyfiglet
    from termcolor import colored
    PYFIGLET_AVAILABLE = True
except ImportError:
    PYFIGLET_AVAILABLE = False

# Config no longer needed for verbose checks

class UserDisplay:
    """Single interface for all user-facing output using Rich formatting"""
    
    def __init__(self):
        self.console = Console()
        self._last_was_plugin = False
        
        # Loading management
        self.live = None
        self.current_tool = None
        self.target = None
        self.start_time = None
        self._is_loading_active = False
        self._update_thread = None
        self._stop_event = None
        
        # Activity tracking
        self.last_activity = None
        self.activity_count = 0
        self.is_stalled = False
        self.stall_threshold = 30
    
    def plugin_start(self, target: str, plugin_name: str):
        """Show plugin start with clean formatting"""
        # Add spacing if last message wasn't a plugin message
        if not self._last_was_plugin:
            self.console.print()
            
        start_text = Text()
        start_text.append("Starting: ", style="bright_white")
        start_text.append(f"{plugin_name}", style="cyan bold")
        start_text.append(" → ", style="dim white")
        start_text.append(f"{target}", style="yellow")
        
        self.console.print(start_text)
        self._last_was_plugin = True
    
    def plugin_complete(self, target: str, plugin_name: str, duration: str, success: bool = True):
        """Show plugin completion with clean formatting"""
        icon = "✓" if success else "✗"
        color = "green" if success else "red"
        
        complete_text = Text()
        complete_text.append("Completed: ", style="bright_white")
        complete_text.append(f"{plugin_name}", style="cyan bold")
        complete_text.append(" → ", style="dim white") 
        complete_text.append(f"{target}", style="yellow")
        complete_text.append(f" ({duration})", style="dim green")
        complete_text.append(f" {icon}", style=f"{color} bold")
        
        self.console.print(complete_text)
        self._last_was_plugin = True
    
    def status_info(self, message: str):
        """Show informational status message"""
        # Add spacing before non-plugin messages
        if self._last_was_plugin:
            self.console.print()
            self._last_was_plugin = False
            
        self.console.print(f"[bright_blue]•[/bright_blue] {message}")
    
    def status_warning(self, message: str):
        """Show warning message"""
        # Add spacing before non-plugin messages
        if self._last_was_plugin:
            self.console.print()
            self._last_was_plugin = False
            
        self.console.print(f"[yellow]![/yellow] {message}")
    
    def status_error(self, message: str):
        """Show error message"""
        # Add spacing before non-plugin messages  
        if self._last_was_plugin:
            self.console.print()
            self._last_was_plugin = False
            
        self.console.print(f"[red]✗[/red] {message}")
    
    def status_debug(self, message: str):
        """Show debug message"""
        # Add spacing before non-plugin messages
        if self._last_was_plugin:
            self.console.print()
            self._last_was_plugin = False
            
        self.console.print(f"[dim]debug:[/dim] {message}")
    
    def target_start(self, target: str):
        """Show target scan start"""
        self.console.print()
        self.console.print(f"[bold bright_yellow]Scanning target: {target}[/bold bright_yellow]")
        self.console.print()
        self._last_was_plugin = False
    
    def target_complete(self, target: str, duration: str):
        """Show target scan completion"""
        self.console.print()
        self.console.print(f"[bold green]Target {target} completed in {duration}[/bold green]")
        self.console.print()
        self._last_was_plugin = False
    
    def show_summary(self, message: str):
        """Show summary or important information"""
        self.console.print()
        self.console.print(f"[bold bright_white]{message}[/bold bright_white]")
        self.console.print()
        self._last_was_plugin = False
    
    def show_ascii_art(self):
        """Display clean ASCII art for ipcrawler"""
        if PYFIGLET_AVAILABLE:
            # Create modern ASCII art with pyfiglet and rich styling
            ascii_text = pyfiglet.figlet_format("IPCRAWLER", font="slant")
            
            self.console.print("═" * 75, style="dim cyan")
            self.console.print()
            
            # Split lines and apply gradient colors
            lines = ascii_text.split('\n')
            colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'magenta']
            
            for i, line in enumerate(lines):
                if line.strip():
                    color = colors[i % len(colors)]
                    self.console.print(line, style=f"bold {color}")
                else:
                    self.console.print(line)
            
            self.console.print()
            self.console.print("    🕷️  Multi-threaded Network Reconnaissance & Service Crawler  🕷️", style="bold bright_magenta")
            self.console.print()
            self.console.print("═" * 75, style="dim cyan")
            self.console.print()
        else:
            # Simple text banner
            banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║  ██╗██████╗  ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗        ║
║  ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗       ║
║  ██║██████╔╝██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝       ║
║  ██║██╔═══╝ ██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗       ║
║  ██║██║     ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║       ║
║  ╚═╝╚═╝      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝       ║
║                                                                              ║
║       🕷️  Multi-threaded Network Reconnaissance & Service Crawler  🕷️        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
            self.console.print(banner, style="bold cyan")
    
    def show_version(self, version: str = "0.1.0-alpha", with_art: bool = True):
        """Display version information"""
        if with_art:
            self.show_ascii_art()
            self.console.print()
        
        version_text = Text.assemble(
            ("🕷️  ", "cyan"), ("ipcrawler ", "bold cyan"),
            (f"v{version}", "bold green"), ("  🕸️", "dim bright_magenta")
        )
        self.console.print(Panel(Align.center(version_text), border_style="cyan", box=box.DOUBLE, padding=(1, 2)))
    
    def show_help(self, version: str = "0.1.0-alpha"):
        """Display modern help interface"""
        # Spider theme colors
        theme_color = "cyan"
        accent_color = "bright_magenta"
        success_color = "green"
        
        # Banner
        banner_text = Text()
        banner_text.append("🕷️  ipcrawler", style=f"bold {theme_color}")
        banner_text.append("  🕸️", style=f"dim {accent_color}")
        subtitle = Text("Smart Network Reconnaissance Made Simple", style=f"italic {accent_color}")
        
        self.console.print(Panel(
            Align.center(Text.assemble(banner_text, "\n", subtitle)),
            box=box.DOUBLE, border_style=theme_color, padding=(1, 2)
        ))
        self.console.print()
        
        # Usage
        usage_text = Text.assemble(
            ("Usage: ", "bold white"), ("ipcrawler ", f"bold {theme_color}"),
            ("[OPTIONS] ", f"{accent_color}"), ("TARGET(S)", f"bold {success_color}")
        )
        self.console.print(Panel(usage_text, title="🎯 Usage", border_style=theme_color, box=box.ROUNDED))
        self.console.print()
        
        # Examples
        examples = [
            ("Single target", "ipcrawler 192.168.1.100"),
            ("Multiple targets", "ipcrawler 10.0.0.1 target.com"),
            ("From file", "ipcrawler -t targets.txt"),
            ("Custom ports", "ipcrawler -p 80,443,8080 target.com"),
            ("Comprehensive scan", "ipcrawler --comprehensive target.com"),
            ("Fast scan", "ipcrawler --fast target.com")
        ]
        
        examples_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        examples_table.add_column("Description", style=f"{accent_color}")
        examples_table.add_column("Command", style=f"bold {theme_color}")
        
        for desc, cmd in examples:
            examples_table.add_row(f"🔸 {desc}", cmd)
        
        self.console.print(Panel(examples_table, title="⚡ Quick Examples", border_style=theme_color, box=box.ROUNDED))
        self.console.print()
        
        # Core options
        core_options = [
            ("-t, --target-file", "Read targets from file"),
            ("-p, --ports", "Custom ports to scan"),
            ("--comprehensive", "Enable comprehensive scanning"),
            ("-l, --list", "List available plugins"),
            ("--fast", "Quick reconnaissance scans"),
            ("--help", "Show this help message")
        ]
        
        options_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        options_table.add_column("Option", style=f"bold {theme_color}", width=22)
        options_table.add_column("Description", style="white", width=35)
        
        for option, desc in core_options:
            options_table.add_row(option, desc)
        
        self.console.print(Panel(options_table, title="🛠️  Core Options", border_style=theme_color, box=box.ROUNDED))
        self.console.print()
        
        # Footer
        footer_text = Text.assemble(
            (f"ipcrawler v{version}", f"bold {theme_color}"),
            (" | Built for the cybersecurity community ", "dim white"),
            ("🕷️", f"{accent_color}")
        )
        self.console.print(Panel(Align.center(footer_text), border_style=f"dim {accent_color}", box=box.SIMPLE))
    
    def show_plugin_list(self, plugin_types: Dict[str, List[Any]], list_type: str = "plugins"):
        """Display plugin listing"""
        theme_color = "cyan"
        accent_color = "bright_magenta"
        
        # Banner
        banner_text = Text()
        banner_text.append("🕷️  ipcrawler", style=f"bold {theme_color}")
        banner_text.append("  🕸️", style=f"dim {accent_color}")
        subtitle = Text("Available Plugins", style=f"italic {accent_color}")
        
        self.console.print(Panel(
            Align.center(Text.assemble(banner_text, "\n", subtitle)),
            box=box.DOUBLE, border_style=theme_color, padding=(1, 2)
        ))
        self.console.print()
        
        # Determine what to show
        type_lower = list_type.lower()
        show_port = type_lower in ['plugin', 'plugins', 'port', 'ports', 'portscan', 'portscans']
        show_service = type_lower in ['plugin', 'plugins', 'service', 'services', 'servicescan', 'servicescans']
        show_report = type_lower in ['plugin', 'plugins', 'report', 'reports', 'reporting']
        
        # Show plugin categories
        for category_name, show_category in [('port', show_port), ('service', show_service), ('report', show_report)]:
            if show_category and category_name in plugin_types:
                table = Table(box=box.ROUNDED, show_header=True, header_style=f"bold {theme_color}")
                table.add_column("🎯 Plugin Name", style="bold white", width=25)
                table.add_column("Description", style="dim white", width=50)
                
                for plugin in plugin_types[category_name]:
                    description = plugin.description if hasattr(plugin, 'description') and plugin.description else "No description available"
                    table.add_row(plugin.name, description)
                
                title_map = {
                    'port': "🔍 Port Scan Plugins",
                    'service': "🛠️  Service Scan Plugins", 
                    'report': "📋 Report Plugins"
                }
                
                self.console.print(Panel(table, title=title_map[category_name], border_style=theme_color, box=box.DOUBLE))
                self.console.print()
    
    # Loading and Progress Management
    def start_loading(self, tool_name: str, target: str, command: str = "", estimated_minutes: Optional[int] = None):
        """Start the loading interface"""
        # If already active, just switch to new tool
        if self._is_loading_active:
            self._switch_tool(tool_name, target, command, estimated_minutes)
            return
            
        self.current_tool = tool_name
        self.target = target
        self.start_time = time.time()
        self._is_loading_active = True
        
        # Reset activity tracking
        self.last_activity = time.time()
        self.activity_count = 0
        self.is_stalled = False
        
        # Start live display
        self.live = Live(refresh_per_second=2, console=self.console, auto_refresh=False)
        self.live.start()
        
        # Initial render
        self.live.update(self._render_status())
        self.live.refresh()
        
        # Start background thread for updates
        self._stop_event = threading.Event()
        self._update_thread = threading.Thread(target=self._background_update, daemon=True)
        self._update_thread.start()
    
    def _switch_tool(self, tool_name: str, target: str, command: str = "", estimated_minutes: Optional[int] = None):
        """Switch to a new tool without stopping the loading interface"""
        self.current_tool = tool_name
        self.target = target
        
        # Reset activity tracking
        self.last_activity = time.time()
        self.activity_count = 0
        self.is_stalled = False
        
        # Update display immediately
        if self.live:
            self.live.update(self._render_status())
            self.live.refresh()
    
    def update_progress(self, percentage: Optional[int] = None, status: str = ""):
        """Update status"""
        if not self._is_loading_active:
            return
            
        # Record activity
        self.last_activity = time.time()
        self.activity_count += 1
        self.is_stalled = False
            
        # Update display
        if self.live:
            self.live.update(self._render_status())
            self.live.refresh()
    
    def record_activity(self, activity_type: str = "output"):
        """Record tool activity"""
        if not self._is_loading_active:
            return
            
        self.last_activity = time.time()
        self.activity_count += 1
        self.is_stalled = False
    
    def _render_status(self):
        """Render simple status line"""
        if not self._is_loading_active:
            return Text("")
            
        # Calculate elapsed time
        elapsed = time.time() - self.start_time if self.start_time else 0
        elapsed_str = self._format_time(elapsed)
        
        # Check for stall
        if self.last_activity:
            time_since_activity = time.time() - self.last_activity
            self.is_stalled = time_since_activity > self.stall_threshold
        
        # Create simple one-line status
        status = Text()
        status.append("🕷️ ", style="cyan bold")
        status.append(f"{self.current_tool}", style="white bold")
        status.append(f" → {self.target}", style="yellow")
        status.append(f" [{elapsed_str}]", style="dim white")
        
        # Activity indicator
        if self.is_stalled:
            status.append(" ⏸️", style="red")
        elif self.activity_count > 0:
            status.append(" ⚡", style="green")
        
        return status
    
    def _background_update(self):
        """Background thread to update the display"""
        while self._is_loading_active and not self._stop_event.is_set():
            try:
                # Update the live display
                if self.live and self._is_loading_active:
                    self.live.update(self._render_status())
                    self.live.refresh()
                
                # Wait 0.5 seconds before next update
                self._stop_event.wait(0.5)
                
            except Exception:
                # Ignore any errors in background thread
                pass
    
    def _format_time(self, seconds: float) -> str:
        """Format time duration"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"
    
    def stop_loading(self, success: bool = True, final_message: str = "", silent: bool = False):
        """Stop the loading interface"""
        if not self._is_loading_active:
            return
            
        # Stop background thread
        if self._stop_event:
            self._stop_event.set()
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)
            
        # Stop live display
        if self.live:
            self.live.stop()
        
        # Show completion message (only if not silent and has message)
        if not silent and final_message:
            elapsed = time.time() - self.start_time if self.start_time else 0
            status_icon = "✅" if success else "❌"
            
            completion_text = Text()
            completion_text.append(f"{status_icon} ", style="green bold" if success else "red bold")
            completion_text.append(f"{self.current_tool}", style="white bold")
            completion_text.append(f" completed in {self._format_time(elapsed)}", style="dim white")
            if final_message:
                completion_text.append(f" • {final_message}", style="dim white")
            
            self.console.print(completion_text)
        
        # Reset state
        self._is_loading_active = False
        self.live = None
        self.current_tool = None
        self.start_time = None
        self._update_thread = None
        self._stop_event = None
    
    def is_loading_active(self) -> bool:
        """Check if loading is currently active"""
        return self._is_loading_active
    
    # Scan Status Methods (from loading.py ScanStatus class)
    def show_command_execution(self, target: str, plugin_name: str, command: str, show_details: bool = False):
        """Show command execution details"""
        if show_details:
            # Show detailed command info
            title = f"🔧 {plugin_name} → {target}"
            subtitle = f"💻 Command Execution"
            
            command_panel = Panel(
                Text(command, style="white"),
                title=title,
                subtitle=subtitle,
                title_align="left",
                subtitle_align="right", 
                border_style="bright_blue",
                padding=(0, 1)
            )
        else:
            # Standard command panel
            command_panel = Panel(
                Text(command, style="dim white"),
                title=f"🔧 {plugin_name}",
                title_align="left",
                border_style="blue",
                padding=(0, 1)
            )
        
        self.console.print(command_panel)
        self.console.print()
    
    def show_scan_result(self, target: str, plugin_name: str, result: str, level: str = "info"):
        """Show important scan results"""
        level_styles = {
            "info": ("ℹ️", "blue"),
            "error": ("❌", "red bold"),
            "warn": ("⚠️", "yellow bold"),
            "success": ("✅", "green bold")
        }
        icon, style = level_styles.get(level, ("ℹ️", "blue"))
        
        result_text = Text()
        result_text.append(f"{icon}  ", style=style)
        result_text.append(f"[{target}] ", style="yellow dim")
        result_text.append(result, style="white")
        
        self.console.print(result_text)
    
    def show_pattern_match(self, target: str, plugin_name: str, pattern: str, match: str):
        """Show pattern matches"""
        match_text = Text()
        match_text.append("🎯  ", style="cyan bold")
        match_text.append("Found: ", style="white")
        match_text.append(f"{match}", style="green bold")
        match_text.append(f" [{target}]", style="yellow dim")
        
        self.console.print(match_text)
    
    def show_command_output(self, target: str, plugin_name: str, line: str, show_output: bool = False):
        """Show command output"""
        if show_output:
            output_text = Text()
            output_text.append("   📝 ", style="dim blue")
            output_text.append(f"[{target}] ", style="dim yellow")
            output_text.append(line.strip(), style="dim white")
            
            self.console.print(output_text)
    
    def show_service_discovery(self, target: str, service_name: str, protocol: str, port: int):
        """Show service discovery"""
        discovery_text = Text()
        discovery_text.append("🎯  ", style="cyan bold")
        discovery_text.append("Service Found: ", style="white")
        discovery_text.append(f"{service_name}", style="green bold")
        discovery_text.append(" on ", style="dim white")
        discovery_text.append(f"{protocol}/{port}", style="magenta bold")
        discovery_text.append(f" ({target})", style="yellow dim")
        
        self.console.print()
        self.console.print(discovery_text)
        self.console.print()

# Global instance for easy access
user_display = UserDisplay()