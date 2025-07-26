"""Models for SmartList wordlist recommendations"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class WordlistRecommendation:
    """Individual wordlist recommendation with metadata"""
    wordlist: str                  # Wordlist filename
    path: Optional[str] = None     # Full file path (if catalog available)
    score: float = 0.0             # Relevance score (0.0-1.0)
    confidence: str = "LOW"        # HIGH, MEDIUM, LOW
    reason: str = ""               # Human-readable explanation
    category: str = ""             # Rule category that matched
    matched_rule: str = ""         # Specific rule name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'wordlist': self.wordlist,
            'path': self.path,
            'score': round(self.score, 3),
            'confidence': self.confidence,
            'reason': self.reason,
            'category': self.category,
            'matched_rule': self.matched_rule
        }


@dataclass
class ServiceRecommendation:
    """Recommendations for a specific service"""
    target: str
    port: int
    service_name: str
    detected_tech: Optional[str] = None
    recommendations: List[WordlistRecommendation] = field(default_factory=list)
    context_summary: Dict[str, Any] = field(default_factory=dict)
    total_score: float = 0.0
    confidence_level: str = "LOW"
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'target': self.target,
            'port': self.port,
            'service_name': self.service_name,
            'detected_tech': self.detected_tech,
            'recommendations': [r.to_dict() for r in self.recommendations],
            'context_summary': self.context_summary,
            'total_score': round(self.total_score, 3),
            'confidence_level': self.confidence_level,
            'score_breakdown': {k: round(v, 3) for k, v in self.score_breakdown.items()}
        }


@dataclass
class SmartListResult:
    """Complete SmartList analysis results"""
    target: str
    services: List[ServiceRecommendation] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    port_database_available: bool = False
    catalog_available: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'target': self.target,
            'services': [s.to_dict() for s in self.services],
            'summary': self.summary,
            'execution_time': round(self.execution_time, 2),
            'port_database_available': self.port_database_available,
            'catalog_available': self.catalog_available,
            'statistics': self._get_statistics(),
            'wordlist_recommendations': self._format_recommendations()
        }
    
    def _format_recommendations(self) -> List[Dict[str, Any]]:
        """Format recommendations for report integration"""
        recommendations = []
        for service in self.services:
            service_rec = {
                'service': f"{service.target}:{service.port}",
                'service_name': service.service_name,
                'detected_technology': service.detected_tech,
                'confidence': service.confidence_level,
                'port': service.port,
                'total_score': round(service.total_score, 3),
                'top_wordlists': []
            }
            
            # Include top 5 wordlists with full details
            for rec in service.recommendations[:5]:
                wordlist_info = {
                    'wordlist': rec.wordlist,
                    'score': round(rec.score, 3),
                    'confidence': rec.confidence,
                    'reason': rec.reason,
                    'category': rec.category,
                    'matched_rule': rec.matched_rule,
                    'path': rec.path
                }
                service_rec['top_wordlists'].append(wordlist_info)
            
            # Add score breakdown
            service_rec['score_breakdown'] = {
                k: round(v, 3) for k, v in service.score_breakdown.items() if v > 0
            }
            
            # Add context information
            service_rec['context'] = {
                'port_database_tech': service.context_summary.get('port_database_tech', []),
                'service_category': service.context_summary.get('service_category'),
                'risk_level': service.context_summary.get('risk_level'),
                'matched_rules': service.context_summary.get('matched_rules', []),
                'fallback_used': service.context_summary.get('fallback_used', False)
            }
            
            recommendations.append(service_rec)
        
        return recommendations
    
    def _get_statistics(self) -> Dict[str, Any]:
        """Generate statistics from results"""
        total_services = len(self.services)
        total_recommendations = sum(len(s.recommendations) for s in self.services)
        
        confidence_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        tech_counts = {}
        category_counts = {}
        
        for service in self.services:
            # Count confidence levels
            if service.confidence_level in confidence_counts:
                confidence_counts[service.confidence_level] += 1
            
            # Count technologies
            if service.detected_tech:
                tech_counts[service.detected_tech] = tech_counts.get(service.detected_tech, 0) + 1
            
            # Count rule categories
            for rec in service.recommendations:
                category_counts[rec.category] = category_counts.get(rec.category, 0) + 1
        
        return {
            'total_services': total_services,
            'total_recommendations': total_recommendations,
            'confidence_distribution': confidence_counts,
            'technologies_detected': list(tech_counts.keys()),
            'technology_counts': tech_counts,
            'rule_category_usage': category_counts
        }