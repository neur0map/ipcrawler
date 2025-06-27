from ipcrawler.plugins import ServiceScan

class NmapIMAP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap IMAP"
		self.tags = ['default', 'safe', 'imap', 'email']

	def configure(self):
		self.match_service_name('^imap')
		# Pattern matching for IMAP findings
		self.add_pattern(r'(?i)imap.*version[:\s]*([^\n\r]+)', description='IMAP Version: {match1}')
		self.add_pattern(r'(?i)mail.*server[:\s]*([^\n\r]+)', description='IMAP Mail Server: {match1}')
		self.add_pattern(r'(?i)starttls.*enabled', description='IMAP StartTLS enabled - encrypted email supported')
		self.add_pattern(r'(?i)capabilities[:\s]*([^\n\r]+)', description='IMAP Capabilities: {match1}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(imap* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_imap_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_imap_nmap.xml" {address}', outfile='{protocol}_{port}_imap_nmap.txt')
