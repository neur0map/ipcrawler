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
                service_name = rec.get('service_name', '')
                detected_tech = rec.get('detected_technology', '')
                confidence = rec.get('confidence', 'LOW')
                
                # Enhanced service header with technology info
                service_header = f"Service: {service}"
                if service_name and service_name != 'unknown':
                    service_header += f" ({service_name})"
                if detected_tech:
                    service_header += f" - {detected_tech} detected"
                
                lines.append(service_header)
                lines.append("-" * len(service_header))
                lines.append(f"Confidence: {confidence}")
                lines.append("")
                
                wordlists = rec.get('top_wordlists', [])
                if not wordlists:
                    lines.append("  No specific wordlists recommended for this service")
                else:
                    for wl in wordlists:
                        wordlist_name = wl.get('wordlist', 'Unknown')
                        wl_confidence = wl.get('confidence', 'LOW')
                        reason = wl.get('reason', 'No reason provided')
                        wl_path = wl.get('path')  # Use resolved path from SmartList
                        
                        # Use resolved path if available, otherwise fallback to default path
                        if wl_path:
                            display_path = wl_path
                        else:
                            display_path = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                        
                        lines.append(f"  [{wl_confidence}] {display_path}")
                        lines.append(f"      Reason: {reason}")
                
                lines.append("")
        else:
            lines.append("No SmartList recommendations available")
            lines.append("Note: Run the complete scan workflow including SmartList analysis for intelligent recommendations.")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def get_format_name(self) -> str:
        """Get the report format name"""
        return "WORDLIST_RECOMMENDATION"