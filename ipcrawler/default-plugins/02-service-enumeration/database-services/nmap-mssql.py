from ipcrawler.plugins import ServiceScan

class NmapMSSQL(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap MSSQL"
		self.tags = ['default', 'safe', 'databases']

	def configure(self):
		self.match_service_name([r'^mssql', r'^ms\-sql'])
		# Pattern matching for MSSQL findings
		self.add_pattern(r'(?i)mssql.*version[:\s]*([^\n\r]+)', description='MSSQL Version: {match1}')
		self.add_pattern(r'(?i)database[s]?[:\s]*([^\n\r]+)', description='MSSQL Databases: {match1}')
		self.add_pattern(r'(?i)sa.*login.*enabled', description='CRITICAL: MSSQL SA account enabled')
		self.add_pattern(r'(?i)xp_cmdshell.*enabled', description='CRITICAL: MSSQL xp_cmdshell enabled - command execution possible')

	def manual(self, service, plugin_was_run):
		if service.target.ipversion == 'IPv4':
			service.add_manual_command('(sqsh) interactive database shell:', 'sqsh -U <username> -P <password> -S {address}:{port}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(ms-sql* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" --script-args="mssql.instance-port={port},mssql.username=sa,mssql.password=sa" -oN "{scandir}/{protocol}_{port}_mssql_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_mssql_nmap.xml" {address}', outfile='{protocol}_{port}_mssql_nmap.txt')
