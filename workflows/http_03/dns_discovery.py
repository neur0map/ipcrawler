"""DNS Discovery Module for HTTP_03 Workflow

Handles DNS enumeration, subdomain discovery, and hostname validation.
"""

import asyncio
import socket
from typing import Dict, List, Any, Tuple
from .models import DNSRecord

# DNS dependencies
try:
    import dns.resolver
    import dns.zone
    import dns.query
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


class DNSDiscovery:
    """Handles DNS enumeration and subdomain discovery"""
    
    def __init__(self):
        self.common_patterns = [
            'www', 'mail', 'ftp', 'admin', 'portal', 'api', 'dev',
            'staging', 'test', 'prod', 'vpn', 'remote', 'secure'
        ]
    
    async def enumerate_dns(self, target: str) -> Dict[str, Any]:
        """Perform comprehensive DNS enumeration
        
        Args:
            target: The target domain/IP to enumerate
            
        Returns:
            Dictionary with 'records' and 'subdomains' lists
        """
        dns_info = {
            'records': [],
            'subdomains': []
        }
        
        if not DNS_AVAILABLE:
            return dns_info
        
        try:
            resolver = dns.resolver.Resolver()
            
            # Query multiple record types
            record_types = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA']
            
            for record_type in record_types:
                try:
                    answers = resolver.resolve(target, record_type)
                    for rdata in answers:
                        dns_info['records'].append(DNSRecord(
                            type=record_type,
                            value=str(rdata)
                        ))
                except:
                    continue
            
            # Try zone transfer
            await self._attempt_zone_transfer(target, resolver, dns_info)
            
            # Common subdomain patterns (no wordlist)
            discovered_subdomains = await self._discover_common_subdomains(target)
            dns_info['subdomains'].extend(discovered_subdomains)
                    
        except Exception:
            pass
            
        return dns_info
    
    async def _attempt_zone_transfer(self, target: str, resolver, dns_info: Dict) -> None:
        """Attempt DNS zone transfer"""
        try:
            ns_records = resolver.resolve(target, 'NS')
            for ns in ns_records:
                try:
                    zone = dns.zone.from_xfr(dns.query.xfr(str(ns), target))
                    for name, node in zone.nodes.items():
                        subdomain = str(name) + '.' + target
                        if subdomain not in dns_info['subdomains']:
                            dns_info['subdomains'].append(subdomain)
                except:
                    continue
        except:
            pass
    
    async def _discover_common_subdomains(self, target: str) -> List[str]:
        """Discover subdomains using common patterns"""
        tasks = []
        for pattern in self.common_patterns:
            subdomain = f"{pattern}.{target}"
            tasks.append(self._check_subdomain(subdomain))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        discovered = []
        for subdomain, exists in results:
            if isinstance(exists, bool) and exists:
                discovered.append(subdomain)
        
        return discovered
    
    async def _check_subdomain(self, subdomain: str) -> Tuple[str, bool]:
        """Check if subdomain exists using DNS resolution
        
        Args:
            subdomain: The subdomain to check
            
        Returns:
            Tuple of (subdomain, exists_boolean)
        """
        try:
            socket.gethostbyname(subdomain)
            return subdomain, True
        except:
            return subdomain, False
    
    def build_hostname_list(self, target: str, discovered_hostnames: List[str], 
                           subdomains: List[str]) -> List[str]:
        """Build comprehensive list of hostnames to test
        
        Args:
            target: Original target
            discovered_hostnames: Hostnames from nmap/other sources
            subdomains: DNS discovered subdomains
            
        Returns:
            List of unique hostnames to test
        """
        hostnames = [target]  # Start with original target
        
        # Add discovered hostnames from nmap
        hostnames.extend(discovered_hostnames)
        
        # Add DNS subdomains
        hostnames.extend(subdomains)
        
        # Generate additional hostname patterns based on target
        if '.' in target and not target.replace('.', '').isdigit():  # If it's a domain, not IP
            base_domain = target
            additional_patterns = [
                f"www.{base_domain}",
                f"mail.{base_domain}",
                f"admin.{base_domain}",
                f"api.{base_domain}",
                f"portal.{base_domain}",
                f"secure.{base_domain}",
                f"app.{base_domain}",
                f"web.{base_domain}",
                f"dev.{base_domain}",
                f"staging.{base_domain}",
                f"test.{base_domain}",
                f"prod.{base_domain}"
            ]
            hostnames.extend(additional_patterns)
        
        # Remove duplicates and empty strings, preserve order
        seen = set()
        unique_hostnames = []
        for hostname in hostnames:
            if hostname and hostname not in seen:
                seen.add(hostname)
                unique_hostnames.append(hostname)
        
        return unique_hostnames