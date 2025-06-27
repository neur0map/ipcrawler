from ipcrawler.plugins import ServiceScan

class NmapNFS(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap NFS"
		self.tags = ['default', 'safe', 'nfs']

	def configure(self):
		self.match_service_name(['^nfs', '^rpcbind'])
		# Pattern matching for NFS findings
		self.add_pattern(r'(?i)nfs.*version[:\s]*([^\n\r]+)', description='NFS Version: {match1}')
		self.add_pattern(r'(?i)exports[:\s]*([^\n\r]+)', description='NFS Exports: {match1}')
		self.add_pattern(r'(?i)rpc.*programs[:\s]*([^\n\r]+)', description='RPC Programs: {match1}')
		self.add_pattern(r'(?i)world.*readable', description='CRITICAL: NFS world-readable exports detected')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(rpcinfo or nfs*) and not (brute or broadcast or dos or external or fuzzer)" -oN "{scandir}/{protocol}_{port}_nfs_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_nfs_nmap.xml" {address}', outfile='{protocol}_{port}_nfs_nmap.txt')
