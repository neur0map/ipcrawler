"""
Simplified Reporting Orchestrator for IPCrawler
Clean interface that delegates to the new reporting engine
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .workspace_manager import workspace_manager
from .reporting_engine import reporting_engine
from ..ui.console import console
from .utils import json_serializer


class ReportingOrchestrator:
    """Simplified coordinator that delegates to the new reporting engine"""
    
    def __init__(self):
        """Initialize reporting orchestrator"""
        self.workspace_manager = workspace_manager
        self.reporting_engine = reporting_engine
    
    def create_versioned_workspace(self, target: str, enable_versioning: bool = True) -> Path:
        """Create a new versioned workspace for a target"""
        return self.workspace_manager.create_workspace(target, enable_versioning)
    
    def generate_all_reports(self, workspace_path: Path, workflow_data: Dict[str, Any]) -> Dict[str, Path]:
        """Generate all reports using the new engine"""
        target = workflow_data.get('target', 'unknown')
        
        # Use the new simplified reporting engine
        generated_reports = self.reporting_engine.generate_complete_reports(
            workspace_path=workspace_path,
            workflow_data=workflow_data,
            target=target
        )
        
        # Clean up any legacy structures
        self._cleanup_legacy_structures(workspace_path)
        
        return generated_reports
    
    def generate_workflow_reports(self, workspace_path: Path, workflow_name: str, workflow_data: Dict[str, Any]) -> List[Path]:
        """Save individual workflow results as JSON files (legacy compatibility)"""
        generated_files = []
        
        result_file = workspace_path / f"{workflow_name}_results.json"
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2, default=json_serializer)
            generated_files.append(result_file)
        except Exception:
            pass
        
        return generated_files
    
    def generate_master_report_from_workspace(self, workspace_name: str) -> Dict[str, Path]:
        """Generate reports from existing workspace data"""
        workspace_path = self.workspace_manager.get_workspace_path(workspace_name)
        if not workspace_path.exists():
            return {}
        
        workflow_data = self._load_workspace_data(workspace_path)
        if not workflow_data:
            return {}
        
        target = workflow_data.get('target', workspace_name.split('_')[0])
        
        # Use new engine to generate reports
        return self.reporting_engine.generate_complete_reports(
            workspace_path=workspace_path,
            workflow_data=workflow_data,
            target=target
        )
    
    def list_workspaces(self, target: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available workspaces"""
        return self.workspace_manager.list_workspaces(target)
    
    def clean_old_workspaces(self, target: str, keep_count: int = 5) -> List[Path]:
        """Clean old workspaces for a target"""
        return self.workspace_manager.clean_old_workspaces(target, keep_count)
    
    def _load_workspace_data(self, workspace_path: Path) -> Dict[str, Any]:
        """Load workflow data from workspace files"""
        workflow_data = {}
        
        # Standard workflow file mappings
        workflow_files = {
            'nmap_fast_01': 'nmap_fast_01_results.json',
            'nmap_02': 'nmap_02_results.json',
            'http_03': 'http_03_results.json', 
            'mini_spider_04': 'mini_spider_04_results.json',
            'smartlist_05': 'smartlist_05_results.json'
        }
        
        for workflow_name, filename in workflow_files.items():
            result_file = workspace_path / filename
            if result_file.exists():
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        workflow_data[workflow_name] = json.load(f)
                except Exception:
                    continue
        
        # Try to extract target from data or workspace name
        target = None
        for data in workflow_data.values():
            if isinstance(data, dict) and 'target' in data:
                target = data['target']
                break
        
        if not target:
            workspace_name = workspace_path.name
            target = workspace_name.split('_')[0] if '_' in workspace_name else workspace_name
        
        if target:
            workflow_data['target'] = target
        
        return workflow_data
    
    def _cleanup_legacy_structures(self, workspace_path: Path) -> None:
        """Remove legacy report directories and files (but keep new reports/ folder created by ReportingEngine)"""
        legacy_dirs = ['nmap_fast_01', 'nmap_02', 'http_03', 'mini_spider_04', 'smartlist_05', 'comprehensive']
        
        for dir_name in legacy_dirs:
            legacy_dir = workspace_path / dir_name
            if legacy_dir.exists() and legacy_dir.is_dir():
                try:
                    import shutil
                    shutil.rmtree(legacy_dir)
                    console.info(f"Cleaned up legacy directory: {dir_name}")
                except Exception:
                    pass
    


# Global reporting orchestrator instance
reporting_orchestrator = ReportingOrchestrator()