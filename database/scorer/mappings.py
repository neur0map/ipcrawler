"""
Hardcoded mappings and rule hierarchies for wordlist scoring.
"""

from typing import Dict, List, Tuple, Any
import re


# Level 1: Exact tech + port combinations
EXACT_MATCH_RULES: Dict[Tuple[str, int], List[str]] = {
    # Web Applications
    ("wordpress", 443): ["wordpress-https.txt", "wp-plugins.txt", "wp-themes.txt"],
    ("wordpress", 80): ["wordpress.txt", "wp-plugins.txt", "wp-themes.txt"],
    ("drupal", 443): ["drupal-https.txt", "drupal-modules.txt"],
    ("drupal", 80): ["drupal.txt", "drupal-modules.txt"],
    ("joomla", 443): ["joomla-https.txt", "joomla-components.txt"],
    ("joomla", 80): ["joomla.txt", "joomla-components.txt"],
    
    # Application Servers
    ("tomcat", 8080): ["tomcat-manager.txt", "java-servlets.txt", "tomcat-examples.txt"],
    ("tomcat", 8443): ["tomcat-manager-https.txt", "java-servlets.txt"],
    ("jetty", 8080): ["jetty-paths.txt", "java-servlets.txt"],
    ("glassfish", 4848): ["glassfish-admin.txt", "java-ee.txt"],
    ("wildfly", 8080): ["wildfly-paths.txt", "jboss-paths.txt"],
    ("weblogic", 7001): ["weblogic-paths.txt", "oracle-paths.txt"],
    
    # Web Servers
    ("apache", 80): ["apache-common.txt", "apache-manual.txt", "apache-config.txt"],
    ("apache", 443): ["apache-https.txt", "apache-manual.txt"],
    ("nginx", 80): ["nginx-common.txt", "nginx-config.txt"],
    ("nginx", 443): ["nginx-https.txt", "nginx-config.txt"],
    ("iis", 80): ["iis-common.txt", "aspnet-paths.txt", "iis-shortnames.txt"],
    ("iis", 443): ["iis-https.txt", "aspnet-paths.txt"],
    
    # Databases
    ("mysql", 3306): ["mysql-admin.txt", "phpmyadmin.txt"],
    ("postgresql", 5432): ["postgresql-admin.txt", "pgadmin.txt"],
    ("mongodb", 27017): ["mongodb-admin.txt", "mongo-express.txt"],
    ("redis", 6379): ["redis-commands.txt"],
    ("mssql", 1433): ["mssql-admin.txt", "sql-injection.txt"],
    
    # Admin Panels
    ("phpmyadmin", 80): ["phpmyadmin-paths.txt", "mysql-admin.txt"],
    ("phpmyadmin", 443): ["phpmyadmin-https.txt", "mysql-admin.txt"],
    ("adminer", 80): ["adminer-paths.txt", "database-admin.txt"],
    ("webmin", 10000): ["webmin-paths.txt", "linux-admin.txt"],
    
    # Development Tools
    ("jenkins", 8080): ["jenkins-paths.txt", "ci-cd-paths.txt"],
    ("jenkins", 8443): ["jenkins-https.txt", "ci-cd-paths.txt"],
    ("gitlab", 80): ["gitlab-paths.txt", "git-paths.txt"],
    ("gitlab", 443): ["gitlab-https.txt", "git-paths.txt"],
    ("grafana", 3000): ["grafana-paths.txt", "monitoring-paths.txt"],
    
    # Protocols & Services
    ("ssh", 22): ["ssh-users.txt", "ssh-keys.txt"],
    ("ftp", 21): ["ftp-common.txt", "ftp-dirs.txt"],
    ("smb", 445): ["smb-shares.txt", "windows-shares.txt"],
    ("rdp", 3389): ["rdp-users.txt", "windows-users.txt"],
}


