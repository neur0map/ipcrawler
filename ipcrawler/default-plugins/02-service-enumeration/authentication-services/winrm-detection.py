from ipcrawler.plugins import ServiceScan
from ipcrawler.io import fformat
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os

class WinRMDetection(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'WinRM Detection'
		self.tags = ['default', 'safe', 'winrm']

	def configure(self):
		self.match_service_name('^wsman')
		self.match_service('tcp', [5985, 5986], '^http')

	async def run(self, service):
		filename = fformat('{scandir}/{protocol}_{port}_winrm-detection.txt')
		with open(filename, mode='wt', encoding='utf8') as winrm:
			winrm.write('WinRM was possibly detected running on ' + service.protocol + ' port ' + str(service.port) + '.\nCheck _manual_commands.txt for manual commands you can run against this service.')

	def manual(self, service, plugin_was_run):
		# Get wordlist paths from WordlistManager
		try:
			wordlist_manager = get_wordlist_manager()
			current_size = wordlist_manager.get_wordlist_size()
			username_wordlist = wordlist_manager.get_wordlist_path('usernames', config.get('data_dir'), current_size)
			password_wordlist = wordlist_manager.get_wordlist_path('passwords', config.get('data_dir'), current_size)
			
			if not username_wordlist or not os.path.exists(username_wordlist):
				service.add_manual_command('WinRM bruteforce requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No username wordlist available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
			elif not password_wordlist or not os.path.exists(password_wordlist):
				service.add_manual_command('WinRM bruteforce requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No password wordlist available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
			else:
				service.add_manual_commands('Bruteforce logins:', [
					'crackmapexec winrm {address} -d \'' + self.get_global('domain', default='<domain>') + '\' -u \'' + username_wordlist + '\' -p \'' + password_wordlist + '\''
				])
		except Exception:
			service.add_manual_command('WinRM bruteforce requires WordlistManager configuration:', [
				'# WordlistManager not available. Please check configuration.'
			])

		service.add_manual_commands('Check login (requires credentials):', [
			'crackmapexec winrm {address} -d \'' + self.get_global('domain', default='<domain>') + '\' -u \'<username>\' -p \'<password>\''
		])

		service.add_manual_commands('Evil WinRM (gem install evil-winrm):', [
			'evil-winrm -u \'<user>\' -p \'<password>\' -i {address}',
			'evil-winrm -u \'<user>\' -H \'<hash>\' -i {address}'
		])
