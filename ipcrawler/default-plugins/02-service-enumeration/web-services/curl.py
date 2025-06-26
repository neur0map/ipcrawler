from ipcrawler.plugins import ServiceScan

class Curl(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Curl"
		self.tags = ['default', 'safe', 'http']

	def configure(self):
		self.add_option("path", default="/", help="The path on the web server to curl. Default: %(default)s")
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)
		# Enhanced technology detection patterns
		self.add_pattern(r'(?i)powered[ -]by[:\s]*([^\n\r]+)', description='Technology Stack: Powered by {match1} - web framework/CMS identification')
		self.add_pattern(r'(?i)x-powered-by[:\s]*([^\n\r]+)', description='Technology Header: X-Powered-By {match1} - server technology disclosure')
		self.add_pattern(r'(?i)generator[:\s]*([^\n\r"]+)', description='Content Generator: {match1} - CMS/framework identification')
		self.add_pattern(r'(?i)<title>([^<]+)</title>', description='Page Title: {match1}')
		
		# === COMPREHENSIVE CMS DETECTION (HTB + Modern) ===
		
		# Traditional CMS Platforms
		self.add_pattern(r'(?i)wp-content|wp-includes|wordpress', description='WordPress CMS detected - check /wp-admin, /wp-content/uploads, plugin vulnerabilities')
		self.add_pattern(r'(?i)wp-json/wp/v2', description='WordPress REST API v2 exposed - potential user enumeration and data disclosure')
		self.add_pattern(r'(?i)joomla|/administrator/|com_content', description='Joomla CMS detected - check /administrator/, component vulnerabilities')
		self.add_pattern(r'(?i)drupal|sites/default|/user/login', description='Drupal CMS detected - check /admin/, module vulnerabilities, Drupalgeddon')
		self.add_pattern(r'(?i)typo3|fileadmin|typo3conf', description='TYPO3 CMS detected - check /typo3/, extension vulnerabilities')
		self.add_pattern(r'(?i)concrete5|/dashboard/|ccm_token', description='Concrete5 CMS detected - check dashboard access')
		self.add_pattern(r'(?i)silverstripe|/admin/|/dev/build', description='SilverStripe CMS detected - check admin panel access')
		
		# E-commerce Platforms (Common in HTB)
		self.add_pattern(r'(?i)magento|/admin/|mage/|skin/frontend', description='Magento E-commerce detected - check admin panel, connect vulnerabilities')
		self.add_pattern(r'(?i)prestashop|/admin\d+/|prestashop', description='PrestaShop E-commerce detected - check randomized admin directory')
		self.add_pattern(r'(?i)opencart|/admin/|route=common', description='OpenCart E-commerce detected - check admin panel access')
		self.add_pattern(r'(?i)woocommerce|wc-api', description='WooCommerce (WordPress) E-commerce detected - check REST API endpoints')
		self.add_pattern(r'(?i)shopify|myshopify\.com', description='Shopify E-commerce platform detected')
		self.add_pattern(r'(?i)bigcommerce', description='BigCommerce E-commerce platform detected')
		
		# Wiki and Documentation Platforms
		self.add_pattern(r'(?i)mediawiki|/wiki/|api\.php', description='MediaWiki detected - check API endpoints, user enumeration')
		self.add_pattern(r'(?i)dokuwiki|doku\.php', description='DokuWiki detected - check file upload vulnerabilities')
		self.add_pattern(r'(?i)confluence|/wiki/|atlassian', description='Atlassian Confluence detected - check for CVE-2021-26084, CVE-2022-26134')
		self.add_pattern(r'(?i)tiddlywiki', description='TiddlyWiki detected - check for data exposure')
		self.add_pattern(r'(?i)gitiles|/\+/refs', description='Gitiles (Git web interface) detected - source code exposure')
		
		# Headless/Modern CMS (API-first)
		self.add_pattern(r'(?i)strapi|/admin/auth|/api/|strapi', description='Strapi Headless CMS detected - check admin panel, API endpoints')
		self.add_pattern(r'(?i)ghost|/ghost/|ghost-api', description='Ghost CMS detected - check admin panel at /ghost/')
		self.add_pattern(r'(?i)contentful|contentful\.com', description='Contentful Headless CMS detected')
		self.add_pattern(r'(?i)sanity\.io|sanity-check', description='Sanity CMS detected')
		self.add_pattern(r'(?i)forestry\.io', description='Forestry CMS detected')
		self.add_pattern(r'(?i)netlify-cms|netlify', description='Netlify CMS detected')
		
		# Static Site Generators (Common in Modern Development)
		self.add_pattern(r'(?i)jekyll|_site/|jekyll-', description='Jekyll Static Site Generator detected')
		self.add_pattern(r'(?i)hugo|hugo-|/themes/', description='Hugo Static Site Generator detected')
		self.add_pattern(r'(?i)gatsby|gatsby-|/public/', description='Gatsby.js Static Site Generator detected')
		self.add_pattern(r'(?i)next\.js|_next/|next-', description='Next.js React Framework detected')
		self.add_pattern(r'(?i)nuxt\.js|_nuxt/|nuxt-', description='Nuxt.js Vue Framework detected')
		self.add_pattern(r'(?i)gridsome', description='Gridsome Vue.js Static Site Generator detected')
		self.add_pattern(r'(?i)hexo|hexo-', description='Hexo Static Site Generator detected')
		
		# === MODERN WEB FRAMEWORKS ===
		
		# JavaScript Frameworks (Frontend)
		self.add_pattern(r'(?i)react|react-dom|_react|__REACT', description='React.js Library detected - modern JavaScript UI framework')
		self.add_pattern(r'(?i)vue\.js|vue-|__VUE', description='Vue.js Framework detected - progressive JavaScript framework')
		self.add_pattern(r'(?i)angular|ng-|@angular', description='Angular Framework detected - Google TypeScript framework')
		self.add_pattern(r'(?i)svelte|svelte-', description='Svelte Framework detected - compile-time JavaScript framework')
		self.add_pattern(r'(?i)ember\.js|ember-', description='Ember.js Framework detected')
		self.add_pattern(r'(?i)backbone\.js|backbone-', description='Backbone.js Framework detected')
		self.add_pattern(r'(?i)alpine\.js|x-data', description='Alpine.js Framework detected - lightweight JavaScript framework')
		
		# JavaScript Backend Frameworks
		self.add_pattern(r'(?i)express\.js|express/|expressjs', description='Express.js Node.js Framework detected')
		self.add_pattern(r'(?i)fastify|fastify/', description='Fastify Node.js Framework detected - high performance web framework')
		self.add_pattern(r'(?i)koa\.js|koa/|koajs', description='Koa.js Node.js Framework detected')
		self.add_pattern(r'(?i)hapi\.js|hapi/', description='Hapi.js Node.js Framework detected')
		self.add_pattern(r'(?i)nest\.js|nestjs', description='NestJS Node.js Framework detected - enterprise Node.js framework')
		self.add_pattern(r'(?i)meteor|meteor/', description='Meteor.js Full-stack Framework detected')
		
		# PHP Frameworks (Very Common in HTB)
		self.add_pattern(r'(?i)laravel|laravel_session|/vendor/laravel', description='Laravel PHP Framework detected - check .env file, debug mode, Artisan')
		self.add_pattern(r'(?i)symphony|symfony|/bundles/', description='Symfony PHP Framework detected - check debug toolbar, profiler')
		self.add_pattern(r'(?i)codeigniter|/application/|/system/', description='CodeIgniter PHP Framework detected - check config files')
		self.add_pattern(r'(?i)cakephp|cake_|/app/webroot', description='CakePHP Framework detected - check debug mode')
		self.add_pattern(r'(?i)zend|zf_|/library/Zend', description='Zend Framework detected - check configuration files')
		self.add_pattern(r'(?i)yii|yii-|/protected/', description='Yii PHP Framework detected - check debug mode, gii module')
		self.add_pattern(r'(?i)phalcon', description='Phalcon PHP Framework detected - C-extension framework')
		self.add_pattern(r'(?i)slim/|slim-', description='Slim PHP Framework detected - microframework')
		self.add_pattern(r'(?i)lumen|lumen-', description='Lumen PHP Framework detected - Laravel microframework')
		
		# Python Frameworks (Popular in HTB)
		self.add_pattern(r'(?i)django|django-|/admin/login', description='Django Python Framework detected - check admin panel, debug mode')
		self.add_pattern(r'(?i)flask|flask-|werkzeug', description='Flask Python Framework detected - check debug mode, Werkzeug debugger')
		self.add_pattern(r'(?i)fastapi|/docs|/redoc', description='FastAPI Python Framework detected - check auto-generated docs at /docs, /redoc')
		self.add_pattern(r'(?i)tornado|tornadoweb', description='Tornado Python Framework detected')
		self.add_pattern(r'(?i)bottle\.py|bottle', description='Bottle Python Framework detected - micro web framework')
		self.add_pattern(r'(?i)pyramid|pyramid-', description='Pyramid Python Framework detected')
		self.add_pattern(r'(?i)cherrypy', description='CherryPy Python Framework detected')
		self.add_pattern(r'(?i)starlette', description='Starlette Python ASGI Framework detected')
		self.add_pattern(r'(?i)quart|quart-', description='Quart Python Async Framework detected')
		
		# Ruby Frameworks
		self.add_pattern(r'(?i)ruby.on.rails|rails/|railties', description='Ruby on Rails Framework detected - check debug mode, routes')
		self.add_pattern(r'(?i)sinatra|sinatra/', description='Sinatra Ruby Framework detected - lightweight web framework')
		self.add_pattern(r'(?i)padrino', description='Padrino Ruby Framework detected')
		self.add_pattern(r'(?i)hanami', description='Hanami Ruby Framework detected')
		
		# .NET Frameworks (Common in Windows HTB boxes)
		self.add_pattern(r'(?i)asp\.net.core|aspnetcore', description='ASP.NET Core detected - modern cross-platform .NET framework')
		self.add_pattern(r'(?i)asp\.net.mvc|mvc-', description='ASP.NET MVC Framework detected')
		self.add_pattern(r'(?i)asp\.net.web.api', description='ASP.NET Web API detected - RESTful services framework')
		self.add_pattern(r'(?i)blazor|blazor-', description='Blazor Framework detected - .NET web UI framework')
		self.add_pattern(r'(?i)umbraco|/umbraco/', description='Umbraco CMS (.NET) detected - check admin panel')
		self.add_pattern(r'(?i)orchard|orchard-', description='Orchard CMS (.NET) detected')
		self.add_pattern(r'(?i)dotnetnuke|dnn|/admin/controlpanel', description='DotNetNuke CMS detected - check admin panel')
		
		# Java Frameworks (Spring, etc.)
		self.add_pattern(r'(?i)spring.boot|spring-boot', description='Spring Boot Framework detected - check actuator endpoints')
		self.add_pattern(r'(?i)spring.mvc|spring-mvc', description='Spring MVC Framework detected')
		self.add_pattern(r'(?i)struts|struts2|/struts/', description='Apache Struts Framework detected - check for CVE-2017-5638, CVE-2018-11776')
		self.add_pattern(r'(?i)jsf|javax\.faces', description='JavaServer Faces (JSF) detected')
		self.add_pattern(r'(?i)wicket|apache.wicket', description='Apache Wicket Framework detected')
		self.add_pattern(r'(?i)vaadin', description='Vaadin Framework detected - Java web application framework')
		self.add_pattern(r'(?i)grails|grails-', description='Grails Framework detected - Groovy web framework')
		self.add_pattern(r'(?i)play.framework|play-', description='Play Framework detected - reactive web framework')
		
		# Go Frameworks
		self.add_pattern(r'(?i)gin-gonic|gin/', description='Gin Go Framework detected - HTTP web framework')
		self.add_pattern(r'(?i)echo|echo/', description='Echo Go Framework detected - high performance web framework')
		self.add_pattern(r'(?i)fiber|gofiber', description='Fiber Go Framework detected - Express.js inspired framework')
		self.add_pattern(r'(?i)beego', description='Beego Go Framework detected - MVC framework')
		self.add_pattern(r'(?i)revel|revel-', description='Revel Go Framework detected - full-stack framework')
		
		# Rust Frameworks
		self.add_pattern(r'(?i)actix|actix-web', description='Actix-web Rust Framework detected')
		self.add_pattern(r'(?i)rocket|rocket-', description='Rocket Rust Framework detected')
		self.add_pattern(r'(?i)warp|warp-', description='Warp Rust Framework detected')
		
		# === HTB/CTF SPECIFIC TECHNOLOGIES ===
		
		# Vulnerable/Practice Applications (Common in HTB)
		self.add_pattern(r'(?i)dvwa|damn.vulnerable', description='DVWA (Damn Vulnerable Web App) detected - practice application')
		self.add_pattern(r'(?i)webgoat|webgoat', description='WebGoat vulnerable application detected')
		self.add_pattern(r'(?i)mutillidae|mutillidae', description='Mutillidae vulnerable application detected')
		self.add_pattern(r'(?i)bwapp|bee-box', description='bWAPP vulnerable application detected')
		self.add_pattern(r'(?i)juice.shop|juice-shop', description='OWASP Juice Shop vulnerable application detected')
		self.add_pattern(r'(?i)vulnhub|vulnhub', description='VulnHub vulnerable application detected')
		
		# Git and Version Control Exposure (Common in HTB)
		self.add_pattern(r'(?i)\.git/|git-|/\.git/', description='CRITICAL: Git repository exposed - source code disclosure risk')
		self.add_pattern(r'(?i)\.svn/|subversion', description='CRITICAL: SVN repository exposed - source code disclosure risk')
		self.add_pattern(r'(?i)\.hg/|mercurial', description='CRITICAL: Mercurial repository exposed - source code disclosure risk')
		self.add_pattern(r'(?i)gitlab|gitlab-', description='GitLab detected - check for exposed repositories, admin access')
		self.add_pattern(r'(?i)gitea|gitea-', description='Gitea Git service detected - lightweight Git hosting')
		self.add_pattern(r'(?i)gogs|gogs-', description='Gogs Git service detected - self-hosted Git service')
		
		# Development/Debug Interfaces (HTB Gold)
		self.add_pattern(r'(?i)phpinfo\(\)|phpinfo', description='CRITICAL: PHP Info page exposed - configuration disclosure')
		self.add_pattern(r'(?i)phpmyadmin|pma/|/phpmyadmin/', description='phpMyAdmin detected - database administration interface')
		self.add_pattern(r'(?i)adminer|adminer\.php', description='Adminer database tool detected - check for SQL injection')
		self.add_pattern(r'(?i)webmin|webmin/', description='Webmin administration panel detected')
		self.add_pattern(r'(?i)cpanel|whm/', description='cPanel/WHM hosting control panel detected')
		self.add_pattern(r'(?i)plesk|plesk-', description='Plesk hosting control panel detected')
		self.add_pattern(r'(?i)directadmin', description='DirectAdmin hosting control panel detected')
		
		# Container and Orchestration (Modern Infrastructure)
		self.add_pattern(r'(?i)docker|container|/var/lib/docker', description='Docker containerization detected - check for container escape')
		self.add_pattern(r'(?i)kubernetes|k8s|/api/v1', description='Kubernetes detected - container orchestration platform')
		self.add_pattern(r'(?i)rancher|rancher/', description='Rancher Kubernetes management platform detected')
		self.add_pattern(r'(?i)portainer|portainer/', description='Portainer Docker management interface detected')
		
		# API and Microservices
		self.add_pattern(r'(?i)swagger|/swagger-ui|/api-docs', description='Swagger API documentation detected - explore API endpoints')
		self.add_pattern(r'(?i)openapi|/openapi\.json', description='OpenAPI specification detected - API documentation available')
		self.add_pattern(r'(?i)graphql|/graphql', description='GraphQL API detected - check introspection, mutations')
		self.add_pattern(r'(?i)api/v1|api/v2|/api/', description='REST API endpoints detected - check for authentication bypass')
		
		# Monitoring and Observability
		self.add_pattern(r'(?i)grafana|grafana/', description='Grafana monitoring dashboard detected - check default credentials')
		self.add_pattern(r'(?i)kibana|kibana/', description='Kibana (Elasticsearch) interface detected')
		self.add_pattern(r'(?i)prometheus|/metrics', description='Prometheus metrics endpoint detected - potential information disclosure')
		self.add_pattern(r'(?i)jaeger|jaeger-', description='Jaeger distributed tracing detected')
		self.add_pattern(r'(?i)zipkin', description='Zipkin distributed tracing detected')
		
		# Message Queues and Brokers
		self.add_pattern(r'(?i)rabbitmq|rabbit-mq', description='RabbitMQ message broker detected - check management interface')
		self.add_pattern(r'(?i)apache.kafka|kafka', description='Apache Kafka message broker detected')
		self.add_pattern(r'(?i)redis|redis-', description='Redis in-memory database detected - check for unauthorized access')
		self.add_pattern(r'(?i)memcached', description='Memcached caching system detected')
		
		# Version Detection Patterns
		self.add_pattern(r'(?i)php[/\s]*([\d\.]+)', description='PHP Version {match1} detected - check for known vulnerabilities')
		self.add_pattern(r'(?i)python[/\s]*([\d\.]+)', description='Python Version {match1} detected')
		self.add_pattern(r'(?i)node\.js[/\s]*([\d\.]+)', description='Node.js Version {match1} detected')
		self.add_pattern(r'(?i)ruby[/\s]*([\d\.]+)', description='Ruby Version {match1} detected')
		self.add_pattern(r'(?i)java[/\s]*([\d\.]+)', description='Java Version {match1} detected')
		self.add_pattern(r'(?i)apache[/\s]*([\d\.]+)', description='Apache HTTP Server Version {match1} detected')
		self.add_pattern(r'(?i)nginx[/\s]*([\d\.]+)', description='Nginx Version {match1} detected')
		
		# Authentication and Identity Management Systems
		self.add_pattern(r'(?i)dalo.*radius|daloradius', description='DaloRADIUS detected - web-based RADIUS management interface (check default admin:radius)')
		self.add_pattern(r'(?i)freeradius|free.*radius', description='FreeRADIUS server detected - authentication, authorization, and accounting')
		self.add_pattern(r'(?i)radius.*manager|radmin', description='RADIUS management interface detected - check for default credentials')
		self.add_pattern(r'(?i)ldap.*admin|phpldapadmin', description='LDAP administration interface detected - directory service management')
		self.add_pattern(r'(?i)active.*directory|msad|ad.*domain', description='Microsoft Active Directory detected - enterprise identity service')
		self.add_pattern(r'(?i)openldap|slapd', description='OpenLDAP directory service detected')
		self.add_pattern(r'(?i)kerberos|krb5|kinit', description='Kerberos authentication protocol detected')
		self.add_pattern(r'(?i)saml|shibboleth|idp', description='SAML/Shibboleth identity provider detected')
		self.add_pattern(r'(?i)cas.*server|jasig.*cas', description='CAS (Central Authentication Service) detected')
		self.add_pattern(r'(?i)keycloak|redhat.*sso', description='Keycloak identity and access management detected')
		self.add_pattern(r'(?i)okta|auth0|onelogin', description='Cloud identity provider detected (Okta/Auth0/OneLogin)')
		
		# Network Management and Monitoring (HTB Common)
		self.add_pattern(r'(?i)pfsense|pf.*sense', description='pfSense firewall detected - network security appliance')
		self.add_pattern(r'(?i)opnsense|opn.*sense', description='OPNsense firewall detected - network security platform')
		self.add_pattern(r'(?i)untangle|untangle.*ng', description='Untangle network gateway detected')
		self.add_pattern(r'(?i)smoothwall|smooth.*wall', description='SmoothWall firewall detected')
		self.add_pattern(r'(?i)ipfire|ip.*fire', description='IPFire firewall distribution detected')
		self.add_pattern(r'(?i)zentyal|zentyal.*server', description='Zentyal server detected - Linux network infrastructure')
		self.add_pattern(r'(?i)clearos|clear.*os', description='ClearOS server detected - network infrastructure platform')
		
		# Network Monitoring Tools (Common in Enterprise/HTB)
		self.add_pattern(r'(?i)nagios|nagios.*core', description='Nagios monitoring system detected - check default nagiosadmin credentials')
		self.add_pattern(r'(?i)icinga|icinga2', description='Icinga monitoring system detected - network/service monitoring')
		self.add_pattern(r'(?i)zabbix|zabbix.*server', description='Zabbix monitoring detected - check default Admin:zabbix credentials')
		self.add_pattern(r'(?i)cacti|cacti.*rrd', description='Cacti network monitoring detected - check default admin:admin credentials')
		self.add_pattern(r'(?i)observium|observium.*ce', description='Observium network monitoring detected')
		self.add_pattern(r'(?i)librenms|libre.*nms', description='LibreNMS network monitoring detected')
		self.add_pattern(r'(?i)pandora.*fms|pandorafms', description='Pandora FMS monitoring detected')
		self.add_pattern(r'(?i)monitorix|monitorix.*system', description='Monitorix system monitoring detected')
		
		# Virtualization and Hypervisor Management
		self.add_pattern(r'(?i)vmware.*vsphere|vcenter', description='VMware vSphere/vCenter detected - virtualization management')
		self.add_pattern(r'(?i)vmware.*esxi|esxi.*host', description='VMware ESXi hypervisor detected')
		self.add_pattern(r'(?i)proxmox|proxmox.*ve', description='Proxmox VE detected - virtualization management platform')
		self.add_pattern(r'(?i)citrix.*xenserver|xen.*server', description='Citrix XenServer hypervisor detected')
		self.add_pattern(r'(?i)hyper-v|hyperv.*manager', description='Microsoft Hyper-V detected - virtualization platform')
		self.add_pattern(r'(?i)ovirt|red.*hat.*virtualization', description='oVirt/RHV virtualization management detected')
		self.add_pattern(r'(?i)xcp-ng|xen.*cloud', description='XCP-ng hypervisor detected')
		
		# Storage and NAS Systems (HTB Infrastructure)
		self.add_pattern(r'(?i)freenas|truenas', description='FreeNAS/TrueNAS storage system detected - network attached storage')
		self.add_pattern(r'(?i)openmediavault|omv', description='OpenMediaVault NAS detected - storage management')
		self.add_pattern(r'(?i)rockstor|rock.*stor', description='Rockstor NAS detected - CentOS-based storage')
		self.add_pattern(r'(?i)unraid|unraid.*server', description='Unraid storage system detected')
		self.add_pattern(r'(?i)synology|dsm.*synology', description='Synology NAS detected - DiskStation Manager')
		self.add_pattern(r'(?i)qnap|qts.*qnap', description='QNAP NAS detected - QTS operating system')
		self.add_pattern(r'(?i)drobo.*dashboard|drobo.*nas', description='Drobo NAS system detected')
		
		# Backup and Archival Systems
		self.add_pattern(r'(?i)bacula|bacula.*director', description='Bacula backup system detected - enterprise backup solution')
		self.add_pattern(r'(?i)bareos|bareos.*director', description='Bareos backup system detected - Bacula fork')
		self.add_pattern(r'(?i)amanda|amanda.*backup', description='Amanda backup system detected - network backup solution')
		self.add_pattern(r'(?i)backup.*exec|symantec.*backup', description='Symantec Backup Exec detected')
		self.add_pattern(r'(?i)veeam|veeam.*backup', description='Veeam backup software detected')
		self.add_pattern(r'(?i)duplicati|duplicati.*backup', description='Duplicati backup client detected')
		
		# Cloud Platform Detection
		self.add_pattern(r'(?i)aws|amazon.web.services', description='Amazon Web Services (AWS) detected')
		self.add_pattern(r'(?i)azure|microsoft.azure', description='Microsoft Azure detected')
		self.add_pattern(r'(?i)google.cloud|gcp', description='Google Cloud Platform (GCP) detected')
		self.add_pattern(r'(?i)digitalocean', description='DigitalOcean cloud platform detected')
		self.add_pattern(r'(?i)heroku', description='Heroku platform-as-a-service detected')
		self.add_pattern(r'(?i)vercel|zeit', description='Vercel deployment platform detected')
		self.add_pattern(r'(?i)netlify', description='Netlify hosting platform detected')

	async def run(self, service):
		if service.protocol == 'tcp':
			# Get all hostnames to scan (discovered vhosts + fallback to IP)
			hostnames = service.target.get_all_hostnames()
			best_hostname = service.target.get_best_hostname()
			
			# CRITICAL: Ensure we always have hostnames - safety check
			if not hostnames:
				service.error("❌ CRITICAL: No hostnames available for curl! Using IP fallback.")
				hostnames = [service.target.ip if service.target.ip else service.target.address]
			
			service.info(f"🌐 Using hostnames for curl scan: {', '.join(hostnames)}")
			service.info(f"✅ Final hostnames for curl scan: {', '.join(hostnames)}")
			
			# Scan each hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				scan_hostname = hostname
				if ':' in hostname and not hostname.startswith('['):
					scan_hostname = f'[{hostname}]'
				
				service.info(f"🔧 Running curl against: {hostname}")
				await service.execute('curl -sSik {http_scheme}://' + scan_hostname + ':{port}' + self.get_option('path'), outfile='{protocol}_{port}_{http_scheme}_curl_' + hostname_label + '.html')
