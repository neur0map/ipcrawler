"""Wordlist format reporter for IPCrawler SmartList

Generates a wordlists.txt file with ready-to-copy wordlist paths.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from ..base.reporter import BaseReporter
from ..templates.engine import get_template_engine
from src.core.ui.console.base import console


class WordlistReporter(BaseReporter):
    """Generates wordlists.txt file with SmartList recommendations"""
    
    def __init__(self, output_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize wordlist reporter
        
        Args:
            output_dir: Directory to save wordlist file
            theme: Theme to use (affects formatting preferences)
        """
        super().__init__(output_dir)
        self.theme = theme
        self.template_engine = get_template_engine(theme)
        console.debug(f"Wordlist reporter initialized with theme '{theme}'")
    
    def get_format(self) -> str:
        """Get the report format name"""
        return 'wordlist'
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate wordlists.txt file
        
        Args:
            data: Scan data to format
            **kwargs: Additional options (target, workflow, timestamp)
            
        Returns:
            Path to generated wordlists.txt file
        """
        self.ensure_output_dir()
        
        # Check if SmartList data exists
        if 'smartlist' not in data or not data['smartlist']:
            console.warning("No SmartList data found for wordlist generation", internal=True)
            return None
        
        # Prepare context
        context = self._prepare_context(data, **kwargs)
        
        # Generate filename
        filename = "wordlists.txt"
        output_path = self.output_dir / filename
        
        try:
            # Render template
            wordlist_content = self.template_engine.render_template(
                'workflows/wordlists.txt.j2', 
                context
            )
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(wordlist_content)
            
            console.success(f"Generated wordlist file: {output_path}", internal=True)
            return output_path
            
        except Exception as e:
            console.error(f"Failed to generate wordlist file: {e}", internal=True)
            raise
    
    def _prepare_context(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare context for template rendering"""
        # Base context
        context = {
            'data': data,
            'target': kwargs.get('target', data.get('target', 'Unknown')),
            'workflow': kwargs.get('workflow', 'smartlist_05'),
        }
        
        # Add SmartList data
        if 'smartlist' in data:
            context['smartlist'] = data['smartlist']
        
        # Process SmartList recommendations for better template access
        if context.get('smartlist', {}).get('wordlist_recommendations'):
            context['smartlist'] = self._process_smartlist_data(context['smartlist'])
        
        return context
    
    def _process_smartlist_data(self, smartlist_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process SmartList data for template rendering"""
        processed = smartlist_data.copy()
        
        # Ensure proper data structure for template
        if 'wordlist_recommendations' in processed:
            for service_rec in processed['wordlist_recommendations']:
                # Ensure port is available
                if 'port' not in service_rec:
                    # Try to extract port from service string
                    service_str = service_rec.get('service', '')
                    if ':' in service_str:
                        try:
                            service_rec['port'] = int(service_str.split(':')[1])
                        except (ValueError, IndexError):
                            service_rec['port'] = None
                    else:
                        service_rec['port'] = None
                
                # Ensure top_wordlists exists and is processed
                if 'top_wordlists' not in service_rec:
                    service_rec['top_wordlists'] = []
                
                # Sort wordlists by score (highest first)
                service_rec['top_wordlists'].sort(
                    key=lambda w: w.get('score', 0), 
                    reverse=True
                )
        
        return processed