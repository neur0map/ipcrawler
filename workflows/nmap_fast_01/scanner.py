import asyncio
import os
import re
import time
import tempfile
from typing import List, Optional, Set, Tuple
from pathlib import Path

from rich.console import Console

from workflows.core.base import BaseWorkflow, WorkflowResult
from src.core.utils.nmap_utils import is_root, build_fast_discovery_command, build_hostname_discovery_command
from src.core.utils.target_sanitizer import sanitize_target

console = Console()


class NmapFastScanner(BaseWorkflow):
    """Fast nmap scanner with integrated hostname discovery"""
    
    def __init__(self):
        super().__init__("nmap_fast")
        # Get HTTP ports from database with fallback
        try:
            from workflows.core.db_integration import get_common_http_ports
            self.common_http_ports = get_common_http_ports()
        except ImportError:
            # Fallback if database helper not available
            self.common_http_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
    
    def validate_input(self, target: str, **kwargs) -> bool:
        """Validate input parameters"""
        if not target or not target.strip():
            return False
        return True
    
    
    
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
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.gnmap', prefix=f'nmap_fast_{sanitize_target(target)}_', delete=True) as temp_file:
                temp_output = Path(temp_file.name)
                
                root_privileged = is_root()
                
                cmd = build_fast_discovery_command(target, str(temp_output), root_privileged)
                
                
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
                            "scan_mode": "privileged" if root_privileged else "unprivileged",
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
                
                # Step 3: Update /etc/hosts if we found hostnames
                hosts_updated = False
                if discovered_mappings:
                    if root_privileged:
                        hosts_updated = await self._update_etc_hosts(discovered_mappings)
                        if hosts_updated:
                            console.print(f"  [success]✓ Updated /etc/hosts with {len(discovered_mappings)} hostname mapping(s)[/success]")
                        else:
                            console.print(f"  [yellow]⚠ Failed to update /etc/hosts[/yellow]")
                    else:
                        console.print(f"  [yellow]⚠ Found {len(discovered_mappings)} hostname(s) but need root privileges to update /etc/hosts[/yellow]")
                        # Save to file for manual addition
                        hosts_file = await self._save_hosts_mappings(discovered_mappings, target)
                        if hosts_file:
                            console.print(f"  [cyan]→ Saved hostname mappings to: {hosts_file}[/cyan]")
                            console.print(f"  [dim]  Run: sudo cat {hosts_file} >> /etc/hosts[/dim]")
                        
                        # Display the mappings for manual addition
                        console.print(f"  [dim]Manual /etc/hosts entries:[/dim]")
                        for ip, hostname in sorted(discovered_mappings):
                            console.print(f"  [dim]  {ip}\\t{hostname}[/dim]")
                else:
                    console.print(f"  [dim]No hostname mappings discovered[/dim]")
                
                return WorkflowResult(
                    success=True,
                    data={
                        "tool": "nmap-fast",
                        "target": target,
                        "open_ports": sorted_ports,
                        "port_count": len(sorted_ports),
                        "scan_mode": "privileged" if root_privileged else "unprivileged",
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
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.nmap', prefix=f'nmap_http_{sanitize_target(target)}_', delete=True) as temp_file:
                temp_output = Path(temp_file.name)
                
                cmd = build_hostname_discovery_command(target, http_ports, str(temp_output))
                
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
                    
                    # Debug: Show scan output length for troubleshooting
                    console.print(f"  [dim]Nmap hostname scan completed ({len(nmap_output)} chars output)[/dim]")
                    
                    # Optional: Save nmap output for debugging (uncomment if needed)
                    # self._save_debug_output(nmap_output, target, http_ports)
                    
                    hostnames = self._extract_hostnames_from_nmap_output(nmap_output, target)
                    
                    # Show results with better context
                    if not hostnames and len(nmap_output.strip()) > 50:
                        console.print(f"  [yellow]No hostnames discovered for {target} on ports {http_ports}[/yellow]")
                        # Debug: Show first few lines of output to help diagnose
                        output_preview = '\n'.join(nmap_output.split('\n')[:3])
                        console.print(f"  [dim]Scan output preview: {output_preview[:100]}...[/dim]")
                    elif hostnames:
                        console.print(f"  [success]✓ Discovered {len(hostnames)} hostname(s): {', '.join(hostnames)}[/success]")
                    elif len(nmap_output.strip()) <= 50:
                        console.print(f"  [dim]Hostname scan produced minimal output, likely no HTTP services responding[/dim]")
                    
                    for hostname in hostnames:
                        ip = await self._resolve_hostname_fast(hostname)
                        if ip:
                            mappings.add((ip, hostname))
                            console.print(f"  [success]  → {hostname} resolves to {ip}[/success]")
                        else:
                            mappings.add((target, hostname))
                            console.print(f"  [yellow]  → {hostname} (no DNS resolution, mapped to {target})[/yellow]")
                else:
                    # If the nmap command failed, provide detailed error info
                    console.print(f"  [red]Hostname discovery scan failed (exit code: {process.returncode})[/red]")
                    if stderr:
                        stderr_str = stderr.decode('utf-8', errors='ignore')
                        console.print(f"  [dim]Error: {stderr_str[:150]}[/dim]")
                    if stdout:
                        stdout_str = stdout.decode('utf-8', errors='ignore')
                        if stdout_str.strip():
                            console.print(f"  [dim]Output: {stdout_str[:100]}[/dim]")
                            
        except Exception as e:
            console.print(f"  [dim]Hostname discovery error: {str(e)}[/dim]")
            
        return mappings
    
    def _extract_hostnames_from_nmap_output(self, nmap_output: str, target: str) -> List[str]:
        """Extract hostnames from nmap script output"""
        hostnames = []
        
        # Universal patterns to match ANY hostname in nmap output, prioritized by reliability
        patterns = [
            # SSL Certificate Subject Alternative Names (most reliable)
            r'DNS:([a-zA-Z0-9.-]+)',
            r'Subject Alternative Name:\s*DNS:([a-zA-Z0-9.-]+)',
            
            # HTTP redirects (very reliable)
            r'Location:\s*https?://([^/\s<>\r\n]+)',
            r'Redirects to:\s*https?://([^/\s<>\r\n]+)',
            
            # HTTP headers (nmap script output format)
            r'^\s*\|\s*Host:\s*([a-zA-Z0-9.-]+)',  # Host header in nmap script format
            r'Host:\s*([a-zA-Z0-9.-]+)',
            r'server[:\s]*([a-zA-Z0-9.-]+)',
            
            # Nmap HTTP script specific patterns
            r'http-headers:.*?Host:\s*([a-zA-Z0-9.-]+)',
            r'http-methods:.*?Host:\s*([a-zA-Z0-9.-]+)',
            r'\|\s*Host:\s*([a-zA-Z0-9.-]+)',  # Script output with pipe format
            
            # SSL Certificate Common Name and Subject
            r'commonName=([a-zA-Z0-9.-]+)',
            r'Subject:\s*.*?CN=([a-zA-Z0-9.-]+)',
            r'CN=([a-zA-Z0-9.-]+)',
            
            # HTTP title with ANY domain pattern
            r'http-title:\s*.*?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
            r'<title>.*?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}).*?</title>',
            
            # href/src in HTML content
            r'href=["\']https?://([^/\s"\'<>\r\n]+)',
            r'src=["\']https?://([^/\s"\'<>\r\n]+)',
            
            # Virtual host and config indicators
            r'vhost["\']?\s*[:=]\s*["\']([^"\'<>\s]+)["\']',
            r'hostname["\']?\s*[:=]\s*["\']([^"\'<>\s]+)["\']',
            r'domain["\']?\s*[:=]\s*["\']([^"\'<>\s]+)["\']',
            
            # JavaScript and config references
            r'var\s+host\s*=\s*["\']([^"\'<>\s]+)["\']',
            r'hostname["\']?\s*:\s*["\']([^"\'<>\s]+)["\']',
            
            # Meta tags and content with ANY domain
            r'<meta[^>]+content=["\']([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']',
            
            # Generic domain patterns - catch ANY valid hostname format
            r'\b([a-zA-Z0-9-]{2,}\.[a-zA-Z0-9.-]{2,})\b',  # Any domain with subdomain
            r'\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,})\b',          # Basic domain.tld format
            
            # URLs and references with domains
            r'https?://([a-zA-Z0-9.-]+)',
            r'//([a-zA-Z0-9.-]+)',
            
            # Common hostname contexts
            r'hostname[:\s]*([a-zA-Z0-9.-]+)',
            r'domain[:\s]*([a-zA-Z0-9.-]+)',
            r'server[:\s]*([a-zA-Z0-9.-]+)',
        ]
        
        # Track which patterns find hostnames for debugging
        pattern_matches = {}
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, nmap_output, re.IGNORECASE | re.MULTILINE)
            if matches:
                pattern_matches[f"pattern_{i}"] = {"pattern": pattern, "matches": matches}
                
            for match in matches:
                # Handle both string and tuple matches
                if isinstance(match, tuple):
                    hostname = match[0] if match else None
                else:
                    hostname = match
                
                if hostname and hostname != target and self._is_valid_hostname(hostname):
                    hostnames.append(hostname)
                    console.print(f"  [cyan]  ✓ Pattern match: '{pattern[:50]}...' found '{hostname}'[/cyan]")
        
        # Debug: Show which patterns matched if any
        if pattern_matches and len(nmap_output) > 100:
            console.print(f"  [dim]Hostname extraction: {len(pattern_matches)} pattern(s) matched[/dim]")
                    
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
    
    async def _save_hosts_mappings(self, mappings: Set[Tuple[str, str]], target: str) -> Optional[str]:
        """Save hostname mappings to a file for manual addition to /etc/hosts"""
        try:
            import tempfile
            from datetime import datetime
            
            # Create a temporary file in the working directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ipcrawler_hosts_{sanitize_target(target)}_{timestamp}.txt"
            filepath = Path.cwd() / filename
            
            with open(filepath, 'w') as f:
                f.write(f"# IPCrawler discovered hostname mappings for {target}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write("# Add these entries to /etc/hosts:\n\n")
                
                for ip, hostname in sorted(mappings):
                    f.write(f"{ip}\t{hostname}\n")
                
                f.write(f"\n# End IPCrawler entries\n")
            
            return str(filepath)
            
        except Exception as e:
            console.print(f"  [dim]Failed to save hostname mappings: {e}[/dim]")
            return None
    
    def _save_debug_output(self, nmap_output: str, target: str, port_list: str):
        """Save nmap output for debugging hostname extraction"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nmap_debug_{sanitize_target(target)}_{timestamp}.txt"
            filepath = Path.cwd() / filename
            
            with open(filepath, 'w') as f:
                f.write(f"# Nmap output for hostname discovery debugging\n")
                f.write(f"# Target: {target}, Ports: {port_list}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
                f.write(nmap_output)
            
            console.print(f"  [dim]Debug: Saved nmap output to {filepath}[/dim]")
        except Exception as e:
            console.print(f"  [dim]Debug: Failed to save nmap output: {e}[/dim]")
            
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if hostname is valid"""
        if not hostname or len(hostname) > 255:
            return False
            
        # Skip obviously invalid hostnames
        if hostname.startswith('.') or hostname.endswith('.'):
            return False
            
        # Skip localhost and common non-targets (exact matches only)
        skip_hostnames = ['localhost', '127.0.0.1', '0.0.0.0', 'example.com', 'test.com']
        if hostname.lower() in skip_hostnames:
            return False
            
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
        
        # All valid hostnames are accepted - no TLD restrictions
        # This allows discovery of ANY hostname structure
        return True