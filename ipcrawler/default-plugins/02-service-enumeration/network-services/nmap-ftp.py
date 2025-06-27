from ipcrawler.plugins import ServiceScan

class NmapFTP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap FTP'
		self.description = "FTP service enumeration using nmap scripts"
		self.tags = ['default', 'safe', 'ftp']

	def configure(self):
		self.match_service_name([r'^ftp', r'^ftp\-data'])
		# Pattern matching for FTP findings
		self.add_pattern(r'(?i)ftp.*version[:\s]*([^\n\r]+)', description='FTP Version: {match1}')
		self.add_pattern(r'(?i)anonymous.*ftp.*allowed', description='CRITICAL: Anonymous FTP access enabled')
		self.add_pattern(r'(?i)ftp.*bounce.*enabled', description='CRITICAL: FTP bounce attack possible')
		self.add_pattern(r'(?i)ssl.*tls.*enabled', description='FTP SSL/TLS (FTPS) enabled - encrypted transfers supported')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(ftp* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_ftp_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_ftp_nmap.xml" {address}', outfile='{protocol}_{port}_ftp_nmap.txt')
