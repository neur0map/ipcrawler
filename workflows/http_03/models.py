"""Models for HTTP scanning results"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class DNSRecord:
    """DNS record information"""
    type: str
    value: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HTTPVulnerability:
    """HTTP vulnerability information"""
    type: str
    severity: str  # low, medium, high, critical
    description: str
    url: str
    evidence: Optional[str] = None
    remediation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class HTTPService:
    """HTTP service information"""
    port: int
    scheme: str  # http or https
    url: str
    status_code: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    server: Optional[str] = None
    is_https: bool = False
    technologies: List[str] = field(default_factory=list)
    discovered_paths: List[str] = field(default_factory=list)
    response_body: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Don't include response_body in output
        data.pop('response_body', None)
        return data


@dataclass
class HTTPScanResult:
    """Complete HTTP scan results"""
    target: str
    services: List[HTTPService] = field(default_factory=list)
    vulnerabilities: List[HTTPVulnerability] = field(default_factory=list)
    dns_records: List[DNSRecord] = field(default_factory=list)
    subdomains: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'target': self.target,
            'services': [s.to_dict() for s in self.services],
            'vulnerabilities': [v.to_dict() for v in self.vulnerabilities],
            'dns_records': [d.to_dict() for d in self.dns_records],
            'subdomains': self.subdomains,
            'summary': {
                'total_services': len(self.services),
                'total_vulnerabilities': len(self.vulnerabilities),
                'severity_counts': self._count_severities(),
                'technologies': self._get_all_technologies(),
                'discovered_paths': self._get_all_paths()
            }
        }
    
    def _count_severities(self) -> Dict[str, int]:
        """Count vulnerabilities by severity"""
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for vuln in self.vulnerabilities:
            if vuln.severity in counts:
                counts[vuln.severity] += 1
        return counts
    
    def _get_all_technologies(self) -> List[str]:
        """Get all unique technologies detected"""
        techs = []
        for service in self.services:
            techs.extend(service.technologies)
        return list(set(techs))
    
    def _get_all_paths(self) -> List[str]:
        """Get all discovered paths"""
        paths = []
        for service in self.services:
            paths.extend(service.discovered_paths)
        return list(set(paths))