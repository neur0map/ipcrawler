from ipcrawler.plugins import ServiceScan

class WhatWeb(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "whatweb"
		self.description = "Web application and technology identification"
		self.tags = ['default', 'safe', 'http']

	def configure(self):
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)

	async def run(self, service):
		if service.protocol == 'tcp' and service.target.ipversion == 'IPv4':
			# Get all hostnames to scan (discovered vhosts + fallback to IP)
			hostnames = service.target.get_all_hostnames()
			
			# CRITICAL: Ensure we always have hostnames - safety check
			if not hostnames:
				service.error("❌ CRITICAL: No hostnames available for whatweb! Using IP fallback.")
				hostnames = [service.target.ip if service.target.ip else service.target.address]
			
			service.info(f"🌐 Using hostnames for whatweb scan: {', '.join(hostnames)}")
			service.info(f"✅ Final hostnames for whatweb scan: {', '.join(hostnames)}")
			
			# Scan each hostname
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				service.info(f"🔧 Running whatweb against: {hostname}")
				await service.execute('whatweb --color=never --no-errors -a 3 -v {http_scheme}://' + hostname + ':{port} 2>&1', outfile='{protocol}_{port}_{http_scheme}_whatweb_' + hostname_label + '.txt')
