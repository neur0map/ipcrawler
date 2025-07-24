"""
Utility functions for HTTP scanner workflow.

This module contains input validation, content parsing helpers,
hostname extraction, and other common utility functions.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse, urljoin
from utils.debug import debug_print


def validate_input(target: str, **kwargs) -> Tuple[bool, List[str]]:
    """
    Validate input parameters for HTTP scanning.
    
    Args:
        target: Target hostname or IP address
        **kwargs: Additional parameters
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    if not target:
        errors.append("Target is required")
    
    # Basic target validation
    if target and not re.match(r'^[a-zA-Z0-9.-]+$', target):
        errors.append("Invalid target format")
    
    return len(errors) == 0, errors


def build_hostname_list(target: str, discovered_hostnames: List[str], subdomains: List[str], 
                       scanner_config_manager=None) -> List[str]:
    """
    Build comprehensive list of hostnames to test.
    
    Args:
        target: Original target
        discovered_hostnames: Hostnames discovered from previous scans
        subdomains: DNS subdomains
        scanner_config_manager: Optional config manager for database patterns
        
    Returns:
        List of unique hostnames to test
    """
    hostnames = [target]  # Start with original target
    
    # Add discovered hostnames from nmap
    hostnames.extend(discovered_hostnames)
    
    # Add DNS subdomains
    hostnames.extend(subdomains)
    
    # Generate additional hostname patterns from database
    if '.' in target and not target.replace('.', '').isdigit():  # If it's a domain, not IP
        base_domain = target
        
        # Get subdomain patterns from database
        subdomain_patterns = []
        if scanner_config_manager:
            try:
                subdomain_patterns = scanner_config_manager.get_common_subdomains()
            except Exception:
                pass
        
        # Fallback if database unavailable
        if not subdomain_patterns:
            subdomain_patterns = [
                "www", "mail", "admin", "api", "portal", "secure", "app", "web",
                "dev", "staging", "test", "prod"
            ]
        
        additional_patterns = [f"{pattern}.{base_domain}" for pattern in subdomain_patterns]
        hostnames.extend(additional_patterns)
    
    # Remove duplicates and empty strings, preserve order
    seen = set()
    unique_hostnames = []
    for hostname in hostnames:
        if hostname and hostname not in seen:
            seen.add(hostname)
            unique_hostnames.append(hostname)
    
    return unique_hostnames


def extract_title(response_body: Optional[str]) -> str:
    """
    Extract title from HTML response.
    
    Args:
        response_body: HTML response content
        
    Returns:
        Extracted title or empty string
    """
    if not response_body:
        return ""
    
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', response_body, re.IGNORECASE)
    return title_match.group(1).strip() if title_match else ""


def extract_hostnames_from_response(service_url: str, headers: Dict[str, str], 
                                   response_body: Optional[str], original_ip: str) -> List[str]:
    """
    Extract additional hostnames from HTTP response.
    
    Args:
        service_url: Service URL
        headers: Response headers
        response_body: Response content
        original_ip: Original target IP
        
    Returns:
        List of discovered hostnames
    """
    hostnames = []
    
    # From redirects in Location header
    location = headers.get('location', '')
    if location:
        parsed = urlparse(location)
        if parsed.hostname:
            hostnames.append(parsed.hostname)
    
    # From HTML content - simplified patterns
    if response_body:
        # Find basic HTTP links
        http_links = re.findall(r'https?://([^/\s"\'<>]+)', response_body)
        for hostname in http_links:
            if '.' in hostname and not hostname.replace('.', '').isdigit():
                hostnames.append(hostname)
    
    # Remove duplicates and filter relevant hostnames
    unique_hostnames = list(set(hostnames))
    
    # Filter to only include hostnames that might be related to the target
    filtered = []
    target_parts = original_ip.split('.')
    
    for hostname in unique_hostnames:
        # Skip obviously unrelated domains
        if any(skip in hostname.lower() for skip in ['google', 'facebook', 'twitter', 'cdn', 'googleapis']):
            continue
        
        # Include if it shares domain components with target or is a subdomain
        if any(part in hostname for part in target_parts if len(part) > 2):
            filtered.append(hostname)
        elif '.' in original_ip and hostname.endswith(original_ip.split('.', 1)[1]):
            filtered.append(hostname)
    
    return filtered[:10]  # Limit to prevent excessive discoveries


