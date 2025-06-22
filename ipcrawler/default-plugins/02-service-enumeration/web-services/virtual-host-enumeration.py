from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
from shutil import which
import os, requests, random, string, urllib3

urllib3.disable_warnings()

class VirtualHost(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Virtual Host Enumeration'
		self.slug = 'vhost-enum'
		self.tags = ['default', 'safe', 'http', 'long']

	def configure(self):
		self.add_option('hostname', help='The hostname to use as the base host (e.g. example.com) for virtual host enumeration. Default: %(default)s')
		# Default to auto-detection - wordlists will be resolved at runtime
		self.add_list_option('wordlist', default=['auto'], help='The wordlist(s) to use when enumerating virtual hosts. Use "auto" for automatic SecLists detection, or specify custom paths. Default: %(default)s')
		self.add_option('threads', default=10, help='The number of threads to use when enumerating virtual hosts. Default: %(default)s')
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)

	async def run(self, service):
		hostnames = []
		if self.get_option('hostname'):
			hostnames.append(self.get_option('hostname'))
		if service.target.type == 'hostname' and service.target.address not in hostnames:
			hostnames.append(service.target.address)
		if self.get_global('domain') and self.get_global('domain') not in hostnames:
			hostnames.append(self.get_global('domain'))
		
		# Add already discovered hostnames as base domains for further vhost discovery
		discovered_hostnames = service.target.discovered_hostnames
		for discovered in discovered_hostnames:
			if discovered not in hostnames:
				hostnames.append(discovered)
				service.info(f"🔄 Using previously discovered hostname as base: {discovered}")

		if len(hostnames) > 0:
			# Resolve wordlists at runtime
			wordlists = self.get_option('wordlist')
			resolved_wordlists = []
			
			for wordlist in wordlists:
				if wordlist == 'auto':
					# Auto-detect best available wordlist using configured size preference
					try:
						wordlist_manager = get_wordlist_manager()
						current_size = wordlist_manager.get_wordlist_size()
						vhost_path = wordlist_manager.get_wordlist_path('vhosts', config.get('data_dir'), current_size)
						if vhost_path and os.path.exists(vhost_path):
							resolved_wordlists.append(vhost_path)
						else:
							# Fallback to hardcoded SecLists path
							fallback_path = '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt'
							if os.path.exists(fallback_path):
								resolved_wordlists.append(fallback_path)
							else:
								service.warn('No vhost wordlist found. Please install SecLists or specify a custom wordlist.')
								continue
					except Exception:
						# Fallback to hardcoded SecLists path if WordlistManager isn't available
						fallback_path = '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt'
						if os.path.exists(fallback_path):
							resolved_wordlists.append(fallback_path)
						else:
							service.warn('No vhost wordlist found. Please install SecLists or specify a custom wordlist.')
							continue
				else:
					# User specified a custom wordlist path
					if os.path.exists(wordlist):
						resolved_wordlists.append(wordlist)
					else:
						service.warn(f'Wordlist not found: {wordlist}')
						continue
			
			for wordlist in resolved_wordlists:
				name = os.path.splitext(os.path.basename(wordlist))[0]
				for hostname in hostnames:
					try:
						wildcard = requests.get(
							('https' if service.secure else 'http') + '://' + service.target.address + ':' + str(service.port) + '/',
							headers={'Host': ''.join(random.choice(string.ascii_letters) for _ in range(20)) + '.' + hostname},
							verify=False,
							allow_redirects=False
						)
						size = str(len(wildcard.content))
					except requests.exceptions.RequestException as e:
						service.error(f"Wildcard request failed for {hostname}: {e}", verbosity=1)
						continue

					await service.execute(
						'ffuf -u {http_scheme}://' + hostname + ':{port}/ -t ' + str(self.get_option('threads')) +
						' -w ' + wordlist + ' -H "Host: FUZZ.' + hostname + '" -mc all -fs ' + size +
						' -r -noninteractive -s | tee "{scandir}/{protocol}_{port}_{http_scheme}_' + hostname + '_vhosts_' + name + '.txt"'
					)
		else:
			service.info('The target was not a hostname, nor was a hostname provided as an option. Skipping virtual host enumeration.')
