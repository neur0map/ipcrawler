"""Master text report generator for IPCrawler"""

from pathlib import Path
from typing import Dict, Any, Optional
from ..base_reporter import BaseReporter


class MasterTextReporter(BaseReporter):
    """Master text report generator"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate master text report"""
        filename = kwargs.get('filename')
        if not filename:
            target = kwargs.get('target', 'unknown')
            filename = self.generate_filename(target, 'master')
        elif not filename.endswith('.txt'):
            filename += '.txt'
        
        output_path = self.get_output_path(filename)
        
        # Generate comprehensive text report
        lines = []
        lines.append("=" * 80)
        lines.append(f"IPCrawler Master Report - {kwargs.get('target', 'Unknown Target')}")
        lines.append("=" * 80)
        lines.append("")
        
        # Add all data sections
        for key, value in data.items():
            if key not in ['generated_at', 'format', 'version']:
                lines.append(f"{key.upper().replace('_', ' ')}")
                lines.append("-" * 40)
                lines.append(str(value))
                lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def get_format_name(self) -> str:
        """Get the report format name"""
        return "MASTER_TXT"