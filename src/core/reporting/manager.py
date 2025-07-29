"""Report manager for IPCrawler"""

from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

from ..ui.console import console
from .formats.json_reporter import JSONReporter
from .formats.text_reporter import TextReporter
from .formats.wordlist_reporter import WordlistReporter
from .formats.master_text_reporter import MasterTextReporter
from .formats.wordlist_recommendation_reporter import WordlistRecommendationReporter
from .multi_format_reporter import MultiFormatReporter


class ReportManager:
    """Centralized report management for IPCrawler"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize report manager"""
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.reporters = self._initialize_reporters()
        self.multi_reporter = MultiFormatReporter(list(self.reporters.values()))
    
    def _initialize_reporters(self) -> Dict[str, Any]:
        """Initialize format-specific reporters"""
        return {
            'json': JSONReporter(self.output_dir),
            'txt': TextReporter(self.output_dir),
            'wordlist': WordlistReporter(self.output_dir),
            'master_txt': MasterTextReporter(self.output_dir),
            'wordlist_recommendation': WordlistRecommendationReporter(self.output_dir),
        }
    
    def generate_report(self, data: Dict[str, Any],
                       formats: Optional[List[str]] = None,
                       target: Optional[str] = None,
                       workflow: Optional[str] = None,
                       **kwargs) -> Dict[str, Path]:
        """Generate reports in specified formats"""
        if formats is None:
            formats = self.get_available_formats()
        
        if workflow:
            workflow_dir = self.output_dir / workflow
            workflow_dir.mkdir(parents=True, exist_ok=True)
            for reporter in self.reporters.values():
                reporter.output_dir = workflow_dir
        
        kwargs.update({
            'target': target or 'unknown',
            'workflow': workflow,
            'timestamp': datetime.now()
        })
        
        try:
            results = self.multi_reporter.generate_all(data, formats)
            console.success(f"Generated {len(results)} report files", internal=True)
            return results
        except Exception as e:
            console.error(f"Report generation failed: {e}", internal=True)
            return {}
    
    def generate_workspace_report(self, data: Dict[str, Any],
                                 workspace_dir: Path,
                                 formats: Optional[List[str]] = None,
                                 **kwargs) -> Dict[str, Path]:
        """Generate reports in a specific workspace directory"""
        reports_dir = workspace_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Temporarily update output directories
        original_dirs = {}
        for fmt, reporter in self.reporters.items():
            original_dirs[fmt] = reporter.output_dir
            reporter.output_dir = reports_dir
        
        try:
            results = self.generate_report(data, formats, **kwargs)
        finally:
            # Restore original directories
            for fmt, reporter in self.reporters.items():
                reporter.output_dir = original_dirs[fmt]
        
        return results
    
    def generate_master_report(self, data: Dict[str, Any],
                             target: Optional[str] = None,
                             format_type: str = 'txt',
                             **kwargs) -> Path:
        """Generate a master TXT report consolidating all workflow findings"""
        if format_type != 'txt':
            console.warning(f"Only TXT format supported for master reports, using 'txt'", internal=True)
            format_type = 'txt'
        
        master_format = f'master_{format_type}'
        
        if master_format in self.reporters:
            results = self.generate_report(
                data,
                formats=[master_format], 
                target=target, 
                workflow='comprehensive',
                **kwargs
            )
            return results.get(master_format)
        else:
            console.error(f"Master TXT reporter not found", internal=True)
            return None
    
    def generate_wordlist_recommendations(self, data: Dict[str, Any],
                                        target: Optional[str] = None,
                                        enable_versioning: bool = False,
                                        **kwargs) -> Path:
        """Generate wordlist recommendations file"""
        if 'wordlist_recommendation' in self.reporters:
            reporter = self.reporters['wordlist_recommendation']
            return reporter.generate(
                data,
                target=target,
                enable_versioning=enable_versioning,
                **kwargs
            )
        else:
            console.error(f"Wordlist recommendation reporter not found", internal=True)
            return None
    
    def add_reporter(self, format_name: str, reporter) -> None:
        """Add a custom reporter"""
        self.reporters[format_name] = reporter
    
    def remove_reporter(self, format_name: str) -> None:
        """Remove a reporter"""
        if format_name in self.reporters:
            del self.reporters[format_name]
    
    def get_available_formats(self) -> List[str]:
        """Get list of available report formats"""
        return list(self.reporters.keys())
    
    def set_output_directory(self, output_dir: Path) -> None:
        """Set output directory for all reporters"""
        self.output_dir = Path(output_dir)
        for reporter in self.reporters.values():
            reporter.output_dir = self.output_dir
    
    def create_workflow_manager(self, workflow_name: str):
        """Create a workflow-specific report manager"""
        return WorkflowReportManager(self, workflow_name)


class WorkflowReportManager:
    """Workflow-specific report manager"""
    
    def __init__(self, parent_manager: ReportManager, workflow_name: str):
        """Initialize workflow report manager"""
        self.parent = parent_manager
        self.workflow_name = workflow_name
        self.workflow_dir = parent_manager.output_dir / workflow_name
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, data: Dict[str, Any],
                       formats: Optional[List[str]] = None,
                       **kwargs) -> Dict[str, Path]:
        """Generate workflow reports"""
        kwargs['workflow'] = self.workflow_name
        return self.parent.generate_report(data, formats, **kwargs)
    
    def generate_workspace_report(self, data: Dict[str, Any],
                                workspace_dir: Path,
                                formats: Optional[List[str]] = None,
                                **kwargs) -> Dict[str, Path]:
        """Generate reports in workspace directory"""
        kwargs['workflow'] = self.workflow_name
        return self.parent.generate_workspace_report(data, workspace_dir, formats, **kwargs)


# Global report manager instance
report_manager = ReportManager()