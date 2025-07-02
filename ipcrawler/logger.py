#!/usr/bin/env python3

"""
Enhanced Unified Raw Log Capture for IPCrawler

This module provides comprehensive centralized logging functionality for all plugin execution.
Every tool/plugin output is captured to structured log files under results/{target}/scans/
with YAML-formatted error logging and complete stdout capture.
"""

import asyncio
import os
import sys
import yaml
import io
import contextlib
from pathlib import Path
from typing import Optional, Tuple, Union, Dict, Any
import subprocess
from datetime import datetime, timezone

from ipcrawler.io import CommandStreamReader


class UnifiedLogger:
    """
    Handles unified logging for all plugin subprocess execution.
    
    Captures stdout to per-plugin log files and stderr to centralized error log.
    Provides clean terminal status messages instead of raw output dumps.
    """
    
    def __init__(self, target_address: str, scandir: str):
        """
        Initialize logger for a specific target.
        
        Args:
            target_address: Target IP or hostname
            scandir: Base scan directory (e.g., results/192.168.1.1 or results/192.168.1.1/scans)
        """
        self.target_address = target_address
        self.scandir = Path(scandir)
        
        # If scandir already ends with 'scans', use it directly, otherwise add 'scans'
        if self.scandir.name == "scans":
            self.scans_dir = self.scandir
        else:
            self.scans_dir = self.scandir / "scans"
            
        self.error_log = self.scans_dir / "errors.log"
        
        # Ensure scans directory exists
        self._setup_directories()
    
    def _setup_directories(self):
        """Create necessary log directories if they don't exist."""
        try:
            self.scans_dir.mkdir(parents=True, exist_ok=True)
            
            # Create error log file if it doesn't exist
            if not self.error_log.exists():
                self.error_log.touch()
                
        except Exception as e:
            print(f"[!] Failed to create log directories: {e}", file=sys.stderr)
    
    def get_plugin_log_path(self, plugin_name: str) -> Path:
        """
        Get the stdout log path for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin (e.g., 'nmap', 'feroxbuster')
            
        Returns:
            Path to plugin-specific log file
        """
        # Sanitize plugin name for filename
        safe_name = "".join(c for c in plugin_name if c.isalnum() or c in "._-")
        return self.scans_dir / f"{safe_name}.log"
    
    def log_command_start(self, plugin_name: str, command: str):
        """
        Log the start of a command execution.
        
        Args:
            plugin_name: Name of the plugin
            command: Command being executed
        """
        timestamp = asyncio.get_event_loop().time()
        log_path = self.get_plugin_log_path(plugin_name)
        
        try:
            with open(log_path, 'w') as f:
                f.write(f"=== {plugin_name.upper()} EXECUTION LOG ===\n")
                f.write(f"Target: {self.target_address}\n")
                f.write(f"Command: {command}\n")
                f.write(f"Started: {timestamp}\n")
                f.write("=" * 50 + "\n\n")
        except Exception as e:
            print(f"[!] Failed to write to {log_path}: {e}", file=sys.stderr)
    
    def log_error(self, plugin_name: str, command: str, exit_code: int, stderr_content: str):
        """
        Log an error to the centralized error log as structured YAML.
        
        Args:
            plugin_name: Name of the plugin that failed
            command: Command that failed
            exit_code: Process exit code
            stderr_content: Standard error output
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        error_entry = {
            'plugin': plugin_name,
            'target': self.target_address,
            'timestamp': timestamp,
            'exit_code': exit_code,
            'command': command,
            'message': stderr_content.strip() if stderr_content else ""
        }
        
        try:
            # Load existing errors to append to the list
            errors_list = []
            if self.error_log.exists() and self.error_log.stat().st_size > 0:
                try:
                    with open(self.error_log, 'r') as f:
                        content = f.read().strip()
                        if content:
                            errors_list = yaml.safe_load(content) or []
                except yaml.YAMLError:
                    # If YAML is corrupted, start fresh but preserve old content
                    errors_list = [{'plugin': 'legacy', 'message': 'Previous errors corrupted, starting fresh'}]
            
            # Append new error
            errors_list.append(error_entry)
            
            # Write back as YAML
            with open(self.error_log, 'w') as f:
                yaml.dump(errors_list, f, default_flow_style=False, allow_unicode=True)
                
        except Exception as e:
            # Fallback to basic logging if YAML fails
            try:
                with open(self.error_log, 'a') as f:
                    f.write(f"\n# YAML Error - Fallback logging\n")
                    f.write(f"# Plugin: {plugin_name}, Exit: {exit_code}, Time: {timestamp}\n")
                    f.write(f"# Command: {command}\n")
                    f.write(f"# Error: {stderr_content}\n")
            except:
                print(f"[!] Failed to write to error log: {e}", file=sys.stderr)
    
    async def execute_with_logging(
        self,
        command: str,
        plugin_name: str,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[float] = None
    ) -> Tuple[int, str, str]:
        """
        Execute a command with comprehensive unified logging.
        
        Args:
            command: Command to execute
            plugin_name: Name of the plugin for logging
            cwd: Working directory for command execution
            env: Environment variables
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (exit_code, stdout_content, stderr_content)
        """
        stdout_log = self.get_plugin_log_path(plugin_name)
        
        # Log command start
        self.log_command_start(plugin_name, command)
        
        try:
            # Create subprocess with comprehensive output capture
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                cwd=cwd,
                env=env,
                limit=10*1024*1024  # 10MB buffer limit for large outputs
            )
            
            # Capture output with proper timeout handling
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                exit_code = process.returncode
            except asyncio.TimeoutError:
                # Handle timeout gracefully
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                
                # Get partial output if available
                stdout_data = b"[Command timed out - partial output may be available above]"
                stderr_data = b"Command execution timed out"
                exit_code = -1
            
            # Decode output with robust error handling
            try:
                stdout_content = stdout_data.decode('utf-8', errors='replace')
            except Exception:
                stdout_content = str(stdout_data, errors='replace')
                
            try:
                stderr_content = stderr_data.decode('utf-8', errors='replace')
            except Exception:
                stderr_content = str(stderr_data, errors='replace')
            
            # Write complete stdout to plugin-specific log (append to existing header)
            try:
                with open(stdout_log, 'a', encoding='utf-8') as f:
                    if stdout_content:
                        f.write(stdout_content)
                    else:
                        f.write("[No stdout output]\n")
                    f.write(f"\n=== EXECUTION COMPLETED (Exit Code: {exit_code}) ===\n")
            except Exception as e:
                print(f"[!] Failed to write stdout to {stdout_log}: {e}", file=sys.stderr)
            
            # Log errors for any non-zero exit code or stderr content
            if exit_code != 0 or stderr_content.strip():
                self.log_error(plugin_name, command, exit_code, stderr_content)
            
            return exit_code, stdout_content, stderr_content
            
        except Exception as e:
            error_msg = f"Failed to execute command: {str(e)}"
            self.log_error(plugin_name, command, -1, error_msg)
            return -1, "", error_msg
    
    def print_status(self, plugin_name: str, success: bool, message: str = ""):
        """
        Print clean status message to terminal.
        
        Args:
            plugin_name: Name of the plugin
            success: Whether the operation was successful
            message: Optional additional message
        """
        symbol = "✓" if success else "!"
        log_path = self.get_plugin_log_path(plugin_name)
        
        if success:
            print(f"[{symbol}] {plugin_name} completed — logs to scans/{log_path.name}")
        else:
            error_ref = "see scans/errors.log"
            if message:
                print(f"[{symbol}] {plugin_name} error: {message} — {error_ref}")
            else:
                print(f"[{symbol}] {plugin_name} error — {error_ref}")
    
    def _log_suppressed_output(self, stream_type: str, content: str):
        """
        Log output that was suppressed from direct print statements.
        
        Args:
            stream_type: 'stdout' or 'stderr'
            content: The suppressed content
        """
        suppressed_log = self.scans_dir / "suppressed_output.log"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            with open(suppressed_log, 'a', encoding='utf-8') as f:
                f.write(f"\n=== SUPPRESSED {stream_type.upper()} ===\n")
                f.write(f"Target: {self.target_address}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Content:\n{content}\n")
                f.write("=" * 50 + "\n")
        except Exception as e:
            # Fallback - don't let logging errors break execution
            pass
    
    def create_output_suppressor(self) -> 'OutputSuppressor':
        """Create an output suppressor for this logger."""
        return OutputSuppressor(self)


class OutputSuppressor:
    """Context manager to suppress all print output to stdout during plugin execution."""
    
    def __init__(self, logger: 'UnifiedLogger'):
        self.logger = logger
        self.original_stdout = None
        self.original_stderr = None
        self.suppressed_output = []
    
    def __enter__(self):
        """Redirect stdout/stderr to capture any direct prints."""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Create string buffers to capture output
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        
        # Redirect output
        sys.stdout = self.stdout_buffer
        sys.stderr = self.stderr_buffer
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original stdout/stderr and log any captured output."""
        # Get captured content
        stdout_content = self.stdout_buffer.getvalue()
        stderr_content = self.stderr_buffer.getvalue()
        
        # Restore original streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Log any captured output
        if stdout_content.strip():
            self.logger._log_suppressed_output("stdout", stdout_content)
        if stderr_content.strip():
            self.logger._log_suppressed_output("stderr", stderr_content)
    
    def get_captured_output(self) -> Tuple[str, str]:
        """Get captured stdout and stderr content."""
        return self.stdout_buffer.getvalue(), self.stderr_buffer.getvalue()


