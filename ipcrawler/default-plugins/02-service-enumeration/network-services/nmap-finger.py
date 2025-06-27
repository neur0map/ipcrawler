from ipcrawler.plugins import ServiceScan

class NmapFinger(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap finger"
		self.tags = ['default', 'safe', 'finger']

	def configure(self):
		self.match_service_name('^finger')
		# Pattern matching for Finger findings
		self.add_pattern(r'(?i)user[s]?[:\s]*([^\n\r]+)', description='Finger Users Found: {match1}')
		self.add_pattern(r'(?i)login[:\s]*([^\n\r]+)', description='Finger Login Info: {match1}')
		self.add_pattern(r'(?i)real.*name[:\s]*([^\n\r]+)', description='Finger Real Names: {match1}')
		self.add_pattern(r'(?i)finger.*enabled', description='Finger service enabled - user enumeration possible')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,finger" -oN "{scandir}/{protocol}_{port}_finger_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_finger_nmap.xml" {address}', outfile='{protocol}_{port}_finger_nmap.txt')
