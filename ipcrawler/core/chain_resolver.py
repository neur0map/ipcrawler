"""
Chain Resolver for IPCrawler
Handles template chaining, variable passing, and conditional execution.
"""

import socket
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class DiscoveredDomain:
    """Represents a discovered domain/vhost."""
    domain: str
    ip: str
    status_code: int
    size: int
    
    def __str__(self):
        return f"{self.domain} ({self.status_code})"


class ChainResolver:
    """Resolves template chaining and variable passing between templates."""
    
    def __init__(self):
        self.discovered_domains: List[DiscoveredDomain] = []
        self.chain_variables: Dict[str, Any] = {}
    
    def resolve_target_ip(self, target: str) -> Optional[str]:
        """Resolve target hostname to IP address."""
        try:
            # Remove protocol if present
            if target.startswith(('http://', 'https://')):
                target = target.split('://', 1)[1]
            
            # Remove port if present
            if ':' in target:
                target = target.split(':', 1)[0]
            
            # Remove path if present
            if '/' in target:
                target = target.split('/', 1)[0]
            
            # Check if it's already an IP address
            if self._is_ip_address(target):
                return target
            
            # Resolve hostname to IP
            ip_address = socket.gethostbyname(target)
            return ip_address
            
        except (socket.gaierror, socket.error):
            return None
    
    def _is_ip_address(self, target: str) -> bool:
        """Check if target is an IP address."""
        try:
            socket.inet_aton(target)
            return True
        except socket.error:
            return False
    
    def extract_discovered_domains(self, results: List[Any], target_ip: str) -> List[DiscoveredDomain]:
        """Extract discovered domains from vhost discovery results."""
        discovered_domains = []
        
        for result in results:
            if not hasattr(result, 'output') or not result.output:
                continue
            
            # Parse gobuster vhost output
            if 'gobuster' in getattr(result, 'tool', '').lower():
                domains = self._parse_gobuster_vhost_output(result.output, target_ip)
                discovered_domains.extend(domains)
            
            # Parse curl vhost output
            elif 'curl' in getattr(result, 'tool', '').lower():
                domains = self._parse_curl_vhost_output(result.output, target_ip)
                discovered_domains.extend(domains)
        
        # Remove duplicates
        seen = set()
        unique_domains = []
        for domain in discovered_domains:
            key = (domain.domain, domain.ip)
            if key not in seen:
                seen.add(key)
                unique_domains.append(domain)
        
        self.discovered_domains = unique_domains
        return unique_domains
    
    def _parse_gobuster_vhost_output(self, output: str, target_ip: str) -> List[DiscoveredDomain]:
        """Parse gobuster vhost output for discovered domains."""
        domains = []
        
        # Gobuster vhost output format: "Found: subdomain.example.com (Status: 200) [Size: 1234]"
        pattern = r'Found:\\s+([^\\s]+)\\s+\\(Status:\\s+(\\d+)\\)\\s+\\[Size:\\s+(\\d+)\\]'
        
        for line in output.split('\\n'):
            match = re.search(pattern, line)
            if match:
                domain = match.group(1)
                status_code = int(match.group(2))
                size = int(match.group(3))
                
                domains.append(DiscoveredDomain(
                    domain=domain,
                    ip=target_ip,
                    status_code=status_code,
                    size=size
                ))
        
        return domains
    
    def _parse_curl_vhost_output(self, output: str, target_ip: str) -> List[DiscoveredDomain]:
        """Parse curl vhost output for discovered domains."""
        domains = []
        
        # Look for VHOST CHECK headers and status codes
        lines = output.split('\\n')
        current_domain = None
        current_status = None
        current_size = None
        
        for line in lines:
            line = line.strip()
            
            # Extract domain from Host header
            if 'Host:' in line:
                host_match = re.search(r'Host:\\s+([^\\s]+)', line)
                if host_match:
                    current_domain = host_match.group(1)
            
            # Extract status code
            if 'Status:' in line:
                status_match = re.search(r'Status:\\s+(\\d+)', line)
                if status_match:
                    current_status = int(status_match.group(1))
            
            # Extract size
            if 'Size:' in line:
                size_match = re.search(r'Size:\\s+(\\d+)', line)
                if size_match:
                    current_size = int(size_match.group(1))
            
            # If we have all components, create domain entry
            if current_domain and current_status and current_size:
                # Only add if status indicates success or interesting response
                if current_status in [200, 301, 302, 403]:
                    domains.append(DiscoveredDomain(
                        domain=current_domain,
                        ip=target_ip,
                        status_code=current_status,
                        size=current_size
                    ))
                
                # Reset for next domain
                current_domain = None
                current_status = None
                current_size = None
        
        return domains
    
    def generate_chain_variables(self, discovered_domains: List[DiscoveredDomain]) -> Dict[str, Any]:
        """Generate chain variables from discovered domains."""
        chain_variables = {}
        
        if not discovered_domains:
            return chain_variables
        
        # Generate domain lists
        all_domains = [d.domain for d in discovered_domains]
        success_domains = [d.domain for d in discovered_domains if d.status_code == 200]
        redirect_domains = [d.domain for d in discovered_domains if d.status_code in [301, 302]]
        
        # Add various domain lists
        chain_variables.update({
            'discovered_domains': all_domains,
            'success_domains': success_domains,
            'redirect_domains': redirect_domains,
            'domain_count': len(all_domains),
            'success_count': len(success_domains),
            'redirect_count': len(redirect_domains)
        })
        
        # Add individual domain variables (first 10 domains)
        for i, domain in enumerate(all_domains[:10]):
            chain_variables[f'domain_{i+1}'] = domain
        
        # Add primary domain (first successful domain or first domain)
        if success_domains:
            chain_variables['primary_domain'] = success_domains[0]
        elif all_domains:
            chain_variables['primary_domain'] = all_domains[0]
        
        # Add formatted domain lists for tools
        chain_variables.update({
            'domains_comma': ','.join(all_domains),
            'domains_space': ' '.join(all_domains),
            'domains_newline': '\\n'.join(all_domains)
        })
        
        self.chain_variables = chain_variables
        return chain_variables
    
    def resolve_variables(self, template_args: List[str], chain_variables: Dict[str, Any]) -> List[str]:
        """Resolve chain variables in template arguments."""
        if not chain_variables:
            return template_args
        
        resolved_args = []
        
        for arg in template_args:
            if isinstance(arg, str):
                # Replace chain variables
                resolved_arg = arg
                for var_name, var_value in chain_variables.items():
                    placeholder = f'{{{{chain.{var_name}}}}}'
                    if placeholder in resolved_arg:
                        resolved_arg = resolved_arg.replace(placeholder, str(var_value))
                
                resolved_args.append(resolved_arg)
            else:
                resolved_args.append(arg)
        
        return resolved_args
    
    def should_execute_template(self, template_name: str, chain_variables: Dict[str, Any]) -> bool:
        """Determine if a template should be executed based on chain conditions."""
        # For now, execute all templates
        # This can be extended to support conditional execution based on:
        # - Template metadata (e.g., "requires_domains": true)
        # - Chain variable values (e.g., only run if domains discovered)
        # - Template dependencies (e.g., template A must run before template B)
        
        return True
    
    def get_execution_order(self, templates: List[Any]) -> List[Any]:
        """Get best execution order for templates based on dependencies."""
        # For now, return templates in original order
        # This can be extended to support:
        # - Dependency resolution
        # - Parallel execution groups
        # - Priority-based ordering
        
        return templates
    
    def reset(self):
        """Reset chain resolver state."""
        self.discovered_domains.clear()
        self.chain_variables.clear()