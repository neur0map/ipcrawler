from ipcrawler.plugins import ServiceScan
from ipcrawler.config import config
from ipcrawler.wordlists import get_wordlist_manager
from shutil import which
import os

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
		self.add_choice_option('vhost-mode', default='smart', choices=['all', 'best', 'smart'], help='How to handle multiple discovered hostnames: all=scan all, best=scan best only, smart=scan best + unique domains. Default: %(default)s')
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)

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
				# Auto-detect best available wordlist using configured size preference
				try:
					wordlist_manager = get_wordlist_manager()
					current_size = wordlist_manager.get_wordlist_size()
					service.info(f"🔍 WordlistManager size: {current_size}")
					
					web_dirs_path = wordlist_manager.get_wordlist_path('web_directories', config.get('data_dir'), current_size)
					service.info(f"🔍 Resolved wordlist path: {web_dirs_path}")
					
					if web_dirs_path and os.path.exists(web_dirs_path):
						resolved_wordlists.append(web_dirs_path)
						service.info(f"✅ Using wordlist: {web_dirs_path}")
					else:
						service.error(f'❌ No wordlist found for size "{current_size}". Path attempted: {web_dirs_path}')
						service.info(f"💡 Try: --dirbuster.wordlist /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt")
						return
				except Exception as e:
					service.error(f'❌ WordlistManager error: {e}')
					service.info(f"💡 Try: --dirbuster.wordlist /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt")
					return
			else:
				# User specified a custom wordlist path
				service.info(f"✅ Using custom wordlist: {wordlist}")
				resolved_wordlists.append(wordlist)
		
		# Scan each hostname with each wordlist
		for hostname in hostnames:
			hostname_label = hostname.replace('.', '_').replace(':', '_')
			for wordlist in resolved_wordlists:
				name = os.path.splitext(os.path.basename(wordlist))[0]
				
				# Use IPv6 brackets if needed for IP addresses
				scan_hostname = hostname
				if ':' in hostname and not hostname.startswith('['):
					scan_hostname = f'[{hostname}]'
				
				if self.get_option('tool') == 'feroxbuster':
					status_codes = self.get_option('status-codes')
					await service.execute('feroxbuster -u {http_scheme}://' + scan_hostname + ':{port}/ -t ' + str(self.get_option('threads')) + ' -w ' + wordlist + ' -x "' + self.get_option('ext') + '" -s ' + status_codes + ' -v -k ' + ('' if self.get_option('recursive') else '-n ')  + '-q -e -r -o "{scandir}/{protocol}_{port}_{http_scheme}_feroxbuster_' + hostname_label + '_' + name + '.txt"' + (' ' + self.get_option('extras') if self.get_option('extras') else ''))

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
