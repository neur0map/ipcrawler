from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os

class BruteforceSMB(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Bruteforce SMB'
		self.tags = ['default', 'safe', 'active-directory']

	def configure(self):
		self.match_service('tcp', 445, r'^microsoft\-ds')
		self.match_service('tcp', 139, r'^netbios')
		
		# Add patterns for SMB bruteforce result detection
		self.add_pattern(r'(?i)login:\s*(\S+)\s+password:\s*(\S+)', description='CRITICAL: SMB credentials found - User: {match1}, Password: {match2}')
		self.add_pattern(r'(?i)(\S+):\S+\s+\[.*\+.*\]', description='CRITICAL: SMB authentication successful for user: {match1}')
		self.add_pattern(r'(?i)pwned!.*(\S+)', description='CRITICAL: SMB admin access gained for user: {match1}')
		self.add_pattern(r'(?i)STATUS_LOGON_FAILURE', description='INFO: SMB authentication failed')
		self.add_pattern(r'(?i)STATUS_PASSWORD_EXPIRED.*(\S+)', description='WARNING: SMB password expired for user: {match1}')
		self.add_pattern(r'(?i)STATUS_ACCOUNT_LOCKED_OUT.*(\S+)', description='WARNING: SMB account locked for user: {match1}')
		self.add_pattern(r'(?i)guest.*allowed|anonymous.*login', description='WARNING: SMB guest or anonymous access allowed')

	def manual(self, service, plugin_was_run):
		# Get wordlist paths from WordlistManager
		try:
			wordlist_manager = get_wordlist_manager()
			current_size = wordlist_manager.get_wordlist_size()
			username_wordlist = wordlist_manager.get_wordlist_path('usernames', config.get('data_dir'), current_size)
			password_wordlist = wordlist_manager.get_wordlist_path('passwords', config.get('data_dir'), current_size)
			
			if not username_wordlist or not os.path.exists(username_wordlist) or not password_wordlist or not os.path.exists(password_wordlist):
				service.add_manual_command('SMB bruteforce requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No wordlists available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
				return
		except Exception:
			service.add_manual_command('SMB bruteforce requires WordlistManager configuration:', [
				'# WordlistManager not available. Please check configuration.'
			])
			return
		
		service.add_manual_command('Bruteforce SMB', [
			'crackmapexec smb {address} --port={port} -u "' + username_wordlist + '" -p "' + password_wordlist + '"'
		])
