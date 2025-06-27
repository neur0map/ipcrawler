from ipcrawler.plugins import ServiceScan

class NmapRedis(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap Redis'
		self.tags = ['default', 'safe', 'redis']

	def configure(self):
		self.match_service_name('^redis$')
		# Pattern matching for Redis findings
		self.add_pattern(r'(?i)redis.*version[:\s]*([^\n\r]+)', description='Redis Version: {match1}')
		self.add_pattern(r'(?i)redis.*mode[:\s]*([^\n\r]+)', description='Redis Mode: {match1}')
		self.add_pattern(r'(?i)no.*auth.*required', description='CRITICAL: Redis authentication disabled - unauthorized access possible')
		self.add_pattern(r'(?i)config.*rewrite.*enabled', description='Redis config rewrite enabled - potential persistence mechanism')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,redis-info" -oN "{scandir}/{protocol}_{port}_redis_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_redis_nmap.xml" {address}', outfile='{protocol}_{port}_redis_nmap.txt')
