from ipcrawler.plugins import ServiceScan

class NmapMulticastDNS(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Nmap Multicast DNS'
		self.tags = ['default', 'safe', 'dns']

	def configure(self):
		self.match_service_name(['^mdns', '^zeroconf'])
		# Pattern matching for mDNS findings
		self.add_pattern(r'(?i)mdns.*service[s]?[:\s]*([^\n\r]+)', description='mDNS Services: {match1}')
		self.add_pattern(r'(?i)zeroconf.*enabled', description='Zeroconf (Bonjour/Avahi) service discovery enabled')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(dns* or ssl*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_multicastdns_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_multicastdns_nmap.xml" {address}', outfile='{protocol}_{port}_multicastdns_nmap.txt')
