from ipcrawler.plugins import ServiceScan

class WPScan(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'WPScan'
		self.tags = ['default', 'safe', 'http']

	def configure(self):
		self.add_option('api-token', help='An API Token from wpvulndb.com to help search for more vulnerabilities.')
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)

	def manual(self, service, plugin_was_run):
		api_token = ''
		if self.get_option('api-token'):
			api_token = ' --api-token ' + self.get_option('api-token')

		# Get all hostnames for manual commands (includes discovered hostnames + IP fallback)
		hostnames = service.target.get_all_hostnames()
		
		# CRITICAL: Ensure we always have hostnames for manual commands
		if not hostnames:
			hostnames = [service.target.ip if service.target.ip else service.target.address]
		
		# Add manual commands for each discovered hostname
		for hostname in hostnames:
			hostname_label = hostname.replace('.', '_').replace(':', '_')
			hostname_desc = f" ({hostname})" if hostname != service.target.ip else " (IP fallback)"
			scan_hostname = hostname
			if ':' in hostname and not hostname.startswith('['):
				scan_hostname = f'[{hostname}]'
			
			service.add_manual_command(f'(wpscan) WordPress Security Scanner{hostname_desc}:', 'wpscan --url {http_scheme}://' + scan_hostname + ':{port}/ --no-update -e vp,vt,tt,cb,dbe,u,m --plugins-detection aggressive --plugins-version-detection aggressive -f cli-no-color' + api_token + ' 2>&1 | tee "{scandir}/{protocol}_{port}_{http_scheme}_wpscan_' + hostname_label + '.txt"')
