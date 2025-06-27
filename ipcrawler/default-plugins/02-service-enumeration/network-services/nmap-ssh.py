from ipcrawler.plugins import ServiceScan

class NmapSSH(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap SSH"
		self.description = "SSH service enumeration using nmap scripts"
		self.tags = ['default', 'safe', 'ssh']

	def configure(self):
		self.match_service_name('^ssh')
		# Pattern matching for SSH findings
		self.add_pattern(r'(?i)ssh.*version[:\s]*([^\n\r]+)', description='SSH Version: {match1}')
		self.add_pattern(r'(?i)host.*key[:\s]*([^\n\r]+)', description='SSH Host Key: {match1}')
		self.add_pattern(r'(?i)authentication.*methods[:\s]*([^\n\r]+)', description='SSH Auth Methods: {match1}')
		self.add_pattern(r'(?i)password.*authentication.*disabled', description='SSH password authentication disabled - key-based only')
		self.add_pattern(r'(?i)root.*login.*enabled', description='CRITICAL: SSH root login enabled')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,ssh2-enum-algos,ssh-hostkey,ssh-auth-methods" -oN "{scandir}/{protocol}_{port}_ssh_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_ssh_nmap.xml" {address}', outfile='{protocol}_{port}_ssh_nmap.txt')
