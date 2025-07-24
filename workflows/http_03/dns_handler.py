"""
DNS enumeration and subdomain discovery for HTTP scanner workflow.

This module handles DNS record queries, subdomain discovery, zone transfers,
and common subdomain pattern testing.
"""

import asyncio
import socket
from typing import Dict, Any, List, Tuple
from .models import DNSRecord
from .config import get_scanner_config
from utils.debug import debug_print


class DNSHandler:
    """DNS enumeration and subdomain discovery handler"""
    
    def __init__(self):
        self.config = get_scanner_config()
    
    async def enumerate_dns(self, target: str) -> Dict[str, Any]:
        """
        Perform comprehensive DNS enumeration.
        
        Args:
            target: Target domain or hostname
            
        Returns:
            Dictionary with DNS records and discovered subdomains
        """
        dns_info = {
            'records': [],
            'subdomains': []
        }
        
        if not self.config.deps_available:
            debug_print("DNS dependencies not available, skipping DNS enumeration")
            return dns_info
        
        try:
            import dns.resolver
            import dns.zone
            import dns.query
            
            resolver = dns.resolver.Resolver()
            
            # Query multiple record types
            dns_info['records'] = await self._query_dns_records(resolver, target)
            
            # Try zone transfer
            zone_subdomains = await self._attempt_zone_transfer(resolver, target)
            dns_info['subdomains'].extend(zone_subdomains)
            
            # Common subdomain patterns
            pattern_subdomains = await self._test_common_subdomains(target)
            dns_info['subdomains'].extend(pattern_subdomains)
            
            # Remove duplicates
            dns_info['subdomains'] = list(set(dns_info['subdomains']))
            
        except Exception as e:
            debug_print(f"DNS enumeration error: {e}", level="WARNING")
        
        return dns_info
    
    async def _query_dns_records(self, resolver, target: str) -> List[DNSRecord]:
        """
        Query multiple DNS record types.
        
        Args:
            resolver: DNS resolver instance
            target: Target domain
            
        Returns:
            List of DNS records
        """
        records = []
        record_types = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA']
        
        for record_type in record_types:
            try:
                answers = resolver.resolve(target, record_type)
                for rdata in answers:
                    records.append(DNSRecord(
                        type=record_type,
                        value=str(rdata)
                    ))
                debug_print(f"Found {len(answers)} {record_type} records for {target}")
            except Exception as e:
                debug_print(f"No {record_type} records for {target}: {e}")
                continue
        
        return records
    
    async def _attempt_zone_transfer(self, resolver, target: str) -> List[str]:
        """
        Attempt DNS zone transfer to discover subdomains.
        
        Args:
            resolver: DNS resolver instance
            target: Target domain
            
        Returns:
            List of discovered subdomains
        """
        subdomains = []
        
        try:
            import dns.zone
            import dns.query
            
            # Get NS records first
            ns_records = resolver.resolve(target, 'NS')
            debug_print(f"Found {len(ns_records)} NS records for zone transfer attempt")
            
            for ns in ns_records:
                try:
                    # Attempt zone transfer
                    zone = dns.zone.from_xfr(dns.query.xfr(str(ns), target))
                    debug_print(f"Successful zone transfer from {ns}")
                    
                    for name, node in zone.nodes.items():
                        subdomain = str(name) + '.' + target
                        if subdomain not in subdomains and subdomain != target:
                            subdomains.append(subdomain)
                            debug_print(f"Zone transfer discovered: {subdomain}")
                            
                except Exception as e:
                    debug_print(f"Zone transfer failed for {ns}: {e}")
                    continue
                    
        except Exception as e:
            debug_print(f"Zone transfer enumeration failed: {e}")
        
        return subdomains
    
    async def _test_common_subdomains(self, target: str) -> List[str]:
        """
        Test common subdomain patterns.
        
        Args:
            target: Target domain
            
        Returns:
            List of discovered subdomains
        """
        subdomains = []
        
        # Get common patterns from database
        common_patterns = []
        if self.config.scanner_config_manager:
            try:
                common_patterns = self.config.scanner_config_manager.get_common_subdomain_patterns()
            except Exception as e:
                debug_print(f"Could not get subdomain patterns from database: {e}", level="WARNING")
        
        # Fallback patterns if database unavailable
        if not common_patterns:
            common_patterns = [
                'www', 'mail', 'ftp', 'admin', 'portal', 'api', 'dev',
                'staging', 'test', 'prod', 'vpn', 'remote', 'secure',
                'app', 'web', 'blog', 'shop', 'store', 'support',
                'help', 'docs', 'cdn', 'static', 'assets', 'media',
                'images', 'img', 'upload', 'download', 'files',
                'beta', 'alpha', 'demo', 'preview', 'sandbox'
            ]
        
        debug_print(f"Testing {len(common_patterns)} common subdomain patterns")
        
        # Create tasks for concurrent testing
        tasks = []
        for pattern in common_patterns:
            subdomain = f"{pattern}.{target}"
            tasks.append(self._check_subdomain(subdomain))
        
        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(20)  # Limit concurrent DNS queries
        
        async def test_with_semaphore(task):
            async with semaphore:
                return await task
        
        limited_tasks = [test_with_semaphore(task) for task in tasks]
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        # Process results
        for subdomain, exists in results:
            if isinstance(exists, bool) and exists:
                subdomains.append(subdomain)
                debug_print(f"Subdomain discovered: {subdomain}")
            elif isinstance(exists, Exception):
                debug_print(f"Error testing subdomain {subdomain}: {exists}")
        
        return subdomains
    
    async def _check_subdomain(self, subdomain: str) -> Tuple[str, bool]:
        """
        Check if a subdomain exists via DNS resolution.
        
        Args:
            subdomain: Subdomain to test
            
        Returns:
            Tuple of (subdomain, exists)
        """
        try:
            # Use asyncio to make DNS lookup non-blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, socket.gethostbyname, subdomain)
            return subdomain, True
        except socket.gaierror:
            return subdomain, False
        except Exception as e:
            debug_print(f"DNS lookup error for {subdomain}: {e}")
            return subdomain, False
    
    def get_subdomain_patterns(self) -> List[str]:
        """
        Get subdomain patterns from configuration.
        
        Returns:
            List of subdomain patterns
        """
        if self.config.scanner_config_manager:
            try:
                return self.config.scanner_config_manager.get_common_subdomains()
            except Exception as e:
                debug_print(f"Could not get subdomain patterns: {e}", level="WARNING")
        
        # Fallback patterns
        return [
            "www", "mail", "admin", "api", "portal", "secure", "app", "web",
            "dev", "staging", "test", "prod", "beta", "alpha", "demo"
        ]
    
    async def reverse_dns_lookup(self, ip_address: str) -> List[str]:
        """
        Perform reverse DNS lookup to find hostnames.
        
        Args:
            ip_address: IP address to lookup
            
        Returns:
            List of hostnames
        """
        hostnames = []
        
        try:
            loop = asyncio.get_event_loop()
            hostname, aliaslist, ipaddrlist = await loop.run_in_executor(
                None, socket.gethostbyaddr, ip_address
            )
            
            if hostname:
                hostnames.append(hostname)
                debug_print(f"Reverse DNS found: {hostname}")
            
            # Add aliases
            for alias in aliaslist:
                if alias and alias not in hostnames:
                    hostnames.append(alias)
                    debug_print(f"Reverse DNS alias found: {alias}")
                    
        except socket.herror:
            debug_print(f"No reverse DNS for {ip_address}")
        except Exception as e:
            debug_print(f"Reverse DNS lookup error for {ip_address}: {e}")
        
        return hostnames
    
    async def get_dns_info_fallback(self, target: str) -> Dict[str, Any]:
        """
        Fallback DNS enumeration using system tools.
        
        Args:
            target: Target domain
            
        Returns:
            Basic DNS information
        """
        import subprocess
        import re
        
        dns_info = {
            'records': [],
            'subdomains': []
        }
        
        try:
            # Basic DNS lookup using nslookup
            result = subprocess.run(
                ["nslookup", target],
                capture_output=True,
                text=True,
                timeout=self.config.get_timeout_settings()['dns']
            )
            
            if result.returncode == 0:
                # Extract IP addresses
                ips = re.findall(r'Address: ([\\d.]+)', result.stdout)
                for ip in ips:
                    dns_info['records'].append({
                        "type": "A",
                        "value": ip
                    })
                debug_print(f"Fallback DNS found {len(ips)} A records")
                
        except Exception as e:
            debug_print(f"Fallback DNS lookup failed: {e}")
        
        return dns_info