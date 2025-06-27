from ipcrawler.plugins import ServiceScan

class NmapRsync(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap Rsync'
		self.tags = ['default', 'safe', 'rsync']

	def configure(self):
		self.match_service_name('^rsync')
		# Pattern matching for Rsync findings
		self.add_pattern(r'(?i)rsync.*version[:\s]*([^\n\r]+)', description='Rsync Version: {match1}')
		self.add_pattern(r'(?i)modules[:\s]*([^\n\r]+)', description='Rsync Modules: {match1}')
		self.add_pattern(r'(?i)anonymous.*access.*enabled', description='CRITICAL: Rsync anonymous access enabled')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(rsync* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_rsync_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_rsync_nmap.xml" {address}', outfile='{protocol}_{port}_rsync_nmap.txt')
