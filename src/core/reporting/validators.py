"""Workflow output validators for IPCrawler"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class WorkflowOutputValidator:
    """Validates workflow output data structures"""
    
    WORKFLOW_SCHEMAS = {
        'nmap_fast_01': {
            'required': ['tool', 'target', 'open_ports'],
            'optional': ['hostname_mappings', 'etc_hosts_updated', 'scan_mode']
        },
        'nmap_02': {
            'required': ['hosts'],
            'optional': ['scan_type', 'scan_mode', 'duration', 'warnings']
        },
        'http_03': {
            'required': ['services'],
            'optional': ['vulnerabilities', 'subdomains', 'dns_records', 'summary']
        },
        'mini_spider_04': {
            'required': ['discovered_urls'],
            'optional': ['interesting_findings', 'categorized_results', 'enhanced_analysis', 'summary']
        },
        'smartlist_05': {
            'required': ['wordlist_recommendations'],
            'optional': ['total_services_analyzed', 'summary', 'services']
        }
    }
    
    @classmethod
    def validate_workflow_output(cls, workflow_name: str, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate workflow output data
        
        Args:
            workflow_name: Name of the workflow
            data: Output data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if workflow_name not in cls.WORKFLOW_SCHEMAS:
            logger.warning(f"No schema defined for workflow: {workflow_name}")
            return True, []  # Pass validation if no schema defined
        
        schema = cls.WORKFLOW_SCHEMAS[workflow_name]
        
        # Check required fields
        for field in schema.get('required', []):
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate specific field types
        if workflow_name == 'mini_spider_04':
            cls._validate_spider_output(data, errors)
        elif workflow_name == 'nmap_02':
            cls._validate_nmap_output(data, errors)
        elif workflow_name == 'http_03':
            cls._validate_http_output(data, errors)
        elif workflow_name == 'smartlist_05':
            cls._validate_smartlist_output(data, errors)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _validate_spider_output(data: Dict[str, Any], errors: List[str]) -> None:
        """Validate mini spider specific output"""
        if 'discovered_urls' in data:
            urls = data['discovered_urls']
            if not isinstance(urls, list):
                errors.append("discovered_urls must be a list")
            else:
                # Check URL structure
                for i, url_data in enumerate(urls[:5]):  # Check first 5
                    if isinstance(url_data, dict):
                        if 'url' not in url_data:
                            errors.append(f"discovered_urls[{i}] missing 'url' field")
                    elif not isinstance(url_data, str):
                        errors.append(f"discovered_urls[{i}] must be dict with 'url' field or string")
        
        if 'categorized_results' in data:
            if not isinstance(data['categorized_results'], dict):
                errors.append("categorized_results must be a dictionary")
    
    @staticmethod
    def _validate_nmap_output(data: Dict[str, Any], errors: List[str]) -> None:
        """Validate nmap specific output"""
        if 'hosts' in data:
            hosts = data['hosts']
            if not isinstance(hosts, list):
                errors.append("hosts must be a list")
            else:
                for i, host in enumerate(hosts[:5]):  # Check first 5
                    if not isinstance(host, dict):
                        errors.append(f"hosts[{i}] must be a dictionary")
                    elif 'ip' not in host:
                        errors.append(f"hosts[{i}] missing 'ip' field")
    
    @staticmethod
    def _validate_http_output(data: Dict[str, Any], errors: List[str]) -> None:
        """Validate HTTP scanner output"""
        if 'services' in data:
            services = data['services']
            if not isinstance(services, list):
                errors.append("services must be a list")
            else:
                for i, service in enumerate(services[:5]):  # Check first 5
                    if not isinstance(service, dict):
                        errors.append(f"services[{i}] must be a dictionary")
                    elif 'port' not in service:
                        errors.append(f"services[{i}] missing 'port' field")
    
    @staticmethod
    def _validate_smartlist_output(data: Dict[str, Any], errors: List[str]) -> None:
        """Validate SmartList output"""
        if 'wordlist_recommendations' in data:
            recs = data['wordlist_recommendations']
            if not isinstance(recs, list):
                errors.append("wordlist_recommendations must be a list")


def validate_all_workflows(workflow_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate all workflow outputs in the combined data
    
    Args:
        workflow_data: Combined workflow data
        
    Returns:
        Dictionary mapping workflow names to list of validation errors
    """
    all_errors = {}
    
    for workflow_name, data in workflow_data.items():
        if isinstance(data, dict) and data:  # Skip None or empty data
            is_valid, errors = WorkflowOutputValidator.validate_workflow_output(workflow_name, data)
            if not is_valid:
                all_errors[workflow_name] = errors
                logger.warning(f"Validation errors for {workflow_name}: {errors}")
    
    return all_errors