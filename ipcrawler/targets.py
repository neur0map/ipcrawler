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
		self.discovered_hostnames = []  # Store discovered hostnames from vhost discovery

	async def add_service(self, service):
		async with self.lock:
			self.pending_services.append(service)

	def _validate_hostname(self, hostname):
		"""Validate hostname before adding to discovered hostnames"""
		if not hostname:
			return None

		# Remove any whitespace
		hostname = hostname.strip()

		# Check for valid hostname format
		import re

		# Reject obviously malformed hostnames that look like concatenated strings
		suspicious_patterns = [
			r'\.html?$',           # Ends with .html or .htm (likely concatenated)
			r'\.php$',             # Ends with .php (likely concatenated)
			r'\.js$',              # Ends with .js (likely concatenated)
			r'\.css$',             # Ends with .css (likely concatenated)
			r'home$',              # Ends with 'home' (likely concatenated)
			r'index$',             # Ends with 'index' (likely concatenated)
			r'admin$',             # Ends with 'admin' (likely concatenated)
			r'login$',             # Ends with 'login' (likely concatenated)
		]

		for pattern in suspicious_patterns:
			if re.search(pattern, hostname, re.IGNORECASE):
				return None

		# Allow IP addresses and valid hostnames
		if re.match(r'^[a-zA-Z0-9.-]+$', hostname) and len(hostname) > 0:
			# Ensure no double dots or invalid characters
			if '..' not in hostname and not hostname.startswith('.') and not hostname.endswith('.'):
				# Additional check: hostname should not be too long (max 253 chars per RFC)
				if len(hostname) <= 253:
					return hostname

		return None

	async def add_discovered_hostname(self, hostname):
		"""Add a discovered hostname from vhost discovery"""
		async with self.lock:
			# Validate hostname before adding
			validated_hostname = self._validate_hostname(hostname)
			if validated_hostname and validated_hostname != self.address and validated_hostname != self.ip:
				if validated_hostname not in self.discovered_hostnames:
					self.discovered_hostnames.append(validated_hostname)
				else:
					print(f"🔧 DEBUG: Hostname already exists: {validated_hostname}")
			elif hostname and not validated_hostname:
				print(f"⚠️ WARNING: Invalid hostname rejected: '{hostname}'")

	def get_best_hostname(self):
		"""Get the best hostname to use for web scanning (prefers discovered hostnames)"""
		if self.discovered_hostnames and len(self.discovered_hostnames) > 0:
			return self.discovered_hostnames[0]  # Use first discovered hostname
		elif self.type == 'hostname' and self.address:
			return self.address  # Use original hostname if target was a hostname
		else:
			# Always fall back to IP - this should never be None
			return self.ip if self.ip else self.address

	def get_all_hostnames(self):
		"""Get all available hostnames for comprehensive scanning"""
		hostnames = []

		# Add discovered hostnames first (highest priority) - with validation
		if self.discovered_hostnames:
			for hostname in self.discovered_hostnames:
				validated = self._validate_hostname(hostname)
				if validated and validated not in hostnames:
					hostnames.append(validated)
				elif hostname and not validated:
					print(f"⚠️ WARNING: Invalid discovered hostname skipped: '{hostname}'")

		# Add original hostname if it was a hostname target - with validation
		if self.type == 'hostname' and self.address:
			validated_address = self._validate_hostname(self.address)
			if validated_address and validated_address not in hostnames:
				hostnames.append(validated_address)

		# Always include IP as fallback - with validation
		fallback_ip = self.ip if self.ip else self.address
		if fallback_ip:
			validated_fallback = self._validate_hostname(fallback_ip)
			if validated_fallback and validated_fallback not in hostnames:
				hostnames.append(validated_fallback)

		# Ensure we ALWAYS have at least one hostname (the IP)
		if not hostnames:
			final_fallback = self.ip if self.ip else self.address
			validated_final = self._validate_hostname(final_fallback)
			if validated_final:
				hostnames = [validated_final]
			else:
				print(f"❌ CRITICAL: No valid hostnames available! Fallback: '{final_fallback}'")
				# In extreme cases, still return something to prevent crashes
				hostnames = [final_fallback] if final_fallback else ['127.0.0.1']

		# Debug logging
		print(f"🔧 DEBUG get_all_hostnames(): discovered_hostnames={self.discovered_hostnames}, type={self.type}, address={self.address}, ip={self.ip}, final_hostnames={hostnames}")

		return hostnames

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
		
		# Show beautiful command execution details
		scan_status.show_command_execution(address, plugin.name, cmd, config['verbose'])

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
		
		# Show beautiful command execution details
		scan_status.show_command_execution(f"{self.target.address}:{self.port}", plugin.name, cmd, config['verbose'])

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
