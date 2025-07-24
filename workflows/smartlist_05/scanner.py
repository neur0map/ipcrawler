"""SmartList Wordlist Recommendation Scanner"""
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
from datetime import datetime

from workflows.core.base import BaseWorkflow, WorkflowResult
from .models import SmartListResult, ServiceRecommendation, WordlistRecommendation
from utils.debug import debug_print
from utils.results import result_manager

# Import SmartList components
try:
    from src.core.scorer import (
        score_wordlists_with_catalog,
        score_wordlists,
        get_wordlist_paths,
        get_port_context,
        explain_scoring,
        get_scoring_stats,
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
            
            # Check component availability
            stats = get_scoring_stats() if SMARTLIST_AVAILABLE else {}
            result.port_database_available = stats.get('port_database_available', False)
            result.catalog_available = stats.get('catalog_available', False)
            
            # Aggregate scan results from previous workflows
            aggregated_data = self._aggregate_scan_results(previous_results)
            
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
        """Aggregate data from previous workflow results"""
        aggregated = {
            'services': [],
            'technologies': {},
            'os_info': None,
            'dns_records': [],
            'vulnerabilities': []
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
                                    categories.add(url_data['category'])
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
        
        debug_print(f"Aggregated {len(aggregated['services'])} services from previous scans")
        return aggregated
    
    def _build_service_context(self, service_data: Dict[str, Any], 
                              aggregated_data: Dict[str, Any]) -> ScoringContext:
        """Build ScoringContext from service data with spider intelligence"""
        # Extract technology with multi-source confidence scoring
        tech = None
        tech_confidence = 0.0
        tech_sources = []
        
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
        
        # 3. Check product/version from nmap - Medium confidence
        elif service_data.get('product'):
            # Extract technology from product name
            product = service_data['product'].lower()
            # Common technology patterns
            tech_patterns = {
                'apache': 'apache',
                'nginx': 'nginx',
                'mysql': 'mysql',
                'mariadb': 'mariadb',
                'postgresql': 'postgresql',
                'mongodb': 'mongodb',
                'redis': 'redis',
                'tomcat': 'tomcat',
                'wordpress': 'wordpress',
                'drupal': 'drupal',
                'joomla': 'joomla',
                'jenkins': 'jenkins',
                'gitlab': 'gitlab',
                'phpmyadmin': 'phpmyadmin'
            }
            
            for pattern, tech_name in tech_patterns.items():
                if pattern in product:
                    tech = tech_name
                    tech_confidence = 0.7
                    tech_sources.append('nmap_product')
                    break
        
        # 4. Check X-Powered-By header - Medium confidence
        elif service_data.get('headers', {}).get('X-Powered-By'):
            powered_by = service_data['headers']['X-Powered-By']
            if powered_by:
                tech = powered_by.split('/')[0].lower()
                tech_confidence = 0.6
                tech_sources.append('http_header')
        
        # 5. Infer from spider URL categories - Lower confidence but useful
        elif service_data.get('spider_categories'):
            category_tech_map = {
                'admin': 'admin_panel',
                'api': 'rest_api',
                'auth': 'authentication',
                'docs': 'documentation',
                'dev': 'development'
            }
            
            for category in service_data['spider_categories']:
                if category in category_tech_map:
                    tech = category_tech_map[category]
                    tech_confidence = 0.4
                    tech_sources.append('spider_categories')
                    break
        
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
        
        # Create enhanced context with spider data
        context = ScoringContext(
            target=service_data['host'],
            port=service_data['port'],
            service=service_desc,
            tech=tech,
            os=aggregated_data.get('os_info', {}).get('os') if aggregated_data.get('os_info') else None,
            version=service_data.get('version'),
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
        except Exception as e:
            debug_print(f"Could not resolve wordlist paths: {e}")
            wordlist_paths = [None] * len(result.wordlists)
        
        # Build enhanced recommendations with spider context
        recommendations = []
        for i, wordlist in enumerate(result.wordlists[:10]):  # Top 10
            # Determine which rule category this came from
            category = self._determine_category(result.matched_rules)
            
            # Use full path if available, otherwise just the wordlist name
            wordlist_path = wordlist_paths[i] if i < len(wordlist_paths) and wordlist_paths[i] else None
            
            # Generate enhanced reason with spider context
            reason = self._generate_enhanced_reason(result, wordlist, context)
            
            rec = WordlistRecommendation(
                wordlist=wordlist,
                path=wordlist_path,
                score=result.score,
                confidence=result.confidence.value.upper(),  # Convert enum to string
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
            confidence_level=result.confidence.value.upper(),
            score_breakdown={
                'exact_match': result.explanation.exact_match,
                'tech_category': result.explanation.tech_category,
                'port_context': result.explanation.port_context,
                'service_keywords': result.explanation.service_keywords,
                'generic_fallback': result.explanation.generic_fallback
            }
        )
        
        return service_rec
    
    def _apply_spider_scoring_boosts(self, result, context: ScoringContext, service_data: Dict[str, Any]):
        """Apply scoring boosts based on spider intelligence"""
        spider_data = context.spider_data
        boost_factor = 1.0
        additional_rules = []
        
        # High tech confidence boost
        if spider_data.get('tech_confidence', 0) > 0.8:
            boost_factor *= 1.2
            additional_rules.append(f"spider_tech_confidence:{spider_data['tech_confidence']:.2f}")
        
        # URL category boosts
        category_boosts = {
            'admin': 1.3,  # Admin panels are high value targets
            'api': 1.2,    # APIs are important
            'auth': 1.25,  # Authentication endpoints
            'config': 1.4, # Config files are critical
            'dev': 1.1     # Development resources
        }
        
        for category in spider_data.get('categories', []):
            if category in category_boosts:
                boost_factor *= category_boosts[category]
                additional_rules.append(f"spider_category:{category}")
        
        # Path discovery boost - more paths = better targeting
        path_count = len(spider_data.get('discovered_paths', []))
        if path_count > 10:
            boost_factor *= 1.15
            additional_rules.append(f"spider_paths_rich:{path_count}")
        elif path_count > 5:
            boost_factor *= 1.1
            additional_rules.append(f"spider_paths_good:{path_count}")
        
        # Apply boosts to result
        if boost_factor > 1.0:
            result.score = min(result.score * boost_factor, 1.0)  # Cap at 1.0
            result.matched_rules.extend(additional_rules)
            debug_print(f"Applied spider boost factor {boost_factor:.2f} to recommendations")
        
        return result
    
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