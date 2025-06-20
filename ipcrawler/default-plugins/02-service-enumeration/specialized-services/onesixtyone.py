from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config
import os

class OneSixtyOne(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "OneSixtyOne"
		self.tags = ['default', 'safe', 'snmp']

	def configure(self):
		self.match_service_name('^snmp')
		self.match_port('udp', 161)
		self.run_once(True)
		# Default to auto-detection - wordlist will be resolved at runtime
		self.add_option('community-strings', default='auto', help='The file containing a list of community strings to try. Use "auto" for automatic SecLists detection, or specify a custom path. Default: %(default)s')

	async def run(self, service):
		if service.target.ipversion == 'IPv4':
			# Resolve wordlist at runtime
			community_strings = self.get_option('community-strings')
			
			if community_strings == 'auto':
				# Auto-detect best available wordlist using configured size preference
				try:
					wordlist_manager = get_wordlist_manager()
					current_size = wordlist_manager.get_wordlist_size()
					snmp_path = wordlist_manager.get_wordlist_path('snmp_communities', config.get('data_dir'), current_size)
					if snmp_path and os.path.exists(snmp_path):
						community_strings = snmp_path
					else:
						service.error(f'No SNMP community strings wordlist found for size "{current_size}". Please install SecLists or configure custom wordlists in WordlistManager.')
						return
				except Exception as e:
					service.error(f'WordlistManager unavailable: {e}. Please install SecLists or configure custom wordlists.')
					return
			else:
				# User specified a custom wordlist path
				if not os.path.exists(community_strings):
					service.warn(f'Community strings file not found: {community_strings}')
					return
			
			await service.execute('onesixtyone -c ' + community_strings + ' -dd {address} 2>&1', outfile='{protocol}_{port}_snmp_onesixtyone.txt')
