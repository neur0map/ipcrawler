from ipcrawler.plugins import ServiceScan
from ipcrawler.config import config
from ipcrawler.wordlists import get_wordlist_manager
from shutil import which
import os
import time

class DirBuster(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Directory Buster"
		self.slug = 'dirbuster'
		self.description = "Discovers hidden directories and files on web servers using wordlists"
		self.priority = 0
		self.tags = ['default', 'safe', 'long', 'http']

	def configure(self):
		# Auto-detect available tools and pick the best default
		tool_priority = ['feroxbuster', 'gobuster', 'ffuf', 'dirsearch', 'dirb']
		default_tool = 'feroxbuster'  # fallback
		for tool in tool_priority:
			if which(tool) is not None:
				default_tool = tool
				break
		
		self.add_choice_option('tool', default=default_tool, choices=['feroxbuster', 'gobuster', 'dirsearch', 'ffuf', 'dirb'], help='The tool to use for directory busting. Default: %(default)s')
		# Default to auto-detection - wordlists will be resolved at runtime
		self.add_list_option('wordlist', default=['auto'], help='The wordlist(s) to use when directory busting. Use "auto" for automatic SecLists detection, or specify custom paths. Default: %(default)s')
		self.add_option('threads', default=10, help='The number of threads to use when directory busting. Default: %(default)s')
		self.add_option('ext', default='php,html,txt', help='The extensions you wish to fuzz (no dot, comma separated). Default: %(default)s')
		self.add_true_option('recursive', help='Enables recursive searching (where available). Warning: This may cause significant increases to scan times.')
		self.add_option('status-codes', default='200,301,302,303,307,308,403,401,405', help='HTTP status codes to include in results (comma-separated). Default: %(default)s')
		self.add_option('extras', default='', help='Any extra options you wish to pass to the tool when it runs. e.g. --dirbuster.extras=\'--discover-backup\'')
		self.add_option('timeout', default=3600, help='Maximum time in seconds for directory busting scan. Default: %(default)s (1 hour)')
		self.add_choice_option('vhost-mode', default='smart', choices=['all', 'best', 'smart'], help='How to handle multiple discovered hostnames: all=scan all, best=scan best only, smart=scan best + unique domains. Default: %(default)s')
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)
		# Pattern matching for directory busting findings
		self.add_pattern(r'(?i)200\s+\d+\w?\s+([^\s]+)', description='Directory/File Found (200): {match1}')
		self.add_pattern(r'(?i)30[1-8]\s+\d+\w?\s+([^\s]+)', description='Redirect Found (30x): {match1}')
		self.add_pattern(r'(?i)403\s+\d+\w?\s+([^\s]+)', description='Forbidden Access (403): {match1} - potential restricted resource')
		self.add_pattern(r'(?i)401\s+\d+\w?\s+([^\s]+)', description='Authentication Required (401): {match1}')

	def check(self):
		tool = self.get_option('tool')
		
		# Check if the selected tool is available
		if which(tool) is None:
			# Check if any alternative tools are available
			alternatives = []
			for alt_tool in ['feroxbuster', 'gobuster', 'ffuf', 'dirsearch', 'dirb']:
				if alt_tool != tool and which(alt_tool) is not None:
					alternatives.append(alt_tool)
			
			if alternatives:
				self.error(f'The {tool} program could not be found, but {", ".join(alternatives)} is available. Use --dirbuster.tool={alternatives[0]} to use an alternative.')
				return False
			else:
				self.error(f'The {tool} program could not be found. Make sure it is installed. (On Kali, try: sudo apt install {tool})')
				return False
		
		return True

	async def run(self, service):
		dot_extensions = ','.join(['.' + x for x in self.get_option('ext').split(',')])
		
		# Get hostnames based on vhost-mode setting
		all_hostnames = service.target.get_all_hostnames()
		best_hostname = service.target.get_best_hostname()
		vhost_mode = self.get_option('vhost-mode')
		
		# Show hostname debug info
		service.info(f"🔍 Target type: {service.target.type}, address: {service.target.address}")
		service.info(f"🔍 Discovered hostnames: {service.target.discovered_hostnames}")
		service.info(f"🔍 All hostnames: {all_hostnames}")
		service.info(f"🔍 Best hostname: {best_hostname}")
		
		# CRITICAL: Ensure we always have hostnames - safety check
		if not all_hostnames:
			service.error("❌ CRITICAL: No hostnames available! Using IP fallback.")
			all_hostnames = [service.target.ip if service.target.ip else service.target.address]
		if not best_hostname:
			service.error("❌ CRITICAL: No best hostname available! Using IP fallback.")
			best_hostname = service.target.ip if service.target.ip else service.target.address
		
		# Select hostnames based on mode
		if vhost_mode == 'best':
			hostnames = [best_hostname]
			service.info(f"🌐 Using best hostname only: {best_hostname}")
		elif vhost_mode == 'smart':
			# Use best hostname + unique domains (avoid scanning similar subdomains)
			hostnames = [best_hostname]
			seen_domains = set()
			if '.' in best_hostname:
				seen_domains.add('.'.join(best_hostname.split('.')[-2:]))  # Get root domain
			
			for hostname in all_hostnames:
				if hostname != best_hostname:
					# Add if it's a different root domain or IP
					if '.' not in hostname or '.'.join(hostname.split('.')[-2:]) not in seen_domains:
						hostnames.append(hostname)
						if '.' in hostname:
							seen_domains.add('.'.join(hostname.split('.')[-2:]))
			
			service.info(f"🌐 Using smart hostname selection: {', '.join(hostnames)}")
		else:  # 'all'
			hostnames = all_hostnames
			service.info(f"🌐 Using all hostnames: {', '.join(hostnames)}")
		
		# FINAL SAFETY CHECK: Ensure we have hostnames to scan
		if not hostnames:
			service.error("❌ CRITICAL: No hostnames to scan! Emergency IP fallback.")
			hostnames = [service.target.ip if service.target.ip else service.target.address]
		
		if len(hostnames) > 1:
			service.info(f"🎯 Primary hostname: {best_hostname}")
			service.info(f"⚡ Scanning {len(hostnames)} hostname(s) - use --dirbuster.vhost-mode=best for faster scans")
		
		service.info(f"✅ Final hostnames for directory enumeration: {', '.join(hostnames)}")
		
		# Resolve wordlists at runtime
		wordlists = self.get_option('wordlist')
		resolved_wordlists = []
		
		service.info(f"🔍 Wordlist option: {wordlists}")
		
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
								smart_wordlist_path = selector.select_wordlist('web_directories', detected_technologies)
								
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
						
						web_dirs_path = wordlist_manager.get_wordlist_path('web_directories', config.get('data_dir', ''), current_size, detected_technologies)
						service.info(f"🔍 WordlistManager resolved path: {web_dirs_path}")
						
						if web_dirs_path and os.path.exists(web_dirs_path):
							resolved_wordlists.append(web_dirs_path)
							service.info(f"✅ Using WordlistManager wordlist: {web_dirs_path}")
						else:
							service.error(f'❌ WordlistManager found no wordlist for size "{current_size}". Path attempted: {web_dirs_path}')
							service.error("⚠️  This could cause abnormally fast scan completion!")
							
					# PRIORITY 3: Hard-coded fallbacks if both Smart Selector and WordlistManager failed
					if not resolved_wordlists:
						service.info("📦 Trying hard-coded fallback wordlists")
						import platform
						if platform.system() == "Darwin":  # macOS
							service.info(f"💡 Install SecLists: brew install seclists")
						else:
							service.info(f"💡 Install SecLists: sudo apt install seclists")
						service.info(f"💡 Or specify custom: --dirbuster.wordlist /path/to/wordlist.txt")
						
						fallback_paths = [
							'/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt',
							'/usr/share/wordlists/dirb/common.txt',
							'/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt'
						]
						found_fallback = False
						for fallback_path in fallback_paths:
							if os.path.exists(fallback_path):
								service.info(f"🔄 Using fallback wordlist: {fallback_path}")
								resolved_wordlists.append(fallback_path)
								found_fallback = True
								break
						if not found_fallback:
							service.error("❌ No fallback wordlists available - skipping directory busting for this hostname")
							continue  # Skip this hostname, but continue with others
				except Exception as e:
					service.error(f'❌ WordlistManager error: {e}')
					service.error("⚠️  This could cause abnormally fast scan completion!")
					import platform
					if platform.system() == "Darwin":  # macOS
						service.info(f"💡 Install SecLists: brew install seclists")
					else:
						service.info(f"💡 Install SecLists: sudo apt install seclists")
					service.info(f"💡 Or specify custom: --dirbuster.wordlist /path/to/wordlist.txt")
					# Continue with fallback instead of terminating
					fallback_paths = [
						'/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt',
						'/usr/share/wordlists/dirb/common.txt',
						'/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt'
					]
					found_fallback = False
					for fallback_path in fallback_paths:
						if os.path.exists(fallback_path):
							service.info(f"🔄 Using fallback wordlist: {fallback_path}")
							resolved_wordlists.append(fallback_path)
							found_fallback = True
							break
					if not found_fallback:
						service.error("❌ No fallback wordlists available - skipping directory busting for this hostname")
						continue  # Skip this hostname, but continue with others
			else:
				# User specified a custom wordlist path
				service.info(f"✅ Using custom wordlist: {wordlist}")
				resolved_wordlists.append(wordlist)
		
		# Check if we have any wordlists available
		if not resolved_wordlists:
			service.error("❌ No wordlists available for directory busting")
			service.error("🚨 This explains why the scan completed in only 4 seconds!")
			service.info("💡 Install SecLists:")
			import platform
			if platform.system() == "Darwin":  # macOS
				service.info("   • macOS: brew install seclists")
				service.info("   • Or: git clone https://github.com/danielmiessler/SecLists.git /usr/local/share/seclists")
			else:  # Linux
				service.info("   • Linux: sudo apt install seclists")
				service.info("   • Or: sudo yum install seclists")
			service.info("💡 Alternative: --dirbuster.wordlist /path/to/custom/wordlist.txt")
			service.info("💡 Check installation: ls /usr/share/seclists/Discovery/Web-Content/")
			return  # Exit gracefully, don't crash the scan
		
		# Scan each hostname with each wordlist
		for hostname in hostnames:
			hostname_label = hostname.replace('.', '_').replace(':', '_')
			for wordlist in resolved_wordlists:
				# CRITICAL: Validate wordlist exists before attempting to use it
				if not os.path.exists(wordlist):
					service.error(f"❌ Wordlist file does not exist: {wordlist}")
					service.error("🚨 This WILL cause feroxbuster to exit in ~4 seconds!")
					service.info(f"💡 Available wordlists: ls {os.path.dirname(wordlist)}")
					continue  # Skip this wordlist, try next one
				
				# Check if wordlist is empty
				try:
					with open(wordlist, 'r') as f:
						first_line = f.readline().strip()
						if not first_line:
							service.error(f"❌ Wordlist is empty: {wordlist}")
							service.error("🚨 This WILL cause feroxbuster to exit in ~4 seconds!")
							continue
				except Exception as e:
					service.error(f"❌ Cannot read wordlist {wordlist}: {e}")
					continue
				
				name = os.path.splitext(os.path.basename(wordlist))[0]
				service.info(f"✅ Using validated wordlist: {wordlist}")
				
				# Use IPv6 brackets if needed for IP addresses
				scan_hostname = hostname
				if ':' in hostname and not hostname.startswith('['):
					scan_hostname = f'[{hostname}]'
				
				if self.get_option('tool') == 'feroxbuster':
					status_codes = self.get_option('status-codes')
					
					# Log the exact command being executed for debugging
					ferox_cmd = 'timeout ' + str(self.get_option('timeout')) + ' feroxbuster -u {http_scheme}://' + scan_hostname + ':{port}/ -t ' + str(self.get_option('threads')) + ' -w ' + wordlist + ' -x "' + self.get_option('ext') + '" -s ' + status_codes + ' -v -k ' + ('' if self.get_option('recursive') else '-n ')  + '-q -e -r -o "{scandir}/{protocol}_{port}_{http_scheme}_feroxbuster_' + hostname_label + '_' + name + '.txt"' + (' ' + self.get_option('extras') if self.get_option('extras') else '')
					service.info(f"🔧 Executing: {ferox_cmd.replace('{http_scheme}', 'http').replace('{port}', str(service.port))}")
					
					start_time = time.time()
					process, stdout, stderr = await service.execute(ferox_cmd, outfile='{protocol}_{port}_{http_scheme}_feroxbuster_' + hostname_label + '_' + name + '.txt')
					end_time = time.time()
					duration = end_time - start_time
					
					# Check if scan completed abnormally fast
					if duration < 10:  # Less than 10 seconds is suspicious
						service.error(f"🚨 SUSPICIOUS: feroxbuster completed in {duration:.1f}s - this is abnormally fast!")
						service.info("💡 Possible causes:")
						service.info("   • Target not responding to HTTP requests")
						service.info("   • Wordlist file missing or empty")
						service.info("   • Network connectivity issues")
						service.info("   • Target returning identical responses (rate limiting)")
						service.info(f"💡 Test manually: curl -I http://{scan_hostname}:{service.port}/")
					else:
						service.info(f"✅ feroxbuster completed in {duration:.1f}s")

				elif self.get_option('tool') == 'gobuster':
					status_codes = self.get_option('status-codes')
					await service.execute('gobuster dir -u {http_scheme}://' + scan_hostname + ':{port}/ -t ' + str(self.get_option('threads')) + ' -w ' + wordlist + ' -s ' + status_codes + ' -e -k -x "' + self.get_option('ext') + '" -z -r -o "{scandir}/{protocol}_{port}_{http_scheme}_gobuster_' + hostname_label + '_' + name + '.txt"' + (' ' + self.get_option('extras') if self.get_option('extras') else ''))

				elif self.get_option('tool') == 'dirsearch':
					if service.target.ipversion == 'IPv6' and hostname == service.target.ip:
						service.error('dirsearch does not support IPv6.')
						continue
					else:
						status_codes = self.get_option('status-codes')
						await service.execute('dirsearch -u {http_scheme}://' + hostname + ':{port}/ -t ' + str(self.get_option('threads')) + ' -e "' + self.get_option('ext') + '" --include-status=' + status_codes + ' -f -q -F ' + ('-r ' if self.get_option('recursive') else '') + '-w ' + wordlist + ' --format=plain -o "{scandir}/{protocol}_{port}_{http_scheme}_dirsearch_' + hostname_label + '_' + name + '.txt"' + (' ' + self.get_option('extras') if self.get_option('extras') else ''))

				elif self.get_option('tool') == 'ffuf':
					status_codes = self.get_option('status-codes')
					await service.execute('ffuf -u {http_scheme}://' + scan_hostname + ':{port}/FUZZ -t ' + str(self.get_option('threads')) + ' -w ' + wordlist + ' -e "' + dot_extensions + '" -mc ' + status_codes + ' -v -r ' + ('-recursion ' if self.get_option('recursive') else '') + '-noninteractive' + (' ' + self.get_option('extras') if self.get_option('extras') else '') + ' | tee {scandir}/{protocol}_{port}_{http_scheme}_ffuf_' + hostname_label + '_' + name + '.txt')

				elif self.get_option('tool') == 'dirb':
					# Note: dirb doesn't support status code filtering, it shows all responses
					service.info(f"⚠️ dirb doesn't support status code filtering - use feroxbuster or gobuster for cleaner output")
					await service.execute('dirb {http_scheme}://' + scan_hostname + ':{port}/ ' + wordlist + ' -l ' + ('' if self.get_option('recursive') else '-r ')  + '-S -X ",' + dot_extensions + '" -f -o "{scandir}/{protocol}_{port}_{http_scheme}_dirb_' + hostname_label + '_' + name + '.txt"' + (' ' + self.get_option('extras') if self.get_option('extras') else ''))

	def manual(self, service, plugin_was_run):
		dot_extensions = ','.join(['.' + x for x in self.get_option('ext').split(',')])
		
		# Get all hostnames to scan
		hostnames = service.target.get_all_hostnames()
		best_hostname = service.target.get_best_hostname()
		
		# Get wordlist path from WordlistManager for manual commands
		try:
			wordlist_manager = get_wordlist_manager()
			current_size = wordlist_manager.get_wordlist_size()
			web_dirs_path = wordlist_manager.get_wordlist_path('web_directories', config.get('data_dir'), current_size)
			if not web_dirs_path or not os.path.exists(web_dirs_path):
				service.add_manual_command('Directory enumeration requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No wordlists available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
				return
		except Exception:
			service.add_manual_command('Directory enumeration requires WordlistManager configuration:', [
				'# WordlistManager not available. Please check configuration.'
			])
			return
		
		# Add commands for each discovered hostname
		for hostname in hostnames:
			hostname_label = hostname.replace('.', '_').replace(':', '_')
			scan_hostname = hostname
			if ':' in hostname and not hostname.startswith('['):
				scan_hostname = f'[{hostname}]'
			
			hostname_desc = f" ({hostname})" if hostname != service.target.ip else " (IP fallback)"
			
			if self.get_option('tool') == 'feroxbuster':
				status_codes = self.get_option('status-codes')
				service.add_manual_command(f'(feroxbuster) Multi-threaded directory/file enumeration{hostname_desc}:', [
					'feroxbuster -u {http_scheme}://' + scan_hostname + ':{port} -t ' + str(self.get_option('threads')) + ' -w ' + web_dirs_path + ' -x "' + self.get_option('ext') + '" -s ' + status_codes + ' -v -k ' + ('' if self.get_option('recursive') else '-n ')  + '-e -r -o {scandir}/{protocol}_{port}_{http_scheme}_feroxbuster_' + hostname_label + '_manual.txt' + (' ' + self.get_option('extras') if self.get_option('extras') else '')
				])
			elif self.get_option('tool') == 'gobuster':
				status_codes = self.get_option('status-codes')
				service.add_manual_command(f'(gobuster v3) Multi-threaded directory/file enumeration{hostname_desc}:', [
					'gobuster dir -u {http_scheme}://' + scan_hostname + ':{port}/ -t ' + str(self.get_option('threads')) + ' -w ' + web_dirs_path + ' -s ' + status_codes + ' -e -k -x "' + self.get_option('ext') + '" -r -o "{scandir}/{protocol}_{port}_{http_scheme}_gobuster_' + hostname_label + '_manual.txt"' + (' ' + self.get_option('extras') if self.get_option('extras') else '')
				])
			elif self.get_option('tool') == 'dirsearch':
				if not (service.target.ipversion == 'IPv6' and hostname == service.target.ip):
					status_codes = self.get_option('status-codes')
					service.add_manual_command(f'(dirsearch) Multi-threaded directory/file enumeration{hostname_desc}:', [
						'dirsearch -u {http_scheme}://' + hostname + ':{port}/ -t ' + str(self.get_option('threads')) + ' -e "' + self.get_option('ext') + '" --include-status=' + status_codes + ' -f -F ' + ('-r ' if self.get_option('recursive') else '') + '-w ' + web_dirs_path + ' --format=plain --output="{scandir}/{protocol}_{port}_{http_scheme}_dirsearch_' + hostname_label + '_manual.txt"' + (' ' + self.get_option('extras') if self.get_option('extras') else '')
					])
			elif self.get_option('tool') == 'ffuf':
				status_codes = self.get_option('status-codes')
				service.add_manual_command(f'(ffuf) Multi-threaded directory/file enumeration{hostname_desc}:', [
					'ffuf -u {http_scheme}://' + scan_hostname + ':{port}/FUZZ -t ' + str(self.get_option('threads')) + ' -w ' + web_dirs_path + ' -e "' + dot_extensions + '" -mc ' + status_codes + ' -v -r ' + ('-recursion ' if self.get_option('recursive') else '') + '-noninteractive' + (' ' + self.get_option('extras') if self.get_option('extras') else '') + ' | tee {scandir}/{protocol}_{port}_{http_scheme}_ffuf_' + hostname_label + '_manual.txt'
				])
			elif self.get_option('tool') == 'dirb':
				service.add_manual_command(f'(dirb) Directory/file enumeration{hostname_desc}:', [
					'dirb {http_scheme}://' + scan_hostname + ':{port}/ ' + web_dirs_path + ' -l ' + ('' if self.get_option('recursive') else '-r ')  + '-X ",' + dot_extensions + '" -f -o "{scandir}/{protocol}_{port}_{http_scheme}_dirb_' + hostname_label + '_manual.txt"' + (' ' + self.get_option('extras') if self.get_option('extras') else '')
				])
