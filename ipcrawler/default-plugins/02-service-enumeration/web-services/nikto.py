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

	async def run(self, service):
		if service.target.ipversion == 'IPv4':
			# Get all hostnames to scan (discovered vhosts + fallback to IP)
			hostnames = service.target.get_all_hostnames()
			best_hostname = service.target.get_best_hostname()
			
			# CRITICAL: Ensure we always have hostnames - safety check
			if not hostnames:
				service.error("❌ CRITICAL: No hostnames available for nikto! Using IP fallback.")
				hostnames = [service.target.ip if service.target.ip else service.target.address]
			if not best_hostname:
				service.error("❌ CRITICAL: No best hostname available for nikto! Using IP fallback.")
				best_hostname = service.target.ip if service.target.ip else service.target.address
			
			# Show hostname debug info
			service.info(f"🔍 Target discovered_hostnames = {service.target.discovered_hostnames}")
			service.info(f"🔍 All hostnames = {hostnames}")
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
			hostnames = service.target.get_all_hostnames()
			
			# CRITICAL: Ensure we always have hostnames for manual commands
			if not hostnames:
				hostnames = [service.target.ip if service.target.ip else service.target.address]
			
			# Add manual commands for each discovered hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				hostname_desc = f" ({hostname})" if hostname != service.target.ip else " (IP fallback)"
				service.add_manual_command(f'(nikto) Web server enumeration tool{hostname_desc}:', 'nikto -ask=no -nointeractive -h {http_scheme}://' + hostname + ':{port} 2>&1 | tee "{scandir}/{protocol}_{port}_{http_scheme}_nikto_' + hostname_label + '.txt"')
