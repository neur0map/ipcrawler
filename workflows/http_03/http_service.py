"""HTTP Service Scanner Module for HTTP_03 Workflow

Handles individual HTTP/HTTPS service scanning and hostname discovery.
"""

import re
from typing import List, Optional
from urllib.parse import urlparse
from .models import HTTPService

# HTTP dependencies
try:
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


class HTTPServiceScanner:
    """Handles HTTP/HTTPS service scanning"""
    
    def __init__(self, user_agents: List[str]):
        """Initialize with user agent list"""
        self.user_agents = user_agents
        self.original_ip = None  # Set by parent scanner
    
    async def scan_http_service(self, target: str, port: int, 
                               use_ip: Optional[str] = None) -> Optional[HTTPService]:
        """Scan a single HTTP/HTTPS service
        
        Args:
            target: Target hostname/IP
            port: Port to scan
            use_ip: IP to connect to (for hostname testing)
            
        Returns:
            HTTPService object if successful, None otherwise
        """
        if not HTTP_AVAILABLE:
            return None
            
        # Determine scheme order based on port
        if port == 443 or port == 8443:
            schemes = ['https', 'http']
        elif port == 80 or port == 8080 or port == 8000:
            schemes = ['http', 'https']
        else:
            schemes = ['http', 'https']  # Try HTTP first for unknown ports
            
        for scheme in schemes:
            # Use IP for connection if provided, otherwise use target
            connect_to = use_ip if use_ip else target
            
            # Don't include port for standard ports
            if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                url = f"{scheme}://{connect_to}"
            else:
                url = f"{scheme}://{connect_to}:{port}"
            
            try:
                # Use more specific timeouts
                timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
                async with httpx.AsyncClient(
                    verify=False, 
                    timeout=timeout,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                ) as client:
                    # Set proper Host header with the target (which might be a hostname)
                    headers = {
                        "User-Agent": self.user_agents[0],
                        "Host": target  # Use the target (hostname) for Host header
                    }
                    
                    response = await client.get(
                        url,
                        headers=headers,
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
                    try:
                        service.response_body = response.text[:10000]
                    except:
                        service.response_body = ""
                    
                    return service
                    
            except httpx.ConnectError:
                # Connection refused or timeout - try next scheme
                continue
            except httpx.TimeoutException:
                # Timeout - try next scheme
                continue
            except Exception:
                # Other errors - try next scheme
                continue
                
        return None
    
    def is_unique_service(self, new_service: HTTPService, 
                         existing_services: List[HTTPService]) -> bool:
        """Check if service is unique (different content/headers from existing ones)
        
        Args:
            new_service: New service to check
            existing_services: List of existing services
            
        Returns:
            True if service is unique, False if duplicate
        """
        for existing in existing_services:
            if (existing.port == new_service.port and 
                existing.scheme == new_service.scheme):
                
                # Compare key indicators of uniqueness
                same_status = existing.status_code == new_service.status_code
                same_server = existing.server == new_service.server
                same_title = self._extract_title(existing.response_body) == self._extract_title(new_service.response_body)
                same_content_length = len(existing.response_body or '') == len(new_service.response_body or '')
                
                # If all key indicators are the same, consider it duplicate
                if same_status and same_server and same_title and same_content_length:
                    return False
        
        return True
    
    def extract_hostnames_from_response(self, service: HTTPService) -> List[str]:
        """Extract additional hostnames from HTTP response
        
        Args:
            service: HTTPService with response data
            
        Returns:
            List of discovered hostnames
        """
        hostnames = []
        
        # From redirects in Location header
        location = service.headers.get('location', '')
        if location:
            parsed = urlparse(location)
            if parsed.hostname:
                hostnames.append(parsed.hostname)
        
        # From HTML content
        if service.response_body:
            # Find links with different hostnames
            link_pattern = r'https?://([^/\s"\']+)'
            for match in re.finditer(link_pattern, service.response_body):
                hostname = match.group(1)
                if '.' in hostname and not hostname.replace('.', '').isdigit():
                    hostnames.append(hostname)
            
            # Extract from specific HTML elements
            patterns = [
                r'href=["\']https?://([^/\s"\']+)',
                r'src=["\']https?://([^/\s"\']+)',
                r'action=["\']https?://([^/\s"\']+)'
            ]
            
            for pattern in patterns:
                for match in re.finditer(pattern, service.response_body):
                    hostname = match.group(1)
                    if '.' in hostname and not hostname.replace('.', '').isdigit():
                        hostnames.append(hostname)
        
        # Remove duplicates and filter relevant hostnames
        unique_hostnames = list(set(hostnames))
        
        # Filter to only include hostnames that might be related to the target
        filtered = []
        if self.original_ip:
            target_parts = self.original_ip.split('.')
            
            for hostname in unique_hostnames:
                # Skip obviously unrelated domains
                if any(skip in hostname.lower() for skip in ['google', 'facebook', 'twitter', 'cdn', 'googleapis']):
                    continue
                
                # Include if it shares domain components with target or is a subdomain
                if any(part in hostname for part in target_parts if len(part) > 2):
                    filtered.append(hostname)
                elif '.' in self.original_ip and hostname.endswith(self.original_ip.split('.', 1)[1]):
                    filtered.append(hostname)
        
        return filtered[:10]  # Limit to prevent excessive discoveries
    
    async def test_discovered_hostname(self, hostname: str, port: int, original_service: HTTPService) -> Optional[HTTPService]:
        """Test a discovered hostname to see if it serves different content
        
        Args:
            hostname: Hostname to test
            port: Port to test
            original_service: Original service for comparison
            
        Returns:
            HTTPService if hostname serves different content, None otherwise
        """
        if not HTTP_AVAILABLE:
            return None
        
        # Determine scheme based on original service
        scheme = original_service.scheme
        
        try:
            # Use more specific timeouts
            timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
            async with httpx.AsyncClient(
                verify=False, 
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            ) as client:
                # Build URL for hostname
                if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                    url = f"{scheme}://{self.original_ip}"
                else:
                    url = f"{scheme}://{self.original_ip}:{port}"
                
                # Set proper Host header with the discovered hostname
                headers = {
                    "User-Agent": self.user_agents[0],
                    "Host": hostname  # Use discovered hostname for Host header
                }
                
                response = await client.get(
                    url,
                    headers=headers,
                    follow_redirects=True
                )
                
                # Create service object
                new_service = HTTPService(
                    port=port,
                    scheme=scheme,
                    url=f"{scheme}://{hostname}" + (f":{port}" if port not in [80, 443] else ""),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    server=response.headers.get('server', 'Unknown'),
                    is_https=(scheme == 'https')
                )
                
                # Get response body for analysis
                try:
                    new_service.response_body = response.text[:10000]
                except:
                    new_service.response_body = ""
                
                # Check if this hostname serves different content than original
                if self._is_different_content(new_service, original_service):
                    new_service.virtual_host = hostname
                    return new_service
                    
        except Exception as e:
            debug_print(f"Error testing hostname {hostname}: {e}")
            
        return None
    
    def _is_different_content(self, service1: HTTPService, service2: HTTPService) -> bool:
        """Check if two services serve significantly different content
        
        Args:
            service1: First service
            service2: Second service
            
        Returns:
            True if content is significantly different
        """
        # Different status codes indicate different behavior
        if service1.status_code != service2.status_code:
            return True
        
        # Different servers suggest different configurations
        if service1.server != service2.server:
            return True
        
        # Compare titles
        title1 = self._extract_title(service1.response_body)
        title2 = self._extract_title(service2.response_body)
        if title1 != title2 and title1 and title2:
            return True
        
        # Compare content lengths (significant difference)
        len1 = len(service1.response_body or '')
        len2 = len(service2.response_body or '')
        if abs(len1 - len2) > min(len1, len2) * 0.3:  # >30% difference
            return True
        
        # Compare key headers that indicate different applications
        key_headers = ['x-powered-by', 'x-generator', 'x-drupal-cache', 'x-varnish']
        for header in key_headers:
            val1 = service1.headers.get(header, '')
            val2 = service2.headers.get(header, '')
            if val1 != val2 and (val1 or val2):
                return True
        
        # Check for different application indicators in content
        if service1.response_body and service2.response_body:
            content1 = service1.response_body.lower()
            content2 = service2.response_body.lower()
            
            # Look for application-specific keywords
            app_keywords = [
                'wordpress', 'drupal', 'joomla', 'django', 'laravel',
                'roundcube', 'webmail', 'phpmyadmin', 'grafana',
                'jenkins', 'kibana', 'prometheus'
            ]
            
            for keyword in app_keywords:
                in_content1 = keyword in content1
                in_content2 = keyword in content2
                if in_content1 != in_content2:  # Present in one but not the other
                    return True
        
        return False
    
    def _extract_title(self, response_body: Optional[str]) -> str:
        """Extract title from HTML response
        
        Args:
            response_body: HTML response body
            
        Returns:
            Extracted title or empty string
        """
        if not response_body:
            return ""
        
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', response_body, re.IGNORECASE)
        return title_match.group(1).strip() if title_match else ""