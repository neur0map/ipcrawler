"""Workspace Cleanup Command

Command to clean up old IPCrawler workspaces.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import shutil

from ..orchestrator import reporting_orchestrator
from ...ui.console import console


class WorkspaceCleanCommand:
    """Command to clean up old workspaces"""
    
    def __init__(self):
        """Initialize workspace clean command"""
        self.orchestrator = reporting_orchestrator
    
    def execute(self, target: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> bool:
        """Execute workspace cleanup
        
        Args:
            target: Optional target to clean (None = all targets)
            options: Command options
            
        Returns:
            True if successful
        """
        options = options or {}
        keep_count = options.get('keep_count', 5)
        dry_run = options.get('dry_run', False)
        
        try:
            if target:
                # Clean specific target
                return self._clean_target(target, keep_count, dry_run)
            else:
                # Clean all targets
                return self._clean_all_targets(keep_count, dry_run)
                
        except Exception as e:
            console.error(f"Error during cleanup: {e}")
            return False
    
    def _clean_target(self, target: str, keep_count: int, dry_run: bool) -> bool:
        """Clean workspaces for a specific target
        
        Args:
            target: Target name
            keep_count: Number of workspaces to keep
            dry_run: If True, only show what would be deleted
            
        Returns:
            True if successful
        """
        console.print(f"\nCleaning workspaces for: {target}")
        
        workspaces = self.orchestrator.list_workspaces(target)
        
        if len(workspaces) <= keep_count:
            console.print(f"   ✅ No cleanup needed ({len(workspaces)} workspaces <= {keep_count})")
            return True
        
        # Show what will be removed
        to_remove = workspaces[keep_count:]
        console.print(f"   Will remove {len(to_remove)} workspace(s):")
        
        total_size = 0
        for workspace in to_remove:
            timestamp_str = workspace.created.strftime("%Y-%m-%d %H:%M:%S") if workspace.created else "Unknown"
            size_mb = workspace.size / (1024 * 1024)
            total_size += workspace.size
            console.print(f"     • {workspace.name} [{timestamp_str}] ({size_mb:.1f} MB)")
        
        if dry_run:
            console.print("\n   [DRY RUN] No files were deleted")
            return True
        
        # Confirm removal
        confirm = console.input(f"\nRemove {len(to_remove)} workspace(s)? [y/N]: ").lower().strip()
        if confirm != 'y':
            console.print("   Cancelled")
            return True
        
        # Perform cleanup
        removed_paths = self.orchestrator.clean_old_workspaces(target, keep_count)
        
        if removed_paths:
            console.success(f"   Removed {len(removed_paths)} workspace(s)")
            console.print(f"   Freed {total_size / (1024 * 1024):.1f} MB")
        
        return True
    
    def _clean_all_targets(self, keep_count: int, dry_run: bool) -> bool:
        """Clean workspaces for all targets
        
        Args:
            keep_count: Number of workspaces to keep per target
            dry_run: If True, only show what would be deleted
            
        Returns:
            True if successful
        """
        console.print("\nCleaning workspaces for all targets...")
        
        # Get all unique targets
        all_workspaces = self.orchestrator.list_workspaces()
        targets = set(w.target for w in all_workspaces)
        
        if not targets:
            console.print("   No workspaces found")
            return True
        
        console.print(f"   Found {len(targets)} target(s)")
        
        total_to_remove = 0
        total_size = 0
        cleanup_plan = {}
        
        for target in sorted(targets):
            target_workspaces = [w for w in all_workspaces if w.target == target]
            
            if len(target_workspaces) > keep_count:
                to_remove = target_workspaces[keep_count:]
                cleanup_plan[target] = to_remove
                total_to_remove += len(to_remove)
                total_size += sum(w.size for w in to_remove)
        
        if total_to_remove == 0:
            console.print("   ✅ No cleanup needed")
            return True
        
        # Show cleanup plan
        console.print(f"\n   Will remove {total_to_remove} workspace(s) across {len(cleanup_plan)} target(s):")
        for target, workspaces in cleanup_plan.items():
            console.print(f"\n   {target}: {len(workspaces)} workspace(s)")
            for workspace in workspaces[:2]:  # Show first 2
                timestamp_str = workspace.created.strftime("%Y-%m-%d %H:%M") if workspace.created else "Unknown"
                console.print(f"     • {workspace.name} [{timestamp_str}]")
            if len(workspaces) > 2:
                console.print(f"     ... and {len(workspaces) - 2} more")
        
        console.print(f"\n   Total space to free: {total_size / (1024 * 1024):.1f} MB")
        
        if dry_run:
            console.print("\n   [DRY RUN] No files were deleted")
            return True
        
        # Confirm removal
        confirm = console.input(f"\nRemove {total_to_remove} workspace(s) across {len(cleanup_plan)} target(s)? [y/N]: ").lower().strip()
        if confirm != 'y':
            console.print("   Cancelled")
            return True
        
        # Perform cleanup for each target
        total_removed = 0
        for target in cleanup_plan:
            removed_paths = self.orchestrator.clean_old_workspaces(target, keep_count)
            total_removed += len(removed_paths)
        
        console.success(f"   Removed {total_removed} workspace(s)")
        console.print(f"   Freed {total_size / (1024 * 1024):.1f} MB")
        
        return True
    
    @staticmethod
    def get_help():
        """Get command help text
        
        Returns:
            Help text for the command
        """
        return """Clean up old IPCrawler workspaces
        
Usage:
  ipcrawler report clean-workspaces [--target=<target>] [--keep=<count>] [--dry-run]

Options:
  --target=<target>    Clean only specified target
  --keep=<count>      Number of workspaces to keep per target (default: 5)
  --dry-run           Show what would be removed without deleting

Examples:
  ipcrawler report clean-workspaces --target=google_com --keep=3
  ipcrawler report clean-workspaces --keep=10
  ipcrawler report clean-workspaces --dry-run
"""