from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os

class SMTPUserEnum(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'SMTP-User-Enum'
		self.tags = ['default', 'safe', 'smtp', 'email']

	def configure(self):
		self.match_service_name('^smtp')

	async def run(self, service):
		# Get wordlist paths from WordlistManager
		try:
			wordlist_manager = get_wordlist_manager()
			current_size = wordlist_manager.get_wordlist_size()
			username_wordlist = wordlist_manager.get_wordlist_path('usernames', config.get('data_dir'), current_size)
			
			if not username_wordlist or not os.path.exists(username_wordlist):
				await service.execute('echo "SMTP user enumeration requires wordlists - Install SecLists or configure custom wordlists"', outfile='{protocol}_{port}_smtp_user-enum_error.txt')
				await service.execute('echo "No username wordlist available. Install SecLists: apt install seclists"', outfile='{protocol}_{port}_smtp_user-enum_error.txt', append=True)
				return
		except Exception:
			await service.execute('echo "SMTP user enumeration requires WordlistManager configuration"', outfile='{protocol}_{port}_smtp_user-enum_error.txt')
			await service.execute('echo "WordlistManager not available. Please check configuration."', outfile='{protocol}_{port}_smtp_user-enum_error.txt', append=True)
			return
		
		await service.execute('hydra smtp-enum://{addressv6}:{port}/vrfy -L "' + username_wordlist + '" 2>&1', outfile='{protocol}_{port}_smtp_user-enum_hydra_vrfy.txt')
		await service.execute('hydra smtp-enum://{addressv6}:{port}/expn -L "' + username_wordlist + '" 2>&1', outfile='{protocol}_{port}_smtp_user-enum_hydra_expn.txt')

	def manual(self, service, plugin_was_run):
		# Get wordlist paths from WordlistManager
		try:
			wordlist_manager = get_wordlist_manager()
			current_size = wordlist_manager.get_wordlist_size()
			username_wordlist = wordlist_manager.get_wordlist_path('usernames', config.get('data_dir'), current_size)
			
			if not username_wordlist or not os.path.exists(username_wordlist):
				service.add_manual_command('SMTP user enumeration requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No username wordlist available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
				return
		except Exception:
			service.add_manual_command('SMTP user enumeration requires WordlistManager configuration:', [
				'# WordlistManager not available. Please check configuration.'
			])
			return
		
		service.add_manual_command('Try User Enumeration using "RCPT TO". Replace <TARGET-DOMAIN> with the target\'s domain name:', [
			'hydra smtp-enum://{addressv6}:{port}/rcpt -L "' + username_wordlist + '" -o "{scandir}/{protocol}_{port}_smtp_user-enum_hydra_rcpt.txt" -p <TARGET-DOMAIN>'
		])
