from ipcrawler.plugins import ServiceScan

class NmapMountd(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap Mountd"
		self.tags = ['default', 'safe', 'nfs']

	def configure(self):
		self.match_service_name('^mountd')
		# Pattern matching for Mountd findings
		self.add_pattern(r'(?i)mountd.*version[:\s]*([^\n\r]+)', description='Mountd Version: {match1}')
		self.add_pattern(r'(?i)mount.*points[:\s]*([^\n\r]+)', description='NFS Mount Points: {match1}')
		self.add_pattern(r'(?i)exports[:\s]*([^\n\r]+)', description='NFS Exports via Mountd: {match1}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,nfs* and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_mountd_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_mountd_nmap.xml" {address}', outfile='{protocol}_{port}_mountd_nmap.txt')
