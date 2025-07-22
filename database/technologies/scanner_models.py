"""
Pydantic models for scanner configuration database
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import json


class DNSEnumerationConfig(BaseModel):
    """DNS enumeration configuration"""
    common_subdomain_patterns: List[str] = Field(default_factory=list)


class MonitoringHTMLPattern(BaseModel):
    """HTML pattern for monitoring detection"""
    pattern: str
    description: str


class JavaScriptConfigPattern(BaseModel):
    """JavaScript configuration pattern"""
    pattern: str
    description: str


class PathDiscoveryConfig(BaseModel):
    """Path discovery configuration"""
    common_application_paths: List[str] = Field(default_factory=list)
    monitoring_html_patterns: List[MonitoringHTMLPattern] = Field(default_factory=list)
    javascript_config_patterns: List[JavaScriptConfigPattern] = Field(default_factory=list)
    server_specific_paths: Dict[str, List[str]] = Field(default_factory=dict)


class ContentValidationConfig(BaseModel):
    """Content validation configuration"""
    error_indicators: List[str] = Field(default_factory=list)
    valid_content_indicators: List[str] = Field(default_factory=list)
    valid_status_codes: List[int] = Field(default_factory=list)


class SecurityAnalysisConfig(BaseModel):
    """Security analysis configuration"""
    security_headers: Dict[str, str] = Field(default_factory=dict)
    information_disclosure_headers: List[str] = Field(default_factory=list)
    content_validation: ContentValidationConfig = Field(default_factory=ContentValidationConfig)


class HostnameGenerationConfig(BaseModel):
    """Hostname generation configuration"""
    common_subdomains: List[str] = Field(default_factory=list)


class ScannerConfiguration(BaseModel):
    """Complete scanner configuration database"""
    dns_enumeration: DNSEnumerationConfig = Field(default_factory=DNSEnumerationConfig)
    path_discovery: PathDiscoveryConfig = Field(default_factory=PathDiscoveryConfig)
    security_analysis: SecurityAnalysisConfig = Field(default_factory=SecurityAnalysisConfig)
    hostname_generation: HostnameGenerationConfig = Field(default_factory=HostnameGenerationConfig)


def load_scanner_configuration_from_file(file_path: Path) -> ScannerConfiguration:
    """Load scanner configuration from JSON file"""
    with open(file_path, 'r') as f:
        json_data = json.load(f)
    
    # Transform the JSON structure to match our model
    config_data = {}
    
    # DNS enumeration
    if 'dns_enumeration' in json_data:
        config_data['dns_enumeration'] = DNSEnumerationConfig(**json_data['dns_enumeration'])
    
    # Path discovery
    if 'path_discovery' in json_data:
        path_data = json_data['path_discovery']
        
        # Transform monitoring patterns
        monitoring_patterns = []
        for pattern_data in path_data.get('monitoring_html_patterns', []):
            monitoring_patterns.append(MonitoringHTMLPattern(**pattern_data))
        
        # Transform JS config patterns
        js_patterns = []
        for pattern_data in path_data.get('javascript_config_patterns', []):
            js_patterns.append(JavaScriptConfigPattern(**pattern_data))
        
        config_data['path_discovery'] = PathDiscoveryConfig(
            common_application_paths=path_data.get('common_application_paths', []),
            monitoring_html_patterns=monitoring_patterns,
            javascript_config_patterns=js_patterns,
            server_specific_paths=path_data.get('server_specific_paths', {})
        )
    
    # Security analysis
    if 'security_analysis' in json_data:
        sec_data = json_data['security_analysis']
        
        # Transform content validation
        content_val = ContentValidationConfig()
        if 'content_validation' in sec_data:
            content_val = ContentValidationConfig(**sec_data['content_validation'])
        
        config_data['security_analysis'] = SecurityAnalysisConfig(
            security_headers=sec_data.get('security_headers', {}),
            information_disclosure_headers=sec_data.get('information_disclosure_headers', []),
            content_validation=content_val
        )
    
    # Hostname generation
    if 'hostname_generation' in json_data:
        config_data['hostname_generation'] = HostnameGenerationConfig(**json_data['hostname_generation'])
    
    return ScannerConfiguration(**config_data)


class ScannerConfigManager:
    """Manager for scanner configuration with lazy loading"""
    
    def __init__(self, config_file_path: Path):
        self.config_file_path = config_file_path
        self._config: Optional[ScannerConfiguration] = None
    
    @property
    def config(self) -> ScannerConfiguration:
        """Get configuration with lazy loading"""
        if self._config is None:
            self._config = load_scanner_configuration_from_file(self.config_file_path)
        return self._config
    
    def get_common_subdomain_patterns(self) -> List[str]:
        """Get common subdomain patterns for DNS enumeration"""
        return self.config.dns_enumeration.common_subdomain_patterns
    
    def get_common_application_paths(self) -> List[str]:
        """Get common application paths for discovery"""
        return self.config.path_discovery.common_application_paths
    
    def get_monitoring_html_patterns(self) -> List[str]:
        """Get monitoring HTML patterns as regex strings"""
        return [pattern.pattern for pattern in self.config.path_discovery.monitoring_html_patterns]
    
    def get_javascript_config_patterns(self) -> List[str]:
        """Get JavaScript config patterns as regex strings"""
        return [pattern.pattern for pattern in self.config.path_discovery.javascript_config_patterns]
    
    def get_server_specific_paths(self, server_type: str) -> List[str]:
        """Get server-specific paths for a given server type"""
        return self.config.path_discovery.server_specific_paths.get(server_type.lower(), [])
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers configuration"""
        return self.config.security_analysis.security_headers
    
    def get_information_disclosure_headers(self) -> List[str]:
        """Get headers that may disclose information"""
        return self.config.security_analysis.information_disclosure_headers
    
    def get_error_indicators(self) -> List[str]:
        """Get error page indicators"""
        return self.config.security_analysis.content_validation.error_indicators
    
    def get_valid_content_indicators(self) -> List[str]:
        """Get valid content indicators"""
        return self.config.security_analysis.content_validation.valid_content_indicators
    
    def get_valid_status_codes(self) -> List[int]:
        """Get valid HTTP status codes"""
        return self.config.security_analysis.content_validation.valid_status_codes
    
    def get_common_subdomains(self) -> List[str]:
        """Get common subdomains for hostname generation"""
        return self.config.hostname_generation.common_subdomains