"""Subdomain Discovery Module for HTTP_03 Workflow

Handles fast subdomain enumeration using external tools like subfinder and dnsx,
running in parallel with the main HTTP workflow to avoid delays.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess

# Utils
from src.core.utils.debugging import debug_print
from workflows.core.command_logger import get_command_logger


class SubdomainDiscovery:
    """Handles fast subdomain enumeration using external tools"""
    
    def __init__(self):
        """Initialize subdomain discovery"""
        self._check_tools_availability()
    
    def _check_tools_availability(self) -> None:
        """Check if required tools are available"""
        self.subfinder_available = self._is_tool_available('subfinder')
        self.dnsx_available = self._is_tool_available('dnsx')
        
        if not self.subfinder_available:
            debug_print("subfinder not found - subdomain discovery will be limited", level="WARNING")
        if not self.dnsx_available:
            debug_print("dnsx not found - DNS validation will be limited", level="WARNING")
    
    def _is_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH"""
        try:
            result = subprocess.run(['which', tool], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def discover_subdomains_parallel(self, target: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Discover subdomains in parallel with main HTTP workflow
        
        Args:
            target: Target domain/IP to discover subdomains for
            timeout: Maximum time in seconds for discovery
            
        Returns:
            Dictionary with discovered subdomains and metadata
        """
        # Skip if target is an IP address
        if self._is_ip_address(target):
            debug_print(f"Skipping subdomain discovery for IP address: {target}")
            return {
                'subdomains': [],
                'total_found': 0,
                'method': 'skipped',
                'reason': 'IP address provided'
            }
        
        debug_print(f"Starting parallel subdomain discovery for {target}")
        
        # Run discovery methods in parallel
        tasks = []
        
        if self.subfinder_available:
            tasks.append(self._run_subfinder(target, timeout))
        
        # Fallback method if subfinder not available
        if not self.subfinder_available:
            tasks.append(self._basic_subdomain_discovery(target))
        
        try:
            # Run all tasks with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            # Combine results
            all_subdomains = set()
            methods_used = []
            
            for result in results:
                if isinstance(result, dict) and 'subdomains' in result:
                    all_subdomains.update(result['subdomains'])
                    methods_used.append(result.get('method', 'unknown'))
                elif isinstance(result, Exception):
                    debug_print(f"Subdomain discovery error: {result}", level="WARNING")
            
            # Validate subdomains with dnsx if available
            validated_subdomains = []
            if self.dnsx_available and all_subdomains:
                validated_subdomains = await self._validate_with_dnsx(list(all_subdomains))
            else:
                validated_subdomains = list(all_subdomains)
            
            return {
                'subdomains': validated_subdomains,
                'total_found': len(validated_subdomains),
                'method': '+'.join(methods_used),
                'tools_used': {
                    'subfinder': self.subfinder_available,
                    'dnsx': self.dnsx_available
                }
            }
            
        except asyncio.TimeoutError:
            debug_print(f"Subdomain discovery timed out after {timeout}s", level="WARNING")
            return {
                'subdomains': [],
                'total_found': 0,
                'method': 'timeout',
                'error': f'Discovery timed out after {timeout}s'
            }
    
    async def _run_subfinder(self, target: str, timeout: int = 300) -> Dict[str, Any]:
        """Run subfinder for subdomain enumeration"""
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp_file:
                output_file = tmp_file.name
            
            # Build subfinder command
            cmd = [
                'subfinder',
                '-d', target,
                '-o', output_file,
                '-silent',  # Silent mode for clean output
                '-all',     # Use all sources
                '-timeout', str(min(timeout - 30, 180))  # Leave buffer time
            ]
            
            # Log the command being executed
            get_command_logger().log_command("http_03", ' '.join(cmd))
            
            debug_print(f"Running subfinder for {target}")
            
            # Execute subfinder
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout - 10
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise asyncio.TimeoutError("subfinder timed out")
            
            # Read results from output file
            subdomains = []
            try:
                with open(output_file, 'r') as f:
                    subdomains = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                debug_print("Subfinder output file not found", level="WARNING")
            finally:
                # Clean up temporary file
                try:
                    Path(output_file).unlink()
                except:
                    pass
            
            # Filter out invalid subdomains
            valid_subdomains = [sub for sub in subdomains if self._is_valid_subdomain(sub, target)]
            
            debug_print(f"Subfinder found {len(valid_subdomains)} subdomains for {target}")
            
            return {
                'subdomains': valid_subdomains,
                'method': 'subfinder',
                'total_found': len(valid_subdomains)
            }
            
        except Exception as e:
            debug_print(f"Subfinder execution failed: {e}", level="WARNING")
            return {
                'subdomains': [],
                'method': 'subfinder_failed',
                'error': str(e)
            }
    
    async def _validate_with_dnsx(self, subdomains: List[str]) -> List[str]:
        """Validate subdomains using dnsx"""
        if not subdomains:
            return []
        
        try:
            # Create temporary file for input
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                tmp_file.write('\n'.join(subdomains))
                input_file = tmp_file.name
            
            # Build dnsx command
            cmd = [
                'dnsx',
                '-l', input_file,
                '-silent',
                '-resp',  # Include response
                '-a',     # A records
                '-timeout', '5'
            ]
            
            # Log the command being executed
            get_command_logger().log_command("http_03", ' '.join(cmd))
            
            debug_print(f"Validating {len(subdomains)} subdomains with dnsx")
            
            # Execute dnsx
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse dnsx output
            validated = []
            if stdout:
                lines = stdout.decode().strip().split('\n')
                for line in lines:
                    if line.strip() and '[' in line:  # dnsx format: domain [ip]
                        domain = line.split('[')[0].strip()
                        if domain:
                            validated.append(domain)
            
            # Clean up temporary file
            try:
                Path(input_file).unlink()
            except:
                pass
            
            debug_print(f"dnsx validated {len(validated)} subdomains")
            return validated
            
        except Exception as e:
            debug_print(f"dnsx validation failed: {e}", level="WARNING")
            return subdomains  # Return original list if validation fails
    
    async def _basic_subdomain_discovery(self, target: str) -> Dict[str, Any]:
        """Basic subdomain discovery when subfinder is not available"""
        common_subdomains = [
            'www', 'mail', 'ftp', 'admin', 'api', 'dev', 'staging', 'test',
            'portal', 'app', 'web', 'secure', 'vpn', 'remote', 'support',
            'blog', 'shop', 'store', 'cdn', 'media', 'static', 'assets',
            'm', 'mobile', 'wap', 'beta', 'alpha', 'demo', 'docs'
        ]
        
        discovered = []
        
        # Test common subdomains
        for subdomain in common_subdomains:
            full_domain = f"{subdomain}.{target}"
            if await self._test_subdomain_exists(full_domain):
                discovered.append(full_domain)
        
        return {
            'subdomains': discovered,
            'method': 'basic_patterns',
            'total_found': len(discovered)
        }
    
    async def _test_subdomain_exists(self, subdomain: str) -> bool:
        """Test if a subdomain exists using DNS resolution"""
        try:
            import socket
            await asyncio.get_event_loop().run_in_executor(
                None, socket.gethostbyname, subdomain
            )
            return True
        except socket.gaierror:
            return False
        except Exception:
            return False
    
    def _is_ip_address(self, target: str) -> bool:
        """Check if target is an IP address"""
        import re
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        
        return bool(re.match(ipv4_pattern, target) or re.match(ipv6_pattern, target))
    
    def _is_valid_subdomain(self, subdomain: str, base_domain: str) -> bool:
        """Validate that subdomain is related to base domain"""
        if not subdomain or not base_domain:
            return False
        
        # Must end with base domain
        if not subdomain.endswith('.' + base_domain) and subdomain != base_domain:
            return False
        
        # Basic format validation
        if len(subdomain) > 255:
            return False
        
        # No wildcard certificates
        if subdomain.startswith('*'):
            return False
        
        return True
    
    async def get_discovery_status(self) -> Dict[str, Any]:
        """Get status of subdomain discovery tools and capabilities"""
        return {
            'subfinder_available': self.subfinder_available,
            'dnsx_available': self.dnsx_available,
            'capabilities': {
                'passive_enumeration': self.subfinder_available,
                'dns_validation': self.dnsx_available,
                'basic_patterns': True
            },
            'recommended_setup': [
                'go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest',
                'go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest'
            ] if not (self.subfinder_available and self.dnsx_available) else []
        }