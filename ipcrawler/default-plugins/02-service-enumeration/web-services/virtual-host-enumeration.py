from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
from shutil import which
import os
import requests
import random
import string
import urllib3
import platform
import socket

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

		# If no hostnames found but we have an IP target, try to discover hostnames first
		if len(hostnames) == 0 and service.target.type == 'ip':
			# For IP targets, we can still attempt vhost enumeration if the user explicitly enables it
			# or if we find hostnames through other means (reverse DNS, certificates, etc.)
			if self.get_option('hostname'):
				# User provided explicit hostname for IP target
				hostnames.append(self.get_option('hostname'))
			else:
				# Try reverse DNS lookup for the IP
				try:
					reverse_dns = socket.gethostbyaddr(service.target.address)[0]
					if reverse_dns and reverse_dns != service.target.address:
						hostnames.append(reverse_dns)
						service.info(f"🔍 Discovered hostname via reverse DNS: {reverse_dns}")
				except:
					pass
				
				# If still no hostnames, inform user how to enable vhost enumeration for IP targets
				if len(hostnames) == 0:
					service.info(f"💡 To enumerate virtual hosts on IP {service.target.address}, use: --vhost-enum.hostname=example.com")
					return

		if len(hostnames) > 0:
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
									smart_wordlist_path = selector.select_wordlist('vhosts', detected_technologies)
									
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
							
							vhost_path = wordlist_manager.get_wordlist_path('vhosts', config.get('data_dir'), current_size, detected_technologies)
							service.info(f"🔍 WordlistManager resolved path: {vhost_path}")
							
							if vhost_path and os.path.exists(vhost_path):
								resolved_wordlists.append(vhost_path)
								service.info(f"✅ Using WordlistManager wordlist: {vhost_path}")
							else:
								service.error(f'❌ WordlistManager found no wordlist for size "{current_size}". Path attempted: {vhost_path}')
								
						# PRIORITY 3: Hard-coded fallbacks if both Smart Selector and WordlistManager failed
						if not resolved_wordlists:
							service.info("📦 Trying hard-coded fallback wordlists")
							if platform.system() == "Darwin":  # macOS
								service.info(f"💡 Install SecLists: brew install seclists")
							else:
								service.info(f"💡 Install SecLists: sudo apt install seclists")
							service.info(f"💡 Or specify custom: --vhost-enum.wordlist /path/to/wordlist.txt")
							
							fallback_paths = [
								'/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
								'/usr/share/wordlists/dirb/common.txt',
								'/usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt'
							]
							found_fallback = False
							for fallback_path in fallback_paths:
								if os.path.exists(fallback_path):
									service.info(f"🔄 Using fallback wordlist: {fallback_path}")
									resolved_wordlists.append(fallback_path)
									found_fallback = True
									break
							if not found_fallback:
								service.warn('No vhost wordlist found. Please install SecLists or specify a custom wordlist.')
								continue
					except Exception as e:
						service.error(f'❌ WordlistManager error: {e}')
						service.info("📦 Trying hard-coded fallback wordlists")
						if platform.system() == "Darwin":  # macOS
							service.info(f"💡 Install SecLists: brew install seclists")
						else:
							service.info(f"💡 Install SecLists: sudo apt install seclists")
						service.info(f"💡 Or specify custom: --vhost-enum.wordlist /path/to/wordlist.txt")
						
						fallback_paths = [
							'/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
							'/usr/share/wordlists/dirb/common.txt',
							'/usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt'
						]
						found_fallback = False
						for fallback_path in fallback_paths:
							if os.path.exists(fallback_path):
								service.info(f"🔄 Using fallback wordlist: {fallback_path}")
								resolved_wordlists.append(fallback_path)
								found_fallback = True
								break
						if not found_fallback:
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

					# Build ffuf command with verbosity options
					verbose_level = self.get_global('verbose', 0)
					ffuf_cmd = ('ffuf -u {http_scheme}://' + hostname + ':{port}/ -t ' + str(self.get_option('threads')) +
						' -w ' + wordlist + ' -H "Host: FUZZ.' + hostname + '" -mc all -fs ' + size +
						' -r -noninteractive')
					
					# Add verbosity flags based on -vvv level
					if verbose_level is not None and verbose_level >= 3:
						# -vvv: Show detailed scan info but still keep results clean (no per-word spam)
						service.info(f"🔍 Running virtual host enumeration with detailed output")
						service.info(f"🎯 Wordlist: {os.path.basename(wordlist)} ({self.get_option('threads')} threads)")
						ffuf_cmd += ' -s'  # Keep silent to avoid clutter, we'll show our own messages
					elif verbose_level is not None and verbose_level >= 2:
						# -vv: Show scan progress but keep clean
						service.info(f"🔍 Scanning virtual hosts on {hostname}")
						ffuf_cmd += ' -s'
					else:
						# Default: Silent mode
						ffuf_cmd += ' -s'
					
					ffuf_cmd += (' -o "{scandir}/{protocol}_{port}_{http_scheme}_' + hostname + '_vhosts_' + name + '.txt" -of csv')
					
					# Show progress info
					with open(wordlist, 'r') as f:
						total_lines = sum(1 for _ in f)
					service.info(f"🔍 Enumerating {total_lines} virtual hosts on {hostname}...")
					
					# Enhanced pattern matching for virtual host discoveries
					self.add_pattern(r'(\S+\.' + hostname.replace('.', r'\.') + r')', description='Virtual Host discovered: {match1} - additional subdomain/service available')
					
					await service.execute(ffuf_cmd, outfile='{protocol}_{port}_{http_scheme}_' + hostname + '_vhosts_' + name + '.txt')
		else:
			service.info('The target was not a hostname, nor was a hostname provided as an option. Skipping virtual host enumeration.')
