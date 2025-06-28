from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os
import platform

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
		# Pattern matching for subdomain findings
		self.add_pattern(r'(?i)found.*subdomain[s]?[:\s]*([^\n\r]+)', description='Subdomains Found: {match1}')
		self.add_pattern(r'(?i)[a-z0-9\-]+\.[a-z0-9\-\.]+\.[a-z]{2,}', description='Subdomain Discovered: {match0}')
		self.add_pattern(r'(?i)gobuster.*found[:\s]*([^\n\r]+)', description='Gobuster Subdomain: {match1}')

	async def run(self, service):
		domains = []

		if self.get_option('domain'):
			domains.append(self.get_option('domain'))
		if service.target.type == 'hostname' and service.target.address not in domains:
			domains.append(service.target.address)
		if self.get_global('domain') and self.get_global('domain') not in domains:
			domains.append(self.get_global('domain'))

		# Add discovered hostnames as potential domains for subdomain enumeration
		discovered_hostnames = service.target.discovered_hostnames
		for discovered in discovered_hostnames:
			if discovered not in domains:
				domains.append(discovered)
				service.info(f"🔄 Using discovered hostname for subdomain enum: {discovered}")

		# For IP targets, provide helpful guidance
		if len(domains) == 0 and service.target.type == 'ip':
			service.info(f"💡 To enumerate subdomains for IP {service.target.address}, use: --subdomain-enum.domain=example.com")
			return

		if len(domains) > 0:
			# Resolve wordlists at runtime
			wordlists = self.get_option('wordlist')
			resolved_wordlists = []
			
			for wordlist in wordlists:
				if wordlist == 'auto':
					# Auto-detect best available wordlist using Smart Wordlist Selector FIRST
					try:
						# Detect technologies from scan results
						from ipcrawler.technology_detector import TechnologyDetector
						detector = TechnologyDetector(service.target.scandir)
						detected_technologies = detector.detect_from_scan_results()
						
						if detected_technologies:
							service.info(f"🤖 Detected technologies: {', '.join(detected_technologies)}")
						else:
							service.info("🤖 No specific technologies detected")
						
						# PRIORITY 1: Try Smart Wordlist Selector first
						smart_wordlist_path = None
						if detected_technologies:
							try:
								from ipcrawler.smart_wordlist_selector import SmartWordlistSelector
								
								# Get SecLists path from WordlistManager
								wordlist_manager = get_wordlist_manager()
								config_data = wordlist_manager.load_config()
								seclists_path = config_data.get('detected_paths', {}).get('seclists_base')
								
								if seclists_path and os.path.exists(seclists_path):
									service.info(f"🤖 Using Smart Wordlist Selector with SecLists at: {seclists_path}")
									selector = SmartWordlistSelector(seclists_path)
									smart_wordlist_path = selector.select_wordlist('subdomains', detected_technologies)
									
									if smart_wordlist_path and os.path.exists(smart_wordlist_path):
										resolved_wordlists.append(smart_wordlist_path)
										# Use the actually selected technology, not the first detected one
										selected_tech = selector.get_selected_technology() or list(detected_technologies)[0]
										selection_info = selector.get_selection_info(smart_wordlist_path, selected_tech)
										service.info(f"✅ Smart selection: {selection_info}")
										service.info(f"✅ Using technology-specific wordlist: {smart_wordlist_path}")
									else:
										service.info("🤖 Smart Wordlist Selector found no technology-specific wordlists")
										service.info(f"🤖 Technologies detected: {', '.join(detected_technologies)}")
										service.info(f"🤖 Catalog available: {bool(selector.catalog)}")
										if selector.catalog:
											service.info(f"🤖 Catalog wordlists: {len(selector.catalog.get('wordlists', {}))}")
								else:
									service.info("🤖 Smart Wordlist Selector: SecLists path not available")
							except Exception as e:
								service.info(f"🤖 Smart Wordlist Selector unavailable: {e}")
						
						# PRIORITY 2: Fallback to WordlistManager if Smart Selector didn't find anything
						if not smart_wordlist_path:
							service.info("📚 Falling back to WordlistManager (wordlists.toml)")
							wordlist_manager = get_wordlist_manager()
							current_size = wordlist_manager.get_wordlist_size()
							service.info(f"🔍 WordlistManager size: {current_size}")
							
							subdomain_path = wordlist_manager.get_wordlist_path('subdomains', config.get('data_dir'), current_size, detected_technologies)
							service.info(f"🔍 WordlistManager resolved path: {subdomain_path}")
							
							if subdomain_path and os.path.exists(subdomain_path):
								resolved_wordlists.append(subdomain_path)
								service.info(f"✅ Using WordlistManager wordlist: {subdomain_path}")
							else:
								service.error(f'❌ WordlistManager found no wordlist for size "{current_size}". Path attempted: {subdomain_path}')
								
						# PRIORITY 3: Hard-coded fallbacks if both Smart Selector and WordlistManager failed
						if not resolved_wordlists:
							service.info("📦 Trying hard-coded fallback wordlists")
							if platform.system() == "Darwin":  # macOS
								service.info(f"💡 Install SecLists: brew install seclists")
							else:
								service.info(f"💡 Install SecLists: sudo apt install seclists")
							service.info(f"💡 Or specify custom: --subdomain-enum.wordlist /path/to/wordlist.txt")
							
							fallback_paths = [
								'/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
								'/usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt',
								'/usr/share/wordlists/dirb/common.txt'
							]
							found_fallback = False
							for fallback_path in fallback_paths:
								if os.path.exists(fallback_path):
									service.info(f"🔄 Using fallback wordlist: {fallback_path}")
									resolved_wordlists.append(fallback_path)
									found_fallback = True
									break
							if not found_fallback:
								service.warn('No subdomain wordlist found. Please install SecLists or specify a custom wordlist.')
								continue
					except Exception as e:
						service.error(f'❌ WordlistManager error: {e}')
						service.info("📦 Trying hard-coded fallback wordlists")
						if platform.system() == "Darwin":  # macOS
							service.info(f"💡 Install SecLists: brew install seclists")
						else:
							service.info(f"💡 Install SecLists: sudo apt install seclists")
						service.info(f"💡 Or specify custom: --subdomain-enum.wordlist /path/to/wordlist.txt")
						
						fallback_paths = [
							'/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
							'/usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt',
							'/usr/share/wordlists/dirb/common.txt'
						]
						found_fallback = False
						for fallback_path in fallback_paths:
							if os.path.exists(fallback_path):
								service.info(f"🔄 Using fallback wordlist: {fallback_path}")
								resolved_wordlists.append(fallback_path)
								found_fallback = True
								break
						if not found_fallback:
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
					await service.execute('gobuster dns -d ' + domain + ' -r {addressv6} -w ' + wordlist + ' -o "{scandir}/{protocol}_{port}_' + domain + '_subdomains_' + name + '.txt"', outfile='{protocol}_{port}_' + domain + '_subdomains_' + name + '.txt')
		else:
			service.info('The target was not a domain, nor was a domain provided as an option. Skipping subdomain enumeration.')
