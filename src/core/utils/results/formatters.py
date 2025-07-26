"""Result formatters for IPCrawler"""

import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from pathlib import Path


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


class BaseFormatter:
    """Base class for result formatters"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
    
    def format(self, data: Dict[str, Any], **kwargs) -> str:
        """Format data - to be implemented by subclasses"""
        raise NotImplementedError
    
    def save(self, data: Dict[str, Any], filename: str, **kwargs) -> Path:
        """Save formatted data to file"""
        formatted_data = self.format(data, **kwargs)
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_data)
        
        return output_path


class JSONFormatter(BaseFormatter):
    """JSON formatter for results"""
    
    def __init__(self, output_dir: Optional[Path] = None, indent: int = 2):
        super().__init__(output_dir)
        self.indent = indent
    
    def format(self, data: Dict[str, Any], **kwargs) -> str:
        """Format data as JSON"""
        return json.dumps(
            data,
            indent=self.indent,
            cls=DateTimeJSONEncoder,
            ensure_ascii=False
        )


class TextFormatter(BaseFormatter):
    """Text formatter for results"""
    
    def format(self, data: Dict[str, Any], **kwargs) -> str:
        """Format data as human-readable text"""
        lines = []
        
        # Add timestamp
        if 'timestamp' in data:
            lines.append(f"Report generated: {data['timestamp']}")
            lines.append("=" * 50)
            lines.append("")
        
        # Add target info
        if 'target' in data:
            lines.append(f"Target: {data['target']}")
            lines.append("")
        
        # Add scan results
        if 'hosts' in data:
            lines.append("HOST RESULTS:")
            lines.append("-" * 20)
            for host in data['hosts']:
                lines.append(f"Host: {host.get('address', 'Unknown')}")
                lines.append(f"Status: {host.get('status', 'Unknown')}")
                
                if 'ports' in host:
                    lines.append("Ports:")
                    for port in host['ports']:
                        state = port.get('state', 'unknown')
                        port_num = port.get('port', 'unknown')
                        service = port.get('service', 'unknown')
                        lines.append(f"  {port_num}/{port.get('protocol', 'tcp')} {state} {service}")
                lines.append("")
        
        # Add other data
        for key, value in data.items():
            if key not in ['timestamp', 'target', 'hosts']:
                lines.append(f"{key.upper()}: {value}")
                lines.append("")
        
        return "\n".join(lines)