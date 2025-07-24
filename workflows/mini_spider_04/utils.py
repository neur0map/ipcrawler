"""Utility functions for Mini Spider workflow"""
import re
import hashlib
from urllib.parse import urlparse, urljoin, parse_qs, urlunparse
from typing import List, Set, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from .models import CrawledURL


@dataclass
class URLNormalizer:
    """URL normalization and deduplication utilities"""
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for consistent comparison"""
        try:
            parsed = urlparse(url.strip())
            
            # Convert to lowercase domain
            netloc = parsed.netloc.lower()
            
            # Remove default ports
            if netloc.endswith(':80') and parsed.scheme == 'http':
                netloc = netloc[:-3]
            elif netloc.endswith(':443') and parsed.scheme == 'https':
                netloc = netloc[:-4]
            
            # Normalize path
            path = parsed.path or '/'
            if path != '/' and path.endswith('/'):
                path = path.rstrip('/')
            
            # Sort query parameters for consistent comparison
            query = ''
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=True)
                sorted_params = sorted(params.items())
                query_parts = []
                for key, values in sorted_params:
                    for value in sorted(values):
                        query_parts.append(f"{key}={value}")
                query = '&'.join(query_parts)
            
            # Reconstruct URL
            normalized = urlunparse((
                parsed.scheme.lower(),
                netloc,
                path,
                parsed.params,
                query,
                ''  # Remove fragment
            ))
            
            return normalized
            
        except Exception:
            return url
    
    @staticmethod
    def get_url_signature(url: str) -> str:
        """Generate unique signature for URL deduplication"""
        normalized = URLNormalizer.normalize_url(url)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    @staticmethod
    def are_urls_similar(url1: str, url2: str, similarity_threshold: float = 0.8) -> bool:
        """Check if two URLs are similar (for detecting parameter variations)"""
        try:
            parsed1 = urlparse(url1)
            parsed2 = urlparse(url2)
            
            # Must be same scheme, host, and path
            if (parsed1.scheme != parsed2.scheme or 
                parsed1.netloc.lower() != parsed2.netloc.lower() or 
                parsed1.path != parsed2.path):
                return False
            
            # Compare query parameters
            params1 = set(parse_qs(parsed1.query or '').keys())
            params2 = set(parse_qs(parsed2.query or '').keys())
            
            if not params1 and not params2:
                return True
            
            if not params1 or not params2:
                return False
            
            # Calculate parameter similarity
            intersection = len(params1.intersection(params2))
            union = len(params1.union(params2))
            
            similarity = intersection / union if union > 0 else 0
            return similarity >= similarity_threshold
            
        except Exception:
            return False


class URLFilter:
    """URL filtering utilities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.exclude_extensions = config.get('exclude_extensions', [])
        self.exclude_patterns = config.get('exclude_patterns', [])
        self.include_patterns = config.get('include_patterns', [])
        self.max_path_length = config.get('max_path_length', 1000)
        self.max_query_params = config.get('max_query_params', 50)
    
    def should_include_url(self, url: str) -> Tuple[bool, str]:
        """
        Check if URL should be included in results
        Returns (should_include, reason)
        """
        try:
            parsed = urlparse(url)
            
            # Basic validation
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL format"
            
            if parsed.scheme not in ['http', 'https']:
                return False, f"Unsupported scheme: {parsed.scheme}"
            
            # Path length check
            if len(parsed.path) > self.max_path_length:
                return False, f"Path too long: {len(parsed.path)} chars"
            
            # Query parameter count check
            if parsed.query:
                params = parse_qs(parsed.query)
                if len(params) > self.max_query_params:
                    return False, f"Too many query parameters: {len(params)}"
            
            # Extension filtering
            path_lower = parsed.path.lower()
            for ext in self.exclude_extensions:
                if path_lower.endswith(ext.lower()):
                    return False, f"Excluded extension: {ext}"
            
            # Pattern exclusion
            full_url_lower = url.lower()
            for pattern in self.exclude_patterns:
                if re.search(pattern, full_url_lower, re.IGNORECASE):
                    return False, f"Matches exclusion pattern: {pattern}"
            
            # Pattern inclusion (if specified, URL must match at least one)
            if self.include_patterns:
                matched_include = False
                for pattern in self.include_patterns:
                    if re.search(pattern, full_url_lower, re.IGNORECASE):
                        matched_include = True
                        break
                
                if not matched_include:
                    return False, "Does not match any inclusion pattern"
            
            return True, "Passed all filters"
            
        except Exception as e:
            return False, f"Filter error: {str(e)}"
    
    def categorize_url(self, url: str) -> str:
        """Categorize URL based on path patterns"""
        try:
            parsed = urlparse(url)
            path_lower = parsed.path.lower()
            
            # Admin/Management interfaces
            admin_patterns = [
                r'/admin', r'/administrator', r'/manage', r'/management',
                r'/console', r'/dashboard', r'/panel', r'/control'
            ]
            
            for pattern in admin_patterns:
                if re.search(pattern, path_lower):
                    return "admin"
            
            # API endpoints
            api_patterns = [
                r'/api', r'/rest', r'/graphql', r'/v\d+',
                r'\.json$', r'\.xml$', r'/services'
            ]
            
            for pattern in api_patterns:
                if re.search(pattern, path_lower):
                    return "api"
            
            # Configuration files
            config_patterns = [
                r'config', r'settings', r'\.conf$', r'\.ini$',
                r'\.env$', r'\.yaml$', r'\.yml$', r'\.properties$'
            ]
            
            for pattern in config_patterns:
                if re.search(pattern, path_lower):
                    return "config"
            
            # Authentication/Security
            auth_patterns = [
                r'/login', r'/signin', r'/auth', r'/oauth',
                r'/register', r'/signup', r'/password', r'/reset'
            ]
            
            for pattern in auth_patterns:
                if re.search(pattern, path_lower):
                    return "auth"
            
            # Documentation
            docs_patterns = [
                r'/docs', r'/documentation', r'/help', r'/wiki',
                r'/manual', r'/guide', r'/readme', r'/swagger'
            ]
            
            for pattern in docs_patterns:
                if re.search(pattern, path_lower):
                    return "docs"
            
            # Development/Debug
            dev_patterns = [
                r'/dev', r'/debug', r'/test', r'/staging',
                r'/phpinfo', r'/info\.php', r'/status'
            ]
            
            for pattern in dev_patterns:
                if re.search(pattern, path_lower):
                    return "dev"
            
            # Static files
            static_patterns = [
                r'/static', r'/assets', r'/css', r'/js',
                r'/images', r'/img', r'/fonts', r'/media'
            ]
            
            for pattern in static_patterns:
                if re.search(pattern, path_lower):
                    return "static"
            
            # Applications
            app_patterns = [
                r'\.php$', r'\.asp$', r'\.aspx$', r'\.jsp$',
                r'/app', r'/application', r'/portal'
            ]
            
            for pattern in app_patterns:
                if re.search(pattern, path_lower):
                    return "application"
            
            # Default category
            if parsed.path == '/' or not parsed.path:
                return "root"
            elif parsed.path.count('/') == 1:
                return "toplevel"
            else:
                return "other"
                
        except Exception:
            return "unknown"


