from ipcrawler.plugins import ServiceScan

class NmapDNS(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap DNS'
		self.tags = ['default', 'safe', 'dns']

	def configure(self):
		self.match_service_name('^domain')
		# Pattern matching for DNS findings
		self.add_pattern(r'(?i)dns.*version[:\s]*([^\n\r]+)', description='DNS Server Version: {match1}')
		self.add_pattern(r'(?i)bind.*version[:\s]*([^\n\r]+)', description='BIND Version: {match1}')
		self.add_pattern(r'(?i)zone.*transfer.*allowed', description='CRITICAL: DNS zone transfer allowed - information disclosure')
		self.add_pattern(r'(?i)recursion.*enabled', description='DNS recursion enabled - potential amplification attacks')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(dns* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_dns_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_dns_nmap.xml" {address}', outfile='{protocol}_{port}_dns_nmap.txt')
