from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os

class SubdomainEnumeration(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Subdomain Enumeration"
		self.slug = "subdomain-enum"
		self.tags = ['default', 'safe', 'long', 'dns']

	def configure(self):
		self.add_option('domain', help='The domain to use as the base domain (e.g. example.com) for subdomain enumeration. Default: %(default)s')
		# Default to auto-detection - wordlists will be resolved at runtime
		self.add_list_option('wordlist', default=['auto'], help='The wordlist(s) to use when enumerating subdomains. Use "auto" for automatic SecLists detection, or specify custom paths. Default: %(default)s')
		self.add_option('threads', default=10, help='The number of threads to use when enumerating subdomains. Default: %(default)s')
		self.match_service_name('^domain')

	async def run(self, service):
		domains = []

		if self.get_option('domain'):
			domains.append(self.get_option('domain'))
		if service.target.type == 'hostname' and service.target.address not in domains:
			domains.append(service.target.address)
		if self.get_global('domain') and self.get_global('domain') not in domains:
			domains.append(self.get_global('domain'))

		if len(domains) > 0:
			# Resolve wordlists at runtime
			wordlists = self.get_option('wordlist')
			resolved_wordlists = []
			
			for wordlist in wordlists:
				if wordlist == 'auto':
					# Auto-detect best available wordlist using configured size preference
					try:
						wordlist_manager = get_wordlist_manager()
						current_size = wordlist_manager.get_wordlist_size()
						subdomain_path = wordlist_manager.get_wordlist_path('subdomains', config.get('data_dir'), current_size)
						if subdomain_path and os.path.exists(subdomain_path):
							resolved_wordlists.append(subdomain_path)
						else:
							# Fallback to hardcoded SecLists path
							fallback_path = '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt'
							if os.path.exists(fallback_path):
								resolved_wordlists.append(fallback_path)
							else:
								service.warn('No subdomain wordlist found. Please install SecLists or specify a custom wordlist.')
								continue
					except Exception:
						# Fallback to hardcoded SecLists path if WordlistManager isn't available
						fallback_path = '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt'
						if os.path.exists(fallback_path):
							resolved_wordlists.append(fallback_path)
						else:
							service.warn('No subdomain wordlist found. Please install SecLists or specify a custom wordlist.')
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
				for domain in domains:
					await service.execute('gobuster dns -d ' + domain + ' -r {addressv6} -w ' + wordlist + ' -o "{scandir}/{protocol}_{port}_' + domain + '_subdomains_' + name + '.txt"')
		else:
			service.info('The target was not a domain, nor was a domain provided as an option. Skipping subdomain enumeration.')
