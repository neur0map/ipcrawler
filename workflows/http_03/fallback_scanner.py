"""Fallback Scanner Module for HTTP_03 Workflow

Handles basic HTTP connectivity checks and fallback scanning methods when advanced features are unavailable.
"""

import socket
import asyncio
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from .models import HTTPService

# HTTP dependencies
try:
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

# Utils
from src.core.utils.debugging import debug_print


class FallbackScanner:
    """Handles basic HTTP scanning when advanced features are unavailable"""
    
    def __init__(self, user_agents: List[str]):
        """Initialize with user agent list"""
        self.user_agents = user_agents or ['IPCrawler/1.0']
        self.original_ip = None  # Set by parent scanner
    
    async def basic_connectivity_check(self, target: str, ports: List[int]) -> List[Dict[str, Any]]:
        """Basic TCP connectivity check for HTTP/HTTPS ports"""
        results = []
        
        for port in ports:
            if await self._check_port_open(target, port):
                # Determine likely scheme based on port
                scheme = 'https' if port in [443, 8443] else 'http'
                
                service_info = {
                    'host': target,
                    'port': port,
                    'scheme': scheme,
                    'status': 'open',
                    'method': 'tcp_connect'
                }
                
                results.append(service_info)
        
        return results
    
    async def _check_port_open(self, host: str, port: int, timeout: float = 3.0) -> bool:
        """Check if a TCP port is open"""
        try:
            # Use asyncio.wait_for to handle timeout
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            
            # Close the connection
            writer.close()
            await writer.wait_closed()
            
            return True
            
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
        except Exception:
            return False
    
    async def basic_http_check(self, target: str, port: int) -> Optional[HTTPService]:
        """Basic HTTP check without advanced features"""
        if not HTTP_AVAILABLE:
            return await self._socket_based_http_check(target, port)
        
        # Try HTTPS first for common HTTPS ports
        schemes = ['https', 'http'] if port in [443, 8443] else ['http', 'https']
        
        for scheme in schemes:
            service = await self._simple_http_request(target, port, scheme)
            if service:
                return service
        
        return None
    
    async def _simple_http_request(self, target: str, port: int, scheme: str) -> Optional[HTTPService]:
        """Simple HTTP request without advanced error handling"""
        try:
            # Build URL
            if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                url = f"{scheme}://{target}"
            else:
                url = f"{scheme}://{target}:{port}"
            
            # Simple timeout configuration
            timeout = httpx.Timeout(connect=5.0, read=10.0)
            
            async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": self.user_agents[0]},
                    follow_redirects=False  # Don't follow redirects in basic mode
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
                
                # Get basic response body (limited)
                try:
                    service.response_body = response.text[:5000]  # Limit to 5KB
                except:
                    service.response_body = ""
                
                return service
                
        except Exception as e:
            debug_print(f"Basic HTTP check failed for {scheme}://{target}:{port} - {e}")
            return None
    
    async def _socket_based_http_check(self, target: str, port: int) -> Optional[HTTPService]:
        """Socket-based HTTP check when httpx is not available"""
        try:
            # Try HTTPS first for common HTTPS ports
            is_https = port in [443, 8443]
            scheme = 'https' if is_https else 'http'
            
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, sock.connect, (target, port)
                )
                
                # Send basic HTTP request
                request = f"GET / HTTP/1.1\r\nHost: {target}\r\nUser-Agent: {self.user_agents[0]}\r\nConnection: close\r\n\r\n"
                await asyncio.get_event_loop().run_in_executor(
                    None, sock.sendall, request.encode()
                )
                
                # Receive response
                response_data = b""
                while True:
                    try:
                        chunk = await asyncio.get_event_loop().run_in_executor(
                            None, sock.recv, 4096
                        )
                        if not chunk:
                            break
                        response_data += chunk
                        if len(response_data) > 10000:  # Limit response size
                            break
                    except:
                        break
                
                sock.close()
                
                # Parse basic response
                response_text = response_data.decode('utf-8', errors='ignore')
                lines = response_text.split('\r\n')
                
                if lines and 'HTTP/' in lines[0]:
                    # Parse status line
                    status_parts = lines[0].split(' ', 2)
                    status_code = int(status_parts[1]) if len(status_parts) > 1 else 0
                    
                    # Parse headers
                    headers = {}
                    for line in lines[1:]:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            headers[key.strip().lower()] = value.strip()
                        elif line == '':  # End of headers
                            break
                    
                    # Build URL
                    if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                        url = f"{scheme}://{target}"
                    else:
                        url = f"{scheme}://{target}:{port}"
                    
                    service = HTTPService(
                        port=port,
                        scheme=scheme,
                        url=url,
                        status_code=status_code,
                        headers=headers,
                        server=headers.get('server', 'Unknown'),
                        is_https=is_https
                    )
                    
                    # Extract body
                    body_start = response_text.find('\r\n\r\n')
                    if body_start != -1:
                        service.response_body = response_text[body_start + 4:5000]  # Limit to 5KB
                    
                    return service
                    
            except Exception as e:
                debug_print(f"Socket HTTP check failed for {target}:{port} - {e}")
                sock.close()
                
        except Exception as e:
            debug_print(f"Socket creation failed for {target}:{port} - {e}")
        
        return None
    
    def extract_basic_info(self, service: HTTPService) -> Dict[str, Any]:
        """Extract basic information from HTTP service"""
        info = {
            'url': service.url,
            'status_code': service.status_code,
            'server': service.server,
            'scheme': service.scheme,
            'port': service.port
        }
        
        # Extract basic technology indicators
        tech_indicators = []
        
        # From server header
        if service.server and service.server != 'Unknown':
            server_lower = service.server.lower()
            if 'apache' in server_lower:
                tech_indicators.append('Apache')
            elif 'nginx' in server_lower:
                tech_indicators.append('Nginx')
            elif 'iis' in server_lower:
                tech_indicators.append('IIS')
        
        # From headers
        if 'x-powered-by' in service.headers:
            tech_indicators.append(service.headers['x-powered-by'])
        
        # From response body (basic detection)
        if service.response_body:
            body_lower = service.response_body.lower()
            if 'wordpress' in body_lower or 'wp-content' in body_lower:
                tech_indicators.append('WordPress')
            elif 'drupal' in body_lower:
                tech_indicators.append('Drupal')
            elif 'joomla' in body_lower:
                tech_indicators.append('Joomla')
        
        info['technologies'] = list(set(tech_indicators))
        
        return info
    
    def is_likely_web_service(self, service: HTTPService) -> bool:
        """Determine if service is likely a web service"""
        if not service or not service.status_code:
            return False
        
        # HTTP status codes that indicate web services
        web_status_codes = [200, 201, 204, 301, 302, 307, 308, 401, 403, 404, 405, 500, 503]
        
        if service.status_code in web_status_codes:
            return True
        
        # Check for web-related headers
        web_headers = ['content-type', 'server', 'set-cookie', 'location']
        for header in web_headers:
            if header in [h.lower() for h in service.headers.keys()]:
                return True
        
        return False
    
    async def scan_common_ports(self, target: str) -> List[HTTPService]:
        """Scan common HTTP/HTTPS ports using fallback methods"""
        # Get HTTP ports from database with fallback
        try:
            from workflows.core.db_integration import get_common_http_ports
            common_ports = get_common_http_ports()
        except ImportError:
            # Fallback if database helper not available
            common_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
        services = []
        
        # Check connectivity first
        open_ports = []
        for port in common_ports:
            if await self._check_port_open(target, port):
                open_ports.append(port)
        
        # Perform HTTP checks on open ports
        for port in open_ports:
            service = await self.basic_http_check(target, port)
            if service and self.is_likely_web_service(service):
                services.append(service)
        
        return services