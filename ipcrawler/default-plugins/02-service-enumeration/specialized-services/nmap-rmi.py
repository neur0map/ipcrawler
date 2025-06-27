from ipcrawler.plugins import ServiceScan

class NmapRMI(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap RMI"
		self.tags = ['default', 'safe', 'rmi']

	def configure(self):
		self.match_service_name([r'^java\-rmi', r'^rmiregistry'])
		# Pattern matching for RMI findings
		self.add_pattern(r'(?i)rmi.*registry[:\s]*([^\n\r]+)', description='RMI Registry: {match1}')
		self.add_pattern(r'(?i)java.*rmi[:\s]*([^\n\r]+)', description='Java RMI Service: {match1}')
		self.add_pattern(r'(?i)classloader.*vulnerable', description='CRITICAL: RMI vulnerable classloader detected')
		self.add_pattern(r'(?i)remote.*objects[:\s]*([^\n\r]+)', description='RMI Remote Objects: {match1}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,rmi-vuln-classloader,rmi-dumpregistry" -oN "{scandir}/{protocol}_{port}_rmi_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_rmi_nmap.xml" {address}', outfile='{protocol}_{port}_rmi_nmap.txt')
