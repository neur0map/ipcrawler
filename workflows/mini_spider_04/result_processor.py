"""Result processing and analysis for Mini Spider workflow"""
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from urllib.parse import urlparse, parse_qs

from .models import (
    CrawledURL, InterestingFinding, SeverityLevel, 
    URLCategory, DiscoverySource, SpiderStatistics
)
from .utils import URLFilter, categorize_urls, extract_interesting_patterns
from utils.debug import debug_print


class ResultProcessor:
    """Process and analyze spider crawling results"""
    
    def __init__(self):
        self.url_filter = URLFilter({
            'exclude_extensions': [],  # Don't filter at this stage
            'exclude_patterns': [],
            'include_patterns': []
        })
        
    async def process_results(self, discovered_urls: List[CrawledURL], target: str) -> Dict[str, Any]:
        """Process discovered URLs and generate comprehensive analysis"""
        debug_print(f"Processing {len(discovered_urls)} discovered URLs")
        
        # Basic categorization
        categorized_results = self._categorize_discovered_urls(discovered_urls)
        
        # Extract interesting findings
        interesting_findings = self._extract_interesting_findings(discovered_urls)
        
        # Generate statistics
        statistics = self._generate_statistics(discovered_urls, target)
        
        # Additional analysis
        analysis = self._perform_advanced_analysis(discovered_urls)
        
        return {
            'categories': categorized_results,
            'interesting': interesting_findings,
            'statistics': statistics.model_dump() if hasattr(statistics, 'model_dump') else statistics,
            'analysis': analysis
        }
    
    def _categorize_discovered_urls(self, urls: List[CrawledURL]) -> Dict[str, List[CrawledURL]]:
        """Categorize URLs into different types"""
        categories = defaultdict(list)
        
        for url in urls:
            # Use existing category if available
            if url.category:
                category = url.category.value if hasattr(url.category, 'value') else str(url.category)
            else:
                # Determine category based on URL patterns
                category = self._determine_url_category(url.url)
                url.category = URLCategory(category) if category in [c.value for c in URLCategory] else URLCategory.OTHER
            
            categories[category].append(url)
        
        return dict(categories)
    
    def _determine_url_category(self, url: str) -> str:
        """Determine URL category based on patterns"""
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
            
            # Root and top-level
            if parsed.path == '/' or not parsed.path:
                return "root"
            elif parsed.path.count('/') == 1:
                return "toplevel"
            else:
                return "other"
                
        except Exception:
            return "unknown"
    
    def _extract_interesting_findings(self, urls: List[CrawledURL]) -> List[InterestingFinding]:
        """Extract potentially interesting URLs and findings"""
        findings = []
        
        # Define interesting patterns with severity and descriptions
        interesting_patterns = [
            # Critical findings
            (r'/\.git', 'git_repository', SeverityLevel.CRITICAL, 'Git repository exposed'),
            (r'/\.svn', 'svn_repository', SeverityLevel.CRITICAL, 'SVN repository exposed'),
            (r'/\.env', 'environment_file', SeverityLevel.CRITICAL, 'Environment file exposed'),
            (r'/\.aws', 'aws_credentials', SeverityLevel.CRITICAL, 'AWS credentials exposed'),
            (r'/backup', 'backup_file', SeverityLevel.CRITICAL, 'Backup files exposed'),
            (r'/dump', 'database_dump', SeverityLevel.CRITICAL, 'Database dump exposed'),
            
            # High severity
            (r'/admin', 'admin_panel', SeverityLevel.HIGH, 'Admin panel discovered'),
            (r'/config', 'config_file', SeverityLevel.HIGH, 'Configuration file exposed'),
            (r'/phpinfo', 'php_info', SeverityLevel.HIGH, 'PHP info page exposed'),
            (r'/server-status', 'server_status', SeverityLevel.HIGH, 'Server status page exposed'),
            (r'/server-info', 'server_info', SeverityLevel.HIGH, 'Server info page exposed'),
            (r'/manager', 'tomcat_manager', SeverityLevel.HIGH, 'Tomcat manager exposed'),
            
            # Medium severity
            (r'/api', 'api_endpoint', SeverityLevel.MEDIUM, 'API endpoint discovered'),
            (r'/swagger', 'api_docs', SeverityLevel.MEDIUM, 'API documentation exposed'),
            (r'/login', 'login_page', SeverityLevel.MEDIUM, 'Login page discovered'),
            (r'/dashboard', 'dashboard', SeverityLevel.MEDIUM, 'Dashboard discovered'),
            (r'/upload', 'upload_endpoint', SeverityLevel.MEDIUM, 'File upload endpoint'),
            (r'/debug', 'debug_page', SeverityLevel.MEDIUM, 'Debug page exposed'),
            
            # Low severity
            (r'/robots\.txt', 'robots_file', SeverityLevel.LOW, 'Robots.txt file'),
            (r'/sitemap', 'sitemap', SeverityLevel.LOW, 'Sitemap discovered'),
            (r'/test', 'test_page', SeverityLevel.LOW, 'Test page discovered'),
            (r'/docs', 'documentation', SeverityLevel.LOW, 'Documentation discovered'),
            (r'/help', 'help_page', SeverityLevel.LOW, 'Help page discovered')
        ]
        
        for url in urls:
            url_path = urlparse(url.url).path.lower()
            
            for pattern, finding_type, severity, description in interesting_patterns:
                if re.search(pattern, url_path, re.IGNORECASE):
                    finding = InterestingFinding(
                        url=url.url,
                        finding_type=finding_type,
                        severity=severity,
                        reason=description,
                        pattern=pattern,
                        source=url.source,
                        confidence=self._calculate_confidence(url, pattern),
                        metadata=self._extract_finding_metadata(url)
                    )
                    findings.append(finding)
                    break  # Only match first pattern per URL
        
        # Additional context-based findings
        findings.extend(self._extract_context_findings(urls))
        
        # Sort by severity (critical first)
        severity_order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 4
        }
        
        findings.sort(key=lambda x: severity_order.get(x.severity, 5))
        
        debug_print(f"Extracted {len(findings)} interesting findings")
        return findings
    
    def _calculate_confidence(self, url: CrawledURL, pattern: str) -> float:
        """Calculate confidence score for a finding"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if URL responded successfully
        if url.status_code and 200 <= url.status_code < 300:
            confidence += 0.3
        elif url.status_code and url.status_code in [401, 403]:
            confidence += 0.2  # Protected resources are interesting
        
        # Higher confidence for exact matches
        if pattern in [r'/\.git', r'/\.env', r'/admin', r'/config']:
            confidence += 0.2
        
        # Higher confidence if discovered by multiple sources
        if url.source in [DiscoverySource.HTTP_03, DiscoverySource.CUSTOM_CRAWLER]:
            confidence += 0.1
        
        # Lower confidence for very common paths
        common_paths = [r'/test', r'/help', r'/docs']
        if any(cp in pattern for cp in common_paths):
            confidence -= 0.1
        
        return min(1.0, max(0.1, confidence))  # Clamp between 0.1 and 1.0
    
    def _extract_finding_metadata(self, url: CrawledURL) -> Dict[str, Any]:
        """Extract additional metadata for findings"""
        metadata = {
            'status_code': url.status_code,
            'content_type': url.content_type,
            'content_length': url.content_length,
            'response_time': url.response_time,
            'discovered_at': url.discovered_at.isoformat() if url.discovered_at else None
        }
        
        # Add URL analysis
        parsed = urlparse(url.url)
        metadata.update({
            'domain': parsed.netloc,
            'path_depth': len([p for p in parsed.path.split('/') if p]),
            'has_query': bool(parsed.query),
            'has_fragment': bool(parsed.fragment)
        })
        
        return metadata
    
    def _extract_context_findings(self, urls: List[CrawledURL]) -> List[InterestingFinding]:
        """Extract findings based on URL context and patterns"""
        context_findings = []
        
        # Group URLs by domain for context analysis
        domain_groups = defaultdict(list)
        for url in urls:
            try:
                domain = urlparse(url.url).netloc
                domain_groups[domain].append(url)
            except:
                pass
        
        for domain, domain_urls in domain_groups.items():
            # Look for suspicious parameter patterns
            param_findings = self._analyze_parameters(domain_urls, domain)
            context_findings.extend(param_findings)
            
            # Look for directory traversal patterns
            traversal_findings = self._analyze_directory_patterns(domain_urls, domain)
            context_findings.extend(traversal_findings)
            
            # Look for technology-specific patterns
            tech_findings = self._analyze_technology_patterns(domain_urls, domain)
            context_findings.extend(tech_findings)
        
        return context_findings
    
    def _analyze_parameters(self, urls: List[CrawledURL], domain: str) -> List[InterestingFinding]:
        """Analyze URL parameters for interesting patterns"""
        findings = []
        
        suspicious_params = [
            ('id', 'sql_injection_vector', SeverityLevel.MEDIUM),
            ('file', 'file_inclusion_vector', SeverityLevel.HIGH),
            ('path', 'path_traversal_vector', SeverityLevel.MEDIUM),
            ('url', 'open_redirect_vector', SeverityLevel.MEDIUM),
            ('redirect', 'open_redirect_vector', SeverityLevel.MEDIUM),
            ('callback', 'jsonp_callback', SeverityLevel.LOW),
            ('debug', 'debug_parameter', SeverityLevel.MEDIUM),
            ('admin', 'admin_parameter', SeverityLevel.HIGH)
        ]
        
        for url in urls:
            try:
                parsed = urlparse(url.url)
                if parsed.query:
                    params = parse_qs(parsed.query)
                    
                    for param_name in params.keys():
                        param_lower = param_name.lower()
                        
                        for suspicious_param, finding_type, severity in suspicious_params:
                            if suspicious_param in param_lower:
                                finding = InterestingFinding(
                                    url=url.url,
                                    finding_type=finding_type,
                                    severity=severity,
                                    reason=f"Suspicious parameter '{param_name}' found",
                                    pattern=f"parameter:{suspicious_param}",
                                    source=url.source,
                                    confidence=0.6,
                                    metadata={'parameter': param_name, 'domain': domain}
                                )
                                findings.append(finding)
                                break
                                
            except Exception:
                pass
        
        return findings
    
    def _analyze_directory_patterns(self, urls: List[CrawledURL], domain: str) -> List[InterestingFinding]:
        """Analyze directory structure patterns"""
        findings = []
        
        # Extract all directory paths
        directories = set()
        for url in urls:
            try:
                parsed = urlparse(url.url)
                path_parts = [p for p in parsed.path.split('/') if p]
                
                for i in range(len(path_parts)):
                    dir_path = '/' + '/'.join(path_parts[:i+1])
                    directories.add(dir_path)
                    
            except Exception:
                pass
        
        # Look for patterns
        patterns_to_check = [
            ('backup', 'backup_directory', SeverityLevel.HIGH),
            ('old', 'old_files_directory', SeverityLevel.MEDIUM),
            ('tmp', 'temp_directory', SeverityLevel.MEDIUM),
            ('temp', 'temp_directory', SeverityLevel.MEDIUM),
            ('cache', 'cache_directory', SeverityLevel.LOW),
            ('logs', 'log_directory', SeverityLevel.MEDIUM),
            ('uploads', 'upload_directory', SeverityLevel.MEDIUM)
        ]
        
        for directory in directories:
            for pattern, finding_type, severity in patterns_to_check:
                if pattern in directory.lower():
                    # Find a representative URL for this directory
                    representative_url = None
                    for url in urls:
                        if directory in url.url:
                            representative_url = url.url
                            break
                    
                    if representative_url:
                        finding = InterestingFinding(
                            url=representative_url,
                            finding_type=finding_type,
                            severity=severity,
                            reason=f"Potentially sensitive directory: {directory}",
                            pattern=f"directory:{pattern}",
                            source=DiscoverySource.CUSTOM_CRAWLER,
                            confidence=0.7,
                            metadata={'directory': directory, 'domain': domain}
                        )
                        findings.append(finding)
        
        return findings
    
    def _analyze_technology_patterns(self, urls: List[CrawledURL], domain: str) -> List[InterestingFinding]:
        """Analyze technology-specific patterns"""
        findings = []
        
        # Technology-specific patterns
        tech_patterns = [
            (r'\.php$', 'php_application', SeverityLevel.INFO, 'PHP application detected'),
            (r'\.asp$', 'asp_application', SeverityLevel.INFO, 'ASP application detected'),
            (r'\.jsp$', 'java_application', SeverityLevel.INFO, 'Java application detected'),
            (r'/wp-', 'wordpress_site', SeverityLevel.INFO, 'WordPress site detected'),
            (r'/drupal', 'drupal_site', SeverityLevel.INFO, 'Drupal site detected'),
            (r'/joomla', 'joomla_site', SeverityLevel.INFO, 'Joomla site detected'),
            (r'/phpmyadmin', 'phpmyadmin_access', SeverityLevel.HIGH, 'phpMyAdmin access detected'),
            (r'/adminer', 'adminer_access', SeverityLevel.HIGH, 'Adminer access detected')
        ]
        
        # Track technologies found
        technologies_found = set()
        
        for url in urls:
            url_path = urlparse(url.url).path.lower()
            
            for pattern, tech_type, severity, description in tech_patterns:
                if re.search(pattern, url_path) and tech_type not in technologies_found:
                    technologies_found.add(tech_type)
                    
                    finding = InterestingFinding(
                        url=url.url,
                        finding_type=tech_type,
                        severity=severity,
                        reason=description,
                        pattern=pattern,
                        source=url.source,
                        confidence=0.8,
                        metadata={'technology': tech_type, 'domain': domain}
                    )
                    findings.append(finding)
        
        return findings
    
    def _generate_statistics(self, urls: List[CrawledURL], target: str) -> SpiderStatistics:
        """Generate comprehensive statistics"""
        stats = SpiderStatistics()
        
        # Basic counts
        stats.total_discovered_urls = len(urls)
        stats.unique_urls_after_dedup = len(set(url.url for url in urls))
        
        # Count by source
        source_counts = Counter()
        for url in urls:
            source = url.source.value if hasattr(url.source, 'value') else str(url.source)
            source_counts[source] += 1
        stats.urls_by_source = dict(source_counts)
        
        # Count by category
        category_counts = Counter()
        for url in urls:
            if url.category:
                category = url.category.value if hasattr(url.category, 'value') else str(url.category)
                category_counts[category] += 1
        stats.urls_by_category = dict(category_counts)
        
        # Count by status code
        status_counts = Counter()
        for url in urls:
            if url.status_code:
                status_counts[url.status_code] += 1
        stats.urls_by_status_code = dict(status_counts)
        
        # Count interesting findings
        interesting_count = len(self._extract_interesting_findings(urls))
        stats.interesting_findings_count = interesting_count
        
        return stats
    
    def _perform_advanced_analysis(self, urls: List[CrawledURL]) -> Dict[str, Any]:
        """Perform advanced analysis on discovered URLs"""
        analysis = {}
        
        # Domain distribution
        domains = [urlparse(url.url).netloc for url in urls]
        domain_counts = Counter(domains)
        analysis['domain_distribution'] = dict(domain_counts.most_common(10))
        
        # Response code analysis
        response_codes = [url.status_code for url in urls if url.status_code]
        if response_codes:
            analysis['response_code_analysis'] = {
                'successful_responses': len([c for c in response_codes if 200 <= c < 300]),
                'redirect_responses': len([c for c in response_codes if 300 <= c < 400]),
                'client_error_responses': len([c for c in response_codes if 400 <= c < 500]),
                'server_error_responses': len([c for c in response_codes if 500 <= c < 600])
            }
        
        # Depth analysis
        depths = []
        for url in urls:
            try:
                path = urlparse(url.url).path
                depth = len([p for p in path.split('/') if p])
                depths.append(depth)
            except:
                pass
        
        if depths:
            analysis['depth_analysis'] = {
                'max_depth': max(depths),
                'average_depth': sum(depths) / len(depths),
                'depth_distribution': dict(Counter(depths))
            }
        
        # Content type analysis
        content_types = [url.content_type for url in urls if url.content_type]
        if content_types:
            content_type_counts = Counter(content_types)
            analysis['content_type_distribution'] = dict(content_type_counts.most_common(10))
        
        # Time-based analysis
        discovery_times = [url.discovered_at for url in urls if url.discovered_at]
        if discovery_times:
            earliest = min(discovery_times)
            latest = max(discovery_times)
            analysis['discovery_timeline'] = {
                'earliest_discovery': earliest.isoformat(),
                'latest_discovery': latest.isoformat(),
                'discovery_span_seconds': (latest - earliest).total_seconds()
            }
        
        # File extension analysis
        extensions = []
        for url in urls:
            try:
                path = urlparse(url.url).path
                if '.' in path:
                    ext = path.split('.')[-1].lower()
                    if len(ext) <= 5 and ext.isalnum():  # Valid extension
                        extensions.append(ext)
            except:
                pass
        
        if extensions:
            ext_counts = Counter(extensions)
            analysis['file_extension_distribution'] = dict(ext_counts.most_common(15))
        
        return analysis