import asyncio, inspect, os
from typing import final
from ipcrawler.config import config
from ipcrawler.io import e, info, warn, error
from ipcrawler.loading import start_tool_loading, stop_tool_loading, update_tool_progress, scan_status

class Target:

	def __init__(self, address, ip, ipversion, type, ipcrawler):
		self.address = address
		self.ip = ip
		self.ipversion = ipversion
		self.type = type
		self.ipcrawler = ipcrawler
		self.basedir = ''
		self.reportdir = ''
		self.scandir = ''
		self.lock = asyncio.Lock()
		self.ports = None
		self.pending_services = []
		self.services = []
		self.scans = {'ports':{}, 'services':{}}
		self.running_tasks = {}

	async def add_service(self, service):
		async with self.lock:
			self.pending_services.append(service)

	def extract_service(self, line, regex=None):
		return self.ipcrawler.extract_service(line, regex)

	async def extract_services(self, stream, regex=None):
		return await self.ipcrawler.extract_services(stream, regex)

	@final
	def info(self, msg, verbosity=0):
		plugin = inspect.currentframe().f_back.f_locals['self']
		info(f'🎯 [{self.address}/{plugin.slug}] {msg}', verbosity=verbosity)

	@final
	def warn(self, msg, verbosity=0):
		plugin = inspect.currentframe().f_back.f_locals['self']
		warn(f'⚠️ [{self.address}/{plugin.slug}] {msg}', verbosity=verbosity)

	@final
	def error(self, msg, verbosity=0):
		plugin = inspect.currentframe().f_back.f_locals['self']
		error(f'❌ [{self.address}/{plugin.slug}] {msg}', verbosity=verbosity)
		
	def _estimate_port_scan_time(self, plugin_name: str) -> int:
		"""Estimate port scan time based on plugin characteristics"""
		plugin_lower = plugin_name.lower()
		
		# Fast scans (1-3 minutes)
		if any(fast in plugin_lower for fast in ['top-100', 'top-1000', 'guess']):
			return 2
		
		# Medium scans (3-8 minutes)
		elif any(medium in plugin_lower for medium in ['top', 'common']):
			return 4
		
		# Slow scans (8+ minutes)
		elif any(slow in plugin_lower for slow in ['all', 'full', '-p-']):
			return 10
		
		# UDP scans are generally slower
		elif 'udp' in plugin_lower:
			return 8
		
		# Default estimate
		else:
			return 3

	async def execute(self, cmd, blocking=True, outfile=None, errfile=None, future_outfile=None):
		target = self

		# Create variables for command references.
		address = target.address
		addressv6 = target.address
		ipaddress = target.ip
		ipaddressv6 = target.ip
		scandir = target.scandir

		nmap_extra = target.ipcrawler.args.nmap
		if target.ipcrawler.args.nmap_append:
			nmap_extra += ' ' + target.ipcrawler.args.nmap_append

		if target.ipversion == 'IPv6':
			nmap_extra += ' -6'
			if addressv6 == target.ip:
				addressv6 = '[' + addressv6 + ']'
			ipaddressv6 = '[' + ipaddressv6 + ']'

		plugin = inspect.currentframe().f_back.f_locals['self']

		if config['proxychains']:
			nmap_extra += ' -sT'

		cmd = e(cmd)
		tag = plugin.slug

		# Start loading interface for port scan with intelligent estimates
		estimated_time = self._estimate_port_scan_time(plugin.name)
		start_tool_loading(plugin.name, address, cmd, estimated_minutes=estimated_time)
		
		# Command execution details (only at high verbosity)
		info(f'🔧 {plugin.name}: {cmd}', verbosity=3)

		if outfile is not None:
			outfile = os.path.join(target.scandir, e(outfile))

		if errfile is not None:
			errfile = os.path.join(target.scandir, e(errfile))

		if future_outfile is not None:
			future_outfile = os.path.join(target.scandir, e(future_outfile))

		target.scans['ports'][tag]['commands'].append([cmd, outfile if outfile is not None else future_outfile, errfile])

		async with target.lock:
			with open(os.path.join(target.scandir, '_commands.log'), 'a') as file:
				file.writelines(cmd + '\n\n')

		process, stdout, stderr = await target.ipcrawler.execute(cmd, target, tag, patterns=plugin.patterns, outfile=outfile, errfile=errfile)

		target.running_tasks[tag]['processes'].append({'process': process, 'stderr': stderr, 'cmd': cmd})

		# If process should block, sleep until stdout and stderr have finished.
		if blocking:
			while (not (stdout.ended and stderr.ended)):
				await asyncio.sleep(0.1)
			await process.wait()
			
			# Stop loading interface and show completion
			success = process.returncode == 0
			stop_tool_loading(success, f"Exit code: {process.returncode}")

		return process, stdout, stderr

