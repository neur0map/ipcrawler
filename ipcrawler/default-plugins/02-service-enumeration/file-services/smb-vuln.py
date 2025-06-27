from ipcrawler.plugins import ServiceScan

class SMBVuln(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "SMB Vulnerabilities"
		self.tags = ['unsafe', 'smb', 'active-directory']

	def configure(self):
		self.match_service_name([r'^smb', r'^microsoft\-ds', r'^netbios'])
		# Pattern matching for SMB vulnerability findings
		self.add_pattern(r'(?i)ms17.010.*vulnerable', description='CRITICAL: MS17-010 (EternalBlue) vulnerability detected')
		self.add_pattern(r'(?i)ms08.067.*vulnerable', description='CRITICAL: MS08-067 vulnerability detected')
		self.add_pattern(r'(?i)cve.\d{4}.\d+.*vulnerable', description='CRITICAL: SMB CVE vulnerability detected: {match0}')
		self.add_pattern(r'(?i)smb.*vulnerable.*to[:\s]*([^\n\r]+)', description='CRITICAL: SMB Vulnerability: {match1}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -sV -p {port} --script="smb-vuln-*" --script-args="unsafe=1" -oN "{scandir}/{protocol}_{port}_smb_vulnerabilities.txt" -oX "{scandir}/xml/{protocol}_{port}_smb_vulnerabilities.xml" {address}', outfile='{protocol}_{port}_smb_vulnerabilities.txt')

	def manual(self, service, plugin_was_run):
		if not plugin_was_run: # Only suggest these if they weren't run.
			service.add_manual_commands('Nmap scans for SMB vulnerabilities that could potentially cause a DoS if scanned (according to Nmap). Be careful:', 'nmap {nmap_extra} -sV -p {port} --script="smb-vuln-* and dos" --script-args="unsafe=1" -oN "{scandir}/{protocol}_{port}_smb_vulnerabilities.txt" -oX "{scandir}/xml/{protocol}_{port}_smb_vulnerabilities.xml" {address}')
