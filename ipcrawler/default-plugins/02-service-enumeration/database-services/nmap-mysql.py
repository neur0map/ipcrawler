from ipcrawler.plugins import ServiceScan

class NmapMYSQL(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap MYSQL"
		self.description = "MySQL database enumeration using nmap scripts"
		self.tags = ['default', 'safe', 'databases']

	def configure(self):
		self.match_service_name('^mysql')
		# Pattern matching for MySQL findings
		self.add_pattern(r'(?i)mysql.*version[:\s]*([^\n\r]+)', description='MySQL Version: {match1}')
		self.add_pattern(r'(?i)database[s]?[:\s]*([^\n\r]+)', description='MySQL Databases: {match1}')
		self.add_pattern(r'(?i)user[s]?[:\s]*([^\n\r]+)', description='MySQL Users: {match1}')
		self.add_pattern(r'(?i)anonymous.*access.*enabled', description='CRITICAL: MySQL anonymous access enabled')
		self.add_pattern(r'(?i)ssl.*enabled', description='MySQL SSL/TLS enabled - encrypted connections supported')

	def manual(self, service, plugin_was_run):
		if service.target.ipversion == 'IPv4':
			service.add_manual_command('(sqsh) interactive database shell:', 'sqsh -U <username> -P <password> -S {address}:{port}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(mysql* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_mysql_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_mysql_nmap.xml" {address}', outfile='{protocol}_{port}_mysql_nmap.txt')
