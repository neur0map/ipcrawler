from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os

class BruteforceHTTP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Bruteforce HTTP"
		self.tags = ['default', 'http']

	def configure(self):
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)
		
		# Add patterns for HTTP bruteforce result detection
		self.add_pattern(r'(?i)login:\s*(\S+)\s+password:\s*(\S+)', description='CRITICAL: HTTP credentials found - User: {match1}, Password: {match2}')
		self.add_pattern(r'(?i)valid password for\s+(\S+)', description='CRITICAL: Valid HTTP password found for user: {match1}')
		self.add_pattern(r'(?i)successful.*login.*(\S+)', description='CRITICAL: Successful HTTP authentication for user: {match1}')
		self.add_pattern(r'(?i)401.*unauthorized', description='INFO: HTTP 401 Unauthorized - authentication required')
		self.add_pattern(r'(?i)403.*forbidden', description='INFO: HTTP 403 Forbidden - access denied')
		self.add_pattern(r'(?i)200.*ok.*login|dashboard|admin', description='WARNING: HTTP 200 OK - possible successful authentication')
		self.add_pattern(r'(?i)302.*found.*dashboard|admin|home', description='WARNING: HTTP 302 redirect - possible successful authentication')

	def manual(self, service, plugin_was_run):
		# Get wordlist paths from WordlistManager
		try:
			wordlist_manager = get_wordlist_manager()
			current_size = wordlist_manager.get_wordlist_size()
			username_wordlist = wordlist_manager.get_wordlist_path('usernames', config.get('data_dir'), current_size)
			password_wordlist = wordlist_manager.get_wordlist_path('passwords', config.get('data_dir'), current_size)
			
			if not username_wordlist or not os.path.exists(username_wordlist):
				service.add_manual_command('HTTP bruteforce requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No username wordlist available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
				return
				
			if not password_wordlist or not os.path.exists(password_wordlist):
				service.add_manual_command('HTTP bruteforce requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No password wordlist available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
				return
		except Exception:
			service.add_manual_command('HTTP bruteforce requires WordlistManager configuration:', [
				'# WordlistManager not available. Please check configuration.'
			])
			return
		
		service.add_manual_commands('Credential bruteforcing commands (don\'t run these without modifying them):', [
			'hydra -L "' + username_wordlist + '" -P "' + password_wordlist + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_{http_scheme}_auth_hydra.txt" {http_scheme}-get://{addressv6}/path/to/auth/area',
			'medusa -U "' + username_wordlist + '" -P "' + password_wordlist + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_{http_scheme}_auth_medusa.txt" -M http -h {addressv6} -m DIR:/path/to/auth/area',
			'hydra -L "' + username_wordlist + '" -P "' + password_wordlist + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_{http_scheme}_form_hydra.txt" {http_scheme}-post-form://{addressv6}/path/to/login.php:"username=^USER^&password=^PASS^":"invalid-login-message"',
			'medusa -U "' + username_wordlist + '" -P "' + password_wordlist + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_{http_scheme}_form_medusa.txt" -M web-form -h {addressv6} -m FORM:/path/to/login.php -m FORM-DATA:"post?username=&password=" -m DENY-SIGNAL:"invalid login message"'
		])
