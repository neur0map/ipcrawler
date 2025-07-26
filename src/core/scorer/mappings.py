"""
"""



# Level 1: Exact tech + port combinations
EXACT_MATCH_RULES: Dict[Tuple[str, int], List[str]] = {
    # Web Applications (with shared bridge wordlists)
    ("wordpress", 443): ["wordpress-https.txt", "wp-plugins.txt", "wp-themes.txt", "cms-common.txt", "common.txt"],
    ("wordpress", 80): ["wordpress.txt", "wp-plugins.txt", "wp-themes.txt", "cms-common.txt", "common.txt"],
    ("drupal", 443): ["drupal-https.txt", "drupal-modules.txt", "cms-common.txt", "common.txt"],
    ("drupal", 80): ["drupal.txt", "drupal-modules.txt", "cms-common.txt", "common.txt"],
    ("joomla", 443): ["joomla-https.txt", "joomla-components.txt", "cms-common.txt", "common.txt"],
    ("joomla", 80): ["joomla.txt", "joomla-components.txt", "cms-common.txt", "common.txt"],
    
    # Application Servers (with shared bridge wordlists)
    ("tomcat", 8080): ["tomcat-manager.txt", "java-servlets.txt", "tomcat-examples.txt", "java-apps.txt", "common.txt"],
    ("tomcat", 8443): ["tomcat-manager-https.txt", "java-servlets.txt", "java-apps.txt", "common.txt"],
    ("jetty", 8080): ["jetty-paths.txt", "java-servlets.txt", "java-apps.txt", "common.txt"],
    ("glassfish", 4848): ["glassfish-admin.txt", "java-ee.txt", "java-apps.txt", "admin-panels.txt"],
    ("wildfly", 8080): ["wildfly-paths.txt", "jboss-paths.txt", "java-apps.txt", "common.txt"],
    ("weblogic", 7001): ["weblogic-paths.txt", "oracle-paths.txt", "java-apps.txt", "admin-panels.txt"],
    
    # Web Servers (with shared bridge wordlists)
    ("apache", 80): ["apache-common.txt", "apache-manual.txt", "apache-config.txt", "common-web.txt", "common.txt"],
    ("apache", 443): ["apache-https.txt", "apache-manual.txt", "common-web.txt", "common.txt"],
    ("nginx", 80): ["nginx-common.txt", "nginx-config.txt", "common-web.txt", "common.txt"],
    ("nginx", 443): ["nginx-https.txt", "nginx-config.txt", "common-web.txt", "common.txt"],
    ("iis", 80): ["iis-common.txt", "aspnet-paths.txt", "iis-shortnames.txt", "common-web.txt", "common.txt"],
    ("iis", 443): ["iis-https.txt", "aspnet-paths.txt", "common-web.txt", "common.txt"],
    
    # Databases (with shared bridge wordlists)
    ("mysql", 3306): ["mysql-admin.txt", "phpmyadmin.txt", "database-admin.txt", "db-paths.txt"],
    ("postgresql", 5432): ["postgresql-admin.txt", "pgadmin.txt", "database-admin.txt", "db-paths.txt"],
    ("mongodb", 27017): ["mongodb-admin.txt", "mongo-express.txt", "database-admin.txt", "db-paths.txt"],
    ("redis", 6379): ["redis-commands.txt", "database-admin.txt"],
    ("mssql", 1433): ["mssql-admin.txt", "sql-injection.txt", "database-admin.txt", "db-paths.txt"],
    
    # Admin Panels (with shared bridge wordlists)
    ("phpmyadmin", 80): ["phpmyadmin-paths.txt", "mysql-admin.txt", "admin-panels.txt", "database-admin.txt"],
    ("phpmyadmin", 443): ["phpmyadmin-https.txt", "mysql-admin.txt", "admin-panels.txt", "database-admin.txt"],
    ("adminer", 80): ["adminer-paths.txt", "database-admin.txt", "admin-panels.txt"],
    ("webmin", 10000): ["webmin-paths.txt", "linux-admin.txt", "admin-panels.txt"],
    
    # Development Tools (with shared bridge wordlists)
    ("jenkins", 8080): ["jenkins-paths.txt", "ci-cd-paths.txt", "common.txt"],
    ("jenkins", 8443): ["jenkins-https.txt", "ci-cd-paths.txt", "common.txt"],
    ("gitlab", 80): ["gitlab-paths.txt", "git-paths.txt", "ci-cd-paths.txt", "common.txt"],
    ("gitlab", 443): ["gitlab-https.txt", "git-paths.txt", "ci-cd-paths.txt", "common.txt"],
    ("grafana", 3000): ["grafana-paths.txt", "monitoring-paths.txt", "common.txt"],
    
    # Protocols & Services
    ("ssh", 22): ["ssh-users.txt", "ssh-keys.txt"],
    ("ftp", 21): ["ftp-common.txt", "ftp-dirs.txt"],
    ("smb", 445): ["smb-shares.txt", "windows-shares.txt"],
    ("rdp", 3389): ["rdp-users.txt", "windows-users.txt"],
    
    # Missing technologies identified by audit
    ("php", 80): ["php-common.txt", "php-paths.txt", "php-files.txt"],
    ("php", 443): ["php-common.txt", "php-paths.txt", "php-files.txt"],
    ("express", 3000): ["express-routes.txt", "nodejs-paths.txt", "api-endpoints.txt"],
    ("express", 8000): ["express-routes.txt", "nodejs-paths.txt", "api-endpoints.txt"],
    ("caddy", 80): ["caddy-paths.txt", "caddy-config.txt", "web-dirs.txt"],
    ("caddy", 443): ["caddy-paths.txt", "caddy-config.txt", "web-dirs.txt"],
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
                   "tomcat", "jetty", "express", "kestrel", "httpd", "php", "proxy"],
        "wordlists": ["common-web.txt", "web-dirs.txt", "web-files.txt", "common.txt", "express-routes.txt", "nodejs-paths.txt", "php-common.txt", "proxy-paths.txt"],
        "fallback_pattern": r"(http|web\s*server|www|nginx|apache|php|proxy)",
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
                   "cassandra", "couchdb", "elasticsearch", "mssql", "oracle", "db2", "server"],
        "wordlists": ["database-admin.txt", "db-paths.txt", "sql-common.txt", "server-info.txt"],
        "fallback_pattern": r"(database|mysql|postgres|mongo|redis|sql|server)",
        "weight": 0.8
    },
    
    "framework": {
        "matches": ["django", "flask", "rails", "laravel", "symfony", "express",
                   "spring", "struts", "asp.net", "vue", "react", "angular", "php"],
        "wordlists": ["framework-common.txt", "api-endpoints.txt", "php-common.txt"],
        "fallback_pattern": r"(framework|django|flask|rails|laravel|mvc|php)",
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
        "matches": ["haproxy", "varnish", "squid", "traefik", "envoy", "kong", "http/1.1"],
        "wordlists": ["proxy-paths.txt", "cache-paths.txt", "common.txt"],
        "fallback_pattern": r"(proxy|cache|load\s*balancer|reverse|http)",
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
    },
    
    "scripting": {
        "matches": ["php", "python", "ruby", "perl", "nodejs", "node", "express"],
        "wordlists": ["scripting-common.txt", "php-paths.txt", "nodejs-paths.txt", "php-common.txt", "express-routes.txt"],
        "fallback_pattern": r"(php|python|ruby|perl|node|express|script)",
        "weight": 0.7
    },
    
    "reverse_proxy": {
        "matches": ["caddy", "cloudflare", "fastly", "akamai", "aws"],
        "wordlists": ["proxy-paths.txt", "cdn-paths.txt", "reverse-proxy.txt", "web-dirs.txt", "common.txt", "caddy-paths.txt"],
        "fallback_pattern": r"(caddy|cloudflare|proxy|cdn|reverse)",
        "weight": 0.6
    },
    
    "generic_server": {
        "matches": ["server", "http/1.1", "http/1.0", "http/2", "https", "proxy"],
        "wordlists": ["common.txt", "dirs.txt", "server-info.txt"],
        "fallback_pattern": r"(server|http|https|web|proxy)",
        "weight": 0.4
    }
}


