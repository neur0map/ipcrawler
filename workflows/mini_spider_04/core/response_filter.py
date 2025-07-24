"""Response filtering and validation utilities"""
import re
import mimetypes
from typing import List, Dict, Any, Optional, Tuple, Set
from urllib.parse import urlparse
from datetime import datetime

from ..models import CrawledURL, SeverityLevel


class ResponseFilter:
    """Filter and validate HTTP responses for relevance and interest"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._init_default_filters()
        
    def _init_default_filters(self):
        """Initialize default filtering rules"""
        self.default_config = {
            # Status code filtering
            'valid_status_codes': [200, 201, 202, 204, 301, 302, 307, 308, 401, 403, 405],
            'exclude_status_codes': [404, 400, 500, 502, 503, 504],
            
            # Content type filtering
            'valid_content_types': [
                'text/html', 'text/plain', 'application/json', 'application/xml',
                'application/javascript', 'text/javascript', 'text/css',
                'application/pdf', 'application/octet-stream'
            ],
            'exclude_content_types': [
                'image/', 'audio/', 'video/', 'font/',
                'application/zip', 'application/rar'
            ],
            
            # Content length filtering
            'min_content_length': 0,
            'max_content_length': 10485760,  # 10MB
            
            # Response time filtering
            'max_response_time': 30.0,  # 30 seconds
            
            # Content analysis
            'min_content_ratio': 0.1,  # Minimum meaningful content ratio
            'error_page_indicators': [
                'not found', '404', 'page not found',
                'forbidden', '403', 'access denied',
                'internal server error', '500',
                'bad request', '400',
                'service unavailable', '503'
            ],
            
            # Default/template page indicators
            'default_page_indicators': [
                'default apache', 'apache http server test page',
                'nginx welcome', 'welcome to nginx',
                'it works!', 'test page for the apache',
                'default web site page', 'iis windows server',
                'tomcat default page', 'apache tomcat'
            ]
        }
    
    def filter_responses(self, urls: List[CrawledURL]) -> Tuple[List[CrawledURL], Dict[str, Any]]:
        """
        Filter URLs based on response characteristics
        Returns (filtered_urls, filter_stats)
        """
        if not urls:
            return [], {'total_input': 0, 'total_output': 0, 'filtered_out': 0}
        
        original_count = len(urls)
        filtered_urls = []
        filter_stats = {
            'total_input': original_count,
            'filtered_by_status': 0,
            'filtered_by_content_type': 0,
            'filtered_by_content_length': 0,
            'filtered_by_response_time': 0,
            'filtered_by_content_analysis': 0,
            'filtered_by_error_pages': 0,
            'filtered_by_default_pages': 0,
            'passed_all_filters': 0
        }
        
        for url in urls:
            should_include, reason = self._should_include_response(url)
            
            if should_include:
                filtered_urls.append(url)
                filter_stats['passed_all_filters'] += 1
            else:
                # Track filter reason
                if 'status' in reason:
                    filter_stats['filtered_by_status'] += 1
                elif 'content_type' in reason:
                    filter_stats['filtered_by_content_type'] += 1
                elif 'content_length' in reason:
                    filter_stats['filtered_by_content_length'] += 1
                elif 'response_time' in reason:
                    filter_stats['filtered_by_response_time'] += 1
                elif 'error_page' in reason:
                    filter_stats['filtered_by_error_pages'] += 1
                elif 'default_page' in reason:
                    filter_stats['filtered_by_default_pages'] += 1
                else:
                    filter_stats['filtered_by_content_analysis'] += 1
        
        filter_stats['total_output'] = len(filtered_urls)
        filter_stats['filtered_out'] = original_count - len(filtered_urls)
        filter_stats['filter_rate'] = filter_stats['filtered_out'] / original_count if original_count > 0 else 0
        
        return filtered_urls, filter_stats
    
    def _should_include_response(self, url: CrawledURL) -> Tuple[bool, str]:
        """Determine if response should be included based on various criteria"""
        # If no response data available, include by default
        if not url.status_code:
            return True, "no_response_data"
        
        # Status code filtering
        if not self._is_valid_status_code(url.status_code):
            return False, f"invalid_status_code_{url.status_code}"
        
        # Content type filtering
        if url.content_type and not self._is_valid_content_type(url.content_type):
            return False, f"invalid_content_type_{url.content_type}"
        
        # Content length filtering
        if url.content_length is not None and not self._is_valid_content_length(url.content_length):
            return False, f"invalid_content_length_{url.content_length}"
        
        # Response time filtering
        if url.response_time is not None and not self._is_valid_response_time(url.response_time):
            return False, f"slow_response_time_{url.response_time}"
        
        # Additional content analysis would require response body
        # For now, we'll rely on the above basic filters
        
        return True, "passed_all_filters"
    
    def _is_valid_status_code(self, status_code: int) -> bool:
        """Check if status code indicates a meaningful response"""
        valid_codes = self.config.get('valid_status_codes', self.default_config['valid_status_codes'])
        exclude_codes = self.config.get('exclude_status_codes', self.default_config['exclude_status_codes'])
        
        if exclude_codes and status_code in exclude_codes:
            return False
        
        if valid_codes:
            return status_code in valid_codes
        
        # Default: accept most informative status codes
        return status_code not in [404, 400, 500, 502, 503, 504]
    
    def _is_valid_content_type(self, content_type: str) -> bool:
        """Check if content type is relevant for analysis"""
        content_type = content_type.lower().strip()
        
        # Check exclusions first
        exclude_types = self.config.get('exclude_content_types', self.default_config['exclude_content_types'])
        for exclude_type in exclude_types:
            if content_type.startswith(exclude_type.lower()):
                return False
        
        # Check valid types
        valid_types = self.config.get('valid_content_types', self.default_config['valid_content_types'])
        if valid_types:
            for valid_type in valid_types:
                if content_type.startswith(valid_type.lower()):
                    return True
            return False
        
        # Default: exclude binary content types
        binary_types = ['image/', 'audio/', 'video/', 'application/zip', 'application/rar']
        for binary_type in binary_types:
            if content_type.startswith(binary_type):
                return False
        
        return True
    
    def _is_valid_content_length(self, content_length: int) -> bool:
        """Check if content length is within reasonable bounds"""
        min_length = self.config.get('min_content_length', self.default_config['min_content_length'])
        max_length = self.config.get('max_content_length', self.default_config['max_content_length'])
        
        return min_length <= content_length <= max_length
    
    def _is_valid_response_time(self, response_time: float) -> bool:
        """Check if response time is reasonable"""
        max_time = self.config.get('max_response_time', self.default_config['max_response_time'])
        return response_time <= max_time
    
    def analyze_response_content(self, url: CrawledURL, content: str) -> Dict[str, Any]:
        """Analyze response content for meaningful information"""
        if not content:
            return {'meaningful': False, 'reason': 'empty_content'}
        
        analysis = {
            'meaningful': True,
            'content_length': len(content),
            'content_type_detected': self._detect_content_type(content),
            'is_error_page': self._is_error_page(content),
            'is_default_page': self._is_default_page(content),
            'has_meaningful_content': self._has_meaningful_content(content),
            'content_indicators': self._analyze_content_indicators(content)
        }
        
        # Determine if content is meaningful
        if analysis['is_error_page'] or analysis['is_default_page']:
            analysis['meaningful'] = False
            analysis['reason'] = 'error_or_default_page'
        elif not analysis['has_meaningful_content']:
            analysis['meaningful'] = False
            analysis['reason'] = 'minimal_content'
        
        return analysis
    
    def _detect_content_type(self, content: str) -> str:
        """Detect content type from content"""
        content_lower = content.lower().strip()
        
        if content_lower.startswith('<!doctype html') or content_lower.startswith('<html'):
            return 'text/html'
        elif content_lower.startswith('{') and content_lower.endswith('}'):
            return 'application/json'
        elif content_lower.startswith('<?xml'):
            return 'application/xml'
        elif content_lower.startswith('<'):
            return 'text/xml'
        else:
            return 'text/plain'
    
    def _is_error_page(self, content: str) -> bool:
        """Check if content appears to be an error page"""
        content_lower = content.lower()
        error_indicators = self.config.get('error_page_indicators', self.default_config['error_page_indicators'])
        
        for indicator in error_indicators:
            if indicator.lower() in content_lower:
                return True
        
        return False
    
    def _is_default_page(self, content: str) -> bool:
        """Check if content appears to be a default/template page"""
        content_lower = content.lower()
        default_indicators = self.config.get('default_page_indicators', self.default_config['default_page_indicators'])
        
        for indicator in default_indicators:
            if indicator.lower() in content_lower:
                return True
        
        return False
    
    def _has_meaningful_content(self, content: str) -> bool:
        """Check if content has meaningful information"""
        # Remove HTML tags for text analysis
        text_content = re.sub(r'<[^>]+>', '', content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Check content length
        if len(text_content) < 50:  # Too short
            return False
        
        # Check content ratio (meaningful text vs total)
        min_ratio = self.config.get('min_content_ratio', self.default_config['min_content_ratio'])
        content_ratio = len(text_content) / len(content) if content else 0
        
        if content_ratio < min_ratio:
            return False
        
        # Check for meaningful patterns
        meaningful_patterns = [
            r'<title>[^<]{5,}</title>',  # Non-empty title
            r'<h[1-6][^>]*>[^<]{3,}</h[1-6]>',  # Headers with content
            r'<p[^>]*>[^<]{10,}</p>',  # Paragraphs with content
            r'<form[^>]*>',  # Forms
            r'<input[^>]*>',  # Inputs
            r'<a\s+href=["\'][^"\']+["\'][^>]*>[^<]+</a>',  # Links with content
            r'<script[^>]*>',  # JavaScript
            r'\.php|\.asp|\.jsp|\.py',  # Dynamic content indicators
            r'<meta[^>]*>',  # Meta tags
        ]
        
        meaningful_matches = 0
        for pattern in meaningful_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                meaningful_matches += 1
        
        # Require at least 2 meaningful patterns
        return meaningful_matches >= 2
    
    def _analyze_content_indicators(self, content: str) -> Dict[str, bool]:
        """Analyze content for various indicators"""
        content_lower = content.lower()
        
        indicators = {
            'has_forms': bool(re.search(r'<form[^>]*>', content_lower)),
            'has_inputs': bool(re.search(r'<input[^>]*>', content_lower)),
            'has_javascript': bool(re.search(r'<script[^>]*>', content_lower)),
            'has_links': bool(re.search(r'<a\s+href=', content_lower)),
            'has_images': bool(re.search(r'<img[^>]*>', content_lower)),
            'has_tables': bool(re.search(r'<table[^>]*>', content_lower)),
            'has_admin_content': bool(re.search(r'admin|dashboard|management', content_lower)),
            'has_api_content': bool(re.search(r'api|rest|graphql|swagger', content_lower)),
            'has_login_content': bool(re.search(r'login|signin|password', content_lower)),
            'has_config_content': bool(re.search(r'config|settings|environment', content_lower))
        }
        
        return indicators
    
    def prioritize_responses(self, urls: List[CrawledURL]) -> List[CrawledURL]:
        """Prioritize URLs based on response characteristics"""
        if not urls:
            return []
        
        def calculate_priority_score(url: CrawledURL) -> float:
            score = 0.0
            
            # Status code scoring
            if url.status_code:
                if 200 <= url.status_code < 300:
                    score += 10.0
                elif url.status_code in [401, 403]:
                    score += 8.0  # Protected resources are interesting
                elif 300 <= url.status_code < 400:
                    score += 5.0
                else:
                    score += 1.0
            
            # Content type scoring
            if url.content_type:
                ct = url.content_type.lower()
                if 'html' in ct:
                    score += 5.0
                elif 'json' in ct or 'xml' in ct:
                    score += 7.0
                elif 'javascript' in ct or 'css' in ct:
                    score += 3.0
                elif ct.startswith('image/'):
                    score -= 2.0
            
            # URL path scoring
            path = urlparse(url.url).path.lower()
            if any(keyword in path for keyword in ['admin', 'api', 'config', 'login']):
                score += 8.0
            elif any(keyword in path for keyword in ['test', 'debug', 'dev']):
                score += 5.0
            elif any(keyword in path for keyword in ['static', 'assets', 'css', 'js']):
                score -= 1.0
            
            # Response time scoring (faster is better)
            if url.response_time:
                if url.response_time < 1.0:
                    score += 2.0
                elif url.response_time > 10.0:
                    score -= 2.0
            
            # Content length scoring
            if url.content_length:
                if 1000 <= url.content_length <= 100000:  # Reasonable content
                    score += 3.0
                elif url.content_length > 1000000:  # Very large
                    score -= 1.0
            
            # Discovery source scoring
            if url.source:
                source_scores = {
                    'http_03': 3.0,
                    'custom_crawler': 2.0,
                    'hakrawler': 2.0,
                    'html_parsing': 1.0,
                    'seed': 0.5
                }
                source_name = url.source.value if hasattr(url.source, 'value') else str(url.source)
                score += source_scores.get(source_name, 0.0)
            
            return score
        
        # Sort by priority score (highest first)
        sorted_urls = sorted(urls, key=calculate_priority_score, reverse=True)
        return sorted_urls
    
    def get_filter_recommendations(self, urls: List[CrawledURL]) -> Dict[str, Any]:
        """Generate filtering recommendations based on URL analysis"""
        if not urls:
            return {'recommendations': []}
        
        recommendations = []
        
        # Analyze status code distribution
        status_codes = [url.status_code for url in urls if url.status_code]
        if status_codes:
            status_counts = {}
            for code in status_codes:
                status_counts[code] = status_counts.get(code, 0) + 1
            
            # Recommend filtering high-volume error codes
            for code, count in status_counts.items():
                if code >= 400 and count > len(urls) * 0.3:  # More than 30% of URLs
                    recommendations.append({
                        'type': 'status_code_filter',
                        'suggestion': f"Consider filtering status code {code} ({count} occurrences)",
                        'severity': 'medium'
                    })
        
        # Analyze content types
        content_types = [url.content_type for url in urls if url.content_type]
        if content_types:
            type_counts = {}
            for ct in content_types:
                base_type = ct.split('/')[0] if '/' in ct else ct
                type_counts[base_type] = type_counts.get(base_type, 0) + 1
            
            # Recommend filtering binary content
            for ct, count in type_counts.items():
                if ct in ['image', 'video', 'audio'] and count > 10:
                    recommendations.append({
                        'type': 'content_type_filter',
                        'suggestion': f"Consider filtering {ct} content ({count} occurrences)",
                        'severity': 'low'
                    })
        
        return {
            'recommendations': recommendations,
            'total_urls_analyzed': len(urls),
            'analysis_timestamp': datetime.now().isoformat()
        }