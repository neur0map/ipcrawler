from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os

class BruteforceRDP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Bruteforce RDP"
		self.tags = ['default', 'rdp']

	def configure(self):
		self.match_service_name([r'^rdp', r'^ms\-wbt\-server', r'^ms\-term\-serv'])
		
		# Add patterns for RDP bruteforce result detection
		self.add_pattern(r'(?i)login:\s*(\S+)\s+password:\s*(\S+)', description='CRITICAL: RDP credentials found - User: {match1}, Password: {match2}')
		self.add_pattern(r'(?i)valid password for\s+(\S+)', description='CRITICAL: Valid RDP password found for user: {match1}')
		self.add_pattern(r'(?i)successful login.*user[:\s]+(\S+)', description='CRITICAL: Successful RDP login for user: {match1}')
		self.add_pattern(r'(?i)account.*lockout.*(\S+)', description='WARNING: RDP account lockout for user: {match1}')
		self.add_pattern(r'(?i)authentication.*failed|access.*denied', description='INFO: RDP authentication failed')
		self.add_pattern(r'(?i)connection.*refused|timeout', description='WARNING: RDP service connectivity issues')
		self.add_pattern(r'(?i)network.*level.*authentication.*required', description='INFO: RDP Network Level Authentication enabled')

	def manual(self, service, plugin_was_run):
		# Get wordlist paths from WordlistManager
		try:
			wordlist_manager = get_wordlist_manager()
			current_size = wordlist_manager.get_wordlist_size()
			username_wordlist = wordlist_manager.get_wordlist_path('usernames', config.get('data_dir'), current_size)
			password_wordlist = wordlist_manager.get_wordlist_path('passwords', config.get('data_dir'), current_size)
			
			if not username_wordlist or not os.path.exists(username_wordlist):
				service.add_manual_command('RDP bruteforce requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No username wordlist available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
				return
				
			if not password_wordlist or not os.path.exists(password_wordlist):
				service.add_manual_command('RDP bruteforce requires wordlists - Install SecLists or configure custom wordlists:', [
					'# No password wordlist available. Install SecLists: apt install seclists',
					'# Or configure custom wordlists in WordlistManager'
				])
				return
		except Exception:
			service.add_manual_command('RDP bruteforce requires WordlistManager configuration:', [
				'# WordlistManager not available. Please check configuration.'
			])
			return
		
		service.add_manual_commands('Bruteforce logins:', [
			'hydra -L "' + username_wordlist + '" -P "' + password_wordlist + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_rdp_hydra.txt" rdp://{addressv6}',
			'medusa -U "' + username_wordlist + '" -P "' + password_wordlist + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_rdp_medusa.txt" -M rdp -h {addressv6}'
		])