class Service:

	def __init__(self, protocol, port, name, secure=False):
		self.target = None
		self.protocol = protocol.lower()
		self.port = int(port)
		self.name = name
		self.secure = secure
		self.manual_commands = {}

	@final
	def tag(self):
		return self.protocol + '/' + str(self.port) + '/' + self.name

	@final
	def full_tag(self):
		return self.protocol + '/' + str(self.port) + '/' + self.name + '/' + ('secure' if self.secure else 'insecure')

	@final
	def add_manual_commands(self, description, commands):
		if not isinstance(commands, list):
			commands = [commands]
		if description not in self.manual_commands:
			self.manual_commands[description] = []

		# Merge in new unique commands, while preserving order.
		[self.manual_commands[description].append(m) for m in commands if m not in self.manual_commands[description]]

	@final
	def add_manual_command(self, description, command):
		self.add_manual_commands(description, command)

	@final
	def info(self, msg, verbosity=0):
		plugin = inspect.currentframe().f_back.f_locals['self']
		info(f'🎯 [{self.target.address}:{self.port}/{plugin.slug}] {msg}', verbosity=verbosity)

	@final
	def warn(self, msg, verbosity=0):
		plugin = inspect.currentframe().f_back.f_locals['self']
		warn(f'⚠️ [{self.target.address}:{self.port}/{plugin.slug}] {msg}', verbosity=verbosity)

	@final
	def error(self, msg, verbosity=0):
		plugin = inspect.currentframe().f_back.f_locals['self']
		error(f'❌ [{self.target.address}:{self.port}/{plugin.slug}] {msg}', verbosity=verbosity)

	def _estimate_service_scan_time(self, plugin_name: str) -> int:
		"""Estimate scan time based on plugin characteristics"""
		plugin_lower = plugin_name.lower()
		
		# Fast tools (1-3 minutes)
		if any(fast in plugin_lower for fast in ['nmap', 'curl', 'whatweb', 'sslscan']):
			return 2
		
		# Medium tools (3-8 minutes)  
		elif any(medium in plugin_lower for medium in ['nikto', 'enum4linux', 'smbclient', 'showmount']):
			return 5
		
		# Slow tools (8-15 minutes)
		elif any(slow in plugin_lower for slow in ['dirbuster', 'dirb', 'gobuster', 'wfuzz']):
			return 10
		
		# Very slow tools (15+ minutes)
		elif any(very_slow in plugin_lower for very_slow in ['hydra', 'medusa', 'john', 'hashcat']):
			return 20
		
		# Default estimate
		else:
			return 5

	@final
	async def execute(self, cmd, blocking=True, outfile=None, errfile=None, future_outfile=None):
		target = self.target

		# Create variables for command references.
		address = target.address
		addressv6 = target.address
		ipaddress = target.ip
		ipaddressv6 = target.ip
		scandir = target.scandir
		protocol = self.protocol
		port = self.port
		name = self.name

		if not config['no_port_dirs']:
			scandir = os.path.join(scandir, protocol + str(port))
			os.makedirs(scandir, exist_ok=True)
			os.makedirs(os.path.join(scandir, 'xml'), exist_ok=True)

		# Special cases for HTTP.
		http_scheme = 'https' if 'https' in self.name or self.secure is True else 'http'

		nmap_extra = target.ipcrawler.args.nmap
		if target.ipcrawler.args.nmap_append:
			nmap_extra += ' ' + target.ipcrawler.args.nmap_append

		if protocol == 'udp':
			nmap_extra += ' -sU'

		if target.ipversion == 'IPv6':
			nmap_extra += ' -6'
			if addressv6 == target.ip:
				addressv6 = '[' + addressv6 + ']'
			ipaddressv6 = '[' + ipaddressv6 + ']'

		if config['proxychains'] and protocol == 'tcp':
			nmap_extra += ' -sT'

		plugin = inspect.currentframe().f_back.f_locals['self']
		cmd = e(cmd)
		tag = self.tag() + '/' + plugin.slug
		plugin_tag = tag
		if plugin.run_once_boolean:
			plugin_tag = plugin.slug

		# Start loading interface for service scan with intelligent estimates
		estimated_time = self._estimate_service_scan_time(plugin.name)
		start_tool_loading(plugin.name, address, cmd, estimated_minutes=estimated_time)
		
		# Command execution details (only at high verbosity)  
		info(f'🔧 {plugin.name}: {cmd}', verbosity=3)

		if outfile is not None:
			outfile = os.path.join(scandir, e(outfile))

		if errfile is not None:
			errfile = os.path.join(scandir, e(errfile))

		if future_outfile is not None:
			future_outfile = os.path.join(scandir, e(future_outfile))

		target.scans['services'][self][plugin_tag]['commands'].append([cmd, outfile if outfile is not None else future_outfile, errfile])

		async with target.lock:
			with open(os.path.join(target.scandir, '_commands.log'), 'a') as file:
				file.writelines(cmd + '\n\n')

		process, stdout, stderr = await target.ipcrawler.execute(cmd, target, tag, patterns=plugin.patterns, outfile=outfile, errfile=errfile)

		target.running_tasks[tag]['processes'].append({'process': process, 'stderr': stderr, 'cmd': cmd})

		# If process should block, sleep until stdout and stderr have finished.
		if blocking:
			while (not (stdout.ended and stderr.ended)):
				await asyncio.sleep(0.1)
			await process.wait()
			
			# Stop loading interface and show completion
			success = process.returncode == 0
			stop_tool_loading(success, f"Exit code: {process.returncode}")

		return process, stdout, stderr
