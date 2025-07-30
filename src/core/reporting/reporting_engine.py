"""
Simplified IPCrawler Reporting Engine
Generates organized, accurate reports in clean TXT format only
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from ..ui.console import console


@dataclass
class WorkspaceStructure:
    """Defines the clean workspace structure"""
    root: Path
    raw_data: Path
    reports: Path
    manifest: Path
    
    @classmethod
    def create(cls, workspace_path: Path) -> 'WorkspaceStructure':
        """Create workspace structure with proper directories"""
        root = workspace_path
        raw_data = root / "raw_data"
        reports = root / "reports"
        manifest = root / "manifest.json"
        
        # Create directories
        raw_data.mkdir(exist_ok=True)
        reports.mkdir(exist_ok=True)
        
        return cls(root=root, raw_data=raw_data, reports=reports, manifest=manifest)


class ReportingEngine:
    """Simplified, accurate reporting engine for IPCrawler"""
    
    def __init__(self):
        self.supported_workflows = {
            'nmap_fast_01': 'nmap_fast.json',
            'nmap_02': 'nmap_detailed.json', 
            'http_03': 'http_scan.json',
            'mini_spider_04': 'spider_crawl.json',
            'smartlist_05': 'smartlist.json'
        }
    
    def generate_complete_reports(self, workspace_path: Path, workflow_data: Dict[str, Any], 
                                 target: str) -> Dict[str, Path]:
        """Generate complete reporting suite for a target scan"""
        console.info(f"Generating reports for {target} in {workspace_path.name}")
        
        # Create clean workspace structure
        structure = WorkspaceStructure.create(workspace_path)
        
        # Save raw workflow data
        self._save_raw_data(structure, workflow_data)
        
        # Generate human-readable reports
        generated_reports = {}
        
        # 1. Executive Summary (main entry point)
        summary_path = self._generate_summary_report(structure, workflow_data, target)
        if summary_path:
            generated_reports['summary'] = summary_path
        
        # 2. Services Analysis
        services_path = self._generate_services_report(structure, workflow_data, target)
        if services_path:
            generated_reports['services'] = services_path
        
        # 3. Web Analysis
        web_path = self._generate_web_analysis_report(structure, workflow_data, target)
        if web_path:
            generated_reports['web_analysis'] = web_path
        
        # 4. URLs Discovered
        urls_path = self._generate_urls_report(structure, workflow_data, target)
        if urls_path:
            generated_reports['urls'] = urls_path
        
        # 5. Wordlist Recommendations
        wordlist_path = self._generate_wordlist_report(structure, workflow_data, target)  
        if wordlist_path:
            generated_reports['wordlists'] = wordlist_path
        
        # 6. Generate manifest
        manifest_path = self._generate_manifest(structure, generated_reports, workflow_data, target)
        if manifest_path:
            generated_reports['manifest'] = manifest_path
        
        console.success(f"Generated {len(generated_reports)} report files")
        return generated_reports
    
    def _save_raw_data(self, structure: WorkspaceStructure, workflow_data: Dict[str, Any]) -> None:
        """Save raw workflow data as clean JSON files"""
        for workflow_key, filename in self.supported_workflows.items():
            if workflow_key in workflow_data:
                data = workflow_data[workflow_key]
                if data and isinstance(data, dict):
                    file_path = structure.raw_data / filename
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, default=self._json_serializer)
                    except Exception as e:
                        console.warning(f"Failed to save {filename}: {e}")
    
    def _generate_summary_report(self, structure: WorkspaceStructure, workflow_data: Dict[str, Any], 
                                target: str) -> Optional[Path]:
        """Generate executive summary - main entry point"""
        report_path = structure.reports / "summary.txt"
        
        try:
            lines = []
            
            # Professional header
            lines.append("╔" + "=" * 78 + "╗")
            lines.append(f"║ EXECUTIVE SUMMARY - {target.upper():<59} ║")
            lines.append("╠" + "=" * 78 + "╣")
            lines.append(f"║ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<64} ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")
            
            lines.append("🎯 CRITICAL FINDINGS")
            lines.append("=" * 40)
            lines.append("")
            
            # Extract key findings from each workflow
            self._add_nmap_summary(lines, workflow_data)
            self._add_http_summary(lines, workflow_data)
            self._add_spider_summary(lines, workflow_data)
            self._add_wordlist_summary(lines, workflow_data)
            
            # File organization guide
            lines.append("")
            lines.append("📁 REPORT ORGANIZATION")
            lines.append("=" * 40)
            lines.append("• summary.txt (this file) - Executive overview and key findings")
            lines.append("• services.txt - Detailed port and service analysis") 
            lines.append("• web_analysis.txt - HTTP services and security findings")
            lines.append("• urls_discovered.txt - All URLs found during crawling")
            lines.append("• wordlist_recommendations.txt - Targeted wordlists with full paths")
            lines.append("• raw_data/ - Original JSON output from each workflow")
            lines.append("• manifest.json - Complete file inventory and metadata")
            lines.append("")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return report_path
        except Exception as e:
            console.error(f"Failed to generate summary report: {e}")
            return None
    
    def _add_nmap_summary(self, lines: List[str], workflow_data: Dict[str, Any]) -> None:
        """Add nmap findings to summary - show ALL services"""
        # Check both nmap workflows
        all_services = []
        
        for workflow in ['nmap_fast_01', 'nmap_02']:
            if workflow in workflow_data and workflow_data[workflow].get('success'):
                data = workflow_data[workflow].get('data', {})
                if 'hosts' in data:
                    for host in data['hosts']:
                        all_services.extend(host.get('ports', []))
                elif 'services' in data:
                    all_services.extend(data['services'])
        
        if all_services:
            # Deduplicate services by port number
            seen_ports = set()
            unique_services = []
            for service in all_services:
                port = service.get('port')
                if port and port not in seen_ports:
                    seen_ports.add(port)
                    unique_services.append(service)
            
            open_services = [s for s in unique_services if s.get('state') == 'open']
            lines.append(f"🔍 Port Scan Results: {len(open_services)} open ports found")
            lines.append("")
            
            # Show ALL services with full details
            for service in sorted(open_services, key=lambda x: x.get('port', 0)):
                port = service.get('port', 'unknown')
                service_name = service.get('service', 'unknown')
                version = service.get('version', '')
                product = service.get('product', '')
                
                # Build detailed service line
                service_line = f"  • Port {port}/tcp - {service_name}"
                if product:
                    service_line += f" ({product}"
                    if version:
                        service_line += f" {version}"
                    service_line += ")"
                elif version:
                    service_line += f" ({version})"
                
                lines.append(service_line)
            lines.append("")
    
    def _add_http_summary(self, lines: List[str], workflow_data: Dict[str, Any]) -> None:
        """Add HTTP findings to summary - show ALL details"""
        if 'http_03' in workflow_data and workflow_data['http_03'].get('success'):
            data = workflow_data['http_03'].get('data', {})
            
            http_services = data.get('http_services', [])
            if http_services:
                lines.append(f"🌐 Web Services: {len(http_services)} HTTP endpoints discovered")
                lines.append("")
                
                # Show ALL HTTP services with details
                for service in http_services:
                    url = service.get('url', 'Unknown URL')
                    status = service.get('status_code', 'Unknown')
                    title = service.get('title', 'No title')
                    tech = service.get('detected_technology') or service.get('technology', 'Unknown')
                    
                    lines.append(f"  • {url}")
                    lines.append(f"    Status: {status} | Title: {title}")
                    lines.append(f"    Technology: {tech}")
                    
                    # Security issues if present
                    security = service.get('security_analysis', {})
                    if security:
                        for issue, details in security.items():
                            lines.append(f"    ⚠️  {issue}: {details}")
                
                lines.append("")
    
    def _add_spider_summary(self, lines: List[str], workflow_data: Dict[str, Any]) -> None:
        """Add spider crawling summary - show interesting findings"""
        if 'mini_spider_04' in workflow_data and workflow_data['mini_spider_04'].get('success'):
            data = workflow_data['mini_spider_04'].get('data', {})
            
            discovered_urls = data.get('discovered_urls', [])
            if discovered_urls:
                lines.append(f"🕷️ Web Crawling: {len(discovered_urls)} URLs discovered")
                lines.append("")
                
                # Show interesting findings directly
                interesting = data.get('interesting_findings', [])
                if interesting:
                    lines.append("  Interesting Findings:")
                    for finding in interesting:
                        if isinstance(finding, dict):
                            url = finding.get('url', 'Unknown URL')
                            reason = finding.get('reason', 'No reason provided')
                            lines.append(f"  • {url}")
                            lines.append(f"    → {reason}")
                        else:
                            lines.append(f"  • {finding}")
                
                # Show categorized URL summary
                categorized = data.get('categorized_results', {})
                if categorized:
                    lines.append("")
                    lines.append("  URL Categories:")
                    for category, urls in categorized.items():
                        if urls:
                            lines.append(f"  • {category}: {len(urls)} URLs")
                
                lines.append("")
    
    def _add_wordlist_summary(self, lines: List[str], workflow_data: Dict[str, Any]) -> None:
        """Add wordlist recommendations summary - show actual wordlists"""
        if 'smartlist_05' in workflow_data and workflow_data['smartlist_05'].get('success'):
            data = workflow_data['smartlist_05'].get('data', {})
            
            recommendations = data.get('wordlist_recommendations', [])
            if recommendations:
                lines.append(f"📚 Wordlist Intelligence: {len(recommendations)} services analyzed")
                lines.append("")
                
                # Show actual wordlist recommendations
                for rec in recommendations:
                    service = rec.get('service', 'Unknown')
                    port = rec.get('port', 'Unknown')
                    tech = rec.get('detected_technology', '')
                    confidence = rec.get('confidence', 'LOW')
                    
                    service_line = f"  Port {port}"
                    if tech:
                        service_line += f" ({tech})"
                    service_line += f" - {confidence} confidence:"
                    lines.append(service_line)
                    
                    # Show top wordlists
                    wordlists = rec.get('top_wordlists', [])
                    for wl in wordlists[:3]:  # Show top 3 per service
                        wl_name = wl.get('wordlist', 'Unknown')
                        wl_confidence = wl.get('confidence', 'LOW')
                        lines.append(f"    • {wl_name} [{wl_confidence}]")
                
                lines.append("")
    
    def _generate_services_report(self, structure: WorkspaceStructure, workflow_data: Dict[str, Any],
                                 target: str) -> Optional[Path]:
        """Generate detailed services analysis"""
        report_path = structure.reports / "services.txt"
        
        try:
            lines = []
            lines.append("╔" + "=" * 78 + "╗")
            lines.append(f"║ SERVICES ANALYSIS - {target.upper():<58} ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")
            
            # Collect all services from nmap scans
            all_services = []
            for workflow in ['nmap_fast_01', 'nmap_02']:
                if workflow in workflow_data and workflow_data[workflow].get('success'):
                    data = workflow_data[workflow].get('data', {})
                    if 'hosts' in data:
                        for host in data['hosts']:
                            for port in host.get('ports', []):
                                port['scan_type'] = 'fast' if workflow == 'nmap_fast_01' else 'detailed'
                                all_services.append(port)
                    elif 'services' in data:
                        for service in data['services']:
                            service['scan_type'] = 'fast' if workflow == 'nmap_fast_01' else 'detailed'
                            all_services.append(service)
            
            if not all_services:
                lines.append("❌ No service data available")
                lines.append("Possible causes:")
                lines.append("• Nmap scans were not successful")
                lines.append("• Target was not responsive")
                lines.append("• Insufficient privileges for scan")
            else:
                # Group by port number
                services_by_port = {}
                for service in all_services:
                    port = service.get('port', 'unknown')
                    if port not in services_by_port:
                        services_by_port[port] = []
                    services_by_port[port].append(service)
                
                lines.append(f"📊 DISCOVERED SERVICES ({len(services_by_port)} unique ports)")
                lines.append("=" * 50)
                lines.append("")
                
                # Sort by port number
                for port in sorted(services_by_port.keys(), key=lambda x: int(x) if str(x).isdigit() else 99999):
                    services = services_by_port[port]
                    primary_service = services[0]  # Use first/best service info
                    
                    state = primary_service.get('state', 'unknown')
                    service_name = primary_service.get('service', 'unknown')
                    protocol = primary_service.get('protocol', 'tcp')
                    
                    lines.append(f"🔍 Port {port}/{protocol} - {service_name}")
                    lines.append(f"   State: {state}")
                    
                    if 'version' in primary_service:
                        lines.append(f"   Version: {primary_service['version']}")
                    if 'product' in primary_service:
                        lines.append(f"   Product: {primary_service['product']}")
                    if 'extrainfo' in primary_service:
                        lines.append(f"   Extra Info: {primary_service['extrainfo']}")
                    
                    # Show scan type
                    scan_types = set(s.get('scan_type', 'unknown') for s in services)
                    lines.append(f"   Detected by: {', '.join(scan_types)} scan")
                    lines.append("")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return report_path
        except Exception as e:
            console.error(f"Failed to generate services report: {e}")
            return None
    
    def _generate_web_analysis_report(self, structure: WorkspaceStructure, workflow_data: Dict[str, Any],
                                     target: str) -> Optional[Path]:
        """Generate web services analysis"""
        report_path = structure.reports / "web_analysis.txt"
        
        try:
            lines = []
            lines.append("╔" + "=" * 78 + "╗")
            lines.append(f"║ WEB SERVICES ANALYSIS - {target.upper():<52} ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")
            
            if 'http_03' not in workflow_data or not workflow_data['http_03'].get('success'):
                lines.append("❌ No HTTP scan data available")
                lines.append("HTTP workflow was not executed or failed")
            else:
                data = workflow_data['http_03'].get('data', {})
                http_services = data.get('http_services', [])
                
                if not http_services:
                    lines.append("ℹ️ No HTTP services discovered")
                    lines.append("This could mean:")
                    lines.append("• No web services are running")
                    lines.append("• Services are not accessible")
                    lines.append("• HTTP scan configuration needs adjustment")
                else:
                    lines.append(f"🌐 HTTP SERVICES DISCOVERED ({len(http_services)})")
                    lines.append("=" * 50)
                    lines.append("")
                    
                    for i, service in enumerate(http_services, 1):
                        url = service.get('url', 'Unknown URL')
                        status = service.get('status_code', 'No status')
                        title = service.get('title', 'No title')
                        server = service.get('server', 'Unknown server')
                        tech = service.get('detected_technology') or service.get('technology', 'Unknown')
                        
                        lines.append(f"[{i}] {url}")
                        lines.append(f"    Status: {status}")
                        lines.append(f"    Title: {title}")
                        lines.append(f"    Server: {server}")
                        lines.append(f"    Technology: {tech}")
                        
                        # Security headers analysis
                        headers = service.get('security_headers', {})
                        if headers:
                            lines.append("    Security Headers:")
                            for header, value in headers.items():
                                status_icon = "✓" if value else "❌"
                                lines.append(f"      {status_icon} {header}: {value}")
                        
                        # Additional security findings
                        security = service.get('security_analysis', {})
                        if security:
                            lines.append("    Security Analysis:")
                            for finding, details in security.items():
                                lines.append(f"      • {finding}: {details}")
                        
                        lines.append("")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return report_path
        except Exception as e:
            console.error(f"Failed to generate web analysis report: {e}")
            return None
    
    def _generate_urls_report(self, structure: WorkspaceStructure, workflow_data: Dict[str, Any],
                             target: str) -> Optional[Path]:
        """Generate URLs discovered report"""
        report_path = structure.reports / "urls_discovered.txt"
        
        try:
            lines = []
            lines.append("╔" + "=" * 78 + "╗")
            lines.append(f"║ URLS DISCOVERED - {target.upper():<60} ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")
            
            if 'mini_spider_04' not in workflow_data or not workflow_data['mini_spider_04'].get('success'):
                lines.append("❌ No spider crawling data available")
                lines.append("Mini Spider workflow was not executed or failed")
            else:
                data = workflow_data['mini_spider_04'].get('data', {})
                discovered_urls = data.get('discovered_urls', [])
                
                if not discovered_urls:
                    lines.append("ℹ️ No URLs discovered during crawling")
                    lines.append("This could mean:")
                    lines.append("• No web services were accessible for crawling")
                    lines.append("• Crawling was blocked by robots.txt or security measures")
                    lines.append("• Target has minimal web content")
                else:
                    lines.append(f"🕷️ DISCOVERED URLS ({len(discovered_urls)} total)")
                    lines.append("=" * 50)
                    lines.append("")
                    
                    # Show categorized results if available
                    categorized = data.get('categorized_results', {})
                    if categorized:
                        for category, urls in categorized.items():
                            if urls:
                                lines.append(f"📂 {category.upper()} ({len(urls)} URLs)")
                                lines.append("-" * 30)
                                for url_data in urls[:10]:  # Show first 10 per category
                                    if isinstance(url_data, dict):
                                        url = url_data.get('url', str(url_data))
                                    else:
                                        url = str(url_data)
                                    lines.append(f"  • {url}")
                                
                                if len(urls) > 10:
                                    lines.append(f"  ... and {len(urls) - 10} more")
                                lines.append("")
                    else:
                        # Show all URLs if no categorization
                        lines.append("📂 ALL DISCOVERED URLS")
                        lines.append("-" * 30)
                        for url_data in discovered_urls:
                            if isinstance(url_data, dict):
                                url = url_data.get('url', str(url_data))
                            else:
                                url = str(url_data)
                            lines.append(f"  • {url}")
                        lines.append("")
                    
                    # Show interesting findings
                    interesting = data.get('interesting_findings', [])
                    if interesting:
                        lines.append("🎯 INTERESTING FINDINGS")
                        lines.append("=" * 30)
                        for finding in interesting:
                            if isinstance(finding, dict):
                                url = finding.get('url', 'Unknown URL')
                                reason = finding.get('reason', 'No reason provided')
                                lines.append(f"• {url}")
                                lines.append(f"  Reason: {reason}")
                            else:
                                lines.append(f"• {finding}")
                        lines.append("")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return report_path
        except Exception as e:
            console.error(f"Failed to generate URLs report: {e}")
            return None
    
    def _generate_wordlist_report(self, structure: WorkspaceStructure, workflow_data: Dict[str, Any],
                                 target: str) -> Optional[Path]:
        """Generate wordlist recommendations with full paths"""
        report_path = structure.reports / "wordlist_recommendations.txt"
        
        try:
            lines = []
            lines.append("╔" + "=" * 78 + "╗")
            lines.append(f"║ WORDLIST RECOMMENDATIONS - {target.upper():<49} ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")
            
            if 'smartlist_05' not in workflow_data or not workflow_data['smartlist_05'].get('success'):
                lines.append("❌ No SmartList analysis available")
                lines.append("SmartList workflow was not executed or failed")
                lines.append("")
                lines.append("To get wordlist recommendations:")
                lines.append("1. Ensure services are discovered (run nmap scans)")
                lines.append("2. Run HTTP analysis to detect technologies")
                lines.append("3. Execute SmartList workflow for intelligent recommendations")
            else:
                data = workflow_data['smartlist_05'].get('data', {})
                recommendations = data.get('wordlist_recommendations', [])
                
                if not recommendations:
                    lines.append("ℹ️ No wordlist recommendations generated")
                    lines.append("This could mean:")
                    lines.append("• No services were detected for analysis")
                    lines.append("• SmartList database is not available")
                    lines.append("• Service detection was insufficient for matching")
                else:
                    lines.append(f"📚 TARGETED WORDLIST RECOMMENDATIONS ({len(recommendations)} services)")
                    lines.append("=" * 60)
                    lines.append("")
                    
                    for i, rec in enumerate(recommendations, 1):
                        service = rec.get('service', 'Unknown Service')
                        service_name = rec.get('service_name', '')
                        detected_tech = rec.get('detected_technology', '')
                        confidence = rec.get('confidence', 'LOW')
                        port = rec.get('port')
                        
                        # Service header
                        header = f"[{i}] {service}"
                        if service_name and service_name != 'unknown':
                            header += f" ({service_name})"
                        if port:
                            header += f" on port {port}"
                        if detected_tech:
                            header += f" - {detected_tech} detected"
                        
                        lines.append("┌" + "─" * (len(header) + 2) + "┐")
                        lines.append(f"│ {header} │")
                        lines.append("└" + "─" * (len(header) + 2) + "┘")
                        
                        confidence_icon = {"HIGH": "✓", "MEDIUM": "⚠", "LOW": "?"}.get(confidence.upper(), "•")
                        lines.append(f"Confidence: {confidence_icon} {confidence}")
                        lines.append("")
                        
                        wordlists = rec.get('top_wordlists', [])
                        if not wordlists:
                            lines.append("  ⚠ No specific wordlists recommended")
                            lines.append("    Consider running additional scans for better detection")
                        else:
                            lines.append(f"  Recommended Wordlists ({len(wordlists)}):")
                            lines.append("")
                            
                            for j, wl in enumerate(wordlists, 1):
                                wordlist_name = wl.get('wordlist', 'Unknown')
                                wl_confidence = wl.get('confidence', 'LOW')
                                reason = wl.get('reason', 'No reason provided')
                                wl_path = wl.get('path', '')
                                
                                wl_icon = {"HIGH": "✓", "MEDIUM": "⚠", "LOW": "?"}.get(wl_confidence.upper(), "•")
                                lines.append(f"    {j}. [{wl_icon} {wl_confidence}] {wordlist_name}")
                                
                                # Show path with validation
                                if wl_path:
                                    path_obj = Path(wl_path)
                                    if path_obj.exists():
                                        lines.append(f"       📂 Path: {wl_path}")
                                        try:
                                            size_mb = path_obj.stat().st_size / (1024 * 1024)
                                            lines.append(f"       📊 Size: {size_mb:.1f} MB")
                                        except:
                                            pass
                                    else:
                                        lines.append(f"       ⚠️  Path: {wl_path} (File not accessible)")
                                else:
                                    lines.append(f"       📝 Path: [Not resolved from catalog - wordlist name only]")
                                
                                lines.append(f"       💡 Reason: {reason}")
                                lines.append("")
                        
                        lines.append("")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return report_path
        except Exception as e:
            console.error(f"Failed to generate wordlist report: {e}")
            return None
    
    def _generate_manifest(self, structure: WorkspaceStructure, generated_reports: Dict[str, Path],
                          workflow_data: Dict[str, Any], target: str) -> Optional[Path]:
        """Generate workspace manifest with file inventory"""
        try:
            manifest = {
                "target": target,
                "generated_at": datetime.now().isoformat(),
                "workspace_structure": {
                    "raw_data": "JSON output files from each workflow",
                    "reports": "Human-readable TXT analysis files",
                    "manifest.json": "This file - complete workspace inventory"
                },
                "reports": {},
                "raw_data_files": {},
                "workflow_status": {},
                "file_descriptions": {
                    "summary.txt": "Executive summary - START HERE for overview",
                    "services.txt": "Detailed port and service analysis",
                    "web_analysis.txt": "HTTP services and security findings", 
                    "urls_discovered.txt": "All URLs found during crawling",
                    "wordlist_recommendations.txt": "Targeted wordlists with full paths"
                }
            }
            
            # Document generated reports
            for report_type, report_path in generated_reports.items():
                if report_path and report_path.exists() and report_type != 'manifest':
                    relative_path = report_path.relative_to(structure.root)
                    manifest["reports"][report_type] = {
                        "path": str(relative_path),
                        "size_bytes": report_path.stat().st_size,
                        "created_at": datetime.fromtimestamp(report_path.stat().st_ctime).isoformat()
                    }
            
            # Document raw data files
            for workflow_key, filename in self.supported_workflows.items():
                raw_file = structure.raw_data / filename
                if raw_file.exists():
                    manifest["raw_data_files"][workflow_key] = {
                        "filename": filename,
                        "path": f"raw_data/{filename}",
                        "size_bytes": raw_file.stat().st_size,
                        "workflow_success": workflow_data.get(workflow_key, {}).get('success', False)
                    }
            
            # Document workflow execution status
            for workflow_key in self.supported_workflows.keys():
                if workflow_key in workflow_data:
                    workflow_result = workflow_data[workflow_key]
                    manifest["workflow_status"][workflow_key] = {
                        "executed": True,
                        "success": workflow_result.get('success', False),
                        "error": workflow_result.get('error') if not workflow_result.get('success') else None,
                        "execution_time": workflow_result.get('execution_time'),
                        "data_available": bool(workflow_result.get('data'))
                    }
                else:
                    manifest["workflow_status"][workflow_key] = {
                        "executed": False,
                        "success": False,
                        "error": "Workflow not executed",
                        "execution_time": None,
                        "data_available": False
                    }
            
            with open(structure.manifest, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, default=self._json_serializer)
            
            return structure.manifest
        except Exception as e:
            console.error(f"Failed to generate manifest: {e}")
            return None
    
    def _json_serializer(self, obj) -> str:
        """Custom JSON serializer for datetime and other objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)


# Global instance
reporting_engine = ReportingEngine()