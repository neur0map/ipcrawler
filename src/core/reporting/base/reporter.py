"""Base reporter class for IPCrawler

Provides abstract base class for all report generators.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import json


class BaseReporter(ABC):
    """Abstract base class for all IPCrawler reporters"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize reporter
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.metadata = {
            'generator': 'IPCrawler',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }
    
    @abstractmethod
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate report from data
        
        Args:
            data: Data to generate report from
            **kwargs: Additional options
            
        Returns:
            Path to generated report
        """
        pass
    
    @abstractmethod
    def get_format(self) -> str:
        """Get the report format name"""
        pass
    
    def ensure_output_dir(self):
        """Ensure output directory exists"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_output_path(self, filename: str) -> Path:
        """Get full output path for filename"""
        self.ensure_output_dir()
        return self.output_dir / filename
    
    def add_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata to report data"""
        return {
            'metadata': self.metadata,
            'data': data
        }
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate input data
        
        Override in subclasses for specific validation
        """
        return isinstance(data, dict)


class WorkflowReporter(BaseReporter):
    """Base class for workflow-specific reporters"""
    
    def __init__(self, workflow_name: str, output_dir: Optional[Path] = None):
        """Initialize workflow reporter
        
        Args:
            workflow_name: Name of the workflow
            output_dir: Directory to save reports
        """
        super().__init__(output_dir)
        self.workflow_name = workflow_name
        self.metadata['workflow'] = workflow_name
    
    def get_filename(self, target: str, extension: str) -> str:
        """Generate filename for report
        
        Args:
            target: Scan target
            extension: File extension
            
        Returns:
            Generated filename
        """
        # Import re module for regex
        import re
        # Preserve dots for IP addresses, only replace truly problematic characters
        safe_target = re.sub(r'[<>:"/\\|?*]', '_', target)
        safe_target = re.sub(r'_+', '_', safe_target).strip('_')
        return f"{self.workflow_name}_{safe_target}.{extension}"


class MultiFormatReporter:
    """Reporter that can generate multiple formats"""
    
    def __init__(self, reporters: List[BaseReporter]):
        """Initialize with list of reporters
        
        Args:
            reporters: List of reporter instances
        """
        self.reporters = {r.get_format(): r for r in reporters}
    
    def generate_all(self, data: Dict[str, Any], formats: Optional[List[str]] = None) -> Dict[str, Path]:
        """Generate reports in all specified formats
        
        Args:
            data: Data to generate reports from
            formats: List of formats to generate (None = all)
            
        Returns:
            Dictionary mapping format to generated file path
        """
        if formats is None:
            formats = list(self.reporters.keys())
        
        results = {}
        for fmt in formats:
            if fmt in self.reporters:
                try:
                    path = self.reporters[fmt].generate(data)
                    results[fmt] = path
                except Exception as e:
                    # Log error but continue with other formats
                    print(f"Failed to generate {fmt} report: {e}")
        
        return results
    
    def add_reporter(self, reporter: BaseReporter):
        """Add a reporter"""
        self.reporters[reporter.get_format()] = reporter
    
    def remove_reporter(self, format_name: str):
        """Remove a reporter by format name"""
        if format_name in self.reporters:
            del self.reporters[format_name]
    
    def get_available_formats(self) -> List[str]:
        """Get list of available formats"""
        return list(self.reporters.keys())