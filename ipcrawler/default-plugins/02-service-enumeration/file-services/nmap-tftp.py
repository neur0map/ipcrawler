from ipcrawler.plugins import ServiceScan

class NmapTFTP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap TFTP'
		self.tags = ['default', 'safe', 'tftp']

	def configure(self):
		self.match_service_name('^tftp')
		# Pattern matching for TFTP findings
		self.add_pattern(r'(?i)tftp.*version[:\s]*([^\n\r]+)', description='TFTP Version: {match1}')
		self.add_pattern(r'(?i)tftp.*files[:\s]*([^\n\r]+)', description='TFTP Files: {match1}')
		self.add_pattern(r'(?i)read.*access.*enabled', description='TFTP read access enabled')
		self.add_pattern(r'(?i)write.*access.*enabled', description='CRITICAL: TFTP write access enabled')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,tftp-enum" -oN "{scandir}/{protocol}_{port}_tftp-nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_tftp_nmap.xml" {address}', outfile='{protocol}_{port}_tftp-nmap.txt')
