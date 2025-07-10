"""
Target Analyzer for IPCrawler Auto-Wordlist Selection
Simple HTTP technology detection for wordlist selection.
"""

import requests
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
import logging


class TargetAnalyzer:
    """Analyzes targets to detect technologies for wordlist selection."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Technology detection patterns
        self.server_patterns = {
            'apache': re.compile(r'apache', re.IGNORECASE),
            'nginx': re.compile(r'nginx', re.IGNORECASE),
            'iis': re.compile(r'iis|microsoft', re.IGNORECASE),
            'cloudflare': re.compile(r'cloudflare', re.IGNORECASE),
            'tomcat': re.compile(r'tomcat', re.IGNORECASE)
        }
        
        self.technology_patterns = {
            'php': re.compile(r'php', re.IGNORECASE),
            'asp': re.compile(r'asp\.net|aspx', re.IGNORECASE),
            'jsp': re.compile(r'jsp|java', re.IGNORECASE),
            'python': re.compile(r'python|django|flask', re.IGNORECASE),
            'ruby': re.compile(r'ruby|rails', re.IGNORECASE),
            'nodejs': re.compile(r'node\.js|express', re.IGNORECASE)
        }
        
        self.framework_patterns = {
            'wordpress': re.compile(r'wp-content|wordpress|wp-includes', re.IGNORECASE),
            'drupal': re.compile(r'drupal|sites/default', re.IGNORECASE),
            'joomla': re.compile(r'joomla|/administrator/', re.IGNORECASE),
            'laravel': re.compile(r'laravel', re.IGNORECASE),
            'django': re.compile(r'django|csrftoken', re.IGNORECASE),
            'rails': re.compile(r'rails|ruby', re.IGNORECASE)
        }
    
    def analyze_target(self, target: str) -> Dict[str, any]:
        """
        Analyze target URL to detect technologies.
        
        Args:
            target: Target URL to analyze
            
        Returns:
            Dictionary with detected technologies and metadata
        """
        analysis = {
            'target': target,
            'technologies': set(),
            'server': None,
            'frameworks': set(),
            'is_web': False,
            'has_api_indicators': False,
            'has_admin_indicators': False,
            'confidence': 'low'
        }
        
        try:
            # Normalize target URL
            if not target.startswith(('http://', 'https://')):
                target = f"http://{target}"
            
            # Make HTTP request with timeout
            response = requests.get(
                target,
                timeout=self.timeout,
                allow_redirects=True,
                headers={'User-Agent': 'IPCrawler/1.0 Security Scanner'}
            )
            
            analysis['is_web'] = True
            analysis['status_code'] = response.status_code
            
            # Analyze headers
            self._analyze_headers(response.headers, analysis)
            
            # Analyze response content
            if response.text:
                self._analyze_content(response.text, analysis)
            
            # Analyze URL patterns
            self._analyze_url_patterns(target, analysis)
            
            # Determine confidence level
            self._calculate_confidence(analysis)
            
        except requests.exceptions.Timeout:
            self.logger.debug(f"Timeout analyzing target: {target}")
            analysis['error'] = 'timeout'
        except requests.exceptions.ConnectionError:
            self.logger.debug(f"Connection error analyzing target: {target}")
            analysis['error'] = 'connection_error'
        except Exception as e:
            self.logger.debug(f"Error analyzing target {target}: {e}")
            analysis['error'] = str(e)
        
        # Convert sets to lists for JSON serialization
        analysis['technologies'] = list(analysis['technologies'])
        analysis['frameworks'] = list(analysis['frameworks'])
        
        return analysis
    
    def _analyze_headers(self, headers: Dict[str, str], analysis: Dict[str, any]) -> None:
        """Analyze HTTP headers for technology indicators."""
        
        # Server header analysis
        server = headers.get('Server', '').lower()
        if server:
            for tech, pattern in self.server_patterns.items():
                if pattern.search(server):
                    analysis['server'] = tech
                    analysis['technologies'].add(tech)
                    break
        
        # X-Powered-By header analysis
        powered_by = headers.get('X-Powered-By', '').lower()
        if powered_by:
            for tech, pattern in self.technology_patterns.items():
                if pattern.search(powered_by):
                    analysis['technologies'].add(tech)
        
        # Framework-specific headers
        framework_headers = {
            'wordpress': ['x-pingback'],
            'drupal': ['x-drupal-cache', 'x-generator'],
            'laravel': ['x-ratelimit-limit'],
            'django': ['x-frame-options'],
        }
        
        for framework, header_list in framework_headers.items():
            if any(header in headers for header in header_list):
                analysis['frameworks'].add(framework)
                analysis['technologies'].add(framework)
        
        # API indicators
        content_type = headers.get('Content-Type', '').lower()
        if 'application/json' in content_type or 'api' in headers.get('Server', '').lower():
            analysis['has_api_indicators'] = True
            analysis['technologies'].add('api')
    
    def _analyze_content(self, content: str, analysis: Dict[str, any]) -> None:
        """Analyze response content for technology indicators."""
        
        content_lower = content.lower()
        
        # Framework detection from content
        for framework, pattern in self.framework_patterns.items():
            if pattern.search(content):
                analysis['frameworks'].add(framework)
                analysis['technologies'].add(framework)
        
        # Technology detection from content
        for tech, pattern in self.technology_patterns.items():
            if pattern.search(content):
                analysis['technologies'].add(tech)
        
        # Admin panel indicators
        admin_indicators = [
            'admin', 'administrator', 'login', 'dashboard',
            'control panel', 'management', 'wp-admin'
        ]
        
        if any(indicator in content_lower for indicator in admin_indicators):
            analysis['has_admin_indicators'] = True
            analysis['technologies'].add('admin')
        
        # API indicators in content
        api_indicators = [
            '"api":', '/api/', 'rest', 'graphql', 'swagger',
            'application/json', 'api documentation'
        ]
        
        if any(indicator in content_lower for indicator in api_indicators):
            analysis['has_api_indicators'] = True
            analysis['technologies'].add('api')
    
    def _analyze_url_patterns(self, target: str, analysis: Dict[str, any]) -> None:
        """Analyze URL patterns for additional context."""
        
        parsed = urlparse(target)
        path = parsed.path.lower()
        
        # Admin path indicators
        admin_paths = ['/admin', '/administrator', '/wp-admin', '/management']
        if any(admin_path in path for admin_path in admin_paths):
            analysis['has_admin_indicators'] = True
            analysis['technologies'].add('admin')
        
        # API path indicators
        api_paths = ['/api', '/rest', '/graphql', '/v1/', '/v2/']
        if any(api_path in path for api_path in api_paths):
            analysis['has_api_indicators'] = True
            analysis['technologies'].add('api')
        
        # File extension indicators
        if path.endswith(('.php', '.php5')):
            analysis['technologies'].add('php')
        elif path.endswith(('.asp', '.aspx')):
            analysis['technologies'].add('asp')
        elif path.endswith(('.jsp', '.java')):
            analysis['technologies'].add('jsp')
    
    def _calculate_confidence(self, analysis: Dict[str, any]) -> None:
        """Calculate confidence level based on detected indicators."""
        
        indicators_count = (
            len(analysis['technologies']) +
            len(analysis['frameworks']) +
            (1 if analysis['server'] else 0)
        )
        
        if indicators_count >= 3:
            analysis['confidence'] = 'high'
        elif indicators_count >= 2:
            analysis['confidence'] = 'medium'
        else:
            analysis['confidence'] = 'low'
    
    def get_wordlist_context(self, analysis: Dict[str, any]) -> Dict[str, any]:
        """
        Extract wordlist selection context from analysis.
        
        Args:
            analysis: Target analysis result
            
        Returns:
            Context dictionary for wordlist selection
        """
        
        context = {
            'technologies': analysis.get('technologies', []),
            'primary_technology': None,
            'context_hints': [],
            'confidence': analysis.get('confidence', 'low')
        }
        
        # Determine primary technology
        tech_priority = ['wordpress', 'drupal', 'joomla', 'php', 'asp', 'jsp', 'python']
        for tech in tech_priority:
            if tech in analysis.get('technologies', []):
                context['primary_technology'] = tech
                break
        
        # Add context hints
        if analysis.get('has_admin_indicators'):
            context['context_hints'].append('admin')
        
        if analysis.get('has_api_indicators'):
            context['context_hints'].append('api')
        
        if analysis.get('is_web'):
            context['context_hints'].append('web')
        
        # Add server context
        if analysis.get('server'):
            context['context_hints'].append(analysis['server'])
        
        return context


def analyze_target_simple(target: str, timeout: int = 10) -> Dict[str, any]:
    """
    Simple function interface for target analysis.
    
    Args:
        target: Target URL to analyze
        timeout: Request timeout in seconds
        
    Returns:
        Analysis result dictionary
    """
    analyzer = TargetAnalyzer(timeout=timeout)
    return analyzer.analyze_target(target)