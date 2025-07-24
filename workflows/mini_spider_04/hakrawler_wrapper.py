"""Hakrawler tool wrapper for URL discovery"""
import asyncio
import subprocess
import tempfile
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from .models import CrawledURL, DiscoverySource, HakrawlerResult
from .config import get_spider_config, get_config_manager
from .utils import parse_tool_output, is_valid_url, URLFilter
from utils.debug import debug_print


class HakrawlerWrapper:
    """Wrapper for hakrawler tool with intelligent execution"""
    
    def __init__(self):
        self.config = get_spider_config()
        self.config_manager = get_config_manager()
        self.hakrawler_config = self.config.hakrawler
        self.url_filter = URLFilter({
            'exclude_extensions': self.config.exclude_extensions,
            'exclude_patterns': self.config.exclude_patterns,
            'include_patterns': self.config.include_patterns
        })
        self.discovered_urls: Set[str] = set()
        
    async def run_parallel_discovery(self, seed_urls: List[CrawledURL], timeout: int = 30) -> List[CrawledURL]:
        """Run hakrawler discovery in parallel on multiple seed URLs"""
        if not self.config_manager.tools_available.get('hakrawler', False):
            debug_print("Hakrawler not available, skipping", level="WARNING")
            return []
        
        if not seed_urls:
            debug_print("No seed URLs provided for hakrawler")
            return []
        
        debug_print(f"Starting hakrawler with {len(seed_urls)} seed URLs")
        
        # Group seed URLs by domain to optimize hakrawler execution
        domain_groups = self._group_urls_by_domain(seed_urls)
        
        # Run hakrawler for each domain group
        all_results = []
        semaphore = asyncio.Semaphore(3)  # Limit concurrent hakrawler processes
        
        async def run_domain_group(domain: str, urls: List[CrawledURL]) -> List[CrawledURL]:
            async with semaphore:
                return await self._run_hakrawler_for_domain(domain, urls, timeout)
        
        tasks = []
        for domain, urls in domain_groups.items():
            if len(urls) > 0:  # Only process domains with URLs
                tasks.append(run_domain_group(domain, urls))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    debug_print(f"Hakrawler domain processing error: {result}", level="ERROR")
        
        debug_print(f"Hakrawler discovered {len(all_results)} URLs")
        return all_results
    
    def _group_urls_by_domain(self, seed_urls: List[CrawledURL]) -> Dict[str, List[CrawledURL]]:
        """Group URLs by domain for efficient hakrawler execution"""
        from urllib.parse import urlparse
        
        domain_groups = {}
        
        for url in seed_urls:
            try:
                parsed = urlparse(url.url)
                domain = parsed.netloc
                
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(url)
                
            except Exception as e:
                debug_print(f"Error parsing URL {url.url}: {e}")
        
        return domain_groups
    
    async def _run_hakrawler_for_domain(self, domain: str, urls: List[CrawledURL], timeout: int) -> List[CrawledURL]:
        """Run hakrawler for a specific domain"""
        try:
            # Select best representative URL for this domain
            representative_url = self._select_representative_url(urls)
            
            if not representative_url:
                debug_print(f"No valid representative URL for domain {domain}")
                return []
            
            # Run hakrawler
            result = await self._execute_hakrawler(representative_url, timeout)
            
            if not result.success:
                debug_print(f"Hakrawler failed for domain {domain}: {result.error_message}")
                return []
            
            # Process hakrawler output
            discovered_urls = await self._process_hakrawler_output(result, domain)
            
            debug_print(f"Hakrawler found {len(discovered_urls)} URLs for domain {domain}")
            return discovered_urls
            
        except Exception as e:
            debug_print(f"Error running hakrawler for domain {domain}: {e}", level="ERROR")
            return []
    
    def _select_representative_url(self, urls: List[CrawledURL]) -> Optional[str]:
        """Select the best representative URL for hakrawler"""
        if not urls:
            return None
        
        # Prioritize URLs that are likely to have more content
        scored_urls = []
        
        for url in urls:
            score = 0
            url_lower = url.url.lower()
            
            # Prefer root URLs
            if url.url.endswith('/'):
                score += 10
            
            # Prefer HTTPS
            if url.url.startswith('https://'):
                score += 5
            
            # Prefer URLs that responded successfully
            if url.status_code and 200 <= url.status_code < 300:
                score += 20
            
            # Deprioritize very specific paths
            if url.url.count('/') > 3:
                score -= 5
            
            # Prioritize common web ports
            if ':80/' in url_lower or ':443/' in url_lower or '/' == url_lower[-1:]:
                score += 5
            
            scored_urls.append((score, url.url))
        
        # Return URL with highest score
        scored_urls.sort(reverse=True)
        return scored_urls[0][1] if scored_urls else None
    
    async def _execute_hakrawler(self, url: str, timeout: int) -> HakrawlerResult:
        """Execute hakrawler command"""
        start_time = time.time()
        
        try:
            # Build hakrawler command
            cmd = self.config_manager.get_hakrawler_command_args(self.config, url)
            
            debug_print(f"Running hakrawler: {' '.join(cmd)}")
            
            # Create process with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send URL to hakrawler via stdin and wait for completion
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=url.encode()),
                    timeout=timeout
                )
                execution_time = time.time() - start_time
                
                if process.returncode == 0:
                    # Parse output
                    urls_found = []
                    if stdout:
                        output_text = stdout.decode('utf-8', errors='ignore')
                        urls_found = parse_tool_output(output_text, 'hakrawler')
                    
                    return HakrawlerResult(
                        success=True,
                        urls_found=urls_found,
                        execution_time=execution_time,
                        command_used=cmd,
                        stdout=stdout.decode('utf-8', errors='ignore') if stdout else None,
                        stderr=stderr.decode('utf-8', errors='ignore') if stderr else None,
                        return_code=process.returncode
                    )
                else:
                    error_msg = stderr.decode('utf-8', errors='ignore') if stderr else f"Process returned {process.returncode}"
                    return HakrawlerResult(
                        success=False,
                        urls_found=[],
                        execution_time=execution_time,
                        command_used=cmd,
                        stderr=error_msg,
                        return_code=process.returncode,
                        error_message=error_msg
                    )
                    
            except asyncio.TimeoutError:
                # Kill process on timeout
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                
                return HakrawlerResult(
                    success=False,
                    urls_found=[],
                    execution_time=time.time() - start_time,
                    command_used=cmd,
                    error_message=f"Hakrawler timed out after {timeout} seconds"
                )
                
        except Exception as e:
            return HakrawlerResult(
                success=False,
                urls_found=[],
                execution_time=time.time() - start_time,
                command_used=[],
                error_message=f"Hakrawler execution error: {str(e)}"
            )
    
    async def _process_hakrawler_output(self, result: HakrawlerResult, domain: str) -> List[CrawledURL]:
        """Process hakrawler output and convert to CrawledURL objects"""
        processed_urls = []
        
        for url_string in result.urls_found:
            try:
                # Validate URL
                if not is_valid_url(url_string):
                    continue
                
                # Check if URL should be included
                should_include, reason = self.url_filter.should_include_url(url_string)
                if not should_include:
                    continue
                
                # Skip if already discovered
                if url_string in self.discovered_urls:
                    continue
                
                # Create CrawledURL object
                crawled_url = CrawledURL(
                    url=url_string,
                    source=DiscoverySource.HAKRAWLER,
                    discovered_at=datetime.now()
                )
                
                processed_urls.append(crawled_url)
                self.discovered_urls.add(url_string)
                
            except Exception as e:
                debug_print(f"Error processing hakrawler URL {url_string}: {e}")
        
        return processed_urls
    
    async def run_single_url_discovery(self, url: str, timeout: int = 30) -> HakrawlerResult:
        """Run hakrawler on a single URL"""
        if not self.config_manager.tools_available.get('hakrawler', False):
            return HakrawlerResult(
                success=False,
                urls_found=[],
                execution_time=0.0,
                command_used=[],
                error_message="Hakrawler not available"
            )
        
        return await self._execute_hakrawler(url, timeout)
    
    async def run_subdomain_discovery(self, target_domain: str, timeout: int = 60) -> List[str]:
        """Use hakrawler for subdomain discovery"""
        if not self.config_manager.tools_available.get('hakrawler', False):
            debug_print("Hakrawler not available for subdomain discovery")
            return []
        
        try:
            # Create a modified config for subdomain discovery
            cmd = ['hakrawler', '-subs', '-u', '-depth', '1', '-timeout', str(timeout)]
            
            debug_print(f"Running hakrawler for subdomain discovery: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send domain to hakrawler
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=f"https://{target_domain}".encode()),
                timeout=timeout
            )
            
            if process.returncode == 0 and stdout:
                output_text = stdout.decode('utf-8', errors='ignore')
                urls = parse_tool_output(output_text, 'hakrawler')
                
                # Extract unique subdomains
                subdomains = set()
                for url in urls:
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        if parsed.netloc and parsed.netloc != target_domain:
                            subdomains.add(parsed.netloc)
                    except:
                        pass
                
                return list(subdomains)
                
        except Exception as e:
            debug_print(f"Subdomain discovery error: {e}", level="ERROR")
        
        return []
    
    async def run_with_custom_wordlist(self, base_urls: List[str], wordlist_path: str, timeout: int = 60) -> List[CrawledURL]:
        """Run hakrawler with a custom wordlist approach"""
        if not self.config_manager.tools_available.get('hakrawler', False):
            debug_print("Hakrawler not available for custom wordlist")
            return []
        
        discovered_urls = []
        
        # Use hakrawler in a more focused way with wordlist concepts
        for base_url in base_urls[:5]:  # Limit to 5 base URLs
            try:
                # Create temporary input file with paths
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp_file:
                    tmp_file.write(base_url + '\n')
                    
                    # Add common paths based on wordlist
                    if Path(wordlist_path).exists():
                        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as wl:
                            paths = [line.strip() for line in wl.readlines()[:100]]  # Limit to 100 paths
                            for path in paths:
                                if path and not path.startswith('#'):
                                    full_url = base_url.rstrip('/') + '/' + path.lstrip('/')
                                    tmp_file.write(full_url + '\n')
                    
                    tmp_file_path = tmp_file.name
                
                # Run hakrawler with the temporary file
                cmd = ['hakrawler', '-timeout', str(timeout // len(base_urls))]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Read the temp file and send to hakrawler
                with open(tmp_file_path, 'r') as f:
                    input_data = f.read()
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_data.encode()),
                    timeout=timeout // len(base_urls)
                )
                
                # Clean up temp file
                Path(tmp_file_path).unlink(missing_ok=True)
                
                if process.returncode == 0 and stdout:
                    result = HakrawlerResult(
                        success=True,
                        urls_found=parse_tool_output(stdout.decode('utf-8', errors='ignore'), 'hakrawler'),
                        execution_time=0.0,
                        command_used=cmd
                    )
                    
                    processed = await self._process_hakrawler_output(result, base_url)
                    discovered_urls.extend(processed)
                
            except Exception as e:
                debug_print(f"Custom wordlist hakrawler error for {base_url}: {e}")
        
        return discovered_urls
    
    def validate_installation(self) -> bool:
        """Validate hakrawler installation"""
        return self.config_manager.validate_hakrawler_installation()
    
    def get_version(self) -> Optional[str]:
        """Get hakrawler version"""
        try:
            result = subprocess.run(
                ['hakrawler', '-h'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Try to extract version from help output
                output = result.stdout + result.stderr
                version_line = [line for line in output.split('\n') if 'version' in line.lower()]
                if version_line:
                    return version_line[0].strip()
                else:
                    return "unknown"
            
        except Exception as e:
            debug_print(f"Error getting hakrawler version: {e}")
        
        return None
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get hakrawler capabilities"""
        capabilities = {
            'installed': self.config_manager.tools_available.get('hakrawler', False),
            'subdomain_discovery': True,  # hakrawler supports -subs
            'wayback_integration': True,  # hakrawler supports -wayback
            'form_discovery': True,       # hakrawler supports -forms
            'url_extraction': True,       # basic capability
            'custom_user_agent': True,    # hakrawler supports -h flag
            'depth_control': True,        # hakrawler supports -depth
            'timeout_control': True       # hakrawler supports -timeout
        }
        
        return capabilities
    
    def get_recommended_config(self, target_type: str = 'web_app') -> Dict[str, Any]:
        """Get recommended hakrawler configuration for different target types"""
        configs = {
            'web_app': {
                'depth': 3,
                'timeout': 30,
                'include_subdomains': True,
                'include_wayback': False,
                'include_forms': True,
                'threads': 5
            },
            'subdomain_enum': {
                'depth': 1,
                'timeout': 60,
                'include_subdomains': True,
                'include_wayback': True,
                'include_forms': False,
                'threads': 10
            },
            'api_discovery': {
                'depth': 2,
                'timeout': 20,
                'include_subdomains': False,
                'include_wayback': False,
                'include_forms': True,
                'threads': 3
            },
            'quick_scan': {
                'depth': 1,
                'timeout': 10,
                'include_subdomains': False,
                'include_wayback': False,
                'include_forms': True,
                'threads': 8
            }
        }
        
        return configs.get(target_type, configs['web_app'])