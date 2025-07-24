"""Base console interface for IPCrawler

Provides a centralized interface for all console output operations.
"""

from typing import Any, Optional, Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.text import Text
from contextlib import contextmanager
import sys


class IPCrawlerConsole:
    """Centralized console interface for consistent output across IPCrawler"""
    
    def __init__(self, 
                 stderr: bool = False,
                 force_terminal: Optional[bool] = None,
                 force_jupyter: Optional[bool] = None,
                 theme: Optional[str] = None):
        """Initialize console with configuration
        
        Args:
            stderr: Whether to output to stderr instead of stdout
            force_terminal: Force terminal mode
            force_jupyter: Force Jupyter mode
            theme: Color theme to use
        """
        self.console = Console(
            stderr=stderr,
            force_terminal=force_terminal,
            force_jupyter=force_jupyter
        )
        self.theme = theme or "default"
        self._load_theme()
    
    def _load_theme(self):
        """Load color theme configuration"""
        # Theme will be loaded from themes module
        pass
    
    def print(self, *args, **kwargs):
        """Print to console with Rich formatting"""
        self.console.print(*args, **kwargs)
    
    def success(self, message: str, **kwargs):
        """Print success message"""
        self.console.print(f"✅ {message}", style="green", **kwargs)
    
    def error(self, message: str, **kwargs):
        """Print error message"""
        self.console.print(f"❌ {message}", style="red", **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Print warning message"""
        self.console.print(f"⚠️  {message}", style="yellow", **kwargs)
    
    def info(self, message: str, **kwargs):
        """Print info message"""
        self.console.print(f"ℹ️  {message}", style="blue", **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Print critical message"""
        self.console.print(f"🚨 {message}", style="bold red", **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Print debug message"""
        if kwargs.get('verbose', False):
            self.console.print(f"🐛 {message}", style="dim", **kwargs)
    
    def rule(self, title: Optional[str] = None, **kwargs):
        """Print a horizontal rule"""
        self.console.rule(title, **kwargs)
    
    def panel(self, content: Any, title: Optional[str] = None, **kwargs):
        """Display content in a panel"""
        panel = Panel(content, title=title, **kwargs)
        self.console.print(panel)
    
    def table(self, title: Optional[str] = None, **kwargs) -> Table:
        """Create a new table"""
        return Table(title=title, **kwargs)
    
    def print_table(self, table: Table):
        """Print a table to console"""
        self.console.print(table)
    
    def code(self, code: str, lexer: str = "python", **kwargs):
        """Print syntax-highlighted code"""
        syntax = Syntax(code, lexer, **kwargs)
        self.console.print(syntax)
    
    @contextmanager
    def progress(self, description: str = "Processing..."):
        """Context manager for progress display"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(description, total=None)
            yield progress
    
    @contextmanager
    def status(self, status: str, spinner: str = "dots"):
        """Context manager for status display"""
        with self.console.status(status, spinner=spinner):
            yield
    
    def clear(self):
        """Clear the console"""
        self.console.clear()
    
    def save_html(self, path: str, clear: bool = True):
        """Save console output as HTML"""
        self.console.save_html(path, clear=clear)
    
    def save_text(self, path: str, clear: bool = True):
        """Save console output as text"""
        self.console.save_text(path, clear=clear)


# Global console instance
console = IPCrawlerConsole()


# Convenience functions
def print_success(message: str, **kwargs):
    """Print success message"""
    console.success(message, **kwargs)


def print_error(message: str, **kwargs):
    """Print error message"""
    console.error(message, **kwargs)


def print_warning(message: str, **kwargs):
    """Print warning message"""
    console.warning(message, **kwargs)


def print_info(message: str, **kwargs):
    """Print info message"""
    console.info(message, **kwargs)


def print_critical(message: str, **kwargs):
    """Print critical message"""
    console.critical(message, **kwargs)


def print_debug(message: str, **kwargs):
    """Print debug message"""
    console.debug(message, **kwargs)