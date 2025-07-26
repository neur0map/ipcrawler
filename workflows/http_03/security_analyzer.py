"""Security Analyzer Module for HTTP_03 Workflow

Handles HTTP security analysis including header analysis, SSL/TLS validation, and vulnerability detection.
"""

import ssl
import socket
import re
from typing import List
from urllib.parse import urlparse

from .models import HTTPService, HTTPVulnerability

# Utils
from src.core.utils.debugging import debug_print


class SecurityAnalyzer:
    """Handles HTTP security analysis and vulnerability detection"""
    
    def __init__(self):
        """Initialize security analyzer"""
        self.original_ip = None  # Set by parent scanner
    
    def analyze_headers(self, service: HTTPService) -> List[HTTPVulnerability]:
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
        
        # CORS misconfiguration
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
    
    async def analyze_ssl(self, service: HTTPService) -> List[HTTPVulnerability]:
        """Analyze SSL/TLS configuration"""
        vulnerabilities = []
        
        if not service.is_https:
            return vulnerabilities
        
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
    
    async def extract_ssl_hostnames(self, service: HTTPService) -> List[str]:
        """Extract hostnames from SSL certificate Subject Alternative Names"""
        hostnames = []
        
        if not service.is_https:
            return hostnames
        
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
                    
                    # Extract hostnames from Subject Alternative Names
                    if cert and 'subjectAltName' in cert:
                        for name_type, name_value in cert['subjectAltName']:
                            if name_type == 'DNS' and name_value != self.original_ip:
                                # Validate hostname before adding
                                if self._is_valid_ssl_hostname(name_value):
                                    hostnames.append(name_value)
                    
                    # Extract from Common Name as fallback
                    if cert and 'subject' in cert:
                        for field in cert['subject']:
                            for key, value in field:
                                if key == 'commonName' and value != self.original_ip:
                                    if self._is_valid_ssl_hostname(value):
                                        hostnames.append(value)
                        
        except Exception as e:
            debug_print(f"SSL hostname extraction error: {e}")
            
        return list(set(hostnames))  # Remove duplicates
    
    def _is_valid_ssl_hostname(self, hostname: str) -> bool:
        """Validate SSL certificate hostname"""
        if not hostname or len(hostname) > 255:
            return False
            
        # Skip wildcard certificates and invalid patterns
        if hostname.startswith('*') or hostname.startswith('.'):
            return False
            
        # Must contain a dot and not be just numbers
        if '.' not in hostname or hostname.replace('.', '').isdigit():
            return False
            
        # Basic hostname validation
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-\.]*[a-zA-Z0-9]$', hostname):
            return False
            
        return True
    
    def analyze_response_content(self, service: HTTPService) -> List[HTTPVulnerability]:
        """Analyze response content for security issues"""
        vulnerabilities = []
        
        if not service.response_body:
            return vulnerabilities
        
        content = service.response_body.lower()
        
        # Check for sensitive information exposure
        sensitive_patterns = {
            'debug-info': r'debug|stack trace|error:|exception:',
            'internal-path': r'c:\\|/var/|/etc/|/home/',
            'database-error': r'mysql|postgresql|oracle|sql error',
            'api-keys': r'api[_-]?key|secret[_-]?key|access[_-]?token',
            'version-disclosure': r'version\s*[:=]\s*[\d\.]+',
        }
        
        for vuln_type, pattern in sensitive_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                vulnerabilities.append(HTTPVulnerability(
                    type=vuln_type,
                    severity="medium",
                    description=f"Potential {vuln_type.replace('-', ' ')} in response",
                    url=service.url,
                    evidence="Sensitive information found in response body"
                ))
        
        # Check for directory listing
        if re.search(r'index of /|directory listing|parent directory', content):
            vulnerabilities.append(HTTPVulnerability(
                type="directory-listing",
                severity="medium",
                description="Directory listing enabled",
                url=service.url,
                evidence="Directory listing page detected"
            ))
        
        return vulnerabilities