"""JSON format reporter for IPCrawler"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any
from ..base_reporter import BaseReporter


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects and enums"""
    
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        return super().default(obj)


class JSONReporter(BaseReporter):
    """JSON format reporter"""
    
    def __init__(self, output_dir: Optional[Path] = None, indent: int = 2):
        """Initialize JSON reporter"""
        super().__init__(output_dir)
        self.indent = indent
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate JSON report from data
        
        Args:
            data: Report data
            **kwargs: Additional options (filename, target)
        
        Returns:
            Path to generated report file
        """
        
        # Add metadata
        report_data = self.add_metadata(data)
        
        # Get filename using shared utility
        filename = kwargs.get('filename')
        if not filename:
            target = kwargs.get('target', 'unknown')
            workflow = kwargs.get('workflow', 'scan')
            filename = self.generate_filename(target, workflow)
        
        output_path = self.get_output_path(filename)
        
        json_content = json.dumps(
            report_data,
            indent=self.indent, 
            cls=DateTimeJSONEncoder,
            ensure_ascii=False
        )
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        return output_path
    
    def get_format_name(self) -> str:
        """Get the report format name"""
        return "JSON"
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate that data can be serialized to JSON"""
        try:
            json.dumps(data, cls=DateTimeJSONEncoder)
            return True
        except (TypeError, ValueError):
            return False