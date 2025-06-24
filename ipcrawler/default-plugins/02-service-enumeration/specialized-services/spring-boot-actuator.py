from ipcrawler.plugins import ServiceScan
from shutil import which

class SpringBootActuator(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Spring Boot Actuator"
		self.slug = 'spring-boot-actuator'
		self.description = "Enumerates Spring Boot applications and actuator endpoints"
		self.priority = 0
		self.tags = ['default', 'safe', 'web', 'java']

	def configure(self):
		self.add_option('threads', default=10, help='Number of threads for endpoint enumeration. Default: %(default)s')
		self.add_option('timeout', default=10, help='Request timeout in seconds. Default: %(default)s')
		self.add_list_option('common-paths', default=[
			'/', '/actuator', '/actuator/health', '/actuator/info', '/actuator/env',
			'/actuator/beans', '/actuator/configprops', '/actuator/dump', '/actuator/trace',
			'/actuator/mappings', '/actuator/metrics', '/actuator/shutdown', '/actuator/jolokia',
			'/manage', '/management', '/monitoring', '/admin', '/api', '/api/v1', '/api/v2',
			'/health', '/info', '/status', '/version', '/env', '/beans', '/metrics'
		], help='Common Spring Boot and management endpoints to check. Default: %(default)s')
		
		# Match unknown services on common Spring Boot ports
		self.match_service_name('^unknown$')
		# Also match HTTP services that might be Spring Boot
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)
		
		# Add patterns to help identify Spring Boot applications
		self.add_pattern('spring-boot-detected', r'(?i)(spring.boot|whitelabel.error|org\.springframework)')
		self.add_pattern('eureka-detected', r'(?i)(eureka|netflix|service.registry)')
		self.add_pattern('actuator-detected', r'(?i)(/actuator|management.endpoints)')
		self.add_pattern('spring-auth', r'(?i)(spring.security|JSESSIONID)')
		self.add_pattern('java-app', r'(?i)(tomcat|jetty|undertow|java\.version)')

	def check(self):
		if which('curl') is None:
			self.error('The curl program could not be found. Make sure it is installed.')
			return False
		return True

	async def run(self, service):
		if service.protocol == 'tcp':
			# Get all hostnames to scan (discovered vhosts + fallback to IP)
			hostnames = service.target.get_all_hostnames()
			
			# Safety check for hostnames
			if not hostnames:
				service.error("❌ No hostnames available! Using IP fallback.")
				hostnames = [service.target.ip if service.target.ip else service.target.address]
			
			service.info(f"🌐 Scanning Spring Boot endpoints on: {', '.join(hostnames)}")
			
			# Scan each hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				service.info(f"🔧 Checking Spring Boot endpoints on: {hostname}")
				
				# Test basic connectivity and get server info
				service.info(f"📋 Getting basic server information...")
				timeout = self.get_option("timeout")
				process, stdout, stderr = await service.execute(
					f'echo "=== Basic HTTP Headers ===" && '
					f'curl -v -I -m {timeout} {{http_scheme}}://{hostname}:{{port}}/ 2>&1 && '
					f'echo "=== Response Body Sample ===" && '
					f'curl -v -m {timeout} {{http_scheme}}://{hostname}:{{port}}/ 2>&1 | head -20',
					outfile=f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_headers_{hostname_label}.txt'
				)
				
				# Analyze response to identify the service
				response_text = stdout + stderr
				if 'WWW-Authenticate: Basic' in response_text:
					service.info("🔐 HTTP Basic Authentication detected")
				
				# Try to identify the service type from headers and content
				if any(keyword in response_text.lower() for keyword in ['spring', 'boot', 'actuator']):
					service.info("🌱 Spring Boot application detected!")
					# Update service name for better reporting
					service.name = 'Spring Boot'
				elif any(keyword in response_text.lower() for keyword in ['eureka', 'netflix']):
					service.info("🎯 Netflix Eureka service discovery detected!")
					service.name = 'Netflix Eureka'
				elif any(keyword in response_text.lower() for keyword in ['tomcat', 'jetty', 'undertow']):
					service.info("☕ Java web application detected!")
					service.name = 'Java Web App'
				elif 'JSESSIONID' in response_text:
					service.info("☕ Java session-based application detected!")
					service.name = 'Java Web App'
				
				# Check for Spring Boot actuator endpoints
				service.info(f"🔍 Enumerating Spring Boot actuator endpoints...")
				common_paths = self.get_option('common-paths')
				if not common_paths:
					common_paths = ['/actuator', '/health', '/info']
				
				# Create a list of URLs to check
				url_file = f'{{scandir}}/{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_urls_{hostname_label}.txt'
				urls = [f'{{http_scheme}}://{hostname}:{{port}}{path}' for path in common_paths]
				
				# Write URLs to file for reference
				url_list = ' '.join([f'"{url}"' for url in urls])
				await service.execute(
					f'printf "%s\\n" {url_list} > {url_file}',
					outfile=None
				)
				
				# Use curl to check each endpoint efficiently
				timeout = self.get_option("timeout")
				process, stdout, stderr = await service.execute(
					f'while read -r url; do '
					f'echo "=== Checking: $url ==="; '
					f'curl -v -m {timeout} "$url" -H "User-Agent: Mozilla/5.0 (compatible; IPCrawler)" 2>&1 || echo "Connection failed"; '
					f'echo ""; '
					f'done < {url_file}',
					outfile=f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_endpoints_{hostname_label}.txt'
				)
				
				# Check endpoint responses for additional service identification
				endpoint_response = stdout + stderr
				if '/actuator' in endpoint_response and '200' in endpoint_response:
					service.info("🎯 Spring Boot Actuator endpoints found!")
				if 'eureka' in endpoint_response.lower() and '200' in endpoint_response:
					service.info("🎯 Eureka service registry endpoints detected!")
				if any(endpoint in endpoint_response for endpoint in ['/health', '/info', '/metrics']) and '200' in endpoint_response:
					service.info("📊 Management endpoints available!")
				
				# Check for common Spring Boot error pages and info disclosure
				service.info(f"🚨 Checking for information disclosure...")
				timeout = self.get_option("timeout")
				await service.execute(
					f'echo "=== Testing /error endpoint ===" && '
					f'curl -v -m {timeout} {{http_scheme}}://{hostname}:{{port}}/error '
					f'-H "User-Agent: Mozilla/5.0 (compatible; IPCrawler)" 2>&1',
					outfile=f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_error_{hostname_label}.txt'
				)
				
				# Try common authentication bypass techniques
				service.info(f"🔐 Testing authentication bypass techniques...")
				await service.execute(
					f'echo "=== Testing admin:admin ===" && '
					f'curl -v -s -m {timeout} -u admin:admin {{http_scheme}}://{hostname}:{{port}}/ 2>&1 && '
					f'printf "\\n=== Testing default:default ===\\n" && '
					f'curl -v -s -m {timeout} -u default:default {{http_scheme}}://{hostname}:{{port}}/ 2>&1 && '
					f'printf "\\n=== Testing empty credentials ===\\n" && '
					f'curl -v -s -m {timeout} -u : {{http_scheme}}://{hostname}:{{port}}/ 2>&1',
					outfile=f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_auth_test_{hostname_label}.txt'
				)
				
				service.info(f"✅ Spring Boot enumeration completed for {hostname}")

	def manual(self, service, plugin_was_run):
		# Get all hostnames to scan
		hostnames = service.target.get_all_hostnames()
		if not hostnames:
			hostnames = [service.target.ip if service.target.ip else service.target.address]
		
		for hostname in hostnames:
			hostname_label = hostname.replace('.', '_').replace(':', '_')
			hostname_desc = f" ({hostname})" if hostname != service.target.ip else " (IP fallback)"
			
			service.add_manual_command(f'Spring Boot Actuator enumeration{hostname_desc}:', [
				f'# Basic connectivity test',
				f'curl -s -I {{http_scheme}}://{hostname}:{{port}}/',
				f'',
				f'# Check actuator endpoints',
				f'for endpoint in /actuator /actuator/health /actuator/info /actuator/env /actuator/beans; do',
				f'  echo "=== $endpoint ===";',
				f'  curl -s {{http_scheme}}://{hostname}:{{port}}$endpoint;',
				f'  echo "";',
				f'done',
				f'',
				f'# Test common credentials',
				f'curl -s -u admin:admin {{http_scheme}}://{hostname}:{{port}}/',
				f'curl -s -u admin:password {{http_scheme}}://{hostname}:{{port}}/',
				f'',
				f'# Check for management interfaces',
				f'curl -s {{http_scheme}}://{hostname}:{{port}}/manage',
				f'curl -s {{http_scheme}}://{hostname}:{{port}}/admin'
			])