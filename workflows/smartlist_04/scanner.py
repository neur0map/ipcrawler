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
        super().__init__(name="smartlist_04")
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
        
        debug_print(f"Aggregated {len(aggregated['services'])} services from previous scans")
        return aggregated
    
    def _build_service_context(self, service_data: Dict[str, Any], 
                              aggregated_data: Dict[str, Any]) -> ScoringContext:
        """Build ScoringContext from service data"""
        # Extract technology - prioritize explicit detections
        tech = None
        
        # 1. Check technologies array (from http scan)
        if service_data.get('technologies') and len(service_data['technologies']) > 0 and service_data['technologies'][0]:
            tech = service_data['technologies'][0].lower()
        
        # 2. Check product/version from nmap
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
                    break
        
        # 3. Check X-Powered-By header
        elif service_data.get('headers', {}).get('X-Powered-By'):
            powered_by = service_data['headers']['X-Powered-By']
            if powered_by:
                tech = powered_by.split('/')[0].lower()
        
        # Build service description
        service_desc_parts = []
        if service_data.get('product'):
            service_desc_parts.append(service_data['product'])
        if service_data.get('version'):
            service_desc_parts.append(service_data['version'])
        if service_data.get('extra_info'):
            service_desc_parts.append(service_data['extra_info'])
        if not service_desc_parts and service_data.get('service'):
            service_desc_parts.append(service_data['service'])
        
        service_desc = ' '.join(service_desc_parts) or f"Service on port {service_data['port']}"
        
        # Create context - let port database enhance if tech is None
        context = ScoringContext(
            target=service_data['host'],
            port=service_data['port'],
            service=service_desc,
            tech=tech,
            os=aggregated_data.get('os_info', {}).get('os') if aggregated_data.get('os_info') else None,
            version=service_data.get('version'),
            headers=service_data.get('headers', {})
        )
        
        debug_print(f"Built context for {context.target}:{context.port} - tech: {tech}")
        return context
    
    async def _get_service_recommendations(self, context: ScoringContext, 
                                         service_data: Dict[str, Any]) -> ServiceRecommendation:
        """Get SmartList recommendations for a service"""
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
        
        # Build recommendations
        recommendations = []
        for i, wordlist in enumerate(result.wordlists[:10]):  # Top 10
            # Determine which rule category this came from
            category = self._determine_category(result.matched_rules)
            
            rec = WordlistRecommendation(
                wordlist=wordlist,
                path=wordlist_paths[i] if i < len(wordlist_paths) else None,
                score=result.score,
                confidence=result.confidence.value.upper(),  # Convert enum to string
                reason=self._generate_reason(result, wordlist),
                category=category,
                matched_rule=result.matched_rules[0] if result.matched_rules else "none"
            )
            recommendations.append(rec)
        
        # Build context summary
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
        """Generate summary of recommendations"""
        total_services = len(result.services)
        total_recommendations = sum(len(s.recommendations) for s in result.services)
        
        # Find highest confidence services
        high_confidence = [s for s in result.services if s.confidence_level == "HIGH"]
        
        # Collect all detected technologies
        all_techs = set()
        for service in result.services:
            if service.detected_tech:
                all_techs.add(service.detected_tech)
        
        # Build summary
        summary = {
            'analysis_complete': True,
            'total_services_analyzed': total_services,
            'total_wordlists_recommended': total_recommendations,
            'high_confidence_services': len(high_confidence),
            'detected_technologies': list(all_techs),
            'recommendation': self._get_summary_recommendation(result)
        }
        
        # Add top recommendations
        if high_confidence:
            summary['top_targets'] = [
                {
                    'service': f"{s.target}:{s.port}",
                    'technology': s.detected_tech,
                    'top_wordlist': s.recommendations[0].wordlist if s.recommendations else None
                }
                for s in high_confidence[:3]
            ]
        
        return summary
    
    def _get_summary_recommendation(self, result: SmartListResult) -> str:
        """Generate overall recommendation"""
        high_conf = sum(1 for s in result.services if s.confidence_level == "HIGH")
        med_conf = sum(1 for s in result.services if s.confidence_level == "MEDIUM")
        
        if high_conf > 0:
            return f"Found {high_conf} high-confidence targets. Focus fuzzing efforts on these services first."
        elif med_conf > 0:
            return f"Found {med_conf} medium-confidence targets. Consider additional reconnaissance to improve targeting."
        else:
            return "All recommendations are low confidence. Run more detailed scans or manually verify services."
    
    def _save_to_scan_reports(self, target: str, result: SmartListResult):
        """Save SmartList results to scan reports"""
        # Results are automatically included via WorkflowResult.data
        debug_print(f"SmartList analysis complete for {target}")