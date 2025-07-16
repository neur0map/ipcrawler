import asyncio
import os
import re
import time
import subprocess
from typing import List, Optional, Set, Dict, Tuple
from datetime import datetime
import tempfile
from pathlib import Path

from rich.console import Console
from workflows.core.base import BaseWorkflow, WorkflowResult

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
        """Discover redirects on a specific port using curl"""
        mappings = set()
        
        for scheme in ['http', 'https']:
            try:
                # Use curl to follow redirects and capture all URLs
                cmd = [
                    'curl',
                    '-s',                           # Silent
                    '-L',                           # Follow redirects  
                    '-I',                           # Head request only
                    '--max-redirs', '5',            # Max 5 redirects
                    '--connect-timeout', '3',       # Quick timeout
                    '--max-time', '10',             # Total timeout
                    '-w', '%{url_effective}\\n%{redirect_url}\\n',  # Write effective and redirect URLs
                    f'{scheme}://{target}:{port}/'
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    output = stdout.decode().strip()
                    
                    # Extract hostnames from URLs in curl output
                    url_pattern = r'https?://([^:/\s]+)'
                    urls = re.findall(url_pattern, output)
                    
                    for hostname in urls:
                        if hostname != target and self._is_valid_hostname(hostname):
                            # Resolve hostname to IP to create mapping
                            try:
                                ip = await self._resolve_hostname(hostname)
                                if ip:
                                    mappings.add((ip, hostname))
                            except:
                                # If can't resolve, try using target IP
                                mappings.add((target, hostname))
                                
            except asyncio.TimeoutError:
                continue
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
            
        # Basic hostname validation
        if hostname.replace('.', '').replace('-', '').isalnum():
            return True
            
        return False
        
    def _is_ip_address(self, target: str) -> bool:
        """Check if target is an IP address"""
        ip_pattern = r'^\d+\.\d+\.\d+\.\d+$'
        return bool(re.match(ip_pattern, target)) 