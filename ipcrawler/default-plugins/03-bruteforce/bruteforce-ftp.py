from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os

class BruteforceFTP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Bruteforce FTP"
		self.tags = ['default', 'ftp']

	def configure(self):
		self.match_service_name([r'^ftp', r'^ftp\-data'])
		
		# Add patterns for FTP bruteforce result detection
		self.add_pattern(r'(?i)login:\s*(\S+)\s+password:\s*(\S+)', description='CRITICAL: FTP credentials found - User: {match1}, Password: {match2}')
		self.add_pattern(r'(?i)valid password for\s+(\S+)', description='CRITICAL: Valid FTP password found for user: {match1}')
		self.add_pattern(r'(?i)successful login.*user[:\s]+(\S+)', description='CRITICAL: Successful FTP login for user: {match1}')
		self.add_pattern(r'(?i)230.*login successful', description='CRITICAL: FTP login successful')
		self.add_pattern(r'(?i)331.*password required for\s+(\S+)', description='INFO: FTP user exists, password required: {match1}')
		self.add_pattern(r'(?i)530.*login incorrect|authentication failed', description='INFO: FTP authentication failed')
		self.add_pattern(r'(?i)anonymous.*ftp.*allowed', description='WARNING: Anonymous FTP access allowed')

	def manual(self, service, plugin_was_run):
		# Get wordlist paths from WordlistManager
		try:
			wordlist_manager = get_wordlist_manager()
			current_size = wordlist_manager.get_wordlist_size()
			username_wordlist = wordlist_manager.get_wordlist_path('usernames', config.get('data_dir'), current_size)
			password_wordlist = wordlist_manager.get_wordlist_path('passwords', config.get('data_dir'), current_size)
			
			if not username_wordlist or not os.path.exists(username_wordlist) or not password_wordlist or not os.path.exists(password_wordlist):
				service.add_manual_command('FTP bruteforce requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No wordlists available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
				return
		except Exception:
			service.add_manual_command('FTP bruteforce requires WordlistManager configuration:', [
				'# WordlistManager not available. Please check configuration.'
			])
			return
		
		service.add_manual_commands('Bruteforce logins:', [
			'hydra -L "' + username_wordlist + '" -P "' + password_wordlist + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_ftp_hydra.txt" ftp://{addressv6}',
			'medusa -U "' + username_wordlist + '" -P "' + password_wordlist + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_ftp_medusa.txt" -M ftp -h {addressv6}'
		])
