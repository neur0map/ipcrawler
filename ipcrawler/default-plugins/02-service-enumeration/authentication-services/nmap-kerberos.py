from ipcrawler.plugins import ServiceScan

class NmapKerberos(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap Kerberos"
		self.tags = ['default', 'safe', 'kerberos', 'active-directory']

	def configure(self):
		self.match_service_name(['^kerberos', '^kpasswd'])
		# Pattern matching for Kerberos findings
		self.add_pattern(r'(?i)kerberos.*realm[:\s]*([^\n\r]+)', description='Kerberos Realm: {match1}')
		self.add_pattern(r'(?i)valid.*user[s]?[:\s]*([^\n\r]+)', description='Valid Kerberos Users Found: {match1}')
		self.add_pattern(r'(?i)principal[s]?[:\s]*([^\n\r]+)', description='Kerberos Principals: {match1}')
		self.add_pattern(r'(?i)pre.*auth.*disabled', description='CRITICAL: Kerberos Pre-Authentication Disabled - ASREPRoast attack possible')

	async def run(self, service):
		if self.get_global('domain') and self.get_global('username-wordlist'):
			await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,krb5-enum-users" --script-args krb5-enum-users.realm="' + self.get_global('domain') + '",userdb="' + self.get_global('username-wordlist') + '" -oN "{scandir}/{protocol}_{port}_kerberos_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_kerberos_nmap.xml" {address}', outfile='{protocol}_{port}_kerberos_nmap.txt')
		else:
			await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,krb5-enum-users" -oN "{scandir}/{protocol}_{port}_kerberos_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_kerberos_nmap.xml" {address}', outfile='{protocol}_{port}_kerberos_nmap.txt')
