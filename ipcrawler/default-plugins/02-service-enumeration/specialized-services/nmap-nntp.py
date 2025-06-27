from ipcrawler.plugins import ServiceScan

class NmapNNTP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap NNTP"
		self.tags = ['default', 'safe', 'nntp']

	def configure(self):
		self.match_service_name('^nntp')
		# Pattern matching for NNTP findings
		self.add_pattern(r'(?i)nntp.*version[:\s]*([^\n\r]+)', description='NNTP Version: {match1}')
		self.add_pattern(r'(?i)newsgroup[s]?[:\s]*([^\n\r]+)', description='NNTP Newsgroups: {match1}')
		self.add_pattern(r'(?i)ntlm.*authentication', description='NNTP NTLM authentication detected')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,nntp-ntlm-info" -oN "{scandir}/{protocol}_{port}_nntp_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_nntp_nmap.xml" {address}', outfile='{protocol}_{port}_nntp_nmap.txt')
