from ipcrawler.plugins import ServiceScan

class NmapSMTP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap SMTP"
		self.tags = ['default', 'safe', 'smtp', 'email']

	def configure(self):
		self.match_service_name('^smtp')
		# Pattern matching for SMTP findings
		self.add_pattern(r'(?i)smtp.*version[:\s]*([^\n\r]+)', description='SMTP Version: {match1}')
		self.add_pattern(r'(?i)mail.*server[:\s]*([^\n\r]+)', description='Mail Server: {match1}')
		self.add_pattern(r'(?i)open.*relay', description='CRITICAL: SMTP open relay detected - spam risk')
		self.add_pattern(r'(?i)starttls.*enabled', description='SMTP StartTLS enabled - encrypted email supported')
		self.add_pattern(r'(?i)auth.*methods[:\s]*([^\n\r]+)', description='SMTP Auth Methods: {match1}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(smtp* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_smtp_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_smtp_nmap.xml" {address}', outfile='{protocol}_{port}_smtp_nmap.txt')
