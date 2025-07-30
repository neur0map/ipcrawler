"""Workspace List Command

Command to list available IPCrawler workspaces.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from ..orchestrator import reporting_orchestrator
from ...ui.console import console


class WorkspaceListCommand:
    """Command to list available workspaces"""
    
    def __init__(self):
        """Initialize workspace list command"""
        self.orchestrator = reporting_orchestrator
    
    def execute(self, target: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> bool:
        """Execute workspace listing
        
        Args:
            target: Optional target filter
            options: Command options
            
        Returns:
            True if successful
        """
        options = options or {}
        show_details = options.get('details', False)
        
        try:
            workspaces = self.orchestrator.list_workspaces(target)
            
            if not workspaces:
                if target:
                    console.print(f"No workspaces found for target: {target}")
                else:
                    console.print("No workspaces found")
                return True
            
            # Show header
            if target:
                console.print(f"\nWorkspaces for {target}:")
            else:
                console.print("\nAvailable workspaces:")
            
            # Group by target
            targets = {}
            for workspace in workspaces:
                if workspace.target not in targets:
                    targets[workspace.target] = []
                targets[workspace.target].append(workspace)
            
            # Display workspaces
            for target_name, target_workspaces in sorted(targets.items()):
                console.print(f"\n[bold]{target_name}[/bold]")
                
                # Sort by timestamp (newest first)
                target_workspaces.sort(
                    key=lambda w: w.created if w.created else datetime.min, 
                    reverse=True
                )
                
                for workspace in target_workspaces:
                    self._print_workspace_info(workspace, show_details)
            
            # Show summary
            console.print(f"\nTotal: {len(workspaces)} workspace(s)")
            
            return True
            
        except Exception as e:
            console.error(f"Error listing workspaces: {e}")
            return False
    
    def _print_workspace_info(self, workspace, show_details=False):
        """Print information about a single workspace
        
        Args:
            workspace: WorkspaceInfo object
            show_details: Whether to show detailed info
        """
        # Format timestamp
        if workspace.created:
            timestamp_str = workspace.created.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp_str = "No timestamp"
        
        # Format size
        size_mb = workspace.size / (1024 * 1024)
        
        # Basic info
        console.print(f"  • {workspace.name} [{timestamp_str}] ({size_mb:.1f} MB)")
        
        if show_details:
            console.print(f"    Files: {workspace.file_count}")
            console.print(f"    Path: {workspace.path}")
            
            # Check for reports
            if workspace.path.exists():
                reports = self._check_available_reports(workspace.path)
                if reports:
                    console.print(f"    Reports: {', '.join(reports)}")
    
    def _check_available_reports(self, workspace_path: Path):
        """Check what reports are available in workspace
        
        Args:
            workspace_path: Path to workspace
            
        Returns:
            List of available report types
        """
        reports = []
        
        # Check for new report structure
        if (workspace_path / "reports").exists():
            report_dir = workspace_path / "reports"
            if (report_dir / "summary.txt").exists():
                reports.append("summary")
            if (report_dir / "services.txt").exists():
                reports.append("services")
            if (report_dir / "web_analysis.txt").exists():
                reports.append("web")
            if (report_dir / "wordlist_recommendations.txt").exists():
                reports.append("wordlists")
        
        # Check for workflow results
        workflow_files = [
            "nmap_fast_01_results.json",
            "nmap_02_results.json",
            "http_03_results.json", 
            "mini_spider_04_results.json",
            "smartlist_05_results.json"
        ]
        
        workflow_count = sum(1 for f in workflow_files if (workspace_path / f).exists())
        if workflow_count > 0:
            reports.append(f"{workflow_count} workflows")
        
        return reports
    
    @staticmethod
    def get_help():
        """Get command help text
        
        Returns:
            Help text for the command
        """
        return """List available IPCrawler workspaces
        
Usage:
  ipcrawler report list-workspaces [--target=<target>] [--details]

Options:
  --target=<target>    Filter by target name
  --details           Show detailed information

Examples:
  ipcrawler report list-workspaces
  ipcrawler report list-workspaces --target=google_com
  ipcrawler report list-workspaces --details
"""