from ipcrawler.plugins import ServiceScan
from shutil import which

class WhatWeb(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "whatweb"
		self.description = "Web application and technology identification"
		self.tags = ['default', 'safe', 'http']

	def configure(self):
		self.add_choice_option('aggression', default='1', choices=['1', '2', '3', '4'], help='WhatWeb aggression level (1=passive, 4=aggressive). Default: %(default)s')
		self.add_true_option('ignore-errors', help='Continue scanning even if HTTP errors occur')
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)

	def check(self):
		if which('whatweb') is None:
			self.error('The whatweb program could not be found. Make sure it is installed. (On Kali, try: sudo apt install whatweb)')
			return False
		return True

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
			
			# Scan each hostname with better error handling
			for hostname in hostnames:
				hostname_label = hostname.replace('.', '_').replace(':', '_')
				service.info(f"🔧 Running whatweb against: {hostname}")
				
				# Build whatweb command with resilient defaults
				aggression = self.get_option('aggression')
				
				# Use safer command by default - remove --no-errors to allow more lenient scanning
				# Level 1 is passive and much more reliable
				process, stdout, stderr = await service.execute(
					f'whatweb --color=never -a {aggression} -v {{http_scheme}}://' + hostname + ':{port} 2>&1', 
					outfile='{protocol}_{port}_{http_scheme}_whatweb_' + hostname_label + '.txt'
				)
				
				# Check if whatweb failed and provide helpful info
				if process.returncode != 0:
					service.warn(f"⚠️ whatweb returned exit code {process.returncode} for {hostname}")
					
					# Try a simpler whatweb command as fallback
					if process.returncode == 22:  # HTTP error
						service.info(f"🔄 Trying simpler whatweb scan for {hostname} (HTTP error fallback)")
						try:
							await service.execute(
								'whatweb --color=never --no-errors -a 1 {http_scheme}://' + hostname + ':{port} 2>&1', 
								outfile='{protocol}_{port}_{http_scheme}_whatweb_' + hostname_label + '_simple.txt'
							)
						except Exception:
							service.info(f"💡 whatweb fallback also failed for {hostname}")
					
					# Also try a basic curl to see what the actual HTTP response is
					service.info(f"🔍 Checking HTTP response for {hostname} to debug whatweb issue")
					await service.execute(
						'curl -s -I {http_scheme}://' + hostname + ':{port}/ 2>&1', 
						outfile='{protocol}_{port}_{http_scheme}_curl_headers_' + hostname_label + '.txt'
					)
				else:
					service.info(f"✅ whatweb completed successfully for {hostname}")
