from ipcrawler.plugins import ServiceScan

class NmapCUPS(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap CUPS"
		self.tags = ['default', 'safe', 'cups']

	def configure(self):
		self.match_service_name('^ipp')
		# Pattern matching for CUPS findings
		self.add_pattern(r'(?i)cups.*version[:\s]*([^\n\r]+)', description='CUPS Version: {match1}')
		self.add_pattern(r'(?i)printer[s]?.*queue[s]?[:\s]*([^\n\r]+)', description='CUPS Printer Queues: {match1}')
		self.add_pattern(r'(?i)ipp.*enabled', description='Internet Printing Protocol (IPP) enabled')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(cups* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_cups_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_cups_nmap.xml" {address}', outfile='{protocol}_{port}_cups_nmap.txt')
