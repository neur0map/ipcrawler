from ipcrawler.plugins import ServiceScan

class NmapSIP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap SIP"
		self.tags = ['default', 'safe', 'sip']

	def configure(self):
		self.match_service_name(['^asterisk', '^sip'])
		# Pattern matching for SIP findings
		self.add_pattern(r'(?i)sip.*version[:\s]*([^\n\r]+)', description='SIP Version: {match1}')
		self.add_pattern(r'(?i)user[s]?.*found[:\s]*([^\n\r]+)', description='SIP Users Found: {match1}')
		self.add_pattern(r'(?i)sip.*methods[:\s]*([^\n\r]+)', description='SIP Methods: {match1}')
		self.add_pattern(r'(?i)asterisk.*detected', description='Asterisk PBX detected - VoIP system')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,sip-enum-users,sip-methods" -oN "{scandir}/{protocol}_{port}_sip_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_sip_nmap.xml" {address}', outfile='{protocol}_{port}_sip_nmap.txt')
