from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config

class OneSixtyOne(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "OneSixtyOne"
		self.tags = ['default', 'safe', 'snmp']

	def configure(self):
		self.match_service_name('^snmp')
		self.match_port('udp', 161)
		self.run_once(True)
		# Use WordlistManager to get SNMP community strings wordlist
		try:
			wordlist_manager = get_wordlist_manager()
			snmp_path = wordlist_manager.get_wordlist_path('snmp_communities', config.get('data_dir'))
			default_snmp_path = snmp_path if snmp_path else '/usr/share/seclists/Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt'
		except:
			# Fallback to legacy hardcoded path if WordlistManager isn't available
			default_snmp_path = '/usr/share/seclists/Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt'
		
		self.add_option('community-strings', default=default_snmp_path, help='The file containing a list of community strings to try. Default: %(default)s')

	async def run(self, service):
		if service.target.ipversion == 'IPv4':
			await service.execute('onesixtyone -c ' + self.get_option('community-strings') + ' -dd {address} 2>&1', outfile='{protocol}_{port}_snmp_onesixtyone.txt')
