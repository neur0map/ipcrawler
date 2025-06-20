from ipcrawler.plugins import PortScan
from ipcrawler.config import config
import re, requests

class AllTCPPortScan(PortScan):

	def __init__(self):
		super().__init__()
		self.name = 'All TCP Ports'
		self.description = 'Performs an optimized Nmap scan of all TCP ports with rate limiting.'
		self.type = 'tcp'
		self.specific_ports = True
		self.tags = ['default', 'default-port-scan', 'long']

	async def run(self, target):
		# Optimized settings for full port scanning
		timing_opts = ' --max-rate=1000 --min-rate=100'
		
		if config['proxychains']:
			# Lighter scan for proxychains (slower connections)
			service_opts = ' -sV'
			timing_opts = ' --max-rate=300 --min-rate=50'
		else:
			# Balanced service detection (removed --version-all for performance)
			service_opts = ' -sV -sC'

		if target.ports:
			if target.ports['tcp']:
				process, stdout, stderr = await target.execute('nmap {nmap_extra}' + service_opts + timing_opts + ' -p ' + target.ports['tcp'] + ' -oN "{scandir}/_full_tcp_nmap.txt" -oX "{scandir}/xml/_full_tcp_nmap.xml" {address}', blocking=False)
			else:
				return []
		else:
			process, stdout, stderr = await target.execute('nmap {nmap_extra}' + service_opts + timing_opts + ' -p- -oN "{scandir}/_full_tcp_nmap.txt" -oX "{scandir}/xml/_full_tcp_nmap.xml" {address}', blocking=False)
		services = []
		while True:
			line = await stdout.readline()
			if line is not None:
				match = re.search('^Discovered open port ([0-9]+)/tcp', line)
				if match:
					target.info('Discovered open port {bmagenta}tcp/' + match.group(1) + '{rst} on {byellow}' + target.address + '{rst}', verbosity=1)
				service = target.extract_service(line)

				if service:
					# Check if HTTP service appears to be WinRM. If so, override service name as wsman.
					if service.name == 'http' and service.port in [5985, 5986]:
						try:
							# Quick check for WinRM with timeout to prevent hanging
							url = ('https' if service.secure else 'http') + '://' + target.address + ':' + str(service.port) + '/wsman'
							response = requests.get(url, verify=False, timeout=3)
							if response.status_code == 405:
								service.name = 'wsman'
							elif response.status_code == 401:
								service.name = 'wsman'
						except (requests.exceptions.RequestException, requests.exceptions.Timeout):
							# If WinRM check fails, keep as HTTP (don't block scan)
							target.debug('WinRM detection failed for {}:{}, keeping as HTTP'.format(target.address, service.port))

					services.append(service)
			else:
				break
		await process.wait()
		return services
