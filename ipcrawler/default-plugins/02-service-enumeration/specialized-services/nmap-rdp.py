from ipcrawler.plugins import ServiceScan

class NmapRDP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap RDP"
		self.tags = ['default', 'safe', 'rdp']

	def configure(self):
		self.match_service_name([r'^rdp', r'^ms\-wbt\-server', r'^ms\-term\-serv'])
		# Pattern matching for RDP findings
		self.add_pattern(r'(?i)rdp.*version[:\s]*([^\n\r]+)', description='RDP Version: {match1}')
		self.add_pattern(r'(?i)nla.*enabled', description='RDP Network Level Authentication enabled')
		self.add_pattern(r'(?i)nla.*disabled', description='CRITICAL: RDP NLA disabled - weaker authentication')
		self.add_pattern(r'(?i)ssl.*enabled', description='RDP SSL/TLS encryption enabled')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(rdp* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_rdp_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_rdp_nmap.xml" {address}', outfile='{protocol}_{port}_rdp_nmap.txt')
