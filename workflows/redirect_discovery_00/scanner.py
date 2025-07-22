import asyncio
import time
import re
import tempfile
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path

from rich.console import Console

from workflows.core.base import BaseWorkflow, WorkflowResult

console = Console()


class RedirectDiscoveryScanner(BaseWorkflow):
    """Redirect discovery scanner for hostname/subdomain enumeration"""
    
    def __init__(self):
        super().__init__("redirect-discovery")
        self.common_http_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
    
    def validate_input(self, target: str, **kwargs) -> bool:
        """Validate input parameters"""
        if not target or not target.strip():
            return False
        return True
    
    async def execute(self, target: str, **kwargs) -> WorkflowResult:
        """Execute redirect discovery scan to find hostnames"""
        start_time = time.time()
        
        if not self.validate_input(target):
            return WorkflowResult(
                success=False,
                error="Invalid target provided",
                execution_time=time.time() - start_time
            )
        
        try:
            discovered_mappings = []
            
            # First, try to discover open HTTP ports quickly
            console.print(f"🔍 Discovering HTTP redirects for {target}...")
            
            # Quick port check for common HTTP ports
            open_http_ports = await self._quick_port_check(target)
            
            if not open_http_ports:
                console.print("  [dim]No HTTP ports found for redirect discovery[/dim]")
                return WorkflowResult(
                    success=True,
                    data={
                        "tool": "redirect-discovery",
                        "target": target,
                        "discovered_mappings": [],
                        "ports_checked": self.common_http_ports,
                        "redirect_count": 0
                    },
                    execution_time=time.time() - start_time
                )
            
            # Discover redirects on open HTTP ports
            mappings = await self._discover_redirects(target, open_http_ports)
            discovered_mappings.extend(mappings)
            
            # Also try subdomain enumeration using common patterns
            subdomain_mappings = await self._discover_subdomains(target)
            discovered_mappings.extend(subdomain_mappings)
            
            # Remove duplicates
            unique_mappings = []
            seen = set()
            for mapping in discovered_mappings:
                key = (mapping['ip'], mapping['hostname'])
                if key not in seen:
                    seen.add(key)
                    unique_mappings.append(mapping)
            
            console.print(f"✅ Redirect discovery found {len(unique_mappings)} hostname mappings")
            
            return WorkflowResult(
                success=True,
                data={
                    "tool": "redirect-discovery",
                    "target": target,
                    "discovered_mappings": unique_mappings,
                    "ports_checked": open_http_ports,
                    "redirect_count": len(unique_mappings)
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                error=f"Redirect discovery failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _quick_port_check(self, target: str) -> List[int]:
        """Quick check for open HTTP ports using nmap"""
        open_ports = []
        
        try:
            # Quick nmap scan for common HTTP ports
            port_list = ','.join(map(str, self.common_http_ports))
            
            cmd = [
                "nmap",
                "-p", port_list,
                "-sS",  # SYN scan
                "-T4",  # Fast timing
                "--open",
                "-Pn",  # Skip ping
                "-n",   # No DNS resolution
                "--max-retries", "1",
                "--host-timeout", "10s",
                target
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode()
                # Parse for open ports
                port_pattern = r'(\d+)/tcp\s+open'
                matches = re.findall(port_pattern, output)
                
                for port_str in matches:
                    try:
                        port = int(port_str)
                        if port in self.common_http_ports:
                            open_ports.append(port)
                    except ValueError:
                        continue
            
        except Exception as e:
            console.print(f"  [dim]Port check error: {str(e)[:50]}[/dim]")
            # Fallback to common ports if nmap fails
            open_ports = [80, 443]
        
        return open_ports
    
    async def _discover_redirects(self, target: str, ports: List[int]) -> List[Dict[str, str]]:
        """Discover hostnames through HTTP redirects"""
        mappings = []
        
        for port in ports:
            try:
                # Try both HTTP and HTTPS
                protocols = ['http']
                if port in [443, 8443]:
                    protocols = ['https']
                elif port == 80:
                    protocols = ['http', 'https']
                
                for protocol in protocols:
                    url = f"{protocol}://{target}:{port}/"
                    
                    # Use curl to follow redirects and extract Location headers
                    cmd = [
                        "curl",
                        "-I",  # HEAD request
                        "-s",  # Silent
                        "-L",  # Follow redirects
                        "--max-time", "5",
                        "--max-redirs", "3",
                        "--connect-timeout", "3",
                        url
                    ]
                    
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        output = stdout.decode()
                        hostnames = self._extract_hostnames_from_headers(output, target)
                        
                        for hostname in hostnames:
                            mappings.append({
                                'ip': target,
                                'hostname': hostname,
                                'source': f'redirect_{protocol}_{port}'
                            })
                            
            except Exception as e:
                continue
        
        return mappings
    
    async def _discover_subdomains(self, target: str) -> List[Dict[str, str]]:
        """Discover subdomains using common patterns"""
        mappings = []
        
        # Extract base domain if target is an IP
        if self._is_ip_address(target):
            # For IP addresses, try common subdomain patterns with .htb, .local
            base_domains = ['htb', 'local']
            common_subdomains = ['www', 'admin', 'api', 'dev', 'test', 'staging']
            
            for base_domain in base_domains:
                # Try to find the main domain first
                main_domain = await self._try_reverse_dns(target)
                if main_domain and '.' in main_domain:
                    base = main_domain.split('.')[0]
                    full_domain = f"{base}.{base_domain}"
                    
                    # Test if main domain resolves
                    if await self._test_hostname_resolution(full_domain, target):
                        mappings.append({
                            'ip': target,
                            'hostname': full_domain,
                            'source': 'reverse_dns'
                        })
                        
                        # Try common subdomains
                        for subdomain in common_subdomains:
                            test_hostname = f"{subdomain}.{full_domain}"
                            if await self._test_hostname_resolution(test_hostname, target):
                                mappings.append({
                                    'ip': target,
                                    'hostname': test_hostname,
                                    'source': 'subdomain_enum'
                                })
        
        return mappings
    
    def _extract_hostnames_from_headers(self, headers: str, target: str) -> List[str]:
        """Extract hostnames from HTTP headers"""
        hostnames = []
        
        # Patterns to find hostnames in headers
        patterns = [
            r'Location:\s*https?://([^/\s<>\r\n]+)',
            r'Host:\s*([^/\s<>\r\n]+)',
            r'Server:\s*.*?([a-zA-Z0-9-]+\.(?:htb|local|com|net|org))',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, headers, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                hostname = match.strip()
                if hostname and hostname != target and self._is_valid_hostname(hostname):
                    hostnames.append(hostname)
        
        return list(set(hostnames))
    
    async def _try_reverse_dns(self, ip: str) -> Optional[str]:
        """Try reverse DNS lookup"""
        try:
            cmd = ["nslookup", ip]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=3.0
            )
            
            if process.returncode == 0:
                output = stdout.decode()
                # Look for name = pattern
                name_pattern = r'name\s*=\s*([^\s\r\n]+)'
                match = re.search(name_pattern, output, re.IGNORECASE)
                if match:
                    hostname = match.group(1).rstrip('.')
                    if self._is_valid_hostname(hostname):
                        return hostname
                        
        except Exception:
            pass
            
        return None
    
    async def _test_hostname_resolution(self, hostname: str, expected_ip: str) -> bool:
        """Test if hostname resolves to expected IP"""
        try:
            cmd = ["nslookup", hostname]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=2.0
            )
            
            if process.returncode == 0:
                output = stdout.decode()
                # Look for Address: pattern
                ip_pattern = r'Address:\s*(\d+\.\d+\.\d+\.\d+)'
                match = re.search(ip_pattern, output)
                if match:
                    resolved_ip = match.group(1)
                    return resolved_ip == expected_ip
                    
        except Exception:
            pass
            
        return False
    
    def _is_ip_address(self, addr: str) -> bool:
        """Check if string is an IP address"""
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        return bool(re.match(ip_pattern, addr))
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if hostname is valid"""
        if not hostname or len(hostname) > 255:
            return False
            
        # Skip obviously invalid hostnames
        if hostname.startswith('.') or hostname.endswith('.'):
            return False
            
        # Skip localhost and common non-targets
        skip_patterns = ['localhost', '127.0.0.1', '0.0.0.0', 'example.com', 'test.com']
        if any(skip in hostname.lower() for skip in skip_patterns):
            return False
            
        # HTB (HackTheBox) domains are valid targets (.htb extension)
        if hostname.endswith('.htb') or hostname.endswith('.local'):
            return True
            
        # Hostname must contain at least one dot
        if '.' not in hostname:
            return False
            
        # Validate characters
        valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-')
        if not all(c in valid_chars for c in hostname):
            return False
            
        # Must not be just numbers (IP address)
        if hostname.replace('.', '').isdigit():
            return False
            
        return True