from ipcrawler.plugins import ServiceScan

class NmapDistccd(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap distccd"
		self.tags = ['default', 'safe', 'distccd']

	def configure(self):
		self.match_service_name('^distccd')
		# Pattern matching for distccd findings
		self.add_pattern(r'(?i)distcc.*version[:\s]*([^\n\r]+)', description='DistCC Version: {match1}')
		self.add_pattern(r'(?i)cve.2004.2687.*vulnerable', description='CRITICAL: DistCC CVE-2004-2687 vulnerability detected - RCE possible')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,distcc-cve2004-2687" --script-args="distcc-cve2004-2687.cmd=id" -oN "{scandir}/{protocol}_{port}_distcc_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_distcc_nmap.xml" {address}', outfile='{protocol}_{port}_distcc_nmap.txt')
