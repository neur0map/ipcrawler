from ipcrawler.plugins import ServiceScan

class NmapSMB(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap SMB"
		self.description = "SMB service enumeration using nmap scripts"
		self.tags = ['default', 'safe', 'smb', 'active-directory']

	def configure(self):
		self.match_service_name([r'^smb', r'^microsoft\-ds', r'^netbios'])
		# Pattern matching for SMB findings
		self.add_pattern(r'(?i)smb.*version[:\s]*([^\n\r]+)', description='SMB Version: {match1}')
		self.add_pattern(r'(?i)workgroup[:\s]*([^\n\r]+)', description='SMB Workgroup: {match1}')
		self.add_pattern(r'(?i)domain[:\s]*([^\n\r]+)', description='SMB Domain: {match1}')
		self.add_pattern(r'(?i)shares[:\s]*([^\n\r]+)', description='SMB Shares: {match1}')
		self.add_pattern(r'(?i)anonymous.*access.*enabled', description='CRITICAL: SMB anonymous access enabled')
		self.add_pattern(r'(?i)signing.*disabled', description='CRITICAL: SMB signing disabled - relay attacks possible')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(nbstat or smb* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_smb_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_smb_nmap.xml" {address}', outfile='{protocol}_{port}_smb_nmap.txt')
