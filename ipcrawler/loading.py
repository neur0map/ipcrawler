import asyncio
import time
import threading
import os
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from rich.align import Align
from ipcrawler.config import config

console = Console()

class LoadingManager:
    """Simple bottom-pinned status line"""
    
    def __init__(self):
        self.live = None
        self.current_tool = None
        self.target = None
        self.start_time = None
        self.verbosity = config.get('verbose', 0)
        self._is_active = False
        self._update_thread = None
        self._stop_event = None
        
        # Activity tracking
        self.last_activity = None
        self.activity_count = 0
        self.is_stalled = False
        self.stall_threshold = 30
    
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
        
    def start_loading(self, tool_name: str, target: str, command: str = "", estimated_minutes: Optional[int] = None):
        """Start the simple loading interface"""
        # If already active, just switch to new tool
        if self._is_active:
            self._switch_tool(tool_name, target, command, estimated_minutes)
            return
            
        self.current_tool = tool_name
        self.target = target
        self.start_time = time.time()
        self._is_active = True
        
        # Reset activity tracking
        self.last_activity = time.time()
        self.activity_count = 0
        self.is_stalled = False
        
        # Start simple live display - no progress bar, just status line
        # Use auto_refresh=False and control refreshes manually for better performance
        self.live = Live(refresh_per_second=2, console=console, auto_refresh=False)
        self.live.start()
        
        # Initial render
        self.live.update(self._render_status())
        self.live.refresh()
        
        # Start background thread for updates
        self._stop_event = threading.Event()
        self._update_thread = threading.Thread(target=self._background_update, daemon=True)
        self._update_thread.start()
        
    def update_progress(self, percentage: Optional[int] = None, status: str = ""):
        """Update status (simplified - no progress bar)"""
        if not self._is_active:
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
        if not self._is_active:
            return
            
        self.last_activity = time.time()
        self.activity_count += 1
        self.is_stalled = False
    
    def _render_status(self):
        """Render simple status line"""
        if not self._is_active:
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
        while self._is_active and not self._stop_event.is_set():
            try:
                # Update the live display
                if self.live and self._is_active:
                    self.live.update(self._render_status())
                    self.live.refresh()
                
                # Wait 0.5 seconds before next update (2 updates per second)
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
        """Stop the simple loading interface"""
        if not self._is_active:
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
            
            console.print(completion_text)
        
        # Reset state
        self._is_active = False
        self.live = None
        self.current_tool = None
        self.start_time = None
        self._update_thread = None
        self._stop_event = None

# Global loading manager instance
loading_manager = LoadingManager()

def start_tool_loading(tool_name: str, target: str, command: str = "", estimated_minutes: Optional[int] = None):
    """Start loading for a tool"""
    loading_manager.start_loading(tool_name, target, command, estimated_minutes)

def update_tool_progress(percentage: Optional[int] = None, status: str = ""):
    """Update tool progress"""
    loading_manager.update_progress(percentage, status)

def record_tool_activity(activity_type: str = "output"):
    """Record tool activity for intelligent progress tracking"""
    loading_manager.record_activity(activity_type)


def stop_tool_loading(success: bool = True, final_message: str = "", silent: bool = False):
    """Stop loading for a tool"""
    loading_manager.stop_loading(success, final_message, silent)

def is_loading_active() -> bool:
    """Check if loading is currently active"""
    return loading_manager._is_active

