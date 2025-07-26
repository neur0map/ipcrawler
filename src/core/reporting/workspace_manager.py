"""Enhanced Workspace Management for IPCrawler"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from ..utils.target_sanitizer import sanitize_target


@dataclass
class WorkspaceInfo:
    """Information about a workspace"""
    name: str
    path: Path
    target: str
    created: datetime
    size: int
    file_count: int


class WorkspaceManager:
    """Centralized workspace management for IPCrawler"""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize workspace manager"""
        self.base_path = Path(base_path) if base_path else Path("workspaces")
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def create_workspace(self, target: str, enable_versioning: bool = True) -> Path:
        """Create a new workspace for a target with optional versioning"""
        clean_target = self._clean_target_name(target)
        
        if enable_versioning:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workspace_name = f"{clean_target}_{timestamp}"
        else:
            workspace_name = clean_target
        
        workspace_path = self.base_path / workspace_name
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Create latest symlink if versioning is enabled
        if enable_versioning:
            latest_link = self.base_path / f"{clean_target}_latest"
            
            # Handle existing latest link or directory
            if latest_link.exists():
                if latest_link.is_symlink():
                    # Remove existing symlink
                    latest_link.unlink()
                elif latest_link.is_dir():
                    # If it's a regular directory created by individual workflows,
                    # we need to remove it to avoid conflicts
                    import shutil
                    shutil.rmtree(latest_link)
                else:
                    # Remove any other type of file
                    latest_link.unlink()
            elif latest_link.is_symlink():
                # Handle broken symlinks
                latest_link.unlink()
                
            latest_link.symlink_to(workspace_name)
        
        return workspace_path
    
    def get_workspace_path(self, workspace_name: str) -> Path:
        """Get path to a specific workspace"""
        return self.base_path / workspace_name
    
    def list_workspaces(self, target: Optional[str] = None) -> List[WorkspaceInfo]:
        """List all workspaces, optionally filtered by target"""
        workspaces = []
        
        for workspace_dir in self.base_path.iterdir():
            if not workspace_dir.is_dir() or workspace_dir.name.endswith('_latest'):
                continue
            
            workspace_info = self._get_workspace_info(workspace_dir)
            if target is None or workspace_info.target == target:
                workspaces.append(workspace_info)
        
        return sorted(workspaces, key=lambda x: x.created, reverse=True)
    
    def clean_old_workspaces(self, target: str, keep_count: int = 5) -> List[Path]:
        """Clean old workspaces for a target, keeping only the most recent ones"""
        target_workspaces = self.list_workspaces(target)
        
        if len(target_workspaces) <= keep_count:
            return []
        
        workspaces_to_remove = target_workspaces[keep_count:]
        removed_paths = []
        
        for workspace in workspaces_to_remove:
            try:
                shutil.rmtree(workspace.path)
                removed_paths.append(workspace.path)
            except Exception:
                continue
        
        return removed_paths
    
    def get_latest_workspace(self, target: str) -> Optional[Path]:
        """Get the latest workspace for a target"""
        clean_target = self._clean_target_name(target)
        latest_link = self.base_path / f"{clean_target}_latest"
        
        if latest_link.exists() and latest_link.is_symlink():
            return latest_link.resolve()
        
        # Fallback: find the most recent workspace
        target_workspaces = self.list_workspaces(target)
        if target_workspaces:
            return target_workspaces[0].path
        
        return None
    
    def _clean_target_name(self, target: str) -> str:
        """Clean target name for use in filesystem paths"""
        import re
        
        # Replace problematic characters
        clean_name = sanitize_target(target)
        
        # Check if it's an IP address pattern and preserve dots
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if re.match(ip_pattern, clean_name):
            # For IP addresses, keep dots and only allow digits, dots, underscores, and hyphens
            clean_name = ''.join(c for c in clean_name if c.isdigit() or c in '._-')
        else:
            # For other targets, remove dots as they could cause issues
            clean_name = ''.join(c for c in clean_name if c.isalnum() or c in '_-')
        
        return clean_name[:50]  # Limit length
    
    def _get_workspace_info(self, workspace_path: Path) -> WorkspaceInfo:
        """Get information about a workspace"""
        # Extract target from workspace name
        workspace_name = workspace_path.name
        if '_' in workspace_name:
            target = workspace_name.split('_')[0]
        else:
            target = workspace_name
        
        # Get creation time and size
        try:
            stat = workspace_path.stat()
            created = datetime.fromtimestamp(stat.st_ctime)
            
            # Calculate size and file count
            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(workspace_path):
                file_count += len(files)
                for file in files:
                    try:
                        total_size += os.path.getsize(os.path.join(root, file))
                    except (OSError, IOError):
                        continue
        
        except (OSError, IOError):
            created = datetime.now()
            total_size = 0
            file_count = 0
        
        return WorkspaceInfo(
            name=workspace_name,
            path=workspace_path,
            target=target,
            created=created,
            size=total_size,
            file_count=file_count
        )


# Global workspace manager instance
workspace_manager = WorkspaceManager()