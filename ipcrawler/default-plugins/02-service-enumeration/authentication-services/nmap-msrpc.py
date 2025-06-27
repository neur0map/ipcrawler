from ipcrawler.plugins import ServiceScan

class NmapRPC(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap MSRPC"
		self.tags = ['default', 'rpc']

	def configure(self):
		self.match_service_name(['^msrpc', '^rpcbind', '^erpc'])
		# Pattern matching for RPC findings
		self.add_pattern(r'(?i)rpc.*program[s]?[:\s]*([^\n\r]+)', description='RPC Programs Available: {match1}')
		self.add_pattern(r'(?i)endpoint.*mapper', description='RPC Endpoint Mapper detected - service enumeration possible')
		self.add_pattern(r'(?i)uuid[:\s]*([a-f0-9\-]+)', description='RPC Interface UUID: {match1}')
		self.add_pattern(r'(?i)version[:\s]*(\d+\.\d+)', description='RPC Service Version: {match1}')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,msrpc-enum,rpc-grind,rpcinfo" -oN "{scandir}/{protocol}_{port}_rpc_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_rpc_nmap.xml" {address}', outfile='{protocol}_{port}_rpc_nmap.txt')
