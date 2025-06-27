from ipcrawler.plugins import ServiceScan

class NmapLDAP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap LDAP"
		self.tags = ['default', 'safe', 'ldap', 'active-directory']

	def configure(self):
		self.match_service_name('^ldap')
		# Pattern matching for LDAP findings
		self.add_pattern(r'(?i)base.*dn[:\s]*([^\n\r]+)', description='LDAP Base DN: {match1}')
		self.add_pattern(r'(?i)naming.*context[s]?[:\s]*([^\n\r]+)', description='LDAP Naming Context: {match1}')
		self.add_pattern(r'(?i)domain.*component[s]?[:\s]*([^\n\r]+)', description='LDAP Domain Components: {match1}')
		self.add_pattern(r'(?i)anonymous.*bind.*enabled', description='CRITICAL: Anonymous LDAP bind enabled - information disclosure risk')
		self.add_pattern(r'(?i)startTLS.*supported', description='LDAP StartTLS supported - encrypted communication available')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(ldap* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_ldap_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_ldap_nmap.xml" {address}', outfile='{protocol}_{port}_ldap_nmap.txt')
