from ipcrawler.plugins import ServiceScan
from ipcrawler.config import config

class Nikto(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'nikto'
		self.description = "Web server vulnerability scanner for common security issues"
		self.tags = ['default', 'safe', 'long', 'http']

	def configure(self):
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)
		self.add_option('timeout', default=1800, help='Maximum time in seconds for nikto scan. Default: %(default)s (30 minutes)')
		# Pattern matching for Nikto findings
		self.add_pattern(r'(?i)osvdb-[0-9]+', description='OSVDB vulnerability identified: {match0}')
		self.add_pattern(r'(?i)server.*banner[:\s]*([^\n\r]+)', description='Server Banner: {match1}')
		self.add_pattern(r'(?i)vulnerable.*to[:\s]*([^\n\r]+)', description='CRITICAL: Vulnerability detected: {match1}')
		self.add_pattern(r'(?i)default.*file.*found[:\s]*([^\n\r]+)', description='Default file found: {match1}')
		self.add_pattern(r'(?i)directory.*indexing.*enabled', description='CRITICAL: Directory indexing enabled - information disclosure')
		self.add_pattern(r'(?i)backup.*file.*found[:\s]*([^\n\r]+)', description='Backup file found: {match1}')
		self.add_pattern(r'(?i)cgi.*script.*found[:\s]*([^\n\r]+)', description='CGI script found: {match1}')

	def _validate_hostname(self, hostname):
		"""Validate and sanitize hostname for nikto scanning"""
		if not hostname:
			return None

		# Remove any whitespace
		hostname = hostname.strip()

		# Check for valid hostname format (basic validation)
		import re

		# Reject obviously malformed hostnames that look like concatenated strings
		suspicious_patterns = [
			r'\.html?$',           # Ends with .html or .htm (likely concatenated)
			r'\.php$',             # Ends with .php (likely concatenated)
			r'\.js$',              # Ends with .js (likely concatenated)
			r'\.css$',             # Ends with .css (likely concatenated)
			r'home$',              # Ends with 'home' (likely concatenated)
			r'index$',             # Ends with 'index' (likely concatenated)
			r'admin$',             # Ends with 'admin' (likely concatenated)
			r'login$',             # Ends with 'login' (likely concatenated)
		]

		for pattern in suspicious_patterns:
			if re.search(pattern, hostname, re.IGNORECASE):
				return None

		# Allow IP addresses and valid hostnames
		if re.match(r'^[a-zA-Z0-9.-]+$', hostname) and len(hostname) > 0:
			# Ensure no double dots or invalid characters
			if '..' not in hostname and not hostname.startswith('.') and not hostname.endswith('.'):
				# Additional check: hostname should not be too long (max 253 chars per RFC)
				if len(hostname) <= 253:
					return hostname

		return None

	async def run(self, service):
		if service.target.ipversion == 'IPv4':
			# Get all hostnames to scan (discovered vhosts + fallback to IP)
			raw_hostnames = service.target.get_all_hostnames()
			best_hostname = service.target.get_best_hostname()

			# Validate and sanitize all hostnames
			hostnames = []
			for hostname in raw_hostnames:
				validated = self._validate_hostname(hostname)
				if validated:
					hostnames.append(validated)
				else:
					service.warn(f"⚠️ Invalid hostname detected and skipped: '{hostname}'")

			# CRITICAL: Ensure we always have hostnames - safety check
			if not hostnames:
				service.error("❌ CRITICAL: No valid hostnames available for nikto! Using IP fallback.")
				fallback_ip = service.target.ip if service.target.ip else service.target.address
				validated_fallback = self._validate_hostname(fallback_ip)
				if validated_fallback:
					hostnames = [validated_fallback]
				else:
					service.error(f"❌ CRITICAL: Even IP fallback is invalid: '{fallback_ip}'. Skipping nikto scan.")
					return

			# Validate best hostname
			if best_hostname:
				best_hostname = self._validate_hostname(best_hostname)
			if not best_hostname and hostnames:
				best_hostname = hostnames[0]

			# Show hostname debug info
			service.info(f"🔍 Target discovered_hostnames = {service.target.discovered_hostnames}")
			service.info(f"🔍 Raw hostnames = {raw_hostnames}")
			service.info(f"🔍 Validated hostnames = {hostnames}")
			service.info(f"🌐 Using hostnames for nikto scan: {', '.join(hostnames)}")
			if len(hostnames) > 1:
				service.info(f"🎯 Primary hostname: {best_hostname}")

			service.info(f"✅ Final hostnames for nikto scan: {', '.join(hostnames)}")

			# Scan each hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				service.info(f"🔧 Running nikto against: {hostname}")
				# Use more reliable nikto options - remove aggressive tuning options that might cause issues
				await service.execute('timeout ' + str(self.get_option('timeout')) + ' nikto -ask=no -nointeractive -host {http_scheme}://' + hostname + ':{port}', outfile='{protocol}_{port}_{http_scheme}_nikto_' + hostname_label + '.txt')

	def manual(self, service, plugin_was_run):
		if service.target.ipversion == 'IPv4' and not plugin_was_run:
			# Get all hostnames for manual commands
			raw_hostnames = service.target.get_all_hostnames()

			# Validate and sanitize all hostnames
			hostnames = []
			for hostname in raw_hostnames:
				validated = self._validate_hostname(hostname)
				if validated:
					hostnames.append(validated)

			# CRITICAL: Ensure we always have hostnames for manual commands
			if not hostnames:
				fallback_ip = service.target.ip if service.target.ip else service.target.address
				validated_fallback = self._validate_hostname(fallback_ip)
				if validated_fallback:
					hostnames = [validated_fallback]

			# Add manual commands for each discovered hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				hostname_desc = f" ({hostname})" if hostname != service.target.ip else " (IP fallback)"
				service.add_manual_command(f'(nikto) Web server enumeration tool{hostname_desc}:', 'nikto -ask=no -nointeractive -h {http_scheme}://' + hostname + ':{port} 2>&1 | tee "{scandir}/{protocol}_{port}_{http_scheme}_nikto_' + hostname_label + '.txt"')
