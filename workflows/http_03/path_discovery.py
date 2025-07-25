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
    
    async def discover_paths(self, service: HTTPService) -> List[str]:
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
                        
                        return False
                        
                    except Exception:
                        return False
                else:
                    # For HEAD requests with content-length, trust the server
                    return True
                    
            except Exception:
                return False
        
        return False