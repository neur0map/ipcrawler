import asyncio
import os
import re
import time
import tempfile
from typing import List, Optional, Callable
from pathlib import Path

from rich.console import Console

from workflows.core.base import BaseWorkflow, WorkflowResult

console = Console()


class NmapFastScanner(BaseWorkflow):
    """Fast nmap scanner for accurate port discovery"""
    
    def __init__(self):
        super().__init__("nmap-fast")
    
    def validate_input(self, target: str, **kwargs) -> bool:
        """Validate input parameters"""
        if not target or not target.strip():
            return False
        return True
    
    def _is_root(self) -> bool:
        """Check if running with root privileges"""
        return os.geteuid() == 0
    
    
    async def execute(self, target: str, progress_callback: Optional[Callable] = None, **kwargs) -> WorkflowResult:
        """Execute fast nmap scan for port discovery"""
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
                
                # Build fast nmap command for port discovery
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
                        "-n",                   # No DNS resolution
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
                        "-n",                   # No DNS resolution
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
                
                # Read output with proper async handling
                if progress_callback:
                    # Read stdout line by line for real-time updates
                    stdout_lines = []
                    stderr_task = asyncio.create_task(process.stderr.read())
                    
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        line_str = line.decode().strip()
                        stdout_lines.append(line_str)
                        
                        # Check for discovered open ports
                        if "Discovered open port" in line_str:
                            match = re.search(r'Discovered open port (\d+)/(\w+)', line_str)
                            if match:
                                port, protocol = match.groups()
                                progress_callback(int(port), protocol)
                    
                    # Wait for both streams and process
                    stderr_data = await stderr_task
                    await process.wait()
                    stdout_data = '\n'.join(stdout_lines)
                    stderr_data = stderr_data.decode()
                else:
                    # No callback, just get all output
                    stdout_data, stderr_data = await process.communicate()
                    stdout_data = stdout_data.decode()
                    stderr_data = stderr_data.decode()
                
                if process.returncode != 0:
                    return WorkflowResult(
                        success=False,
                        error=f"Fast nmap scan failed: {stderr_data}",
                        execution_time=time.time() - start_time
                    )
                
                # Parse grepable output to extract open ports
                open_ports = set()
                
                if temp_output.exists():
                    try:
                        with open(temp_output, 'r') as f:
                            content = f.read()
                            
                        # Extract ports using regex pattern for grepable output
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
                            "scan_mode": "privileged" if is_root else "unprivileged"
                        },
                        execution_time=time.time() - start_time
                    )
                
                sorted_ports = sorted(list(open_ports))
                console.print(f"✅ Fast scan found {len(sorted_ports)} open ports: {', '.join(map(str, sorted_ports[:10]))}{('...' if len(sorted_ports) > 10 else '')}")
                
                return WorkflowResult(
                    success=True,
                    data={
                        "tool": "nmap-fast",
                        "target": target,
                        "open_ports": sorted_ports,
                        "port_count": len(sorted_ports),
                        "scan_mode": "privileged" if is_root else "unprivileged"
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