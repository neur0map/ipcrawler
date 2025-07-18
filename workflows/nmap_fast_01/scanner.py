import asyncio
import os
import re
import time
import tempfile
from typing import List, Optional, Set, Tuple
from pathlib import Path

from rich.console import Console

from workflows.core.base import BaseWorkflow, WorkflowResult

console = Console()


class NmapFastScanner(BaseWorkflow):
    """Fast nmap scanner with integrated hostname discovery"""
    
    def __init__(self):
        super().__init__("nmap-fast")
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
        """Execute fast nmap scan for port discovery with hostname discovery"""
        start_time = time.time()
        
        if not self.validate_input(target):
            return WorkflowResult(
                success=False,
                error="Invalid target provided",
                execution_time=time.time() - start_time
            )
        
        try:
            # Use secure temporary file for grepable output
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.gnmap', prefix=f'nmap_fast_{target.replace(".", "_")}_', delete=True) as temp_file:
                temp_output = Path(temp_file.name)
                
                is_root = self._is_root()
                
                if is_root:
                    # Privileged scan - faster SYN scan
                    cmd = [
                        "nmap",
                        "-p-",                  # Scan all 65535 ports
                        "-sS",                  # SYN scan (requires root)
                        "-T4",                  # Aggressive timing
                        "--min-rate", "1000",   # Minimum packet rate
                        "--max-retries", "2",   # Maximum retries
                        "--max-rtt-timeout", "100ms", # Prevent hanging on slow hosts
                        "--host-timeout", "5m", # Overall timeout
                        "--open",               # Only show open ports
                        "-Pn",                  # Skip ping (assume host is up)
                        "-n",                   # No DNS resolution for fast scan
                        "-v",                   # Verbose for real-time updates
                        "-oG", str(temp_output), # Grepable output to file
                        target
                    ]
                else:
                    # Unprivileged scan - TCP connect
                    cmd = [
                        "nmap",
                        "-p-",                  # Scan all 65535 ports
                        "-sT",                  # TCP connect scan
                        "-T4",                  # Aggressive timing
                        "--min-rate", "500",    # Lower rate for stability without root
                        "--max-retries", "2",   # Maximum retries
                        "--max-rtt-timeout", "100ms", # Prevent hanging on slow hosts
                        "--host-timeout", "5m", # Overall timeout
                        "--open",               # Only show open ports
                        "-Pn",                  # Skip ping (assume host is up)
                        "-n",                   # No DNS resolution for fast scan
                        "-v",                   # Verbose for real-time updates
                        "-oG", str(temp_output), # Grepable output to file
                        target
                    ]
                
                
                # Execute nmap with real-time output parsing
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Register process for cleanup
                try:
                    from ipcrawler import running_processes
                    running_processes.append(process)
                except:
                    pass  # Ignore if running_processes not available
                
                # Read output without progress tracking
                stdout_data, stderr_data = await process.communicate()
                stdout_data = stdout_data.decode()
                stderr_data = stderr_data.decode()
                
                if process.returncode != 0:
                    return WorkflowResult(
                        success=False,
                        error=f"Fast nmap scan failed: {stderr_data}",
                        execution_time=time.time() - start_time
                    )
                
                open_ports = set()
                
                if temp_output.exists():
                    try:
                        with open(temp_output, 'r') as f:
                            content = f.read()
                            
                        # Regex pattern for grepable output
                        # Pattern matches: 22/open/tcp, 80/open/tcp, etc.
                        port_pattern = r'(\d+)/open'
                        matches = re.findall(port_pattern, content)
                        
                        for port_str in matches:
                            try:
                                port = int(port_str)
                                if 1 <= port <= 65535:
                                    open_ports.add(port)
                            except ValueError:
                                continue
                                
                    except Exception as e:
                        return WorkflowResult(
                            success=False,
                            error=f"Failed to parse scan results: {str(e)}",
                            execution_time=time.time() - start_time
                        )
                
                # File automatically cleaned up when exiting context
                
                if not open_ports:
                    console.print("⚠️  No open ports found during fast scan")
                    return WorkflowResult(
                        success=True,
                        data={
                            "tool": "nmap-fast",
                            "target": target,
                            "open_ports": [],
                            "port_count": 0,
                            "scan_mode": "privileged" if is_root else "unprivileged",
                            "hostname_mappings": [],
                            "etc_hosts_updated": False
                        },
                        execution_time=time.time() - start_time
                    )
                
                sorted_ports = sorted(list(open_ports))
                console.print(f"✅ Fast scan found {len(sorted_ports)} open ports: {', '.join(map(str, sorted_ports[:10]))}{('...' if len(sorted_ports) > 10 else '')}")
                
                # Step 2: Quick hostname discovery using nmap on HTTP ports
                discovered_mappings = set()
                http_ports_found = [port for port in sorted_ports if port in self.common_http_ports]
                
                if http_ports_found:
                    console.print(f"🔍 Discovering hostnames on {len(http_ports_found)} HTTP ports using nmap...")
                    
                    # Quick curl check for redirects first
                    from workflows.core.command_logger import get_command_logger
                    for port in http_ports_found[:2]:  # Check first 2 ports
                        curl_cmd = f"curl -I -s -L --max-time 5 http://{target}:{port}/ | grep -i location"
                        get_command_logger().log_command("nmap_fast_01", curl_cmd)
                    
                    mappings = await self._nmap_hostname_discovery(target, http_ports_found[:3])  # Max 3 ports
                    discovered_mappings.update(mappings)
                
                # Step 3: Update /etc/hosts if we found hostnames and have sudo
                hosts_updated = False
                if discovered_mappings and is_root:
                    hosts_updated = await self._update_etc_hosts(discovered_mappings)
                
                return WorkflowResult(
                    success=True,
                    data={
                        "tool": "nmap-fast",
                        "target": target,
                        "open_ports": sorted_ports,
                        "port_count": len(sorted_ports),
                        "scan_mode": "privileged" if is_root else "unprivileged",
                        "hostname_mappings": [{"ip": ip, "hostname": hostname} for ip, hostname in discovered_mappings],
                        "etc_hosts_updated": hosts_updated
                    },
                    execution_time=time.time() - start_time
                )
            
        except FileNotFoundError:
            return WorkflowResult(
                success=False,
                error="nmap not found. Please install nmap first.",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                error=f"Fast port discovery failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _nmap_hostname_discovery(self, target: str, http_ports: List[int]) -> Set[Tuple[str, str]]:
        """Use nmap scripts to discover hostnames on HTTP ports"""
        mappings = set()
        
        try:
            # Use nmap with http scripts for hostname discovery
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.nmap', prefix=f'nmap_http_{target.replace(".", "_")}_', delete=True) as temp_file:
                temp_output = Path(temp_file.name)
                
                port_list = ','.join(map(str, http_ports))
                
                # Use nmap HTTP scripts to discover hostnames
                cmd = [
                    "nmap",
                    "-p", port_list,
                    "-sC",                    # Default scripts (includes http-title, http-headers)
                    "--script", "http-title,http-headers,http-methods,http-enum",
                    "-T4",                    # Fast timing
                    "--max-retries", "1",     # Quick retries
                    "--host-timeout", "30s",  # Don't hang
                    "-Pn",                    # Skip ping
                    "-oN", str(temp_output),  # Normal output to file
                    target
                ]
                
                # Log the actual command being executed
                from workflows.core.command_logger import get_command_logger
                get_command_logger().log_command("nmap_fast_01", " ".join(cmd))
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and temp_output.exists():
                    with open(temp_output, 'r') as f:
                        nmap_output = f.read()
                    
                    hostnames = self._extract_hostnames_from_nmap_output(nmap_output, target)
                    
                    # Show if no hostnames were found
                    if not hostnames:
                        console.print(f"  [dim]No hostnames discovered for {target}[/dim]")
                    
                    for hostname in hostnames:
                        ip = await self._resolve_hostname_fast(hostname)
                        if ip:
                            mappings.add((ip, hostname))
                        else:
                            mappings.add((target, hostname))
                            
        except Exception as e:
            console.print(f"  [dim]Hostname discovery error: {str(e)[:50]}[/dim]")
            
        return mappings
    
    def _extract_hostnames_from_nmap_output(self, nmap_output: str, target: str) -> List[str]:
        """Extract hostnames from nmap script output"""
        hostnames = []
        
        
        # Patterns to match hostnames in nmap output
        patterns = [
            # HTTP redirects (most common)
            r'Location:\s*https?://([^/\s<>]+)',
            # HTTP title
            r'http-title:\s*.*?([a-zA-Z0-9-]+\.(?:htb|local|com|net|org|io))',
            # href/src in HTML
            r'href=["\']https?://([^/\s"\'<>]+)',
            r'src=["\']https?://([^/\s"\'<>]+)',
            # HTB specific patterns
            r'([a-zA-Z0-9-]+\.htb)',
            r'([a-zA-Z0-9-]+\.local)',
            # Virtual host indicators
            r'Host:\s*([^"\'\s<>\r\n]+)',
            r'hostname["\']?\s*[:=]\s*["\']([^"\'<>\s]+)["\']'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, nmap_output, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                # Handle both string and tuple matches
                if isinstance(match, tuple):
                    hostname = match[0] if match else None
                else:
                    hostname = match
                
                if hostname and hostname != target and self._is_valid_hostname(hostname):
                    hostnames.append(hostname)
                    
        return list(set(hostnames))
    
    async def _resolve_hostname_fast(self, hostname: str) -> Optional[str]:
        """Fast hostname resolution with timeout"""
        try:
            process = await asyncio.create_subprocess_exec(
                'nslookup', hostname,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 2-second timeout for DNS resolution
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=2.0
            )
            
            if process.returncode == 0:
                output = stdout.decode()
                ip_pattern = r'Address: (\d+\.\d+\.\d+\.\d+)'
                match = re.search(ip_pattern, output)
                if match:
                    return match.group(1)
                    
        except asyncio.TimeoutError:
            try:
                process.kill()
                await process.wait()
            except:
                pass
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
                
            # Skip if ipcrawler entries already exist
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