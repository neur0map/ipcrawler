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
