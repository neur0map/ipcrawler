"""Report manager for IPCrawler

Provides unified interface for generating reports in multiple formats.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base.reporter import MultiFormatReporter
from .formats.json_reporter import JSONReporter
from .formats.html_reporter import HTMLReporter
from .formats.text_reporter import TextReporter
from .formats.wordlist_reporter import WordlistReporter
from .formats.master_reporter import MasterReporter, MasterTextReporter
from src.core.ui.console.base import console


class ReportManager:
    """Centralized report management for IPCrawler"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize report manager
        
        Args:
            output_dir: Base directory for all reports
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.reporters = self._initialize_reporters()
        self.multi_reporter = MultiFormatReporter(list(self.reporters.values()))
    
    def _initialize_reporters(self) -> Dict[str, Any]:
        """Initialize format-specific reporters"""
        return {
            'json': JSONReporter(self.output_dir),
            'html': HTMLReporter(self.output_dir),
            'txt': TextReporter(self.output_dir),
            'wordlist': WordlistReporter(self.output_dir),
            'master_html': MasterReporter(self.output_dir),
            'master_txt': MasterTextReporter(self.output_dir),
            # TODO: Add more formats (MD, xml)
        }
    
    def generate_report(self, 
                       data: Dict[str, Any], 
                       formats: Optional[List[str]] = None,
                       target: Optional[str] = None,
                       workflow: Optional[str] = None,
                       **kwargs) -> Dict[str, Path]:
        """Generate reports in specified formats
        
        Args:
            data: Data to generate reports from
            formats: List of formats to generate (None = all available)
            target: Target identifier for filename generation
            workflow: Workflow name for organization
            **kwargs: Additional options passed to reporters
            
        Returns:
            Dictionary mapping format names to generated file paths
        """
        if formats is None:
            formats = self.get_available_formats()
        
        # Create workflow-specific subdirectory if specified
        # Skip if reporters are already set to correct directories
        if workflow and not str(self.reporters['json'].output_dir).endswith(workflow):
            workflow_dir = self.output_dir / workflow
            workflow_dir.mkdir(parents=True, exist_ok=True)
            # Update reporter output directories
            for reporter in self.reporters.values():
                reporter.output_dir = workflow_dir
        
        # Add common kwargs
        kwargs.update({
            'target': target or 'unknown',
            'workflow': workflow,
            'timestamp': datetime.now()
        })
        
        console.debug(f"Generating reports in formats: {formats}")
        
        try:
            results = self.multi_reporter.generate_all(data, formats)
            console.success(f"Generated {len(results)} report files", internal=True)
            return results
        except Exception as e:
            console.error(f"Report generation failed: {e}", internal=True)
            return {}
    
    def generate_workspace_reports(self,
                                 workspace_dir: Path,
                                 data: Dict[str, Any],
                                 formats: Optional[List[str]] = None,
                                 **kwargs) -> Dict[str, Path]:
        """Generate reports in a specific workspace directory
        
        Args:
            workspace_dir: Workspace directory for reports
            data: Data to generate reports from
            formats: List of formats to generate
            **kwargs: Additional options
            
        Returns:
            Dictionary mapping format names to generated file paths
        """
        # Create reports subdirectory in workspace
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
    
    def generate_master_report(self,
                             data: Dict[str, Any],
                             target: Optional[str] = None,
                             format_type: str = 'txt',
                             **kwargs) -> Path:
        """Generate a master report consolidating all workflow findings
        
        Args:
            data: Combined scan data from all workflows
            target: Target identifier for filename
            format_type: Report format ('txt', 'html', or 'both')
            **kwargs: Additional options
            
        Returns:
            Path to generated master report (or TXT if both formats)
        """
        master_format = f'master_{format_type}'
        
        if format_type == 'both':
            # Generate both HTML and TXT master reports
            html_results = self.generate_report(
                data, 
                formats=['master_html'], 
                target=target, 
                workflow='comprehensive',
                **kwargs
            )
            txt_results = self.generate_report(
                data, 
                formats=['master_txt'], 
                target=target, 
                workflow='comprehensive',
                **kwargs
            )
            console.success(f"Generated master reports in both formats", internal=True)
            return txt_results.get('master_txt', list(txt_results.values())[0])
        
        elif master_format in self.reporters:
            results = self.generate_report(
                data, 
                formats=[master_format], 
                target=target, 
                workflow='comprehensive',
                **kwargs
            )
            return results.get(master_format, list(results.values())[0])
        else:
            console.error(f"Unsupported master report format: {format_type}", internal=True)
            raise ValueError(f"Unsupported format: {format_type}")
    
    def add_reporter(self, format_name: str, reporter):
        """Add a custom reporter
        
        Args:
            format_name: Format identifier
            reporter: Reporter instance
        """
        self.reporters[format_name] = reporter
        self.multi_reporter.add_reporter(reporter)
    
    def remove_reporter(self, format_name: str):
        """Remove a reporter
        
        Args:
            format_name: Format identifier to remove
        """
        if format_name in self.reporters:
            del self.reporters[format_name]
            self.multi_reporter.remove_reporter(format_name)
    
    def get_available_formats(self) -> List[str]:
        """Get list of available report formats"""
        return list(self.reporters.keys())
    
    def set_output_directory(self, output_dir: Path):
        """Set output directory for all reporters
        
        Args:
            output_dir: New output directory
        """
        self.output_dir = Path(output_dir)
        for reporter in self.reporters.values():
            reporter.output_dir = self.output_dir
    
    def create_workflow_manager(self, workflow_name: str) -> 'WorkflowReportManager':
        """Create a workflow-specific report manager
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow-specific report manager
        """
        return WorkflowReportManager(self, workflow_name)


class WorkflowReportManager:
    """Workflow-specific report manager"""
    
    def __init__(self, parent_manager: ReportManager, workflow_name: str):
        """Initialize workflow report manager
        
        Args:
            parent_manager: Parent report manager
            workflow_name: Name of the workflow
        """
        self.parent = parent_manager
        self.workflow_name = workflow_name
        self.workflow_dir = parent_manager.output_dir / workflow_name
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, 
                data: Dict[str, Any], 
                formats: Optional[List[str]] = None,
                **kwargs) -> Dict[str, Path]:
        """Generate workflow reports
        
        Args:
            data: Data to generate reports from
            formats: List of formats to generate
            **kwargs: Additional options
            
        Returns:
            Dictionary mapping format names to generated file paths
        """
        kwargs['workflow'] = self.workflow_name
        return self.parent.generate_report(data, formats, **kwargs)
    
    def generate_in_workspace(self,
                            workspace_dir: Path,
                            data: Dict[str, Any],
                            formats: Optional[List[str]] = None,
                            **kwargs) -> Dict[str, Path]:
        """Generate reports in workspace directory
        
        Args:
            workspace_dir: Workspace directory
            data: Data to generate reports from
            formats: List of formats to generate
            **kwargs: Additional options
            
        Returns:
            Dictionary mapping format names to generated file paths
        """
        kwargs['workflow'] = self.workflow_name
        return self.parent.generate_workspace_reports(workspace_dir, data, formats, **kwargs)


# Global report manager instance
report_manager = ReportManager()