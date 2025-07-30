"""Master Report Generation Command

Command to generate comprehensive reports from workspace data.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from ..orchestrator import reporting_orchestrator
from ...ui.console import console


class MasterReportCommand:
    """Command to generate master reports from workspace data"""
    
    def __init__(self):
        """Initialize master report command"""
        self.orchestrator = reporting_orchestrator
    
    def execute(self, workspace_name: str, options: Optional[Dict[str, Any]] = None) -> Optional[Path]:
        """Execute master report generation
        
        Args:
            workspace_name: Name of workspace to generate report from
            options: Command options
            
        Returns:
            Path to generated report or None
        """
        options = options or {}
        
        console.info(f"Generating master report for workspace: {workspace_name}")
        
        # Check if workspace exists
        workspace_path = self.orchestrator.workspace_manager.get_workspace_path(workspace_name)
        
        if not workspace_path.exists():
            console.error(f"Workspace not found: {workspace_name}")
            self._show_available_workspaces()
            return None
        
        try:
            # Generate reports using new engine
            report_paths = self.orchestrator.generate_master_report_from_workspace(workspace_name)
            
            if report_paths:
                console.success(f"Generated {len(report_paths)} report files")
                
                # Show generated files
                for report_type, report_path in report_paths.items():
                    if report_path and report_path.exists():
                        file_size = report_path.stat().st_size
                        console.print(f"  • {report_type}: {report_path.name} ({file_size / 1024:.1f} KB)")
                
                return report_paths.get('summary')  # Return main report path
            else:
                console.error("Failed to generate reports")
                return None
                
        except Exception as e:
            console.error(f"Error generating report: {e}")
            return None
    
    def _show_available_workspaces(self):
        """Show available workspaces to help user"""
        console.print("\nAvailable workspaces:")
        
        workspaces = self.orchestrator.list_workspaces()
        if not workspaces:
            console.print("  No workspaces found")
            return
        
        # Group by target
        targets = {}
        for workspace in workspaces:
            if workspace.target not in targets:
                targets[workspace.target] = []
            targets[workspace.target].append(workspace)
        
        # Display grouped workspaces
        for target, target_workspaces in targets.items():
            console.print(f"\n  {target}:")
            for workspace in target_workspaces[:3]:  # Show max 3 per target
                timestamp = workspace.created.strftime('%Y-%m-%d %H:%M') if workspace.created else ""
                console.print(f"    • {workspace.name} [{timestamp}]")
            
            if len(target_workspaces) > 3:
                console.print(f"    ... and {len(target_workspaces) - 3} more")
        
        if workspaces:
            example_workspace = workspaces[0].name
            console.print(f"\nExample usage:")
            console.print(f"  ipcrawler report master-report --workspace={example_workspace}")
    
    @staticmethod
    def get_help():
        """Get command help text
        
        Returns:
            Help text for the command
        """
        return """Generate master report from workspace data
        
Usage:
  ipcrawler report master-report --workspace=<workspace_name>

Examples:  
  ipcrawler report master-report --workspace=google_com_20250125_143022
  ipcrawler report master-report --workspace=google_com_latest

Options:
  --workspace    Name of the workspace to generate report from (required)
"""