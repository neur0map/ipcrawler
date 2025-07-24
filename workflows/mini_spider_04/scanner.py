"""Mini Spider Workflow - Custom Path Sniffer with Hakrawler Integration"""
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from workflows.core.base import BaseWorkflow, WorkflowResult
from .models import MiniSpiderResult, CrawledURL, DiscoverySource
from .config import get_spider_config
from .utils import validate_input, deduplicate_urls
from .url_extractor import URLExtractor
from .custom_crawler import CustomCrawler
from .hakrawler_wrapper import HakrawlerWrapper
from .result_processor import ResultProcessor
from .enhanced_analyzer import EnhancedAnalyzer
from .enhanced_reporter import EnhancedReporter
from utils.debug import debug_print


class MiniSpiderScanner(BaseWorkflow):
    """Mini Spider workflow for custom path sniffer with hakrawler integration"""
    
    def __init__(self):
        super().__init__(name="mini_spider_04")
        self.config = get_spider_config()
        
        # Initialize modular components
        self.url_extractor = URLExtractor()
        self.custom_crawler = CustomCrawler()
        self.hakrawler_wrapper = HakrawlerWrapper()
        self.result_processor = ResultProcessor()
        self.enhanced_analyzer = EnhancedAnalyzer()
        self.enhanced_reporter = EnhancedReporter()
        
        # Runtime settings
        self.max_concurrent_crawls = 5
        self.crawl_timeout = 30  # seconds per URL
        self.max_total_urls = 1000  # Prevent infinite loops
        
    def validate_input(self, target: str, **kwargs) -> Tuple[bool, List[str]]:
        """Validate input parameters for mini spider scanning"""
        return validate_input(target, **kwargs)
    
    async def execute(self, target: str, previous_results: Optional[Dict[str, Any]] = None, **kwargs) -> WorkflowResult:
        """Execute mini spider scanning workflow"""
        start_time = datetime.now()
        
        # Validate input
        is_valid, validation_errors = self.validate_input(target, **kwargs)
        if not is_valid:
            return WorkflowResult(
                success=False,
                error=f"Input validation failed: {'; '.join(validation_errors)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )
        
        debug_print(f"Starting mini spider scan for {target}")
        
        # Check tool availability and warn user
        from .config import get_config_manager
        config_manager = get_config_manager()
        
        missing_tools = []
        hakrawler_path = config_manager.tools_available.get('hakrawler')
        if not hakrawler_path:
            missing_tools.append("hakrawler")
        # Tool detection done silently
        
        # Check if httpx is available for custom crawler
        try:
            import httpx
        except ImportError:
            missing_tools.append("httpx")
        
        # Missing tools handled silently
        
        try:
            # Initialize result object
            result = MiniSpiderResult(target=target)
            
            # Phase 1: Extract URLs from workflow_03 results
            if previous_results and 'http_03' in previous_results:
                discovered_urls = await self.url_extractor.extract_from_http_results(
                    previous_results['http_03']
                )
                result.seed_urls.extend(discovered_urls)
                debug_print(f"Extracted {len(discovered_urls)} seed URLs from workflow_03")
            else:
                debug_print("No http_03 results found, using target as seed URL")
                # Create basic seed URLs from target
                seed_urls = self._create_seed_urls(target)
                result.seed_urls.extend(seed_urls)
            
            # Phase 2: Custom path sniffer (parallel with hakrawler)
            # Use already discovered URLs from previous workflow as starting URLs
            all_discovered = result.seed_urls.copy()
            
            # Add new paths discovered by custom crawler
            custom_urls = await self.custom_crawler.discover_paths(
                result.seed_urls, 
                max_concurrent=self.max_concurrent_crawls
            )
            all_discovered.extend(custom_urls)
            
            # Phase 3: Hakrawler discovery (parallel with custom crawler)
            hakrawler_urls = await self.hakrawler_wrapper.run_parallel_discovery(
                result.seed_urls,
                timeout=self.crawl_timeout
            )
            
            # Phase 4: Combine and deduplicate results
            all_discovered_urls = all_discovered + hakrawler_urls
            unique_urls = deduplicate_urls(all_discovered_urls)
            
            # Discovery results processed silently
            
            # Limit total URLs to prevent resource exhaustion
            if len(unique_urls) > self.max_total_urls:
                debug_print(f"Limiting results to {self.max_total_urls} URLs (found {len(unique_urls)})")
                unique_urls = unique_urls[:self.max_total_urls]
            
            result.discovered_urls = unique_urls
            
            # Phase 5: Process and categorize results
            processed_results = await self.result_processor.process_results(
                result.discovered_urls,
                target
            )
            
            result.categorized_results = processed_results['categories']
            result.interesting_findings = processed_results['interesting']
            
            # Handle statistics - reconstruct SpiderStatistics object if it's a dict
            stats_data = processed_results['statistics']
            if isinstance(stats_data, dict):
                from .models import SpiderStatistics
                result.statistics = SpiderStatistics(**stats_data)
            else:
                result.statistics = stats_data
            
            # Phase 6: Enhanced analysis (optional but valuable)
            try:
                enhanced_analysis = await self.enhanced_analyzer.analyze_spider_results(result)
                result.enhanced_analysis = enhanced_analysis
                debug_print("Enhanced analysis completed successfully")
            except Exception as e:
                debug_print(f"Enhanced analysis failed: {str(e)}", level="ERROR")
                result.enhanced_analysis = {'error': str(e)}
            
            # Phase 7: Generate summary and save results
            result.summary = self._generate_summary(result)
            result.execution_time = (datetime.now() - start_time).total_seconds()
            
            # Save to workspace
            await self._save_results_to_workspace(target, result)
            
            # Generate comprehensive reports (always attempt if we have discovered URLs)
            if result.discovered_urls:
                debug_print(f"Attempting to generate reports for {len(result.discovered_urls)} discovered URLs")
                try:
                    workspace_dir = Path("workspaces") / target.replace(':', '_').replace('/', '_')
                    reports_dir = workspace_dir / "reports"
                    # Ensure reports directory exists
                    reports_dir.mkdir(parents=True, exist_ok=True)
                    
                    debug_print(f"Generating reports in: {reports_dir}")
                    debug_print(f"Enhanced analysis available: {hasattr(result, 'enhanced_analysis') and bool(result.enhanced_analysis)}")
                    
                    report_files = self.enhanced_reporter.generate_comprehensive_report(
                        result, 
                        reports_dir,
                        formats=['html', 'json', 'txt']
                    )
                    debug_print(f"Generated {len(report_files)} comprehensive reports: {list(report_files.keys())}")
                except Exception as e:
                    debug_print(f"Report generation failed: {str(e)}", level="ERROR")
                    import traceback
                    debug_print(f"Traceback: {traceback.format_exc()}", level="ERROR")
            else:
                debug_print("No URLs discovered, skipping report generation")
            
            debug_print(f"Mini spider scan completed: {len(result.discovered_urls)} URLs discovered")
            
            # Results processed - output handled by main workflow
            
            return WorkflowResult(
                success=True,
                data=result.to_dict(),
                execution_time=result.execution_time
            )
            
        except Exception as e:
            debug_print(f"Mini spider scan failed: {str(e)}", level="ERROR")
            return WorkflowResult(
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _create_seed_urls(self, target: str) -> List[CrawledURL]:
        """Create basic seed URLs when no workflow_03 results are available"""
        seed_urls = []
        
        # Common protocols and ports
        schemes = ['http', 'https']
        ports = [80, 443, 8080, 8443, 8000, 3000, 5000]
        
        for scheme in schemes:
            for port in ports:
                if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                    url = f"{scheme}://{target}/"
                else:
                    url = f"{scheme}://{target}:{port}/"
                
                crawled_url = CrawledURL(
                    url=url,
                    source=DiscoverySource.SEED,
                    status_code=None,
                    content_type=None,
                    content_length=None,
                    discovered_at=datetime.now()
                )
                seed_urls.append(crawled_url)
        
        return seed_urls
    
    def _generate_summary(self, result: MiniSpiderResult) -> Dict[str, Any]:
        """Generate summary of spider results"""
        return {
            'total_seed_urls': len(result.seed_urls),
            'total_discovered_urls': len(result.discovered_urls),
            'discovery_methods': {
                'custom_crawler': len([u for u in result.discovered_urls if u.source == DiscoverySource.CUSTOM_CRAWLER]),
                'hakrawler': len([u for u in result.discovered_urls if u.source == DiscoverySource.HAKRAWLER]),
                'seed': len([u for u in result.discovered_urls if u.source == DiscoverySource.SEED])
            },
            'interesting_findings_count': len(result.interesting_findings),
            'top_categories': list(result.categorized_results.keys())[:5] if result.categorized_results else [],
            'execution_time': result.execution_time,
            'recommendation': self._get_summary_recommendation(result)
        }
    
    def _get_summary_recommendation(self, result: MiniSpiderResult) -> str:
        """Generate recommendation based on results"""
        total_urls = len(result.discovered_urls)
        interesting_count = len(result.interesting_findings)
        
        if interesting_count > 10:
            return f"Found {interesting_count} interesting endpoints. Prioritize manual review of admin panels, API endpoints, and configuration files."
        elif total_urls > 100:
            return f"Discovered {total_urls} URLs. Focus on unique paths and potential entry points."
        elif total_urls > 20:
            return f"Moderate discovery of {total_urls} URLs. Good for targeted testing."
        else:
            return f"Limited discovery of {total_urls} URLs. Consider additional reconnaissance or different techniques."
    
    async def _save_results_to_workspace(self, target: str, result: MiniSpiderResult):
        """Save spider results to workspace files"""
        try:
            # Create workspace directory if it doesn't exist
            workspace_dir = Path("workspaces") / target.replace(':', '_').replace('/', '_')
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # Save all discovered URLs to a text file for easy consumption by other tools
            urls_file = workspace_dir / "discovered_urls.txt"
            with open(urls_file, 'w') as f:
                for url in result.discovered_urls:
                    f.write(f"{url.url}\n")
            
            # Save categorized results
            if result.categorized_results:
                for category, urls in result.categorized_results.items():
                    category_file = workspace_dir / f"urls_{category.lower().replace(' ', '_')}.txt"
                    with open(category_file, 'w') as f:
                        for url in urls:
                            f.write(f"{url.url}\n")
            
            # Save interesting findings
            if result.interesting_findings:
                interesting_file = workspace_dir / "interesting_findings.txt"
                with open(interesting_file, 'w') as f:
                    for finding in result.interesting_findings:
                        f.write(f"{finding.url} - {finding.reason}\n")
            
            # Save enhanced analysis results if available
            if hasattr(result, 'enhanced_analysis') and result.enhanced_analysis:
                enhanced_file = workspace_dir / "enhanced_analysis.json"
                with open(enhanced_file, 'w') as f:
                    import json
                    json.dump(result.enhanced_analysis, f, indent=2, default=str)
                
                # Save priority wordlists if available
                if 'wordlist_recommendations' in result.enhanced_analysis:
                    wordlist_recs = result.enhanced_analysis['wordlist_recommendations']
                    if 'priority_wordlists' in wordlist_recs:
                        wordlist_file = workspace_dir / "recommended_wordlists.txt"
                        with open(wordlist_file, 'w') as f:
                            f.write("# Priority Wordlist Recommendations\n")
                            f.write("# Generated by Enhanced Mini Spider Analysis\n\n")
                            
                            for rec in wordlist_recs['priority_wordlists']:
                                f.write(f"{rec['priority']}: {rec['wordlist']} (Score: {rec['score']:.1f})\n")
                                for reason in rec.get('reasons', []):
                                    f.write(f"  - {reason}\n")
                                f.write("\n")
                
                # Save critical intelligence summary
                if 'critical_intelligence' in result.enhanced_analysis:
                    critical_intel = result.enhanced_analysis['critical_intelligence']
                    critical_file = workspace_dir / "critical_intelligence.txt"
                    with open(critical_file, 'w') as f:
                        f.write("# Critical Intelligence Summary\n\n")
                        
                        for category, findings in critical_intel.items():
                            if findings:
                                f.write(f"## {category.replace('_', ' ').title()}\n")
                                for url, data in findings.items():
                                    f.write(f"- {url}\n")
                                    if isinstance(data, dict) and 'security_issues' in data:
                                        for issue in data['security_issues']:
                                            f.write(f"  ! {issue.get('type', 'unknown')}: {issue.get('match', '')}\n")
                                f.write("\n")
            
            debug_print(f"Results saved to workspace: {workspace_dir}")
            
        except Exception as e:
            debug_print(f"Failed to save results to workspace: {e}", level="ERROR")