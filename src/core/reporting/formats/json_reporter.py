"""JSON format reporter for IPCrawler

Provides JSON output formatting for all workflows.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

from ..base.reporter import BaseReporter


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects and enums"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, 'model_dump'):
            # Handle Pydantic models
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            # Handle objects with __dict__ (fallback)
            return {key: value for key, value in obj.__dict__.items() 
                   if not key.startswith('_')}
        return super().default(obj)


class JSONReporter(BaseReporter):
    """JSON format reporter"""
    
    def __init__(self, output_dir: Optional[Path] = None, indent: int = 2):
        """Initialize JSON reporter
        
        Args:
            output_dir: Directory to save reports
            indent: JSON indentation level
        """
        super().__init__(output_dir)
        self.indent = indent
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate JSON report from data
        
        Args:
            data: Data to generate report from
            **kwargs: Additional options (filename, target)
            
        Returns:
            Path to generated JSON file
        """
        if not self.validate_data(data):
            raise ValueError("Invalid data provided for JSON report")
        
        # Add metadata
        report_data = self.add_metadata(data)
        
        # Get filename
        filename = kwargs.get('filename')
        if not filename:
            target = kwargs.get('target', 'unknown')
            workflow = kwargs.get('workflow', 'scan')
            safe_target = target.replace(':', '_').replace('/', '_').replace('.', '_')
            filename = f"{workflow}_report_{safe_target}.json"
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        output_path = self.get_output_path(filename)
        
        # Generate JSON with custom encoder
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
    
    def get_format(self) -> str:
        """Get the report format name"""
        return "json"
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate that data can be serialized to JSON"""
        try:
            json.dumps(data, cls=DateTimeJSONEncoder)
            return True
        except (TypeError, ValueError):
            return False