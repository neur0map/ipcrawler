"""URL extraction from workflow_03 results"""
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from .models import CrawledURL, DiscoverySource, URLCategory
from .utils import URLFilter, URLNormalizer
from utils.debug import debug_print


class URLExtractor:
    """Extract and process URLs from workflow_03 (HTTP scanner) results"""
    
    def __init__(self):
        self.url_filter = URLFilter({
            'exclude_extensions': ['.jpg', '.png', '.gif', '.css', '.js', '.ico'],
            'exclude_patterns': [r'logout', r'signout', r'delete'],
            'include_patterns': [],
            'max_path_length': 1000,
            'max_query_params': 20
        })
    
    async def extract_from_http_results(self, http_results: Dict[str, Any]) -> List[CrawledURL]:
        """Extract URLs from HTTP_03 workflow results"""
        if not http_results or not http_results.get('success'):
            debug_print("HTTP_03 results not available or failed")
            return []
        
        data = http_results.get('data', {})
        if not data:
            debug_print("No data in HTTP_03 results")
            return []
        
        extracted_urls = []
        seen_urls = set()
        
        # Extract from services
        services = data.get('services', [])
        debug_print(f"Extracting URLs from {len(services)} HTTP services")
        
        for service in services:
            service_urls = self._extract_from_service(service)
            for url in service_urls:
                if url.url not in seen_urls:
                    extracted_urls.append(url)
                    seen_urls.add(url.url)
        
        # Extract from discovered paths in services
        for service in services:
            path_urls = self._extract_from_discovered_paths(service)
            for url in path_urls:
                if url.url not in seen_urls:
                    extracted_urls.append(url)
                    seen_urls.add(url.url)
        
        # Extract from DNS records if they contain URLs
        dns_records = data.get('dns_records', [])
        dns_urls = self._extract_from_dns_records(dns_records, data.get('target'))
        for url in dns_urls:
            if url.url not in seen_urls:
                extracted_urls.append(url)
                seen_urls.add(url.url)
        
        # Extract from subdomains
        subdomains = data.get('subdomains', [])
        subdomain_urls = self._extract_from_subdomains(subdomains)
        for url in subdomain_urls:
            if url.url not in seen_urls:
                extracted_urls.append(url)
                seen_urls.add(url.url)
        
        debug_print(f"Extracted {len(extracted_urls)} unique URLs from HTTP_03 results")
        return extracted_urls
    
    def _extract_from_service(self, service: Dict[str, Any]) -> List[CrawledURL]:
        """Extract URLs from a single HTTP service"""
        urls = []
        
        # Base service URL
        service_url = service.get('url')
        if service_url:
            url = CrawledURL(
                url=service_url,
                source=DiscoverySource.HTTP_03,
                status_code=service.get('status_code'),
                content_type=self._extract_content_type(service.get('headers', {})),
                discovered_at=datetime.now(),
                category=self._categorize_service_url(service_url)
            )
            urls.append(url)
        
        # Generate additional URLs based on service information
        additional_urls = self._generate_service_variants(service)
        urls.extend(additional_urls)
        
        return urls
    
    def _extract_from_discovered_paths(self, service: Dict[str, Any]) -> List[CrawledURL]:
        """Extract URLs from discovered paths in a service"""
        urls = []
        base_url = service.get('url', '')
        
        if not base_url:
            return urls
        
        discovered_paths = service.get('discovered_paths', [])
        
        for path in discovered_paths:
            # Create full URL from base URL and path
            if path.startswith('/'):
                full_url = urljoin(base_url, path)
            elif path.startswith('http'):
                full_url = path
            else:
                full_url = urljoin(base_url, '/' + path)
            
            # Validate and filter URL
            should_include, reason = self.url_filter.should_include_url(full_url)
            if should_include:
                url = CrawledURL(
                    url=full_url,
                    source=DiscoverySource.HTTP_03,
                    discovered_at=datetime.now(),
                    category=self._categorize_path_url(path)
                )
                urls.append(url)
        
        return urls
    
    def _extract_from_dns_records(self, dns_records: List[Dict[str, Any]], target: str) -> List[CrawledURL]:
        """Extract URLs from DNS records"""
        urls = []
        
        for record in dns_records:
            record_type = record.get('type', '')
            value = record.get('value', '')
            
            # Extract URLs from TXT records that might contain URLs
            if record_type == 'TXT' and value:
                found_urls = re.findall(r'https?://[^\s<>"\']+', value)
                for found_url in found_urls:
                    url = CrawledURL(
                        url=found_url,
                        source=DiscoverySource.HTTP_03,
                        discovered_at=datetime.now(),
                        category=URLCategory.OTHER
                    )
                    urls.append(url)
            
            # Generate URLs from A records and CNAME records
            elif record_type in ['A', 'CNAME'] and value and target:
                # Create basic HTTP/HTTPS URLs
                for scheme in ['http', 'https']:
                    for port in [None, 8080, 8443]:
                        if port:
                            if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                                continue
                            test_url = f"{scheme}://{value}:{port}/"
                        else:
                            test_url = f"{scheme}://{value}/"
                        
                        url = CrawledURL(
                            url=test_url,
                            source=DiscoverySource.HTTP_03,
                            discovered_at=datetime.now(),
                            category=URLCategory.ROOT
                        )
                        urls.append(url)
        
        return urls
    
    def _extract_from_subdomains(self, subdomains: List[str]) -> List[CrawledURL]:
        """Extract URLs from discovered subdomains"""
        urls = []
        
        for subdomain in subdomains:
            if subdomain:
                # Create basic HTTP/HTTPS URLs for subdomains
                for scheme in ['http', 'https']:
                    url = CrawledURL(
                        url=f"{scheme}://{subdomain}/",
                        source=DiscoverySource.HTTP_03,
                        discovered_at=datetime.now(),
                        category=URLCategory.ROOT
                    )
                    urls.append(url)
                
                # Add common ports for subdomains
                for port in [8080, 8443, 3000, 8000]:
                    scheme = 'https' if port in [8443, 443] else 'http'
                    url = CrawledURL(
                        url=f"{scheme}://{subdomain}:{port}/",
                        source=DiscoverySource.HTTP_03,
                        discovered_at=datetime.now(),
                        category=URLCategory.ROOT
                    )
                    urls.append(url)
        
        return urls
    
    def _generate_service_variants(self, service: Dict[str, Any]) -> List[CrawledURL]:
        """Generate URL variants based on service information"""
        urls = []
        base_url = service.get('url', '')
        
        if not base_url:
            return urls
        
        # Parse base URL
        parsed = urlparse(base_url)
        base_scheme = parsed.scheme
        base_host = parsed.netloc
        
        # Generate common path variants
        common_paths = [
            '/robots.txt',
            '/sitemap.xml',
            '/api/',
            '/admin/',
            '/login',
            '/dashboard',
            '/.well-known/security.txt',
            '/swagger-ui/',
            '/api-docs/'
        ]
        
        # Technology-specific paths
        technologies = service.get('technologies', [])
        for tech in technologies:
            tech_paths = self._get_technology_paths(tech.lower())
            common_paths.extend(tech_paths)
        
        # Server-specific paths
        server = service.get('server', '')
        if server:
            server_paths = self._get_server_paths(server.lower())
            common_paths.extend(server_paths)
        
        # Create URLs for each path
        for path in common_paths:
            full_url = urljoin(base_url, path)
            should_include, reason = self.url_filter.should_include_url(full_url)
            
            if should_include:
                url = CrawledURL(
                    url=full_url,
                    source=DiscoverySource.HTTP_03,
                    discovered_at=datetime.now(),
                    category=self._categorize_path_url(path)
                )
                urls.append(url)
        
        return urls
    
    def _get_technology_paths(self, technology: str) -> List[str]:
        """Get paths specific to detected technologies"""
        tech_paths = {
            'wordpress': [
                '/wp-admin/',
                '/wp-content/',
                '/wp-includes/',
                '/wp-login.php',
                '/wp-config.php'
            ],
            'drupal': [
                '/admin/',
                '/user/',
                '/node/',
                '/modules/',
                '/themes/'
            ],
            'joomla': [
                '/administrator/',
                '/components/',
                '/modules/',
                '/templates/'
            ],
            'apache': [
                '/server-status',
                '/server-info',
                '/manual/'
            ],
            'nginx': [
                '/nginx_status'
            ],
            'tomcat': [
                '/manager/',
                '/host-manager/',
                '/examples/'
            ],
            'jenkins': [
                '/manage',
                '/configure',
                '/script'
            ],
            'gitlab': [
                '/admin/',
                '/api/v4/',
                '/help'
            ],
            'django': [
                '/admin/',
                '/api/',
                '/static/'
            ],
            'rails': [
                '/rails/info/',
                '/assets/'
            ]
        }
        
        return tech_paths.get(technology, [])
    
    def _get_server_paths(self, server: str) -> List[str]:
        """Get paths specific to detected servers"""
        server_paths = []
        
        if 'apache' in server:
            server_paths.extend(['/server-status', '/server-info'])
        elif 'nginx' in server:
            server_paths.extend(['/nginx_status'])
        elif 'iis' in server:
            server_paths.extend(['/iisstart.htm', '/welcome.png'])
        elif 'tomcat' in server:
            server_paths.extend(['/manager/', '/examples/'])
        
        return server_paths
    
    def _extract_content_type(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract content type from headers"""
        for key, value in headers.items():
            if key.lower() == 'content-type':
                return value.split(';')[0].strip()
        return None
    
    def _categorize_service_url(self, url: str) -> URLCategory:
        """Categorize a service URL"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if not path or path == '/':
            return URLCategory.ROOT
        elif '/admin' in path:
            return URLCategory.ADMIN
        elif '/api' in path:
            return URLCategory.API
        elif '/login' in path or '/auth' in path:
            return URLCategory.AUTH
        else:
            return URLCategory.APPLICATION
    
    def _categorize_path_url(self, path: str) -> URLCategory:
        """Categorize a URL based on its path"""
        path_lower = path.lower()
        
        # Admin interfaces
        if any(pattern in path_lower for pattern in ['/admin', '/manage', '/console', '/dashboard']):
            return URLCategory.ADMIN
        
        # API endpoints
        elif any(pattern in path_lower for pattern in ['/api', '/rest', '/graphql', '/v1/', '/v2/']):
            return URLCategory.API
        
        # Configuration
        elif any(pattern in path_lower for pattern in ['config', '.env', '.conf', 'settings']):
            return URLCategory.CONFIG
        
        # Authentication
        elif any(pattern in path_lower for pattern in ['/login', '/auth', '/signin', '/oauth']):
            return URLCategory.AUTH
        
        # Documentation
        elif any(pattern in path_lower for pattern in ['/docs', '/help', '/manual', '/swagger']):
            return URLCategory.DOCS
        
        # Development/Debug
        elif any(pattern in path_lower for pattern in ['/debug', '/test', '/dev', '/staging']):
            return URLCategory.DEV
        
        # Static resources
        elif any(pattern in path_lower for pattern in ['/static', '/assets', '/css', '/js', '/images']):
            return URLCategory.STATIC
        
        # Applications
        elif any(ext in path_lower for ext in ['.php', '.asp', '.jsp', '.py']):
            return URLCategory.APPLICATION
        
        else:
            return URLCategory.OTHER
    
    def get_extraction_summary(self, urls: List[CrawledURL]) -> Dict[str, Any]:
        """Generate summary of URL extraction"""
        if not urls:
            return {
                'total_urls': 0,
                'by_category': {},
                'by_source': {},
                'domains': []
            }
        
        # Count by category
        by_category = {}
        for url in urls:
            category = url.category.value if url.category else 'unknown'
            by_category[category] = by_category.get(category, 0) + 1
        
        # Count by source
        by_source = {}
        for url in urls:
            source = url.source.value
            by_source[source] = by_source.get(source, 0) + 1
        
        # Extract unique domains
        domains = set()
        for url in urls:
            try:
                parsed = urlparse(url.url)
                if parsed.netloc:
                    domains.add(parsed.netloc)
            except Exception:
                pass
        
        return {
            'total_urls': len(urls),
            'by_category': by_category,
            'by_source': by_source,
            'domains': sorted(list(domains)),
            'unique_domains': len(domains)
        }