class ScanStatus:
    """Beautiful Rich-based status display for scan operations"""
    
    @staticmethod
    def show_scan_start(target: str, plugin_name: str, verbosity: int = 0):
        """Show beautiful scan start message"""
        if verbosity >= 0:  # Show by default
            # Create a clean, spaced start message
            start_text = Text()
            start_text.append("▶️  ", style="green bold")
            start_text.append("Starting: ", style="white")
            start_text.append(f"{plugin_name}", style="cyan bold")
            start_text.append(" → ", style="dim white")
            start_text.append(f"{target}", style="yellow bold")
            
            console.print()  # Add spacing
            console.print(start_text)
    
    @staticmethod
    def show_scan_completion(target: str, plugin_name: str, duration: str, success: bool = True, verbosity: int = 0):
        """Show beautiful scan completion message"""
        if verbosity >= 0:  # Show by default
            icon = "✅" if success else "❌"
            color = "green" if success else "red"
            
            completion_text = Text()
            completion_text.append(f"{icon}  ", style=f"{color} bold")
            completion_text.append("Completed: ", style="white")
            completion_text.append(f"{plugin_name}", style="cyan bold")
            completion_text.append(" → ", style="dim white")
            completion_text.append(f"{target}", style="yellow bold")
            completion_text.append(f" ({duration})", style="dim green")
            
            console.print(completion_text)
            console.print()  # Add spacing
    
    @staticmethod
    def show_command_execution(target: str, plugin_name: str, command: str, verbosity: int = 0):
        """Show beautiful command execution details"""
        if verbosity >= 1:  # Show at -v level
            # At -vvv level, show more detailed info
            if verbosity >= 3:
                # Show more detailed command info
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
            
            console.print(command_panel)
            console.print()  # Add spacing
    
    @staticmethod
    def show_scan_result(target: str, plugin_name: str, result: str, level: str = "info", verbosity: int = 0):
        """Show important scan results with beautiful formatting"""
        if level in ["error", "warn"] or verbosity >= 1:  # Show at -v level
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
            
            console.print(result_text)
    
    @staticmethod
    def show_pattern_match(target: str, plugin_name: str, pattern: str, match: str, verbosity: int = 0):
        """Show pattern matches with beautiful formatting"""
        if verbosity >= 2:  # Show at -vv level
            match_text = Text()
            match_text.append("🎯  ", style="cyan bold")
            match_text.append("Found: ", style="white")
            match_text.append(f"{match}", style="green bold")
            match_text.append(f" [{target}]", style="yellow dim")
            
            console.print(match_text)
    
    @staticmethod
    def show_command_output(target: str, plugin_name: str, line: str, verbosity: int = 0):
        """Show command output with beautiful formatting"""
        if verbosity >= 3:  # Show at -vvv level - even with loading active
            # Create a subtle output line
            output_text = Text()
            output_text.append("   📝 ", style="dim blue")
            output_text.append(f"[{target}] ", style="dim yellow")
            output_text.append(line.strip(), style="dim white")
            
            console.print(output_text)
    
    @staticmethod
    def show_service_discovery(target: str, service_name: str, protocol: str, port: int, verbosity: int = 0):
        """Show service discovery with beautiful formatting"""
        if verbosity >= 0:  # Show by default - important info
            discovery_text = Text()
            discovery_text.append("🎯  ", style="cyan bold")
            discovery_text.append("Service Found: ", style="white")
            discovery_text.append(f"{service_name}", style="green bold")
            discovery_text.append(" on ", style="dim white")
            discovery_text.append(f"{protocol}/{port}", style="magenta bold")
            discovery_text.append(f" ({target})", style="yellow dim")
            
            console.print()  # Add spacing
            console.print(discovery_text)
            console.print()  # Add spacing
    
    @staticmethod
    def show_progress_summary(active_scans: list, verbosity: int = 0):
        """Show a beautiful progress summary table"""
        if verbosity >= 1 and active_scans:  # Show at -v level
            # Create a beautiful table for active scans
            table = Table(title="🔄 Active Scans", show_header=True, header_style="bold cyan")
            table.add_column("Tool", style="cyan", no_wrap=True)
            table.add_column("Target", style="yellow", no_wrap=True)
            table.add_column("Duration", style="green", no_wrap=True)
            table.add_column("Status", style="white")
            
            for scan in active_scans:
                duration = scan.get("duration", "0s")
                # Add color coding based on duration
                if "m" in duration:
                    duration_style = "yellow"  # Long running
                else:
                    duration_style = "green"   # Still fresh
                    
                table.add_row(
                    scan.get("tool", "Unknown"),
                    scan.get("target", "Unknown"),
                    Text(duration, style=duration_style),
                    "🔄 Running"
                )
            
            console.print()
            console.print(Align.center(table))
            console.print()
            
            # Add extra detail at higher verbosity
            if verbosity >= 2:
                scan_count = len(active_scans)
                console.print(Align.center(
                    Text(f"💼 {scan_count} concurrent scan{'s' if scan_count != 1 else ''} in progress", 
                         style="dim italic")
                ))
                console.print()

    @staticmethod
    def show_verbosity_guide():
        """Show a beautiful guide explaining verbosity levels"""
        guide_table = Table(title="🔊 Verbosity Levels", show_header=True, header_style="bold cyan")
        guide_table.add_column("Level", style="cyan bold", no_wrap=True)
        guide_table.add_column("Flag", style="yellow bold", no_wrap=True)
        guide_table.add_column("What You'll See", style="white")
        
        guide_table.add_row(
            "Silent", "-q", "Only the loading bar and critical errors"
        )
        guide_table.add_row(
            "Normal", "(default)", "Scan starts/completions, service discoveries"
        )
        guide_table.add_row(
            "Verbose", "-v", "All above + command panels, progress tables, scan results"
        )
        guide_table.add_row(
            "Very Verbose", "-vv", "All above + pattern matches, detailed findings"
        )
        guide_table.add_row(
            "Debug", "-vvv", "All above + live command output, full debugging"
        )
        
        console.print()
        console.print(Align.center(guide_table))
        console.print()
        console.print(Align.center(
            Text("💡 Use different verbosity levels to control output detail", style="dim italic")
        ))
        console.print()

# Global status instance
scan_status = ScanStatus()