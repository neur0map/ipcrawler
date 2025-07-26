"""Technology Detector Module for HTTP_03 Workflow

Handles detection of web technologies from headers, response content, and other indicators.
"""

import re
from typing import List, Dict, Any

from .models import HTTPService


class TechnologyDetector:
    """Handles detection of web technologies and frameworks"""
    
    def __init__(self):
        """Initialize technology detector"""
        pass
    
    async def detect_technologies(self, service: HTTPService) -> List[str]:
        """Detect technologies from headers and response"""
        technologies = []
        
        # From headers
        header_technologies = self._detect_from_headers(service.headers)
        technologies.extend(header_technologies)
        
        # From response body patterns
        if service.response_body:
            body_technologies = self._detect_from_response_body(service.response_body)
            technologies.extend(body_technologies)
        
        # From URL patterns
        url_technologies = self._detect_from_url(service.url)
        technologies.extend(url_technologies)
        
        return list(set(technologies))  # Remove duplicates
    
    def _detect_from_headers(self, headers: Dict[str, str]) -> List[str]:
        """Detect technologies from HTTP headers"""
        technologies = []
        
        # Technology-specific headers
        tech_headers = {
            'x-powered-by': lambda v: v,
            'server': lambda v: v.split('/')[0] if '/' in v else v,
            'x-generator': lambda v: v,
            'x-drupal-cache': lambda v: 'Drupal',
            'x-wordpress-caching': lambda v: 'WordPress',
            'x-aspnet-version': lambda v: 'ASP.NET',
            'x-aspnetmvc-version': lambda v: 'ASP.NET MVC',
            'x-django-version': lambda v: 'Django',
            'x-rails-version': lambda v: 'Ruby on Rails',
            'x-framework': lambda v: v,
            'x-runtime': lambda v: v,
            'x-version': lambda v: v
        }
        
        for header, parser in tech_headers.items():
            value = headers.get(header, '')
            if value:
                tech = parser(value)
                if tech and tech not in technologies:
                    technologies.append(tech)
        
        # Server header analysis
        server_header = headers.get('server', '').lower()
        if server_header:
            server_technologies = self._analyze_server_header(server_header)
            technologies.extend(server_technologies)
        
        # Content-Type analysis
        content_type = headers.get('content-type', '').lower()
        if content_type:
            ct_technologies = self._analyze_content_type(content_type)
            technologies.extend(ct_technologies)
        
        # Cookie analysis
        set_cookie = headers.get('set-cookie', '').lower()
        if set_cookie:
            cookie_technologies = self._analyze_cookies(set_cookie)
            technologies.extend(cookie_technologies)
        
        return technologies
    
    def _analyze_server_header(self, server_header: str) -> List[str]:
        """Analyze server header for technology indicators"""
        technologies = []
        
        server_patterns = {
            'apache': 'Apache',
            'nginx': 'Nginx',
            'iis': 'IIS',
            'tomcat': 'Apache Tomcat',
            'jetty': 'Jetty',
            'lighttpd': 'Lighttpd',
            'caddy': 'Caddy',
            'cloudflare': 'Cloudflare',
            'openresty': 'OpenResty',
            'gunicorn': 'Gunicorn',
            'uwsgi': 'uWSGI',
            'passenger': 'Passenger',
            'kestrel': 'Kestrel',
            'node.js': 'Node.js',
            'express': 'Express.js'
        }
        
        for pattern, tech in server_patterns.items():
            if pattern in server_header:
                technologies.append(tech)
        
        return technologies
    
    def _analyze_content_type(self, content_type: str) -> List[str]:
        """Analyze content-type header for technology indicators"""
        technologies = []
        
        if 'application/json' in content_type:
            technologies.append('JSON API')
        elif 'application/xml' in content_type:
            technologies.append('XML API')
        elif 'text/xml' in content_type:
            technologies.append('XML')
        
        return technologies
    
    def _analyze_cookies(self, cookies: str) -> List[str]:
        """Analyze cookies for technology indicators"""
        technologies = []
        
        cookie_patterns = {
            'phpsessid': 'PHP',
            'jsessionid': 'Java',
            'asp.net_sessionid': 'ASP.NET',
            'cfid': 'ColdFusion',
            'cftoken': 'ColdFusion',
            'django': 'Django',
            'rails': 'Ruby on Rails',
            'laravel_session': 'Laravel',
            'symfony': 'Symfony',
            'wordpress': 'WordPress',
            'drupal': 'Drupal',
            'joomla': 'Joomla'
        }
        
        for pattern, tech in cookie_patterns.items():
            if pattern in cookies:
                technologies.append(tech)
        
        return technologies
    
    def _detect_from_response_body(self, response_body: str) -> List[str]:
        """Detect technologies from response body patterns"""
        technologies = []
        
        # Framework and CMS patterns
        patterns = {
            'WordPress': [
                r'wp-content',
                r'wp-includes',
                r'wp-admin',
                r'/wp-json/',
                r'wordpress'
            ],
            'Drupal': [
                r'drupal',
                r'sites/default/files',
                r'misc/drupal\.js',
                r'Drupal\.settings'
            ],
            'Joomla': [
                r'joomla',
                r'/media/jui/',
                r'option=com_',
                r'Joomla!'
            ],
            'Django': [
                r'csrfmiddlewaretoken',
                r'django',
                r'__admin_media_prefix__'
            ],
            'Ruby on Rails': [
                r'rails',
                r'csrf-token',
                r'authenticity_token'
            ],
            'ASP.NET': [
                r'__VIEWSTATE',
                r'__EVENTVALIDATION',
                r'aspnet',
                r'ctl00'
            ],
            'PHP': [
                r'\.php["\s]',
                r'\?php',
                r'PHPSESSID'
            ],
            'Node.js': [
                r'node\.js',
                r'express'
            ],
            'React': [
                r'react',
                r'React',
                r'_react',
                r'data-reactroot'
            ],
            'Angular': [
                r'ng-version',
                r'angular',
                r'ng-app',
                r'data-ng-'
            ],
            'Vue.js': [
                r'vue',
                r'Vue',
                r'v-if',
                r'v-for'
            ],
            'jQuery': [
                r'jquery',
                r'jQuery',
                r'\$\('
            ],
            'Bootstrap': [
                r'bootstrap',
                r'Bootstrap',
                r'btn-primary',
                r'container-fluid'
            ],
            'Laravel': [
                r'laravel',
                r'Laravel',
                r'laravel_session'
            ],
            'Symfony': [
                r'symfony',
                r'Symfony',
                r'_sf2_'
            ],
            'CodeIgniter': [
                r'codeigniter',
                r'CodeIgniter',
                r'ci_session'
            ],
            'CakePHP': [
                r'cakephp',
                r'CakePHP',
                r'cake:'
            ],
            'Magento': [
                r'magento',
                r'Magento',
                r'MAGENTO_ROOT'
            ],
            'Shopify': [
                r'shopify',
                r'Shopify',
                r'myshopify'
            ],
            'MediaWiki': [
                r'mediawiki',
                r'MediaWiki',
                r'wgVersion'
            ],
            'TYPO3': [
                r'typo3',
                r'TYPO3',
                r'typo3conf'
            ]
        }
        
        for tech, tech_patterns in patterns.items():
            for pattern in tech_patterns:
                if re.search(pattern, response_body, re.IGNORECASE):
                    technologies.append(tech)
                    break  # Found one pattern for this tech, no need to check others
        
        # JavaScript libraries and frameworks
        js_patterns = {
            'AngularJS': r'angular\.js|ng-app',
            'Backbone.js': r'backbone\.js|Backbone',
            'Ember.js': r'ember\.js|Ember',
            'Knockout.js': r'knockout\.js|ko\.',
            'Prototype': r'prototype\.js|Prototype',
            'MooTools': r'mootools|MooTools',
            'Underscore.js': r'underscore\.js|_\.',
            'Lodash': r'lodash\.js|_\.',
            'Moment.js': r'moment\.js|moment\(',
            'Chart.js': r'chart\.js|Chart\(',
            'D3.js': r'd3\.js|d3\.',
            'Three.js': r'three\.js|THREE\.'
        }
        
        for tech, pattern in js_patterns.items():
            if re.search(pattern, response_body, re.IGNORECASE):
                technologies.append(tech)
        
        # CSS frameworks
        css_patterns = {
            'Foundation': r'foundation\.css|Foundation',
            'Bulma': r'bulma\.css|Bulma',
            'Semantic UI': r'semantic\.css|semantic-ui',
            'Materialize': r'materialize\.css|Materialize',
            'Pure CSS': r'pure\.css|Pure'
        }
        
        for tech, pattern in css_patterns.items():
            if re.search(pattern, response_body, re.IGNORECASE):
                technologies.append(tech)
        
        return technologies
    
    def _detect_from_url(self, url: str) -> List[str]:
        """Detect technologies from URL patterns"""
        technologies = []
        
        url_patterns = {
            'WordPress': r'/wp-content/|/wp-admin/|/wp-includes/',
            'Drupal': r'/sites/default/|/modules/|/themes/',
            'Joomla': r'/components/|/modules/|/templates/',
            'PHP': r'\.php(\?|$)',
            'ASP.NET': r'\.aspx?(\?|$)',
            'JSP': r'\.jsp(\?|$)',
            'ColdFusion': r'\.cfm(\?|$)',
            'Perl': r'\.pl(\?|$)',
            'Python': r'\.py(\?|$)'
        }
        
        for tech, pattern in url_patterns.items():
            if re.search(pattern, url, re.IGNORECASE):
                technologies.append(tech)
        
        return technologies
    
    def get_technology_confidence(self, service: HTTPService, technology: str) -> str:
        """Get confidence level for detected technology"""
        # This could be enhanced with more sophisticated scoring
        
        high_confidence_indicators = {
            'WordPress': ['wp-content', 'wp-admin', 'wp-json'],
            'Drupal': ['drupal', 'sites/default'],
            'Joomla': ['joomla', 'option=com_'],
            'Django': ['csrfmiddlewaretoken'],
            'ASP.NET': ['__VIEWSTATE'],
            'PHP': ['PHPSESSID', '.php']
        }
        
        if technology in high_confidence_indicators:
            indicators = high_confidence_indicators[technology]
            content = service.response_body or ''
            headers_str = str(service.headers).lower()
            url = service.url.lower()
            
            found_indicators = sum(1 for indicator in indicators 
                                 if indicator.lower() in content.lower() 
                                 or indicator.lower() in headers_str 
                                 or indicator.lower() in url)
            
            if found_indicators >= 2:
                return 'HIGH'
            elif found_indicators == 1:
                return 'MEDIUM'
        
        return 'LOW'