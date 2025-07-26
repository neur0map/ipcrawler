"""Centralized Wordlist Recommendation Reporter for IPCrawler"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from ..base_reporter import BaseReporter
from ...utils.target_sanitizer import sanitize_target, create_workspace_path

# Import path resolution from scorer module
try:
    from ...scorer import get_wordlist_paths
    SCORER_AVAILABLE = True
except ImportError:
    SCORER_AVAILABLE = False


class WordlistRecommendationReporter(BaseReporter):
    """Wordlist recommendation reporter"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
    
    def _resolve_wordlist_path(self, wordlist_name: str, context_tech: Optional[str] = None, 
                              context_port: Optional[int] = None) -> Optional[str]:
        """Resolve full path for wordlist using catalog database"""
        if not SCORER_AVAILABLE:
            return None
            
        try:
            # Use existing scorer function to resolve paths from catalog
            paths = get_wordlist_paths([wordlist_name], tech=context_tech, port=context_port)
            return paths[0] if paths and paths[0] else None
        except Exception:
            return None
    
    def _format_confidence_indicator(self, confidence: str) -> str:
        """Format confidence level with visual indicator"""
        confidence_upper = confidence.upper()
        if confidence_upper == 'HIGH':
            return "✓ HIGH"
        elif confidence_upper == 'MEDIUM':
            return "⚠ MEDIUM" 
        elif confidence_upper == 'LOW':
            return "? LOW"
        else:
            return f"• {confidence_upper}"
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate wordlist recommendations report"""
        target = kwargs.get('target', 'unknown')
        
        # Use output directory (workspace root) instead of creating subdirectory
        filename = 'wordlist_recommendations.txt'
        output_path = self.output_dir / filename
        
        lines = []
        lines.append("╔" + "=" * 78 + "╗")
        lines.append(f"║ WORDLIST RECOMMENDATIONS FOR {target.upper():<47} ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")
        
        # Extract SmartList data if available
        smartlist_data = data.get('smartlist_05', {}) or data.get('smartlist', {})
        
        if 'wordlist_recommendations' in smartlist_data:
            recommendations = smartlist_data['wordlist_recommendations']
            
            for idx, rec in enumerate(recommendations, 1):
                service = rec.get('service', 'Unknown')
                service_name = rec.get('service_name', '')
                detected_tech = rec.get('detected_technology', '')
                confidence = rec.get('confidence', 'LOW')
                port = rec.get('port')
                
                # Enhanced service header with technology info
                service_header = f"[{idx}] {service}"
                if service_name and service_name != 'unknown':
                    service_header += f" ({service_name})"
                if detected_tech:
                    service_header += f" - {detected_tech} detected"
                if port:
                    service_header += f" on port {port}"
                
                lines.append("┌" + "─" * (len(service_header) + 2) + "┐")
                lines.append(f"│ {service_header} │")
                lines.append("└" + "─" * (len(service_header) + 2) + "┘")
                lines.append(f"Overall Confidence: {self._format_confidence_indicator(confidence)}")
                lines.append("")
                
                wordlists = rec.get('top_wordlists', [])
                if not wordlists:
                    lines.append("  ⚠ No specific wordlists recommended for this service")
                    lines.append("    └─ Consider running additional scans for better detection")
                else:
                    lines.append(f"  📋 Recommended Wordlists ({len(wordlists)} found):")
                    lines.append("")
                    
                    for wl_idx, wl in enumerate(wordlists, 1):
                        wordlist_name = wl.get('wordlist', 'Unknown')
                        wl_confidence = wl.get('confidence', 'LOW')
                        reason = wl.get('reason', 'No reason provided')
                        wl_path = wl.get('path')  # Use resolved path from SmartList
                        
                        # Try to resolve path from catalog if not provided
                        if not wl_path:
                            wl_path = self._resolve_wordlist_path(wordlist_name, detected_tech, port)
                        
                        # Format the wordlist entry
                        confidence_icon = self._format_confidence_indicator(wl_confidence)
                        lines.append(f"    {wl_idx}. [{confidence_icon}] {wordlist_name}")
                        
                        # Show path with validation
                        if wl_path:
                            path_obj = Path(wl_path)
                            if path_obj.exists():
                                lines.append(f"       📂 Path: {wl_path}")
                                # Show file size if available
                                try:
                                    size_mb = path_obj.stat().st_size / (1024 * 1024)
                                    lines.append(f"       📊 Size: {size_mb:.1f} MB")
                                except:
                                    pass
                            else:
                                lines.append(f"       ⚠ Path: {wl_path} (FILE NOT FOUND)")
                        else:
                            lines.append(f"       ❌ Path: Could not resolve from catalog")
                            
                        lines.append(f"       💡 Reason: {reason}")
                        lines.append("")
                
                lines.append("")
        else:
            lines.append("❌ NO SMARTLIST RECOMMENDATIONS AVAILABLE")
            lines.append("")
            lines.append("📋 What this means:")
            lines.append("  • SmartList analysis was not run or produced no results")
            lines.append("  • Service detection may have failed")
            lines.append("  • Target may not be responding to scans")
            lines.append("")
            lines.append("🔧 How to fix:")
            lines.append("  1. Run the complete scan workflow: nmap → http → smartlist")
            lines.append("  2. Ensure target is reachable and responding")
            lines.append("  3. Check that SmartList database is available")
            lines.append("")
            if SCORER_AVAILABLE:
                lines.append("✓ SmartList scorer module is available")
            else:
                lines.append("❌ SmartList scorer module is NOT available")
        
        # Add footer with summary
        lines.append("")
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║ SUMMARY                                                                   ║")
        lines.append("╠" + "=" * 78 + "╣")
        
        if 'wordlist_recommendations' in smartlist_data:
            total_services = len(smartlist_data['wordlist_recommendations'])
            total_wordlists = sum(len(rec.get('top_wordlists', [])) for rec in smartlist_data['wordlist_recommendations'])
            lines.append(f"║ • Services analyzed: {total_services:<52} ║")
            lines.append(f"║ • Total wordlists recommended: {total_wordlists:<43} ║")
            lines.append(f"║ • Catalog resolution: {'✓ Available' if SCORER_AVAILABLE else '❌ Unavailable':<48} ║")
        else:
            lines.append("║ • No recommendations generated                                             ║")
        
        lines.append("║ • Report generated at: " + f"{target}".ljust(53) + "║")
        lines.append("╚" + "=" * 78 + "╝")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def get_format_name(self) -> str:
        """Get the report format name"""
        return "WORDLIST_RECOMMENDATION"