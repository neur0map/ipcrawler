"""
Path discovery for HTTP scanner workflow.

This module handles SmartList integration, traditional path discovery,
HTML content parsing, and comprehensive path validation.
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse, urljoin
from .models import HTTPService, PathDiscoveryMetadata
from .config import get_scanner_config
from .utils import extract_paths_from_html, get_valid_status_codes, get_error_indicators, get_valid_content_indicators
from workflows.core.command_logger import get_command_logger
from utils.debug import debug_print


class PathDiscovery:
    """Path discovery handler with SmartList and traditional methods"""
    
    def __init__(self, original_ip: str):
        self.config = get_scanner_config()
        self.original_ip = original_ip
    
    async def discover_paths(self, service: HTTPService) -> List[str]:
        """
        Enhanced path discovery using SmartList algorithm and traditional methods.
        
        Args:
            service: HTTPService object to scan
            
        Returns:
            List of discovered paths
        """
        start_time = time.time()
        discovered = []
        total_paths_tested = 0
        discovery_method = "basic"
        wordlist_used = None
        confidence = None
        
        # Get configuration - simple enhanced discovery toggle
        discovery_config = self.config.get_discovery_config()
        enhanced_discovery = discovery_config.get('enhanced', True)
        
        smartlist_enabled = enhanced_discovery and self.config.smartlist_available
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
            html_paths = extract_paths_from_html(service.response_body, self.config.scanner_config_manager)
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
        """
        Use SmartList algorithm for intelligent path discovery.
        
        Args:
            service: HTTPService object
            
        Returns:
            Dictionary with discovery results
        """
        if not self.config.smartlist_available:
            return {'paths': [], 'paths_tested': 0}
        
        try:
            from src.core.scorer import (
                score_wordlists_with_catalog, score_wordlists, 
                get_wordlist_paths, ScoringContext
            )
        except ImportError:
            debug_print("SmartList imports failed", level="WARNING")
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
        concurrency = self.config.get_concurrency_limits()
        max_wordlists = concurrency.get('max_wordlists', 3)
        max_paths_per_wordlist = concurrency.get('max_paths_per_wordlist', 100)
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
                    get_command_logger().log_command(
                        "http_03", 
                        f"ffuf -w {wordlist_path}:FUZZ -u {base_url}/FUZZ -mc 200,301,302,401,403 -t 20"
                    )
                    
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
        """
        Traditional path discovery methods.
        
        Args:
            service: HTTPService object
            config: Discovery configuration
            
        Returns:
            Dictionary with discovery results
        """
        discovered = []
        paths_tested = 0
        
        # Common application patterns from database
        common_paths = []
        if self.config.scanner_config_manager:
            try:
                common_paths = self.config.scanner_config_manager.get_common_application_paths()
            except Exception as e:
                debug_print(f"Error getting common paths from database: {e}", level="WARNING")
        
        # Fallback patterns if database unavailable
        if not common_paths:
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
            db_paths = self.config.get_service_specific_paths(port)
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
        
        # Technology-specific paths from database
        tech_paths = self._get_technology_specific_paths(service)
        
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
    
    def _get_technology_specific_paths(self, service: HTTPService) -> List[str]:
        """
        Get technology-specific paths based on detected technologies and server.
        
        Args:
            service: HTTPService object
            
        Returns:
            List of technology-specific paths
        """
        tech_paths = []
        
        # Technology-specific paths from database
        if service.server and self.config.scanner_config_manager:
            try:
                server_lower = service.server.lower()
                for server_type in ['apache', 'nginx', 'tomcat', 'iis', 'jetty']:
                    if server_type in server_lower:
                        server_paths = self.config.scanner_config_manager.get_server_specific_paths(server_type)
                        tech_paths.extend(server_paths)
                        break
            except Exception as e:
                debug_print(f"Error getting server-specific paths: {e}", level="WARNING")
        
        # Fallback server-specific paths if database unavailable
        elif service.server:
            server_lower = service.server.lower()
            if 'apache' in server_lower:
                tech_paths.extend(['/server-status', '/server-info'])
            elif 'nginx' in server_lower:
                tech_paths.extend(['/nginx_status'])
            elif 'tomcat' in server_lower:
                tech_paths.extend(['/manager/', '/host-manager/'])
        
        # Add monitoring-specific paths based on content analysis
        monitoring_paths = self._get_monitoring_specific_paths(service)
        tech_paths.extend(monitoring_paths)
        
        return tech_paths
    
    def _get_monitoring_specific_paths(self, service: HTTPService) -> List[str]:
        """
        Get monitoring-specific paths based on response content analysis.
        
        Args:
            service: HTTPService object
            
        Returns:
            List of monitoring-specific paths
        """
        monitoring_paths = []
        
        if not service.response_body:
            return monitoring_paths
        
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
        
        return monitoring_paths
    
    async def _test_paths_batch(self, service: HTTPService, paths: List[str]) -> List[str]:
        """
        Test a batch of paths efficiently with detailed validation.
        
        Args:
            service: HTTPService object
            paths: List of paths to test
            
        Returns:
            List of valid paths
        """
        if not paths:
            return []
        
        if not self.config.deps_available:
            debug_print("HTTP dependencies not available for path testing")
            return []
        
        try:
            import httpx
        except ImportError:
            debug_print("httpx not available for path testing")
            return []
        
        # Get settings from config
        timeout_settings = self.config.get_timeout_settings()
        concurrency = self.config.get_concurrency_limits()
        max_concurrent = concurrency.get('max_concurrent', 20)
        
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
        
        async with httpx.AsyncClient(
            verify=False, 
            timeout=httpx.Timeout(connect=timeout_settings['connect'], read=timeout_settings['read'])
        ) as client:
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
            
            # Run technology detection on discovered paths that might contain new tech
            if valid_paths and self.config.technology_matcher:
                try:
                    from .tech_detector import TechnologyDetector
                    tech_detector = TechnologyDetector()
                    await tech_detector.run_tech_detection_on_paths(service, valid_paths)
                except Exception as e:
                    debug_print(f"Error running tech detection on paths: {e}", level="WARNING")
            
            return valid_paths
    
    async def _check_path_with_stats(self, client, url: str, stats: dict) -> Tuple[str, bool]:
        """
        Check path with actual command logging and statistics.
        
        Args:
            client: httpx.AsyncClient instance
            url: Full URL to test
            stats: Statistics dictionary to update
            
        Returns:
            Tuple of (path, is_valid)
        """
        path = urlparse(url).path
        stats['total_tested'] += 1
        
        try:
            # Try HEAD first for efficiency
            response = await client.head(url, headers={"User-Agent": self.config.get_user_agents()[0]})
            
            # Track status codes
            status_code = response.status_code
            stats['status_counts'][status_code] = stats['status_counts'].get(status_code, 0) + 1
            
            # If HEAD fails, try GET for directories
            if response.status_code in [405, 501]:  # Method not allowed
                response = await client.get(url, headers={"User-Agent": self.config.get_user_agents()[0]})
                stats['status_counts'][response.status_code] = stats['status_counts'].get(response.status_code, 0) + 1
            
            # Get valid status codes
            valid_status_codes = get_valid_status_codes(self.config.scanner_config_manager)
            
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
    
    async def _validate_path_content(self, response, url: str, client) -> bool:
        """
        Validate that the path contains meaningful content.
        
        Args:
            response: httpx.Response object
            url: Full URL
            client: httpx.AsyncClient instance
            
        Returns:
            True if content is meaningful, False otherwise
        """
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
                        get_response = await client.get(url, headers={"User-Agent": self.config.get_user_agents()[0]})
                        if get_response.status_code != status_code:
                            return False
                        
                        content = get_response.text[:1000]  # First 1KB only
                        
                        # Exclude empty or minimal responses
                        if len(content.strip()) < 10:
                            return False
                        
                        # Filter out default error pages
                        error_indicators = get_error_indicators(self.config.scanner_config_manager)
                        
                        content_lower = content.lower()
                        for indicator in error_indicators:
                            if indicator in content_lower:
                                return False
                        
                        # Check if it's likely a real file/directory
                        # Files with extensions are more likely to be real
                        path = urlparse(url).path
                        if '.' in path.split('/')[-1]:  # Has file extension
                            return True
                        
                        # Check for meaningful content indicators
                        valid_content_indicators = get_valid_content_indicators(self.config.scanner_config_manager)
                        
                        # Directories with meaningful content
                        if any(tag in content_lower for tag in valid_content_indicators):
                            return True
                        
                        # JSON/API responses
                        if get_response.headers.get('content-type', '').startswith('application/json'):
                            return True
                        
                        return True  # Default to true for other content
                        
                    except Exception:
                        # If GET fails, assume HEAD was correct
                        return True
                
                return True  # Valid status with content-length
                
            except Exception:
                return True  # Default to true if we can't validate content
        
        return False