# Level 2: Technology categories with fallback patterns
TECH_CATEGORY_RULES: Dict[str, Dict[str, Any]] = {
    "cms": {
        "matches": ["wordpress", "drupal", "joomla", "typo3", "magento", "prestashop", 
                   "opencart", "shopify", "wix", "squarespace", "ghost", "strapi"],
        "wordlists": ["cms-common.txt", "cms-plugins.txt", "cms-themes.txt"],
        "fallback_pattern": r"(cms|content\s*management|blog|e-commerce|shop)",
        "weight": 0.8
    },
    
    "web_server": {
        "matches": ["apache", "nginx", "iis", "lighttpd", "caddy", "gunicorn", 
                   "tomcat", "jetty", "express", "kestrel", "httpd"],
        "wordlists": ["common-web.txt", "web-dirs.txt", "web-files.txt"],
        "fallback_pattern": r"(http|web\s*server|www|nginx|apache)",
        "weight": 0.8
    },
    
    "app_server": {
        "matches": ["tomcat", "jetty", "glassfish", "wildfly", "jboss", "weblogic",
                   "websphere", "resin", "geronimo"],
        "wordlists": ["java-apps.txt", "servlets.txt", "java-dirs.txt"],
        "fallback_pattern": r"(java|servlet|jsp|j2ee|jakarta)",
        "weight": 0.8
    },
    
    "database": {
        "matches": ["mysql", "mariadb", "postgresql", "postgres", "mongodb", "redis",
                   "cassandra", "couchdb", "elasticsearch", "mssql", "oracle", "db2"],
        "wordlists": ["database-admin.txt", "db-paths.txt", "sql-common.txt"],
        "fallback_pattern": r"(database|mysql|postgres|mongo|redis|sql)",
        "weight": 0.8
    },
    
    "framework": {
        "matches": ["django", "flask", "rails", "laravel", "symfony", "express",
                   "spring", "struts", "asp.net", "vue", "react", "angular"],
        "wordlists": ["framework-common.txt", "api-endpoints.txt"],
        "fallback_pattern": r"(framework|django|flask|rails|laravel|mvc)",
        "weight": 0.7
    },
    
    "admin_panel": {
        "matches": ["phpmyadmin", "adminer", "webmin", "cpanel", "plesk", "directadmin",
                   "ispconfig", "virtualmin", "cockpit", "ajenti"],
        "wordlists": ["admin-panels.txt", "control-panels.txt", "admin-dirs.txt"],
        "fallback_pattern": r"(admin|panel|control|management|dashboard)",
        "weight": 0.8
    },
    
    "mail_server": {
        "matches": ["postfix", "exim", "sendmail", "exchange", "zimbra", "dovecot",
                   "roundcube", "squirrelmail", "horde"],
        "wordlists": ["mail-common.txt", "webmail.txt", "mail-dirs.txt"],
        "fallback_pattern": r"(mail|smtp|imap|pop3|webmail|exchange)",
        "weight": 0.7
    },
    
    "proxy_lb": {
        "matches": ["haproxy", "varnish", "squid", "traefik", "envoy", "kong"],
        "wordlists": ["proxy-paths.txt", "cache-paths.txt"],
        "fallback_pattern": r"(proxy|cache|load\s*balancer|reverse)",
        "weight": 0.6
    },
    
    "monitoring": {
        "matches": ["nagios", "zabbix", "prometheus", "grafana", "kibana", "splunk",
                   "datadog", "newrelic", "elastic"],
        "wordlists": ["monitoring-paths.txt", "metrics-endpoints.txt"],
        "fallback_pattern": r"(monitor|metric|logging|observability)",
        "weight": 0.7
    },
    
    "ci_cd": {
        "matches": ["jenkins", "gitlab", "github", "bitbucket", "bamboo", "teamcity",
                   "circleci", "travis", "drone", "argocd"],
        "wordlists": ["ci-cd-paths.txt", "git-paths.txt", "pipeline-paths.txt"],
        "fallback_pattern": r"(jenkins|gitlab|ci\/cd|pipeline|build)",
        "weight": 0.7
    },
    
    "container": {
        "matches": ["docker", "kubernetes", "openshift", "rancher", "portainer",
                   "swarm", "mesos", "nomad"],
        "wordlists": ["container-paths.txt", "kubernetes-paths.txt", "docker-registry.txt"],
        "fallback_pattern": r"(docker|kubernetes|k8s|container|registry)",
        "weight": 0.7
    }
}


