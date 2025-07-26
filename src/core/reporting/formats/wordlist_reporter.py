"""Wordlist format reporter for IPCrawler SmartList"""

from pathlib import Path
from typing import Dict, Any, Optional
from ..base_reporter import BaseReporter


class WordlistReporter(BaseReporter):
    """Wordlist format reporter"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate wordlist report"""
        filename = kwargs.get('filename')
        if not filename:
            target = kwargs.get('target', 'unknown')
            workflow = kwargs.get('workflow', 'wordlists')
            filename = self.generate_filename(target, workflow)
        elif not filename.endswith('.txt'):
            filename += '.txt'
        
        output_path = self.get_output_path(filename)
        
        # Simple wordlist output
        lines = []
        if 'wordlists' in data:
            for wordlist in data['wordlists']:
                lines.append(str(wordlist))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def get_format_name(self) -> str:
        """Get the report format name"""
        return "WORDLIST"