def extract_paths_from_html(html_content: str, scanner_config_manager=None) -> List[str]:
    """
    Extract paths from HTML content.
    
    Args:
        html_content: HTML content to parse
        scanner_config_manager: Optional config manager for database patterns
        
    Returns:
        List of discovered paths
    """
    paths = []
    
    # Find basic href and src attributes
    links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', html_content)
    for link in links:
        parsed = urlparse(link)
        if parsed.path and parsed.path != '/':
            # Only include relative paths
            if not parsed.netloc:
                paths.append(parsed.path)
    
    # Look for common monitoring paths
    monitoring_patterns = [
        '/grafana', '/dashboard', '/monitoring', '/metrics', 
        '/prometheus', '/kibana', '/api/health', '/api/v1/query'
    ]
    
    for pattern in monitoring_patterns:
        if pattern in html_content.lower():
            if pattern not in paths:
                paths.append(pattern)
                debug_print(f"Found monitoring path in HTML: {pattern}")
    
    return paths


def is_unique_service(new_service, existing_services) -> bool:
    """
    Check if service is unique (different content/headers from existing ones).
    
    Args:
        new_service: HTTPService object to check
        existing_services: List of existing HTTPService objects
        
    Returns:
        True if service is unique, False otherwise
    """
    for existing in existing_services:
        if (existing.port == new_service.port and 
            existing.scheme == new_service.scheme):
            
            # Compare key indicators of uniqueness
            same_status = existing.status_code == new_service.status_code
            same_server = existing.server == new_service.server
            same_title = extract_title(existing.response_body) == extract_title(new_service.response_body)
            same_content_length = len(existing.response_body or '') == len(new_service.response_body or '')
            
            # If all key indicators are the same, consider it duplicate
            if same_status and same_server and same_title and same_content_length:
                return False
    
    return True


def get_scheme_order_for_port(port: int) -> List[str]:
    """
    Get the preferred scheme order for testing a specific port.
    
    Args:
        port: Port number
        
    Returns:
        List of schemes in preferred order ['https', 'http'] or ['http', 'https']
    """
    if port == 443 or port == 8443:
        return ['https', 'http']
    elif port == 80 or port == 8080 or port == 8000:
        return ['http', 'https']
    else:
        return ['http', 'https']  # Try HTTP first for unknown ports


def build_url(scheme: str, target: str, port: int) -> str:
    """
    Build URL with proper port handling.
    
    Args:
        scheme: http or https
        target: hostname or IP
        port: port number
        
    Returns:
        Formatted URL
    """
    # Don't include port for standard ports
    if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
        return f"{scheme}://{target}"
    else:
        return f"{scheme}://{target}:{port}"


def count_vuln_severities(vulnerabilities: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count vulnerabilities by severity for fallback mode.
    
    Args:
        vulnerabilities: List of vulnerability dictionaries
        
    Returns:
        Dictionary with severity counts
    """
    counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for vuln in vulnerabilities:
        severity = vuln.get('severity', 'low')
        if severity in counts:
            counts[severity] += 1
    return counts


def get_valid_status_codes(scanner_config_manager=None) -> List[int]:
    """
    Get valid HTTP status codes for path discovery.
    
    Args:
        scanner_config_manager: Optional config manager
        
    Returns:
        List of valid status codes
    """
    if scanner_config_manager:
        try:
            return scanner_config_manager.get_valid_status_codes()
        except:
            pass
    
    # Fallback if database unavailable
    return [200, 201, 202, 204, 301, 302, 307, 308, 401, 403]


def get_error_indicators(scanner_config_manager=None) -> List[str]:
    """
    Get error indicators for content validation.
    
    Args:
        scanner_config_manager: Optional config manager
        
    Returns:
        List of error indicators
    """
    if scanner_config_manager:
        try:
            return scanner_config_manager.get_error_indicators()
        except:
            pass
    
    # Fallback if database unavailable
    return [
        'not found', '404', 'file not found',
        'forbidden', '403', 'access denied', 
        'internal server error', '500',
        'bad request', '400',
        'default apache', 'default nginx',
        'it works!', 'welcome to nginx',
        'directory listing', 'index of /',
        'apache http server test page',
        'nginx welcome page',
        'test page for the apache',
        'welcome to caddy'
    ]


def get_valid_content_indicators(scanner_config_manager=None) -> List[str]:
    """
    Get valid content indicators for path validation.
    
    Args:
        scanner_config_manager: Optional config manager
        
    Returns:
        List of valid content indicators
    """
    if scanner_config_manager:
        try:
            return scanner_config_manager.get_valid_content_indicators()
        except:
            pass
    
    # Fallback if database unavailable
    return ['<html>', '<title>', '<h1>', '<form>', 'api']