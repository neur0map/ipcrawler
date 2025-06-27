from ipcrawler.plugins import ServiceScan

class NmapMongoDB(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap MongoDB"
		self.tags = ['default', 'safe', 'databases']

	def configure(self):
		self.match_service_name('^mongod')
		# Pattern matching for MongoDB findings
		self.add_pattern(r'(?i)mongodb.*version[:\s]*([^\n\r]+)', description='MongoDB Version: {match1}')
		self.add_pattern(r'(?i)database[s]?[:\s]*([^\n\r]+)', description='MongoDB Databases: {match1}')
		self.add_pattern(r'(?i)no.*auth.*required', description='CRITICAL: MongoDB authentication disabled')
		self.add_pattern(r'(?i)ssl.*enabled', description='MongoDB SSL/TLS enabled - encrypted connections supported')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(mongodb* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_mongodb_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_mongodb_nmap.xml" {address}', outfile='{protocol}_{port}_mongodb_nmap.txt')
