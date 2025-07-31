#!/usr/bin/env python3
"""
Workflow Feedback System for SmartList Scorer

Integrates discoveries from all workflows to enhance wordlist scoring.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import json
import re

logger = logging.getLogger(__name__)


@dataclass
class WorkflowFeedback:
    """Feedback data from workflow execution"""
    workflow_name: str
    discovered_technologies: List[str]
    discovered_paths: List[str]
    discovered_hostnames: List[str]
    response_patterns: List[str]
    header_indicators: Dict[str, str]
    confidence_scores: Dict[str, float]
    version_info: Optional[str] = None
    spider_data: Optional[Dict[str, Any]] = None


class WorkflowFeedbackCollector:
    """Collects and processes feedback from all workflows"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent.parent / "database"
        self.tech_db = None
        self.feedback_cache = {}
        self._load_tech_db()
    
    def _load_tech_db(self):
        """Load technology database for pattern matching"""
        try:
            tech_db_path = self.db_path / "technologies" / "tech_db.json"
            if tech_db_path.exists():
                with open(tech_db_path, 'r') as f:
                    self.tech_db = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load tech database: {e}")
            self.tech_db = {}
    
    def collect_http_feedback(self, http_results: Dict[str, Any]) -> WorkflowFeedback:
        """Extract feedback from HTTP_03 workflow results"""
        discovered_technologies = []
        discovered_paths = []
        discovered_hostnames = []
        response_patterns = []
        header_indicators = {}
        confidence_scores = {}
        version_info = None
        
        # Extract from services
        services = http_results.get('services', [])
        for service in services:
            # Technologies
            techs = service.get('technologies', [])
            discovered_technologies.extend(techs)
            
            # Paths
            paths = service.get('discovered_paths', [])
            discovered_paths.extend(paths)
            
            # Hostnames
            hostnames = service.get('discovered_hostnames', [])
            discovered_hostnames.extend(hostnames)
            
            # Headers for pattern analysis
            headers = service.get('headers', {})
            header_indicators.update(headers)
            
            # Response body patterns
            response_body = service.get('response_body', '')
            if response_body:
                # Extract technology indicators from response
                patterns = self._extract_response_patterns(response_body)
                response_patterns.extend(patterns)
            
            # Version detection from headers or response
            version = self._extract_version_info(headers, response_body)
            if version:
                version_info = version
        
        # Calculate confidence scores based on pattern matches
        confidence_scores = self._calculate_confidence_scores(
            discovered_technologies, response_patterns, header_indicators
        )
        
        return WorkflowFeedback(
            workflow_name="http_03",
            discovered_technologies=list(set(discovered_technologies)),
            discovered_paths=list(set(discovered_paths)),
            discovered_hostnames=list(set(discovered_hostnames)),
            response_patterns=response_patterns,
            header_indicators=header_indicators,
            confidence_scores=confidence_scores,
            version_info=version_info
        )
    
    def collect_spider_feedback(self, spider_results: Dict[str, Any]) -> WorkflowFeedback:
        """Extract feedback from Mini Spider workflow results"""
        discovered_technologies = []
        discovered_paths = []
        discovered_hostnames = []
        response_patterns = []
        header_indicators = {}
        confidence_scores = {}
        spider_data = {}
        
        # Extract from crawled URLs
        crawled_urls = spider_results.get('crawled_urls', [])
        unique_paths = set()
        
        for crawled_url in crawled_urls:
            if isinstance(crawled_url, dict):
                url = crawled_url.get('url', '')
                status_code = crawled_url.get('status_code', 0)
                
                # Extract path from URL
                from urllib.parse import urlparse
                parsed = urlparse(url)
                if parsed.path and parsed.path != '/':
                    unique_paths.add(parsed.path)
                
                # Extract hostname
                if parsed.hostname:
                    discovered_hostnames.append(parsed.hostname)
        
        discovered_paths = list(unique_paths)
        
        # Extract technology insights from spider analysis
        analysis_results = spider_results.get('analysis_results', {})
        if analysis_results:
            # Technology patterns found during spidering
            tech_patterns = analysis_results.get('technology_patterns', [])
            discovered_technologies.extend(tech_patterns)
            
            # Response patterns
            patterns = analysis_results.get('interesting_patterns', [])
            response_patterns.extend(patterns)
            
            spider_data = analysis_results
        
        return WorkflowFeedback(
            workflow_name="mini_spider_04",
            discovered_technologies=list(set(discovered_technologies)),
            discovered_paths=discovered_paths,
            discovered_hostnames=list(set(discovered_hostnames)),
            response_patterns=response_patterns,
            header_indicators=header_indicators,
            confidence_scores=confidence_scores,
            spider_data=spider_data
        )
    
    def collect_smartlist_feedback(self, smartlist_results: Dict[str, Any]) -> WorkflowFeedback:
        """Extract feedback from SmartList workflow results"""
        discovered_technologies = []
        discovered_paths = []
        response_patterns = []
        confidence_scores = {}
        
        # Extract wordlist performance data
        wordlist_performance = smartlist_results.get('wordlist_performance', {})
        successful_wordlists = smartlist_results.get('successful_wordlists', [])
        
        # Analyze which wordlists were most successful
        for wordlist_name in successful_wordlists:
            performance = wordlist_performance.get(wordlist_name, {})
            success_rate = performance.get('success_rate', 0.0)
            
            if success_rate > 0.5:  # Successful wordlist
                # Infer technology from successful wordlist patterns
                inferred_tech = self._infer_technology_from_wordlist(wordlist_name)
                if inferred_tech:
                    discovered_technologies.append(inferred_tech)
                    confidence_scores[inferred_tech] = success_rate
        
        # Extract discovered paths from results
        discovered_endpoints = smartlist_results.get('discovered_endpoints', [])
        for endpoint in discovered_endpoints:
            if isinstance(endpoint, dict):
                path = endpoint.get('path', '')
                if path:
                    discovered_paths.append(path)
        
        return WorkflowFeedback(
            workflow_name="smartlist_05",
            discovered_technologies=list(set(discovered_technologies)),
            discovered_paths=discovered_paths,
            discovered_hostnames=[],
            response_patterns=response_patterns,
            header_indicators={},
            confidence_scores=confidence_scores
        )
    
    def aggregate_feedback(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate feedback from all workflows"""
        feedback_list = []
        
        # Collect feedback from each workflow
        if 'http_03' in all_results:
            http_feedback = self.collect_http_feedback(all_results['http_03'])
            feedback_list.append(http_feedback)
        
        if 'mini_spider_04' in all_results:
            spider_feedback = self.collect_spider_feedback(all_results['mini_spider_04'])
            feedback_list.append(spider_feedback)
        
        if 'smartlist_05' in all_results:
            smartlist_feedback = self.collect_smartlist_feedback(all_results['smartlist_05'])
            feedback_list.append(smartlist_feedback)
        
        # Aggregate all feedback
        aggregated = {
            'technologies': {},
            'paths': set(),
            'hostnames': set(),
            'response_patterns': [],
            'confidence_scores': {},
            'version_info': None,
            'spider_insights': {}
        }
        
        for feedback in feedback_list:
            # Aggregate technologies with confidence
            for tech in feedback.discovered_technologies:
                if tech in aggregated['technologies']:
                    aggregated['technologies'][tech] += 1
                else:
                    aggregated['technologies'][tech] = 1
            
            # Merge confidence scores
            for tech, confidence in feedback.confidence_scores.items():
                if tech in aggregated['confidence_scores']:
                    aggregated['confidence_scores'][tech] = max(
                        aggregated['confidence_scores'][tech], confidence
                    )
                else:
                    aggregated['confidence_scores'][tech] = confidence
            
            # Aggregate other data
            aggregated['paths'].update(feedback.discovered_paths)
            aggregated['hostnames'].update(feedback.discovered_hostnames)
            aggregated['response_patterns'].extend(feedback.response_patterns)
            
            if feedback.version_info:
                aggregated['version_info'] = feedback.version_info
            
            if feedback.spider_data:
                aggregated['spider_insights'] = feedback.spider_data
        
        # Convert sets to lists for JSON serialization
        aggregated['paths'] = list(aggregated['paths'])
        aggregated['hostnames'] = list(aggregated['hostnames'])
        
        return aggregated
    
    def _extract_response_patterns(self, response_body: str) -> List[str]:
        """Extract technology patterns from response body"""
        patterns = []
        
        if not self.tech_db or not response_body:
            return patterns
        
        response_lower = response_body.lower()
        
        # Check against tech_db patterns
        for category, technologies in self.tech_db.items():
            for tech, tech_info in technologies.items():
                response_patterns = tech_info.get('indicators', {}).get('response_patterns', [])
                for pattern in response_patterns:
                    if pattern.lower() in response_lower:
                        patterns.append(f"{tech}:{pattern}")
        
        return patterns
    
    def _extract_version_info(self, headers: Dict[str, str], response_body: str) -> Optional[str]:
        """Extract version information from headers or response body"""
        # Check common version headers
        version_headers = ['server', 'x-powered-by', 'x-generator']
        
        for header in version_headers:
            value = headers.get(header, '').lower()
            if value:
                # Extract version numbers
                version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', value)
                if version_match:
                    return version_match.group(1)
        
        # Check response body for version indicators
        if response_body:
            # Look for common version patterns
            version_patterns = [
                r'version[:\s]+(\d+\.\d+(?:\.\d+)?)',
                r'v(\d+\.\d+(?:\.\d+)?)',
                r'(\d+\.\d+(?:\.\d+)?)\s+release'
            ]
            
            for pattern in version_patterns:
                match = re.search(pattern, response_body.lower())
                if match:
                    return match.group(1)
        
        return None
    
    def _calculate_confidence_scores(self, technologies: List[str], 
                                   response_patterns: List[str],
                                   headers: Dict[str, str]) -> Dict[str, float]:
        """Calculate confidence scores for detected technologies"""
        confidence_scores = {}
        
        for tech in technologies:
            score = 0.5  # Base confidence
            
            # Check if tech has supporting patterns
            tech_patterns = [p for p in response_patterns if p.startswith(f"{tech}:")]
            if tech_patterns:
                score += 0.3  # Boost for response pattern match
            
            # Check if tech appears in headers
            for header_value in headers.values():
                if tech.lower() in header_value.lower():
                    score += 0.2  # Boost for header match
                    break
            
            confidence_scores[tech] = min(1.0, score)
        
        return confidence_scores
    
    def _infer_technology_from_wordlist(self, wordlist_name: str) -> Optional[str]:
        """Infer technology from successful wordlist name"""
        wordlist_lower = wordlist_name.lower()
        
        # Common wordlist to technology mappings
        tech_mappings = {
            'wordpress': 'wordpress',
            'wp': 'wordpress',
            'drupal': 'drupal',
            'joomla': 'joomla',
            'django': 'django',
            'laravel': 'laravel',
            'tomcat': 'tomcat',
            'jenkins': 'jenkins',
            'phpmyadmin': 'phpmyadmin',
            'apache': 'apache',
            'nginx': 'nginx'
        }
        
        for pattern, tech in tech_mappings.items():
            if pattern in wordlist_lower:
                return tech
        
        return None


# Global feedback collector instance
feedback_collector = WorkflowFeedbackCollector()


def get_feedback_collector() -> WorkflowFeedbackCollector:
    """Get the global feedback collector instance"""
    return feedback_collector


def enhance_scoring_context(original_context: Dict[str, Any], 
                           workflow_results: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance scoring context with workflow feedback"""
    if not workflow_results:
        return original_context
    
    # Aggregate feedback from all workflows
    aggregated_feedback = feedback_collector.aggregate_feedback(workflow_results)
    
    # Enhance the original context
    enhanced_context = original_context.copy()
    
    # Add discovered technologies with confidence
    if aggregated_feedback['technologies']:
        # Get the most frequently detected technology
        most_common_tech = max(aggregated_feedback['technologies'].items(), 
                              key=lambda x: x[1])
        enhanced_context['primary_technology'] = most_common_tech[0]
        enhanced_context['tech_confidence'] = aggregated_feedback['confidence_scores'].get(
            most_common_tech[0], 0.5
        )
    
    # Add version information
    if aggregated_feedback['version_info']:
        enhanced_context['version'] = aggregated_feedback['version_info']
    
    # Add discovered paths for path-aware scoring
    if aggregated_feedback['paths']:
        enhanced_context['discovered_paths'] = aggregated_feedback['paths']
    
    # Add response patterns
    if aggregated_feedback['response_patterns']:
        enhanced_context['response_patterns'] = aggregated_feedback['response_patterns']
    
    # Add spider insights
    if aggregated_feedback['spider_insights']:
        enhanced_context['spider_data'] = aggregated_feedback['spider_insights']
    
    logger.debug(f"Enhanced context with {len(aggregated_feedback['technologies'])} technologies, "
                f"{len(aggregated_feedback['paths'])} paths")
    
    return enhanced_context