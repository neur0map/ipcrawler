from ipcrawler.plugins import ServiceScan

class NmapCassandra(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap Cassandra"
		self.tags = ['default', 'safe', 'cassandra']

	def configure(self):
		self.match_service_name('^apani1')
		# Pattern matching for Cassandra findings
		self.add_pattern(r'(?i)cassandra.*version[:\s]*([^\n\r]+)', description='Cassandra Version: {match1}')
		self.add_pattern(r'(?i)cluster.*name[:\s]*([^\n\r]+)', description='Cassandra Cluster: {match1}')
		self.add_pattern(r'(?i)keyspace[s]?[:\s]*([^\n\r]+)', description='Cassandra Keyspaces: {match1}')
		self.add_pattern(r'(?i)authentication.*disabled', description='CRITICAL: Cassandra authentication disabled')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(cassandra* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_cassandra_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_cassandra_nmap.xml" {address}', outfile='{protocol}_{port}_cassandra_nmap.txt')