# Level 3: Port-based categories
PORT_CATEGORY_RULES: Dict[str, Dict[str, Any]] = {
    "web": {
        "ports": [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000, 4200, 3001],
        "wordlists": ["common.txt", "dirs.txt", "web-content.txt"],
        "weight": 0.6
    },
    
    "web_secure": {
        "ports": [443, 8443, 9443, 4443],
        "wordlists": ["common-https.txt", "dirs-https.txt", "ssl-paths.txt"],
        "weight": 0.6
    },
    
    "database": {
        "ports": [3306, 5432, 1433, 27017, 6379, 5984, 9200, 7474, 8529],
        "wordlists": ["database-common.txt", "db-admin.txt"],
        "weight": 0.6
    },
    
    "admin": {
        "ports": [8080, 9090, 10000, 8834, 7001, 4848, 8161, 9990],
        "wordlists": ["admin-panels.txt", "management-paths.txt"],
        "weight": 0.6
    },
    
    "mail": {
        "ports": [25, 465, 587, 110, 995, 143, 993, 2525],
        "wordlists": ["mail-common.txt", "smtp-commands.txt"],
        "weight": 0.5
    },
    
    "file_transfer": {
        "ports": [21, 22, 873, 445, 139, 2049, 111],
        "wordlists": ["file-transfer.txt", "shares.txt", "ftp-common.txt"],
        "weight": 0.5
    },
    
    "remote_access": {
        "ports": [22, 23, 3389, 5900, 5901, 1194, 4444],
        "wordlists": ["remote-access.txt", "ssh-common.txt", "rdp-common.txt"],
        "weight": 0.5
    },
    
    "proxy": {
        "ports": [3128, 8118, 8123, 1080, 9050],
        "wordlists": ["proxy-paths.txt", "proxy-admin.txt"],
        "weight": 0.5
    },
    
    "development": {
        "ports": [3000, 4200, 5000, 8000, 9000, 3001, 5001, 8001],
        "wordlists": ["dev-paths.txt", "api-endpoints.txt", "debug-paths.txt"],
        "weight": 0.5
    }
}


# Level 4: Generic fallback wordlists
GENERIC_FALLBACK: List[str] = [
    "common.txt",
    "discovery.txt", 
    "dirs.txt",
    "files.txt"
]


# Service keyword mappings for additional context
SERVICE_KEYWORD_RULES: Dict[str, List[str]] = {
    "admin": ["admin-panels.txt", "admin-dirs.txt"],
    "api": ["api-endpoints.txt", "rest-api.txt", "graphql.txt"],
    "login": ["login-pages.txt", "auth-endpoints.txt"],
    "upload": ["upload-forms.txt", "file-upload.txt"],
    "backup": ["backup-files.txt", "backup-dirs.txt"],
    "test": ["test-files.txt", "debug-paths.txt"],
    "dev": ["dev-paths.txt", "development.txt"],
    "staging": ["staging-paths.txt", "test-environments.txt"],
    "mobile": ["mobile-api.txt", "app-endpoints.txt"],
    "ajax": ["ajax-endpoints.txt", "xhr-paths.txt"],
    "websocket": ["websocket-endpoints.txt", "ws-paths.txt"],
    "graphql": ["graphql-endpoints.txt", "graphql-introspection.txt"],
    "rest": ["rest-api.txt", "api-v1.txt", "api-v2.txt"],
    "soap": ["soap-endpoints.txt", "wsdl-files.txt"],
    "xml": ["xml-endpoints.txt", "xml-files.txt"],
    "json": ["json-endpoints.txt", "json-files.txt"]
}


# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "high": 0.8,
    "medium": 0.6,
    "low": 0.0
}


def get_exact_match(tech: str, port: int) -> List[str]:
    """Get wordlists for exact tech+port match."""
    key = (tech.lower() if tech else "", port)
    return EXACT_MATCH_RULES.get(key, [])