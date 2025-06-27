from ipcrawler.plugins import ServiceScan

class NmapOracle(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap Oracle"
		self.tags = ['default', 'safe', 'databases']

	def configure(self):
		self.match_service_name('^oracle')
		# Pattern matching for Oracle findings
		self.add_pattern(r'(?i)oracle.*version[:\s]*([^\n\r]+)', description='Oracle Version: {match1}')
		self.add_pattern(r'(?i)sid[:\s]*([^\n\r]+)', description='Oracle SID: {match1}')
		self.add_pattern(r'(?i)service.*name[s]?[:\s]*([^\n\r]+)', description='Oracle Service Names: {match1}')
		self.add_pattern(r'(?i)tns.*listener', description='Oracle TNS Listener detected')

	def manual(self, service, plugin_was_run):
		service.add_manual_command('Brute-force SIDs using Nmap:', 'nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,oracle-sid-brute" -oN "{scandir}/{protocol}_{port}_oracle_sid-brute_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_oracle_sid-brute_nmap.xml" {address}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(oracle* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_oracle_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_oracle_nmap.xml" {address}', outfile='{protocol}_{port}_oracle_nmap.txt')
