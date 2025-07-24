"""Enhanced Mini Spider Intelligence Analyzer

Deep analysis of discovered URLs, content inspection, and advanced wordlist intelligence.
Extends the base Mini Spider functionality with comprehensive security analysis.
"""

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from urllib.parse import urlparse, urljoin
from collections import Counter, defaultdict

# HTTP libraries with fallback
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import subprocess

from .models import (
    CrawledURL, InterestingFinding, SeverityLevel, 
    URLCategory, DiscoverySource, MiniSpiderResult
)
from src.core.utils.debugging import debug_print


class EnhancedAnalyzer:
    """Enhanced intelligence analyzer for Mini Spider results"""
    
    def __init__(self):
        self.session = None
        self.analysis_timeout = 10  # seconds per request
        self.max_content_size = 1024 * 1024  # 1MB max download
        self.max_concurrent_analysis = 5
        
        # Technology fingerprints
        self.tech_fingerprints = self._load_tech_fingerprints()
        
        # Wordlist mappings
        self.wordlist_mappings = self._load_wordlist_mappings()
        
        # Initialize HTTP session if available
        if HTTPX_AVAILABLE:
            self.session = httpx.AsyncClient(
                timeout=self.analysis_timeout,
                follow_redirects=True,
                verify=False  # For testing environments
            )
    
    async def analyze_spider_results(self, spider_result: MiniSpiderResult) -> Dict[str, Any]:
        """Perform enhanced analysis of spider results"""
        debug_print("Starting enhanced analysis of spider results")
        
        analysis_start_time = time.time()
        
        # Initialize analysis result structure
        enhanced_analysis = {
            'target': spider_result.target,
            'analysis_timestamp': datetime.now().isoformat(),
            'critical_intelligence': {},
            'technology_profile': {},
            'security_assessment': {},
            'wordlist_recommendations': {},
            'deep_findings': [],
            'execution_time': 0.0
        }
        
        try:
            # Phase 1: Deep content inspection of critical findings
            critical_intel = await self._inspect_critical_findings(spider_result.interesting_findings)
            enhanced_analysis['critical_intelligence'] = critical_intel
            
            # Phase 2: Technology fingerprinting
            tech_profile = await self._analyze_technology_stack(spider_result.discovered_urls)
            enhanced_analysis['technology_profile'] = tech_profile
            
            # Phase 3: Security assessment
            security_assessment = await self._perform_security_assessment(
                spider_result.discovered_urls, 
                spider_result.interesting_findings
            )
            enhanced_analysis['security_assessment'] = security_assessment
            
            # Phase 4: Advanced wordlist recommendations
            wordlist_recs = await self._generate_advanced_wordlist_recommendations(
                tech_profile, 
                security_assessment, 
                spider_result.categorized_results
            )
            enhanced_analysis['wordlist_recommendations'] = wordlist_recs
            
            # Phase 5: Deep pattern analysis
            deep_findings = await self._discover_deep_patterns(spider_result.discovered_urls)
            enhanced_analysis['deep_findings'] = deep_findings
            
            # Calculate execution time
            enhanced_analysis['execution_time'] = time.time() - analysis_start_time
            
            debug_print(f"Enhanced analysis completed in {enhanced_analysis['execution_time']:.2f}s")
            
            return enhanced_analysis
            
        except Exception as e:
            debug_print(f"Enhanced analysis failed: {str(e)}", level="ERROR")
            enhanced_analysis['error'] = str(e)
            enhanced_analysis['execution_time'] = time.time() - analysis_start_time
            return enhanced_analysis
        
        finally:
            if self.session:
                await self.session.aclose()
    
    async def _inspect_critical_findings(self, findings: List[InterestingFinding]) -> Dict[str, Any]:
        """Deep inspection of critical and high-severity findings"""
        debug_print("Performing deep inspection of critical findings")
        
        critical_intel = {
            'exposed_files': {},
            'configuration_leaks': {},
            'admin_interfaces': {},
            'api_endpoints': {},
            'security_headers': {},
            'error_information': {}
        }
        
        # Filter for critical and high findings
        high_priority_findings = [
            f for f in findings 
            if f.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
        ]
        
        # Process findings concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent_analysis)
        tasks = []
        
        for finding in high_priority_findings:
            task = self._inspect_single_finding(finding, semaphore)
            tasks.append(task)
        
        # Execute all inspections
        inspection_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for finding, result in zip(high_priority_findings, inspection_results):
            if isinstance(result, Exception):
                debug_print(f"Inspection failed for {finding.url}: {result}", level="ERROR")
                continue
            
            if result:
                self._categorize_inspection_result(finding, result, critical_intel)
        
        return critical_intel
    
    async def _inspect_single_finding(self, finding: InterestingFinding, semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
        """Inspect a single finding for additional intelligence"""
        async with semaphore:
            try:
                if not HTTPX_AVAILABLE:
                    return await self._inspect_with_curl(finding.url)
                
                response = await self.session.get(
                    finding.url,
                    timeout=self.analysis_timeout
                )
                
                # Extract comprehensive information
                inspection_data = {
                    'url': finding.url,
                    'finding_type': finding.finding_type,
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content_length': len(response.content),
                    'response_time': response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0,
                    'content_preview': '',
                    'technology_indicators': [],
                    'security_issues': [],
                    'interesting_patterns': []
                }
                
                # Analyze content if it's text-based
                if self._is_text_content(response.headers.get('content-type', '')):
                    content = response.text[:self.max_content_size]
                    inspection_data['content_preview'] = content[:1000]  # First 1KB for preview
                    
                    # Extract technology indicators
                    inspection_data['technology_indicators'] = self._extract_tech_indicators(content, response.headers)
                    
                    # Find security issues
                    inspection_data['security_issues'] = self._find_security_issues(content, finding.finding_type)
                    
                    # Find interesting patterns
                    inspection_data['interesting_patterns'] = self._find_interesting_patterns(content)
                
                return inspection_data
                
            except Exception as e:
                debug_print(f"Failed to inspect {finding.url}: {str(e)}")
                return None
    
    async def _inspect_with_curl(self, url: str) -> Optional[Dict[str, Any]]:
        """Fallback inspection using curl when httpx is not available"""
        try:
            # Use curl with headers and limited size
            cmd = [
                'curl', '-s', '-I', '--max-time', str(self.analysis_timeout),
                '--max-filesize', str(self.max_content_size),
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.analysis_timeout + 5)
            
            if result.returncode == 0:
                headers = {}
                lines = result.stdout.strip().split('\n')
                
                for line in lines[1:]:  # Skip status line
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip().lower()] = value.strip()
                
                return {
                    'url': url,
                    'headers': headers,
                    'content_preview': '',
                    'technology_indicators': [],
                    'security_issues': [],
                    'interesting_patterns': []
                }
            
        except Exception as e:
            debug_print(f"Curl inspection failed for {url}: {str(e)}")
        
        return None
    
    def _is_text_content(self, content_type: str) -> bool:
        """Check if content type is text-based and worth analyzing"""
        text_types = [
            'text/', 'application/json', 'application/xml', 
            'application/javascript', 'application/x-javascript'
        ]
        return any(ct in content_type.lower() for ct in text_types)
    
    def _extract_tech_indicators(self, content: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract technology indicators from content and headers"""
        indicators = []
        
        # Check headers for technology indicators
        for header, value in headers.items():
            header_lower = header.lower()
            
            # Server headers
            if header_lower == 'server':
                indicators.append({
                    'type': 'server',
                    'technology': value,
                    'confidence': 0.9,
                    'source': 'header'
                })
            
            # Framework headers
            elif header_lower.startswith('x-powered-by'):
                indicators.append({
                    'type': 'framework',
                    'technology': value,
                    'confidence': 0.95,
                    'source': 'header'
                })
        
        # Check content for technology patterns
        for pattern, tech_info in self.tech_fingerprints.items():
            if re.search(pattern, content, re.IGNORECASE):
                indicators.append({
                    'type': tech_info['type'],
                    'technology': tech_info['name'],
                    'confidence': tech_info['confidence'],
                    'source': 'content',
                    'pattern': pattern
                })
        
        return indicators
    
    def _find_security_issues(self, content: str, finding_type: str) -> List[Dict[str, Any]]:
        """Find potential security issues in content"""
        security_issues = []
        
        # Common security issue patterns
        security_patterns = {
            'credentials_exposed': [
                r'password\s*[=:]\s*["\']?(\w+)',
                r'api[_-]?key\s*[=:]\s*["\']?([a-zA-Z0-9_-]+)',
                r'secret\s*[=:]\s*["\']?(\w+)',
                r'token\s*[=:]\s*["\']?([a-zA-Z0-9_.-]+)'
            ],
            'database_info': [
                r'mysql://[^\\s]+',
                r'postgresql://[^\\s]+',
                r'mongodb://[^\\s]+',
                r'DB_HOST\s*[=:]\s*["\']?([^\\s"\']+)'
            ],
            'internal_paths': [
                r'(/var/[^\\s]+)',
                r'(/etc/[^\\s]+)',
                r'(/home/[^\\s]+)',
                r'(C:\\\\[^\\s]+)'
            ],
            'debug_info': [
                r'stack trace',
                r'traceback',
                r'debug.*mode.*on',
                r'error.*line.*\d+'
            ]
        }
        
        for issue_type, patterns in security_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    security_issues.append({
                        'type': issue_type,
                        'pattern': pattern,
                        'match': match.group(0),
                        'severity': self._assess_security_severity(issue_type, finding_type)
                    })
        
        return security_issues
    
    def _find_interesting_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Find interesting patterns that might aid in further analysis"""
        patterns = []
        
        # URLs and endpoints
        url_pattern = r'https?://[^\s<>"\']+|/[^\s<>"\']*\.(?:php|asp|aspx|jsp|cgi)'
        for match in re.finditer(url_pattern, content):
            patterns.append({
                'type': 'endpoint',
                'value': match.group(0),
                'context': 'discovered_url'
            })
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, content):
            patterns.append({
                'type': 'email',
                'value': match.group(0),
                'context': 'contact_info'
            })
        
        # Version numbers
        version_pattern = r'v?(\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?)'
        for match in re.finditer(version_pattern, content):
            patterns.append({
                'type': 'version',
                'value': match.group(0),
                'context': 'software_version'
            })
        
        return patterns
    
    def _assess_security_severity(self, issue_type: str, finding_type: str) -> str:
        """Assess the severity of a security issue"""
        severity_map = {
            'credentials_exposed': 'critical',
            'database_info': 'high',
            'internal_paths': 'medium',
            'debug_info': 'low'
        }
        
        base_severity = severity_map.get(issue_type, 'low')
        
        # Increase severity for certain finding types
        if finding_type in ['git_repository', 'environment_file']:
            if base_severity == 'high':
                return 'critical'
            elif base_severity == 'medium':
                return 'high'
        
        return base_severity
    
    def _categorize_inspection_result(self, finding: InterestingFinding, result: Dict[str, Any], critical_intel: Dict[str, Any]):
        """Categorize inspection results into appropriate intelligence categories"""
        finding_type = finding.finding_type
        
        # Categorize based on finding type
        if finding_type in ['environment_file', 'git_repository', 'backup_file']:
            critical_intel['exposed_files'][finding.url] = result
        
        elif finding_type in ['config_file', 'php_info', 'server_status']:
            critical_intel['configuration_leaks'][finding.url] = result
        
        elif finding_type in ['admin_panel', 'dashboard', 'tomcat_manager']:
            critical_intel['admin_interfaces'][finding.url] = result
        
        elif finding_type in ['api_endpoint', 'api_docs']:
            critical_intel['api_endpoints'][finding.url] = result
        
        # Extract security headers information
        if 'headers' in result:
            security_headers = self._analyze_security_headers(result['headers'])
            if security_headers:
                critical_intel['security_headers'][finding.url] = security_headers
        
        # Extract error information
        if result.get('security_issues'):
            error_info = [issue for issue in result['security_issues'] if issue['type'] == 'debug_info']
            if error_info:
                critical_intel['error_information'][finding.url] = error_info
    
    def _analyze_security_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze security headers"""
        security_analysis = {
            'missing_headers': [],
            'weak_configurations': [],
            'good_practices': []
        }
        
        # Important security headers to check
        security_headers = {
            'x-frame-options': 'Clickjacking protection',
            'x-content-type-options': 'MIME type sniffing protection',
            'x-xss-protection': 'XSS protection',
            'strict-transport-security': 'HTTPS enforcement',
            'content-security-policy': 'Content Security Policy',
            'referrer-policy': 'Referrer policy',
            'permissions-policy': 'Permissions policy'
        }
        
        for header, description in security_headers.items():
            if header not in [h.lower() for h in headers.keys()]:
                security_analysis['missing_headers'].append({
                    'header': header,
                    'description': description,
                    'impact': 'security_improvement'
                })
            else:
                security_analysis['good_practices'].append({
                    'header': header,
                    'description': description
                })
        
        return security_analysis
    
    def _load_tech_fingerprints(self) -> Dict[str, Dict[str, Any]]:
        """Load technology fingerprinting patterns"""
        return {
            r'WordPress': {
                'type': 'cms',
                'name': 'WordPress',
                'confidence': 0.9
            },
            r'Drupal': {
                'type': 'cms', 
                'name': 'Drupal',
                'confidence': 0.9
            },
            r'Joomla': {
                'type': 'cms',
                'name': 'Joomla',
                'confidence': 0.9
            },
            r'Laravel': {
                'type': 'framework',
                'name': 'Laravel',
                'confidence': 0.85
            },
            r'Django': {
                'type': 'framework',
                'name': 'Django',
                'confidence': 0.85
            },
            r'React': {
                'type': 'frontend',
                'name': 'React',
                'confidence': 0.8
            },
            r'Angular': {
                'type': 'frontend',
                'name': 'Angular',
                'confidence': 0.8
            },
            r'Vue\.js': {
                'type': 'frontend',
                'name': 'Vue.js',
                'confidence': 0.8
            }
        }
    
    def _load_wordlist_mappings(self) -> Dict[str, List[str]]:
        """Load wordlist mappings for different technologies"""
        return {
            'wordpress': ['wp-common.txt', 'cms-wordpress.txt', 'wp-plugins.txt'],
            'drupal': ['cms-drupal.txt', 'drupal-modules.txt'],
            'joomla': ['cms-joomla.txt', 'joomla-components.txt'],
            'laravel': ['framework-laravel.txt', 'php-frameworks.txt'],
            'django': ['framework-django.txt', 'python-frameworks.txt'],
            'nginx': ['web-nginx.txt', 'server-configs.txt'],
            'apache': ['web-apache.txt', 'server-configs.txt'],
            'api': ['api-endpoints.txt', 'rest-api.txt'],
            'admin': ['admin-panels.txt', 'management-interfaces.txt'],
            'config': ['config-files.txt', 'sensitive-files.txt']
        }

    async def _analyze_technology_stack(self, urls: List[CrawledURL]) -> Dict[str, Any]:
        """Analyze the technology stack based on discovered URLs"""
        debug_print("Analyzing technology stack from discovered URLs")
        
        tech_analysis = {
            'detected_technologies': [],
            'confidence_scores': {},
            'framework_indicators': [],
            'server_technologies': [],
            'cms_indicators': [],
            'language_indicators': []
        }
        
        # Analyze URL patterns for technology indicators
        tech_counters = {
            'cms': Counter(),
            'framework': Counter(), 
            'language': Counter(),
            'server': Counter()
        }
        
        for url in urls:
            parsed_url = urlparse(url.url)
            path = parsed_url.path.lower()
            
            # CMS Detection
            if '/wp-' in path or 'wordpress' in path:
                tech_counters['cms']['wordpress'] += 1
            elif '/drupal' in path or 'sites/default' in path:
                tech_counters['cms']['drupal'] += 1
            elif '/joomla' in path or 'administrator' in path:
                tech_counters['cms']['joomla'] += 1
            
            # Framework Detection
            if '/laravel' in path or 'app/Http' in path:
                tech_counters['framework']['laravel'] += 1
            elif '/django' in path or 'admin/login' in path:
                tech_counters['framework']['django'] += 1
            elif '/spring' in path or '.do' in path:
                tech_counters['framework']['spring'] += 1
            
            # Language Detection
            if path.endswith('.php'):
                tech_counters['language']['php'] += 1
            elif path.endswith('.asp') or path.endswith('.aspx'):
                tech_counters['language']['asp.net'] += 1
            elif path.endswith('.jsp'):
                tech_counters['language']['java'] += 1
            elif path.endswith('.py'):
                tech_counters['language']['python'] += 1
            
            # Server hints from headers if available
            if hasattr(url, 'headers') and url.headers:
                server_header = url.headers.get('server', '').lower()
                if 'nginx' in server_header:
                    tech_counters['server']['nginx'] += 1
                elif 'apache' in server_header:
                    tech_counters['server']['apache'] += 1
                elif 'iis' in server_header:
                    tech_counters['server']['iis'] += 1
        
        # Process technology detection results
        total_urls = len(urls)
        
        for tech_type, counter in tech_counters.items():
            for tech_name, count in counter.most_common(3):  # Top 3 per category
                confidence = min(0.95, count / total_urls + 0.1)  # Cap at 95%
                
                tech_info = {
                    'name': tech_name,
                    'type': tech_type,
                    'confidence': confidence,
                    'evidence_count': count,
                    'indicators': []
                }
                
                tech_analysis['detected_technologies'].append(tech_info)
                tech_analysis['confidence_scores'][tech_name] = confidence
                
                # Categorize by type
                if tech_type == 'cms':
                    tech_analysis['cms_indicators'].append(tech_info)
                elif tech_type == 'framework':
                    tech_analysis['framework_indicators'].append(tech_info)
                elif tech_type == 'server':
                    tech_analysis['server_technologies'].append(tech_info)
                elif tech_type == 'language':
                    tech_analysis['language_indicators'].append(tech_info)
        
        debug_print(f"Detected {len(tech_analysis['detected_technologies'])} technologies")
        return tech_analysis
    
    async def _perform_security_assessment(self, urls: List[CrawledURL], findings: List[InterestingFinding]) -> Dict[str, Any]:
        """Perform comprehensive security assessment"""
        debug_print("Performing security assessment of discovered findings")
        
        security_assessment = {
            'risk_score': 0,
            'vulnerability_indicators': [],
            'attack_surface': {},
            'security_recommendations': [],
            'exposure_analysis': {},
            'threat_vectors': []
        }
        
        # Calculate base risk score from findings
        risk_weights = {
            SeverityLevel.CRITICAL: 40,
            SeverityLevel.HIGH: 20,
            SeverityLevel.MEDIUM: 10,
            SeverityLevel.LOW: 5,
            SeverityLevel.INFO: 1
        }
        
        total_risk = 0
        severity_counts = Counter()
        
        for finding in findings:
            severity_counts[finding.severity] += 1
            total_risk += risk_weights.get(finding.severity, 0)
        
        # Normalize risk score (0-100)
        security_assessment['risk_score'] = min(100, total_risk)
        
        # Analyze attack surface
        attack_surface = {
            'admin_interfaces': len([f for f in findings if 'admin' in f.finding_type]),
            'api_endpoints': len([f for f in findings if 'api' in f.finding_type]),
            'config_exposures': len([f for f in findings if 'config' in f.finding_type or 'environment' in f.finding_type]),
            'auth_endpoints': len([f for f in findings if 'login' in f.finding_type or 'auth' in f.finding_type]),
            'debug_interfaces': len([f for f in findings if 'debug' in f.finding_type or 'info' in f.finding_type])
        }
        security_assessment['attack_surface'] = attack_surface
        
        # Identify vulnerability indicators
        vuln_indicators = []
        
        # Check for common vulnerability patterns
        critical_findings = [f for f in findings if f.severity == SeverityLevel.CRITICAL]
        for finding in critical_findings:
            if finding.finding_type == 'git_repository':
                vuln_indicators.append({
                    'type': 'source_code_exposure',
                    'description': 'Git repository exposed - may contain credentials, keys, or sensitive code',
                    'severity': 'critical',
                    'impact': 'Full application source code and history accessible',
                    'recommendation': 'Immediately block access to .git directory'
                })
            
            elif finding.finding_type == 'environment_file':
                vuln_indicators.append({
                    'type': 'configuration_exposure',
                    'description': 'Environment file exposed - likely contains sensitive configuration',
                    'severity': 'critical',
                    'impact': 'Database credentials, API keys, and secrets may be exposed',
                    'recommendation': 'Remove environment file from web root'
                })
        
        high_findings = [f for f in findings if f.severity == SeverityLevel.HIGH]
        for finding in high_findings:
            if finding.finding_type == 'admin_panel':
                vuln_indicators.append({
                    'type': 'privileged_access',
                    'description': 'Admin panel discovered - potential privilege escalation target',
                    'severity': 'high',
                    'impact': 'Administrative access if credentials are weak or default',
                    'recommendation': 'Ensure strong authentication and access controls'
                })
        
        security_assessment['vulnerability_indicators'] = vuln_indicators
        
        # Generate threat vectors
        threat_vectors = []
        
        if attack_surface['admin_interfaces'] > 0:
            threat_vectors.append({
                'vector': 'Administrative Interface Attack',
                'description': 'Brute force or credential stuffing against admin panels',
                'likelihood': 'high' if attack_surface['admin_interfaces'] > 2 else 'medium',
                'wordlists': ['admin-passwords.txt', 'default-credentials.txt']
            })
        
        if attack_surface['api_endpoints'] > 0:
            threat_vectors.append({
                'vector': 'API Enumeration Attack',
                'description': 'Discovery and exploitation of API endpoints',
                'likelihood': 'medium',
                'wordlists': ['api-endpoints.txt', 'rest-api.txt']
            })
        
        if attack_surface['config_exposures'] > 0:
            threat_vectors.append({
                'vector': 'Configuration Exploitation',
                'description': 'Leverage exposed configuration for further access',
                'likelihood': 'high',
                'wordlists': ['config-files.txt', 'sensitive-files.txt']
            })
        
        security_assessment['threat_vectors'] = threat_vectors
        
        # Generate security recommendations
        recommendations = []
        
        if severity_counts[SeverityLevel.CRITICAL] > 0:
            recommendations.append({
                'priority': 1,
                'action': 'Immediate Response Required',
                'description': f'Address {severity_counts[SeverityLevel.CRITICAL]} critical security exposures immediately',
                'impact': 'Critical security risk - potential for complete compromise'
            })
        
        if attack_surface['admin_interfaces'] > 0:
            recommendations.append({
                'priority': 2,
                'action': 'Secure Administrative Access',
                'description': 'Implement strong authentication and IP restrictions for admin interfaces',
                'impact': 'Prevents unauthorized administrative access'
            })
        
        if attack_surface['config_exposures'] > 0:
            recommendations.append({
                'priority': 2,
                'action': 'Hide Configuration Files',
                'description': 'Remove or properly protect configuration and environment files',
                'impact': 'Prevents exposure of sensitive configuration data'
            })
        
        recommendations.append({
            'priority': 3,
            'action': 'Implement Security Headers',
            'description': 'Add comprehensive security headers to all responses',
            'impact': 'Provides defense-in-depth against various attack vectors'
        })
        
        security_assessment['security_recommendations'] = recommendations
        
        # Exposure analysis
        security_assessment['exposure_analysis'] = {
            'total_findings': len(findings),
            'critical_exposures': severity_counts[SeverityLevel.CRITICAL],
            'high_risk_exposures': severity_counts[SeverityLevel.HIGH],
            'information_disclosures': severity_counts[SeverityLevel.LOW] + severity_counts[SeverityLevel.INFO],
            'overall_exposure': 'critical' if severity_counts[SeverityLevel.CRITICAL] > 0 else 'high' if severity_counts[SeverityLevel.HIGH] > 0 else 'medium'
        }
        
        debug_print(f"Security assessment completed - Risk score: {security_assessment['risk_score']}")
        return security_assessment
    
    async def _generate_advanced_wordlist_recommendations(self, tech_profile: Dict[str, Any], 
                                                        security_assessment: Dict[str, Any],
                                                        categorized_results: Dict[str, List[CrawledURL]]) -> Dict[str, Any]:
        """Generate advanced wordlist recommendations based on analysis"""
        debug_print("Generating advanced wordlist recommendations")
        
        recommendations = {
            'priority_wordlists': [],
            'technology_specific': {},
            'attack_vector_focused': {},
            'custom_recommendations': [],
            'context_based': {}
        }
        
        # Priority scoring system
        priority_scores = {}
        
        # Technology-based recommendations
        for tech in tech_profile.get('detected_technologies', []):
            tech_name = tech['name'].lower()
            confidence = tech['confidence']
            
            # Map technology to wordlists
            if tech_name in self.wordlist_mappings:
                wordlists = self.wordlist_mappings[tech_name]
                for wordlist in wordlists:
                    score = confidence * 100  # Base score from confidence
                    priority_scores[wordlist] = priority_scores.get(wordlist, 0) + score
                    
                    if tech_name not in recommendations['technology_specific']:
                        recommendations['technology_specific'][tech_name] = []
                    recommendations['technology_specific'][tech_name].append({
                        'wordlist': wordlist,
                        'confidence': confidence,
                        'reason': f'Detected {tech_name} with {confidence:.1%} confidence'
                    })
        
        # Attack vector-based recommendations
        threat_vectors = security_assessment.get('threat_vectors', [])
        for vector in threat_vectors:
            vector_type = vector['vector'].lower()
            likelihood = vector['likelihood']
            wordlists = vector.get('wordlists', [])
            
            likelihood_multiplier = {'high': 1.5, 'medium': 1.0, 'low': 0.7}.get(likelihood, 1.0)
            
            for wordlist in wordlists:
                score = 50 * likelihood_multiplier  # Base score for attack vectors
                priority_scores[wordlist] = priority_scores.get(wordlist, 0) + score
                
                if vector_type not in recommendations['attack_vector_focused']:
                    recommendations['attack_vector_focused'][vector_type] = []
                recommendations['attack_vector_focused'][vector_type].append({
                    'wordlist': wordlist,
                    'likelihood': likelihood,
                    'reason': f'Addresses {vector["description"]}'
                })
        
        # Context-based recommendations from discovered URLs
        for category, urls in categorized_results.items():
            if not urls:
                continue
                
            category_lower = category.lower()
            url_count = len(urls)
            
            # Boost score based on number of URLs in category
            category_multiplier = min(2.0, 1.0 + (url_count / 10.0))
            
            if category_lower == 'admin':
                wordlists = ['admin-panels.txt', 'management-interfaces.txt', 'admin-passwords.txt']
                base_score = 60
            elif category_lower == 'api':
                wordlists = ['api-endpoints.txt', 'rest-api.txt', 'graphql-endpoints.txt']
                base_score = 50
            elif category_lower == 'config':
                wordlists = ['config-files.txt', 'sensitive-files.txt', 'backup-files.txt']
                base_score = 70
            elif category_lower == 'auth':
                wordlists = ['auth-endpoints.txt', 'login-pages.txt']
                base_score = 40
            elif category_lower == 'docs':
                wordlists = ['documentation.txt', 'help-pages.txt']
                base_score = 20
            else:
                continue
            
            for wordlist in wordlists:
                score = base_score * category_multiplier
                priority_scores[wordlist] = priority_scores.get(wordlist, 0) + score
                
                if category_lower not in recommendations['context_based']:
                    recommendations['context_based'][category_lower] = []
                recommendations['context_based'][category_lower].append({
                    'wordlist': wordlist,
                    'url_count': url_count,
                    'reason': f'Found {url_count} URLs in {category} category'
                })
        
        # Generate custom recommendations based on patterns
        custom_recs = self._generate_custom_wordlist_recommendations(categorized_results)
        recommendations['custom_recommendations'] = custom_recs
        
        # Add scores for custom recommendations
        for rec in custom_recs:
            wordlist = rec['wordlist']
            score = rec.get('priority_score', 30)
            priority_scores[wordlist] = priority_scores.get(wordlist, 0) + score
        
        # Create prioritized list
        priority_list = []
        for wordlist, score in sorted(priority_scores.items(), key=lambda x: x[1], reverse=True):
            # Determine priority level
            if score >= 100:
                priority = 'CRITICAL'
            elif score >= 70:
                priority = 'HIGH'
            elif score >= 40:
                priority = 'MEDIUM'
            else:
                priority = 'LOW'
            
            priority_list.append({
                'wordlist': wordlist,
                'priority': priority,
                'score': score,
                'reasons': self._get_wordlist_reasons(wordlist, recommendations)
            })
        
        recommendations['priority_wordlists'] = priority_list[:10]  # Top 10
        
        debug_print(f"Generated {len(priority_list)} wordlist recommendations")
        return recommendations
    
    def _generate_custom_wordlist_recommendations(self, categorized_results: Dict[str, List[CrawledURL]]) -> List[Dict[str, Any]]:
        """Generate custom wordlist recommendations based on discovered patterns"""
        custom_recs = []
        
        # Analyze URL patterns for custom wordlist hints
        all_urls = []
        for urls in categorized_results.values():
            all_urls.extend(urls)
        
        # Extract common path patterns
        path_segments = []
        file_extensions = Counter()
        directory_names = Counter()
        
        for url in all_urls:
            try:
                parsed = urlparse(url.url)
                path_parts = [p for p in parsed.path.split('/') if p]
                path_segments.extend(path_parts)
                
                # Count file extensions
                if path_parts and '.' in path_parts[-1]:
                    ext = path_parts[-1].split('.')[-1].lower()
                    if len(ext) <= 4 and ext.isalnum():
                        file_extensions[ext] += 1
                
                # Count directory names
                for part in path_parts[:-1]:  # Exclude filename
                    if len(part) > 2:
                        directory_names[part.lower()] += 1
                        
            except Exception:
                continue
        
        # Recommend based on common patterns
        common_extensions = file_extensions.most_common(3)
        for ext, count in common_extensions:
            if count >= 2:  # At least 2 occurrences
                custom_recs.append({
                    'wordlist': f'{ext}-files.txt',
                    'type': 'file_extension',
                    'pattern': f'*.{ext}',
                    'occurrences': count,
                    'priority_score': min(50, count * 10),
                    'reason': f'Found {count} .{ext} files - may indicate additional {ext} resources'
                })
        
        # Recommend based on common directories
        common_dirs = directory_names.most_common(5)
        for dirname, count in common_dirs:
            if count >= 2 and len(dirname) > 2:
                custom_recs.append({
                    'wordlist': f'{dirname}-paths.txt',
                    'type': 'directory_pattern',
                    'pattern': f'/*{dirname}*',
                    'occurrences': count,
                    'priority_score': min(40, count * 8),
                    'reason': f'Common directory pattern "{dirname}" found {count} times'
                })
        
        return custom_recs
    
    def _get_wordlist_reasons(self, wordlist: str, recommendations: Dict[str, Any]) -> List[str]:
        """Get all reasons why a wordlist was recommended"""
        reasons = []
        
        # Check technology-specific reasons
        for tech, tech_recs in recommendations.get('technology_specific', {}).items():
            for rec in tech_recs:
                if rec['wordlist'] == wordlist:
                    reasons.append(rec['reason'])
        
        # Check attack vector reasons
        for vector, vector_recs in recommendations.get('attack_vector_focused', {}).items():
            for rec in vector_recs:
                if rec['wordlist'] == wordlist:
                    reasons.append(rec['reason'])
        
        # Check context-based reasons
        for context, context_recs in recommendations.get('context_based', {}).items():
            for rec in context_recs:
                if rec['wordlist'] == wordlist:
                    reasons.append(rec['reason'])
        
        # Check custom reasons
        for rec in recommendations.get('custom_recommendations', []):
            if rec['wordlist'] == wordlist:
                reasons.append(rec['reason'])
        
        return reasons
    
    async def _discover_deep_patterns(self, urls: List[CrawledURL]) -> List[Dict[str, Any]]:
        """Discover deep patterns in URL structure and naming"""
        debug_print("Discovering deep patterns in URL structure")
        
        patterns = []
        
        if not urls:
            return patterns
        
        # Extract URL components for analysis
        url_data = []
        for url in urls:
            try:
                parsed = urlparse(url.url)
                url_data.append({
                    'url': url.url,
                    'domain': parsed.netloc,
                    'path': parsed.path,
                    'path_parts': [p for p in parsed.path.split('/') if p],
                    'query': parsed.query,
                    'status_code': getattr(url, 'status_code', None)
                })
            except Exception:
                continue
        
        # Pattern 1: Common directory structures
        directory_patterns = self._analyze_directory_patterns(url_data)
        patterns.extend(directory_patterns)
        
        # Pattern 2: Naming conventions
        naming_patterns = self._analyze_naming_conventions(url_data)
        patterns.extend(naming_patterns)
        
        # Pattern 3: Response code patterns
        response_patterns = self._analyze_response_patterns(url_data)
        patterns.extend(response_patterns)
        
        # Pattern 4: Parameter patterns
        parameter_patterns = self._analyze_parameter_patterns(url_data)
        patterns.extend(parameter_patterns)
        
        debug_print(f"Discovered {len(patterns)} deep patterns")
        return patterns
    
    def _analyze_directory_patterns(self, url_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze directory structure patterns"""
        patterns = []
        
        # Group URLs by directory depth
        depth_groups = defaultdict(list)
        for data in url_data:
            depth = len(data['path_parts'])
            depth_groups[depth].append(data)
        
        # Find common directory structures
        for depth, urls in depth_groups.items():
            if len(urls) < 2 or depth == 0:
                continue
            
            # Find common path prefixes
            path_prefixes = Counter()
            for url_info in urls:
                for i in range(1, len(url_info['path_parts']) + 1):
                    prefix = '/'.join(url_info['path_parts'][:i])
                    path_prefixes[prefix] += 1
            
            # Report significant patterns
            for prefix, count in path_prefixes.most_common(3):
                if count >= 2 and len(prefix) > 2:
                    patterns.append({
                        'type': 'directory_structure',
                        'pattern': f'/{prefix}/*',
                        'occurrences': count,
                        'depth': depth,
                        'confidence': min(0.95, count / len(urls)),
                        'recommendation': f'Consider fuzzing additional paths under /{prefix}/',
                        'wordlist_hint': f'{prefix.replace("/", "-")}-paths.txt'
                    })
        
        return patterns
    
    def _analyze_naming_conventions(self, url_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze URL naming conventions"""
        patterns = []
        
        # Extract all path components
        all_components = []
        for data in url_data:
            all_components.extend(data['path_parts'])
        
        if not all_components:
            return patterns
        
        # Analyze naming patterns
        naming_styles = {
            'underscore': 0,
            'hyphen': 0,
            'camelcase': 0,
            'lowercase': 0,
            'numbers': 0
        }
        
        for component in all_components:
            if '_' in component:
                naming_styles['underscore'] += 1
            if '-' in component:
                naming_styles['hyphen'] += 1
            if any(c.isupper() for c in component) and any(c.islower() for c in component):
                naming_styles['camelcase'] += 1
            if component.islower():
                naming_styles['lowercase'] += 1
            if any(c.isdigit() for c in component):
                naming_styles['numbers'] += 1
        
        total_components = len(all_components)
        
        # Report significant naming patterns
        for style, count in naming_styles.items():
            if count >= 2:
                prevalence = count / total_components
                if prevalence >= 0.2:  # At least 20% prevalence
                    patterns.append({
                        'type': 'naming_convention',
                        'pattern': style,
                        'prevalence': prevalence,
                        'occurrences': count,
                        'confidence': min(0.9, prevalence),
                        'recommendation': f'Use {style} naming convention in wordlists',
                        'wordlist_hint': f'Generate custom wordlist with {style} patterns'
                    })
        
        return patterns
    
    def _analyze_response_patterns(self, url_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze HTTP response code patterns"""
        patterns = []
        
        # Group URLs by response code
        response_groups = defaultdict(list)
        for data in url_data:
            if data['status_code']:
                response_groups[data['status_code']].append(data)
        
        total_urls = len([d for d in url_data if d['status_code']])
        
        for status_code, urls in response_groups.items():
            count = len(urls)
            if count < 2:
                continue
            
            prevalence = count / total_urls if total_urls > 0 else 0
            
            # Analyze what makes these URLs return the same status
            if status_code == 403:  # Forbidden
                patterns.append({
                    'type': 'access_control',
                    'pattern': f'HTTP {status_code}',
                    'occurrences': count,
                    'prevalence': prevalence,
                    'confidence': 0.8,
                    'recommendation': 'These paths may be protected - investigate access controls',
                    'security_implication': 'Potential sensitive areas requiring authentication'
                })
            
            elif status_code == 404:  # Not Found
                if prevalence > 0.5:  # Majority are 404s
                    patterns.append({
                        'type': 'enumeration_opportunity',
                        'pattern': f'HTTP {status_code}',
                        'occurrences': count,
                        'prevalence': prevalence,
                        'confidence': 0.6,
                        'recommendation': 'High 404 rate - expand wordlist coverage',
                        'wordlist_hint': 'Use more comprehensive wordlists'
                    })
            
            elif status_code == 200:  # Success
                patterns.append({
                    'type': 'accessible_content',
                    'pattern': f'HTTP {status_code}',
                    'occurrences': count,
                    'prevalence': prevalence,
                    'confidence': 0.9,
                    'recommendation': 'These paths are accessible - analyze content for further enumeration',
                    'security_implication': 'Confirmed accessible endpoints for deeper analysis'
                })
        
        return patterns
    
    def _analyze_parameter_patterns(self, url_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze URL parameter patterns"""
        patterns = []
        
        # Extract all parameters
        all_params = []
        for data in url_data:
            if data['query']:
                try:
                    from urllib.parse import parse_qs
                    params = parse_qs(data['query'])
                    all_params.extend(params.keys())
                except Exception:
                    continue
        
        if not all_params:
            return patterns
        
        # Analyze parameter usage
        param_counts = Counter(all_params)
        total_params = len(all_params)
        
        for param, count in param_counts.most_common(5):
            if count >= 2:
                prevalence = count / total_params
                
                # Classify parameter types
                param_lower = param.lower()
                if any(keyword in param_lower for keyword in ['id', 'user', 'admin']):
                    risk_level = 'high'
                    implication = 'Potential injection or privilege escalation vector'
                elif any(keyword in param_lower for keyword in ['file', 'path', 'url']):
                    risk_level = 'medium'
                    implication = 'Potential file inclusion or traversal vector'
                else:
                    risk_level = 'low'
                    implication = 'Standard parameter - analyze for application logic'
                
                patterns.append({
                    'type': 'parameter_usage',
                    'pattern': f'parameter:{param}',
                    'occurrences': count,
                    'prevalence': prevalence,
                    'risk_level': risk_level,
                    'confidence': min(0.8, prevalence + 0.2),
                    'recommendation': f'Test parameter "{param}" for vulnerabilities',
                    'security_implication': implication,
                    'wordlist_hint': f'Include {param} variants in parameter fuzzing'
                })
        
        return patterns