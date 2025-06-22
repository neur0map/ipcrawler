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

	async def run(self, service):
		if service.target.ipversion == 'IPv4':
			# Get all hostnames to scan (discovered vhosts + fallback to IP)
			hostnames = service.target.get_all_hostnames()
			best_hostname = service.target.get_best_hostname()
			
			# Debug output only with --debug flag
			if config.get('debug', False):
				service.info(f"🐛 DEBUG: Target discovered_hostnames = {service.target.discovered_hostnames}")
				service.info(f"🐛 DEBUG: All hostnames = {hostnames}")
			
			service.info(f"🌐 Using hostnames for nikto scan: {', '.join(hostnames)}")
			if len(hostnames) > 1:
				service.info(f"🎯 Primary hostname: {best_hostname}")
			
			# Scan each hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				await service.execute('nikto -ask=no -Tuning=x4567890ac -nointeractive -host {http_scheme}://' + hostname + ':{port} 2>&1 | tee "{scandir}/{protocol}_{port}_{http_scheme}_nikto_' + hostname_label + '.txt"')

	def manual(self, service, plugin_was_run):
		if service.target.ipversion == 'IPv4' and not plugin_was_run:
			# Get all hostnames for manual commands
			hostnames = service.target.get_all_hostnames()
			
			# Add manual commands for each discovered hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				hostname_desc = f" ({hostname})" if hostname != service.target.ip else " (IP fallback)"
				service.add_manual_command(f'(nikto) Web server enumeration tool{hostname_desc}:', 'nikto -ask=no -h {http_scheme}://' + hostname + ':{port} 2>&1 | tee "{scandir}/{protocol}_{port}_{http_scheme}_nikto_' + hostname_label + '.txt"')
