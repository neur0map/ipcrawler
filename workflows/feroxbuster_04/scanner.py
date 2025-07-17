"""
Feroxbuster Scanner with Intelligent Wordlist Selection

Uses the wordlist scorer to select optimal wordlists based on previous scan results
and service context for web directory and file discovery with feroxbuster.
"""

import subprocess
import json
import logging
import threading
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from workflows.core.base import BaseWorkflow
from database.scorer.scorer_engine import score_wordlists_with_catalog, get_wordlist_paths
from database.scorer.models import ScoringContext
from database.scorer.cache import ScorerCache

logger = logging.getLogger(__name__)


class FeroxbusterScanner(BaseWorkflow):
    """Feroxbuster web directory scanner with intelligent wordlist selection."""
    
    def __init__(self):
        super().__init__("feroxbuster")
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
    
    def _run_feroxbuster(self, target_url: str, wordlist_path: str, extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run feroxbuster with the selected wordlist."""
        try:
            # Prepare feroxbuster command with performance optimizations and proper filtering
            cmd = [
                'feroxbuster',
                '--url', target_url,
                '--wordlist', wordlist_path,
                '--status-codes', '200,301,302,403,405',  # Include useful status codes
                '--threads', '50',  # High thread count for speed
                '--timeout', '8',   # 8 second timeout
                '--user-agent', 'Mozilla/5.0 (compatible; ipcrawler/1.0)',
                '--output', '-',    # Output to stdout
                '--json',          # JSON output for parsing
                '--silent',        # Reduce noise
                '--no-recursion',  # Don't recurse directories for initial scan
                '--filter-size', '0'       # Filter out zero-byte responses
            ]
            
            # Add extensions if specified
            if extensions:
                # Limit to 5 extensions max to avoid command line issues
                limited_extensions = extensions[:5]
                for ext in limited_extensions:
                    cmd.extend(['--extensions', ext.lstrip('.')])  # Remove leading dot
            
            logger.info(f"Running feroxbuster on {target_url} with wordlist: {wordlist_path}")
            logger.info(f"🎯 Filtering: 200,301,302,403,405 status codes, excluding zero-byte files")
            if extensions:
                logger.info(f"Extensions: {extensions[:5]}")
                
            # Log wordlist size for performance expectations
            try:
                wordlist_size = sum(1 for _ in open(wordlist_path, 'r', errors='ignore'))
                total_requests = wordlist_size * len(extensions) if extensions else wordlist_size
                expected_time = total_requests / (50 * 8)  # rough estimate: 50 threads * ~8 req/sec/thread
                logger.info(f"Wordlist size: {wordlist_size:,} entries, ~{total_requests:,} total requests, estimated {expected_time:.0f}s")
            except:
                pass
            
            # Live timer setup
            timer_running = threading.Event()
            timer_running.set()
            start_time = time.time()
            
            # Extract wordlist filename for display
            wordlist_name = os.path.basename(wordlist_path)
            
            def live_timer():
                """Display live elapsed time while feroxbuster runs."""
                while timer_running.is_set():
                    elapsed = time.time() - start_time
                    minutes = int(elapsed // 60)
                    seconds = int(elapsed % 60)
                    
                    # Clear current line and print timer with wordlist name (truncate if too long)
                    display_name = wordlist_name if len(wordlist_name) <= 30 else wordlist_name[:27] + "..."
                    timer_text = f'  → Scanning with feroxbuster using {display_name}... {minutes:02d}:{seconds:02d} elapsed'
                    sys.stdout.write(f'\r{timer_text}' + ' ' * 50)  # More padding to clear old text
                    sys.stdout.write(f'\r{timer_text}')  # Write the actual text
                    sys.stdout.flush()
                    
                    time.sleep(1)
            
            # Start timer thread
            timer_thread = threading.Thread(target=live_timer, daemon=True)
            timer_thread.start()
            
            # Run feroxbuster
            logger.info(f"Running feroxbuster command: {' '.join(cmd)}")
            
            try:
                # Run feroxbuster with explicit encoding and reasonable timeout
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')  # 5 minute max
            finally:
                # Stop timer and clear line
                timer_running.clear()
                elapsed = time.time() - start_time
                completion_text = f'  ✓ Feroxbuster scan completed in {elapsed:.2f}s'
                sys.stdout.write(f'\r{completion_text}' + ' ' * 30)  # Clear any remaining timer text
                sys.stdout.write(f'\r{completion_text}\n')  # Write completion message
                sys.stdout.flush()
            
            # Debug logging
            logger.debug(f"feroxbuster return code: {result.returncode}")
            logger.debug(f"feroxbuster stdout length: {len(result.stdout)}")
            logger.debug(f"feroxbuster stderr length: {len(result.stderr)}")
            
            if result.stderr:
                logger.warning(f"feroxbuster stderr: {result.stderr[:500]}")
            
            if result.returncode == 0:
                if result.stdout.strip():
                    # Parse newline-delimited JSON records
                    results = []
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            try:
                                json_obj = json.loads(line)
                                # Additional filtering to remove noise
                                if self._is_valid_finding(json_obj):
                                    results.append(json_obj)
                            except json.JSONDecodeError as e:
                                logger.debug(f"Failed to parse JSON line: {e}")
                                logger.debug(f"Problematic line: {line[:200]}")
                                continue
                    
                    logger.info(f"feroxbuster found {len(results)} valid findings")
                    return {'results': results}
                else:
                    # No output typically means no findings
                    logger.info("feroxbuster returned no output - no findings")
                    return {'results': []}
            else:
                error_msg = result.stderr or 'feroxbuster command failed'
                logger.error(f"feroxbuster failed with return code {result.returncode}: {error_msg}")
                return {'error': error_msg, 'returncode': result.returncode}
                
        except subprocess.TimeoutExpired:
            logger.warning(f"feroxbuster timeout for {target_url}")
            return {'error': 'Timeout expired'}
        except FileNotFoundError:
            logger.error("feroxbuster not found. Please install feroxbuster first.")
            return {'error': 'feroxbuster not found'}
        except Exception as e:
            logger.error(f"feroxbuster error for {target_url}: {str(e)}")
            return {'error': str(e)}
    
    def _is_valid_finding(self, finding: Dict[str, Any]) -> bool:
        """Filter out noise and low-value findings."""
        try:
            url = finding.get('url', '')
            status = finding.get('status', 0)
            length = finding.get('content_length', 0)
            
            # Accept useful status codes
            if status not in [200, 301, 302, 403, 405]:
                return False
            
            # Filter out very small responses for 200 status (likely error pages)
            if status == 200 and length < 50:
                return False
            
            # Filter out very common false positives in URL
            url_lower = url.lower()
            false_positives = [
                'error', 'notfound', '404', 'invalid', 'missing',
                'default', 'empty', 'blank', 'placeholder'
            ]
            
            for fp in false_positives:
                if fp in url_lower:
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Error validating finding: {e}")
            return True  # Be permissive if validation fails
    
    def _get_catalog_wordlists_direct(self, context: ScoringContext) -> List[str]:
        """
        Direct catalog search to bypass broken category indexing.
        Returns actual SecLists wordlist names for web content.
        """
        try:
            from database.wordlists.resolver import resolver
            
            if not resolver.is_available():
                logger.warning("Catalog not available")
                return []
            
            # Direct search for directory-related wordlists
            search_terms = ['directory', 'dirs', 'web', 'content']
            all_matches = set()
            
            for term in search_terms:
                matches = resolver.search_wordlists(term, max_results=20)
                for entry in matches:
                    # Filter for web-relevant wordlists
                    if (entry.category.value == 'web-content' or 
                        'directories' in entry.tags or
                        any(port in [80, 443, 8080, 8443] for port in entry.port_compatibility)):
                        all_matches.add(entry.name)
            
            # Convert to list and sort by preference
            wordlist_names = list(all_matches)
            
            # Prioritize common good wordlists by size and effectiveness
            priority_patterns = [
                ('directory-list-2.3-small', 'small'),           # ~87k entries - fast
                ('raft-small-directories', 'small'),             # Small wordlist
                ('directory-list-lowercase-2.3-small', 'small'), # ~87k entries - fast
                ('raft-medium-directories', 'medium'),           # Medium size
                ('directory-list-2.3-medium', 'large'),          # ~220k entries - slow
                ('directory-list-lowercase-2.3-medium', 'large') # ~220k entries - slow
            ]
            
            sorted_wordlists = []
            # First add small/fast wordlists
            for pattern, size in priority_patterns:
                if size == 'small':
                    matches = [w for w in wordlist_names if pattern in w.lower()]
                    sorted_wordlists.extend(matches)
                    # Remove matches from remaining list
                    wordlist_names = [w for w in wordlist_names if w not in matches]
            
            # Then add medium wordlists
            for pattern, size in priority_patterns:
                if size == 'medium':
                    matches = [w for w in wordlist_names if pattern in w.lower()]
                    sorted_wordlists.extend(matches)
                    wordlist_names = [w for w in wordlist_names if w not in matches]
            
            # Finally add large wordlists (only if needed)
            for pattern, size in priority_patterns:
                if size == 'large':
                    matches = [w for w in wordlist_names if pattern in w.lower()]
                    sorted_wordlists.extend(matches)
                    wordlist_names = [w for w in wordlist_names if w not in matches]
            
            logger.info(f"Found {len(sorted_wordlists)} catalog wordlists: {sorted_wordlists[:3]}...")
            return sorted_wordlists[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Failed to get catalog wordlists: {e}")
            return []
    
    def _get_intelligent_wordlists(self, context: ScoringContext) -> List[str]:
        """
        Get wordlists using full intelligence: port database + scorer + catalog.
        This provides complete visibility into the recommendation process.
        """
        try:
            logger.info("🧠 Starting intelligent wordlist selection...")
            logger.info(f"📊 Context: {context.target}:{context.port} | Tech: {context.tech} | Service: {context.service}")
            
            # Step 1: Check port database for specific recommendations
            port_recommendations = self._get_port_database_recommendations(context)
            logger.info(f"🔌 Port database recommendations: {port_recommendations}")
            
            # Step 2: Get scorer recommendations with catalog integration
            scorer_recommendations = self._get_scorer_recommendations(context)
            logger.info(f"🎯 Scorer recommendations: {scorer_recommendations}")
            
            # Step 3: Get catalog wordlists as fallback
            catalog_recommendations = self._get_catalog_wordlists_direct(context)
            logger.info(f"📚 Catalog fallback: {catalog_recommendations[:3]}...")
            
            # Step 4: Combine intelligently with priority
            final_wordlists = []
            
            # Priority 1: Port database high-priority wordlists
            if port_recommendations.get('high'):
                final_wordlists.extend(port_recommendations['high'])
                logger.info(f"✅ Added port database HIGH priority: {port_recommendations['high']}")
            
            # Priority 2: Scorer recommendations (if available)
            if scorer_recommendations:
                for wl in scorer_recommendations[:3]:  # Top 3 scorer picks
                    if wl not in final_wordlists:
                        final_wordlists.append(wl)
                logger.info(f"✅ Added scorer top picks: {scorer_recommendations[:3]}")
            
            # Priority 3: Port database medium-priority
            if port_recommendations.get('medium'):
                for wl in port_recommendations['medium']:
                    if wl not in final_wordlists:
                        final_wordlists.append(wl)
                logger.info(f"✅ Added port database MEDIUM priority: {port_recommendations['medium']}")
            
            # Priority 4: Catalog recommendations as fallback
            for wl in catalog_recommendations[:3]:
                if wl not in final_wordlists:
                    final_wordlists.append(wl)
            logger.info(f"✅ Added catalog fallback: {[w for w in catalog_recommendations[:3] if w not in final_wordlists]}")
            
            # Ensure we have at least one wordlist
            if not final_wordlists:
                final_wordlists = catalog_recommendations[:1]
                logger.warning("⚠️ No intelligent recommendations found, using catalog fallback")
            
            logger.info(f"🎉 Final intelligent selection: {final_wordlists}")
            return final_wordlists
            
        except Exception as e:
            logger.error(f"❌ Intelligence system failed: {e}")
            return self._get_catalog_wordlists_direct(context)
    
    def _get_port_database_recommendations(self, context: ScoringContext) -> Dict[str, List[str]]:
        """Get wordlist recommendations from the port database."""
        try:
            import json
            with open('database/ports/port_db.json', 'r') as f:
                port_db = json.load(f)
            
            port_str = str(context.port)
            if port_str in port_db:
                port_info = port_db[port_str]
                wordlists = port_info.get('associated_wordlists', {})
                
                # Log port intelligence
                tech_stack = port_info.get('tech_stack', {})
                classification = port_info.get('classification', {})
                logger.info(f"🔍 Port {context.port} intelligence:")
                logger.info(f"  📋 Classification: {classification.get('category', 'unknown')}")
                logger.info(f"  ⚙️ Tech stack: {tech_stack}")
                logger.info(f"  📝 Description: {port_info.get('description', 'N/A')[:100]}...")
                
                return wordlists
            else:
                logger.info(f"ℹ️ No specific intelligence for port {context.port}")
                return {}
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to load port database: {e}")
            return {}
    
    def _get_scorer_recommendations(self, context: ScoringContext) -> List[str]:
        """Get recommendations from the scorer system."""
        try:
            from database.scorer.scorer_engine import score_wordlists_with_catalog
            result = score_wordlists_with_catalog(context)
            
            if result and result.wordlists:
                logger.info(f"📈 Scorer analysis:")
                logger.info(f"  🎯 Score: {result.score:.2f} | Confidence: {result.confidence}")
                logger.info(f"  📐 Rules matched: {result.matched_rules}")
                logger.info(f"  🔄 Fallback used: {result.fallback_used}")
                return result.wordlists
            else:
                logger.info("ℹ️ Scorer returned no recommendations")
                return []
                
        except Exception as e:
            logger.warning(f"⚠️ Scorer system failed: {e}")
            return []
    
    def _write_scan_reports(self, results: List[Dict[str, Any]], workspace_path: Path) -> None:
        """Write feroxbuster scan results to scan_reports.txt."""
        try:
            scan_reports_path = workspace_path / "scan_reports.txt"
            
            with open(scan_reports_path, 'w', encoding='utf-8') as f:
                f.write("# Feroxbuster Scan Results\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("# Format: [STATUS] URL (SIZE bytes) - WORDLIST\n\n")
                
                total_findings = 0
                for result_entry in results:
                    target = result_entry.get('target', 'unknown')
                    wordlist = result_entry.get('wordlist', 'unknown')
                    findings = result_entry.get('findings', [])
                    
                    if findings:
                        f.write(f"## Target: {target}\n")
                        f.write(f"## Wordlist: {wordlist}\n")
                        f.write(f"## Findings: {len(findings)}\n\n")
                        
                        for finding in findings:
                            status = finding.get('status', 'unknown')
                            url = finding.get('url', 'unknown')
                            size = finding.get('content_length', 0)
                            
                            # Format: [200] http://example.com/admin (1234 bytes) - directory-list-small
                            f.write(f"[{status}] {url} ({size} bytes) - {wordlist}\n")
                            total_findings += 1
                        
                        f.write("\n")
                
                f.write(f"\n# Total findings: {total_findings}\n")
                f.write(f"# Targets scanned: {len(results)}\n")
            
            logger.info(f"📝 Scan results written to {scan_reports_path}")
            return scan_reports_path
            
        except Exception as e:
            logger.error(f"Failed to write scan reports: {e}")
            return None
    
    async def execute(self, target: str, previous_results: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Execute feroxbuster scanning with intelligent wordlist selection."""
        if not self.validate_input(target=target):
            return self._create_result(False, error="Invalid target")
        
        if not previous_results:
            return self._create_result(False, error="No previous results available for service detection")
        
        # Get HTTP services from previous scans
        http_services = self._get_http_services(previous_results)
        
        if not http_services:
            return self._create_result(True, data={'message': 'No HTTP services found'})
        
        results = []
        
        for service in http_services:
            # Build target URL using discovered hostname (not IP)
            hostname = service.get('host')  # This comes from actual_target
            port = service.get('port', 80)
            protocol = 'https' if service.get('ssl') else 'http'
            
            # Only include port for non-standard ports
            if (protocol == 'https' and port == 443) or (protocol == 'http' and port == 80):
                target_url = f"{protocol}://{hostname}"
            else:
                target_url = f"{protocol}://{hostname}:{port}"
            
            logger.info(f"Targeting discovered hostname: {target_url}")
            
            # Build scoring context
            context = self._build_scoring_context(service, previous_results)
            
            # Get wordlist recommendation using full intelligence system
            intelligent_wordlists = self._get_intelligent_wordlists(context)
            
            if not intelligent_wordlists:
                logger.warning("No intelligent wordlists found, skipping service...")
                continue
            
            # Use the first wordlist from intelligent system
            selected_wordlist = intelligent_wordlists[0]
            logger.info(f"🎯 Selected intelligent wordlist: {selected_wordlist}")
            
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
            
            # Save selection to cache (skip for catalog-based selection)
            cache_entry_id = None
            logger.debug("Skipping cache save for catalog-based selection")
            
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
            
            # Run feroxbuster
            scan_result = self._run_feroxbuster(target_url, wordlist_path, extensions)
            
            # Process results
            findings = []
            if 'results' in scan_result:
                for item in scan_result['results']:
                    findings.append({
                        'url': item.get('url'),
                        'status': item.get('status'),
                        'content_length': item.get('content_length'),
                        'word_count': item.get('word_count'),
                        'line_count': item.get('line_count')
                    })
            
            result_entry = {
                'target': target_url,
                'wordlist': selected_wordlist,
                'confidence': 1.0, # Catalog search has no confidence score
                'score': 0.0, # Catalog search has no score
                'matched_rules': [], # Catalog search has no matched rules
                'findings': findings,
                'error': scan_result.get('error')
            }
            
            results.append(result_entry)
            
            # Update cache with scan outcome (if we have a cache entry)
            if cache_entry_id:
                try:
                    self.cache.update_outcome(cache_entry_id, {
                        'success': len(findings) > 0,
                        'findings_count': len(findings),
                        'error': scan_result.get('error'),
                        'wordlist_used': selected_wordlist
                    })
                except Exception as e:
                    logger.warning(f"Failed to update cache outcome: {e}")
        
        # Write scan reports to scan_reports.txt
        workspace_path = kwargs.get('workspace_path')
        if workspace_path:
            self._write_scan_reports(results, Path(workspace_path))
        else:
            # Try to get workspace from result manager
            try:
                from utils.results import result_manager
                workspace = result_manager.create_workspace(target)
                self._write_scan_reports(results, workspace)
            except Exception as e:
                logger.warning(f"Could not write scan reports: {e}")
        
        # Log final summary
        total_findings = sum(len(r.get('findings', [])) for r in results)
        services_with_findings = len([r for r in results if r.get('findings')])
        
        logger.info(f"🎉 Feroxbuster scan summary:")
        logger.info(f"  📊 Services scanned: {len(results)}")
        logger.info(f"  ✅ Services with findings: {services_with_findings}")
        logger.info(f"  🎯 Total paths found: {total_findings}")
        
        if total_findings > 0:
            logger.info(f"  💾 Results saved to scan_reports.txt")
            # Log a few example findings for verification
            for result_entry in results[:2]:  # Show first 2 services
                if result_entry.get('findings'):
                    target = result_entry.get('target', 'unknown')
                    findings_count = len(result_entry.get('findings', []))
                    logger.info(f"    📂 {target}: {findings_count} paths")
                    for finding in result_entry.get('findings', [])[:3]:  # Show first 3 paths
                        url = finding.get('url', '')
                        size = finding.get('content_length', 0)
                        status = finding.get('status', 0)
                        logger.info(f"      🔗 [{status}] {url} ({size} bytes)")
        
        return self._create_result(True, data={
            'services_scanned': len(results),
            'total_findings': total_findings,
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