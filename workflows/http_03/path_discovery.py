"""Path Discovery Engine Module for HTTP_03 Workflow

Handles intelligent path discovery using SmartList algorithm and traditional methods.
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from urllib.parse import urlparse, urljoin
import re

from .models import HTTPService, PathDiscoveryMetadata

# Database imports
try:
    import json
    from pathlib import Path
    database_path = Path(__file__).parent.parent.parent / "database"
    scanner_config_path = database_path / "technologies" / "scanner_config.json"
    
    def load_scanner_config():
        if scanner_config_path.exists():
            with open(scanner_config_path, 'r') as f:
                return json.load(f)
        return {}
    
    SCANNER_CONFIG_AVAILABLE = True
except Exception:
    SCANNER_CONFIG_AVAILABLE = False
    def load_scanner_config():
        return {}

# SmartList imports
try:
    from src.core.tools.smartlist.core import score_wordlists, score_wordlists_with_catalog, ScoringContext
    from src.core.tools.smartlist.utils import get_wordlist_paths
    SMARTLIST_AVAILABLE = True
except ImportError:
    SMARTLIST_AVAILABLE = False

# HTTP dependencies
try:
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

# Utils
from src.core.utils.debugging import debug_print
from workflows.core.command_logger import get_command_logger


class PathDiscoveryEngine:
    """Handles intelligent path discovery using multiple methods"""
    
    def __init__(self, user_agents: List[str], config: Dict[str, Any]):
        """Initialize with user agents and configuration"""
        self.user_agents = user_agents
        self.config = config
        self.original_ip = None  # Set by parent scanner
        self.scanner_config = load_scanner_config()
        self.redirect_analysis = {
            'destinations': {},
            'patterns': [],
            'baseline_responses': []
        }
    
    async def discover_paths(self, service: HTTPService) -> List[str]:
        """Enhanced path discovery with false positive detection"""
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
        
        # Phase 0: Baseline Response Detection (NEW)
        baseline_detected = await self._detect_baseline_responses(service)
        if baseline_detected['is_generic_redirect']:
            debug_print(f"Generic redirect detected: {baseline_detected['redirect_destination']}")
            # Extract hostname and continue with that instead
            if baseline_detected.get('discovered_hostname'):
                debug_print(f"Discovered hostname: {baseline_detected['discovered_hostname']}")
                service.discovered_hostnames = [baseline_detected['discovered_hostname']]
        
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
        
        # 2.5. Technology-aware path discovery (NEW)
        if service.technologies:
            tech_paths = await self._discover_paths_tech_aware(service)
            discovered.extend(tech_paths['paths'])
            total_paths_tested += tech_paths.get('paths_tested', 0)
        
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
        except Exception:
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
        """Extract paths from HTML content"""
        paths = []
        
        # Find all href and src attributes
        links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', html_content)
        for link in links:
            parsed = urlparse(link)
            if parsed.path and parsed.path != '/':
                # Only include relative paths or paths on same domain
                if not parsed.netloc or parsed.netloc == '':
                    paths.append(parsed.path)
        
        return paths
    
    async def _test_paths_batch(self, service: HTTPService, paths: List[str]) -> List[str]:
        """Test a batch of paths efficiently with detailed validation"""
        if not paths or not HTTP_AVAILABLE:
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
            
            # Enhanced validation using baseline analysis
            validation_result = await self._validate_path_with_baseline(response, url, client)
            is_meaningful = validation_result['is_valid']
            
            # Log detailed validation info for debugging
            if validation_result['reasons']:
                debug_print(f"Path {path} validation: {', '.join(validation_result['reasons'])} (confidence: {validation_result['confidence']})")
            
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
                        
                        return False
                        
                    except Exception:
                        return False
                else:
                    # For HEAD requests with content-length, trust the server
                    return True
                    
            except Exception:
                return False
        
        return False
    
    async def _detect_baseline_responses(self, service: HTTPService) -> Dict[str, Any]:
        """Detect baseline responses to identify generic redirects and false positives"""
        if not HTTP_AVAILABLE:
            return {
                'is_generic_redirect': False,
                'redirect_destination': None,
                'discovered_hostname': None,
                'baseline_patterns': []
            }
        
        # Test paths that should not exist
        test_paths = [
            '/4d3f2a1b9c8e7f1a2b3c.html',  # Random non-existent file
            '/nonexistent-path-test-12345',   # Random path
            '/baseline-test-404-check'        # Another test path
        ]
        
        redirect_destinations = {}
        response_patterns = {}
        
        try:
            timeout = 5
            async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
                for test_path in test_paths:
                    try:
                        url = urljoin(service.url, test_path)
                        response = await client.get(
                            url, 
                            headers={"User-Agent": self.user_agents[0]},
                            follow_redirects=False  # Don't follow to analyze redirects
                        )
                        
                        # Track redirect destinations
                        if response.status_code in [301, 302, 307, 308]:
                            location = response.headers.get('location', '')
                            if location:
                                redirect_destinations[location] = redirect_destinations.get(location, 0) + 1
                        
                        # Track response patterns
                        pattern_key = f"{response.status_code}_{len(response.content)}"
                        response_patterns[pattern_key] = response_patterns.get(pattern_key, 0) + 1
                        
                    except Exception as e:
                        debug_print(f"Error testing baseline path {test_path}: {e}")
                        continue
        
        except Exception as e:
            debug_print(f"Baseline response detection error: {e}")
            return {'is_generic_redirect': False, 'redirect_destination': None, 'discovered_hostname': None}
        
        # Analyze results
        analysis = {
            'is_generic_redirect': False,
            'redirect_destination': None,
            'discovered_hostname': None,
            'baseline_patterns': list(response_patterns.keys())
        }
        
        # Check if all/most test paths redirect to the same location
        if redirect_destinations:
            most_common_redirect = max(redirect_destinations.items(), key=lambda x: x[1])
            redirect_location, redirect_count = most_common_redirect
            
            # If >50% of test paths redirect to same location, it's likely generic
            if redirect_count >= len(test_paths) * 0.5:
                analysis['is_generic_redirect'] = True
                analysis['redirect_destination'] = redirect_location
                
                # Try to extract hostname from redirect
                parsed_redirect = urlparse(redirect_location)
                if parsed_redirect.hostname and parsed_redirect.hostname != self.original_ip:
                    analysis['discovered_hostname'] = parsed_redirect.hostname
                    debug_print(f"Discovered hostname from redirect: {parsed_redirect.hostname}")
        
        # Store baseline patterns for later comparison
        self.redirect_analysis['baseline_responses'] = response_patterns
        
        return analysis
    
    async def _validate_path_with_baseline(self, response: 'httpx.Response', url: str, client: 'httpx.AsyncClient') -> Dict[str, Any]:
        """Enhanced path validation using baseline response analysis"""
        path = urlparse(url).path
        status_code = response.status_code
        content_length = len(response.content) if hasattr(response, 'content') else 0
        
        # Check against baseline patterns
        current_pattern = f"{status_code}_{content_length}"
        is_baseline = current_pattern in self.redirect_analysis.get('baseline_responses', {})
        
        # Enhanced redirect analysis
        redirect_info = {'is_redirect': False, 'destination': None, 'is_generic': False}
        if status_code in [301, 302, 307, 308]:
            redirect_info['is_redirect'] = True
            location = response.headers.get('location', '')
            redirect_info['destination'] = location
            
            # Check if this matches our baseline generic redirect
            if location in self.redirect_analysis.get('destinations', {}):
                redirect_info['is_generic'] = True
        
        # Use scanner config for validation if available
        validation_result = {
            'is_valid': False,
            'confidence': 'low',
            'reasons': [],
            'redirect_info': redirect_info,
            'is_baseline_match': is_baseline
        }
        
        # Apply database-driven validation
        if SCANNER_CONFIG_AVAILABLE and self.scanner_config:
            content_validation = self.scanner_config.get('security_analysis', {}).get('content_validation', {})
            valid_status_codes = content_validation.get('valid_status_codes', [200, 301, 302, 401, 403])
            error_indicators = content_validation.get('error_indicators', [])
            
            # Check status code validity
            if status_code in valid_status_codes:
                validation_result['reasons'].append(f'valid_status_{status_code}')
                
                # Skip baseline pattern matches for actual content
                if not is_baseline or status_code not in [301, 302, 307, 308]:
                    validation_result['is_valid'] = True
                    validation_result['confidence'] = 'medium'
                    
                    # Enhanced content validation for successful responses
                    if status_code == 200:
                        try:
                            content = response.text[:1000].lower()
                            
                            # Check for error indicators
                            has_error_indicators = any(indicator in content for indicator in error_indicators)
                            if has_error_indicators:
                                validation_result['is_valid'] = False
                                validation_result['reasons'].append('error_content_detected')
                            else:
                                validation_result['confidence'] = 'high'
                                validation_result['reasons'].append('clean_content')
                                
                        except Exception:
                            pass
        
        # Handle redirects specially
        if redirect_info['is_redirect']:
            if redirect_info['is_generic']:
                validation_result['is_valid'] = False
                validation_result['reasons'].append('generic_redirect')
            elif not is_baseline:
                validation_result['is_valid'] = True
                validation_result['confidence'] = 'medium'
                validation_result['reasons'].append('specific_redirect')
        
        return validation_result
    
    async def _discover_paths_tech_aware(self, service: HTTPService) -> Dict[str, Any]:
        """Technology-aware path discovery using tech_db.json"""
        discovered = []
        paths_tested = 0
        
        if not SCANNER_CONFIG_AVAILABLE:
            return {'paths': [], 'paths_tested': 0}
        
        try:
            # Load tech database
            tech_db_path = database_path / "technologies" / "tech_db.json"
            if not tech_db_path.exists():
                return {'paths': [], 'paths_tested': 0}
            
            with open(tech_db_path, 'r') as f:
                tech_db = json.load(f)
            
            # Get server-specific paths from scanner config
            server_paths = self.scanner_config.get('path_discovery', {}).get('server_specific_paths', {})
            
            tech_specific_paths = []
            
            # Match detected technologies with database entries
            for technology in service.technologies:
                tech_lower = technology.lower()
                
                # Search through all tech categories
                for category, technologies in tech_db.items():
                    if tech_lower in technologies:
                        tech_info = technologies[tech_lower]
                        
                        # Get discovery paths from tech database
                        discovery_paths = tech_info.get('discovery_paths', [])
                        tech_specific_paths.extend(discovery_paths)
                        
                        # Get path patterns from indicators
                        indicators = tech_info.get('indicators', {})
                        path_patterns = indicators.get('path_patterns', [])
                        tech_specific_paths.extend(path_patterns)
                        
                        debug_print(f"Found {len(discovery_paths)} tech-specific paths for {technology}")
                        break
                
                # Also check server-specific paths
                if tech_lower in server_paths:
                    tech_specific_paths.extend(server_paths[tech_lower])
            
            # Remove duplicates
            unique_tech_paths = list(set(tech_specific_paths))
            
            if unique_tech_paths:
                debug_print(f"Testing {len(unique_tech_paths)} technology-specific paths")
                
                # Test the technology-specific paths
                valid_paths = await self._test_paths_batch(service, unique_tech_paths)
                discovered.extend(valid_paths)
                paths_tested = len(unique_tech_paths)
                
                # Log the technology-specific discovery
                base_url = service.url.rstrip('/')
                get_command_logger().log_command("http_03", f"# Technology-aware paths for {', '.join(service.technologies)}")
                for path in unique_tech_paths[:5]:  # Show first 5 as examples
                    get_command_logger().log_command("http_03", f"curl -s -o /dev/null -w '%{{http_code}}' {base_url}{path}")
        
        except Exception as e:
            debug_print(f"Technology-aware path discovery error: {e}")
        
        return {
            'paths': discovered,
            'paths_tested': paths_tested,
            'method': 'technology_aware'
        }