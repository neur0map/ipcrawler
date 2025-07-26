"""Centralized Reporting Orchestrator for IPCrawler"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .workspace_manager import workspace_manager
from .manager import ReportManager
from .formats.wordlist_recommendation_reporter import WordlistRecommendationReporter
from .validators import validate_all_workflows


class ReportingOrchestrator:
    """Centralized coordinator for all IPCrawler reporting"""
    
    def __init__(self):
        """Initialize reporting orchestrator"""
        self.workspace_manager = workspace_manager
        self.report_manager = ReportManager()
        self.wordlist_reporter = WordlistRecommendationReporter()
        
        # Track generated files for cleanup and organization
        self.generated_files: Dict[str, List[Path]] = {}
    
    def create_versioned_workspace(self, target: str, enable_versioning: bool = True) -> Path:
        """Create a new versioned workspace for a target"""
        workspace_path = self.workspace_manager.create_workspace(target, enable_versioning)
        return workspace_path
    
    def generate_all_reports(self, workspace_path: Path, workflow_data: Dict[str, Any]) -> Dict[str, Path]:
        """Generate all reports for a complete scan with organized structure"""
        target = workflow_data.get('target', 'unknown')
        generated_reports = {}
        
        # Validate workflow outputs
        validation_errors = validate_all_workflows(workflow_data)
        if validation_errors:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Workflow validation errors found: {validation_errors}")
        
        # Create organized directory structure
        raw_data_dir = workspace_path / "raw_data"
        raw_data_dir.mkdir(exist_ok=True)
        
        # 1. Save individual workflow results in organized raw_data/ directory
        self._save_organized_workflow_results(raw_data_dir, workflow_data)
        
        # 2. Generate executive summary (main file for enumeration)
        summary_path = self._generate_executive_summary(workspace_path, workflow_data, target)
        if summary_path:
            generated_reports['summary'] = summary_path
        
        # 3. Generate detailed technical findings
        detailed_path = self._generate_detailed_findings(workspace_path, workflow_data, target)
        if detailed_path:
            generated_reports['detailed_findings'] = detailed_path
        
        # 4. Generate wordlist recommendations (in workspace root)
        wordlist_path = self._generate_organized_wordlist_recommendations(workspace_path, workflow_data, target)
        if wordlist_path:
            generated_reports['wordlist_recommendations'] = wordlist_path
        
        # 5. Generate reports manifest
        manifest_path = self._generate_reports_manifest(workspace_path, generated_reports, workflow_data, target)
        if manifest_path:
            generated_reports['manifest'] = manifest_path
        
        # 6. Clean up any legacy report structures
        self._cleanup_legacy_structures(workspace_path)
        
        return generated_reports
    
    def generate_workflow_reports(self, workspace_path: Path, workflow_name: str, workflow_data: Dict[str, Any]) -> List[Path]:
        """Generate reports for a single workflow"""
        generated_files = []
        
        result_file = workspace_path / f"{workflow_name}_results.json"
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2, default=self._json_serializer)
            generated_files.append(result_file)
        except Exception as e:
            pass
        
        return generated_files
    
    def generate_master_report_from_workspace(self, workspace_name: str) -> Dict[str, Path]:
        """Generate master report from existing workspace data"""
        workspace_path = self.workspace_manager.get_workspace_path(workspace_name)
        if not workspace_path.exists():
            return {}
        
        workflow_data = self._load_workspace_data(workspace_path)
        if not workflow_data:
            return {}
        
        target = workflow_data.get('target', workspace_name)
        
        master_report_path = self._generate_master_report(workspace_path, workflow_data, target)
        wordlist_path = self._generate_wordlist_recommendations(workspace_path, workflow_data, target)
        
        results = {}
        if master_report_path:
            results['master_report'] = master_report_path
        if wordlist_path:
            results['wordlist_recommendations'] = wordlist_path
        
        return results
    
    def list_workspaces(self, target: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available workspaces"""
        return self.workspace_manager.list_workspaces(target)
    
    def clean_old_workspaces(self, target: str, keep_count: int = 5) -> List[Path]:
        """Clean old workspaces for a target"""
        return self.workspace_manager.clean_old_workspaces(target, keep_count)
    
    def _save_organized_workflow_results(self, raw_data_dir: Path, workflow_data: Dict[str, Any]) -> None:
        """Save individual workflow results as organized JSON files"""
        workflow_mappings = {
            'nmap_fast_01': 'nmap_results.json',
            'nmap_02': 'nmap_detailed_results.json', 
            'http_03': 'http_results.json',
            'mini_spider_04': 'spider_results.json',
            'smartlist_05': 'smartlist_results.json'
        }
        
        for workflow_name, filename in workflow_mappings.items():
            if workflow_name in workflow_data:
                result_file = raw_data_dir / filename
                try:
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(workflow_data[workflow_name], f, indent=2, default=self._json_serializer)
                except Exception:
                    continue
    
    def _generate_master_report(self, workspace_path: Path, workflow_data: Dict[str, Any], target: str) -> Optional[Path]:
        """Generate master TXT report"""
        try:
            # Set output directory to workspace
            original_output_dir = self.report_manager.output_dir
            self.report_manager.set_output_directory(workspace_path)
            try:
                master_report_path = self.report_manager.generate_master_report(
                    data=workflow_data,
                    target=target,
                    format_type='txt'
                )
                return master_report_path
            finally:
                # Restore original output directory
                self.report_manager.set_output_directory(original_output_dir)
        except Exception:
            return None
    
    def _generate_wordlist_recommendations(self, workspace_path: Path, workflow_data: Dict[str, Any], target: str) -> Optional[Path]:
        """Generate wordlist recommendations file"""
        try:
            # Check if we have SmartList data
            if 'smartlist_05' not in workflow_data:
                return None
            
            wordlist_path = self.wordlist_reporter.generate(
                data=workflow_data,
                target=target,
                enable_versioning=False  # No versioning in orchestrated mode
            )
            
            return wordlist_path
        except Exception:
            return None
    
    def _generate_spider_files(self, workspace_path: Path, workflow_data: Dict[str, Any]) -> Dict[str, Path]:
        """Generate Mini Spider specific files"""
        spider_files = {}
        
        if 'mini_spider_04' not in workflow_data:
            return spider_files
        
        spider_data = workflow_data['mini_spider_04']
        
        # Generate discovered URLs file
        if 'discovered_urls' in spider_data:
            try:
                urls_file = workspace_path / "discovered_urls.txt"
                with open(urls_file, 'w', encoding='utf-8') as f:
                    for url_data in spider_data['discovered_urls']:
                        if isinstance(url_data, dict):
                            url = url_data.get('url', str(url_data))
                        else:
                            url = str(url_data)
                        f.write(f"{url}\n")
                spider_files['discovered_urls'] = urls_file
            except Exception:
                pass
        
        # Generate categorized URL files
        if 'categorized_results' in spider_data:
            try:
                for category, urls in spider_data['categorized_results'].items():
                    category_file = workspace_path / f"urls_{category.lower().replace(' ', '_')}.txt"
                    with open(category_file, 'w', encoding='utf-8') as f:
                        for url_data in urls:
                            if isinstance(url_data, dict):
                                url = url_data.get('url', str(url_data))
                            else:
                                url = str(url_data)
                            f.write(f"{url}\n")
                    spider_files[f'urls_{category}'] = category_file
            except Exception:
                pass
            
        # Generate interesting findings file
        if 'interesting_findings' in spider_data:
            try:
                findings_file = workspace_path / "interesting_findings.txt"
                with open(findings_file, 'w', encoding='utf-8') as f:
                    for finding in spider_data['interesting_findings']:
                        if isinstance(finding, dict):
                            url = finding.get('url', 'Unknown')
                            reason = finding.get('reason', 'No reason provided')
                            f.write(f"{url} - {reason}\n")
                spider_files['interesting_findings'] = findings_file
            except Exception:
                pass
        
        # Generate enhanced analysis JSON file if available
        if 'enhanced_analysis' in spider_data:
            try:
                enhanced_file = workspace_path / "enhanced_analysis.json"
                with open(enhanced_file, 'w', encoding='utf-8') as f:
                    json.dump(spider_data['enhanced_analysis'], f, indent=2, default=self._json_serializer)
                spider_files['enhanced_analysis'] = enhanced_file
            except Exception:
                pass
        
        # Generate critical intelligence summary
        if 'enhanced_analysis' in spider_data and 'critical_intelligence' in spider_data['enhanced_analysis']:
            try:
                critical_intel = spider_data['enhanced_analysis']['critical_intelligence']
                critical_file = workspace_path / "critical_intelligence.txt"
                with open(critical_file, 'w', encoding='utf-8') as f:
                    f.write("# Critical Intelligence Summary\n\n")
                    
                    for category, findings in critical_intel.items():
                        if findings:
                            f.write(f"## {category.replace('_', ' ').title()}\n")
                            if isinstance(findings, dict):
                                for url, data in findings.items():
                                    f.write(f"- {url}\n")
                                    if isinstance(data, dict) and 'security_issues' in data:
                                        for issue in data['security_issues']:
                                            f.write(f"  ! {issue.get('type', 'unknown')}: {issue.get('match', '')}\n")
                            elif isinstance(findings, list):
                                for item in findings:
                                    if isinstance(item, dict):
                                        f.write(f"- {item.get('url', item)}\n")
                                    else:
                                        f.write(f"- {item}\n")
                            f.write("\n")
                spider_files['critical_intelligence'] = critical_file
            except Exception:
                pass
        
        return spider_files
    
    def _load_workspace_data(self, workspace_path: Path) -> Dict[str, Any]:
        """Load workflow data from workspace files"""
        workflow_data = {}
        
        workflow_files = {
            'nmap_fast_01': 'nmap_fast_01_results.json',
            'nmap_02': 'nmap_02_results.json',
            'http_03': 'http_03_results.json', 
            'mini_spider_04': 'mini_spider_04_results.json',
            'smartlist_05': 'smartlist_05_results.json'
        }
        
        for workflow_name, filename in workflow_files.items():
            result_file = workspace_path / filename
            if result_file.exists():
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        workflow_data[workflow_name] = json.load(f)
                except Exception:
                    continue
        
        # Try to extract target from data
        target = None
        for data in workflow_data.values():
            if isinstance(data, dict) and 'target' in data:
                target = data['target']
                break
        
        if not target:
            # Infer from workspace name
            workspace_name = workspace_path.name
            if '_' in workspace_name:
                target = workspace_name.split('_')[0]
            else:
                target = workspace_name
        
        if target:
            workflow_data['target'] = target
        
        return workflow_data
    
    def _generate_executive_summary(self, workspace_path: Path, workflow_data: Dict[str, Any], target: str) -> Optional[Path]:
        """Generate executive summary - main file for enumeration with critical info"""
        try:
            summary_path = workspace_path / "summary.txt"
            lines = []
            
            # Professional header
            lines.append("╔" + "=" * 78 + "╗")
            lines.append(f"║ EXECUTIVE SUMMARY - {target.upper():<59} ║")
            lines.append("╠" + "=" * 78 + "╣")
            lines.append(f"║ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<64} ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")
            
            # Critical enumeration data first
            lines.append("🎯 CRITICAL ENUMERATION DATA")
            lines.append("=" * 40)
            lines.append("")
            
            # Service summary
            all_services = []
            for workflow in ['nmap_fast_01', 'nmap_02']:
                if workflow in workflow_data and workflow_data[workflow].get('success'):
                    for host in workflow_data[workflow].get('data', {}).get('hosts', []):
                        all_services.extend(host.get('ports', []))
            
            if all_services:
                lines.append("🔍 Open Ports & Services:")
                for service in all_services:
                    port = service.get('port')
                    state = service.get('state', 'unknown')
                    service_name = service.get('service', 'unknown')
                    version = service.get('version', '')
                    if state == 'open':
                        version_info = f" ({version})" if version else ""
                        lines.append(f"  • {port}/tcp - {service_name}{version_info}")
                lines.append("")
            
            # HTTP services specifically
            if 'http_03' in workflow_data and workflow_data['http_03'].get('success'):
                http_data = workflow_data['http_03'].get('data', {})
                if 'http_services' in http_data:
                    lines.append("🌐 HTTP Services Details:")
                    for service in http_data['http_services']:
                        url = service.get('url', 'Unknown')
                        title = service.get('title', '')
                        server = service.get('server', '')
                        status = service.get('status_code', '')
                        
                        lines.append(f"  • {url}")
                        if title:
                            lines.append(f"    Title: {title}")
                        if server:
                            lines.append(f"    Server: {server}")
                        if status:
                            lines.append(f"    Status: {status}")
                    lines.append("")
            
            # Technology detection
            detected_techs = set()
            if 'http_03' in workflow_data:
                http_data = workflow_data['http_03'].get('data', {})
                for service in http_data.get('http_services', []):
                    tech = service.get('detected_technology')
                    if tech:
                        detected_techs.add(tech)
            
            if detected_techs:
                lines.append("⚡ Detected Technologies:")
                for tech in sorted(detected_techs):
                    lines.append(f"  • {tech}")
                lines.append("")
            
            # Wordlist recommendations summary
            if 'smartlist_05' in workflow_data and workflow_data['smartlist_05'].get('success'):
                smartlist_data = workflow_data['smartlist_05'].get('data', {})
                if 'wordlist_recommendations' in smartlist_data:
                    lines.append("📚 TOP WORDLIST RECOMMENDATIONS:")
                    for rec in smartlist_data['wordlist_recommendations'][:3]:  # Top 3 services
                        service = rec.get('service', 'Unknown')
                        confidence = rec.get('confidence', 'LOW')
                        top_wordlists = rec.get('top_wordlists', [])[:2]  # Top 2 wordlists per service
                        
                        lines.append(f"  {service} [{confidence} confidence]:")
                        for wl in top_wordlists:
                            wordlist_name = wl.get('wordlist', 'Unknown')
                            wl_path = wl.get('path', 'Path not resolved')
                            lines.append(f"    • {wordlist_name}")
                            lines.append(f"      {wl_path}")
                    lines.append("")
            
            # Spider findings (if available)
            if 'mini_spider_04' in workflow_data and workflow_data['mini_spider_04'].get('success'):
                spider_data = workflow_data['mini_spider_04'].get('data', {})
                discovered_urls = spider_data.get('discovered_urls', [])
                if discovered_urls:
                    lines.append(f"🕷️ Spider Crawling: {len(discovered_urls)} URLs discovered")
                    if 'interesting_findings' in spider_data:
                        interesting = spider_data['interesting_findings'][:5]  # Top 5 interesting
                        if interesting:
                            lines.append("  Top interesting findings:")
                            for finding in interesting:
                                if isinstance(finding, dict):
                                    url = finding.get('url', 'Unknown')
                                    reason = finding.get('reason', '')
                                    lines.append(f"    • {url} - {reason}")
                    lines.append("")
            
            # Quick stats summary
            lines.append("📊 SCAN STATISTICS")
            lines.append("=" * 40)
            total_services = len(all_services)
            total_open = len([s for s in all_services if s.get('state') == 'open'])
            total_urls = 0
            total_wordlists = 0
            
            if 'mini_spider_04' in workflow_data:
                spider_data = workflow_data['mini_spider_04'].get('data', {})
                total_urls = len(spider_data.get('discovered_urls', []))
            
            if 'smartlist_05' in workflow_data:
                smartlist_data = workflow_data['smartlist_05'].get('data', {})
                for rec in smartlist_data.get('wordlist_recommendations', []):
                    total_wordlists += len(rec.get('top_wordlists', []))
            
            lines.append(f"• Total ports scanned: {total_services}")
            lines.append(f"• Open ports found: {total_open}")
            lines.append(f"• URLs discovered: {total_urls}")
            lines.append(f"• Wordlists recommended: {total_wordlists}")
            lines.append("")
            
            lines.append("📁 FILE ORGANIZATION")
            lines.append("=" * 40)
            lines.append("• summary.txt - This executive summary (START HERE)")
            lines.append("• wordlist_recommendations.txt - Full wordlist details with paths")
            lines.append("• detailed_findings.txt - Complete technical analysis")
            lines.append("• raw_data/ - JSON output files for further analysis")
            lines.append("")
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return summary_path
            
        except Exception:
            return None
    
    def _generate_detailed_findings(self, workspace_path: Path, workflow_data: Dict[str, Any], target: str) -> Optional[Path]:
        """Generate detailed technical findings - comprehensive analysis"""
        try:
            # Use the existing master text reporter but with organized naming
            original_output_dir = self.report_manager.output_dir
            self.report_manager.set_output_directory(workspace_path)
            try:
                # Generate using existing master reporter logic
                from .formats.master_text_reporter import MasterTextReporter
                reporter = MasterTextReporter(workspace_path)
                
                detailed_path = reporter.generate(
                    data=workflow_data,
                    target=target,
                    filename='detailed_findings.txt'
                )
                return detailed_path
            finally:
                self.report_manager.set_output_directory(original_output_dir)
        except Exception:
            return None
    
    def _generate_organized_wordlist_recommendations(self, workspace_path: Path, workflow_data: Dict[str, Any], target: str) -> Optional[Path]:
        """Generate wordlist recommendations in workspace root"""
        try:
            # Use the existing wordlist reporter but save to workspace root
            wordlist_path = workspace_path / "wordlist_recommendations.txt"
            
            # Use existing wordlist reporter logic
            reporter = WordlistRecommendationReporter(workspace_path)
            reporter.output_dir = workspace_path  # Override to save in root
            
            return reporter.generate(
                data=workflow_data,
                target=target
            )
        except Exception:
            return None
    
    def _generate_reports_manifest(self, workspace_path: Path, generated_reports: Dict[str, Path], 
                                  workflow_data: Dict[str, Any], target: str) -> Optional[Path]:
        """Generate reports manifest with metadata"""
        try:
            manifest_path = workspace_path / "reports.json"
            
            manifest = {
                "target": target,
                "generated_at": datetime.now().isoformat(),
                "reports": {},
                "raw_data_files": {},
                "statistics": {
                    "total_files": len(generated_reports),
                    "workflows_executed": len([k for k in workflow_data.keys() if k != 'target']),
                    "scan_successful": True
                },
                "file_descriptions": {
                    "summary.txt": "Executive summary with critical enumeration data - START HERE",
                    "detailed_findings.txt": "Complete technical analysis with all workflow details",
                    "wordlist_recommendations.txt": "Wordlist recommendations with full paths and reasoning",
                    "raw_data/": "JSON output files for automated processing and further analysis"
                }
            }
            
            # Add generated report paths
            for report_type, report_path in generated_reports.items():
                if report_path and report_path.exists():
                    relative_path = report_path.relative_to(workspace_path)
                    manifest["reports"][report_type] = {
                        "path": str(relative_path),
                        "size_bytes": report_path.stat().st_size,
                        "created_at": datetime.fromtimestamp(report_path.stat().st_ctime).isoformat()
                    }
            
            # Add raw data files
            raw_data_dir = workspace_path / "raw_data"
            if raw_data_dir.exists():
                for json_file in raw_data_dir.glob("*.json"):
                    relative_path = json_file.relative_to(workspace_path)
                    manifest["raw_data_files"][json_file.stem] = {
                        "path": str(relative_path),
                        "size_bytes": json_file.stat().st_size,
                        "workflow": json_file.stem.replace('_results', '')
                    }
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, default=self._json_serializer)
            
            return manifest_path
            
        except Exception:
            return None
    
    def _cleanup_legacy_structures(self, workspace_path: Path) -> None:
        """Remove legacy report directories and files"""
        legacy_dirs = ['reports', 'nmap_fast_01', 'nmap_02', 'http_03', 'mini_spider_04', 'smartlist_05']
        
        for dir_name in legacy_dirs:
            legacy_dir = workspace_path / dir_name
            if legacy_dir.exists() and legacy_dir.is_dir():
                try:
                    import shutil
                    shutil.rmtree(legacy_dir)
                except Exception:
                    pass
    
    def _json_serializer(self, obj) -> str:
        """Custom JSON serializer for datetime and enum objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)


# Global reporting orchestrator instance
reporting_orchestrator = ReportingOrchestrator()