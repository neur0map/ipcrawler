"""Result manager for IPCrawler - legacy compatibility"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from .formatters import JSONFormatter, TextFormatter


class ResultManager:
    """Legacy result manager for backward compatibility"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.json_formatter = JSONFormatter(self.output_dir)
        self.text_formatter = TextFormatter(self.output_dir)
    
    def save_json(self, data: Dict[str, Any], filename: str, **kwargs) -> Path:
        """Save data as JSON file"""
        return self.json_formatter.save(data, filename, **kwargs)
    
    def save_text(self, data: Dict[str, Any], filename: str, **kwargs) -> Path:
        """Save data as text file"""
        return self.text_formatter.save(data, filename, **kwargs)
    
    def format_json(self, data: Dict[str, Any], **kwargs) -> str:
        """Format data as JSON string"""
        return self.json_formatter.format(data, **kwargs)
    
    def format_text(self, data: Dict[str, Any], **kwargs) -> str:
        """Format data as text string"""
        return self.text_formatter.format(data, **kwargs)
    
    def set_output_dir(self, output_dir: Path) -> None:
        """Set output directory"""
        self.output_dir = Path(output_dir)
        self.json_formatter.output_dir = self.output_dir
        self.text_formatter.output_dir = self.output_dir