from ipcrawler.plugins import PortScan
from ipcrawler.config import config
import re, requests, asyncio

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
		timing_opts = ' -T5 --min-rate=5000 --max-rate=10000'
		
		if config['proxychains']:
			# Lighter scan for proxychains (slower connections)
			service_opts = ' -sV'
			timing_opts = ' -T4 --min-rate=1000 --max-rate=3000'
		else:
			# Balanced service detection (removed --version-all for performance)
			service_opts = ' -sV -sC'

		if target.ports:
			if target.ports['tcp']:
				process, stdout, stderr = await target.execute('nmap {nmap_extra}' + service_opts + timing_opts + ' -p ' + target.ports['tcp'] + ' -oN "{scandir}/_full_tcp_nmap.txt" -oX "{scandir}/xml/_full_tcp_nmap.xml" {address}')
			else:
				return []
		else:
			process, stdout, stderr = await target.execute('nmap {nmap_extra}' + service_opts + timing_opts + ' -p- -oN "{scandir}/_full_tcp_nmap.txt" -oX "{scandir}/xml/_full_tcp_nmap.xml" {address}')
		services = await target.extract_services(stdout)

		for service in services:
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

		# Ensure proper process cleanup on macOS with configured timeout
		configured_timeout = config.get('timeout', 120) * 60  # Default 2 hours in seconds
		
		try:
			await asyncio.wait_for(process.wait(), timeout=configured_timeout)
		except asyncio.TimeoutError:
			# Force cleanup if process doesn't terminate properly
			try:
				process.kill()
				await asyncio.wait_for(process.wait(), timeout=3)
			except (asyncio.TimeoutError, OSError):
				pass
		
		return services
