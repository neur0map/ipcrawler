"""LEGACY Master text report generator for IPCrawler - DEPRECATED
USE: src.core.reporting.reporting_engine.ReportingEngine instead
This file is kept for compatibility but should not be used in new code.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..base_reporter import BaseReporter


class MasterTextReporter(BaseReporter):
    """DEPRECATED - Use ReportingEngine instead"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
    
    def _format_dict_data(self, data: Any, indent: int = 2) -> List[str]:
        """Format dictionary data with proper structure"""
        lines = []
        indent_str = " " * indent
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{indent_str}• {key.replace('_', ' ').title()}:")
                    lines.extend(self._format_dict_data(value, indent + 2))
                else:
                    lines.append(f"{indent_str}• {key.replace('_', ' ').title()}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data, 1):
                if isinstance(item, dict):
                    lines.append(f"{indent_str}{i}.")
                    lines.extend(self._format_dict_data(item, indent + 2))
                else:
                    lines.append(f"{indent_str}• {item}")
        else:
            lines.append(f"{indent_str}{data}")
            
        return lines
    
    def _format_service_data(self, services: List[Dict[str, Any]]) -> List[str]:
        """Format service discovery data with enhanced structure"""
        lines = []
        
        for idx, service in enumerate(services, 1):
            port = service.get('port', 'Unknown')
            protocol = service.get('protocol', 'tcp')
            service_name = service.get('service', 'unknown')
            state = service.get('state', 'unknown')
            
            # Service header
            lines.append(f"  [{idx}] Port {port}/{protocol} - {service_name}")
            lines.append(f"      State: {state}")
            
            # Additional service details
            if 'version' in service:
                lines.append(f"      Version: {service['version']}")
            if 'product' in service:
                lines.append(f"      Product: {service['product']}")
            if 'extrainfo' in service:
                lines.append(f"      Extra Info: {service['extrainfo']}")
                
            lines.append("")
            
        return lines
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate master text report"""
        filename = kwargs.get('filename')
        if not filename:
            target = kwargs.get('target', 'unknown')
            filename = self.generate_filename(target, 'master')
        elif not filename.endswith('.txt'):
            filename += '.txt'
        
        output_path = self.get_output_path(filename)
        target = kwargs.get('target', 'Unknown Target')
        
        # Generate comprehensive text report
        lines = []
        
        # Professional header
        lines.append("╔" + "=" * 78 + "╗")
        lines.append(f"║ IPCRAWLER MASTER REPORT FOR {target.upper():<44} ║")
        lines.append("╠" + "=" * 78 + "╣")
        lines.append(f"║ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<64} ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")
        
        # Process each workflow section with structured formatting
        workflow_sections = ['nmap_fast_01', 'nmap_02', 'http_03', 'mini_spider_04', 'smartlist_05']
        
        for section in workflow_sections:
            if section in data and data[section]:
                section_name = section.replace('_', ' ').title()
                lines.append(f"📋 {section_name}")
                lines.append("═" * (len(section_name) + 3))
                lines.append("")
                
                section_data = data[section]
                
                # Special formatting for different workflow types
                if section.startswith('nmap') and 'services' in section_data:
                    lines.append("🔍 Discovered Services:")
                    lines.extend(self._format_service_data(section_data['services']))
                    
                elif section == 'http_03' and 'http_services' in section_data:
                    lines.append("🌐 HTTP Services Analysis:")
                    lines.extend(self._format_dict_data(section_data['http_services']))
                    
                elif section == 'mini_spider_04' and 'discovered_urls' in section_data:
                    urls = section_data['discovered_urls']
                    lines.append(f"🕷️ Spider Crawling Results ({len(urls)} URLs found):")
                    lines.extend(self._format_dict_data(section_data))
                    
                elif section == 'smartlist_05' and 'wordlist_recommendations' in section_data:
                    recs = section_data['wordlist_recommendations']
                    lines.append(f"📚 Wordlist Recommendations ({len(recs)} services):")
                    lines.extend(self._format_dict_data(section_data))
                    
                else:
                    # Generic formatting for other data
                    lines.extend(self._format_dict_data(section_data))
                
                lines.append("")
        
        # Add any additional sections not in standard workflows
        for key, value in data.items():
            if key not in workflow_sections and key not in ['generated_at', 'format', 'version', 'target']:
                section_name = key.replace('_', ' ').title()
                lines.append(f"📊 {section_name}")
                lines.append("═" * (len(section_name) + 3))
                lines.append("")
                lines.extend(self._format_dict_data(value))
                lines.append("")
        
        # Add footer summary
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║ SCAN SUMMARY                                                              ║")
        lines.append("╠" + "=" * 78 + "╣")
        
        # Count results across workflows
        total_services = 0
        total_urls = 0
        total_wordlists = 0
        
        for section in workflow_sections:
            if section in data:
                section_data = data[section]
                if 'services' in section_data:
                    total_services += len(section_data['services'])
                if 'discovered_urls' in section_data:
                    total_urls += len(section_data['discovered_urls'])
                if 'wordlist_recommendations' in section_data:
                    total_wordlists += sum(len(rec.get('top_wordlists', [])) for rec in section_data['wordlist_recommendations'])
        
        lines.append(f"║ • Total services discovered: {total_services:<49} ║")
        lines.append(f"║ • Total URLs found: {total_urls:<57} ║") 
        lines.append(f"║ • Total wordlists recommended: {total_wordlists:<44} ║")
        lines.append(f"║ • Target: {target:<67} ║")
        lines.append("╚" + "=" * 78 + "╝")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def get_format_name(self) -> str:
        """Get the report format name"""
        return "MASTER_TXT"