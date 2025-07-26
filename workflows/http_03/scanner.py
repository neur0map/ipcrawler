"""Advanced HTTP Scanner with modular components"""
import asyncio
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from workflows.core.base import BaseWorkflow, WorkflowResult
from .models import HTTPScanResult
from src.core.utils.debugging import debug_print

# Import modular components
from .dns_discovery import DNSDiscovery
from .http_service import HTTPServiceScanner
from .path_discovery import PathDiscoveryEngine
from .security_analyzer import SecurityAnalyzer
from .technology_detector import TechnologyDetector
from .fallback_scanner import FallbackScanner
from .subdomain_discovery import SubdomainDiscovery

def check_dependencies():
    """Check if HTTP scanner dependencies are available at runtime"""
    try:
        import httpx
        import dns.resolver
        return True
    except ImportError:
        return False


class HTTPAdvancedScanner(BaseWorkflow):
    """Advanced HTTP scanner with modular components"""
    
    def __init__(self):
        super().__init__(name="http_03")
        self.common_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
        self.timeout = 10
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ]
        self.config = self._load_config()
        
        # Initialize modular components
        self.dns_discovery = DNSDiscovery()
        self.http_service_scanner = HTTPServiceScanner(self.user_agents)
        self.path_discovery = PathDiscoveryEngine(self.user_agents, self.config)
        self.security_analyzer = SecurityAnalyzer()
        self.technology_detector = TechnologyDetector()
        self.fallback_scanner = FallbackScanner(self.user_agents)
        self.subdomain_discovery = SubdomainDiscovery()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            debug_print(f"Could not load config.yaml: {e}", level="WARNING")
            return {}
        
    async def execute(self, target: str, ports: Optional[List[int]] = None, **kwargs) -> WorkflowResult:
        """Execute advanced HTTP scanning workflow with modular components"""
        start_time = datetime.now()
        discovered_hostnames = kwargs.get('discovered_hostnames', [])
        
        # Validate input
        is_valid, validation_errors = self.validate_input(target, **kwargs)
        if not is_valid:
            return WorkflowResult(
                success=False,
                error=f"Validation failed: {'; '.join(validation_errors)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Store the original IP target for connection purposes
        self.original_ip = target
        # Set original IP in all components
        self.dns_discovery.original_ip = target
        self.http_service_scanner.original_ip = target
        self.path_discovery.original_ip = target
        self.security_analyzer.original_ip = target
        self.fallback_scanner.original_ip = target
        
        # Check dependencies at runtime for more accurate detection
        runtime_deps_available = check_dependencies()
        
        if not runtime_deps_available:
            debug_print(f"Dependencies not available. Using fallback implementation. Target: {target}")
            return await self._execute_fallback(target, ports, discovered_hostnames=discovered_hostnames, **kwargs)
        
        try:
            results = HTTPScanResult(target=target)
            
            # Start parallel subdomain discovery if target is a domain
            subdomain_task = None
            if not self._is_ip_address(target):
                subdomain_task = asyncio.create_task(
                    self.subdomain_discovery.discover_subdomains_parallel(target)
                )
            
            # DNS enumeration
            dns_info = await self.dns_discovery.enumerate_dns(target)
            results.dns_records = dns_info['records']
            results.subdomains = dns_info['subdomains']
            
            # Build hostname list
            all_hostnames = self.dns_discovery.build_hostname_list(
                target, discovered_hostnames, results.subdomains
            )
            
            # Determine ports to scan
            scan_ports = ports if ports else self.common_ports
            debug_print(f"HTTP scanner - ports: {scan_ports}, testing {len(all_hostnames)} hostnames")
            
            # HTTP service discovery
            for port in scan_ports:
                for hostname in all_hostnames:
                    use_ip = self.original_ip if hostname != self.original_ip else None
                    service = await self.http_service_scanner.scan_http_service(hostname, port, use_ip=use_ip)
                    if service:
                        service.actual_target = hostname
                        
                        if self.http_service_scanner.is_unique_service(service, results.services):
                            results.services.append(service)
                            debug_print(f"Found service: {service.url} (hostname: {hostname})")
                            
                            # Extract additional hostnames
                            new_hostnames = self.http_service_scanner.extract_hostnames_from_response(service)
                            if new_hostnames:
                                debug_print(f"Discovered hostnames: {new_hostnames}")
                                for new_hostname in new_hostnames:
                                    if new_hostname not in all_hostnames:
                                        all_hostnames.append(new_hostname)
                                        new_service = await self.http_service_scanner.scan_http_service(
                                            new_hostname, port, use_ip=self.original_ip
                                        )
                                        if new_service and self.http_service_scanner.is_unique_service(new_service, results.services):
                                            new_service.actual_target = new_hostname
                                            results.services.append(new_service)

            # Advanced analysis for all services
            for service in results.services:
                # Path discovery
                discovered_paths = await self.path_discovery.discover_paths(service)
                service.discovered_paths.extend(discovered_paths)
                
                # Security analysis
                header_vulns = self.security_analyzer.analyze_headers(service)
                results.vulnerabilities.extend(header_vulns)
                
                content_vulns = self.security_analyzer.analyze_response_content(service)
                results.vulnerabilities.extend(content_vulns)
                
                # Technology detection
                service.technologies = await self.technology_detector.detect_technologies(service)
                
                # SSL analysis for HTTPS
                if service.is_https:
                    ssl_vulns = await self.security_analyzer.analyze_ssl(service)
                    results.vulnerabilities.extend(ssl_vulns)
                    
                    ssl_hostnames = await self.security_analyzer.extract_ssl_hostnames(service)
                    if ssl_hostnames:
                        debug_print(f"SSL hostnames: {ssl_hostnames}")
                        for ssl_hostname in ssl_hostnames:
                            if ssl_hostname not in all_hostnames:
                                all_hostnames.append(ssl_hostname)
                                ssl_service = await self.http_service_scanner.scan_http_service(
                                    ssl_hostname, service.port, use_ip=self.original_ip
                                )
                                if ssl_service and self.http_service_scanner.is_unique_service(ssl_service, results.services):
                                    ssl_service.actual_target = ssl_hostname
                                    results.services.append(ssl_service)
            
            # Wait for subdomain discovery to complete
            if subdomain_task:
                try:
                    subdomain_results = await subdomain_task
                    if subdomain_results['subdomains']:
                        results.subdomains.extend(subdomain_results['subdomains'])
                        results.subdomains = list(set(results.subdomains))  # Remove duplicates
                        debug_print(f"Parallel subdomain discovery found {len(subdomain_results['subdomains'])} subdomains")
                except Exception as e:
                    debug_print(f"Subdomain discovery error: {e}", level="WARNING")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Build result
            result_dict = results.to_dict()
            result_dict['fallback_mode'] = False
            result_dict['scan_engine'] = 'modular_httpx'
            result_dict['tested_hostnames'] = all_hostnames
            
            return WorkflowResult(
                success=True,
                data=result_dict,
                execution_time=execution_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _is_ip_address(self, target: str) -> bool:
        """Check if target is an IP address"""
        import re
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        return bool(re.match(ipv4_pattern, target) or re.match(ipv6_pattern, target))
    
    async def _execute_fallback(self, target: str, ports: Optional[List[int]] = None, **kwargs) -> WorkflowResult:
        """Fallback implementation using built-in modules"""
        start_time = datetime.now()
        discovered_hostnames = kwargs.get('discovered_hostnames', [])
        
        try:
            # Use fallback scanner for basic connectivity
            scan_ports = ports if ports else self.common_ports
            services = await self.fallback_scanner.scan_common_ports(target)
            
            # Build basic result
            result_dict = {
                'target': target,
                'services': [service.to_dict() for service in services],
                'vulnerabilities': [],
                'dns_records': [],
                'subdomains': [],
                'summary': {
                    'total_services': len(services),
                    'total_vulnerabilities': 0,
                    'severity_counts': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
                    'technologies': [],
                    'discovered_paths': []
                },
                'fallback_mode': True,
                'scan_engine': 'fallback_scanner'
            }
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return WorkflowResult(
                success=True,
                data=result_dict,
                execution_time=execution_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    def validate_input(self, target: str, **kwargs) -> tuple[bool, list[str]]:
        """Validate input parameters"""
        errors = []
        
        if not target:
            errors.append("Target is required")
        
        # Basic target validation
        import re
        if target and not re.match(r'^[a-zA-Z0-9.-]+$', target):
            errors.append("Invalid target format")
        
        return len(errors) == 0, errors