class URLDeduplicator:
    """Advanced URL deduplication"""
    
    def __init__(self, enable_similarity_check: bool = True):
        self.enable_similarity_check = enable_similarity_check
        self.seen_signatures: Set[str] = set()
        self.url_clusters: Dict[str, List[str]] = {}
    
    def deduplicate_urls(self, urls: List[CrawledURL]) -> List[CrawledURL]:
        """Remove duplicate URLs from list"""
        unique_urls = []
        
        for url in urls:
            if self.is_unique_url(url.url):
                unique_urls.append(url)
        
        return unique_urls
    
    def is_unique_url(self, url: str) -> bool:
        """Check if URL is unique"""
        signature = URLNormalizer.get_url_signature(url)
        
        if signature in self.seen_signatures:
            return False
        
        # Check similarity if enabled
        if self.enable_similarity_check:
            normalized = URLNormalizer.normalize_url(url)
            base_url = self._get_base_url(normalized)
            
            if base_url in self.url_clusters:
                for existing_url in self.url_clusters[base_url]:
                    if URLNormalizer.are_urls_similar(normalized, existing_url):
                        return False
                
                self.url_clusters[base_url].append(normalized)
            else:
                self.url_clusters[base_url] = [normalized]
        
        self.seen_signatures.add(signature)
        return True
    
    def _get_base_url(self, url: str) -> str:
        """Get base URL for clustering"""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        except Exception:
            return url
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        return {
            'unique_signatures': len(self.seen_signatures),
            'url_clusters': len(self.url_clusters),
            'total_clustered_urls': sum(len(cluster) for cluster in self.url_clusters.values())
        }


def validate_input(target: str, **kwargs) -> Tuple[bool, List[str]]:
    """Validate input parameters for mini spider scanning"""
    errors = []
    
    # Validate target
    if not target:
        errors.append("Target is required")
    elif not isinstance(target, str):
        errors.append("Target must be a string")
    else:
        # Basic format validation
        if not re.match(r'^[a-zA-Z0-9.-]+$', target.strip()):
            errors.append("Invalid target format")
    
    # Validate optional parameters
    if 'ports' in kwargs:
        ports = kwargs['ports']
        if ports is not None:
            if not isinstance(ports, list):
                errors.append("Ports must be a list")
            else:
                for port in ports:
                    if not isinstance(port, int) or port < 1 or port > 65535:
                        errors.append(f"Invalid port: {port}")
    
    if 'max_urls' in kwargs:
        max_urls = kwargs['max_urls']
        if not isinstance(max_urls, int) or max_urls < 1:
            errors.append("max_urls must be a positive integer")
    
    if 'timeout' in kwargs:
        timeout = kwargs['timeout']
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            errors.append("timeout must be a positive number")
    
    return len(errors) == 0, errors


