from ipcrawler.plugins import ServiceScan

class NmapTelnet(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap Telnet'
		self.tags = ['default', 'safe', 'telnet']

	def configure(self):
		self.match_service_name('^telnet')
		# Pattern matching for Telnet findings
		self.add_pattern(r'(?i)telnet.*version[:\s]*([^\n\r]+)', description='Telnet Version: {match1}')
		self.add_pattern(r'(?i)encryption.*enabled', description='Telnet encryption enabled')
		self.add_pattern(r'(?i)encryption.*disabled', description='CRITICAL: Telnet encryption disabled - plaintext communication')
		self.add_pattern(r'(?i)ntlm.*authentication', description='Telnet NTLM authentication detected')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,telnet-encryption,telnet-ntlm-info" -oN "{scandir}/{protocol}_{port}_telnet-nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_telnet_nmap.xml" {address}', outfile='{protocol}_{port}_telnet-nmap.txt')
