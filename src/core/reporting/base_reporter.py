"""Base reporter class for IPCrawler"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from ..utils.target_sanitizer import generate_safe_filename


class BaseReporter(ABC):
    """Base class for all report formatters"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate report - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """Get the format name - must be implemented by subclasses"""
        pass
    
    def get_output_path(self, filename: str) -> Path:
        """Get full output path for a filename"""
        return self.output_dir / filename
    
    def generate_filename(self, target: str, workflow: str = 'scan', **kwargs) -> str:
        """Generate safe filename for reports
        
        Args:
            target: Target hostname or IP
            workflow: Workflow name
            **kwargs: Additional options (can override extension)
            
        Returns:
            Safe filename with appropriate extension
        """
        # Get extension from format name
        format_name = self.get_format_name()
        extension = kwargs.get('extension', format_name.lower())
        
        return generate_safe_filename(target, workflow, extension)
    
    def add_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata to report data"""
        report_data = data.copy()
        report_data.update({
            'generated_at': datetime.now().isoformat(),
            'format': self.get_format_name(),
            'version': '1.0.0'
        })
        return report_data