def deduplicate_urls(urls: List[CrawledURL], enable_similarity_check: bool = True) -> List[CrawledURL]:
    """Convenience function to deduplicate URLs"""
    deduplicator = URLDeduplicator(enable_similarity_check)
    return deduplicator.deduplicate_urls(urls)


def filter_urls(urls: List[str], config: Dict[str, Any]) -> List[Tuple[str, bool, str]]:
    """
    Filter URLs based on configuration
    Returns list of (url, should_include, reason) tuples
    """
    url_filter = URLFilter(config)
    results = []
    
    for url in urls:
        should_include, reason = url_filter.should_include_url(url)
        results.append((url, should_include, reason))
    
    return results


def categorize_urls(urls: List[str], config: Dict[str, Any]) -> Dict[str, List[str]]:
    """Categorize URLs into different types"""
    url_filter = URLFilter(config)
    categories = {}
    
    for url in urls:
        category = url_filter.categorize_url(url)
        if category not in categories:
            categories[category] = []
        categories[category].append(url)
    
    return categories


def extract_interesting_patterns(urls: List[CrawledURL]) -> List[Dict[str, Any]]:
    """Extract potentially interesting URLs based on patterns"""
    interesting = []
    
    # Patterns that indicate interesting endpoints
    interesting_patterns = [
        (r'/admin', 'admin_panel', 'high'),
        (r'/api', 'api_endpoint', 'medium'),
        (r'\.php$', 'php_script', 'medium'),
        (r'/config', 'config_file', 'high'),
        (r'/backup', 'backup_file', 'high'),
        (r'/\.git', 'git_repository', 'critical'),
        (r'/\.env', 'environment_file', 'critical'),
        (r'/swagger', 'api_docs', 'medium'),
        (r'/debug', 'debug_page', 'medium'),
        (r'/test', 'test_page', 'low'),
        (r'/upload', 'upload_endpoint', 'medium'),
        (r'/login', 'login_page', 'medium'),
        (r'/dashboard', 'dashboard', 'medium')
    ]
    
    for url in urls:
        for pattern, finding_type, severity in interesting_patterns:
            if re.search(pattern, url.url, re.IGNORECASE):
                interesting.append({
                    'url': url.url,
                    'type': finding_type,
                    'severity': severity,
                    'pattern': pattern,
                    'source': url.source.value if hasattr(url.source, 'value') else str(url.source),
                    'reason': f"Matches {finding_type} pattern: {pattern}"
                })
                break  # Only match first pattern per URL
    
    # Sort by severity (critical first)
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    interesting.sort(key=lambda x: severity_order.get(x['severity'], 4))
    
    return interesting


def build_url_list_for_tools(urls: List[CrawledURL], tool_format: str = 'plain') -> str:
    """Build URL list in format suitable for external tools"""
    if tool_format == 'plain':
        return '\n'.join(url.url for url in urls)
    elif tool_format == 'hakrawler':
        # Hakrawler expects one URL per line
        return '\n'.join(url.url for url in urls)
    elif tool_format == 'ffuf':
        # FFUF format with FUZZ placeholder
        return '\n'.join(url.url.replace('FUZZ', 'FUZZ') for url in urls)
    else:
        return '\n'.join(url.url for url in urls)


def parse_tool_output(output: str, tool_name: str) -> List[str]:
    """Parse output from external tools to extract URLs"""
    urls = []
    
    if tool_name == 'hakrawler':
        # Hakrawler outputs one URL per line
        for line in output.strip().split('\n'):
            line = line.strip()
            if line and (line.startswith('http://') or line.startswith('https://')):
                urls.append(line)
    
    elif tool_name == 'curl':
        # Extract URLs from curl output (if any)
        url_pattern = r'https?://[^\s<>"\']+[^\s<>"\'.,]'
        urls = re.findall(url_pattern, output)
    
    else:
        # Generic URL extraction
        url_pattern = r'https?://[^\s<>"\']+[^\s<>"\'.,]'
        urls = re.findall(url_pattern, output)
    
    return list(set(urls))  # Remove duplicates


def get_url_depth(url: str) -> int:
    """Get the depth of a URL (number of path segments)"""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            return 0
        return len(path.split('/'))
    except Exception:
        return 0


def is_valid_url(url: str) -> bool:
    """Basic URL validation"""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ['http', 'https'] and
            parsed.netloc and
            len(url) < 2000  # Reasonable URL length limit
        )
    except Exception:
        return False