from ipcrawler.plugins import ServiceScan

class NmapSNMP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap SNMP"
		self.tags = ['default', 'safe', 'snmp']

	def configure(self):
		self.match_service_name('^snmp')
		# Pattern matching for SNMP findings
		self.add_pattern(r'(?i)snmp.*version[:\s]*([^\n\r]+)', description='SNMP Version: {match1}')
		self.add_pattern(r'(?i)community.*string[s]?[:\s]*([^\n\r]+)', description='SNMP Community Strings: {match1}')
		self.add_pattern(r'(?i)public.*community', description='CRITICAL: SNMP public community string detected')
		self.add_pattern(r'(?i)system.*info[:\s]*([^\n\r]+)', description='SNMP System Info: {match1}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(snmp* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_snmp-nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_snmp_nmap.xml" {address}', outfile='{protocol}_{port}_snmp-nmap.txt')
