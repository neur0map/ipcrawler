"""
Technology detection for HTTP scanner workflow.

This module handles database-driven technology detection with fuzzy matching,
fallback pattern matching, and technology-specific path discovery.
"""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from .models import HTTPService
from .config import get_scanner_config
from utils.debug import debug_print


class TechnologyDetector:
    """Technology detection handler with database integration"""
    
    def __init__(self):
        self.config = get_scanner_config()
    
    async def detect_technologies(self, service: HTTPService) -> List[str]:
        """
        Detect technologies using database-driven detection with fuzzy matching.
        
        Args:
            service: HTTPService object to analyze
            
        Returns:
            List of detected technology names
        """
        technologies = []
        
        # Use technology database if available
        if self.config.technology_matcher:
            try:
                # Get detection results with fuzzy matching
                detection_results = self.config.technology_matcher.detect_technologies(
                    response_body=service.response_body or "",
                    headers=service.headers,
                    url_path=urlparse(service.url).path,
                    fuzzy_threshold=80
                )
                
                # Extract technology names from results
                for result in detection_results:
                    technologies.append(result.name)
                    debug_print(f"Detected {result.name} (confidence: {result.confidence:.2f})")
                    
                    # Add discovery paths to service for further testing
                    if result.discovery_paths:
                        service.discovered_paths.extend(result.discovery_paths)
                
                # Return early if database detection found technologies
                if technologies:
                    return list(set(technologies))
                    
            except Exception as e:
                debug_print(f"Technology database detection error: {e}", level="WARNING")
        
        # Fallback to hardcoded patterns if database is unavailable
        fallback_technologies = self._detect_technologies_fallback(service)
        technologies.extend(fallback_technologies)
        
        return list(set(technologies))
    
    def _detect_technologies_fallback(self, service: HTTPService) -> List[str]:
        """
        Fallback technology detection using hardcoded patterns.
        
        Args:
            service: HTTPService object to analyze
            
        Returns:
            List of detected technologies
        """
        technologies = []
        
        # From headers
        tech_headers = {
            'x-powered-by': lambda v: v,
            'server': lambda v: v.split('/')[0] if '/' in v else v,
            'x-generator': lambda v: v
        }
        
        for header, parser in tech_headers.items():
            value = service.headers.get(header, '')
            if value:
                tech = parser(value)
                if tech:
                    technologies.append(tech)
                    debug_print(f"Technology detected from header {header}: {tech}")
        
        # From response body patterns (simplified fallback)
        if service.response_body:
            body_patterns = {
                'WordPress': r'wp-content|wp-includes',
                'Django': r'csrfmiddlewaretoken',
                'Grafana': r'grafana|Grafana|grafana\\.js|grafana-app',
                'Prometheus': r'prometheus|Prometheus|/metrics',
                'Monitoring Dashboard': r'dashboard|Dashboard|monitoring|Monitoring',
                'Apache': r'Apache|apache',
                'Nginx': r'nginx|Nginx',
                'IIS': r'IIS|Microsoft-IIS',
                'Tomcat': r'tomcat|Tomcat',
                'JBoss': r'jboss|JBoss',
                'WebLogic': r'weblogic|WebLogic',
                'Spring': r'spring|Spring',
                'Struts': r'struts|Struts',
                'React': r'react|React',
                'Angular': r'angular|Angular|ng-',
                'Vue.js': r'vue|Vue|v-',
                'jQuery': r'jquery|jQuery',
                'Bootstrap': r'bootstrap|Bootstrap',
                'Node.js': r'node|Node\\.js',
                'Express': r'express|Express',
                'PHP': r'php|PHP',
                'ASP.NET': r'asp\\.net|ASP\\.NET|__doPostBack',
                'JSF': r'jsf|JSF|javax\\.faces',
                'Wicket': r'wicket|Wicket',
                'Rails': r'rails|Rails|ruby',
                'Laravel': r'laravel|Laravel',
                'Symfony': r'symfony|Symfony',
                'CodeIgniter': r'codeigniter|CodeIgniter',
                'CakePHP': r'cakephp|CakePHP',
                'Drupal': r'drupal|Drupal',
                'Joomla': r'joomla|Joomla',
                'Magento': r'magento|Magento',
                'PrestaShop': r'prestashop|PrestaShop',
                'Shopify': r'shopify|Shopify',
                'WooCommerce': r'woocommerce|WooCommerce',
                'MediaWiki': r'mediawiki|MediaWiki',
                'phpMyAdmin': r'phpmyadmin|phpMyAdmin',
                'Adminer': r'adminer|Adminer',
                'Jenkins': r'jenkins|Jenkins',
                'GitLab': r'gitlab|GitLab',
                'GitHub': r'github|GitHub',
                'Bitbucket': r'bitbucket|Bitbucket',
                'Confluence': r'confluence|Confluence',
                'JIRA': r'jira|JIRA',
                'Bamboo': r'bamboo|Bamboo',
                'TeamCity': r'teamcity|TeamCity',
                'SonarQube': r'sonarqube|SonarQube',
                'Nexus': r'nexus|Nexus',
                'Artifactory': r'artifactory|Artifactory',
                'Docker': r'docker|Docker',
                'Kubernetes': r'kubernetes|Kubernetes|k8s',
                'OpenShift': r'openshift|OpenShift',
                'Rancher': r'rancher|Rancher',
                'Portainer': r'portainer|Portainer',
                'Traefik': r'traefik|Traefik',
                'HAProxy': r'haproxy|HAProxy',
                'Caddy': r'caddy|Caddy',
                'Lighttpd': r'lighttpd|Lighttpd',
                'Cherokee': r'cherokee|Cherokee',
                'Varnish': r'varnish|Varnish',
                'Squid': r'squid|Squid',
                'Redis': r'redis|Redis',
                'Memcached': r'memcached|Memcached',
                'MongoDB': r'mongodb|MongoDB',
                'PostgreSQL': r'postgresql|PostgreSQL',
                'MySQL': r'mysql|MySQL',
                'MariaDB': r'mariadb|MariaDB',
                'Oracle': r'oracle|Oracle',
                'SQL Server': r'sql\\s*server|SQL\\s*Server',
                'SQLite': r'sqlite|SQLite',
                'Elasticsearch': r'elasticsearch|Elasticsearch',
                'Solr': r'solr|Solr',
                'Lucene': r'lucene|Lucene',
                'Kibana': r'kibana|Kibana',
                'Logstash': r'logstash|Logstash',
                'Beats': r'beats|Beats',
                'Fluentd': r'fluentd|Fluentd',
                'Graylog': r'graylog|Graylog',
                'Splunk': r'splunk|Splunk',
                'Nagios': r'nagios|Nagios',
                'Zabbix': r'zabbix|Zabbix',
                'Icinga': r'icinga|Icinga',
                'Sensu': r'sensu|Sensu',
                'Datadog': r'datadog|Datadog',
                'New Relic': r'newrelic|New\\s*Relic',
                'Dynatrace': r'dynatrace|Dynatrace',
                'AppDynamics': r'appdynamics|AppDynamics',
                'Pingdom': r'pingdom|Pingdom'
            }
            
            for tech, pattern in body_patterns.items():
                if re.search(pattern, service.response_body, re.IGNORECASE):
                    technologies.append(tech)
                    debug_print(f"Technology detected from body pattern: {tech}")
        
        return technologies
    
    async def run_tech_detection_on_paths(self, service: HTTPService, paths: List[str]) -> None:
        """
        Run technology detection on discovered paths to catch technologies not in homepage.
        
        Args:
            service: HTTPService object
            paths: List of discovered paths to analyze
        """
        if not self.config.technology_matcher or not paths:
            return
        
        if not self.config.deps_available:
            debug_print("HTTP dependencies not available for path-based tech detection")
            return
        
        try:
            import httpx
            
            debug_print(f"Running technology detection on {len(paths)} discovered paths")
            
            # Limit to most promising paths for performance
            concurrency = self.config.get_concurrency_limits()
            max_paths_to_check = 5
            interesting_paths = self._prioritize_tech_paths(paths, max_paths_to_check)
            
            timeout_settings = self.config.get_timeout_settings()
            async with httpx.AsyncClient(
                verify=False, 
                timeout=httpx.Timeout(connect=timeout_settings['connect'], read=timeout_settings['read'])
            ) as client:
                
                for path in interesting_paths:
                    try:
                        # Get full content for this path
                        from urllib.parse import urljoin
                        path_url = urljoin(service.url, path)
                        response = await client.get(
                            path_url, 
                            headers={"User-Agent": self.config.get_user_agents()[0]}
                        )
                        
                        if response.status_code in [200, 201, 202]:
                            # Run technology detection on this path's content
                            path_detection_results = self.config.technology_matcher.detect_technologies(
                                response_body=response.text[:10000],  # First 10KB
                                headers=dict(response.headers),
                                url_path=urlparse(path_url).path,
                                fuzzy_threshold=80
                            )
                            
                            # Add any new technologies found
                            existing_techs = set(service.technologies)
                            new_techs = []
                            
                            for result in path_detection_results:
                                if result.name not in existing_techs:
                                    new_techs.append(result.name)
                                    service.technologies.append(result.name)
                                    debug_print(f"Found {result.name} on path {path} (confidence: {result.confidence:.2f})")
                                    
                                    # Add discovery paths from this newly detected tech
                                    if result.discovery_paths:
                                        service.discovered_paths.extend(result.discovery_paths)
                            
                            if new_techs:
                                debug_print(f"Path {path} revealed new technologies: {new_techs}")
                        
                    except Exception as e:
                        debug_print(f"Error running tech detection on path {path}: {e}", level="WARNING")
                        continue
                        
        except Exception as e:
            debug_print(f"Error in path-based technology detection: {e}", level="WARNING")
    
    def _prioritize_tech_paths(self, paths: List[str], max_paths: int) -> List[str]:
        """
        Prioritize paths that are more likely to contain technology indicators.
        
        Args:
            paths: List of paths to prioritize
            max_paths: Maximum number of paths to return
            
        Returns:
            Prioritized list of paths
        """
        # Priority patterns for technology detection
        tech_priority_patterns = [
            'admin', 'grafana', 'dashboard', 'api', 'login', 'console',
            'management', 'monitoring', 'prometheus', 'kibana', 'jenkins',
            'wordpress', 'wp-admin', 'wp-content', 'drupal', 'joomla',
            'phpmyadmin', 'mysql', 'postgresql', 'redis', 'elasticsearch',
            'solr', 'mongo', 'django', 'flask', 'rails', 'laravel',
            'symfony', 'codeigniter', 'cakephp', 'zend', 'yii',
            'spring', 'struts', 'hibernate', 'tomcat', 'wildfly',
            'websphere', 'weblogic', 'nginx', 'apache', 'iis',
            'lighttpd', 'caddy', 'haproxy', 'traefik', 'envoy',
            'docker', 'kubernetes', 'rancher', 'portainer', 'swarm',
            'minio', 's3', 'vault', 'consul', 'etcd', 'zookeeper',
            'kafka', 'rabbitmq', 'activemq', 'celery', 'sidekiq',
            'swagger', 'openapi', 'graphql', 'rest', 'soap',
            'oauth', 'saml', 'ldap', 'kerberos', 'jwt',
            'splunk', 'elastic', 'logstash', 'fluentd', 'graylog',
            'nagios', 'zabbix', 'icinga', 'sensu', 'datadog',
            'newrelic', 'dynatrace', 'appdynamics', 'pingdom'
        ]
        
        # Sort paths by likely tech content
        prioritized_paths = []
        regular_paths = []
        
        for path in paths[:max_paths * 2]:  # Check more for prioritization
            path_lower = path.lower()
            if any(pattern in path_lower for pattern in tech_priority_patterns):
                prioritized_paths.append(path)
            else:
                regular_paths.append(path)
        
        # Take top priority paths plus some regular ones
        return (prioritized_paths + regular_paths)[:max_paths]
    
    def get_technology_specific_paths(self, service: HTTPService) -> List[str]:
        """
        Get technology-specific paths based on detected server and technologies.
        
        Args:
            service: HTTPService object
            
        Returns:
            List of technology-specific paths
        """
        tech_paths = []
        
        # Get paths from database if available
        if self.config.scanner_config_manager and service.server:
            try:
                server_lower = service.server.lower()
                for server_type in ['apache', 'nginx', 'tomcat', 'iis', 'jetty']:
                    if server_type in server_lower:
                        server_paths = self.config.scanner_config_manager.get_server_specific_paths(server_type)
                        tech_paths.extend(server_paths)
                        debug_print(f"Added {len(server_paths)} {server_type}-specific paths")
                        break
            except Exception as e:
                debug_print(f"Error getting server-specific paths: {e}", level="WARNING")
        
        # Fallback server-specific paths if database unavailable
        if not tech_paths and service.server:
            server_lower = service.server.lower()
            if 'apache' in server_lower:
                tech_paths.extend(['/server-status', '/server-info'])
            elif 'nginx' in server_lower:
                tech_paths.extend(['/nginx_status'])
            elif 'tomcat' in server_lower:
                tech_paths.extend(['/manager/', '/host-manager/'])
            elif 'iis' in server_lower:
                tech_paths.extend(['/iisstart.htm', '/welcome.png'])
            elif 'jetty' in server_lower:
                tech_paths.extend(['/test/', '/async-rest/'])
        
        # Add monitoring-specific paths based on content analysis
        monitoring_paths = self._get_monitoring_specific_paths(service)
        tech_paths.extend(monitoring_paths)
        
        return tech_paths
    
    def _get_monitoring_specific_paths(self, service: HTTPService) -> List[str]:
        """
        Get monitoring-specific paths based on response content analysis.
        
        Args:
            service: HTTPService object
            
        Returns:
            List of monitoring-specific paths
        """
        monitoring_paths = []
        
        if not service.response_body:
            return monitoring_paths
        
        response_lower = service.response_body.lower()
        
        # Grafana-specific paths
        if any(indicator in response_lower for indicator in ['grafana', '/grafana', 'grafana.js', 'grafana-app']):
            monitoring_paths.extend([
                '/grafana/', '/grafana/api/health', '/grafana/login',
                '/grafana/api/dashboards', '/grafana/api/datasources',
                '/api/health', '/api/dashboards', '/api/datasources'
            ])
            debug_print("Detected Grafana indicators, adding Grafana-specific paths")
        
        # Generic monitoring dashboard paths
        if any(indicator in response_lower for indicator in ['dashboard', 'monitoring', 'metrics', 'telemetry']):
            monitoring_paths.extend([
                '/metrics', '/health', '/status', '/api/health',
                '/monitoring/', '/dashboard/', '/admin/monitoring',
                '/api/v1/query', '/prometheus/', '/kibana/'
            ])
            debug_print("Detected monitoring indicators, adding dashboard paths")
        
        # Prometheus-specific paths
        if any(indicator in response_lower for indicator in ['prometheus', '/metrics', 'prom_']):
            monitoring_paths.extend([
                '/metrics', '/api/v1/query', '/api/v1/label',
                '/prometheus/', '/prometheus/api/v1/query'
            ])
            debug_print("Detected Prometheus indicators, adding Prometheus paths")
        
        return monitoring_paths