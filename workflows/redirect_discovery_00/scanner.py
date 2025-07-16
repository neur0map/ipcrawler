import asyncio
import os
import re
import time
import subprocess
from typing import List, Optional, Set, Dict, Tuple
from datetime import datetime
import tempfile
from pathlib import Path
import socket

from rich.console import Console
from workflows.core.base import BaseWorkflow, WorkflowResult

# Try to import httpx for better HTTP handling
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

console = Console()


class RedirectDiscoveryScanner(BaseWorkflow):
    """Quick redirect discovery and hostname mapping workflow"""
    
    def __init__(self):
        super().__init__("redirect-discovery")
        self.common_http_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
        
    def validate_input(self, target: str, **kwargs) -> bool:
        """Validate input parameters"""
        if not target or not target.strip():
            return False
        return True
        
    def _is_root(self) -> bool:
        """Check if running with root privileges"""
        return os.geteuid() == 0
        
    async def execute(self, target: str, **kwargs) -> WorkflowResult:
        """Execute quick redirect discovery and hostname mapping"""
        start_time = time.time()
        
        if not self.validate_input(target):
            return WorkflowResult(
                success=False,
                error="Invalid target provided",
                execution_time=time.time() - start_time
            )
            
        console.print("🔍 [bold]Quick Redirect Discovery[/bold] - Mapping hostnames for optimal scanning")
        
        discovered_mappings = set()  # Set of (ip, hostname) tuples
        is_root = self._is_root()
        
        try:
            # Step 1: Quick HTTP discovery on common ports
            console.print("→ Testing common HTTP ports for redirects...")
            
            for port in self.common_http_ports:
                mappings = await self._discover_redirects_on_port(target, port)
                discovered_mappings.update(mappings)
                
            # Step 2: DNS-based discovery
            console.print("→ Performing DNS enumeration...")
            dns_mappings = await self._dns_discovery(target)
            discovered_mappings.update(dns_mappings)
            
            # Step 3: Extract unique hostname mappings
            hostname_count = len(discovered_mappings)
            console.print(f"✓ Discovered {hostname_count} hostname mappings")
            
            # Step 4: Add to /etc/hosts if sudo is available
            hosts_updated = False
            if is_root and discovered_mappings:
                hosts_updated = await self._update_etc_hosts(discovered_mappings)
                if hosts_updated:
                    console.print(f"✓ Added {len(discovered_mappings)} entries to [green]/etc/hosts[/green]")
                    console.print("  → All subsequent workflows will benefit from hostname resolution")
                else:
                    console.print("⚠ Failed to update /etc/hosts - continuing without hostname mappings")
            elif discovered_mappings and not is_root:
                console.print("ℹ [yellow]Discovered hostnames but no sudo privileges[/yellow]")
                console.print("  → Use 'sudo ipcrawler target' for automatic /etc/hosts updates")
                console.print("  → Subsequent workflows will use IP-based scanning")
            else:
                console.print("ℹ No hostnames discovered - proceeding with IP-based scanning")
                
            # Prepare results for subsequent workflows  
            result_data = {
                "tool": "redirect-discovery",
                "target": target,
                "discovered_mappings": [{"ip": ip, "hostname": hostname} for ip, hostname in discovered_mappings],
                "hostname_count": hostname_count,
                "etc_hosts_updated": hosts_updated,
                "sudo_available": is_root,
                "tested_ports": self.common_http_ports
            }
            
            return WorkflowResult(
                success=True,
                data=result_data,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                error=f"Redirect discovery failed: {str(e)}",
                execution_time=time.time() - start_time
            )
            
    async def _discover_redirects_on_port(self, target: str, port: int) -> Set[Tuple[str, str]]:
        """Discover redirects and virtual hosts using httpx (same as HTTP scanner)"""
        mappings = set()
        
        if HTTPX_AVAILABLE:
            # Use httpx for better hostname discovery (same as HTTP scanner)
            mappings.update(await self._httpx_discovery(target, port))
        else:
            # Fallback to curl method
            mappings.update(await self._curl_discovery(target, port))
            
        return mappings
        
    async def _httpx_discovery(self, target: str, port: int) -> Set[Tuple[str, str]]:
        """Use httpx for hostname discovery (matches HTTP scanner approach)"""
        mappings = set()
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]
        
        # Test different schemes
        schemes = ['https', 'http'] if port in [443, 8443] else ['http', 'https']
        
        for scheme in schemes:
            try:
                # Build URL
                if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                    url = f"{scheme}://{target}"
                else:
                    url = f"{scheme}://{target}:{port}"
                
                timeout = httpx.Timeout(connect=3.0, read=10.0, write=3.0, pool=3.0)
                async with httpx.AsyncClient(
                    verify=False, 
                    timeout=timeout,
                    follow_redirects=True,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                ) as client:
                    
                    # 1. Standard request to discover redirects and content
                    headers = {"User-Agent": user_agents[0]}
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code < 400:
                        # Extract hostnames from response
                        discovered = self._extract_hostnames_from_response(response, target)
                        for hostname in discovered:
                            ip = await self._resolve_hostname(hostname)
                            if ip:
                                mappings.add((ip, hostname))
                                console.print(f"  → Found hostname: [cyan]{hostname}[/cyan] → {ip}")
                            else:
                                mappings.add((target, hostname))
                                console.print(f"  → Found hostname: [cyan]{hostname}[/cyan] → {target} (DNS failed)")
                    
                    # 2. Test common virtual host patterns  
                    if not mappings and not self._is_ip_address(target):
                        potential_hosts = self._generate_potential_hostnames(target)
                        for hostname in potential_hosts[:5]:  # Test top 5 to keep it fast
                            vhost_mappings = await self._test_virtual_host_httpx(client, target, port, scheme, hostname)
                            mappings.update(vhost_mappings)
                            if len(mappings) >= 3:  # Stop after finding a few
                                break
                                
            except Exception as e:
                console.print(f"  [dim]→ {scheme}://{target}:{port} - {str(e)[:50]}[/dim]")
                continue
                
        return mappings
        
    async def _curl_discovery(self, target: str, port: int) -> Set[Tuple[str, str]]:
        """Fallback curl-based discovery"""
        mappings = set()
        
        for scheme in ['http', 'https']:
            try:
                cmd = [
                    'curl', '-s', '-L', '--max-redirs', '5',
                    '--connect-timeout', '3', '--max-time', '10',
                    f'{scheme}://{target}:{port}/'
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    output = stdout.decode().strip()
                    hostnames = self._extract_hostnames_from_text(output, target)
                    
                    for hostname in hostnames:
                        ip = await self._resolve_hostname(hostname)
                        if ip:
                            mappings.add((ip, hostname))
                            console.print(f"  → Found hostname: [cyan]{hostname}[/cyan] → {ip}")
                        else:
                            mappings.add((target, hostname))
                            
            except Exception:
                continue
                
        return mappings
        
    async def _dns_discovery(self, target: str) -> Set[Tuple[str, str]]:
        """Perform DNS enumeration to discover additional hostnames"""
        mappings = set()
        
        # Skip DNS discovery if target is already an IP
        if self._is_ip_address(target):
            return mappings
            
        # Common subdomain patterns  
        subdomains = [
            'www', 'api', 'mail', 'ftp', 'admin', 'portal', 'app', 'dev',
            'staging', 'test', 'beta', 'secure', 'vpn', 'remote'
        ]
        
        for subdomain in subdomains:
            hostname = f"{subdomain}.{target}"
            try:
                ip = await self._resolve_hostname(hostname)
                if ip:
                    mappings.add((ip, hostname))
            except:
                continue
                
        return mappings
         
    def _extract_hostnames_from_response(self, response, target: str) -> List[str]:
        """Extract hostnames from httpx response (headers + body)"""
        hostnames = []
        
        # From redirect locations
        if hasattr(response, 'history') and response.history:
            for redirect_response in response.history:
                location = redirect_response.headers.get('location', '')
                if location:
                    from urllib.parse import urlparse
                    parsed = urlparse(location)
                    if parsed.hostname and parsed.hostname != target:
                        hostnames.append(parsed.hostname)
        
        # From response body
        try:
            body = response.text
            hostnames.extend(self._extract_hostnames_from_text(body, target))
        except:
            pass
            
        return list(set(hostnames))
        
    def _extract_hostnames_from_text(self, text: str, target: str) -> List[str]:
        """Extract hostnames from text content"""
        hostnames = []
        
        # Enhanced patterns for hostname discovery
        patterns = [
            r'href=["\']https?://([^/\s"\'<>]+)',
            r'src=["\']https?://([^/\s"\'<>]+)', 
            r'action=["\']https?://([^/\s"\'<>]+)',
            r'window\.location[^"\']*["\']https?://([^/\s"\'<>]+)',
            r'document\.domain\s*=\s*["\']([^"\'<>]+)["\']',
            # HTB and CTF specific patterns
            r'([a-zA-Z0-9-]+\.htb)',
            r'([a-zA-Z0-9-]+\.local)',
            r'hostname["\']?\s*[:=]\s*["\']([^"\'<>\s]+)["\']',
            r'domain["\']?\s*[:=]\s*["\']([^"\'<>\s]+)["\']',
            r'Host:\s*([^"\'\s<>\r\n]+)',
            r'SERVER_NAME["\']?\s*[:=]\s*["\']([^"\'<>\s]+)["\']'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match != target and self._is_valid_hostname(match):
                    hostnames.append(match)
                    
        return list(set(hostnames))
        
    async def _test_virtual_host_httpx(self, client, target: str, port: int, scheme: str, hostname: str) -> Set[Tuple[str, str]]:
        """Test virtual host using httpx with Host header"""
        mappings = set()
        
        try:
            if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                url = f"{scheme}://{target}"
            else:
                url = f"{scheme}://{target}:{port}"
                
            # Test with Host header
            headers = {
                "Host": hostname,
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            }
            
            response = await client.get(url, headers=headers, timeout=5.0)
            
            # Check if we get a valid response indicating virtual host exists
            if response.status_code in [200, 301, 302, 403]:
                # Additional validation: check if response differs from default
                try:
                    default_response = await client.get(url, timeout=3.0)
                    if (response.status_code != default_response.status_code or 
                        len(response.content) != len(default_response.content)):
                        
                        ip = await self._resolve_hostname(hostname)
                        if ip:
                            mappings.add((ip, hostname))
                        else:
                            mappings.add((target, hostname))
                        console.print(f"  → Virtual host found: [cyan]{hostname}[/cyan]")
                except:
                    # If can't get default response, assume virtual host is valid
                    mappings.add((target, hostname))
                    console.print(f"  → Virtual host found: [cyan]{hostname}[/cyan]")
                    
        except Exception:
            pass
            
        return mappings
        
    async def _resolve_hostname(self, hostname: str) -> Optional[str]:
        """Resolve hostname to IP address"""
        try:
            # Use nslookup for reliable resolution
            process = await asyncio.create_subprocess_exec(
                'nslookup', hostname,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode()
                # Extract IP from nslookup output
                ip_pattern = r'Address: (\d+\.\d+\.\d+\.\d+)'
                match = re.search(ip_pattern, output)
                if match:
                    return match.group(1)
                    
        except Exception:
            pass
            
        return None
        
    async def _update_etc_hosts(self, mappings: Set[Tuple[str, str]]) -> bool:
        """Update /etc/hosts with discovered mappings"""
        if not mappings:
            return False
            
        try:
            # Create backup of /etc/hosts
            backup_cmd = ['cp', '/etc/hosts', '/etc/hosts.ipcrawler.backup']
            await asyncio.create_subprocess_exec(*backup_cmd)
            
            # Read current /etc/hosts
            with open('/etc/hosts', 'r') as f:
                current_content = f.read()
                
            # Check if we already have ipcrawler entries
            if '# IPCrawler entries' in current_content:
                # Remove existing ipcrawler entries
                lines = current_content.split('\n')
                filtered_lines = []
                skip_section = False
                
                for line in lines:
                    if line.startswith('# IPCrawler entries'):
                        skip_section = True
                        continue
                    elif line.startswith('# End IPCrawler entries'):
                        skip_section = False
                        continue
                    elif not skip_section:
                        filtered_lines.append(line)
                        
                current_content = '\n'.join(filtered_lines)
            
            # Add new ipcrawler entries
            new_entries = ['\n# IPCrawler entries - auto-generated']
            for ip, hostname in sorted(mappings):
                new_entries.append(f'{ip}\t{hostname}')
            new_entries.append('# End IPCrawler entries\n')
            
            # Write updated /etc/hosts
            updated_content = current_content.rstrip() + '\n'.join(new_entries)
            
            with open('/etc/hosts', 'w') as f:
                f.write(updated_content)
                
            return True
            
        except Exception as e:
            console.print(f"✗ Failed to update /etc/hosts: {e}")
            return False
            
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
        if hostname.endswith('.htb'):
            return True
            
        # Basic hostname validation - must contain at least one dot
        if '.' not in hostname:
            return False
            
        # Check for valid characters
        valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-')
        if not all(c in valid_chars for c in hostname):
            return False
            
        # Must not be just numbers (IP address)
        if hostname.replace('.', '').isdigit():
            return False
            
        return True
        
    def _is_ip_address(self, target: str) -> bool:
        """Check if target is an IP address"""
        ip_pattern = r'^\d+\.\d+\.\d+\.\d+$'
        return bool(re.match(ip_pattern, target))
        
    def _generate_potential_hostnames(self, target: str) -> List[str]:
        """Generate potential hostnames based on target"""
        hostnames = []
        
        # If target is an IP, can't generate hostnames
        if self._is_ip_address(target):
            return hostnames
            
        # Generate common subdomain patterns
        base_domain = target
        potential_patterns = [
            'www', 'mail', 'ftp', 'admin', 'portal', 'api', 'app', 'dev',
            'staging', 'test', 'prod', 'secure', 'vpn', 'remote', 'blog',
            'shop', 'store', 'demo', 'beta', 'cms', 'dashboard'
        ]
        
        for pattern in potential_patterns:
            hostnames.append(f"{pattern}.{base_domain}")
            
        return hostnames
        
    async def _test_virtual_host(self, target: str, port: int, scheme: str, hostname: str) -> Set[Tuple[str, str]]:
        """Test virtual host by sending Host header"""
        mappings = set()
        
        try:
            # Use curl with explicit Host header
            url = f'{scheme}://{target}:{port}/'
            cmd = [
                'curl',
                '-s',
                '--connect-timeout', '3',
                '--max-time', '5',
                '-H', f'Host: {hostname}',
                '-I',  # Just headers for virtual host testing
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode().strip()
                
                # Check if we get a different response (indicates virtual host exists)
                if output and 'HTTP/' in output:
                    # Look for signs this is a valid virtual host
                    status_line = output.split('\n')[0] if output else ''
                    if '200' in status_line or '301' in status_line or '302' in status_line:
                        # Check if hostname resolves, if not map to target IP
                        try:
                            ip = await self._resolve_hostname(hostname)
                            if ip:
                                mappings.add((ip, hostname))
                            else:
                                mappings.add((target, hostname))
                            console.print(f"  → Virtual host found: [cyan]{hostname}[/cyan]")
                        except:
                            mappings.add((target, hostname))
                            
        except Exception:
            pass
            
        return mappings 