# Level 3: Port-based categories with hierarchical priority
PORT_CATEGORY_RULES: Dict[str, Dict[str, Any]] = {
    # Web categories - merged and optimized to eliminate conflicts
    "web_standard": {
        "ports": [80, 8888],
        "wordlists": ["common.txt", "dirs.txt", "web-content.txt", "phpmyadmin-paths.txt", "adminer-paths.txt", "php-common.txt", "caddy-paths.txt", "caddy-config.txt"],
        "weight": 0.6,
        "priority": 1
    },
    
    "web_secure": {
        "ports": [443, 8443, 9443, 4443],
        "wordlists": ["common.txt", "dirs.txt", "web-content.txt", "common-https.txt", "dirs-https.txt", "ssl-paths.txt", "phpmyadmin-https.txt", "php-common.txt", "caddy-paths.txt", "caddy-config.txt"],
        "weight": 0.7,
        "priority": 1
    },
    
    "web_admin": {
        "ports": [8080, 9090, 10000, 8834, 7001, 4848, 8161, 9990],
        "wordlists": ["common.txt", "dirs.txt", "web-content.txt", "admin-panels.txt", "management-paths.txt"],
        "weight": 0.7,
        "priority": 1
    },
    
    "web_development": {
        "ports": [3000, 4200, 5000, 8000, 9000, 3001, 5001, 8001],
        "wordlists": ["common.txt", "dirs.txt", "web-content.txt", "dev-paths.txt", "api-endpoints.txt", "debug-paths.txt"],
        "weight": 0.7,
        "priority": 1
    },
    
    # Database category
    "database": {
        "ports": [3306, 5432, 1433, 27017, 6379, 5984, 9200, 7474, 8529],
        "wordlists": ["database-common.txt", "db-admin.txt", "database-admin.txt", "db-paths.txt"],
        "weight": 0.6,
        "priority": 2
    },
    
    # Mail category
    "mail": {
        "ports": [25, 465, 587, 110, 995, 143, 993, 2525],
        "wordlists": ["mail-common.txt", "smtp-commands.txt"],
        "weight": 0.5,
        "priority": 3
    },
    
    # Remote access (SSH gets priority over file transfer for port 22)
    "remote_access": {
        "ports": [22, 23, 3389, 5900, 5901, 1194, 4444],
        "wordlists": ["remote-access.txt", "ssh-common.txt", "rdp-common.txt", "ssh-users.txt", "ssh-keys.txt", "rdp-users.txt", "windows-users.txt"],
        "weight": 0.6,
        "priority": 2
    },
    
    # File transfer (excludes port 22 to avoid conflict)
    "file_transfer": {
        "ports": [21, 873, 445, 139, 2049, 111],
        "wordlists": ["file-transfer.txt", "shares.txt", "ftp-common.txt", "smb-shares.txt", "windows-shares.txt"],
        "weight": 0.5,
        "priority": 3
    },
    
    # Proxy category
    "proxy": {
        "ports": [3128, 8118, 8123, 1080, 9050],
        "wordlists": ["proxy-paths.txt", "proxy-admin.txt"],
        "weight": 0.5,
        "priority": 3
    },
    
    # DNS category (new - fixes missing port 53)
    "dns": {
        "ports": [53, 853, 5353],
        "wordlists": ["dns-common.txt", "dns-records.txt"],
        "weight": 0.5,
        "priority": 3
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
    # Core service patterns
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
    "json": ["json-endpoints.txt", "json-files.txt"],
    
    # Extended service patterns for better coverage
    "auth": ["auth-endpoints.txt", "oauth-paths.txt", "saml-paths.txt"],
    "authentication": ["auth-endpoints.txt", "login-pages.txt"],
    "authorization": ["auth-endpoints.txt", "rbac-paths.txt"],
    "config": ["config-files.txt", "settings-paths.txt"],
    "configuration": ["config-files.txt", "admin-config.txt"],
    "dashboard": ["dashboard-paths.txt", "admin-panels.txt"],
    "monitoring": ["monitoring-paths.txt", "metrics-endpoints.txt"],
    "health": ["health-check.txt", "status-endpoints.txt"],
    "status": ["status-endpoints.txt", "health-check.txt"],
    "metrics": ["metrics-endpoints.txt", "prometheus-paths.txt"],
    "logs": ["log-files.txt", "logging-paths.txt"],
    "logging": ["log-files.txt", "admin-logs.txt"],
    "cache": ["cache-endpoints.txt", "redis-paths.txt"],
    "session": ["session-paths.txt", "auth-endpoints.txt"],
    "cookie": ["session-paths.txt", "auth-endpoints.txt"],
    "security": ["security-paths.txt", "auth-endpoints.txt"],
    "ssl": ["ssl-paths.txt", "tls-endpoints.txt"],
    "tls": ["ssl-paths.txt", "tls-endpoints.txt"],
    "cert": ["ssl-paths.txt", "certificate-paths.txt"],
    "certificate": ["ssl-paths.txt", "certificate-paths.txt"],
    "static": ["static-files.txt", "assets-paths.txt"],
    "assets": ["static-files.txt", "assets-paths.txt"],
    "media": ["media-files.txt", "uploads-paths.txt"],
    "images": ["media-files.txt", "image-paths.txt"],
    "css": ["static-files.txt", "css-paths.txt"],
    "js": ["static-files.txt", "javascript-paths.txt"],
    "javascript": ["static-files.txt", "javascript-paths.txt"],
    "font": ["static-files.txt", "font-paths.txt"],
    "download": ["download-paths.txt", "file-paths.txt"],
    "redirect": ["redirect-paths.txt", "url-paths.txt"],
    "proxy": ["proxy-paths.txt", "forward-paths.txt"],
    "forward": ["proxy-paths.txt", "forward-paths.txt"]
}


# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "high": 0.8,
    "medium": 0.6,
    "low": 0.0
}


