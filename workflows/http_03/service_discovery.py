"""
HTTP/HTTPS service discovery for HTTP scanner workflow.

This module handles HTTP service detection, connection testing,
and service validation across multiple hostnames and ports.
"""

import subprocess
import re
from typing import List, Optional, Dict, Any
from .models import HTTPService
from .config import get_scanner_config
from .utils import (
    get_scheme_order_for_port, build_url, extract_hostnames_from_response,
    is_unique_service, count_vuln_severities
)
from utils.debug import debug_print


class ServiceDiscovery:
    """HTTP/HTTPS service discovery handler"""
    
    def __init__(self, original_ip: str):
        self.config = get_scanner_config()
        self.original_ip = original_ip
    
    async def scan_http_service(self, target: str, port: int, use_ip: Optional[str] = None) -> Optional[HTTPService]:
        """
        Scan a single HTTP/HTTPS service.
        
        Args:
            target: Target hostname or IP
            port: Port to scan
            use_ip: Optional IP to use for connection (with Host header)
            
        Returns:
            HTTPService object if service found, None otherwise
        """
        if not self.config.deps_available:
            return await self._scan_service_fallback(target, port, use_ip)
        
        try:
            import httpx
            
            # Determine scheme order based on port
            schemes = get_scheme_order_for_port(port)
            
            for scheme in schemes:
                service = await self._test_service_with_httpx(target, port, scheme, use_ip)
                if service:
                    return service
                    
        except Exception as e:
            debug_print(f"Service scan error for {target}:{port}: {e}")
        
        return None
    
    async def _test_service_with_httpx(self, target: str, port: int, scheme: str, 
                                     use_ip: Optional[str] = None) -> Optional[HTTPService]:
        """
        Test service using httpx library.
        
        Args:
            target: Target hostname
            port: Port number
            scheme: http or https
            use_ip: Optional IP for connection
            
        Returns:
            HTTPService if successful, None otherwise
        """
        import httpx
        
        # Use IP for connection if provided, otherwise use target
        connect_to = use_ip if use_ip else target
        url = build_url(scheme, connect_to, port)
        
        try:
            # Use specific timeouts from config
            timeout_settings = self.config.get_timeout_settings()
            timeout = httpx.Timeout(
                connect=timeout_settings['connect'],
                read=timeout_settings['read'],
                write=timeout_settings['write'],
                pool=timeout_settings['pool']
            )
            
            concurrency = self.config.get_concurrency_limits()
            async with httpx.AsyncClient(
                verify=False,
                timeout=timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=concurrency['max_keepalive_connections'],
                    max_connections=concurrency['max_connections']
                )
            ) as client:
                # Set proper Host header with the target (which might be a hostname)
                headers = {
                    "User-Agent": self.config.get_user_agents()[0],
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
                    service.response_body = response.text[:10000]  # First 10KB
                except:
                    service.response_body = ""
                
                debug_print(f"Service found: {scheme}://{target}:{port} (status: {response.status_code})")
                return service
                
        except Exception as e:
            debug_print(f"HTTP {scheme} test failed for {target}:{port}: {e}")
            
        return None
    
    async def _scan_service_fallback(self, target: str, port: int, use_ip: Optional[str] = None) -> Optional[HTTPService]:
        """
        Fallback service scanning using curl.
        
        Args:
            target: Target hostname
            port: Port number
            use_ip: Optional IP for connection
            
        Returns:
            HTTPService if successful, None otherwise
        """
        schemes = get_scheme_order_for_port(port)
        
        for scheme in schemes:
            service = await self._test_service_with_curl(target, port, scheme, use_ip)
            if service:
                return service
        
        return None
    
    async def _test_service_with_curl(self, target: str, port: int, scheme: str, 
                                    use_ip: Optional[str] = None) -> Optional[HTTPService]:
        """
        Test service using curl command.
        
        Args:
            target: Target hostname
            port: Port number
            scheme: http or https
            use_ip: Optional IP for connection
            
        Returns:
            HTTPService if successful, None otherwise
        """
        # Determine what to connect to
        connect_to = use_ip if use_ip else target
        url = build_url(scheme, connect_to, port)
        
        curl_cmd = [
            "curl", "-I", "-s", "-m", "5",
            "-k",  # Allow insecure connections
            "-L",  # Follow redirects
            "-H", f"User-Agent: {self.config.get_user_agents()[0]}",
        ]
        
        # Always add Host header when using IP to connect but testing hostname
        if use_ip and target != use_ip:
            curl_cmd.extend(["-H", f"Host: {target}"])
        
        curl_cmd.append(url)
        
        try:
            result = subprocess.run(
                curl_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            debug_print(f"curl command: {' '.join(curl_cmd)}")
            debug_print(f"curl return code: {result.returncode}")
            
            if result.returncode == 0 and result.stdout:
                service = HTTPService(
                    port=port,
                    scheme=scheme,
                    url=url,
                    headers={},
                    is_https=(scheme == 'https')
                )
                
                # Parse headers
                lines = result.stdout.strip().split('\\n')
                if lines:
                    status_match = re.match(r'HTTP/[\\d.]+ (\\d+)', lines[0])
                    if status_match:
                        service.status_code = int(status_match.group(1))
                
                for line in lines[1:]:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        service.headers[key.strip()] = value.strip()
                        
                        if key.lower() == 'server':
                            service.server = value.strip()
                
                debug_print(f"Fallback service found: {url} (status: {service.status_code})")
                return service
                
        except Exception as e:
            debug_print(f"curl error for {url}: {e}")
        
        return None
    
    async def discover_all_services(self, all_hostnames: List[str], scan_ports: List[int]) -> List[HTTPService]:
        """
        Discover HTTP services across all hostname and port combinations.
        
        Args:
            all_hostnames: List of hostnames to test
            scan_ports: List of ports to scan
            
        Returns:
            List of discovered HTTPService objects
        """
        services = []
        
        debug_print(f"Testing {len(scan_ports)} ports across {len(all_hostnames)} hostnames")
        
        # HTTP service discovery - test ALL hostname combinations
        for port in scan_ports:
            # Test each hostname for this port
            for hostname in all_hostnames:
                # Determine connection target (IP if hostname differs from target)
                use_ip = self.original_ip if hostname != self.original_ip else None
                service = await self.scan_http_service(hostname, port, use_ip=use_ip)
                if service:
                    # Store which hostname worked
                    service.actual_target = hostname
                    
                    # Check if this is a unique service (different from existing ones)
                    if is_unique_service(service, services):
                        services.append(service)
                        debug_print(f"Found unique service: {service.url} (hostname: {hostname})")
                        
                        # Extract additional hostnames from response
                        new_hostnames = self._extract_new_hostnames(service, all_hostnames)
                        if new_hostnames:
                            debug_print(f"Discovered additional hostnames: {new_hostnames}")
                            # Test newly discovered hostnames on this port
                            for new_hostname in new_hostnames:
                                additional_service = await self.scan_http_service(
                                    new_hostname, port, use_ip=self.original_ip
                                )
                                if additional_service and is_unique_service(additional_service, services):
                                    additional_service.actual_target = new_hostname
                                    services.append(additional_service)
                                    debug_print(f"Found service via discovered hostname: {additional_service.url}")
                                    # Update the all_hostnames list for other ports
                                    all_hostnames.append(new_hostname)
        
        return services
    
    def _extract_new_hostnames(self, service: HTTPService, existing_hostnames: List[str]) -> List[str]:
        """
        Extract new hostnames from service response.
        
        Args:
            service: HTTPService object
            existing_hostnames: List of already known hostnames
            
        Returns:
            List of newly discovered hostnames
        """
        new_hostnames = extract_hostnames_from_response(
            service.url, service.headers, service.response_body, self.original_ip
        )
        
        # Filter out hostnames we already know about
        filtered_new = []
        for hostname in new_hostnames:
            if hostname not in existing_hostnames:
                filtered_new.append(hostname)
        
        return filtered_new
    
    async def discover_services_fallback(self, all_hostnames: List[str], scan_ports: List[int]) -> Dict[str, Any]:
        """
        Fallback service discovery for when dependencies are unavailable.
        
        Args:
            all_hostnames: List of hostnames to test
            scan_ports: List of ports to scan
            
        Returns:
            Dictionary with service discovery results
        """
        results = {
            "services": [],
            "vulnerabilities": [],
            "fallback_mode": True,
            "scan_engine": "curl+nslookup"
        }
        
        debug_print(f"Fallback mode scanning ports: {scan_ports}, testing {len(all_hostnames)} hostnames")
        
        for port in scan_ports:
            # Try HTTP first for common HTTP ports
            if port in [80, 8080, 8000]:
                schemes = ['http', 'https']
            elif port in [443, 8443]:
                schemes = ['https', 'http']
            else:
                schemes = ['http', 'https']
            
            for scheme in schemes:
                for try_target in all_hostnames:
                    # Determine what to connect to
                    connect_to = self.original_ip if try_target != self.original_ip else try_target
                    url = build_url(scheme, connect_to, port)
                    
                    curl_cmd = [
                        "curl", "-I", "-s", "-m", "5",
                        "-k",  # Allow insecure connections
                        "-L",  # Follow redirects
                        "-H", f"User-Agent: {self.config.get_user_agents()[0]}",
                    ]
                    
                    # Always add Host header when using a hostname
                    if try_target != self.original_ip:
                        curl_cmd.extend(["-H", f"Host: {try_target}"])
                    
                    curl_cmd.append(url)
                    
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
                            lines = result.stdout.strip().split('\\n')
                            if lines:
                                status_match = re.match(r'HTTP/[\\d.]+ (\\d+)', lines[0])
                                if status_match:
                                    service["status_code"] = int(status_match.group(1))
                            
                            for line in lines[1:]:
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    service["headers"][key.strip()] = value.strip()
                                    
                                    if key.lower() == 'server':
                                        service["server"] = value.strip()
                            
                            # Check if this is unique before adding
                            is_unique = True
                            for existing in results["services"]:
                                if (existing["port"] == service["port"] and 
                                    existing["scheme"] == service["scheme"] and
                                    existing.get("status_code") == service.get("status_code") and
                                    existing.get("server") == service.get("server")):
                                    is_unique = False
                                    break
                            
                            if is_unique:
                                results["services"].append(service)
                                debug_print(f"Found unique service in fallback: {url} (hostname: {try_target})")
                                
                                # Basic vulnerability checks
                                vulns = self._check_basic_vulnerabilities(service)
                                results["vulnerabilities"].extend(vulns)
                            
                    except Exception as e:
                        debug_print(f"curl error for {url}: {e}")
                        continue
        
        # Add summary if we found services
        if results['services']:
            results['summary'] = {
                'total_services': len(results['services']),
                'total_vulnerabilities': len(results['vulnerabilities']),
                'severity_counts': count_vuln_severities(results['vulnerabilities']),
                'technologies': [],
                'discovered_paths': []
            }
        
        return results
    
    def _check_basic_vulnerabilities(self, service: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Basic vulnerability checks for fallback mode.
        
        Args:
            service: Service dictionary
            
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
        
        return vulnerabilities