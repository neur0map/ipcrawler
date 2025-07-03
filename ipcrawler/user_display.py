#!/usr/bin/env python3
"""
Single Rich-based User Output System for IPCrawler

This module provides a unified, clean interface for all user-facing output.
Designed to be easily replaceable with TUI interface later.
"""

from rich.console import Console
from rich.text import Text

# Import config with fallback to avoid circular imports
try:
    from ipcrawler.config import config
except ImportError:
    # Fallback config if import fails
    config = {'verbose': 0}

class UserDisplay:
    """Single interface for all user-facing output using Rich formatting"""
    
    def __init__(self):
        self.console = Console()
        self._last_was_plugin = False
    
    def plugin_start(self, target: str, plugin_name: str):
        """Show plugin start with clean formatting"""
        if config.get('verbose', 0) >= 0:  # Show by default
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
        if config.get('verbose', 0) >= 0:  # Show by default
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
    
    def status_info(self, message: str, verbosity: int = 0):
        """Show informational status message"""
        if config.get('verbose', 0) >= verbosity:
            # Add spacing before non-plugin messages
            if self._last_was_plugin:
                self.console.print()
                self._last_was_plugin = False
                
            self.console.print(f"[bright_blue]•[/bright_blue] {message}")
    
    def status_warning(self, message: str, verbosity: int = 0):
        """Show warning message"""
        if config.get('verbose', 0) >= verbosity:
            # Add spacing before non-plugin messages
            if self._last_was_plugin:
                self.console.print()
                self._last_was_plugin = False
                
            self.console.print(f"[yellow]![/yellow] {message}")
    
    def status_error(self, message: str, verbosity: int = 0):
        """Show error message"""
        if config.get('verbose', 0) >= verbosity:
            # Add spacing before non-plugin messages  
            if self._last_was_plugin:
                self.console.print()
                self._last_was_plugin = False
                
            self.console.print(f"[red]✗[/red] {message}")
    
    def status_debug(self, message: str):
        """Show debug message"""
        if config.get('verbose', 0) >= 2:
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

# Global instance for easy access
user_display = UserDisplay()