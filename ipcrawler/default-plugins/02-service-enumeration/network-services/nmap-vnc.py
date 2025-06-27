from ipcrawler.plugins import ServiceScan

class NmapVNC(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap VNC'
		self.tags = ['default', 'safe', 'vnc']

	def configure(self):
		self.match_service_name('^vnc')
		# Pattern matching for VNC findings
		self.add_pattern(r'(?i)vnc.*version[:\s]*([^\n\r]+)', description='VNC Version: {match1}')
		self.add_pattern(r'(?i)vnc.*title[:\s]*([^\n\r]+)', description='VNC Desktop Title: {match1}')
		self.add_pattern(r'(?i)password.*required', description='VNC password authentication enabled')
		self.add_pattern(r'(?i)no.*authentication', description='CRITICAL: VNC authentication disabled - open access')
		self.add_pattern(r'(?i)encryption.*enabled', description='VNC encryption enabled')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(vnc* or realvnc* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" --script-args="unsafe=1" -oN "{scandir}/{protocol}_{port}_vnc_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_vnc_nmap.xml" {address}', outfile='{protocol}_{port}_vnc_nmap.txt')
