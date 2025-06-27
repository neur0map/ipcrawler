from ipcrawler.plugins import ServiceScan

class NmapIrc(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap IRC'
		self.tags = ['default', 'safe', 'irc']

	def configure(self):
		self.match_service_name('^irc')
		# Pattern matching for IRC findings
		self.add_pattern(r'(?i)irc.*server[:\s]*([^\n\r]+)', description='IRC Server: {match1}')
		self.add_pattern(r'(?i)botnet.*channels[:\s]*([^\n\r]+)', description='CRITICAL: IRC Botnet Channels: {match1}')
		self.add_pattern(r'(?i)unrealircd.*backdoor', description='CRITICAL: UnrealIRCd backdoor detected')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV --script irc-botnet-channels,irc-info,irc-unrealircd-backdoor -oN "{scandir}/{protocol}_{port}_irc_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_irc_nmap.xml" -p {port} {address}', outfile='{protocol}_{port}_irc_nmap.txt')
