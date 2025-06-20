from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config

class BruteforceSSH(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Bruteforce SSH"
		self.tags = ['default', 'ssh']

	def configure(self):
		self.match_service_name('ssh')

	def manual(self, service, plugin_was_run):
		# Get wordlist paths using WordlistManager
		try:
			wordlist_manager = get_wordlist_manager()
			username_wordlist = wordlist_manager.get_wordlist_path('usernames', config.get('data_dir')) or self.get_global('username_wordlist', default='/usr/share/seclists/Usernames/top-usernames-shortlist.txt')
			password_wordlist = wordlist_manager.get_wordlist_path('passwords', config.get('data_dir')) or self.get_global('password_wordlist', default='/usr/share/seclists/Passwords/darkweb2017-top100.txt')
		except:
			# Fallback to global configuration if WordlistManager isn't available
			username_wordlist = self.get_global('username_wordlist', default='/usr/share/seclists/Usernames/top-usernames-shortlist.txt')
			password_wordlist = self.get_global('password_wordlist', default='/usr/share/seclists/Passwords/darkweb2017-top100.txt')
		
		service.add_manual_command('Bruteforce logins:', [
			'hydra -L "' + username_wordlist + '" -P "' + password_wordlist + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_ssh_hydra.txt" ssh://{addressv6}',
			'medusa -U "' + username_wordlist + '" -P "' + password_wordlist + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_ssh_medusa.txt" -M ssh -h {addressv6}'
		])
