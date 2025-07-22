"""Advanced HTTP Scanner with httpx, DNS enumeration, and vulnerability discovery"""
import asyncio
import socket
import ssl
import subprocess
import re
import json
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urlparse, urljoin
import base64
import hashlib
from datetime import datetime

def check_dependencies():
    """Check if HTTP scanner dependencies are available at runtime"""
    try:
        import httpx
        import dns.resolver
        import dns.zone
        import dns.query
        return True
    except ImportError:
        return False

# Try to import dependencies for global use
try:
    import httpx
    import dns.resolver
    import dns.zone
    import dns.query
    DEPS_AVAILABLE = True
except ImportError as e:
    DEPS_AVAILABLE = False

from workflows.core.base import BaseWorkflow, WorkflowResult
from workflows.core.command_logger import get_command_logger
from .models import HTTPScanResult, HTTPService, HTTPVulnerability, DNSRecord, PathDiscoveryMetadata
from utils.debug import debug_print

# Port database integration
try:
    from database.ports import load_port_database
    PORT_DB_AVAILABLE = True
except ImportError:
    PORT_DB_AVAILABLE = False

# SmartList integration
try:
    from src.core.scorer import (
        score_wordlists_with_catalog,
        score_wordlists,
        get_wordlist_paths,
        ScoringContext
    )
    SMARTLIST_AVAILABLE = True
except ImportError as e:
    SMARTLIST_AVAILABLE = False
    debug_print(f"SmartList components not available: {e}", level="WARNING")


