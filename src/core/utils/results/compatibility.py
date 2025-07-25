"""Compatibility layer for legacy result management

Provides backward compatibility with existing utils/results.py usage
while redirecting to the centralized reporting system.
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
from enum import Enum

from ...reporting.manager import report_manager
from ...ui.console.base import console


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects and enums."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            # Handle any enum type by returning its value
            return obj.value
        elif hasattr(obj, 'model_dump'):
            # Handle Pydantic models
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            # Handle objects with __dict__ (fallback)
            return {key: value for key, value in obj.__dict__.items() 
                   if not key.startswith('_')}
        return super().default(obj)


class BaseFormatter(ABC):
    """Abstract base class for result formatters."""
    
    @abstractmethod
    def format(self, target: str, data: Dict) -> str:
        """Format scan data into the specific output format."""
        pass


class JSONFormatter(BaseFormatter):
    """Formats scan results as JSON."""
    
    def format(self, target: str, data: Dict) -> str:
        """Format scan data as JSON string."""
        return json.dumps(data, indent=2, cls=DateTimeJSONEncoder)


class TextFormatter(BaseFormatter):
    """Formats scan results as human-readable text report."""
    
    def format(self, target: str, data: Dict) -> str:
        """Generate detailed text report."""
        # Use the centralized text reporter
        from ...reporting.formats.text_reporter import TextReporter
        temp_reporter = TextReporter(Path.cwd())
        return temp_reporter._format_text_report(target, data)


class HTMLFormatter(BaseFormatter):
    """Formats scan results as HTML report."""
    
    def format(self, target: str, data: Dict) -> str:
        """Generate HTML report with inline CSS."""
        from ...reporting.formats.html_reporter import HTMLReporter
        temp_reporter = HTMLReporter(Path.cwd())
        return temp_reporter._format_html_content(target, data)


class ResultManager:
    """Legacy compatibility class that redirects to centralized reporting."""
    
    def __init__(self):
        self.formatters = {
            'json': JSONFormatter(),
            'txt': TextFormatter(),
            'html': HTMLFormatter()
        }
    
    @staticmethod
    def create_workspace(target: str) -> Path:
        """Create workspace directory for scan results."""
        # Sanitize target name for directory usage
        clean_target = ResultManager._sanitize_target_name(target)
        
        # Use clean target name without timestamp
        base_path = Path("workspaces")
        workspace_path = base_path / clean_target
        
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # If running as sudo, change ownership to the real user
        if os.geteuid() == 0:  # Running as root
            # Get the real user ID from SUDO_UID environment variable
            sudo_uid = os.environ.get('SUDO_UID')
            sudo_gid = os.environ.get('SUDO_GID')
            
            if sudo_uid and sudo_gid:
                # Change ownership of workspaces directory and all subdirectories
                subprocess.run(['chown', '-R', f'{sudo_uid}:{sudo_gid}', str(base_path)], 
                              capture_output=True, check=False)
        
        return workspace_path
    
    @staticmethod
    def _sanitize_target_name(target: str) -> str:
        """Sanitize target name for use as directory name, preserving dots for IPs"""
        import re
        # Replace only truly invalid filesystem characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', target)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it's not empty and not too long
        if not sanitized:
            sanitized = 'unknown_target'
        elif len(sanitized) > 50:
            sanitized = sanitized[:50].rstrip('_')
        return sanitized
    
    @staticmethod
    def finalize_scan_data(data: Dict) -> Dict:
        """Finalize scan data by sorting ports and removing internal indexes."""
        # Sort ports for each host
        for host in data.get("hosts", []):
            if "ports" in host and host["ports"]:
                host["ports"].sort(key=lambda p: p.get("port", 0))
        
        # Remove internal index
        if "hosts_index" in data:
            del data["hosts_index"]
        
        return data
    
    def save_results(self, workspace: Path, target: str, data: Dict, 
                    formats: Optional[List[str]] = None, workflow: str = None) -> None:
        """Save scan results using centralized reporting system with workflow organization."""
        console.debug(f"Save results called - Workspace: {workspace}, Target: {target}, Workflow: {workflow}")
        
        # Default to all formats if none specified
        if formats is None:
            formats = ['json', 'txt', 'html']
        
        # Finalize data before saving
        data = self.finalize_scan_data(data)
        
        try:
            # Set the output directory to workspace before generating
            original_output_dir = report_manager.output_dir
            report_manager.set_output_directory(workspace)
            
            try:
                # Use workflow-specific directory structure
                if workflow:
                    workflow_dir = workspace / workflow
                    workflow_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Temporarily set reporters to use workflow directory
                    original_dirs = {}
                    for fmt, reporter in report_manager.reporters.items():
                        original_dirs[fmt] = reporter.output_dir
                        reporter.output_dir = workflow_dir
                    
                    try:
                        # Generate reports directly in workflow directory
                        results = report_manager.generate_report(
                            data=data,
                            formats=formats,
                            target=target,
                            workflow=workflow
                        )
                    finally:
                        # Restore original directories
                        for fmt, reporter in report_manager.reporters.items():
                            reporter.output_dir = original_dirs[fmt]
                else:
                    # Use legacy workspace reports structure
                    results = report_manager.generate_workspace_reports(
                        workspace_dir=workspace,
                        data=data,
                        formats=formats,
                        target=target
                    )
            finally:
                # Always restore original output directory
                report_manager.set_output_directory(original_output_dir)
            
            console.success(f"Generated {len(results)} report files using centralized system", internal=True)
            
            # Fix file permissions if running as sudo
            if os.geteuid() == 0:  # Running as root
                sudo_uid = os.environ.get('SUDO_UID')
                sudo_gid = os.environ.get('SUDO_GID')
                
                if sudo_uid and sudo_gid:
                    console.debug(f"Fixing permissions for sudo user {sudo_uid}:{sudo_gid}")
                    # Change ownership of all created files
                    for file in results.values():
                        try:
                            result = subprocess.run(['chown', f'{sudo_uid}:{sudo_gid}', str(file)], 
                                          capture_output=True, check=False)
                            if result.returncode != 0:
                                console.warning(f"chown failed for {file}: {result.stderr}", internal=True)
                        except Exception as e:
                            console.error(f"Permission fix failed for {file}: {e}", internal=True)
                else:
                    console.debug("No SUDO_UID/SUDO_GID found, skipping permission fix")
            else:
                console.debug("Not running as root, no permission fix needed")
                
        except Exception as e:
            console.error(f"Centralized reporting failed, falling back to legacy method: {e}", internal=True)
            self._legacy_save_results(workspace, target, data, formats)
    
    def _legacy_save_results(self, workspace: Path, target: str, data: Dict, 
                           formats: List[str]) -> None:
        """Fallback to legacy save method if centralized system fails."""
        console.warning("Using legacy save_results method as fallback", internal=True)
        
        # Determine file prefix
        prefix = "scan_"
        
        # Save in each requested format
        files_created = []
        for fmt in formats:
            if fmt not in self.formatters:
                console.warning(f"Unknown format: {fmt}", internal=True)
                continue
            
            # Determine filename
            if fmt == 'json':
                filename = f"{prefix}results.json"
            elif fmt == 'txt':
                filename = f"{prefix}report.txt"
            elif fmt == 'html':
                filename = f"{prefix}report.html"
            else:
                console.warning(f"Unhandled format: {fmt}", internal=True)
                continue
            
            filepath = workspace / filename
            console.debug(f"Creating {fmt}: {filepath}")
            
            try:
                # Format data
                formatted_content = self.formatters[fmt].format(target, data)
                
                # Write file with UTF-8 encoding
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)
                
                files_created.append(filepath)
                console.success(f"Successfully created: {filepath}", internal=True)
                
            except Exception as e:
                console.error(f"Failed to create {fmt} file: {e}", internal=True)
        
        console.info(f"Legacy method created {len(files_created)} files", internal=True)
    
    async def save_results_async(self, workspace: Path, target: str, data: Dict, 
                               formats: Optional[List[str]] = None) -> None:
        """Asynchronously save scan results (wrapper for compatibility)."""
        # For now, just call the sync version
        # This can be enhanced later to use true async I/O if needed
        self.save_results(workspace, target, data, formats)


# Global instance for compatibility
result_manager_compat = ResultManager()