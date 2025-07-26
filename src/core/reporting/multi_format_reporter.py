"""Multi-format reporter for IPCrawler"""

from pathlib import Path
from typing import Dict, List, Any
from .base_reporter import BaseReporter


class MultiFormatReporter:
    """Handles multiple report formats"""
    
    def __init__(self, reporters: List[BaseReporter]):
        self.reporters = {reporter.get_format_name().lower(): reporter for reporter in reporters}
    
    def generate_all(self, data: Dict[str, Any], formats: List[str] = None, **kwargs) -> Dict[str, Path]:
        """Generate reports in all specified formats"""
        if formats is None:
            formats = list(self.reporters.keys())
        
        results = {}
        
        for format_name in formats:
            format_key = format_name.lower()
            if format_key in self.reporters:
                try:
                    reporter = self.reporters[format_key]
                    output_path = reporter.generate(data, **kwargs)
                    results[format_name] = output_path
                except Exception as e:
                    # Log error but continue with other formats
                    continue
        
        return results
    
    def add_reporter(self, reporter: BaseReporter):
        """Add a new reporter"""
        self.reporters[reporter.get_format_name().lower()] = reporter
    
    def get_available_formats(self) -> List[str]:
        """Get list of available formats"""
        return list(self.reporters.keys())