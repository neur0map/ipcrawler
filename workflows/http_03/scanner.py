"""Advanced HTTP Scanner with modular architecture and enhanced discovery capabilities"""
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from workflows.core.base import BaseWorkflow, WorkflowResult
from .models import HTTPScanResult
from .config import get_scanner_config
from .utils import validate_input, build_hostname_list
from .dns_handler import DNSHandler
from .service_discovery import ServiceDiscovery
from .tech_detector import TechnologyDetector
from .path_discovery import PathDiscovery
from .security_analyzer import SecurityAnalyzer
from utils.debug import debug_print


class HTTPAdvancedScanner(BaseWorkflow):
    """Advanced HTTP scanner with modular architecture and enhanced discovery capabilities"""
    
    def __init__(self):
        super().__init__(name="http_03")
        self.config = get_scanner_config()
        self.common_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
        
        # Initialize modular components
        self.dns_handler = None
        self.service_discovery = None
        self.tech_detector = None
        self.path_discovery = None
        self.security_analyzer = None
        
        # Will be set during execution
        self.original_ip = None
        
    def _initialize_components(self, target: str):
        """Initialize modular components with target information"""
        self.dns_handler = DNSHandler()
        self.service_discovery = ServiceDiscovery(target)
        self.tech_detector = TechnologyDetector()
        self.path_discovery = PathDiscovery(target)
        self.security_analyzer = SecurityAnalyzer()
    
    def validate_input(self, target: str, **kwargs) -> Tuple[bool, List[str]]:
        """Validate input parameters for HTTP scanning"""
        return validate_input(target, **kwargs)
        
    async def execute(self, target: str, ports: Optional[List[int]] = None, **kwargs) -> WorkflowResult:
        """Execute advanced HTTP scanning workflow with modular architecture"""
        start_time = datetime.now()
        discovered_hostnames = kwargs.get('discovered_hostnames', [])
        
        # Validate input first
        is_valid, validation_errors = validate_input(target, **kwargs)
        if not is_valid:
            return WorkflowResult(
                success=False,
                error=f"Input validation failed: {'; '.join(validation_errors)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Store the original IP target for connection purposes
        self.original_ip = target
        
        # Initialize modular components
        self._initialize_components(target)
        
        # Check dependencies at runtime for more accurate detection
        if not self.config.deps_available:
            debug_print(f"Dependencies not available at runtime. Using fallback implementation. Target: {target}, Ports: {ports}, Hostnames: {discovered_hostnames}")
            return await self._execute_fallback(target, ports, discovered_hostnames=discovered_hostnames, **kwargs)
        
        try:
            results = HTTPScanResult(target=target)
            
            # DNS enumeration first
            dns_info = await self.dns_handler.enumerate_dns(target)
            results.dns_records = dns_info['records']
            results.subdomains = dns_info['subdomains']
            
            # Combine all possible hostnames
            all_hostnames = build_hostname_list(
                target, discovered_hostnames, results.subdomains, 
                self.config.scanner_config_manager
            )
            
            # Determine ports to scan
            scan_ports = ports if ports else self.common_ports
            debug_print(f"HTTP scanner execute - ports: {scan_ports}, testing {len(all_hostnames)} hostnames: {all_hostnames}")
            
            # HTTP service discovery - discover all services across hostnames and ports
            discovered_services = await self.service_discovery.discover_all_services(all_hostnames, scan_ports)
            results.services = discovered_services
            
            # Advanced analysis for all discovered services
            for service in results.services:
                # Technology detection
                service.technologies = await self.tech_detector.detect_technologies(service)
                
                # Path discovery with SmartList and traditional methods
                discovered_paths = await self.path_discovery.discover_paths(service)
                service.discovered_paths.extend(discovered_paths)
                
                # Security analysis
                vulnerabilities = await self.security_analyzer.analyze_service_security(service)
                results.vulnerabilities.extend(vulnerabilities)
            
            # Cross-service vulnerability analysis
            cross_vulns = self.security_analyzer.analyze_cross_service_vulnerabilities(results)
            results.vulnerabilities.extend(cross_vulns)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Add scan metadata
            result_dict = results.to_dict()
            result_dict['fallback_mode'] = False
            result_dict['scan_engine'] = 'httpx+dnspython+modular'
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
    
    async def _execute_fallback(self, target: str, ports: Optional[List[int]] = None, **kwargs) -> WorkflowResult:
        """Fallback implementation using modular components with system tools"""
        start_time = datetime.now()
        discovered_hostnames = kwargs.get('discovered_hostnames', [])
        
        # Initialize modular components
        self._initialize_components(target)
        
        try:
            debug_print(f"Fallback mode - Target: {target}, Ports: {ports}, Hostnames: {discovered_hostnames}")
            
            # Use DNS handler for fallback DNS enumeration
            dns_info = await self.dns_handler.get_dns_info_fallback(target)
            
            # Build comprehensive hostname list
            all_hostnames = build_hostname_list(
                target, discovered_hostnames, dns_info.get('subdomains', []), 
                self.config.scanner_config_manager
            )
            
            # Determine ports to scan
            scan_ports = ports if ports else self.common_ports
            
            # Use service discovery for fallback scanning
            results = await self.service_discovery.discover_services_fallback(all_hostnames, scan_ports)
            
            # Add DNS information
            results['dns_records'] = dns_info.get('records', [])
            results['subdomains'] = dns_info.get('subdomains', [])
            results['tested_hostnames'] = all_hostnames
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            debug_print(f"Fallback scan results: {len(results['services'])} services found")
            
            return WorkflowResult(
                success=True,
                data=results,
                execution_time=execution_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds()
            )
