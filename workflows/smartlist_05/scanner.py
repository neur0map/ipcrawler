"""SmartList Wordlist Recommendation Scanner"""
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
from datetime import datetime

from workflows.core.base import BaseWorkflow, WorkflowResult
from .models import SmartListResult, ServiceRecommendation, WordlistRecommendation
from src.core.utils.debugging import debug_print

try:
    from src.core.scorer import (
        score_wordlists_with_catalog,
        score_wordlists,
        get_wordlist_paths,
        get_port_context,
        explain_scoring,
        get_scoring_stats,
        get_database_availability,
        ScoringContext
    )
    SMARTLIST_AVAILABLE = True
except ImportError as e:
    SMARTLIST_AVAILABLE = False
    debug_print(f"SmartList components not available: {e}", level="ERROR")


class SmartListScanner(BaseWorkflow):
    """Intelligent wordlist recommendation based on scan results"""
    
    def __init__(self):
        super().__init__(name="smartlist_05")
        # Get HTTP ports from database with fallback
        try:
            from workflows.core.db_integration import get_common_http_ports
            self.web_ports = get_common_http_ports()
        except ImportError:
            # Fallback if database helper not available
            self.web_ports = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000, 4200, 3001]
        
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters"""
        if not kwargs.get('target'):
            debug_print("Missing required parameter: target", level="ERROR")
            return False
        
        if not SMARTLIST_AVAILABLE:
            debug_print("SmartList components not available", level="ERROR")
            return False
            
        return True
    
    async def execute(self, **kwargs) -> WorkflowResult:
        """Execute SmartList analysis"""
        start_time = time.time()
        target = kwargs.get('target')
        previous_results = kwargs.get('previous_results', {})
        
        debug_print(f"Starting SmartList analysis for {target}")
        
        try:
            # Create result object
            result = SmartListResult(target=target)
            
            # Check database availability
            if SMARTLIST_AVAILABLE:
                stats = get_scoring_stats()  # Now works without parameters
                result.port_database_available = stats.get('port_database_available', False)
                result.catalog_available = stats.get('catalog_available', False)
                
                # Debug database status
                if result.port_database_available:
                    debug_print("✓ Port database loaded and available", level="INFO")
                else:
                    error_msg = stats.get('port_db_error', 'Unknown error')
                    debug_print(f"✗ Port database not available: {error_msg}", level="WARNING")
                
                if result.catalog_available:
                    debug_print("✓ Wordlist catalog loaded and available", level="INFO")
                else:
                    error_msg = stats.get('catalog_error', 'Unknown error')
                    debug_print(f"✗ Wordlist catalog not available: {error_msg}", level="WARNING")
                
                # Log database paths for debugging
                if 'database_path' in stats:
                    debug_print(f"Database path: {stats['database_path']}", level="DEBUG")
            else:
                result.port_database_available = False
                result.catalog_available = False
                debug_print("SmartList components not available - database checks skipped", level="WARNING")
            
            # Aggregate scan results from previous workflows
            aggregated_data = self._aggregate_scan_results(previous_results)
            
            # Mini Spider data now comes from previous_results
            # No need to load from workspace files anymore
            
            if not aggregated_data['services']:
                debug_print("No services found in previous scan results", level="WARNING")
                result.summary = {
                    'message': 'No services discovered in previous scans',
                    'recommendation': 'Run nmap and http scans first'
                }
            else:
                # Build contexts and get recommendations for each service
                for service_data in aggregated_data['services']:
                    context = self._build_service_context(service_data, aggregated_data)
                    service_rec = await self._get_service_recommendations(context, service_data)
                    result.services.append(service_rec)
                
                # Generate summary
                result.summary = self._generate_summary(result)
            
            result.execution_time = time.time() - start_time
            
            # Save results to scan reports
            self._save_to_scan_reports(target, result)
            
            return WorkflowResult(
                success=True,
                data=result.to_dict(),
                execution_time=result.execution_time
            )
            
        except Exception as e:
            debug_print(f"SmartList analysis failed: {str(e)}", level="ERROR")
            return WorkflowResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def _aggregate_scan_results(self, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced cross-workflow data aggregation with correlation analysis"""
        aggregated = {
            'services': [],
            'technologies': {},
            'os_info': None,
            'dns_records': [],
            'vulnerabilities': [],
            'correlation_metadata': {
                'workflow_sources': [],
                'data_quality_scores': {},
                'cross_validation': {},
                'technology_consensus': {},
                'version_correlation': {},
                'confidence_matrix': {}
            }
        }
        
        # Extract from nmap_fast_01
        if 'nmap_fast_01' in previous_results:
            fast_data = previous_results['nmap_fast_01']
            if fast_data.get('success') and fast_data.get('data'):
                for host in fast_data['data'].get('hosts', []):
                    for port_info in host.get('ports', []):
                        aggregated['services'].append({
                            'host': host.get('ip'),
                            'port': port_info.get('port'),
                            'protocol': port_info.get('protocol', 'tcp'),
                            'state': port_info.get('state'),
                            'service': port_info.get('service', ''),
                            'source': 'nmap_fast'
                        })
        
        # Extract from nmap_02 (detailed scan)
        if 'nmap_02' in previous_results:
            detailed_data = previous_results['nmap_02']
            if detailed_data.get('success') and detailed_data.get('data'):
                for host in detailed_data['data'].get('hosts', []):
                    # OS information
                    if host.get('os'):
                        aggregated['os_info'] = {
                            'os': host.get('os'),
                            'accuracy': host.get('os_accuracy')
                        }
                    
                    # Enhanced service information
                    for port_info in host.get('ports', []):
                        # Find and update existing service or add new
                        port_num = port_info.get('port')
                        existing = None
                        for svc in aggregated['services']:
                            if svc['port'] == port_num and svc['host'] == host.get('ip'):
                                existing = svc
                                break
                        
                        if existing:
                            # Update with detailed info
                            existing.update({
                                'service': port_info.get('service', existing.get('service', '')),
                                'version': port_info.get('version'),
                                'product': port_info.get('product'),
                                'extra_info': port_info.get('extra_info'),
                                'scripts': port_info.get('scripts', []),
                                'cpe': port_info.get('cpe', [])
                            })
                        else:
                            # Add new service
                            aggregated['services'].append({
                                'host': host.get('ip'),
                                'port': port_num,
                                'protocol': port_info.get('protocol', 'tcp'),
                                'state': port_info.get('state'),
                                'service': port_info.get('service', ''),
                                'version': port_info.get('version'),
                                'product': port_info.get('product'),
                                'extra_info': port_info.get('extra_info'),
                                'scripts': port_info.get('scripts', []),
                                'cpe': port_info.get('cpe', []),
                                'source': 'nmap_detailed'
                            })
        
        # Extract from http_03
        if 'http_03' in previous_results:
            http_data = previous_results['http_03']
            if http_data.get('success') and http_data.get('data'):
                # DNS records
                aggregated['dns_records'] = http_data['data'].get('dns_records', [])
                
                # HTTP services with technology detection
                for service in http_data['data'].get('services', []):
                    port_num = service.get('port')
                    
                    # Find existing service to enhance
                    existing = None
                    for svc in aggregated['services']:
                        if svc['port'] == port_num and svc['host'] == http_data['data'].get('target'):
                            existing = svc
                            break
                    
                    if existing:
                        # Add HTTP-specific information
                        existing.update({
                            'scheme': service.get('scheme'),
                            'url': service.get('url'),
                            'status_code': service.get('status_code'),
                            'headers': service.get('headers', {}),
                            'server': service.get('server'),
                            'is_https': service.get('is_https', False),
                            'technologies': service.get('technologies', []),
                            'discovered_paths': service.get('discovered_paths', [])
                        })
                        
                        # Extract technology from headers
                        headers = service.get('headers', {})
                        if 'X-Powered-By' in headers:
                            tech = headers['X-Powered-By'].split('/')[0].lower()
                            if tech not in existing.get('technologies', []):
                                existing.setdefault('technologies', []).append(tech)
                    else:
                        # Add as new HTTP service
                        aggregated['services'].append({
                            'host': http_data['data'].get('target'),
                            'port': port_num,
                            'protocol': 'tcp',
                            'state': 'open',
                            'service': 'http' if not service.get('is_https') else 'https',
                            'scheme': service.get('scheme'),
                            'url': service.get('url'),
                            'status_code': service.get('status_code'),
                            'headers': service.get('headers', {}),
                            'server': service.get('server'),
                            'is_https': service.get('is_https', False),
                            'technologies': service.get('technologies', []),
                            'discovered_paths': service.get('discovered_paths', []),
                            'source': 'http_scan'
                        })
                
                # Vulnerabilities
                aggregated['vulnerabilities'] = http_data['data'].get('vulnerabilities', [])
        
        # Extract from mini_spider_04
        if 'mini_spider_04' in previous_results:
            spider_data = previous_results['mini_spider_04']
            if spider_data.get('success') and spider_data.get('data'):
                spider_result = spider_data['data']
                
                # Add spider data to aggregated structure
                aggregated['spider_data'] = {
                    'discovered_urls': spider_result.get('discovered_urls', []),
                    'categorized_results': spider_result.get('categorized_results', {}),
                    'interesting_findings': spider_result.get('interesting_findings', []),
                    'statistics': spider_result.get('statistics', {}),
                    'tools_used': spider_result.get('statistics', {}).get('tools_used', [])
                }
                
                # Enhance existing services with spider intelligence
                for service in aggregated['services']:
                    if service.get('port') in self.web_ports:
                        # Find relevant spider URLs for this service
                        service_urls = []
                        base_url = f"{service.get('scheme', 'http')}://{service['host']}"
                        if service.get('port') not in [80, 443]:
                            base_url += f":{service['port']}"
                        
                        # Collect URLs from spider data that match this service
                        for url_data in spider_result.get('discovered_urls', []):
                            if isinstance(url_data, dict) and url_data.get('url', '').startswith(base_url):
                                service_urls.append(url_data)
                        
                        # Add spider intelligence to service
                        if service_urls:
                            service['spider_urls'] = service_urls
                            service['spider_url_count'] = len(service_urls)
                            
                            # Extract additional paths discovered by spider
                            spider_paths = []
                            for url_data in service_urls:
                                url = url_data.get('url', '')
                                if url.startswith(base_url):
                                    path = url[len(base_url):] or '/'
                                    if path not in spider_paths:
                                        spider_paths.append(path)
                            
                            # Merge with existing discovered paths
                            existing_paths = service.get('discovered_paths', [])
                            all_paths = list(set(existing_paths + spider_paths))
                            service['discovered_paths'] = all_paths
                            service['spider_discovered_paths'] = spider_paths
                            
                            # Extract categories from spider URLs
                            categories = set()
                            for url_data in service_urls:
                                if url_data.get('category'):
                                    category = url_data['category']
                                    # Handle enum or string values
                                    if hasattr(category, 'value'):
                                        categories.add(category.value)
                                    else:
                                        categories.add(str(category))
                            service['spider_categories'] = list(categories)
                            
                            # Add spider-detected technologies
                            spider_techs = []
                            for finding in spider_result.get('interesting_findings', []):
                                if finding.get('url', '').startswith(base_url):
                                    # Extract technology hints from findings
                                    finding_type = finding.get('finding_type', '')
                                    if 'technology' in finding_type.lower() or 'framework' in finding_type.lower():
                                        metadata = finding.get('metadata', {})
                                        if 'technology' in metadata:
                                            spider_techs.append(metadata['technology'])
                            
                            if spider_techs:
                                # Merge with existing technologies
                                existing_techs = service.get('technologies', [])
                                all_techs = list(set(existing_techs + spider_techs))
                                service['technologies'] = all_techs
                                service['spider_technologies'] = spider_techs
        
        # Perform cross-workflow correlation analysis
        aggregated = self._analyze_cross_workflow_correlations(aggregated, previous_results)
        
        debug_print(f"Aggregated {len(aggregated['services'])} services from previous scans with enhanced correlation")
        return aggregated
    
    def _build_service_context(self, service_data: Dict[str, Any], 
                              aggregated_data: Dict[str, Any]) -> ScoringContext:
        """Build ScoringContext from service data with spider intelligence"""
        # Extract technology using enhanced cross-workflow correlation
        tech = None
        tech_confidence = 0.0
        tech_sources = []
        
        # First, check if we have consensus technology from correlation analysis
        service_key = f"{service_data['host']}:{service_data['port']}"
        correlation_meta = aggregated_data.get('correlation_metadata', {})
        tech_consensus = correlation_meta.get('technology_consensus', {})
        
        if service_key in tech_consensus:
            consensus_info = tech_consensus[service_key]
            tech = consensus_info['technology']
            tech_confidence = consensus_info['confidence']
            tech_sources.append(f"consensus_({consensus_info['consensus_score']}_votes)")
            debug_print(f"Using consensus technology for {service_key}: {tech} (confidence: {tech_confidence:.2f})")
            
        # If no consensus, fall back to individual workflow detection
        if not tech:
            # 1. Check technologies array (from http scan) - High confidence
            if service_data.get('technologies') and len(service_data['technologies']) > 0 and service_data['technologies'][0]:
                tech = service_data['technologies'][0].lower()
                tech_confidence = 0.8
                tech_sources.append('http_scan')
            
            # 2. Check spider-detected technologies - High confidence if found
            elif service_data.get('spider_technologies'):
                tech = service_data['spider_technologies'][0].lower()
                tech_confidence = 0.9  # Spider is very thorough
                tech_sources.append('spider_scan')
            
            # 3. Check product/version from nmap using database patterns - Medium confidence
            elif service_data.get('product'):
                product = service_data['product'].lower()
                detected_tech = self._detect_technology_from_database(
                    product_string=product,
                    port=service_data.get('port')
                )
                
                if detected_tech:
                    tech = detected_tech['technology']
                    tech_confidence = detected_tech['confidence']
                    tech_sources.append(f"nmap_product_db:{detected_tech['source']}")
                    debug_print(f"Database-detected tech from product '{product}': {tech} (confidence: {tech_confidence:.2f})")
            
            # 4. Database-driven HTTP header analysis - Medium to High confidence
            elif service_data.get('headers'):
                headers = service_data['headers']
                detected_tech = self._detect_technology_from_headers(
                    headers=headers,
                    port=service_data.get('port')
                )
                
                if detected_tech:
                    tech = detected_tech['technology']
                    tech_confidence = detected_tech['confidence']
                    tech_sources.append(f"http_header_db:{detected_tech['source']}")
                    debug_print(f"Database-detected tech from headers: {tech} (confidence: {tech_confidence:.2f}, source: {detected_tech['source']})")
            
            # 5. Database-driven spider category analysis - Lower confidence but useful  
            elif service_data.get('spider_categories'):
                detected_tech = self._detect_technology_from_spider_categories(
                    categories=service_data['spider_categories'],
                    port=service_data.get('port')
                )
                
                if detected_tech:
                    tech = detected_tech['technology']
                    tech_confidence = detected_tech['confidence']
                    tech_sources.append(f"spider_categories_db:{detected_tech['source']}")
                    debug_print(f"Database-detected tech from spider categories: {tech} (confidence: {tech_confidence:.2f})")
        
        # Build enhanced service description with spider intelligence
        service_desc_parts = []
        if service_data.get('product'):
            service_desc_parts.append(service_data['product'])
        if service_data.get('version'):
            service_desc_parts.append(service_data['version'])
        if service_data.get('extra_info'):
            service_desc_parts.append(service_data['extra_info'])
        if not service_desc_parts and service_data.get('service'):
            service_desc_parts.append(service_data['service'])
        
        # Add spider context to service description
        if service_data.get('spider_url_count', 0) > 0:
            service_desc_parts.append(f"({service_data['spider_url_count']} URLs discovered)")
        
        if service_data.get('spider_categories'):
            categories_str = ', '.join(service_data['spider_categories'])
            service_desc_parts.append(f"Categories: {categories_str}")
        
        service_desc = ' '.join(service_desc_parts) or f"Service on port {service_data['port']}"
        
        # Build spider intelligence data
        spider_intelligence = {
            'url_count': service_data.get('spider_url_count', 0),
            'categories': service_data.get('spider_categories', []),
            'discovered_paths': service_data.get('spider_discovered_paths', []),
            'tech_confidence': tech_confidence,
            'tech_sources': tech_sources,
            'has_spider_intel': service_data.get('spider_url_count', 0) > 0
        }
        
        # Get enhanced version information from correlation analysis
        version = service_data.get('version')
        correlation_meta = aggregated_data.get('correlation_metadata', {})
        version_correlations = correlation_meta.get('version_correlation', {})
        
        # Use consensus version if available (higher accuracy)
        if service_key in version_correlations:
            consensus_version = version_correlations[service_key].get('consensus_version')
            if consensus_version:
                version = consensus_version
                debug_print(f"Using consensus version for {service_key}: {version}")
        
        # Create enhanced context with spider data and consensus information
        context = ScoringContext(
            target=service_data['host'],
            port=service_data['port'],
            service=service_desc,
            tech=tech,
            os=aggregated_data.get('os_info', {}).get('os') if aggregated_data.get('os_info') else None,
            version=version,
            headers=service_data.get('headers', {}),
            spider_data=spider_intelligence if spider_intelligence['has_spider_intel'] else None
        )
        
        debug_print(f"Built enhanced context for {context.target}:{context.port} - tech: {tech} (confidence: {tech_confidence:.2f}, sources: {tech_sources})")
        return context
    
    async def _get_service_recommendations(self, context: ScoringContext, 
                                         service_data: Dict[str, Any]) -> ServiceRecommendation:
        """Get SmartList recommendations for a service with spider intelligence"""
        # Get port context for additional information
        port_info = get_port_context(context.port) if SMARTLIST_AVAILABLE else {}
        
        # Score wordlists using the three-tier architecture
        try:
            # Try catalog-enhanced scoring first
            result = score_wordlists_with_catalog(context)
            debug_print(f"Got catalog-enhanced recommendations for port {context.port}")
        except Exception as e:
            # Fall back to basic scoring
            debug_print(f"Catalog scoring failed, using basic: {e}")
            result = score_wordlists(context)
        
        # Apply spider intelligence scoring boosts
        if context.spider_data and context.spider_data.get('has_spider_intel'):
            result = self._apply_spider_scoring_boosts(result, context, service_data)
        
        # Get wordlist paths if available
        wordlist_paths = []
        try:
            wordlist_paths = get_wordlist_paths(
                result.wordlists,
                tech=context.tech,
                port=context.port
            )
            debug_print(f"Resolved {len(wordlist_paths)} wordlist paths for port {context.port}")
        except Exception as e:
            debug_print(f"Could not resolve wordlist paths: {e}", level="WARNING")
            wordlist_paths = [None] * len(result.wordlists)
        
        # Build enhanced recommendations with spider context
        recommendations = []
        for i, wordlist in enumerate(result.wordlists[:10]):  # Top 10
            # Determine which rule category this came from
            category = self._determine_category(result.matched_rules)
            
            # Use full path if available, otherwise just the wordlist name
            wordlist_path = wordlist_paths[i] if i < len(wordlist_paths) and wordlist_paths[i] else None
            if wordlist_path:
                debug_print(f"Wordlist '{wordlist}' resolved to path: {wordlist_path}")
            else:
                debug_print(f"No path resolved for wordlist '{wordlist}'", level="WARNING")
            
            # Generate enhanced reason with spider context
            reason = self._generate_enhanced_reason(result, wordlist, context)
            
            rec = WordlistRecommendation(
                wordlist=wordlist,
                path=wordlist_path,
                score=result.score,
                confidence=result.confidence.upper() if isinstance(result.confidence, str) else result.confidence.value.upper(),
                reason=reason,
                category=category,
                matched_rule=result.matched_rules[0] if result.matched_rules else "none"
            )
            recommendations.append(rec)
        
        # Build enhanced context summary with spider data
        context_summary = {
            'service_description': context.service,
            'detected_technology': context.tech,
            'port_database_tech': port_info.get('technologies', []) if port_info else [],
            'service_category': port_info.get('category') if port_info else None,
            'risk_level': port_info.get('risk_level') if port_info else None,
            'is_web_service': port_info.get('is_web_service', False) if port_info else context.port in self.web_ports,
            'matched_rules': result.matched_rules,
            'fallback_used': result.fallback_used
        }
        
        # Add spider intelligence to context summary
        if context.spider_data and context.spider_data.get('has_spider_intel'):
            spider_data = context.spider_data
            context_summary.update({
                'spider_intelligence': {
                    'urls_discovered': spider_data.get('url_count', 0),
                    'categories_found': spider_data.get('categories', []),
                    'paths_discovered': len(spider_data.get('discovered_paths', [])),
                    'tech_confidence': spider_data.get('tech_confidence', 0),
                    'tech_sources': spider_data.get('tech_sources', []),
                    'enhanced_scoring': True
                }
            })
        
        # Create service recommendation
        service_rec = ServiceRecommendation(
            target=context.target,
            port=context.port,
            service_name=service_data.get('service', 'unknown'),
            detected_tech=context.tech,
            recommendations=recommendations,
            context_summary=context_summary,
            total_score=result.score,
            confidence_level=result.confidence.upper() if isinstance(result.confidence, str) else result.confidence.value.upper(),
            score_breakdown={
                'exact_match': result.explanation.get('exact_match', 0.0) if isinstance(result.explanation, dict) else result.explanation.exact_match,
                'tech_category': result.explanation.get('tech_category', 0.0) if isinstance(result.explanation, dict) else result.explanation.tech_category,
                'port_context': result.explanation.get('port_context', 0.0) if isinstance(result.explanation, dict) else result.explanation.port_context,
                'service_keywords': result.explanation.get('service_keywords', 0.0) if isinstance(result.explanation, dict) else result.explanation.service_keywords,
                'generic_fallback': result.explanation.get('generic_fallback', 0.0) if isinstance(result.explanation, dict) else result.explanation.generic_fallback
            }
        )
        
        return service_rec
    
    def _apply_spider_scoring_boosts(self, result, context: ScoringContext, service_data: Dict[str, Any]):
        """Enhanced spider intelligence with database-driven content categorization"""
        spider_data = context.spider_data
        boost_factor = 1.0
        additional_rules = []
        
        # Enhanced content analysis using database patterns
        content_analysis = self._analyze_spider_content_with_database(spider_data, context.tech, context.port)
        
        # Apply database-driven category boosts
        for category, analysis in content_analysis.items():
            if analysis['confidence'] > 0.6:  # Only high-confidence categorizations
                boost_factor *= analysis['boost_factor']
                additional_rules.append(f"spider_db_category:{category}:{analysis['confidence']:.2f}")
                debug_print(f"Applied database-driven category boost: {category} (confidence: {analysis['confidence']:.2f}, boost: {analysis['boost_factor']:.2f})")
        
        # Technology-specific pattern boosts
        if spider_data.get('tech_confidence', 0) > 0.8:
            tech_boost = self._calculate_tech_specific_boost(context.tech, spider_data)
            boost_factor *= tech_boost
            additional_rules.append(f"spider_tech_specific:{context.tech}:{tech_boost:.2f}")
        
        # Path pattern analysis
        path_analysis = self._analyze_discovered_paths(spider_data.get('discovered_paths', []), context.tech)
        if path_analysis['security_relevance'] > 0.7:
            boost_factor *= (1.0 + path_analysis['security_relevance'] * 0.3)
            additional_rules.append(f"spider_security_paths:{path_analysis['security_relevance']:.2f}")
        
        # File extension intelligence
        file_ext_boost = self._analyze_file_extensions(spider_data.get('discovered_paths', []), context.tech)
        if file_ext_boost > 1.0:
            boost_factor *= file_ext_boost
            additional_rules.append(f"spider_file_extensions:{file_ext_boost:.2f}")
        
        # Apply boosts to result
        if boost_factor > 1.0:
            result.score = min(result.score * boost_factor, 1.0)  # Cap at 1.0
            result.matched_rules.extend(additional_rules)
            debug_print(f"Applied enhanced spider boost factor {boost_factor:.2f} to recommendations")
        
        return result
    
    def _analyze_cross_workflow_correlations(self, aggregated: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and correlate data across workflows for improved accuracy"""
        try:
            correlation_meta = aggregated['correlation_metadata']
            
            # Track workflow sources
            correlation_meta['workflow_sources'] = list(previous_results.keys())
            
            # Analyze technology consensus across workflows
            tech_consensus = {}
            version_correlations = {}
            
            for service in aggregated['services']:
                service_key = f"{service['host']}:{service['port']}"
                
                # Collect technology detections from different sources
                tech_sources = {
                    'nmap': service.get('service', ''),
                    'http': service.get('technologies', []),
                    'spider': service.get('spider_technologies', []),
                    'product': service.get('product', ''),
                    'headers': service.get('headers', {})
                }
                
                # Build technology consensus
                tech_votes = {}
                confidence_scores = {}
                
                # Process nmap service detection
                if tech_sources['nmap']:
                    tech_name = tech_sources['nmap'].lower()
                    tech_votes[tech_name] = tech_votes.get(tech_name, 0) + 2  # High weight
                    confidence_scores[tech_name] = confidence_scores.get(tech_name, []) + [0.8]
                
                # Process HTTP-detected technologies
                if tech_sources['http']:
                    for tech in tech_sources['http']:
                        tech_name = tech.lower()
                        tech_votes[tech_name] = tech_votes.get(tech_name, 0) + 3  # Highest weight
                        confidence_scores[tech_name] = confidence_scores.get(tech_name, []) + [0.9]
                
                # Process spider-detected technologies
                if tech_sources['spider']:
                    for tech in tech_sources['spider']:
                        tech_name = tech.lower()
                        tech_votes[tech_name] = tech_votes.get(tech_name, 0) + 2  # High weight
                        confidence_scores[tech_name] = confidence_scores.get(tech_name, []) + [0.8]
                
                # Process product string
                if tech_sources['product']:
                    # Use database detection for product string
                    detected_tech = self._detect_technology_from_database(
                        tech_sources['product'].lower(),
                        service.get('port')
                    )
                    if detected_tech:
                        tech_name = detected_tech['technology']
                        tech_votes[tech_name] = tech_votes.get(tech_name, 0) + 1
                        confidence_scores[tech_name] = confidence_scores.get(tech_name, []) + [detected_tech['confidence']]
                
                # Process headers
                if tech_sources['headers']:
                    detected_tech = self._detect_technology_from_headers(
                        tech_sources['headers'],
                        service.get('port')
                    )
                    if detected_tech:
                        tech_name = detected_tech['technology']
                        tech_votes[tech_name] = tech_votes.get(tech_name, 0) + 1
                        confidence_scores[tech_name] = confidence_scores.get(tech_name, []) + [detected_tech['confidence']]
                
                # Calculate consensus technology
                if tech_votes:
                    # Find technology with highest consensus
                    consensus_tech = max(tech_votes.items(), key=lambda x: x[1])
                    tech_name, vote_count = consensus_tech
                    
                    # Calculate average confidence
                    avg_confidence = sum(confidence_scores.get(tech_name, [0.5])) / len(confidence_scores.get(tech_name, [1]))
                    
                    tech_consensus[service_key] = {
                        'technology': tech_name,
                        'consensus_score': vote_count,
                        'confidence': avg_confidence,
                        'sources': list(tech_sources.keys()),
                        'alternative_detections': {k: v for k, v in tech_votes.items() if k != tech_name and v > 0}
                    }
                    
                    # Update service with consensus technology
                    service['consensus_technology'] = tech_name
                    service['technology_confidence'] = avg_confidence
                    service['technology_sources'] = len([s for s in tech_sources.values() if s])
                
                # Analyze version correlations
                version_info = {
                    'nmap_version': service.get('version'),
                    'product_version': None,
                    'header_version': None
                }
                
                # Extract version from product string
                if service.get('product'):
                    import re
                    version_match = re.search(r'(\d+\.[\d\.]+)', service['product'])
                    if version_match:
                        version_info['product_version'] = version_match.group(1)
                
                # Extract version from headers
                headers = service.get('headers', {})
                for header_name, header_value in headers.items():
                    if 'version' in header_name.lower():
                        import re
                        version_match = re.search(r'(\d+\.[\d\.]+)', header_value)
                        if version_match:
                            version_info['header_version'] = version_match.group(1)
                            break
                
                # Store version correlation if multiple sources agree
                versions_found = [v for v in version_info.values() if v]
                if len(versions_found) > 1:
                    version_correlations[service_key] = {
                        'detected_versions': version_info,
                        'correlation_strength': len(versions_found),
                        'consensus_version': max(set(versions_found), key=versions_found.count) if versions_found else None
                    }
                    
                    # Update service with consensus version
                    if version_correlations[service_key]['consensus_version']:
                        service['consensus_version'] = version_correlations[service_key]['consensus_version']
            
            # Calculate overall data quality score
            total_services = len(aggregated['services'])
            services_with_consensus = len(tech_consensus)
            services_with_versions = len(version_correlations)
            
            quality_score = 0.0
            if total_services > 0:
                quality_score = (
                    (services_with_consensus / total_services) * 0.6 +  # Technology consensus weight
                    (services_with_versions / total_services) * 0.2 +   # Version correlation weight
                    (len(correlation_meta['workflow_sources']) / 4) * 0.2  # Workflow completeness weight
                )
            
            # Store correlation results
            correlation_meta['technology_consensus'] = tech_consensus
            correlation_meta['version_correlation'] = version_correlations
            correlation_meta['data_quality_scores'] = {
                'overall_quality': quality_score,
                'technology_consensus_rate': services_with_consensus / total_services if total_services > 0 else 0,
                'version_correlation_rate': services_with_versions / total_services if total_services > 0 else 0,
                'workflow_completeness': len(correlation_meta['workflow_sources']) / 4
            }
            
            debug_print(f"Cross-workflow correlation analysis complete:")
            debug_print(f"  - Technology consensus: {services_with_consensus}/{total_services} services")
            debug_print(f"  - Version correlations: {services_with_versions}/{total_services} services") 
            debug_print(f"  - Overall data quality: {quality_score:.2f}")
            
            return aggregated
            
        except Exception as e:
            debug_print(f"Error in cross-workflow correlation analysis: {e}", level="ERROR")
            return aggregated
    
    def _detect_technology_from_database(self, product_string: str, port: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Detect technology from product string using database patterns"""
        try:
            # Get database availability
            db_stats = get_database_availability()
            if not db_stats.get('port_database_available'):
                debug_print("Port database not available for technology detection", level="WARNING")
                return None
            
            # Load port database
            port_db_path = Path(db_stats['port_database_path'])
            with open(port_db_path, 'r') as f:
                port_db = json.load(f)
            
            best_match = None
            best_confidence = 0.0
            
            # Check each port's alternative services and banners
            for port_num, port_info in port_db.items():
                # Check alternative services (exact and partial matches)
                if 'alternative_services' in port_info:
                    for service in port_info['alternative_services']:
                        service_lower = service.lower()
                        
                        # Exact match - high confidence
                        if service_lower == product_string:
                            return {
                                'technology': service_lower,
                                'confidence': 0.9,
                                'source': f'alternative_service_exact_{port_num}'
                            }
                        
                        # Partial match - medium confidence
                        elif service_lower in product_string or product_string in service_lower:
                            if 0.7 > best_confidence:
                                best_match = {
                                    'technology': service_lower,
                                    'confidence': 0.7,
                                    'source': f'alternative_service_partial_{port_num}'
                                }
                                best_confidence = 0.7
                
                # Check default service
                if 'default_service' in port_info:
                    default_service = port_info['default_service'].lower()
                    if default_service in product_string or product_string in default_service:
                        if 0.6 > best_confidence:
                            best_match = {
                                'technology': default_service,
                                'confidence': 0.6,
                                'source': f'default_service_{port_num}'
                            }
                            best_confidence = 0.6
                
                # Check banners for pattern matching
                if 'indicators' in port_info and 'banners' in port_info['indicators']:
                    for banner in port_info['indicators']['banners']:
                        banner_lower = banner.lower()
                        if banner_lower in product_string:
                            if 0.5 > best_confidence:
                                best_match = {
                                    'technology': banner_lower,
                                    'confidence': 0.5,
                                    'source': f'banner_match_{port_num}'
                                }
                                best_confidence = 0.5
            
            return best_match
            
        except Exception as e:
            debug_print(f"Error in database technology detection: {e}", level="ERROR")
            return None
    
    def _detect_technology_from_headers(self, headers: Dict[str, str], port: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Detect technology from HTTP headers using database patterns"""
        try:
            # Get database availability
            db_stats = get_database_availability()
            if not db_stats.get('port_database_available'):
                return None
            
            # Load port database
            port_db_path = Path(db_stats['port_database_path'])
            with open(port_db_path, 'r') as f:
                port_db = json.load(f)
            
            # Header importance and confidence mapping
            header_importance = {
                'x-powered-by': 0.8,
                'server': 0.7,
                'x-generator': 0.9,
                'x-drupal-cache': 0.95,
                'x-pingback': 0.9,
                'x-aspnet-version': 0.95,
                'x-aspnetmvc-version': 0.95,
                'x-frame-options': 0.3
            }
            
            best_match = None
            best_confidence = 0.0
            
            # Check each header against database patterns
            for header_name, header_value in headers.items():
                header_lower = header_name.lower()
                value_lower = header_value.lower()
                
                base_confidence = header_importance.get(header_lower, 0.4)
                
                # Check against all services in database
                for port_num, port_info in port_db.items():
                    # Check alternative services
                    if 'alternative_services' in port_info:
                        for service in port_info['alternative_services']:
                            service_lower = service.lower()
                            
                            if service_lower in value_lower:
                                confidence = base_confidence * 0.9  # Slight reduction for partial match
                                if confidence > best_confidence:
                                    best_match = {
                                        'technology': service_lower,
                                        'confidence': confidence,
                                        'source': f'{header_lower}_service_match'
                                    }
                                    best_confidence = confidence
                    
                    # Check tech stack information
                    if 'tech_stack' in port_info:
                        tech_stack = port_info['tech_stack']
                        for stack_key, stack_value in tech_stack.items():
                            if stack_value and isinstance(stack_value, str):
                                if stack_value.lower() in value_lower:
                                    confidence = base_confidence * 0.8
                                    if confidence > best_confidence:
                                        best_match = {
                                            'technology': stack_value.lower(),
                                            'confidence': confidence,
                                            'source': f'{header_lower}_tech_stack_{stack_key}'
                                        }
                                        best_confidence = confidence
            
            return best_match
            
        except Exception as e:
            debug_print(f"Error in header-based technology detection: {e}", level="ERROR")
            return None
    
    def _detect_technology_from_spider_categories(self, categories: List[str], port: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Detect technology from spider categories using database patterns"""
        try:
            # Get database availability  
            db_stats = get_database_availability()
            if not db_stats.get('port_database_available'):
                return None
            
            # Load port database
            port_db_path = Path(db_stats['port_database_path'])
            with open(port_db_path, 'r') as f:
                port_db = json.load(f)
            
            # Category to technology inference patterns
            category_patterns = {}
            
            # Build patterns from database
            for port_num, port_info in port_db.items():
                if 'classification' in port_info and 'category' in port_info['classification']:
                    db_category = port_info['classification']['category']
                    default_service = port_info.get('default_service', 'unknown')
                    
                    if db_category not in category_patterns:
                        category_patterns[db_category] = []
                    category_patterns[db_category].append(default_service)
            
            best_match = None
            best_confidence = 0.0
            
            # Match spider categories against database categories
            for spider_category in categories:
                spider_lower = spider_category.lower()
                
                # Direct category match
                if spider_lower in category_patterns:
                    # Use most common service for this category
                    services = category_patterns[spider_lower]
                    most_common = max(set(services), key=services.count) if services else 'unknown'
                    
                    if most_common != 'unknown':
                        confidence = 0.4  # Low confidence for category inference
                        if confidence > best_confidence:
                            best_match = {
                                'technology': most_common,
                                'confidence': confidence,
                                'source': f'category_inference_{spider_lower}'
                            }
                            best_confidence = confidence
                
                # Partial category matching
                for db_category, services in category_patterns.items():
                    if spider_lower in db_category or db_category in spider_lower:
                        most_common = max(set(services), key=services.count) if services else 'unknown'
                        
                        if most_common != 'unknown':
                            confidence = 0.3  # Lower confidence for partial match
                            if confidence > best_confidence:
                                best_match = {
                                    'technology': most_common,
                                    'confidence': confidence,
                                    'source': f'category_partial_{db_category}'
                                }
                                best_confidence = confidence
            
            return best_match
            
        except Exception as e:
            debug_print(f"Error in spider category technology detection: {e}", level="ERROR")
            return None
    
    def _analyze_spider_content_with_database(self, spider_data: Dict[str, Any], tech: Optional[str], port: Optional[int]) -> Dict[str, Dict[str, float]]:
        """Analyze spider content using database-driven categorization patterns"""
        try:
            # Get database availability
            db_stats = get_database_availability()
            if not db_stats.get('port_database_available'):
                return self._fallback_content_analysis(spider_data)
            
            # Load port database
            port_db_path = Path(db_stats['port_database_path'])
            with open(port_db_path, 'r') as f:
                port_db = json.load(f)
            
            content_analysis = {}
            discovered_paths = spider_data.get('discovered_paths', [])
            
            # Build category patterns from database
            db_patterns = {}
            for port_num, port_info in port_db.items():
                if 'classification' in port_info:
                    category = port_info['classification'].get('category', 'unknown')
                    
                    # Extract path patterns if available
                    if 'indicators' in port_info and 'paths' in port_info['indicators']:
                        if category not in db_patterns:
                            db_patterns[category] = {
                                'paths': [],
                                'keywords': [],
                                'boost_factor': 1.0
                            }
                        db_patterns[category]['paths'].extend(port_info['indicators']['paths'])
                    
                    # Set boost factors based on category importance
                    category_boost_map = {
                        'web': 1.2,
                        'database': 1.4,
                        'admin-panel': 1.5,
                        'cms': 1.3,
                        'development': 1.25,
                        'api': 1.3,
                        'authentication': 1.4,
                        'file-transfer': 1.1,
                        'remote-access': 1.2
                    }
                    
                    if category in db_patterns:
                        db_patterns[category]['boost_factor'] = category_boost_map.get(category, 1.1)
            
            # Analyze discovered paths against database patterns
            for category, patterns in db_patterns.items():
                matches = 0
                total_patterns = len(patterns['paths'])
                
                if total_patterns > 0:
                    for path in discovered_paths:
                        path_str = path if isinstance(path, str) else str(path)
                        for pattern in patterns['paths']:
                            if pattern.lower() in path_str.lower():
                                matches += 1
                                break
                    
                    confidence = min(matches / max(len(discovered_paths), 1), 1.0)
                    
                    if confidence > 0.3:  # Only include meaningful matches
                        content_analysis[category] = {
                            'confidence': confidence,
                            'boost_factor': patterns['boost_factor'],
                            'matches': matches,
                            'total_paths': len(discovered_paths)
                        }
            
            return content_analysis
            
        except Exception as e:
            debug_print(f"Error in database-driven content analysis: {e}", level="ERROR")
            return self._fallback_content_analysis(spider_data)
    
    def _fallback_content_analysis(self, spider_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Fallback content analysis when database is unavailable"""
        fallback_patterns = {
            'admin': {'keywords': ['admin', 'management', 'dashboard', 'control'], 'boost_factor': 1.3},
            'api': {'keywords': ['api', 'rest', 'graphql', 'endpoint'], 'boost_factor': 1.2},
            'auth': {'keywords': ['login', 'auth', 'signin', 'oauth'], 'boost_factor': 1.25},
            'config': {'keywords': ['config', 'settings', 'env', '.config'], 'boost_factor': 1.4},
            'dev': {'keywords': ['dev', 'debug', 'test', 'staging'], 'boost_factor': 1.1}
        }
        
        content_analysis = {}
        discovered_paths = spider_data.get('discovered_paths', [])
        
        for category, pattern_info in fallback_patterns.items():
            matches = 0
            for path in discovered_paths:
                path_str = path if isinstance(path, str) else str(path)
                for keyword in pattern_info['keywords']:
                    if keyword in path_str.lower():
                        matches += 1
                        break
            
            if matches > 0:
                confidence = min(matches / max(len(discovered_paths), 1), 1.0)
                content_analysis[category] = {
                    'confidence': confidence,
                    'boost_factor': pattern_info['boost_factor'],
                    'matches': matches,
                    'total_paths': len(discovered_paths)
                }
        
        return content_analysis
    
    def _calculate_tech_specific_boost(self, tech: Optional[str], spider_data: Dict[str, Any]) -> float:
        """Calculate technology-specific boost based on spider findings"""
        if not tech:
            return 1.0
        
        tech_lower = tech.lower()
        discovered_paths = spider_data.get('discovered_paths', [])
        boost = 1.0
        
        # Technology-specific path patterns
        tech_patterns = {
            'wordpress': ['/wp-admin/', '/wp-content/', '/wp-includes/', '.php'],
            'drupal': ['/admin/', '/node/', '/modules/', '/themes/'],
            'apache': ['/server-status', '/server-info', '.htaccess'],
            'nginx': ['/nginx_status', '.conf'],
            'tomcat': ['/manager/', '/host-manager/', '.jsp'],
            'jenkins': ['/job/', '/build/', '/configure'],
            'php': ['.php', '/phpinfo', '/index.php'],
            'mysql': ['/phpmyadmin/', '/adminer/', '/mysql/'],
            'nodejs': ['/node_modules/', '.js', 'package.json'],
            'python': ['.py', '/admin/', '__pycache__/']
        }
        
        if tech_lower in tech_patterns:
            pattern_matches = 0
            total_patterns = len(tech_patterns[tech_lower])
            
            for path in discovered_paths:
                path_str = path if isinstance(path, str) else str(path)
                for pattern in tech_patterns[tech_lower]:
                    if pattern in path_str.lower():
                        pattern_matches += 1
                        break
            
            if pattern_matches > 0:
                match_ratio = pattern_matches / max(len(discovered_paths), 1)
                boost = 1.0 + (match_ratio * 0.3)  # Up to 30% boost
        
        return min(boost, 1.5)  # Cap at 50% boost
    
    def _analyze_discovered_paths(self, discovered_paths: List[Any], tech: Optional[str]) -> Dict[str, float]:
        """Analyze discovered paths for security relevance"""
        if not discovered_paths:
            return {'security_relevance': 0.0}
        
        # Security-relevant path patterns
        security_patterns = {
            'high_value': ['/admin/', '/manager/', '/config/', '/backup/', '/private/', '/.env', '/secret'],
            'medium_value': ['/login', '/auth/', '/user/', '/account/', '/dashboard/', '/control'],
            'low_value': ['/info', '/status', '/health/', '/debug/', '/test/']
        }
        
        high_matches = 0
        medium_matches = 0
        low_matches = 0
        
        for path in discovered_paths:
            path_str = path if isinstance(path, str) else str(path)
            path_lower = path_str.lower()
            
            # Check high value patterns
            for pattern in security_patterns['high_value']:
                if pattern in path_lower:
                    high_matches += 1
                    break
            else:
                # Check medium value patterns
                for pattern in security_patterns['medium_value']:
                    if pattern in path_lower:
                        medium_matches += 1
                        break
                else:
                    # Check low value patterns
                    for pattern in security_patterns['low_value']:
                        if pattern in path_lower:
                            low_matches += 1
                            break
        
        # Calculate weighted security relevance
        total_paths = len(discovered_paths)
        security_score = (
            (high_matches * 3.0 + medium_matches * 2.0 + low_matches * 1.0) / 
            max(total_paths * 3.0, 1)
        )
        
        return {
            'security_relevance': min(security_score, 1.0),
            'high_value_paths': high_matches,
            'medium_value_paths': medium_matches,
            'low_value_paths': low_matches,
            'total_analyzed': total_paths
        }
    
    def _analyze_file_extensions(self, discovered_paths: List[Any], tech: Optional[str]) -> float:
        """Analyze file extensions for technology-specific boost"""
        if not discovered_paths:
            return 1.0
        
        # Technology-specific file extension mappings
        tech_extensions = {
            'php': ['.php', '.phtml', '.php3', '.php4', '.php5'],
            'asp': ['.asp', '.aspx', '.ashx', '.asmx'],
            'jsp': ['.jsp', '.jspx', '.jsw'],
            'python': ['.py', '.pyc', '.pyo', '.wsgi'], 
            'nodejs': ['.js', '.json', '.node'],
            'ruby': ['.rb', '.rhtml', '.erb'],
            'perl': ['.pl', '.pm', '.cgi'],
            'coldfusion': ['.cfm', '.cfc', '.cfml']
        }
        
        if not tech or tech.lower() not in tech_extensions:
            return 1.0
        
        tech_exts = tech_extensions[tech.lower()]
        matching_files = 0
        total_files = 0
        
        for path in discovered_paths:
            path_str = path if isinstance(path, str) else str(path)
            
            # Count files (paths with extensions)
            if '.' in path_str:
                total_files += 1
                for ext in tech_exts:
                    if path_str.lower().endswith(ext):
                        matching_files += 1
                        break
        
        if total_files == 0:
            return 1.0
        
        match_ratio = matching_files / total_files
        # Boost based on match ratio: higher ratio = higher confidence in technology
        boost = 1.0 + (match_ratio * 0.2)  # Up to 20% boost
        
        return min(boost, 1.3)  # Cap at 30% boost
    
    def _generate_enhanced_reason(self, result, wordlist: str, context: ScoringContext) -> str:
        """Generate enhanced reason with spider intelligence"""
        base_reason = self._generate_reason(result, wordlist)
        
        if not context.spider_data or not context.spider_data.get('has_spider_intel'):
            return base_reason
        
        spider_data = context.spider_data
        enhancements = []
        
        # Add spider-specific context
        if spider_data.get('url_count', 0) > 0:
            enhancements.append(f"{spider_data['url_count']} URLs discovered")
        
        if spider_data.get('categories'):
            categories = ', '.join(spider_data['categories'])
            enhancements.append(f"found {categories} endpoints")
        
        if spider_data.get('tech_confidence', 0) > 0.7:
            confidence = spider_data['tech_confidence']
            sources = ', '.join(spider_data.get('tech_sources', []))
            enhancements.append(f"tech detected with {confidence:.0%} confidence via {sources}")
        
        # Combine base reason with enhancements
        if enhancements:
            enhancement_text = '; '.join(enhancements)
            return f"{base_reason} (Spider: {enhancement_text})"
        
        return base_reason
    
    def _determine_category(self, matched_rules: List[str]) -> str:
        """Determine the primary category from matched rules"""
        if not matched_rules:
            return "none"
        
        # Check first rule
        first_rule = matched_rules[0]
        if first_rule.startswith('exact:'):
            return "exact"
        elif first_rule.startswith('tech_category:'):
            return "tech_category"
        elif first_rule.startswith('tech_pattern:'):
            return "tech_pattern"
        elif first_rule.startswith('port:'):
            return "port"
        elif first_rule.startswith('keyword:'):
            return "keyword"
        elif first_rule == 'generic_fallback':
            return "fallback"
        else:
            return "other"
    
    def _generate_reason(self, result, wordlist: str) -> str:
        """Generate human-readable reason for recommendation"""
        if result.fallback_used:
            return "Generic wordlist for basic discovery"
        
        if result.matched_rules:
            rule = result.matched_rules[0]
            if rule.startswith('exact:'):
                parts = rule.split(':')
                if len(parts) >= 3:
                    return f"Exact match for {parts[1]} on port {parts[2]}"
            elif rule.startswith('tech_category:'):
                category = rule.split(':')[1]
                return f"Matches {category} technology category"
            elif rule.startswith('port:'):
                category = rule.split(':')[1]
                return f"Common wordlist for {category} services"
            elif rule.startswith('keyword:'):
                keyword = rule.split(':')[1]
                return f"Service description contains '{keyword}'"
        
        return f"Recommended based on service analysis (score: {result.score:.3f})"
    
    def _generate_summary(self, result: SmartListResult) -> Dict[str, Any]:
        """Generate enhanced summary of recommendations with spider intelligence"""
        total_services = len(result.services)
        total_recommendations = sum(len(s.recommendations) for s in result.services)
        
        # Find highest confidence services
        high_confidence = [s for s in result.services if s.confidence_level == "HIGH"]
        
        # Collect all detected technologies
        all_techs = set()
        for service in result.services:
            if service.detected_tech:
                all_techs.add(service.detected_tech)
        
        # Analyze spider intelligence impact
        spider_enhanced_services = 0
        total_spider_urls = 0
        spider_categories = set()
        
        for service in result.services:
            context_summary = service.context_summary
            if context_summary.get('spider_intelligence', {}).get('enhanced_scoring'):
                spider_enhanced_services += 1
                spider_intel = context_summary['spider_intelligence']
                total_spider_urls += spider_intel.get('urls_discovered', 0)
                spider_categories.update(spider_intel.get('categories_found', []))
        
        # Build enhanced summary
        summary = {
            'analysis_complete': True,
            'total_services_analyzed': total_services,
            'total_wordlists_recommended': total_recommendations,
            'high_confidence_services': len(high_confidence),
            'detected_technologies': list(all_techs),
            'recommendation': self._get_enhanced_summary_recommendation(result, spider_enhanced_services)
        }
        
        # Add spider intelligence summary
        if spider_enhanced_services > 0:
            summary['spider_intelligence'] = {
                'services_enhanced': spider_enhanced_services,
                'total_urls_discovered': total_spider_urls,
                'categories_found': list(spider_categories),
                'intelligence_boost': True
            }
        
        # Add enhanced top recommendations with spider context
        if high_confidence:
            summary['top_targets'] = []
            for s in high_confidence[:3]:
                target_info = {
                    'service': f"{s.target}:{s.port}",
                    'technology': s.detected_tech,
                    'top_wordlist': s.recommendations[0].wordlist if s.recommendations else None
                }
                
                # Add spider context if available
                spider_intel = s.context_summary.get('spider_intelligence')
                if spider_intel:
                    target_info['spider_context'] = {
                        'urls_found': spider_intel.get('urls_discovered', 0),
                        'categories': spider_intel.get('categories_found', []),
                        'enhanced': True
                    }
                
                summary['top_targets'].append(target_info)
        
        return summary
    
    
    def _get_enhanced_summary_recommendation(self, result: SmartListResult, spider_enhanced_services: int) -> str:
        """Generate enhanced overall recommendation with spider intelligence"""
        high_conf = sum(1 for s in result.services if s.confidence_level == "HIGH")
        med_conf = sum(1 for s in result.services if s.confidence_level == "MEDIUM")
        
        base_rec = ""
        if high_conf > 0:
            base_rec = f"Found {high_conf} high-confidence targets. Focus fuzzing efforts on these services first."
        elif med_conf > 0:
            base_rec = f"Found {med_conf} medium-confidence targets. Consider additional reconnaissance to improve targeting."
        else:
            base_rec = "All recommendations are low confidence. Run more detailed scans or manually verify services."
        
        # Add spider intelligence context
        if spider_enhanced_services > 0:
            spider_context = f" Spider intelligence enhanced {spider_enhanced_services} service(s) with additional URL discovery and technology detection."
            return base_rec + spider_context
        
        return base_rec
    
    def _get_summary_recommendation(self, result: SmartListResult) -> str:
        """Generate overall recommendation (legacy method)"""
        return self._get_enhanced_summary_recommendation(result, 0)
    
    def _save_to_scan_reports(self, target: str, result: SmartListResult):
        """Save SmartList results to scan reports"""
        # Results are automatically included via WorkflowResult.data
        debug_print(f"SmartList analysis complete for {target}")