"""Custom path sniffer implementation"""
import asyncio
import time
import subprocess
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from pathlib import Path

from .models import CrawledURL, DiscoverySource, CustomCrawlerResult, CrawlerStats
from .config import get_spider_config
from .utils import URLFilter, URLNormalizer, is_valid_url
from utils.debug import debug_print

# Try to import httpx for async HTTP requests
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    debug_print("httpx not available, will use curl fallback")


class CustomCrawler:
    """Custom path sniffer with intelligent discovery techniques"""
    
    def __init__(self):
        self.config = get_spider_config()
        self.crawler_config = self.config.custom_crawler
        self.url_filter = URLFilter({
            'exclude_extensions': self.config.exclude_extensions,
            'exclude_patterns': self.config.exclude_patterns,
            'include_patterns': self.config.include_patterns
        })
        self.stats = CrawlerStats()
        self.discovered_urls: Set[str] = set()
        
    async def discover_paths(self, seed_urls: List[CrawledURL], max_concurrent: int = 10) -> List[CrawledURL]:
        """Discover paths using custom sniffer techniques"""
        start_time = time.time()
        
        if not seed_urls:
            debug_print("No seed URLs provided for custom crawler")
            print("    ⚠ No seed URLs available for custom crawler")
            return []
        
        debug_print(f"Starting custom crawler with {len(seed_urls)} seed URLs")
        print(f"    → Testing {len(seed_urls)} seed URLs...")
        
        discovered = []
        
        try:
            # Check HTTP library availability
            if not HTTPX_AVAILABLE:
                print("    ⚠ httpx not available, using curl fallback (slower)")
            
            # Phase 1: Test seed URLs and extract base URLs
            active_base_urls = await self._validate_seed_urls(seed_urls)
            debug_print(f"Validated {len(active_base_urls)} active base URLs: {active_base_urls}")
            
            if len(active_base_urls) == 0:
                print("    ⚠ No seed URLs are responding - target may be down or filtered")
                return []
            else:
                print(f"    ✓ {len(active_base_urls)} URLs responding, starting discovery...")
            
            # Phase 2: Common path discovery
            print(f"    → Phase 2: Testing common paths...")
            common_paths = await self._discover_common_paths(active_base_urls, max_concurrent)
            discovered.extend(common_paths)
            print(f"    ✓ Common paths: {len(common_paths)} found")
            
            # Phase 3: Smart path generation based on responses
            print(f"    → Phase 3: Smart path generation...")
            smart_paths = await self._discover_smart_paths(active_base_urls, max_concurrent)
            discovered.extend(smart_paths)
            print(f"    ✓ Smart paths: {len(smart_paths)} found")
            
            # Phase 4: Directory traversal and path extension
            if discovered:
                print(f"    → Phase 4: Extending discovered paths...")
                extended_paths = await self._extend_discovered_paths(discovered[:20], max_concurrent)  # Limit to top 20
                discovered.extend(extended_paths)
                print(f"    ✓ Extended paths: {len(extended_paths)} found")
            
            # Phase 5: HTML link extraction from discovered pages
            if discovered:
                print(f"    → Phase 5: Extracting links from pages...")
                link_paths = await self._extract_links_from_pages(discovered[:10])  # Limit to top 10
                discovered.extend(link_paths)
                print(f"    ✓ Extracted links: {len(link_paths)} found")
            
            execution_time = time.time() - start_time
            self.stats.total_bytes_downloaded = getattr(self.stats, 'total_bytes_downloaded', 0)
            
            debug_print(f"Custom crawler completed: {len(discovered)} URLs discovered in {execution_time:.2f}s")
            
            return discovered
            
        except Exception as e:
            debug_print(f"Custom crawler error: {e}", level="ERROR")
            return discovered
    
    async def _validate_seed_urls(self, seed_urls: List[CrawledURL]) -> List[str]:
        """Validate seed URLs and extract active base URLs"""
        active_bases = []
        
        # Create semaphore for concurrent requests
        semaphore = asyncio.Semaphore(self.crawler_config.max_concurrent)
        
        async def validate_url(seed_url: CrawledURL) -> Optional[str]:
            async with semaphore:
                if HTTPX_AVAILABLE:
                    return await self._validate_url_httpx(seed_url.url)
                else:
                    return await self._validate_url_curl(seed_url.url)
        
        # Test all seed URLs concurrently
        tasks = [validate_url(seed_url) for seed_url in seed_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for seed_url, result in zip(seed_urls, results):
            debug_print(f"Validating {seed_url.url} -> {result}")
            if isinstance(result, str) and result:
                active_bases.append(result)
                self.stats.urls_tested += 1
                self.stats.successful_requests += 1
                debug_print(f"Successfully validated: {seed_url.url} -> {result}")
            elif isinstance(result, Exception):
                debug_print(f"Error validating {seed_url.url}: {result}")
                self.stats.urls_tested += 1
                self.stats.failed_requests += 1
            else:
                debug_print(f"Failed validation {seed_url.url}: {result} (None or False)")
                self.stats.urls_tested += 1
                self.stats.failed_requests += 1
        
        return list(set(active_bases))  # Remove duplicates
    
    async def _validate_url_httpx(self, url: str) -> Optional[str]:
        """Validate URL using httpx"""
        debug_print(f"Validating URL with httpx: {url}")
        try:
            timeout = httpx.Timeout(
                connect=5.0, 
                read=self.crawler_config.request_timeout, 
                write=5.0, 
                pool=5.0
            )
            
            async with httpx.AsyncClient(
                verify=self.crawler_config.verify_ssl,
                timeout=timeout,
                follow_redirects=self.crawler_config.follow_redirects,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            ) as client:
                
                headers = self.crawler_config.custom_headers.copy()
                headers['User-Agent'] = random.choice(self.crawler_config.user_agents)
                
                debug_print(f"Making HEAD request to {url}")
                try:
                    response = await client.head(url, headers=headers)
                except Exception as head_error:
                    debug_print(f"HEAD request failed, trying GET: {head_error}")
                    # Fallback to GET request if HEAD fails
                    response = await client.get(url, headers=headers)
                debug_print(f"Response status: {response.status_code} for {url}")
                
                if response.status_code < 400:
                    # Extract base URL
                    parsed = urlparse(url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    debug_print(f"URL validation successful: {url} -> {base_url}")
                    return base_url
                else:
                    debug_print(f"URL validation failed: {url} (status {response.status_code})")
                    
        except Exception as e:
            debug_print(f"httpx validation failed for {url}: {e}")
        
        return None
    
    async def _validate_url_curl(self, url: str) -> Optional[str]:
        """Validate URL using curl fallback"""
        try:
            cmd = [
                'curl', '-I', '-s', '-L', '--max-time', '10',
                '-H', f"User-Agent: {random.choice(self.crawler_config.user_agents)}",
                url
            ]
            
            if not self.crawler_config.verify_ssl:
                cmd.append('-k')
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                # Parse status code from curl output
                output = stdout.decode('utf-8', errors='ignore')
                if 'HTTP/' in output:
                    lines = output.strip().split('\n')
                    if lines:
                        status_line = lines[0]
                        if ' 200 ' in status_line or ' 301 ' in status_line or ' 302 ' in status_line:
                            parsed = urlparse(url)
                            return f"{parsed.scheme}://{parsed.netloc}"
            
        except Exception as e:
            debug_print(f"curl validation failed for {url}: {e}")
        
        return None
    
    async def _discover_common_paths(self, base_urls: List[str], max_concurrent: int) -> List[CrawledURL]:
        """Discover common paths across all base URLs"""
        common_paths = [
            # Information disclosure
            '/robots.txt', '/sitemap.xml', '/.well-known/security.txt',
            '/humans.txt', '/crossdomain.xml', '/clientaccesspolicy.xml',
            
            # Admin interfaces
            '/admin/', '/administrator/', '/admin.php', '/admin.html',
            '/dashboard/', '/console/', '/control/', '/manage/',
            '/cp/', '/backend/', '/panel/',
            
            # API endpoints
            '/api/', '/api/v1/', '/api/v2/', '/rest/', '/graphql',
            '/api/docs/', '/api-docs/', '/swagger/', '/swagger-ui/',
            '/openapi.json', '/swagger.json',
            
            # Authentication
            '/login', '/login.php', '/login.html', '/signin',
            '/auth/', '/oauth/', '/sso/',
            
            # Configuration files
            '/.env', '/config.php', '/configuration.php', '/settings.php',
            '/web.config', '/app.config', '/.htaccess',
            '/wp-config.php', '/config.yml', '/config.yaml',
            
            # Development/Debug
            '/debug/', '/test/', '/dev/', '/staging/',
            '/phpinfo.php', '/info.php', '/status/',
            '/.git/', '/.svn/', '/.hg/',
            
            # Backup files
            '/backup/', '/backups/', '/bak/', '/old/',
            '/backup.sql', '/database.sql', '/dump.sql',
            
            # Common applications
            '/wp-admin/', '/wp-login.php', '/wp-content/',
            '/phpmyadmin/', '/pma/', '/mysql/',
            '/mail/', '/webmail/', '/email/',
            
            # Monitoring/Stats
            '/stats/', '/statistics/', '/metrics/',
            '/health/', '/ping/', '/version/',
            '/monitor/', '/nagios/', '/zabbix/',
            
            # Upload/File management
            '/upload/', '/uploads/', '/files/', '/file/',
            '/media/', '/attachments/', '/documents/',
            
            # CMS/Framework specific
            '/user/', '/users/', '/account/', '/profile/',
            '/search/', '/install/', '/setup/',
            '/cgi-bin/', '/scripts/', '/bin/'
        ]
        
        discovered = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def test_path(base_url: str, path: str) -> Optional[CrawledURL]:
            async with semaphore:
                return await self._test_single_path(base_url, path)
        
        # Create tasks for all combinations
        tasks = []
        for base_url in base_urls:
            for path in common_paths:
                tasks.append(test_path(base_url, path))
        
        # Execute all tasks
        debug_print(f"Testing {len(tasks)} path combinations ({len(base_urls)} base URLs × {len(common_paths)} paths)")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_count = 0
        exception_count = 0
        for result in results:
            if isinstance(result, CrawledURL):
                discovered.append(result)
                successful_count += 1
            elif isinstance(result, Exception):
                exception_count += 1
                debug_print(f"Path test exception: {result}")
        
        debug_print(f"Common path discovery: {successful_count} successful, {exception_count} exceptions, {len(discovered)} URLs found")
        
        # Show sample of discovered URLs for debugging
        if discovered:
            sample_size = min(5, len(discovered))
            debug_print(f"Sample discovered URLs: {[url.url for url in discovered[:sample_size]]}")
        
        return discovered
    
    async def _discover_smart_paths(self, base_urls: List[str], max_concurrent: int) -> List[CrawledURL]:
        """Smart path discovery based on server responses and patterns"""
        discovered = []
        
        # First, probe each base URL to understand the server
        server_info = {}
        for base_url in base_urls:
            info = await self._probe_server_info(base_url)
            server_info[base_url] = info
        
        # Generate smart paths based on server information
        smart_paths = self._generate_smart_paths(server_info)
        
        # Test smart paths
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def test_smart_path(base_url: str, path: str) -> Optional[CrawledURL]:
            async with semaphore:
                return await self._test_single_path(base_url, path)
        
        tasks = []
        for base_url, paths in smart_paths.items():
            for path in paths[:50]:  # Limit to 50 paths per base URL
                tasks.append(test_smart_path(base_url, path))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, CrawledURL):
                discovered.append(result)
        
        debug_print(f"Smart path discovery found {len(discovered)} URLs")
        return discovered
    
    async def _probe_server_info(self, base_url: str) -> Dict[str, Any]:
        """Probe server to understand technology and configuration"""
        info = {
            'server': None,
            'technologies': [],
            'cms': None,
            'framework': None,
            'headers': {}
        }
        
        try:
            if HTTPX_AVAILABLE:
                timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
                async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
                    headers = {'User-Agent': random.choice(self.crawler_config.user_agents)}
                    response = await client.get(base_url, headers=headers)
                    
                    info['headers'] = dict(response.headers)
                    info['server'] = response.headers.get('server', '')
                    
                    # Detect technologies from headers
                    if 'x-powered-by' in response.headers:
                        info['technologies'].append(response.headers['x-powered-by'])
                    
                    # Detect CMS/Framework from response body
                    content = response.text[:5000]  # First 5KB
                    info['cms'] = self._detect_cms(content)
                    info['framework'] = self._detect_framework(content)
                    
        except Exception as e:
            debug_print(f"Server probing failed for {base_url}: {e}")
        
        return info
    
    def _detect_cms(self, content: str) -> Optional[str]:
        """Detect CMS from response content"""
        cms_patterns = {
            'wordpress': [r'wp-content', r'wp-includes', r'/wp-json/'],
            'drupal': [r'Drupal', r'/sites/default/', r'drupal.js'],
            'joomla': [r'Joomla', r'/media/jui/', r'joomla.js'],
            'magento': [r'Mage.', r'/skin/frontend/', r'Magento'],
            'prestashop': [r'PrestaShop', r'/themes/default/', r'prestashop'],
            'opencart': [r'OpenCart', r'catalog/view/', r'opencart']
        }
        
        content_lower = content.lower()
        for cms, patterns in cms_patterns.items():
            if any(pattern.lower() in content_lower for pattern in patterns):
                return cms
        
        return None
    
    def _detect_framework(self, content: str) -> Optional[str]:
        """Detect framework from response content"""
        framework_patterns = {
            'django': [r'csrfmiddlewaretoken', r'django', r'/static/admin/'],
            'flask': [r'Flask', r'werkzeug'],
            'rails': [r'Rails', r'authenticity_token', r'/assets/'],
            'laravel': [r'Laravel', r'csrf-token', r'laravel_session'],
            'symfony': [r'Symfony', r'_token', r'/bundles/'],
            'express': [r'Express', r'connect.sid'],
            'spring': [r'Spring', r'JSESSIONID', r'/spring/'],
            'struts': [r'Struts', r'struts', r'.action']
        }
        
        content_lower = content.lower()
        for framework, patterns in framework_patterns.items():
            if any(pattern.lower() in content_lower for pattern in patterns):
                return framework
        
        return None
    
    def _generate_smart_paths(self, server_info: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate smart paths based on server information"""
        smart_paths = {}
        
        for base_url, info in server_info.items():
            paths = []
            
            # Server-specific paths
            server = info.get('server', '').lower()
            if 'apache' in server:
                paths.extend(['/server-status', '/server-info', '/manual/'])
            elif 'nginx' in server:
                paths.extend(['/nginx_status', '/status'])
            elif 'iis' in server:
                paths.extend(['/iisstart.htm', '/welcome.png'])
            elif 'tomcat' in server:
                paths.extend(['/manager/', '/examples/', '/docs/'])
            
            # CMS-specific paths
            cms = info.get('cms')
            if cms == 'wordpress':
                paths.extend([
                    '/wp-admin/', '/wp-login.php', '/wp-content/',
                    '/wp-includes/', '/wp-json/', '/xmlrpc.php'
                ])
            elif cms == 'drupal':
                paths.extend([
                    '/user/', '/admin/', '/node/', '/modules/', '/themes/'
                ])
            elif cms == 'joomla':
                paths.extend([
                    '/administrator/', '/components/', '/modules/', '/templates/'
                ])
            
            # Framework-specific paths
            framework = info.get('framework')
            if framework == 'django':
                paths.extend(['/admin/', '/static/', '/media/'])
            elif framework == 'rails':
                paths.extend(['/rails/info/', '/assets/'])
            elif framework == 'laravel':
                paths.extend(['/public/', '/storage/', '/vendor/'])
            
            # Technology-specific paths
            for tech in info.get('technologies', []):
                if 'php' in tech.lower():
                    paths.extend(['/phpinfo.php', '/info.php'])
                elif 'node' in tech.lower():
                    paths.extend(['/node_modules/'])
            
            smart_paths[base_url] = list(set(paths))  # Remove duplicates
        
        return smart_paths
    
    async def _test_single_path(self, base_url: str, path: str) -> Optional[CrawledURL]:
        """Test a single path and return CrawledURL if successful"""
        full_url = urljoin(base_url, path)
        
        # Check if URL should be included
        should_include, reason = self.url_filter.should_include_url(full_url)
        if not should_include:
            debug_print(f"URL filtered out: {full_url} - reason: {reason}")
            return None
        
        # Check if already discovered
        if full_url in self.discovered_urls:
            debug_print(f"URL already discovered: {full_url}")
            return None
        
        try:
            start_time = time.time()
            debug_print(f"Testing path: {full_url}")
            
            if HTTPX_AVAILABLE:
                result = await self._test_path_httpx(full_url)
            else:
                result = await self._test_path_curl(full_url)
            
            if result:
                response_time = time.time() - start_time
                result.response_time = response_time
                result.tested_at = datetime.now()
                
                self.discovered_urls.add(full_url)
                self.stats.add_response(True, response_time, result.content_length)
                
                debug_print(f"Successfully discovered: {full_url} (status: {result.status_code})")
                return result
            else:
                self.stats.add_response(False)
                debug_print(f"Path test failed: {full_url}")
                
        except Exception as e:
            debug_print(f"Error testing path {full_url}: {e}")
            self.stats.add_response(False)
        
        return None
    
    async def _test_path_httpx(self, url: str) -> Optional[CrawledURL]:
        """Test path using httpx"""
        try:
            timeout = httpx.Timeout(
                connect=5.0, 
                read=self.crawler_config.request_timeout, 
                write=5.0, 
                pool=5.0
            )
            
            async with httpx.AsyncClient(
                verify=self.crawler_config.verify_ssl,
                timeout=timeout,
                follow_redirects=self.crawler_config.follow_redirects
            ) as client:
                
                headers = self.crawler_config.custom_headers.copy()
                headers['User-Agent'] = random.choice(self.crawler_config.user_agents)
                
                # Try HEAD first, fallback to GET if needed
                try:
                    response = await client.head(url, headers=headers)
                    debug_print(f"HEAD response for {url}: {response.status_code}")
                except Exception as head_error:
                    debug_print(f"HEAD failed for {url}, trying GET: {head_error}")
                    response = await client.get(url, headers=headers)
                    debug_print(f"GET response for {url}: {response.status_code}")
                
                # Consider successful if status is informative
                # Include more status codes that indicate the path exists or is interesting
                if response.status_code in [200, 201, 202, 204, 301, 302, 307, 308, 401, 403, 405, 500, 502, 503]:
                    content_length = None
                    content_type = None
                    
                    if 'content-length' in response.headers:
                        try:
                            content_length = int(response.headers['content-length'])
                        except ValueError:
                            pass
                    
                    if 'content-type' in response.headers:
                        content_type = response.headers['content-type'].split(';')[0].strip()
                    
                    # Handle redirects
                    redirect_url = None
                    if response.status_code in [301, 302, 307, 308] and 'location' in response.headers:
                        redirect_url = response.headers['location']
                    
                    debug_print(f"Accepted response: {url} -> {response.status_code}")
                    return CrawledURL(
                        url=url,
                        source=DiscoverySource.CUSTOM_CRAWLER,
                        status_code=response.status_code,
                        content_type=content_type,
                        content_length=content_length,
                        redirect_url=redirect_url,
                        discovered_at=datetime.now()
                    )
                else:
                    debug_print(f"Rejected response: {url} -> {response.status_code}")
                    
        except Exception as e:
            debug_print(f"httpx test failed for {url}: {e}")
        
        return None
    
    async def _test_path_curl(self, url: str) -> Optional[CrawledURL]:
        """Test path using curl"""
        try:
            cmd = [
                'curl', '-I', '-s', '-L', '--max-time', str(self.crawler_config.request_timeout),
                '-H', f"User-Agent: {random.choice(self.crawler_config.user_agents)}",
                url
            ]
            
            if not self.crawler_config.verify_ssl:
                cmd.append('-k')
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode('utf-8', errors='ignore')
                
                # Parse HTTP status
                status_code = None
                content_type = None
                content_length = None
                
                lines = output.strip().split('\n')
                for line in lines:
                    if line.startswith('HTTP/'):
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                status_code = int(parts[1])
                            except ValueError:
                                pass
                    elif line.lower().startswith('content-type:'):
                        content_type = line.split(':', 1)[1].strip().split(';')[0]
                    elif line.lower().startswith('content-length:'):
                        try:
                            content_length = int(line.split(':', 1)[1].strip())
                        except ValueError:
                            pass
                
                # Consider successful if status is informative
                if status_code and status_code in [200, 201, 202, 204, 301, 302, 307, 308, 401, 403, 405, 500, 502, 503]:
                    return CrawledURL(
                        url=url,
                        source=DiscoverySource.CUSTOM_CRAWLER,
                        status_code=status_code,
                        content_type=content_type,
                        content_length=content_length,
                        discovered_at=datetime.now()
                    )
                    
        except Exception as e:
            debug_print(f"curl test failed for {url}: {e}")
        
        return None
    
    async def _extend_discovered_paths(self, discovered: List[CrawledURL], max_concurrent: int) -> List[CrawledURL]:
        """Extend discovered paths by finding directory listings and path variations"""
        extended = []
        
        # Extract directories from discovered paths
        directories = set()
        for url in discovered:
            parsed = urlparse(url.url)
            path_parts = parsed.path.strip('/').split('/')
            
            # Generate directory paths
            for i in range(1, len(path_parts)):
                dir_path = '/' + '/'.join(path_parts[:i]) + '/'
                directories.add(urljoin(url.url, dir_path))
        
        # Test directory variations
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def test_directory(dir_url: str) -> List[CrawledURL]:
            async with semaphore:
                results = []
                
                # Test directory itself
                if dir_url not in self.discovered_urls:
                    result = await self._test_single_path(dir_url, '')
                    if result:
                        results.append(result)
                
                # Test common files in directory
                common_files = ['index.html', 'index.php', 'default.html', 'readme.txt', '.htaccess']
                for filename in common_files:
                    file_url = urljoin(dir_url, filename)
                    if file_url not in self.discovered_urls:
                        result = await self._test_single_path(file_url, '')
                        if result:
                            results.append(result)
                
                return results
        
        # Test all directories
        tasks = [test_directory(dir_url) for dir_url in list(directories)[:20]]  # Limit to 20 directories
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                extended.extend(result)
        
        debug_print(f"Path extension found {len(extended)} additional URLs")
        return extended
    
    async def _extract_links_from_pages(self, discovered: List[CrawledURL]) -> List[CrawledURL]:
        """Extract links from discovered pages"""
        links = []
        
        # Only process pages that returned 200 OK
        processable_urls = [url for url in discovered if url.status_code == 200]
        
        for url in processable_urls[:5]:  # Limit to 5 pages
            try:
                page_links = await self._extract_links_from_page(url.url)
                links.extend(page_links)
            except Exception as e:
                debug_print(f"Error extracting links from {url.url}: {e}")
        
        debug_print(f"Link extraction found {len(links)} URLs")
        return links
    
    async def _extract_links_from_page(self, url: str) -> List[CrawledURL]:
        """Extract links from a single page"""
        links = []
        
        try:
            if HTTPX_AVAILABLE:
                timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
                async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
                    headers = {'User-Agent': random.choice(self.crawler_config.user_agents)}
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        content = response.text[:50000]  # Limit to 50KB
                        extracted_links = self._parse_links_from_html(content, url)
                        
                        for link_url in extracted_links:
                            if is_valid_url(link_url) and link_url not in self.discovered_urls:
                                should_include, reason = self.url_filter.should_include_url(link_url)
                                if should_include:
                                    crawled_url = CrawledURL(
                                        url=link_url,
                                        source=DiscoverySource.HTML_PARSING,
                                        discovered_at=datetime.now()
                                    )
                                    links.append(crawled_url)
                                    self.discovered_urls.add(link_url)
        
        except Exception as e:
            debug_print(f"Error extracting links from {url}: {e}")
        
        return links
    
    def _parse_links_from_html(self, content: str, base_url: str) -> List[str]:
        """Parse links from HTML content"""
        import re
        
        links = []
        
        # Find href attributes
        href_pattern = r'href=["\']([^"\']+)["\']'
        for match in re.finditer(href_pattern, content, re.IGNORECASE):
            link = match.group(1)
            full_url = urljoin(base_url, link)
            links.append(full_url)
        
        # Find src attributes for scripts and other resources
        src_pattern = r'src=["\']([^"\']+)["\']'
        for match in re.finditer(src_pattern, content, re.IGNORECASE):
            link = match.group(1)
            if not link.startswith('data:'):  # Skip data URLs
                full_url = urljoin(base_url, link)
                links.append(full_url)
        
        # Find action attributes in forms
        action_pattern = r'action=["\']([^"\']+)["\']'
        for match in re.finditer(action_pattern, content, re.IGNORECASE):
            link = match.group(1)
            full_url = urljoin(base_url, link)
            links.append(full_url)
        
        return list(set(links))  # Remove duplicates
    
    def get_results(self) -> CustomCrawlerResult:
        """Get custom crawler results"""
        return CustomCrawlerResult(
            success=True,
            urls_found=list(self.discovered_urls),
            execution_time=0.0,  # Will be set by caller
            stats=self.stats
        )