# Diversification pools - alternative wordlists for entropy improvement
WORDLIST_ALTERNATIVES: Dict[str, List[str]] = {
    # Common web wordlists - swap when overused
    "common.txt": [
        "discovery.txt",
        "quick.txt", 
        "medium.txt",
        "small.txt"
    ],
    
    "dirs.txt": [
        "directory-list-2.3-medium.txt",
        "directory-list-lowercase-2.3-medium.txt",
        "big.txt",
        "common-directories.txt"
    ],
    
    "files.txt": [
        "common-files.txt",
        "quickhits.txt",
        "big-files.txt",
        "sensitive-files.txt"
    ],
    
    # Admin panel alternatives
    "admin-panels.txt": [
        "admin-interfaces.txt",
        "management-consoles.txt",
        "control-panels.txt",
        "admin-dirs.txt"
    ],
    
    "admin-dirs.txt": [
        "admin-directories.txt",
        "admin-paths.txt",
        "management-dirs.txt",
        "control-dirs.txt"
    ],
    
    # Database alternatives
    "database-admin.txt": [
        "db-admin-tools.txt",
        "database-interfaces.txt",
        "sql-admin.txt",
        "db-management.txt"
    ],
    
    "db-paths.txt": [
        "database-paths.txt",
        "sql-paths.txt",
        "db-directories.txt",
        "database-dirs.txt"
    ],
    
    # API alternatives
    "api-endpoints.txt": [
        "rest-api.txt",
        "api-v1.txt",
        "api-methods.txt",
        "graphql.txt"
    ],
    
    "rest-api.txt": [
        "api-endpoints.txt",
        "restful-paths.txt",
        "api-resources.txt",
        "web-api.txt"
    ],
    
    # CMS alternatives
    "cms-common.txt": [
        "cms-paths.txt",
        "content-management.txt",
        "blog-paths.txt",
        "cms-admin.txt"
    ],
    
    "wordpress.txt": [
        "wp-directories.txt",
        "wp-common.txt",
        "wordpress-paths.txt",
        "wp-content.txt"
    ],
    
    # Development alternatives
    "dev-paths.txt": [
        "development.txt",
        "dev-directories.txt",
        "staging-paths.txt",
        "test-paths.txt"
    ],
    
    "debug-paths.txt": [
        "debug-files.txt",
        "debug-dirs.txt",
        "test-files.txt",
        "development-files.txt"
    ],
    
    # Technology-specific alternatives
    "java-apps.txt": [
        "java-servlets.txt",
        "jsp-pages.txt",
        "java-paths.txt",
        "tomcat-paths.txt"
    ],
    
    "php-paths.txt": [
        "php-files.txt",
        "php-common.txt",
        "php-applications.txt",
        "php-dirs.txt"
    ],
    
    # Monitoring alternatives
    "monitoring-paths.txt": [
        "metrics-endpoints.txt",
        "monitoring-dirs.txt",
        "observability-paths.txt",
        "health-checks.txt"
    ],
    
    # Generic fallback alternatives
    "discovery.txt": [
        "common.txt",
        "quick.txt",
        "basic.txt",
        "essential.txt"
    ]
}


    """Get wordlists for exact tech+port match."""
    key = (tech.lower() if tech else "", port)


    """Get alternative wordlists for diversification."""


    """Check if a wordlist has alternatives available."""


    """Get set of all wordlists that have alternatives."""
