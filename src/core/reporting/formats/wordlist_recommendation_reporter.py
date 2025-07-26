"""Centralized Wordlist Recommendation Reporter for IPCrawler"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from ..base_reporter import BaseReporter
from ...utils.target_sanitizer import sanitize_target, create_workspace_path


class WordlistRecommendationReporter(BaseReporter):
    """Wordlist recommendation reporter"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate wordlist recommendations report"""
        target = kwargs.get('target', 'unknown')
        
        # Create wordlists directory structure using shared utility
        safe_target = sanitize_target(target)
        wordlists_dir = Path(create_workspace_path(target)) / f"wordlists_for_{safe_target}"
        wordlists_dir.mkdir(parents=True, exist_ok=True)
        
        filename = 'recommended_wordlists.txt'
        output_path = wordlists_dir / filename
        
        lines = []
        lines.append(f"Recommended Wordlists for {target}")
        lines.append("=" * 50)
        lines.append("")
        
        # Extract SmartList data if available
        smartlist_data = data.get('smartlist_05', {}) or data.get('smartlist', {})
        
        if 'wordlist_recommendations' in smartlist_data:
            recommendations = smartlist_data['wordlist_recommendations']
            
            for rec in recommendations:
                service = rec.get('service', 'Unknown')
                lines.append(f"Service: {service}")
                lines.append("-" * 20)
                
                wordlists = rec.get('top_wordlists', [])
                for wl in wordlists:
                    wordlist_name = wl.get('wordlist', 'Unknown')
                    confidence = wl.get('confidence', 'LOW')
                    path = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                    lines.append(f"  [{confidence}] {path}")
                
                lines.append("")
        else:
            lines.append("No wordlist recommendations available")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def get_format_name(self) -> str:
        """Get the report format name"""
        return "WORDLIST_RECOMMENDATION"