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
		self.add_pattern('(?i)powered[ -]by[^\n]+')

	async def run(self, service):
		if service.protocol == 'tcp':
			# Get all hostnames to scan (discovered vhosts + fallback to IP)
			hostnames = service.target.get_all_hostnames()
			best_hostname = service.target.get_best_hostname()
			
			service.info(f"🌐 Using hostnames for curl scan: {', '.join(hostnames)}")
			
			# Scan each hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				scan_hostname = hostname
				if ':' in hostname and not hostname.startswith('['):
					scan_hostname = f'[{hostname}]'
				
				await service.execute('curl -sSik {http_scheme}://' + scan_hostname + ':{port}' + self.get_option('path'), outfile='{protocol}_{port}_{http_scheme}_curl_' + hostname_label + '.html')