class HTTPAdvancedScanner(BaseWorkflow):
    """Advanced HTTP scanner with multiple discovery techniques"""
    
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
        self.port_database = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            debug_print(f"Could not load config.yaml: {e}", level="WARNING")
            return {}
            
    def _load_port_database(self):
        """Load port database for service-specific path discovery"""
        if not PORT_DB_AVAILABLE or self.port_database is not None:
            return
            
        try:
            db_path = Path(__file__).parent.parent.parent / "database" / "ports" / "port_db.json"
            with open(db_path, 'r') as f:
                db_data = json.load(f)
            self.port_database = load_port_database(db_data)
            debug_print("Port database loaded successfully")
        except Exception as e:
            debug_print(f"Could not load port database: {e}", level="WARNING")
            self.port_database = {}
    
    def _get_service_specific_paths(self, port: int) -> List[str]:
        """Get service-specific paths from port database"""
        if not self.port_database:
            return []
            
        try:
            port_entry = self.port_database.ports.get(str(port)) if hasattr(self.port_database, 'ports') else None
            if port_entry and hasattr(port_entry, 'indicators') and port_entry.indicators and hasattr(port_entry.indicators, 'paths'):
                paths = port_entry.indicators.paths or []
                debug_print(f"Found {len(paths)} database paths for port {port}: {paths}")
                return paths
        except Exception as e:
            debug_print(f"Error getting service paths for port {port}: {e}", level="WARNING")
            
        return []
        
    async def execute(self, target: str, ports: Optional[List[int]] = None, **kwargs) -> WorkflowResult:
        """Execute advanced HTTP scanning workflow"""
        start_time = datetime.now()
        discovered_hostnames = kwargs.get('discovered_hostnames', [])
        
        # Validate input first
        is_valid, validation_errors = self.validate_input(target, **kwargs)
        if not is_valid:
            return WorkflowResult(
                success=False,
                error=f"Input validation failed: {'; '.join(validation_errors)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Store the original IP target for connection purposes
        self.original_ip = target
        
        # Check dependencies at runtime for more accurate detection
        runtime_deps_available = check_dependencies()
        
        if not runtime_deps_available:
            debug_print(f"Dependencies not available at runtime. Using fallback implementation. Target: {target}, Ports: {ports}, Hostnames: {discovered_hostnames}")
            return await self._execute_fallback(target, ports, discovered_hostnames=discovered_hostnames, **kwargs)
        
        try:
            results = HTTPScanResult(target=target)
            
            # Load port database for enhanced service discovery
            self._load_port_database()
            
            # DNS enumeration first
            dns_info = await self._dns_enumeration(target)
            results.dns_records = dns_info['records']
            results.subdomains = dns_info['subdomains']
            
            # Combine all possible hostnames
            all_hostnames = self._build_hostname_list(target, discovered_hostnames, results.subdomains)
            
            # Determine ports to scan
            scan_ports = ports if ports else self.common_ports
            debug_print(f"HTTP scanner execute - ports: {scan_ports}, testing {len(all_hostnames)} hostnames: {all_hostnames}")
            
            # HTTP service discovery - test ALL hostname combinations
            for port in scan_ports:
                # Test each hostname for this port
                for hostname in all_hostnames:
                    # Determine connection target (IP if hostname differs from target)
                    use_ip = self.original_ip if hostname != self.original_ip else None
                    service = await self._scan_http_service(hostname, port, use_ip=use_ip)
                    if service:
                        # Store which hostname worked
                        service.actual_target = hostname
                        
                        # Check if this is a unique service (different from existing ones)
                        if self._is_unique_service(service, results.services):
                            results.services.append(service)
                            debug_print(f"Found unique service: {service.url} (hostname: {hostname})")
                            
                            # Extract additional hostnames from response
                            new_hostnames = self._extract_hostnames_from_response(service)
                            if new_hostnames:
                                debug_print(f"Discovered additional hostnames: {new_hostnames}")
                                # Test newly discovered hostnames on this port
                                for new_hostname in new_hostnames:
                                    if new_hostname not in all_hostnames:
                                        all_hostnames.append(new_hostname)
                                        service = await self._scan_http_service(new_hostname, port, use_ip=self.original_ip)
                                        if service and self._is_unique_service(service, results.services):
                                            service.actual_target = new_hostname
                                            results.services.append(service)
                                            debug_print(f"Found service via discovered hostname: {service.url}")

            # Advanced discovery techniques for all services
            for service in results.services:
                # Path discovery without wordlists
                discovered_paths = await self._discover_paths(service)
                service.discovered_paths.extend(discovered_paths)
                
                # Header analysis
                vulnerabilities = self._analyze_headers(service)
                results.vulnerabilities.extend(vulnerabilities)
                
                # Technology detection
                service.technologies = await self._detect_technologies(service)
                
                # SSL/TLS analysis for HTTPS
                if service.is_https:
                    ssl_vulns = await self._analyze_ssl(service)
                    results.vulnerabilities.extend(ssl_vulns)
            
            # Cross-service analysis
            cross_vulns = self._cross_service_analysis(results)
            results.vulnerabilities.extend(cross_vulns)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Add scan metadata
            result_dict = results.to_dict()
            result_dict['fallback_mode'] = False
            result_dict['scan_engine'] = 'httpx+dnspython'
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
        """Fallback implementation using curl and system tools"""
        start_time = datetime.now()
        discovered_hostnames = kwargs.get('discovered_hostnames', [])
        
        # Store the original IP target
        original_ip = target
        
        try:
            debug_print(f"Fallback mode - Target: {target}, Ports: {ports}, Hostnames: {discovered_hostnames}")
            
            results = {
                "target": target,
                "services": [],
                "vulnerabilities": [],
                "dns_records": [],
                "subdomains": [],
                "fallback_mode": True,  # Flag to indicate fallback was used
                "scan_engine": "curl+nslookup"  # Indicate what tools were used
            }
            
            # Basic DNS lookup
            try:
                dns_result = subprocess.run(
                    ["nslookup", target],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if dns_result.returncode == 0:
                    ips = re.findall(r'Address: ([\d.]+)', dns_result.stdout)
                    for ip in ips:
                        results["dns_records"].append({
                            "type": "A",
                            "value": ip
                        })
            except:
                pass
            
            # Build comprehensive hostname list for fallback mode
            all_hostnames = self._build_hostname_list(target, discovered_hostnames, [])
            
            # Scan ports with curl
            scan_ports = ports if ports else self.common_ports
            debug_print(f"Fallback mode scanning ports: {scan_ports}, testing {len(all_hostnames)} hostnames")
            
            for port in scan_ports:
                # Try HTTP first for common HTTP ports
                if port in [80, 8080, 8000]:
                    schemes = ['http', 'https']
                elif port in [443, 8443]:
                    schemes = ['https', 'http']
                else:
                    schemes = ['http', 'https']
                
                for scheme in schemes:
                    for try_target in all_hostnames:
                        # Determine what to connect to
                        connect_to = original_ip if try_target in discovered_hostnames else try_target
                        
                        # Don't include port for standard ports
                        if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                            url = f"{scheme}://{connect_to}"
                        else:
                            url = f"{scheme}://{connect_to}:{port}"
                        
                        curl_cmd = [
                            "curl", "-I", "-s", "-m", "5",
                            "-k",  # Allow insecure connections
                            "-L",  # Follow redirects
                            "-H", f"User-Agent: {self.user_agents[0]}",
                        ]
                        
                        # Always add Host header when using a hostname
                        if try_target in discovered_hostnames:
                            curl_cmd.extend(["-H", f"Host: {try_target}"])
                        
                        curl_cmd.append(url)
                        
                        try:
                            result = subprocess.run(
                                curl_cmd,
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            
                            debug_print(f"curl command: {' '.join(curl_cmd)}")
                            debug_print(f"curl return code: {result.returncode}")
                            debug_print(f"curl stdout length: {len(result.stdout) if result.stdout else 0}")
                            debug_print(f"curl stderr: {result.stderr[:200] if result.stderr else 'None'}")
                            
                            if result.returncode == 0 and result.stdout:
                                service = {
                                    "port": port,
                                    "scheme": scheme,
                                    "url": url,
                                    "headers": {},
                                    "status_code": None,
                                    "server": None,
                                    "technologies": []
                                }
                                
                                # Parse headers
                                lines = result.stdout.strip().split('\n')
                                if lines:
                                    status_match = re.match(r'HTTP/[\d.]+ (\d+)', lines[0])
                                    if status_match:
                                        service["status_code"] = int(status_match.group(1))
                                
                                for line in lines[1:]:
                                    if ':' in line:
                                        key, value = line.split(':', 1)
                                        service["headers"][key.strip()] = value.strip()
                                        
                                        if key.lower() == 'server':
                                            service["server"] = value.strip()
                                
                                # Check if this is unique before adding
                                is_unique = True
                                for existing in results["services"]:
                                    if (existing["port"] == service["port"] and 
                                        existing["scheme"] == service["scheme"] and
                                        existing.get("status_code") == service.get("status_code") and
                                        existing.get("server") == service.get("server")):
                                        is_unique = False
                                        break
                                
                                if is_unique:
                                    results["services"].append(service)
                                    debug_print(f"Found unique service in fallback: {url} (hostname: {try_target})")
                                    
                                    # Basic vulnerability checks
                                    vulns = self._check_basic_vulnerabilities(service)
                                    results["vulnerabilities"].extend(vulns)
                                
                        except Exception as e:
                            debug_print(f"curl error for {url}: {e}")
                            continue
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            debug_print(f"Fallback scan results: {len(results['services'])} services found")
            
            # Add tested hostnames to results
            results['tested_hostnames'] = all_hostnames
            
            # Add summary if we found services
            if results['services']:
                # Add basic summary
                results['summary'] = {
                    'total_services': len(results['services']),
                    'total_vulnerabilities': len(results['vulnerabilities']),
                    'severity_counts': self._count_vuln_severities(results['vulnerabilities']),
                    'technologies': [],
                    'discovered_paths': []
                }
            
            debug_print(f"Fallback mode complete - Final results: {len(results.get('services', []))} services, execution_time: {execution_time:.2f}s")
            
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
    
    async def _dns_enumeration(self, target: str) -> Dict[str, Any]:
        """Perform DNS enumeration without wordlists"""
        dns_info = {
            'records': [],
            'subdomains': []
        }
        
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
            
            # Common subdomain patterns (no wordlist)
            common_patterns = [
                'www', 'mail', 'ftp', 'admin', 'portal', 'api', 'dev',
                'staging', 'test', 'prod', 'vpn', 'remote', 'secure'
            ]
            
            tasks = []
            for pattern in common_patterns:
                subdomain = f"{pattern}.{target}"
                tasks.append(self._check_subdomain(subdomain))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for subdomain, exists in results:
                if isinstance(exists, bool) and exists:
                    dns_info['subdomains'].append(subdomain)
                    
        except Exception:
            pass
            
        return dns_info
    
    async def _check_subdomain(self, subdomain: str) -> Tuple[str, bool]:
        """Check if subdomain exists"""
        try:
            socket.gethostbyname(subdomain)
            return subdomain, True
        except:
            return subdomain, False
    
    async def _scan_http_service(self, target: str, port: int, use_ip: Optional[str] = None) -> Optional[HTTPService]:
        """Scan a single HTTP/HTTPS service"""
        # Determine scheme order based on port
        if port == 443 or port == 8443:
            schemes = ['https', 'http']
        elif port == 80 or port == 8080 or port == 8000:
            schemes = ['http', 'https']
        else:
            schemes = ['http', 'https']  # Try HTTP first for unknown ports
            
        for scheme in schemes:
            # Use IP for connection if provided, otherwise use target
            connect_to = use_ip if use_ip else target
            
            # Don't include port for standard ports
            if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                url = f"{scheme}://{connect_to}"
            else:
                url = f"{scheme}://{connect_to}:{port}"
            
            try:
                # Use more specific timeouts
                timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
                async with httpx.AsyncClient(
                    verify=False, 
                    timeout=timeout,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                ) as client:
                    # Set proper Host header with the target (which might be a hostname)
                    headers = {
                        "User-Agent": self.user_agents[0],
                        "Host": target  # Use the target (hostname) for Host header
                    }
                    
                    response = await client.get(
                        url,
                        headers=headers,
                        follow_redirects=True
                    )
                    
                    service = HTTPService(
                        port=port,
                        scheme=scheme,
                        url=url,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        server=response.headers.get('server', 'Unknown'),
                        is_https=(scheme == 'https')
                    )
                    
                    # Get response body for analysis
                    try:
                        service.response_body = response.text[:10000]
                    except:
                        service.response_body = ""
                    
                    return service
                    
            except httpx.ConnectError:
                # Connection refused or timeout - try next scheme
                continue
            except httpx.TimeoutException:
                # Timeout - try next scheme
                continue
            except Exception:
                # Other errors - try next scheme
                continue
                
        return None
    
    async def _discover_paths(self, service: HTTPService) -> List[str]:
        """Enhanced path discovery using SmartList algorithm and traditional methods"""
        start_time = time.time()
        discovered = []
        total_paths_tested = 0
        discovery_method = "basic"
        wordlist_used = None
        confidence = None
        
        # Get configuration - simple enhanced discovery toggle
        discovery_config = self.config.get('discovery', {})
        enhanced_discovery = discovery_config.get('enhanced', True)
        
        smartlist_enabled = enhanced_discovery and SMARTLIST_AVAILABLE
        discovery_enabled = True  # Always enabled, but mode depends on 'enhanced' setting
        
        # 1. SmartList intelligent discovery (if enabled and available)
        if smartlist_enabled:
            try:
                smartlist_paths = await self._discover_paths_with_smartlist(service)
                if smartlist_paths:
                    discovered.extend(smartlist_paths['paths'])
                    discovery_method = "smartlist"
                    wordlist_used = smartlist_paths.get('wordlist_used')
                    confidence = smartlist_paths.get('confidence')
                    total_paths_tested += smartlist_paths.get('paths_tested', 0)
                    
                    # Store SmartList recommendations in service
                    service.smartlist_recommendations = smartlist_paths.get('recommendations', [])
            except Exception as e:
                debug_print(f"SmartList discovery error: {e}", level="WARNING")
        
        # 2. Traditional discovery methods (if enabled or SmartList failed)
        if discovery_enabled and (not smartlist_enabled or not discovered):
            traditional_paths = await self._discover_paths_traditional(service, discovery_config)
            discovered.extend(traditional_paths['paths'])
            if discovery_method == "basic":  # Only override if SmartList didn't work
                discovery_method = traditional_paths.get('method', 'traditional')
            total_paths_tested += traditional_paths.get('paths_tested', 0)
            
        
        # 3. Parse HTML for links (always enabled)
        if service.response_body:
            html_paths = self._extract_paths_from_html(service.response_body)
            discovered.extend(html_paths)
        
        # Remove duplicates and clean up
        unique_paths = list(set(discovered))
        discovery_time = time.time() - start_time
        
        # Store discovery metadata
        service.discovery_metadata = PathDiscoveryMetadata(
            discovery_method=discovery_method,
            wordlist_used=wordlist_used,
            confidence=confidence,
            total_paths_tested=total_paths_tested,
            successful_paths=len(unique_paths),
            discovery_time=discovery_time
        )
        
        
        return unique_paths
    
    async def _discover_paths_with_smartlist(self, service: HTTPService) -> Dict[str, Any]:
        """Use SmartList algorithm for intelligent path discovery"""
        if not SMARTLIST_AVAILABLE:
            return {'paths': [], 'paths_tested': 0}
        
        # Build context for SmartList
        target_host = urlparse(service.url).hostname or self.original_ip
        
        # Extract technology from service
        tech = None
        if service.technologies and service.technologies[0]:
            tech = service.technologies[0].lower()
        elif service.server:
            # Try to extract tech from server header
            server_lower = service.server.lower()
            if 'apache' in server_lower:
                tech = 'apache'
            elif 'nginx' in server_lower:
                tech = 'nginx'
            elif 'tomcat' in server_lower:
                tech = 'tomcat'
        
        context = ScoringContext(
            target=target_host,
            port=service.port,
            service=f"{service.scheme} service",
            tech=tech,
            headers=service.headers
        )
        
        # Get SmartList recommendations
        try:
            result = score_wordlists_with_catalog(context)
        except Exception as e:
            result = score_wordlists(context)
        
        if not result.wordlists:
            debug_print("No wordlist recommendations from SmartList", level="WARNING")
            return {'paths': [], 'paths_tested': 0}
        
        # Sensible defaults for SmartList operation
        max_wordlists = 3
        max_paths_per_wordlist = 100
        min_confidence = 'MEDIUM'
        
        # Filter by confidence if needed
        confidence_levels = ['HIGH', 'MEDIUM', 'LOW']
        min_conf_idx = confidence_levels.index(min_confidence) if min_confidence in confidence_levels else 1
        
        if confidence_levels.index(result.confidence.value.upper()) > min_conf_idx:
            debug_print(f"SmartList confidence {result.confidence.value} below minimum {min_confidence}")
            return {'paths': [], 'paths_tested': 0}
        
        # Use top wordlists
        wordlists_to_use = result.wordlists[:max_wordlists]
        
        # Get wordlist paths
        try:
            wordlist_paths = get_wordlist_paths(wordlists_to_use, tech=tech, port=service.port)
        except Exception as e:
            debug_print(f"Could not resolve wordlist paths: {e}", level="WARNING")
            return {'paths': [], 'paths_tested': 0}
        
        # Read and test paths from wordlists
        all_paths = []
        total_tested = 0
        
        for i, wordlist_name in enumerate(wordlists_to_use):
            if i >= len(wordlist_paths) or not wordlist_paths[i]:
                continue
                
            wordlist_path = Path(wordlist_paths[i])
            if not wordlist_path.exists():
                debug_print(f"Wordlist not found: {wordlist_path}", level="WARNING")
                continue
                
            try:
                with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                    paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    paths = paths[:max_paths_per_wordlist]  # Limit paths per wordlist
                    
                    # Log the equivalent fuzzing command
                    base_url = service.url.rstrip('/')
                    get_command_logger().log_command("http_03", f"ffuf -w {wordlist_path}:FUZZ -u {base_url}/FUZZ -mc 200,301,302,401,403 -t 20")
                    
                    # Test paths
                    valid_paths = await self._test_paths_batch(service, paths)
                    all_paths.extend(valid_paths)
                    total_tested += len(paths)
                    
            except Exception as e:
                debug_print(f"Error reading wordlist {wordlist_path}: {e}", level="WARNING")
        
        # Build recommendations summary
        recommendations = []
        for i, wordlist in enumerate(wordlists_to_use[:len(wordlist_paths)]):
            if wordlist_paths[i]:
                recommendations.append({
                    'wordlist': wordlist,
                    'path': str(wordlist_paths[i]),
                    'confidence': result.confidence.value.upper(),
                    'score': round(result.score, 3)
                })
        
        return {
            'paths': all_paths,
            'paths_tested': total_tested,
            'wordlist_used': wordlists_to_use[0] if wordlists_to_use else None,
            'confidence': result.confidence.value.upper(),
            'recommendations': recommendations
        }
    
    async def _discover_paths_traditional(self, service: HTTPService, config: Dict[str, Any]) -> Dict[str, Any]:
        """Traditional path discovery methods"""
        discovered = []
        paths_tested = 0
        
        # Common application patterns (always included)
        common_paths = [
            '/robots.txt', '/sitemap.xml', '/.well-known/security.txt',
            '/api/', '/api/v1/', '/api/v2/', '/graphql',
            '/.git/config', '/.env', '/config.php', '/wp-config.php',
            '/admin/', '/login', '/dashboard', '/console',
            '/swagger-ui/', '/api-docs/', '/docs/',
            '/.DS_Store', '/thumbs.db', '/web.config'
        ]
        
        # Add service-specific paths from port database
        try:
            port = int(service.url.split(':')[-1].split('/')[0]) if ':' in service.url else (443 if 'https' in service.url else 80)
            db_paths = self._get_service_specific_paths(port)
            if db_paths:
                debug_print(f"Adding {len(db_paths)} database-specific paths for port {port}")
                common_paths.extend([path for path in db_paths if path not in common_paths])
        except Exception as e:
            debug_print(f"Error adding database paths: {e}", level="WARNING")
        
        # Log the equivalent manual commands for common paths
        base_url = service.url.rstrip('/')
        for path in common_paths[:5]:  # Show first 5 as examples
            get_command_logger().log_command("http_03", f"curl -s -o /dev/null -w '%{{http_code}}' {base_url}{path}")
        if len(common_paths) > 5:
            get_command_logger().log_command("http_03", f"# ... and {len(common_paths) - 5} more common paths")
        
        valid_common = await self._test_paths_batch(service, common_paths)
        discovered.extend(valid_common)
        paths_tested += len(common_paths)
        
        # Technology-specific paths (always included)
        tech_paths = []
        if service.server:
            server_lower = service.server.lower()
            if 'apache' in server_lower:
                tech_paths.extend(['/server-status', '/server-info'])
            elif 'nginx' in server_lower:
                tech_paths.extend(['/nginx_status'])
            elif 'tomcat' in server_lower:
                tech_paths.extend(['/manager/', '/host-manager/'])
                
        # Add monitoring-specific paths based on content analysis
        monitoring_paths = []
        if service.response_body:
            response_lower = service.response_body.lower()
            
            # Grafana-specific paths
            if any(indicator in response_lower for indicator in ['grafana', '/grafana', 'grafana.js', 'grafana-app']):
                monitoring_paths.extend([
                    '/grafana/', '/grafana/api/health', '/grafana/login',
                    '/grafana/api/dashboards', '/grafana/api/datasources',
                    '/api/health', '/api/dashboards', '/api/datasources'
                ])
                debug_print("Detected Grafana indicators, adding Grafana-specific paths")
            
            # Generic monitoring dashboard paths
            if any(indicator in response_lower for indicator in ['dashboard', 'monitoring', 'metrics', 'telemetry']):
                monitoring_paths.extend([
                    '/metrics', '/health', '/status', '/api/health',
                    '/monitoring/', '/dashboard/', '/admin/monitoring',
                    '/api/v1/query', '/prometheus/', '/kibana/'
                ])
                debug_print("Detected monitoring indicators, adding dashboard paths")
                
            # Prometheus-specific paths
            if any(indicator in response_lower for indicator in ['prometheus', '/metrics', 'prom_']):
                monitoring_paths.extend([
                    '/metrics', '/api/v1/query', '/api/v1/label',
                    '/prometheus/', '/prometheus/api/v1/query'
                ])
                debug_print("Detected Prometheus indicators, adding Prometheus paths")
        
        # Combine all technology-specific paths
        if monitoring_paths:
            tech_paths.extend([path for path in monitoring_paths if path not in tech_paths])
        
        if tech_paths:
            # Log technology-specific commands
            for path in tech_paths:
                get_command_logger().log_command("http_03", f"curl -s -o /dev/null -w '%{{http_code}}' {base_url}{path}")
            
            valid_tech = await self._test_paths_batch(service, tech_paths)
            discovered.extend(valid_tech)
            paths_tested += len(tech_paths)
        
        return {
            'paths': discovered,
            'paths_tested': paths_tested,
            'method': 'traditional'
        }
    
    def _extract_paths_from_html(self, html_content: str) -> List[str]:
        """Extract paths from HTML content with enhanced monitoring detection"""
        paths = []
        
        # Find all href and src attributes
        links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', html_content)
        for link in links:
            parsed = urlparse(link)
            if parsed.path and parsed.path != '/':
                # Only include relative paths or paths on same domain
                if not parsed.netloc or parsed.netloc == '':
                    paths.append(parsed.path)
        
        # Enhanced monitoring detection - look for specific patterns in HTML
        monitoring_patterns = [
            r'/grafana[^"\']*',           # Any path containing /grafana
            r'/dashboard[^"\']*',         # Dashboard paths
            r'/monitoring[^"\']*',        # Monitoring paths
            r'/metrics[^"\']*',           # Metrics paths
            r'/prometheus[^"\']*',        # Prometheus paths
            r'/kibana[^"\']*',            # Kibana paths
            r'/api/health[^"\']*',        # Health check APIs
            r'/api/v1/query[^"\']*',      # Prometheus API
            r'data-grafana[^=]*=["\'][^"\']+',  # Grafana data attributes
        ]
        
        for pattern in monitoring_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Clean up the match (remove data attributes)
                if match.startswith('/'):
                    clean_path = match.split('?')[0].split('#')[0]  # Remove query params and fragments
                    if clean_path not in paths:
                        paths.append(clean_path)
                        debug_print(f"Found monitoring path in HTML: {clean_path}")
        
        # Look for JavaScript variables or config that might contain paths
        js_patterns = [
            r'grafanaUrl["\']?\s*:\s*["\']([^"\']+)["\']',     # grafanaUrl config
            r'apiUrl["\']?\s*:\s*["\']([^"\']+)["\']',         # API URL configs
            r'baseUrl["\']?\s*:\s*["\']([^"\']+)["\']',        # Base URL configs
            r'window\.__grafana[^}]*url["\']?\s*:\s*["\']([^"\']+)["\']',  # Window grafana config
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                try:
                    parsed = urlparse(match)
                    if parsed.path and parsed.path != '/' and not parsed.netloc:
                        if parsed.path not in paths:
                            paths.append(parsed.path)
                            debug_print(f"Found monitoring path in JavaScript: {parsed.path}")
                except:
                    pass
        
        return paths
    
    async def _test_paths_batch(self, service: HTTPService, paths: List[str]) -> List[str]:
        """Test a batch of paths efficiently with detailed validation"""
        if not paths:
            return []
        
        # Sensible defaults for path testing
        timeout = 5
        max_concurrent = 20
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Statistics tracking
        stats = {
            'total_tested': 0,
            'valid_paths': 0,
            'status_counts': {},
            'error_count': 0,
            'filtered_out': 0
        }
        
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            # Create tasks with semaphore
            async def test_with_semaphore(path):
                async with semaphore:
                    return await self._check_path_with_stats(client, urljoin(service.url, path), stats)
            
            tasks = [test_with_semaphore(path) for path in paths]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            valid_paths = []
            for path, result in zip(paths, results):
                if isinstance(result, tuple) and len(result) == 2:
                    _, exists = result
                    if exists:
                        valid_paths.append(path)
                elif isinstance(result, Exception):
                    stats['error_count'] += 1
                    debug_print(f"Error testing path {path}: {result}")
            
            return valid_paths
    
    async def _check_path_with_stats(self, client: httpx.AsyncClient, url: str, stats: dict) -> Tuple[str, bool]:
        """Check path with actual command logging"""
        path = urlparse(url).path
        stats['total_tested'] += 1
        
        try:
            # Try HEAD first for efficiency
            response = await client.head(url, headers={"User-Agent": self.user_agents[0]})
            
            # Track status codes
            status_code = response.status_code
            stats['status_counts'][status_code] = stats['status_counts'].get(status_code, 0) + 1
            
            # If HEAD fails, try GET for directories
            if response.status_code in [405, 501]:  # Method not allowed
                response = await client.get(url, headers={"User-Agent": self.user_agents[0]})
                stats['status_counts'][response.status_code] = stats['status_counts'].get(response.status_code, 0) + 1
            
            # Use strict validation by default - only meaningful, accessible content
            valid_status_codes = [200, 201, 202, 204, 301, 302, 307, 308, 401, 403]
            
            # Exclude common false positives
            if response.status_code not in valid_status_codes:
                stats['filtered_out'] += 1
                return path, False
            
            # Additional validation for meaningful content
            is_meaningful = await self._validate_path_content(response, url, client)
            
            if is_meaningful:
                stats['valid_paths'] += 1
            else:
                stats['filtered_out'] += 1
            
            return path, is_meaningful
            
        except Exception as e:
            stats['error_count'] += 1
            debug_print(f"Error checking path {path}: {e}")
            return path, False
    
    
    async def _validate_path_content(self, response: 'httpx.Response', url: str, client: 'httpx.AsyncClient') -> bool:
        """Validate that the path contains meaningful content"""
        
        # Status code based validation
        status_code = response.status_code
        
        # Always include auth-protected paths and redirects
        if status_code in [401, 403, 301, 302, 307, 308]:
            return True
        
        # For successful responses, check content
        if status_code in [200, 201, 202, 204]:
            try:
                # Check content length from headers first
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) == 0:
                    return False
                
                # If it's a HEAD request with no content-length, try GET for small files
                if response.request.method == 'HEAD' and not content_length:
                    try:
                        get_response = await client.get(url, headers={"User-Agent": self.user_agents[0]})
                        if get_response.status_code != status_code:
                            return False
                        
                        content = get_response.text[:1000]  # First 1KB only
                        
                        # Exclude empty or minimal responses
                        if len(content.strip()) < 10:
                            return False
                        
                        # Filter out default error pages and server defaults
                        error_indicators = [
                            'not found', '404', 'file not found',
                            'forbidden', '403', 'access denied', 
                            'internal server error', '500',
                            'bad request', '400',
                            'default apache', 'default nginx',
                            'it works!', 'welcome to nginx',
                            'directory listing', 'index of /',
                            'apache http server test page',
                            'nginx welcome page',
                            'test page for the apache',
                            'welcome to caddy'
                        ]
                        
                        content_lower = content.lower()
                        for indicator in error_indicators:
                            if indicator in content_lower:
                                return False
                        
                        # Check if it's likely a real file/directory
                        # Files with extensions are more likely to be real
                        path = urlparse(url).path
                        if '.' in path.split('/')[-1]:  # Has file extension
                            return True
                        
                        # Directories with meaningful content
                        if any(tag in content_lower for tag in ['<html>', '<title>', '<h1>', '<form>', 'api']):
                            return True
                        
                        # JSON/API responses
                        if response.headers.get('content-type', '').startswith('application/json'):
                            return True
                        
                        return True  # Default to true for other content
                        
                    except Exception:
                        # If GET fails, assume HEAD was correct
                        return True
                
                return True  # Valid status with content-length
                
            except Exception:
                return True  # Default to true if we can't validate content
        
        return False
    
    def _analyze_headers(self, service: HTTPService) -> List[HTTPVulnerability]:
        """Analyze HTTP headers for security issues"""
        vulnerabilities = []
        
        # Missing security headers
        security_headers = {
            'x-frame-options': 'Clickjacking protection',
            'x-content-type-options': 'MIME type sniffing protection',
            'x-xss-protection': 'XSS protection',
            'strict-transport-security': 'HSTS',
            'content-security-policy': 'Content Security Policy',
            'referrer-policy': 'Referrer Policy',
            'permissions-policy': 'Permissions Policy'
        }
        
        for header, description in security_headers.items():
            if header not in [h.lower() for h in service.headers.keys()]:
                vulnerabilities.append(HTTPVulnerability(
                    type=f"missing-{header}",
                    severity="medium",
                    description=f"Missing {description} header",
                    url=service.url,
                    evidence=f"Header '{header}' not found in response"
                ))
        
        # Information disclosure
        info_headers = ['server', 'x-powered-by', 'x-aspnet-version']
        for header in info_headers:
            value = service.headers.get(header, '')
            if value:
                vulnerabilities.append(HTTPVulnerability(
                    type="information-disclosure",
                    severity="low",
                    description=f"Server information disclosure via {header} header",
                    url=service.url,
                    evidence=f"{header}: {value}"
                ))
        
        if 'access-control-allow-origin' in [h.lower() for h in service.headers.keys()]:
            value = next((v for k, v in service.headers.items() if k.lower() == 'access-control-allow-origin'), '')
            if value == '*':
                vulnerabilities.append(HTTPVulnerability(
                    type="cors-misconfiguration",
                    severity="high",
                    description="CORS misconfiguration allows any origin",
                    url=service.url,
                    evidence="Access-Control-Allow-Origin: *"
                ))
        
        return vulnerabilities
    
    async def _detect_technologies(self, service: HTTPService) -> List[str]:
        """Detect technologies from headers and response"""
        technologies = []
        
        # From headers
        tech_headers = {
            'x-powered-by': lambda v: v,
            'server': lambda v: v.split('/')[0] if '/' in v else v,
            'x-generator': lambda v: v
        }
        
        for header, parser in tech_headers.items():
            value = service.headers.get(header, '')
            if value:
                tech = parser(value)
                if tech:
                    technologies.append(tech)
        
        # From response body patterns
        if service.response_body:
            patterns = {
                'WordPress': r'wp-content|wp-includes',
                'Drupal': r'Drupal|drupal',
                'Joomla': r'Joomla|joomla',
                'Django': r'csrfmiddlewaretoken',
                'Ruby on Rails': r'Rails|rails',
                'ASP.NET': r'__VIEWSTATE|aspnet',
                'PHP': r'\.php["\s]',
                'Node.js': r'node\.js|express',
                'React': r'react|React',
                'Angular': r'ng-version|angular',
                'Vue.js': r'vue|Vue',
                # Monitoring and dashboarding tools
                'Grafana': r'grafana|Grafana|grafana\.js|grafana-app|grafana/api|/grafana/',
                'Prometheus': r'prometheus|Prometheus|/metrics|/api/v1/query',
                'Kibana': r'kibana|Kibana|elastic|elasticsearch',
                'Nagios': r'nagios|Nagios',
                'Zabbix': r'zabbix|Zabbix',
                'InfluxDB': r'influxdb|InfluxDB|/query\?db=',
                # Generic monitoring indicators
                'Monitoring Dashboard': r'dashboard|Dashboard|metrics|Metrics|monitoring|Monitoring|telemetry',
                'Time Series DB': r'timeseries|time-series|grafana-datasource'
            }
            
            for tech, pattern in patterns.items():
                if re.search(pattern, service.response_body, re.IGNORECASE):
                    technologies.append(tech)
        
        return list(set(technologies))
    
    async def _analyze_ssl(self, service: HTTPService) -> List[HTTPVulnerability]:
        """Analyze SSL/TLS configuration"""
        vulnerabilities = []
        
        try:
            # Extract hostname and port
            parsed = urlparse(service.url)
            hostname = parsed.hostname
            port = parsed.port or 443
            
            # Get SSL certificate
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    
                    # Check SSL version
                    if version in ['TLSv1', 'TLSv1.1', 'SSLv2', 'SSLv3']:
                        vulnerabilities.append(HTTPVulnerability(
                            type="weak-ssl-version",
                            severity="high",
                            description=f"Weak SSL/TLS version: {version}",
                            url=service.url,
                            evidence=f"Server supports {version}"
                        ))
                    
                    # Check cipher strength
                    if cipher and len(cipher) > 1:
                        cipher_name = cipher[0]
                        if any(weak in cipher_name.lower() for weak in ['rc4', 'des', 'null', 'anon', 'export']):
                            vulnerabilities.append(HTTPVulnerability(
                                type="weak-cipher",
                                severity="medium",
                                description=f"Weak cipher suite: {cipher_name}",
                                url=service.url,
                                evidence=f"Cipher: {cipher_name}"
                            ))
                    
        except Exception:
            pass
            
        return vulnerabilities
    
    def _cross_service_analysis(self, results: HTTPScanResult) -> List[HTTPVulnerability]:
        """Analyze across multiple services for additional vulnerabilities"""
        vulnerabilities = []
        
        # Check for mixed HTTP/HTTPS
        http_services = [s for s in results.services if not s.is_https]
        https_services = [s for s in results.services if s.is_https]
        
        if http_services and https_services:
            for http_service in http_services:
                vulnerabilities.append(HTTPVulnerability(
                    type="mixed-content-risk",
                    severity="medium",
                    description="HTTP service available alongside HTTPS",
                    url=http_service.url,
                    evidence=f"Both HTTP ({http_service.port}) and HTTPS services detected"
                ))
        
        # Check for consistent security headers
        if len(results.services) > 1:
            header_consistency = {}
            for service in results.services:
                for header in ['x-frame-options', 'strict-transport-security']:
                    key = header.lower()
                    if key in [h.lower() for h in service.headers.keys()]:
                        if key not in header_consistency:
                            header_consistency[key] = []
                        header_consistency[key].append(service.url)
            
            for header, urls in header_consistency.items():
                if len(urls) < len(results.services):
                    missing_urls = [s.url for s in results.services if s.url not in urls]
                    for url in missing_urls:
                        vulnerabilities.append(HTTPVulnerability(
                            type="inconsistent-security-headers",
                            severity="low",
                            description=f"Inconsistent {header} header across services",
                            url=url,
                            evidence=f"Header present on {len(urls)} services but missing here"
                        ))
        
        return vulnerabilities
    
    def _check_basic_vulnerabilities(self, service: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Basic vulnerability checks for fallback mode"""
        vulnerabilities = []
        
        # Check for missing security headers
        headers_lower = {k.lower(): v for k, v in service.get('headers', {}).items()}
        
        security_headers = [
            'x-frame-options', 'x-content-type-options', 
            'strict-transport-security', 'content-security-policy'
        ]
        
        for header in security_headers:
            if header not in headers_lower:
                vulnerabilities.append({
                    "type": f"missing-{header}",
                    "severity": "medium",
                    "description": f"Missing {header} security header",
                    "url": service['url']
                })
        
        # Information disclosure
        if 'server' in headers_lower:
            vulnerabilities.append({
                "type": "information-disclosure",
                "severity": "low",
                "description": "Server header exposes version information",
                "url": service['url'],
                "evidence": f"Server: {headers_lower['server']}"
            })
        
        return vulnerabilities
    
    def _count_vuln_severities(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count vulnerabilities by severity for fallback mode"""
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for vuln in vulnerabilities:
            severity = vuln.get('severity', 'low')
            if severity in counts:
                counts[severity] += 1
        return counts
    
    def validate_input(self, target: str, **kwargs) -> Tuple[bool, List[str]]:
        """Validate input parameters"""
        errors = []
        
        if not target:
            errors.append("Target is required")
        
        # Basic target validation
        if target and not re.match(r'^[a-zA-Z0-9.-]+$', target):
            errors.append("Invalid target format")
        
        return len(errors) == 0, errors

    def _build_hostname_list(self, target: str, discovered_hostnames: List[str], subdomains: List[str]) -> List[str]:
        """Build comprehensive list of hostnames to test"""
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
    
    def _is_unique_service(self, new_service: HTTPService, existing_services: List[HTTPService]) -> bool:
        """Check if service is unique (different content/headers from existing ones)"""
        for existing in existing_services:
            if (existing.port == new_service.port and 
                existing.scheme == new_service.scheme):
                
                # Compare key indicators of uniqueness
                same_status = existing.status_code == new_service.status_code
                same_server = existing.server == new_service.server
                same_title = self._extract_title(existing.response_body) == self._extract_title(new_service.response_body)
                same_content_length = len(existing.response_body or '') == len(new_service.response_body or '')
                
                # If all key indicators are the same, consider it duplicate
                if same_status and same_server and same_title and same_content_length:
                    return False
        
        return True
    
    def _extract_title(self, response_body: Optional[str]) -> str:
        """Extract title from HTML response"""
        if not response_body:
            return ""
        
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', response_body, re.IGNORECASE)
        return title_match.group(1).strip() if title_match else ""
    
    def _extract_hostnames_from_response(self, service: HTTPService) -> List[str]:
        """Extract additional hostnames from HTTP response"""
        hostnames = []
        
        # From redirects in Location header
        location = service.headers.get('location', '')
        if location:
            parsed = urlparse(location)
            if parsed.hostname:
                hostnames.append(parsed.hostname)
        
        # From HTML content
        if service.response_body:
            # Find links with different hostnames
            link_pattern = r'https?://([^/\s"\']+)'
            for match in re.finditer(link_pattern, service.response_body):
                hostname = match.group(1)
                if '.' in hostname and not hostname.replace('.', '').isdigit():
                    hostnames.append(hostname)
            
            # Extract from specific HTML elements
            patterns = [
                r'href=["\']https?://([^/\s"\']+)',
                r'src=["\']https?://([^/\s"\']+)',
                r'action=["\']https?://([^/\s"\']+)'
            ]
            
            for pattern in patterns:
                for match in re.finditer(pattern, service.response_body):
                    hostname = match.group(1)
                    if '.' in hostname and not hostname.replace('.', '').isdigit():
                        hostnames.append(hostname)
        
        # Remove duplicates and filter relevant hostnames
        unique_hostnames = list(set(hostnames))
        
        # Filter to only include hostnames that might be related to the target
        filtered = []
        target_parts = self.original_ip.split('.')
        
        for hostname in unique_hostnames:
            # Skip obviously unrelated domains
            if any(skip in hostname.lower() for skip in ['google', 'facebook', 'twitter', 'cdn', 'googleapis']):
                continue
            
            # Include if it shares domain components with target or is a subdomain
            if any(part in hostname for part in target_parts if len(part) > 2):
                filtered.append(hostname)
            elif '.' in self.original_ip and hostname.endswith(self.original_ip.split('.', 1)[1]):
                filtered.append(hostname)
        
        return filtered[:10]  # Limit to prevent excessive discoveries