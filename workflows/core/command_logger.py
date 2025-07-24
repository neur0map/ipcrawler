import os
import datetime
from pathlib import Path
from typing import Optional
import threading
from .exceptions import IPCrawlerError
from .error_collector import collect_error


class CommandLogger:
    """Logs all commands executed by workflows to a commands.txt file in workspaces"""
    
    def __init__(self, workspace_dir: str = "workspaces"):
        self.workspace_dir = Path(workspace_dir)
        self.commands_file = self.workspace_dir / "commands.txt"
        self._lock = threading.Lock()
        self._ensure_workspace_exists()
    
    def _ensure_workspace_exists(self):
        """Ensure the workspace directory exists"""
        try:
            self.workspace_dir.mkdir(exist_ok=True)
        except PermissionError:
            # If we can't create workspaces, use a temp directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "ipcrawler_workspaces"
            temp_dir.mkdir(exist_ok=True)
            self.workspace_dir = temp_dir
            self.commands_file = self.workspace_dir / "commands.txt"
    
    def log_command(self, 
                   workflow_name: str,
                   command: str, 
                   status: str = "started",
                   output: Optional[str] = None,
                   error: Optional[str] = None,
                   ipc_error: Optional[IPCrawlerError] = None):
        """
        Log a command execution with enhanced error integration
        
        Args:
            workflow_name: Name of the workflow executing the command
            command: The actual command being executed
            status: Command status (started, completed, failed)
            output: Command output (optional)
            error: Error message if command failed (optional)
            ipc_error: Structured IPCrawlerError for enhanced error tracking (optional)
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Collect structured error if provided
        occurrence_id = None
        if ipc_error and status.lower() == "failed":
            try:
                occurrence_id = collect_error(ipc_error)
            except Exception:
                # Don't let error collection break command logging
                pass
        
        with self._lock:
            try:
                with open(self.commands_file, "a", encoding="utf-8") as f:
                    # Status indicator with color-like symbols
                    status_symbol = {
                        "started": "⚡",
                        "completed": "✅", 
                        "failed": "❌"
                    }.get(status.lower(), "•")
                    
                    f.write(f"{status_symbol} [{timestamp}] {command}\n")
                    
                    if status.lower() == "completed" and output:
                        # Clean and format output - show FULL output for complete transparency
                        clean_output = output.strip()
                        f.write(f"   └─ Result: {clean_output}\n")
                    
                    if error:
                        f.write(f"   └─ ERROR: {error}\n")
                        
                        # Add structured error information if available
                        if ipc_error:
                            f.write(f"   └─ Error Code: {ipc_error.error_code}\n")
                            f.write(f"   └─ Category: {ipc_error.category.value}\n")
                            f.write(f"   └─ Severity: {ipc_error.severity.value}\n")
                            
                            if occurrence_id:
                                f.write(f"   └─ Error ID: {occurrence_id}\n")
                                
                            if ipc_error.suggestions:
                                f.write(f"   └─ Suggestions: {'; '.join(ipc_error.suggestions)}\n")
                    
                    f.write("\n")
            except (PermissionError, OSError):
                # Silently ignore logging errors in tests/restricted environments
                pass
    
    def log_workflow_start(self, workflow_name: str, target: Optional[str] = None):
        """Log when a workflow starts"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with self._lock:
            try:
                with open(self.commands_file, "a", encoding="utf-8") as f:
                    f.write(f"\n🚀 [{timestamp}] Starting {workflow_name.upper()} workflow")
                    if target:
                        f.write(f" → {target}")
                    f.write(f"\n{'─' * 60}\n")
            except (PermissionError, OSError):
                # Silently ignore logging errors in tests/restricted environments
                pass
    
    def log_workflow_end(self, workflow_name: str, success: bool, execution_time: Optional[float] = None):
        """Log when a workflow ends"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        status_symbol = "🎉" if success else "💥"
        status_text = "COMPLETED" if success else "FAILED"
        
        with self._lock:
            try:
                with open(self.commands_file, "a", encoding="utf-8") as f:
                    f.write(f"{status_symbol} [{timestamp}] {workflow_name.upper()} {status_text}")
                    if execution_time:
                        f.write(f" (took {execution_time:.1f}s)")
                    f.write(f"\n{'─' * 60}\n\n")
            except (PermissionError, OSError):
                # Silently ignore logging errors in tests/restricted environments
                pass
    
    def clear_log(self):
        """Clear the commands log file"""
        with self._lock:
            if self.commands_file.exists():
                self.commands_file.unlink()


# Global logger instance
_command_logger: Optional[CommandLogger] = None


def get_command_logger() -> CommandLogger:
    """Get the global command logger instance"""
    global _command_logger
    if _command_logger is None:
        _command_logger = CommandLogger()
    return _command_logger


def log_command(workflow_name: str, command: str, status: str = "started", 
                output: Optional[str] = None, error: Optional[str] = None,
                ipc_error: Optional[IPCrawlerError] = None):
    """Convenience function to log a command with enhanced error support"""
    logger = get_command_logger()
    logger.log_command(workflow_name, command, status, output, error, ipc_error)


def log_workflow_start(workflow_name: str, target: Optional[str] = None):
    """Convenience function to log workflow start"""
    logger = get_command_logger()
    logger.log_workflow_start(workflow_name, target)


def log_workflow_end(workflow_name: str, success: bool, execution_time: Optional[float] = None):
    """Convenience function to log workflow end"""
    logger = get_command_logger()
    logger.log_workflow_end(workflow_name, success, execution_time)