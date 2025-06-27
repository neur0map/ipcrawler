from ipcrawler.plugins import ServiceScan

class NmapPOP3(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap POP3"
		self.tags = ['default', 'safe', 'pop3', 'email']

	def configure(self):
		self.match_service_name('^pop3')
		# Pattern matching for POP3 findings
		self.add_pattern(r'(?i)pop3.*version[:\s]*([^\n\r]+)', description='POP3 Version: {match1}')
		self.add_pattern(r'(?i)mail.*server[:\s]*([^\n\r]+)', description='POP3 Mail Server: {match1}')
		self.add_pattern(r'(?i)starttls.*enabled', description='POP3 StartTLS enabled - encrypted email supported')
		self.add_pattern(r'(?i)capabilities[:\s]*([^\n\r]+)', description='POP3 Capabilities: {match1}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(pop3* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_pop3_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_pop3_nmap.xml" {address}', outfile='{protocol}_{port}_pop3_nmap.txt')