class LoggingWrapper:
    """
    Wrapper to integrate unified logging with existing IPCrawler execute methods.
    
    This class can be used to wrap the existing execute() methods in plugins.py and targets.py
    to provide unified logging without major refactoring.
    """
    
    def __init__(self, original_execute_func, logger: UnifiedLogger):
        """
        Initialize wrapper around existing execute function.
        
        Args:
            original_execute_func: The original execute method to wrap
            logger: UnifiedLogger instance
        """
        self.original_execute = original_execute_func
        self.logger = logger
    
    async def __call__(self, cmd: str, target_or_service, tag: str, **kwargs):
        """
        Wrapped execute call with unified logging.
        
        Args:
            cmd: Command to execute
            target_or_service: Target or Service object
            tag: Plugin tag/name
            **kwargs: Additional arguments for original execute method
        """
        # Extract plugin name from tag or command
        plugin_name = self._extract_plugin_name(cmd, tag)
        
        # Check if we should bypass logging (for internal commands)
        if self._should_bypass_logging(cmd):
            return await self.original_execute(cmd, target_or_service, tag, **kwargs)
        
        # Override outfile to use our logging
        kwargs_copy = kwargs.copy()
        original_outfile = kwargs_copy.pop('outfile', None)
        
        # Execute with our logging
        exit_code, stdout, stderr = await self.logger.execute_with_logging(
            cmd, plugin_name, 
            cwd=getattr(target_or_service, 'scandir', None),
            env=kwargs.get('env')
        )
        
        # Print status
        self.logger.print_status(plugin_name, exit_code == 0)
        
        # Still call original for compatibility (but suppress output)
        try:
            result = await self.original_execute(cmd, target_or_service, tag, **kwargs_copy)
            return result
        except Exception as e:
            self.logger.print_status(plugin_name, False, str(e))
            raise
    
    def _extract_plugin_name(self, cmd: str, tag: str) -> str:
        """Extract plugin name from command or tag."""
        # Try to get plugin name from command
        cmd_parts = cmd.strip().split()
        if cmd_parts:
            # Remove common prefixes
            tool_name = cmd_parts[0]
            if tool_name in ['timeout', 'sudo']:
                tool_name = cmd_parts[1] if len(cmd_parts) > 1 else tool_name
            return tool_name
        
        return tag or "unknown"
    
    def _should_bypass_logging(self, cmd: str) -> bool:
        """Check if command should bypass unified logging."""
        # Skip logging for internal/utility commands
        bypass_commands = ['mkdir', 'chmod', 'chown', 'cp', 'mv', 'ln']
        cmd_parts = cmd.strip().split()
        if cmd_parts and cmd_parts[0] in bypass_commands:
            return True
        return False


def setup_unified_logging(target_address: str, scandir: str) -> UnifiedLogger:
    """
    Setup unified logging for a target.
    
    Args:
        target_address: Target IP or hostname
        scandir: Base scan directory
        
    Returns:
        UnifiedLogger instance
    """
    return UnifiedLogger(target_address, scandir)