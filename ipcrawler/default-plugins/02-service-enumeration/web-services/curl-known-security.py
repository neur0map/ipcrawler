from ipcrawler.plugins import ServiceScan
from ipcrawler.io import fformat

class CurlKnownSecurity(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Known Security"
		self.tags = ['default', 'safe', 'http']

	def configure(self):
		self.match_service_name('^http')
		self.match_service_name('ssl/http')
		self.match_service_name('^https')
		self.match_service_name('^nacn_http$', negative_match=True)

	async def run(self, service):
		if service.protocol == 'tcp':
			# Get best hostname (discovered hostname or IP fallback)
			best_hostname = service.target.get_best_hostname()
			hostname_label = best_hostname.replace('.', '_').replace(':', '_')
			
			scan_hostname = best_hostname
			if ':' in best_hostname and not best_hostname.startswith('['):
				scan_hostname = f'[{best_hostname}]'
			
			process, stdout, _ = await service.execute('curl -sSikf {http_scheme}://' + scan_hostname + ':{port}/.well-known/security.txt', future_outfile='{protocol}_{port}_{http_scheme}_known-security_' + hostname_label + '.txt')

			lines = await stdout.readlines()

			if process.returncode == 0 and lines:
				filename = fformat('{scandir}/{protocol}_{port}_{http_scheme}_known-security_' + hostname_label + '.txt')
				with open(filename, mode='wt', encoding='utf8') as robots:
					robots.write('\n'.join(lines))
			else:
				service.info('No .well-known/security.txt file found in webroot (/)', verbosity=2)
