"""Advanced HTTP Scanner with httpx, DNS enumeration, and vulnerability discovery"""
import asyncio
import socket
import ssl
import subprocess
import re
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urlparse, urljoin
import base64
import hashlib
from datetime import datetime

try:
    import httpx
    import dns.resolver
    import dns.zone
    import dns.query
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

from workflows.core.base import BaseWorkflow, WorkflowResult
from .models import HTTPScanResult, HTTPService, HTTPVulnerability, DNSRecord


class HTTPAdvancedScanner(BaseWorkflow):
    """Advanced HTTP scanner with multiple discovery techniques"""
    
    def __init__(self):
        super().__init__(name="http_03")
        self.common_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
        self.timeout = 10
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ]
        
    async def execute(self, target: str, ports: Optional[List[int]] = None, **kwargs) -> WorkflowResult:
        """Execute advanced HTTP scanning workflow"""
        start_time = datetime.now()
        
        if not DEPS_AVAILABLE:
            return await self._execute_fallback(target, ports, **kwargs)
        
        try:
            results = HTTPScanResult(target=target)
            
            # DNS enumeration first
            dns_info = await self._dns_enumeration(target)
            results.dns_records = dns_info['records']
            results.subdomains = dns_info['subdomains']
            
            # Determine ports to scan
            scan_ports = ports if ports else self.common_ports
            
            # HTTP service discovery
            for port in scan_ports:
                service = await self._scan_http_service(target, port)
                if service:
                    results.services.append(service)
            
            # Advanced discovery techniques
            for service in results.services:
                # Path discovery without wordlists
                discovered_paths = await self._discover_paths(service)
                service.discovered_paths.extend(discovered_paths)
                
                # Header analysis
                vulnerabilities = self._analyze_headers(service)
                results.vulnerabilities.extend(vulnerabilities)
                
                # Technology detection
                service.technologies = await self._detect_technologies(service)
                
                # SSL/TLS analysis for HTTPS
                if service.is_https:
                    ssl_vulns = await self._analyze_ssl(service)
                    results.vulnerabilities.extend(ssl_vulns)
            
            # Cross-service analysis
            cross_vulns = self._cross_service_analysis(results)
            results.vulnerabilities.extend(cross_vulns)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return WorkflowResult(
                success=True,
                data=results.to_dict(),
                execution_time=execution_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def _execute_fallback(self, target: str, ports: Optional[List[int]] = None, **kwargs) -> WorkflowResult:
        """Fallback implementation using curl and system tools"""
        start_time = datetime.now()
        
        try:
            results = {
                "target": target,
                "services": [],
                "vulnerabilities": [],
                "dns_records": [],
                "subdomains": []
            }
            
            # Basic DNS lookup
            try:
                dns_result = subprocess.run(
                    ["nslookup", target],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if dns_result.returncode == 0:
                    ips = re.findall(r'Address: ([\d.]+)', dns_result.stdout)
                    for ip in ips:
                        results["dns_records"].append({
                            "type": "A",
                            "value": ip
                        })
            except:
                pass
            
            # Scan ports with curl
            scan_ports = ports if ports else self.common_ports
            
            for port in scan_ports:
                for scheme in ['http', 'https']:
                    url = f"{scheme}://{target}:{port}"
                    
                    curl_cmd = [
                        "curl", "-I", "-s", "-m", "5",
                        "-H", f"User-Agent: {self.user_agents[0]}",
                        url
                    ]
                    
                    try:
                        result = subprocess.run(
                            curl_cmd,
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if result.returncode == 0 and result.stdout:
                            service = {
                                "port": port,
                                "scheme": scheme,
                                "url": url,
                                "headers": {},
                                "status_code": None,
                                "server": None,
                                "technologies": []
                            }
                            
                            # Parse headers
                            lines = result.stdout.strip().split('\n')
                            if lines:
                                status_match = re.match(r'HTTP/[\d.]+ (\d+)', lines[0])
                                if status_match:
                                    service["status_code"] = int(status_match.group(1))
                            
                            for line in lines[1:]:
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    service["headers"][key.strip()] = value.strip()
                                    
                                    if key.lower() == 'server':
                                        service["server"] = value.strip()
                            
                            results["services"].append(service)
                            
                            # Basic vulnerability checks
                            vulns = self._check_basic_vulnerabilities(service)
                            results["vulnerabilities"].extend(vulns)
                            
                    except:
                        continue
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return WorkflowResult(
                success=True,
                data=results,
                execution_time=execution_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def _dns_enumeration(self, target: str) -> Dict[str, Any]:
        """Perform DNS enumeration without wordlists"""
        dns_info = {
            'records': [],
            'subdomains': []
        }
        
        try:
            resolver = dns.resolver.Resolver()
            
            # Query multiple record types
            record_types = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA']
            
            for record_type in record_types:
                try:
                    answers = resolver.resolve(target, record_type)
                    for rdata in answers:
                        dns_info['records'].append(DNSRecord(
                            type=record_type,
                            value=str(rdata)
                        ))
                except:
                    continue
            
            # Try zone transfer
            try:
                ns_records = resolver.resolve(target, 'NS')
                for ns in ns_records:
                    try:
                        zone = dns.zone.from_xfr(dns.query.xfr(str(ns), target))
                        for name, node in zone.nodes.items():
                            subdomain = str(name) + '.' + target
                            if subdomain not in dns_info['subdomains']:
                                dns_info['subdomains'].append(subdomain)
                    except:
                        continue
            except:
                pass
            
            # Common subdomain patterns (no wordlist)
            common_patterns = [
                'www', 'mail', 'ftp', 'admin', 'portal', 'api', 'dev',
                'staging', 'test', 'prod', 'vpn', 'remote', 'secure'
            ]
            
            tasks = []
            for pattern in common_patterns:
                subdomain = f"{pattern}.{target}"
                tasks.append(self._check_subdomain(subdomain))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for subdomain, exists in results:
                if isinstance(exists, bool) and exists:
                    dns_info['subdomains'].append(subdomain)
                    
        except Exception:
            pass
            
        return dns_info
    
    async def _check_subdomain(self, subdomain: str) -> Tuple[str, bool]:
        """Check if subdomain exists"""
        try:
            socket.gethostbyname(subdomain)
            return subdomain, True
        except:
            return subdomain, False
    
    async def _scan_http_service(self, target: str, port: int) -> Optional[HTTPService]:
        """Scan a single HTTP/HTTPS service"""
        for scheme in ['https', 'http']:
            url = f"{scheme}://{target}:{port}"
            
            try:
                async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                    response = await client.get(
                        url,
                        headers={"User-Agent": self.user_agents[0]},
                        follow_redirects=True
                    )
                    
                    service = HTTPService(
                        port=port,
                        scheme=scheme,
                        url=url,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        server=response.headers.get('server', 'Unknown'),
                        is_https=(scheme == 'https')
                    )
                    
                    # Get response body for analysis
                    service.response_body = response.text[:10000]  # First 10KB
                    
                    return service
                    
            except:
                continue
                
        return None
    
    async def _discover_paths(self, service: HTTPService) -> List[str]:
        """Discover paths without wordlists using various techniques"""
        discovered = []
        
        # 1. Parse HTML for links
        if service.response_body:
            # Find all href and src attributes
            links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', service.response_body)
            for link in links:
                parsed = urlparse(link)
                if parsed.path and parsed.path != '/':
                    discovered.append(parsed.path)
        
        # 2. Common application patterns
        common_paths = [
            '/robots.txt', '/sitemap.xml', '/.well-known/security.txt',
            '/api/', '/api/v1/', '/api/v2/', '/graphql',
            '/.git/config', '/.env', '/config.php', '/wp-config.php',
            '/admin/', '/login', '/dashboard', '/console',
            '/swagger-ui/', '/api-docs/', '/docs/',
            '/.DS_Store', '/thumbs.db', '/web.config'
        ]
        
        # 3. Technology-specific paths
        if 'apache' in service.server.lower():
            common_paths.extend(['/server-status', '/server-info'])
        if 'nginx' in service.server.lower():
            common_paths.extend(['/nginx_status'])
        
        # Test paths
        async with httpx.AsyncClient(verify=False, timeout=5) as client:
            tasks = []
            for path in set(common_paths):
                url = urljoin(service.url, path)
                tasks.append(self._check_path(client, url))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for path, exists in results:
                if isinstance(exists, bool) and exists:
                    discovered.append(path)
        
        return list(set(discovered))
    
    async def _check_path(self, client: httpx.AsyncClient, url: str) -> Tuple[str, bool]:
        """Check if a path exists"""
        try:
            response = await client.head(url, headers={"User-Agent": self.user_agents[0]})
            path = urlparse(url).path
            return path, response.status_code not in [404, 403]
        except:
            return urlparse(url).path, False
    
    def _analyze_headers(self, service: HTTPService) -> List[HTTPVulnerability]:
        """Analyze HTTP headers for security issues"""
        vulnerabilities = []
        
        # Missing security headers
        security_headers = {
            'x-frame-options': 'Clickjacking protection',
            'x-content-type-options': 'MIME type sniffing protection',
            'x-xss-protection': 'XSS protection',
            'strict-transport-security': 'HSTS',
            'content-security-policy': 'Content Security Policy',
            'referrer-policy': 'Referrer Policy',
            'permissions-policy': 'Permissions Policy'
        }
        
        for header, description in security_headers.items():
            if header not in [h.lower() for h in service.headers.keys()]:
                vulnerabilities.append(HTTPVulnerability(
                    type=f"missing-{header}",
                    severity="medium",
                    description=f"Missing {description} header",
                    url=service.url,
                    evidence=f"Header '{header}' not found in response"
                ))
        
        # Information disclosure
        info_headers = ['server', 'x-powered-by', 'x-aspnet-version']
        for header in info_headers:
            value = service.headers.get(header, '')
            if value:
                vulnerabilities.append(HTTPVulnerability(
                    type="information-disclosure",
                    severity="low",
                    description=f"Server information disclosure via {header} header",
                    url=service.url,
                    evidence=f"{header}: {value}"
                ))
        
        # Weak configurations
        if 'access-control-allow-origin' in [h.lower() for h in service.headers.keys()]:
            value = next((v for k, v in service.headers.items() if k.lower() == 'access-control-allow-origin'), '')
            if value == '*':
                vulnerabilities.append(HTTPVulnerability(
                    type="cors-misconfiguration",
                    severity="high",
                    description="CORS misconfiguration allows any origin",
                    url=service.url,
                    evidence="Access-Control-Allow-Origin: *"
                ))
        
        return vulnerabilities
    
    async def _detect_technologies(self, service: HTTPService) -> List[str]:
        """Detect technologies from headers and response"""
        technologies = []
        
        # From headers
        tech_headers = {
            'x-powered-by': lambda v: v,
            'server': lambda v: v.split('/')[0] if '/' in v else v,
            'x-generator': lambda v: v
        }
        
        for header, parser in tech_headers.items():
            value = service.headers.get(header, '')
            if value:
                tech = parser(value)
                if tech:
                    technologies.append(tech)
        
        # From response body patterns
        if service.response_body:
            patterns = {
                'WordPress': r'wp-content|wp-includes',
                'Drupal': r'Drupal|drupal',
                'Joomla': r'Joomla|joomla',
                'Django': r'csrfmiddlewaretoken',
                'Ruby on Rails': r'Rails|rails',
                'ASP.NET': r'__VIEWSTATE|aspnet',
                'PHP': r'\.php["\s]',
                'Node.js': r'node\.js|express',
                'React': r'react|React',
                'Angular': r'ng-version|angular',
                'Vue.js': r'vue|Vue'
            }
            
            for tech, pattern in patterns.items():
                if re.search(pattern, service.response_body, re.IGNORECASE):
                    technologies.append(tech)
        
        return list(set(technologies))
    
    async def _analyze_ssl(self, service: HTTPService) -> List[HTTPVulnerability]:
        """Analyze SSL/TLS configuration"""
        vulnerabilities = []
        
        try:
            # Extract hostname and port
            parsed = urlparse(service.url)
            hostname = parsed.hostname
            port = parsed.port or 443
            
            # Get SSL certificate
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    
                    # Check SSL version
                    if version in ['TLSv1', 'TLSv1.1', 'SSLv2', 'SSLv3']:
                        vulnerabilities.append(HTTPVulnerability(
                            type="weak-ssl-version",
                            severity="high",
                            description=f"Weak SSL/TLS version: {version}",
                            url=service.url,
                            evidence=f"Server supports {version}"
                        ))
                    
                    # Check cipher strength
                    if cipher and len(cipher) > 1:
                        cipher_name = cipher[0]
                        if any(weak in cipher_name.lower() for weak in ['rc4', 'des', 'null', 'anon', 'export']):
                            vulnerabilities.append(HTTPVulnerability(
                                type="weak-cipher",
                                severity="medium",
                                description=f"Weak cipher suite: {cipher_name}",
                                url=service.url,
                                evidence=f"Cipher: {cipher_name}"
                            ))
                    
        except Exception:
            pass
            
        return vulnerabilities
    
    def _cross_service_analysis(self, results: HTTPScanResult) -> List[HTTPVulnerability]:
        """Analyze across multiple services for additional vulnerabilities"""
        vulnerabilities = []
        
        # Check for mixed HTTP/HTTPS
        http_services = [s for s in results.services if not s.is_https]
        https_services = [s for s in results.services if s.is_https]
        
        if http_services and https_services:
            for http_service in http_services:
                vulnerabilities.append(HTTPVulnerability(
                    type="mixed-content-risk",
                    severity="medium",
                    description="HTTP service available alongside HTTPS",
                    url=http_service.url,
                    evidence=f"Both HTTP ({http_service.port}) and HTTPS services detected"
                ))
        
        # Check for consistent security headers
        if len(results.services) > 1:
            header_consistency = {}
            for service in results.services:
                for header in ['x-frame-options', 'strict-transport-security']:
                    key = header.lower()
                    if key in [h.lower() for h in service.headers.keys()]:
                        if key not in header_consistency:
                            header_consistency[key] = []
                        header_consistency[key].append(service.url)
            
            for header, urls in header_consistency.items():
                if len(urls) < len(results.services):
                    missing_urls = [s.url for s in results.services if s.url not in urls]
                    for url in missing_urls:
                        vulnerabilities.append(HTTPVulnerability(
                            type="inconsistent-security-headers",
                            severity="low",
                            description=f"Inconsistent {header} header across services",
                            url=url,
                            evidence=f"Header present on {len(urls)} services but missing here"
                        ))
        
        return vulnerabilities
    
    def _check_basic_vulnerabilities(self, service: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Basic vulnerability checks for fallback mode"""
        vulnerabilities = []
        
        # Check for missing security headers
        headers_lower = {k.lower(): v for k, v in service.get('headers', {}).items()}
        
        security_headers = [
            'x-frame-options', 'x-content-type-options', 
            'strict-transport-security', 'content-security-policy'
        ]
        
        for header in security_headers:
            if header not in headers_lower:
                vulnerabilities.append({
                    "type": f"missing-{header}",
                    "severity": "medium",
                    "description": f"Missing {header} security header",
                    "url": service['url']
                })
        
        # Information disclosure
        if 'server' in headers_lower:
            vulnerabilities.append({
                "type": "information-disclosure",
                "severity": "low",
                "description": "Server header exposes version information",
                "url": service['url'],
                "evidence": f"Server: {headers_lower['server']}"
            })
        
        return vulnerabilities
    
    def validate_input(self, target: str, **kwargs) -> Tuple[bool, List[str]]:
        """Validate input parameters"""
        errors = []
        
        if not target:
            errors.append("Target is required")
        
        # Basic target validation
        if target and not re.match(r'^[a-zA-Z0-9.-]+$', target):
            errors.append("Invalid target format")
        
        return len(errors) == 0, errors