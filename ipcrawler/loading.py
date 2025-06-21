import asyncio
import time
import threading
import os
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.text import Text
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
    """Simplified status display that doesn't interfere with bottom status line"""
    
    @staticmethod
    def show_scan_start(target: str, plugin_name: str, verbosity: int = 0):
        """Show scan start message (simplified)"""
        # Don't show start messages during live loading to avoid conflicts
        pass
    
    @staticmethod
    def show_scan_result(target: str, plugin_name: str, result: str, level: str = "info", verbosity: int = 0):
        """Show important scan results only"""
        # Only show errors and warnings to avoid cluttering
        if level in ["error", "warn"]:
            level_styles = {
                "error": ("❌", "red bold"),
                "warn": ("⚠️", "yellow bold")
            }
            icon, style = level_styles[level]
            
            text = Text()
            text.append(f"{icon} ", style=style)
            text.append(f"[{target}] ", style="yellow")
            text.append(result, style="white")
            console.print(text)
    
    @staticmethod
    def show_pattern_match(target: str, plugin_name: str, pattern: str, match: str, verbosity: int = 0):
        """Show pattern match (only at high verbosity)"""
        if verbosity >= 3:  # Only at -vvv to avoid clutter
            console.print(f"🎯 [{target}] Found: {match}", style="dim cyan")
    
    @staticmethod
    def show_command_output(target: str, plugin_name: str, line: str, verbosity: int = 0):
        """Show command output (only at highest verbosity and when loading is not active)"""
        # Suppress output when loading interface is active to avoid interference
        # Only show at highest verbosity to avoid clutter
        if verbosity >= 3 and not is_loading_active():
            console.print(f"📝 [{target}] {line}", style="dim white")

# Global status instance
scan_status = ScanStatus()