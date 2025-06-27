from ipcrawler.plugins import ServiceScan

class NmapNTP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap NTP"
		self.tags = ['default', 'safe', 'ntp']

	def configure(self):
		self.match_service_name('^ntp')
		# Pattern matching for NTP findings
		self.add_pattern(r'(?i)ntp.*version[:\s]*([^\n\r]+)', description='NTP Version: {match1}')
		self.add_pattern(r'(?i)ntp.*info[:\s]*([^\n\r]+)', description='NTP Server Info: {match1}')
		self.add_pattern(r'(?i)monlist.*enabled', description='CRITICAL: NTP monlist enabled - amplification attack possible')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(ntp* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_ntp_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_ntp_nmap.xml" {address}', outfile='{protocol}_{port}_ntp_nmap.txt')
