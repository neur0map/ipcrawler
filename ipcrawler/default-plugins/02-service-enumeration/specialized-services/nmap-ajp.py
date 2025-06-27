from ipcrawler.plugins import ServiceScan

class NmapAJP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap AJP'
		self.tags = ['default', 'safe', 'ajp']

	def configure(self):
		self.match_service_name(['^ajp13'])
		# Pattern matching for AJP findings
		self.add_pattern(r'(?i)ajp.*version[:\s]*([^\n\r]+)', description='Apache JServ Protocol (AJP) Version: {match1}')
		self.add_pattern(r'(?i)tomcat.*detected', description='Apache Tomcat detected via AJP')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(ajp-* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_ajp_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_ajp_nmap.xml" {address}', outfile='{protocol}_{port}_ajp_nmap.txt')
