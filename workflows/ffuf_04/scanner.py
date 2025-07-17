"""
Ffuf Scanner with Intelligent Wordlist Selection

Uses the wordlist scorer to select optimal wordlists based on previous scan results
and service context for web fuzzing with ffuf.
"""

import subprocess
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile

from workflows.core.base import BaseWorkflow
from database.scorer.scorer_engine import score_wordlists
from database.scorer.models import ScoringContext
from database.scorer.cache import ScorerCache
from utils.results import result_manager

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
                for port_data in host_data.get('ports', []):
                    service = port_data.get('service', {}).get('name', '')
                    port = port_data.get('port')
                    state = port_data.get('state', {}).get('state', '')
                    
                    if state == 'open' and any(svc in service.lower() for svc in ['http', 'https', 'web']):
                        http_services.append({
                            'host': host_data.get('address'),
                            'port': port,
                            'service': service,
                            'ssl': 'https' in service.lower() or port == 443
                        })
        
        # Check HTTP workflow results
        if 'http' in previous_results:
            http_data = previous_results['http'].get('data', {})
            for service in http_data.get('services', []):
                if service not in http_services:
                    http_services.append(service)
                    
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
                if (http_service.get('host') == service['host'] and 
                    http_service.get('port') == service['port']):
                    headers = http_service.get('headers', {})
                    # Extract server header as tech
                    if 'Server' in headers:
                        tech = headers['Server']
                    # Extract powered-by header as tech (fallback)
                    elif 'X-Powered-By' in headers:
                        tech = headers['X-Powered-By']
        
        return ScoringContext(
            target=service['host'],
            port=service['port'],
            service=service.get('service', 'http'),
            tech=tech,
            headers=headers
        )
    
    def _run_ffuf(self, target_url: str, wordlist_path: str, extensions: List[str] = None) -> Dict[str, Any]:
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
            
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    logger.error("Failed to parse ffuf JSON output")
                    return {'error': 'Failed to parse output', 'raw': result.stdout}
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
            scan_result = self._run_ffuf(target_url, selected_wordlist, extensions)
            
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
                self.cache.record_outcome(
                    context=context,
                    wordlist_id=selected_wordlist,
                    outcome='success' if success else 'failure',
                    details={'findings_count': len(findings)}
                )
            except Exception as e:
                logger.warning(f"Failed to update cache: {e}")
        
        # Results will be saved by the main workflow coordinator
        # Individual workflows just return their data
        
        return self._create_result(True, data={
            'services_scanned': len(results),
            'results': results
        })
    
    def validate_input(self, target: str = None, **kwargs) -> bool:
        """Validate scanner input."""
        return bool(target and isinstance(target, str))
    
    def _create_result(self, success: bool, data: Dict[str, Any] = None, error: str = None) -> Dict[str, Any]:
        """Create a standardized result dictionary."""
        return {
            'success': success,
            'data': data or {},
            'error': error
        }