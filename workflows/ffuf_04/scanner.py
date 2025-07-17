"""
Ffuf Scanner with Intelligent Wordlist Selection

Uses the wordlist scorer to select optimal wordlists based on previous scan results
and service context for web fuzzing with ffuf.
"""

import subprocess
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from workflows.core.base import BaseWorkflow
from database.scorer.scorer_engine import score_wordlists, get_wordlist_paths
from database.scorer.models import ScoringContext
from database.scorer.cache import ScorerCache

logger = logging.getLogger(__name__)


class FfufScanner(BaseWorkflow):
    """Ffuf web fuzzing scanner with intelligent wordlist selection."""
    
    def __init__(self):
        super().__init__("ffuf")
        self.cache = ScorerCache()
        
    def _get_http_services(self, previous_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract HTTP/HTTPS services from previous scan results."""
        http_services = []
        
        # Check nmap results for web services
        if 'nmap_fast' in previous_results:
            nmap_data = previous_results['nmap_fast'].get('data', {})
            for host_data in nmap_data.get('hosts', []):
                if not isinstance(host_data, dict):
                    continue
                    
                for port_data in host_data.get('ports', []):
                    if not isinstance(port_data, dict):
                        continue
                        
                    # Handle both string and dict formats for service field
                    service = port_data.get('service', '')
                    if isinstance(service, dict):
                        service = service.get('name', '')
                    elif not isinstance(service, str):
                        service = str(service) if service else ''
                    
                    port = port_data.get('port')
                    
                    # Handle both string and dict formats for state field  
                    state = port_data.get('state', '')
                    if isinstance(state, dict):
                        state = state.get('state', '')
                    elif not isinstance(state, str):
                        state = str(state) if state else ''
                    
                    # Ensure we have valid data before processing
                    if not service or not port or not state:
                        continue
                    
                    if state == 'open' and any(svc in service.lower() for svc in ['http', 'https', 'web']):
                        host_ip = host_data.get('ip') or host_data.get('address')
                        if host_ip:
                            http_services.append({
                                'host': host_ip,
                                'port': port,
                                'service': service,
                                'ssl': 'https' in service.lower() or port == 443
                            })
        
        # Check HTTP workflow results
        if 'http' in previous_results:
            http_data = previous_results['http'].get('data', {})
            for service in http_data.get('services', []):
                # Convert HTTP service format to expected format
                if 'actual_target' in service or 'url' in service:
                    # Extract host from actual_target or url
                    host = service.get('actual_target')
                    if not host and 'url' in service:
                        # Parse host from URL
                        from urllib.parse import urlparse
                        parsed = urlparse(service['url'])
                        host = parsed.hostname
                    
                    if host:
                        # Convert to expected format
                        converted_service = {
                            'host': host,
                            'port': service.get('port', 80),
                            'service': 'https' if service.get('is_https') else 'http',
                            'ssl': service.get('is_https', False)
                        }
                        
                        # Avoid duplicates
                        if converted_service not in http_services:
                            http_services.append(converted_service)
        
        return http_services
    
    def _build_scoring_context(self, service: Dict[str, Any], previous_results: Dict[str, Any]) -> ScoringContext:
        """Build scoring context from service information and previous results."""
        # Extract technology information
        tech = None
        headers = {}
        
        # Get HTTP response data if available
        if 'http' in previous_results:
            http_data = previous_results['http'].get('data', {})
            for http_service in http_data.get('services', []):
                # Compare using actual_target or parsed URL since we normalized the data
                service_host = service.get('host')
                http_host = http_service.get('actual_target')
                if not http_host and 'url' in http_service:
                    from urllib.parse import urlparse
                    parsed = urlparse(http_service['url'])
                    http_host = parsed.hostname
                
                if (http_host == service_host and 
                    http_service.get('port') == service.get('port')):
                    headers = http_service.get('headers', {})
                    # Extract server header as tech
                    if 'server' in headers:
                        tech = headers['server']
                    elif 'Server' in headers:
                        tech = headers['Server']
                    # Extract powered-by header as tech (fallback)
                    elif 'x-powered-by' in headers:
                        tech = headers['x-powered-by']
                    elif 'X-Powered-By' in headers:
                        tech = headers['X-Powered-By']
        
        return ScoringContext(
            target=service['host'],
            port=service['port'],
            service=service.get('service', 'http'),
            tech=tech,
            headers=headers
        )
    
    def _run_ffuf(self, target_url: str, wordlist_path: str, extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run ffuf with the selected wordlist."""
        try:
            # Prepare ffuf command
            cmd = [
                'ffuf',
                '-u', f"{target_url}/FUZZ",
                '-w', wordlist_path,
                '-mc', 'all',  # Match all status codes
                '-fc', '404',  # Filter out 404s
                '-t', '40',    # 40 threads
                '-timeout', '10',
                '-H', 'User-Agent: Mozilla/5.0 (compatible; ipcrawler/1.0)',
                '-o', '-',     # Output to stdout
                '-of', 'json', # JSON output format
                '-s'           # Silent mode
            ]
            
            # Add extensions if specified
            if extensions:
                ext_string = ','.join(extensions)
                cmd.extend(['-e', ext_string])
            
            logger.info(f"Running ffuf on {target_url} with wordlist: {wordlist_path}")
            
            # Run ffuf
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                if result.stdout.strip():
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse ffuf JSON output. Raw output: {result.stdout[:500]}")
                        # Return empty results structure when no valid JSON but command succeeded
                        return {'results': [], 'error': None}
                else:
                    # No output typically means no findings
                    logger.info("ffuf returned no output - likely no findings")
                    return {'results': []}
            else:
                return {'error': result.stderr or 'ffuf failed', 'returncode': result.returncode}
                
        except subprocess.TimeoutExpired:
            logger.warning(f"ffuf timeout for {target_url}")
            return {'error': 'Timeout expired'}
        except Exception as e:
            logger.error(f"ffuf error for {target_url}: {str(e)}")
            return {'error': str(e)}
    
    async def execute(self, target: str, previous_results: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Execute ffuf scanning with intelligent wordlist selection."""
        if not self.validate_input(target=target):
            return self._create_result(False, error="Invalid target")
        
        # We'll use the global result_manager, no need to create one
        
        if not previous_results:
            return self._create_result(False, error="No previous results available for service detection")
        
        # Get HTTP services from previous scans
        http_services = self._get_http_services(previous_results)
        
        if not http_services:
            return self._create_result(True, data={'message': 'No HTTP services found'})
        
        results = []
        
        for service in http_services:
            # Build target URL
            protocol = 'https' if service.get('ssl') else 'http'
            target_url = f"{protocol}://{service['host']}:{service['port']}"
            
            # Build scoring context
            context = self._build_scoring_context(service, previous_results)
            
            # Get wordlist recommendation
            recommendation = score_wordlists(context)
            
            if not recommendation or not recommendation.wordlists:
                logger.warning(f"No wordlist recommendation for {target_url}")
                continue
            
            # Use the first recommended wordlist
            selected_wordlist = recommendation.wordlists[0]
            logger.info(f"Selected wordlist: {selected_wordlist} (confidence: {recommendation.confidence}, score: {recommendation.score:.2f})")
            
            # Resolve wordlist name to actual file path
            try:
                wordlist_paths = get_wordlist_paths([selected_wordlist], tech=context.tech, port=context.port)
                if wordlist_paths:
                    wordlist_path = wordlist_paths[0]
                    logger.info(f"Resolved wordlist path: {wordlist_path}")
                else:
                    logger.warning(f"Could not resolve wordlist path for {selected_wordlist}, skipping...")
                    continue
            except Exception as e:
                logger.error(f"Error resolving wordlist path: {e}")
                continue
            
            # Save selection to cache
            cache_entry_id = self.cache.save_selection(context, recommendation)
            
            # Determine extensions based on context
            extensions = []
            tech_lower = (context.tech or '').lower()
            if 'php' in tech_lower:
                extensions.extend(['.php', '.php3', '.php4', '.php5', '.phtml'])
            if 'asp' in tech_lower or 'iis' in tech_lower:
                extensions.extend(['.asp', '.aspx', '.ashx', '.asmx'])
            if 'java' in tech_lower or 'tomcat' in tech_lower:
                extensions.extend(['.jsp', '.jsf', '.do'])
            if not extensions:
                extensions = ['.php', '.html', '.txt', '.xml']
            
            # Run ffuf
            scan_result = self._run_ffuf(target_url, wordlist_path, extensions)
            
            # Process results
            findings = []
            if 'results' in scan_result:
                for item in scan_result['results']:
                    findings.append({
                        'url': item.get('url'),
                        'status': item.get('status'),
                        'length': item.get('length'),
                        'words': item.get('words'),
                        'lines': item.get('lines')
                    })
            
            result_entry = {
                'target': target_url,
                'wordlist': selected_wordlist,
                'confidence': recommendation.confidence,
                'score': recommendation.score,
                'matched_rules': recommendation.matched_rules,
                'findings': findings,
                'error': scan_result.get('error')
            }
            
            results.append(result_entry)
            
            # Update cache with outcome
            success = len(findings) > 0 and 'error' not in scan_result
            try:
                outcome_data = {
                    'success': success,
                    'findings_count': len(findings),
                    'wordlist_used': selected_wordlist,
                    'scan_timestamp': datetime.now().isoformat()
                }
                self.cache.update_outcome(cache_entry_id, outcome_data)
            except Exception as e:
                logger.warning(f"Failed to update cache: {e}")
        
        # Results will be saved by the main workflow coordinator
        # Individual workflows just return their data
        
        return self._create_result(True, data={
            'services_scanned': len(results),
            'results': results
        })
    
    def validate_input(self, target: Optional[str] = None, **kwargs) -> bool:
        """Validate scanner input."""
        return bool(target and isinstance(target, str))
    
    def _create_result(self, success: bool, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> Dict[str, Any]:
        """Create a standardized result dictionary."""
        return {
            'success': success,
            'data': data or {},
            'error': error
        }