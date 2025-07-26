"""Text format reporter for IPCrawler"""

from pathlib import Path
from typing import Dict, Any, Optional
from ..base_reporter import BaseReporter


class TextReporter(BaseReporter):
    """Text format reporter"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate text report"""
        # Get filename using shared utility
        filename = kwargs.get('filename')
        if not filename:
            target = kwargs.get('target', 'unknown')
            workflow = kwargs.get('workflow', 'scan')
            filename = self.generate_filename(target, workflow)
        
        output_path = self.get_output_path(filename) 
        
        # Generate text content
        lines = []
        lines.append("=" * 60)
        lines.append(f"IPCrawler Report - {kwargs.get('target', 'Unknown Target')}")
        lines.append("=" * 60)
        lines.append("")
        
        # Add timestamp
        if 'timestamp' in data:
            lines.append(f"Generated: {data['timestamp']}")
            lines.append("")
        
        # Add main content
        for key, value in data.items():
            if key not in ['timestamp', 'generated_at', 'format', 'version']:
                lines.append(f"{key.upper().replace('_', ' ')}: {value}")
                lines.append("")
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def get_format_name(self) -> str:  
        """Get the report format name"""
        return "TXT"