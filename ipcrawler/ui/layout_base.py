"""
Base layout renderer for Rich TUI interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from ..models.result import ExecutionResult, ScanResult
from .plugin_tracker import PluginTracker


class BaseLayoutRenderer(ABC):
    """Abstract base class for Rich TUI layout renderers."""
    
    def __init__(self, config: Dict[str, Any], plugin_tracker: PluginTracker):
        self.config = config
        self.plugin_tracker = plugin_tracker
        self.console = Console()
        
        # Common settings
        self.theme = config.get("theme", "minimal")
        self.scan_active = False
        
        # Theme colors
        self.colors = self._get_theme_colors()
        
        # Layout components
        self.layout = Layout()
        self._setup_layout()
    
    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors based on current theme."""
        themes = {
            "minimal": {
                "border": "white",
                "header_text": "bright_white",
                "header_secondary": "dim white",
                "progress_text": "bright_white",
                "active_text": "bright_white",
                "success_text": "green",
                "error_text": "red",
                "queued_text": "dim white",
                "info_text": "dim white",
                "accent": "blue",
                "warning": "yellow"
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
                "info_text": "bright_black",
                "accent": "bright_blue",
                "warning": "bright_yellow"
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
                "info_text": "green",
                "accent": "bright_green",
                "warning": "bright_yellow"
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
                "info_text": "cyan",
                "accent": "bright_magenta",
                "warning": "bright_yellow"
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
                "info_text": "green",
                "accent": "bright_yellow",
                "warning": "bright_red"
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
                "info_text": "blue",
                "accent": "bright_white",
                "warning": "bright_yellow"
            }
        }
        return themes.get(self.theme, themes["minimal"])
    
    @abstractmethod
    def _setup_layout(self) -> None:
        """Setup the layout structure."""
        pass
    
    @abstractmethod
    def update_display(self) -> None:
        """Update the display with current state."""
        pass
    
    @abstractmethod
    def get_layout_name(self) -> str:
        """Get the name of this layout."""
        pass
    
    def set_scan_active(self, active: bool) -> None:
        """Set scan active state."""
        self.scan_active = active
        self.update_display()
    
    def get_layout(self) -> Layout:
        """Get the Rich Layout object."""
        return self.layout
    
    def get_progress_stats(self) -> Dict[str, Any]:
        """Get current progress statistics."""
        stats = self.plugin_tracker.stats
        progress_pct = self.plugin_tracker.progress_percentage
        elapsed = self.plugin_tracker.get_formatted_elapsed_time()
        
        return {
            "percentage": progress_pct,
            "completed": stats["completed"],
            "failed": stats["failed"],
            "active": stats["active"],
            "queued": stats["queued"],
            "total": stats["total"],
            "elapsed": elapsed
        }