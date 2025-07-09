"""
Plugin state tracking for Rich TUI display.
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass


class PluginState(Enum):
    """Plugin execution states."""
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PluginInfo:
    """Plugin information and state."""
    name: str
    tool: str
    state: PluginState
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get execution duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_running(self) -> bool:
        """Check if plugin is currently running."""
        return self.state == PluginState.ACTIVE
    
    @property
    def is_finished(self) -> bool:
        """Check if plugin has finished (success or failure)."""
        return self.state in (PluginState.COMPLETED, PluginState.FAILED)


class PluginTracker:
    """Tracks plugin states and execution progress."""
    
    def __init__(self):
        self.plugins: Dict[str, PluginInfo] = {}
        self.scan_start_time: Optional[datetime] = None
        self.total_plugins: int = 0
        self.target: str = ""
        
        
    def initialize_scan(self, target: str, template_names: List[str], tools: List[str]) -> None:
        """Initialize scan with all plugins."""
        self.target = target
        # Only set scan_start_time if not already set
        if not self.scan_start_time:
            self.scan_start_time = datetime.now()
        self.total_plugins = len(template_names)
        self.plugins = {}
        
        # Initialize all plugins as queued
        for name, tool in zip(template_names, tools):
            self.plugins[name] = PluginInfo(
                name=name,
                tool=tool,
                state=PluginState.QUEUED
            )
    
    def start_plugin(self, name: str) -> None:
        """Mark plugin as active."""
        if name in self.plugins:
            self.plugins[name].state = PluginState.ACTIVE
            self.plugins[name].start_time = datetime.now()
    
    def complete_plugin(self, name: str, success: bool = True, error: Optional[str] = None) -> None:
        """Mark plugin as completed or failed."""
        if name in self.plugins:
            self.plugins[name].state = PluginState.COMPLETED if success else PluginState.FAILED
            self.plugins[name].end_time = datetime.now()
            if error:
                self.plugins[name].error_message = error
    
    def get_plugins_by_state(self, state: PluginState) -> List[PluginInfo]:
        """Get all plugins in a specific state."""
        return [plugin for plugin in self.plugins.values() if plugin.state == state]
    
    def get_queued_plugins(self) -> List[PluginInfo]:
        """Get all queued plugins."""
        return self.get_plugins_by_state(PluginState.QUEUED)
    
    def get_active_plugins(self) -> List[PluginInfo]:
        """Get all active plugins."""
        return self.get_plugins_by_state(PluginState.ACTIVE)
    
    def get_completed_plugins(self) -> List[PluginInfo]:
        """Get all completed plugins."""
        return self.get_plugins_by_state(PluginState.COMPLETED)
    
    def get_failed_plugins(self) -> List[PluginInfo]:
        """Get all failed plugins."""
        return self.get_plugins_by_state(PluginState.FAILED)
    
    def get_finished_plugins(self) -> List[PluginInfo]:
        """Get all finished plugins (completed or failed)."""
        return [plugin for plugin in self.plugins.values() if plugin.is_finished]
    
    @property
    def progress_percentage(self) -> float:
        """Get overall progress percentage."""
        if self.total_plugins == 0:
            return 0.0
        finished = len(self.get_finished_plugins())
        return (finished / self.total_plugins) * 100
    
    @property
    def elapsed_time(self) -> timedelta:
        """Get elapsed time since scan started."""
        if self.scan_start_time:
            return datetime.now() - self.scan_start_time
        return timedelta(0)
    
    def get_formatted_elapsed_time(self) -> str:
        """Get formatted elapsed time."""
        elapsed = self.elapsed_time
        total_seconds = int(elapsed.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get current statistics."""
        return {
            "total": self.total_plugins,
            "queued": len(self.get_queued_plugins()),
            "active": len(self.get_active_plugins()),
            "completed": len(self.get_completed_plugins()),
            "failed": len(self.get_failed_plugins())
        }
    
    def get_plugin_names_by_state(self, state: PluginState) -> List[str]:
        """Get plugin names in a specific state."""
        return [plugin.name for plugin in self.get_plugins_by_state(state)]
    
    def get_tool_names_by_state(self, state: PluginState) -> List[str]:
        """Get tool names in a specific state."""
        return [plugin.tool for plugin in self.get_plugins_by_state(state)]
    
    def is_scan_complete(self) -> bool:
        """Check if scan is complete."""
        return len(self.get_finished_plugins()) == self.total_plugins
    
    def get_summary(self) -> Dict[str, any]:
        """Get scan summary."""
        stats = self.stats
        return {
            "target": self.target,
            "total_plugins": self.total_plugins,
            "completed": stats["completed"],
            "failed": stats["failed"],
            "success_rate": (stats["completed"] / self.total_plugins * 100) if self.total_plugins > 0 else 0,
            "elapsed_time": self.elapsed_time,
            "is_complete": self.is_scan_complete()
        }