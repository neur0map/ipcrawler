"""
Security analysis for HTTP scanner workflow.

This module handles HTTP header security analysis, SSL/TLS vulnerability detection,
CORS misconfiguration detection, and cross-service vulnerability analysis.
"""

import ssl
import socket
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from .models import HTTPService, HTTPVulnerability, HTTPScanResult
from .config import get_scanner_config
from utils.debug import debug_print


class SecurityAnalyzer:
    """Security analysis handler for HTTP services"""
    
    def __init__(self):
        self.config = get_scanner_config()
    
    async def analyze_service_security(self, service: HTTPService) -> List[HTTPVulnerability]:
        """
        Perform comprehensive security analysis on a single service.
        
        Args:
            service: HTTPService object to analyze
            
        Returns:
            List of discovered vulnerabilities
        """
        vulnerabilities = []
        
        # HTTP header analysis
        header_vulns = self._analyze_headers(service)
        vulnerabilities.extend(header_vulns)
        
        # SSL/TLS analysis for HTTPS services
        if service.is_https:
            ssl_vulns = await self._analyze_ssl(service)
            vulnerabilities.extend(ssl_vulns)
        
        # Content-based security analysis
        content_vulns = self._analyze_response_content(service)
        vulnerabilities.extend(content_vulns)
        
        return vulnerabilities
    
    def _analyze_headers(self, service: HTTPService) -> List[HTTPVulnerability]:
        """
        Analyze HTTP headers for security issues.
        
        Args:
            service: HTTPService object
            
        Returns:
            List of header-related vulnerabilities
        """
        vulnerabilities = []
        
        # Missing security headers from database
        security_headers = {}
        if self.config.scanner_config_manager:
            try:
                security_headers = self.config.scanner_config_manager.get_security_headers()
            except Exception as e:
                debug_print(f"Error getting security headers from database: {e}", level="WARNING")
        
        # Fallback if database unavailable
        if not security_headers:
            security_headers = {
                'x-frame-options': 'Clickjacking protection',
                'x-content-type-options': 'MIME type sniffing protection',
                'x-xss-protection': 'XSS protection',
                'strict-transport-security': 'HSTS',
                'content-security-policy': 'Content Security Policy',
                'referrer-policy': 'Referrer Policy',
                'permissions-policy': 'Permissions Policy'
            }
        
        # Check for missing security headers
        for header, description in security_headers.items():
            if header not in [h.lower() for h in service.headers.keys()]:
                vulnerabilities.append(HTTPVulnerability(
                    type=f"missing-{header}",
                    severity="medium",
                    description=f"Missing {description} header",
                    url=service.url,
                    evidence=f"Header '{header}' not found in response"
                ))
        
        # Information disclosure headers from database
        info_headers = []
        if self.config.scanner_config_manager:
            try:
                info_headers = self.config.scanner_config_manager.get_information_disclosure_headers()
            except Exception as e:
                debug_print(f"Error getting info disclosure headers from database: {e}", level="WARNING")
        
        # Fallback if database unavailable
        if not info_headers:
            info_headers = ['server', 'x-powered-by', 'x-aspnet-version', 'x-generator']
        
        # Check for information disclosure
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
        
        # CORS misconfiguration check
        cors_header = next((v for k, v in service.headers.items() if k.lower() == 'access-control-allow-origin'), '')
        if cors_header == '*':
            vulnerabilities.append(HTTPVulnerability(
                type="cors-misconfiguration",
                severity="high",
                description="CORS misconfiguration allows any origin",
                url=service.url,
                evidence="Access-Control-Allow-Origin: *"
            ))
        
        # Check for weak HSTS configuration
        hsts_header = next((v for k, v in service.headers.items() if k.lower() == 'strict-transport-security'), '')
        if hsts_header and service.is_https:
            if 'max-age' not in hsts_header.lower():
                vulnerabilities.append(HTTPVulnerability(
                    type="weak-hsts",
                    severity="medium", 
                    description="HSTS header missing max-age directive",
                    url=service.url,
                    evidence=f"Strict-Transport-Security: {hsts_header}"
                ))
            elif 'includesubdomains' not in hsts_header.lower():
                vulnerabilities.append(HTTPVulnerability(
                    type="incomplete-hsts",
                    severity="low",
                    description="HSTS header missing includeSubDomains directive",
                    url=service.url,
                    evidence=f"Strict-Transport-Security: {hsts_header}"
                ))
        
        return vulnerabilities
    
    async def _analyze_ssl(self, service: HTTPService) -> List[HTTPVulnerability]:
        """
        Analyze SSL/TLS configuration for vulnerabilities.
        
        Args:
            service: HTTPService object (must be HTTPS)
            
        Returns:
            List of SSL/TLS vulnerabilities
        """
        vulnerabilities = []
        
        if not service.is_https:
            return vulnerabilities
        
        try:
            # Extract hostname and port
            parsed = urlparse(service.url)
            hostname = parsed.hostname
            port = parsed.port or 443
            
            if not hostname:
                return vulnerabilities
            
            # Get SSL certificate
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    
                    # Check SSL/TLS version
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
                    
                    # Certificate analysis
                    if cert:
                        cert_vulns = self._analyze_certificate(cert, service.url)
                        vulnerabilities.extend(cert_vulns)
                    
        except Exception as e:
            debug_print(f"SSL analysis error for {service.url}: {e}", level="WARNING")
        
        return vulnerabilities
    
    def _analyze_certificate(self, cert: Dict[str, Any], service_url: str) -> List[HTTPVulnerability]:
        """
        Analyze SSL certificate for security issues.
        
        Args:
            cert: Certificate information from SSL socket
            service_url: Service URL
            
        Returns:
            List of certificate-related vulnerabilities
        """
        vulnerabilities = []
        
        try:
            import datetime
            
            # Check certificate expiration
            if 'notAfter' in cert:
                not_after = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                days_until_expiry = (not_after - datetime.datetime.now()).days
                
                if days_until_expiry < 0:
                    vulnerabilities.append(HTTPVulnerability(
                        type="expired-certificate",
                        severity="high",
                        description="SSL certificate has expired",
                        url=service_url,
                        evidence=f"Certificate expired on {cert['notAfter']}"
                    ))
                elif days_until_expiry < 30:
                    vulnerabilities.append(HTTPVulnerability(
                        type="expiring-certificate",
                        severity="medium",
                        description=f"SSL certificate expires in {days_until_expiry} days",
                        url=service_url,
                        evidence=f"Certificate expires on {cert['notAfter']}"
                    ))
            
            # Check for self-signed certificates
            if 'issuer' in cert and 'subject' in cert:
                issuer_cn = None
                subject_cn = None
                
                for component in cert.get('issuer', []):
                    if component[0][0] == 'commonName':
                        issuer_cn = component[0][1]
                        break
                
                for component in cert.get('subject', []):
                    if component[0][0] == 'commonName':
                        subject_cn = component[0][1]
                        break
                
                if issuer_cn and subject_cn and issuer_cn == subject_cn:
                    vulnerabilities.append(HTTPVulnerability(
                        type="self-signed-certificate",
                        severity="medium",
                        description="Self-signed SSL certificate detected",
                        url=service_url,
                        evidence=f"Issuer and subject are identical: {issuer_cn}"
                    ))
        
        except Exception as e:
            debug_print(f"Certificate analysis error: {e}", level="WARNING")
        
        return vulnerabilities
    
    def _analyze_response_content(self, service: HTTPService) -> List[HTTPVulnerability]:
        """
        Analyze response content for security issues.
        
        Args:
            service: HTTPService object
            
        Returns:
            List of content-related vulnerabilities
        """
        vulnerabilities = []
        
        if not service.response_body:
            return vulnerabilities
        
        content_lower = service.response_body.lower()
        
        # Check for sensitive information exposure
        sensitive_patterns = self._get_sensitive_patterns()
        
        for pattern_name, pattern in sensitive_patterns.items():
            if re.search(pattern, service.response_body, re.IGNORECASE):
                vulnerabilities.append(HTTPVulnerability(
                    type="sensitive-information-exposure",
                    severity="medium",
                    description=f"Potential {pattern_name} exposure in response",
                    url=service.url,
                    evidence=f"Pattern '{pattern_name}' detected in response"
                ))
        
        # Check for debug information
        debug_indicators = [
            'debug=true', 'debug mode', 'stack trace', 'traceback',
            'exception occurred', 'error occurred', 'mysql_connect',
            'fatal error', 'warning:', 'notice:', 'php error'
        ]
        
        for indicator in debug_indicators:
            if indicator in content_lower:
                vulnerabilities.append(HTTPVulnerability(
                    type="debug-information-disclosure",
                    severity="low",
                    description="Debug information disclosed in response",
                    url=service.url,
                    evidence=f"Debug indicator: {indicator}"
                ))
                break  # Only report once per service
        
        # Check for default installation pages
        default_pages = [
            'apache http server test page',
            'nginx welcome page',
            'iis windows server',
            'welcome to nginx',
            'it works!',
            'apache2 ubuntu default page',
            'test page for the apache',
            'welcome to caddy'
        ]
        
        for page_indicator in default_pages:
            if page_indicator in content_lower:
                vulnerabilities.append(HTTPVulnerability(
                    type="default-installation-page",
                    severity="low",
                    description="Default web server installation page detected",
                    url=service.url,
                    evidence=f"Default page indicator: {page_indicator}"
                ))
                break
        
        return vulnerabilities
    
    def _get_sensitive_patterns(self) -> Dict[str, str]:
        """
        Get patterns for detecting sensitive information.
        
        Returns:
            Dictionary of pattern names and regex patterns
        """
        if self.config.scanner_config_manager:
            try:
                return self.config.scanner_config_manager.get_sensitive_data_patterns()
            except Exception as e:
                debug_print(f"Error getting sensitive patterns from database: {e}", level="WARNING")
        
        # Fallback patterns
        return {
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'api_key': r'(?i)(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{16,}',
            'access_token': r'(?i)(access[_-]?token|accesstoken)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{16,}',
            'private_key': r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
            'connection_string': r'(?i)(connection[_-]?string|connectionstring)["\']?\s*[:=]\s*["\'][^"\']+["\']',
            'password': r'(?i)password["\']?\s*[:=]\s*["\'][^"\']{3,}["\']'
        }
    
    def analyze_cross_service_vulnerabilities(self, results: HTTPScanResult) -> List[HTTPVulnerability]:
        """
        Analyze vulnerabilities across multiple services.
        
        Args:
            results: HTTPScanResult containing all discovered services
            
        Returns:
            List of cross-service vulnerabilities
        """
        vulnerabilities = []
        
        if len(results.services) < 2:
            return vulnerabilities
        
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
        header_consistency = {}
        critical_headers = ['x-frame-options', 'strict-transport-security', 'content-security-policy']
        
        for service in results.services:
            for header in critical_headers:
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
        
        # Check for port-based service exposure patterns
        service_ports = [s.port for s in results.services]
        
        # Check for administrative interfaces on non-standard ports
        admin_ports = [8080, 8443, 9000, 9090, 9200, 5601, 3000]  # Common admin/monitoring ports
        exposed_admin_ports = [port for port in service_ports if port in admin_ports]
        
        if exposed_admin_ports:
            for service in results.services:
                if service.port in exposed_admin_ports:
                    vulnerabilities.append(HTTPVulnerability(
                        type="administrative-interface-exposure",
                        severity="medium",
                        description=f"Administrative interface potentially exposed on port {service.port}",
                        url=service.url,
                        evidence=f"Common administrative port {service.port} is accessible"
                    ))
        
        return vulnerabilities
    
    def check_basic_vulnerabilities_fallback(self, service: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Basic vulnerability checks for fallback mode when full objects unavailable.
        
        Args:
            service: Service dictionary with basic information
            
        Returns:
            List of vulnerability dictionaries
        """
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
        
        # Check for CORS misconfiguration
        if 'access-control-allow-origin' in headers_lower:
            if headers_lower['access-control-allow-origin'] == '*':
                vulnerabilities.append({
                    "type": "cors-misconfiguration",
                    "severity": "high",
                    "description": "CORS misconfiguration allows any origin",
                    "url": service['url'],
                    "evidence": "Access-Control-Allow-Origin: *"
                })
        
        return vulnerabilities