import asyncio, inspect, os, platform, re, sys
from typing import final
from ipcrawler.config import config
from ipcrawler.io import slugify, info, warn, error, fail, CommandStreamReader
from ipcrawler.targets import Service
from ipcrawler.logger import setup_unified_logging


class MockProcess:
	"""Mock process object to maintain compatibility with existing code."""
	
	def __init__(self, returncode):
		self.returncode = returncode
		self.pid = None
	
	async def wait(self):
		"""Mock wait method."""
		return self.returncode


class MockStreamReader:
	"""Mock stream reader to maintain compatibility with existing CommandStreamReader usage."""
	
	def __init__(self, content, target, tag, patterns=None, outfile=None):
		self.content = content
		self.target = target
		self.tag = tag
		self.patterns = patterns or []
		self.outfile = outfile
		self.ended = True  # Mark as ended since we have all content
		
		# Split content into lines for line-by-line reading
		self.lines = (content or "").split('\n') if content else []
		self.line_index = 0
		
		# Process patterns and write outfile if needed
		self._process_content()
	
	def _process_content(self):
		"""Process content for patterns and write to outfile if specified."""
		if self.content and self.outfile:
			try:
				with open(self.outfile, 'w') as f:
					f.write(self.content)
			except Exception as e:
				error(f"Failed to write to {self.outfile}: {e}")
		
		# Process patterns (simplified version of CommandStreamReader pattern matching)
		if self.content and self.patterns:
			for line in self.content.split('\n'):
				for pattern in self.patterns:
					if re.search(pattern.pattern, line):
						# Log pattern match (similar to original CommandStreamReader)
						try:
							pattern_file = os.path.join(self.target.scandir, '_patterns.log')
							with open(pattern_file, 'a') as f:
								f.write(f"[{self.tag}] {pattern.description or pattern.pattern}: {line}\n")
						except Exception as e:
							pass  # Silently continue if pattern logging fails
	
	async def readline(self):
		"""Mock readline method that returns lines one by one, then None when finished."""
		if self.line_index < len(self.lines):
			line = self.lines[self.line_index]
			self.line_index += 1
			return line.encode('utf-8') + b'\n'  # Return as bytes like real readline
		else:
			return None  # Signal end of stream
	
	async def readlines(self):
		"""Mock readlines method that returns all remaining lines as a list."""
		lines = []
		while True:
			line = await self.readline()
			if line is not None:
				# Decode bytes back to string for compatibility with curl plugins
				lines.append(line.decode('utf-8').rstrip('\n'))
			else:
				break
		return lines

class Pattern:

	def __init__(self, pattern, description=None):
		self.pattern = pattern
		self.description = description

class Plugin(object):

	def __init__(self):
		self.name = None
		self.slug = None
		self.description = None
		self.tags = ['default']
		self.priority = 1
		self.patterns = []
		self.ipcrawler = None
		self.disabled = False

	@final
	def add_option(self, name, default=None, help=None):
		self.ipcrawler.add_argument(self, name, metavar='VALUE', default=default, help=help)

	@final
	def add_constant_option(self, name, const, default=None, help=None):
		self.ipcrawler.add_argument(self, name, action='store_const', const=const, default=default, help=help)

	@final
	def add_true_option(self, name, help=None):
		self.ipcrawler.add_argument(self, name, action='store_true', help=help)

	@final
	def add_false_option(self, name, help=None):
		self.ipcrawler.add_argument(self, name, action='store_false', help=help)

	@final
	def add_list_option(self, name, default=None, help=None):
		self.ipcrawler.add_argument(self, name, nargs='+', metavar='VALUE', default=default, help=help)

	@final
	def add_choice_option(self, name, choices, default=None, help=None):
		if not isinstance(choices, list):
			fail('The choices argument for ' + self.name + '\'s ' + name + ' choice option should be a list.')
		self.ipcrawler.add_argument(self, name, choices=choices, default=default, help=help)

	@final
	def get_option(self, name, default=None):
		name = self.slug.replace('-', '_') + '.' + slugify(name).replace('-', '_')

		if name in vars(self.ipcrawler.args):
			if vars(self.ipcrawler.args)[name] is None:
				if default:
					return default
				else:
					return None
			else:
				return vars(self.ipcrawler.args)[name]
		else:
			if default:
				return default
			return None

	@final
	def get_global_option(self, name, default=None):
		name = 'global.' + slugify(name).replace('-', '_')

		if name in vars(self.ipcrawler.args):
			if vars(self.ipcrawler.args)[name] is None:
				if default:
					return default
				else:
					return None
			else:
				return vars(self.ipcrawler.args)[name]
		else:
			if default:
				return default
			return None

	@final
	def get_global(self, name, default=None):
		return self.get_global_option(name, default)

	@final
	def add_pattern(self, pattern, description=None):
		try:
			compiled = re.compile(pattern)
			if description:
				self.patterns.append(Pattern(compiled, description=description))
			else:
				self.patterns.append(Pattern(compiled))
		except re.error:
			fail('Error: The pattern "' + pattern + '" in the plugin "' + self.name + '" is invalid regex.')

	@final
	def info(self, msg, verbosity=0):
		info(f'🔧 [{self.slug}] {msg}', verbosity=1)

	@final
	def warn(self, msg, verbosity=0):
		warn(f'⚠️ [{self.slug}] {msg}', verbosity=verbosity)

	@final
	def error(self, msg, verbosity=0):
		error(f'❌ [{self.slug}] {msg}', verbosity=verbosity)

class PortScan(Plugin):

	def __init__(self):
		super().__init__()
		self.type = None
		self.specific_ports = False

	async def run(self, target):
		raise NotImplementedError

class ServiceScan(Plugin):

	def __init__(self):
		super().__init__()
		self.ports = {'tcp':[], 'udp':[]}
		self.ignore_ports = {'tcp':[], 'udp':[]}
		self.services = []
		self.service_names = []
		self.ignore_service_names = []
		self.run_once_boolean = False
		self.require_ssl_boolean = False
		self.max_target_instances = 0
		self.max_global_instances = 0

	@final
	def match_service(self, protocol, port, name, negative_match=False):
		protocol = protocol.lower()
		if protocol not in ['tcp', 'udp']:
			print('Invalid protocol.')
			sys.exit(1)

		if not isinstance(port, list):
			port = [port]

		port = list(map(int, port))

		if not isinstance(name, list):
			name = [name]

		valid_regex = True
		for r in name:
			try:
				re.compile(r)
			except re.error:
				print('Invalid regex: ' + r)
				valid_regex = False

		if not valid_regex:
			sys.exit(1)

		service = {'protocol': protocol, 'port': port, 'name': name, 'negative_match': negative_match}
		self.services.append(service)

	@final
	def match_port(self, protocol, port, negative_match=False):
		protocol = protocol.lower()
		if protocol not in ['tcp', 'udp']:
			print('Invalid protocol.')
			sys.exit(1)
		else:
			if not isinstance(port, list):
				port = [port]

			port = list(map(int, port))

			if negative_match:
				self.ignore_ports[protocol] = list(set(self.ignore_ports[protocol] + port))
			else:
				self.ports[protocol] = list(set(self.ports[protocol] + port))

	@final
	def match_service_name(self, name, negative_match=False):
		if not isinstance(name, list):
			name = [name]

		valid_regex = True
		for r in name:
			try:
				re.compile(r)
			except re.error:
				print('Invalid regex: ' + r)
				valid_regex = False

		if valid_regex:
			if negative_match:
				self.ignore_service_names = list(set(self.ignore_service_names + name))
			else:
				self.service_names = list(set(self.service_names + name))
		else:
			sys.exit(1)

	@final
	def require_ssl(self, boolean):
		self.require_ssl_boolean = boolean

	@final
	def run_once(self, boolean):
		self.run_once_boolean = boolean

	@final
	def match_all_service_names(self, boolean):
		if boolean:
			# Add a "match all" service name.
			self.match_service_name('.*')

class Report(Plugin):

	def __init__(self):
		super().__init__()

class ipcrawler(object):

	def __init__(self):
		self.pending_targets = []
		self.scanning_targets = []
		self.completed_targets = []
		self.plugins = {}
		self.__slug_regex = re.compile(r'^[a-z0-9\-]+$')
		self.plugin_types = {'port':[], 'service':[], 'report':[]}
		self.port_scan_semaphore = None
		self.service_scan_semaphore = None
		self.argparse = None
		self.argparse_group = None
		self.args = None
		self.missing_services = []
		self.taglist = []
		self.tags = []
		self.excluded_tags = []
		self.patterns = []
		self.errors = False
		self.lock = asyncio.Lock()
		self.load_slug = None
		self.load_module = None

	def add_argument(self, plugin, name, **kwargs):
		name = '--' + plugin.slug + '.' + slugify(name)

		if self.argparse_group is None:
			self.argparse_group = self.argparse.add_argument_group('plugin arguments', description='These are optional arguments for certain plugins.')
		self.argparse_group.add_argument(name, **kwargs)

	def extract_service(self, line, regex):
		if regex is None:
			regex = r'^(?P<port>\d+)\/(?P<protocol>(tcp|udp))(.*)open(\s*)(?P<service>[\w\-\/]+)(\s*)(.*)$'
		
		# Convert bytes to string if necessary
		if isinstance(line, bytes):
			line = line.decode('utf-8', errors='replace').strip()
		
		match = re.search(regex, line)
		if match:
			protocol = match.group('protocol').lower()
			port = int(match.group('port'))
			service = match.group('service')
			secure = True if 'ssl' in service or 'tls' in service else False

			if service.startswith('ssl/') or service.startswith('tls/'):
				service = service[4:]

			return Service(protocol, port, service, secure)
		else:
			return None

	async def extract_services(self, stream, regex):
		if not isinstance(stream, (CommandStreamReader, MockStreamReader)):
			print('Error: extract_services must be passed an instance of a CommandStreamReader or MockStreamReader.')
			return []

		services = []
		while True:
			line = await stream.readline()
			if line is not None:
				service = self.extract_service(line, regex)
				if service:
					services.append(service)
			else:
				break
		return services

	def register(self, plugin, filename):
		if plugin.disabled:
			return

		if plugin.name is None:
			fail('Error: Plugin with class name "' + plugin.__class__.__name__ + '" in ' + filename + ' does not have a name.')

		for _, loaded_plugin in self.plugins.items():
			if plugin.name == loaded_plugin.name:
				fail('Error: Duplicate plugin name "' + plugin.name + '" detected in ' + filename + '.', file=sys.stderr)

		if plugin.slug is None:
			plugin.slug = slugify(plugin.name)
		elif not self.__slug_regex.match(plugin.slug):
			fail('Error: provided slug "' + plugin.slug + '" in ' + filename + ' is not valid (must only contain lowercase letters, numbers, and hyphens).', file=sys.stderr)

		if plugin.slug in config['protected_classes']:
			fail('Error: plugin slug "' + plugin.slug + '" in ' + filename + ' is a protected string. Please change.')

		if plugin.slug not in self.plugins:

			for _, loaded_plugin in self.plugins.items():
				if plugin is loaded_plugin:
					fail('Error: plugin "' + plugin.name + '" in ' + filename + ' already loaded as "' + loaded_plugin.name + '" (' + str(loaded_plugin) + ')', file=sys.stderr)

			configure_function_found = False
			run_coroutine_found = False
			manual_function_found = False

			for member_name, member_value in inspect.getmembers(plugin, predicate=inspect.ismethod):
				if member_name == 'configure':
					configure_function_found = True
				elif member_name == 'run' and inspect.iscoroutinefunction(member_value):
					if len(inspect.getfullargspec(member_value).args) != 2:
						fail('Error: the "run" coroutine in the plugin "' + plugin.name + '" in ' + filename + ' should have two arguments.', file=sys.stderr)
					run_coroutine_found = True
				elif member_name == 'manual':
					if len(inspect.getfullargspec(member_value).args) != 3:
						fail('Error: the "manual" function in the plugin "' + plugin.name + '" in ' + filename + ' should have three arguments.', file=sys.stderr)
					manual_function_found = True

			if not run_coroutine_found and not manual_function_found:
				fail('Error: the plugin "' + plugin.name + '" in ' + filename + ' needs either a "manual" function, a "run" coroutine, or both.', file=sys.stderr)

			if issubclass(plugin.__class__, PortScan):
				if plugin.type is None:
					fail('Error: the PortScan plugin "' + plugin.name + '" in ' + filename + ' requires a type (either tcp or udp).')
				else:
					plugin.type = plugin.type.lower()
					if plugin.type not in ['tcp', 'udp']:
						fail('Error: the PortScan plugin "' + plugin.name + '" in ' + filename + ' has an invalid type (should be tcp or udp).')
				self.plugin_types["port"].append(plugin)
			elif issubclass(plugin.__class__, ServiceScan):
				self.plugin_types["service"].append(plugin)
			elif issubclass(plugin.__class__, Report):
				self.plugin_types["report"].append(plugin)
			else:
				fail('Plugin "' + plugin.name + '" in ' + filename + ' is neither a PortScan, ServiceScan, nor a Report.', file=sys.stderr)

			plugin.tags = [tag.lower() for tag in plugin.tags]

			# Add plugin tags to tag list.
			[self.taglist.append(t) for t in plugin.tags if t not in self.tags]

			plugin.ipcrawler = self
			if configure_function_found:
				plugin.configure()
			self.plugins[plugin.slug] = plugin
		else:
			fail('Error: plugin slug "' + plugin.slug + '" in ' + filename + ' is already assigned.', file=sys.stderr)

	def _get_enhanced_env(self):
		"""Generate enhanced environment for subprocess calls with proper PATH handling."""
		env = os.environ.copy()
		system = platform.system()
		
		# Define expected paths by platform based on Makefile install locations
		if system == "Darwin":  # macOS
			expected_paths = [
				"/opt/homebrew/bin",  # Apple Silicon Homebrew
				"/usr/local/bin",     # Intel Homebrew
				"/usr/bin",           # System
				"/bin"                # System
			]
		elif system == "Linux":
			expected_paths = [
				"/usr/bin",           # APT packages
				"/usr/local/bin",     # Manual/GitHub installs
				"/bin",               # System
				"/usr/sbin",          # System admin tools
				"/sbin"               # System admin tools
			]
		else:
			expected_paths = ["/usr/bin", "/usr/local/bin", "/bin"]
		
		# Ensure all expected paths are in PATH
		current_path = env.get('PATH', '')
		path_dirs = current_path.split(os.pathsep) if current_path else []
		
		for expected_path in expected_paths:
			if expected_path not in path_dirs and os.path.exists(expected_path):
				path_dirs.insert(0, expected_path)  # Add to front for priority
		
		env['PATH'] = os.pathsep.join(path_dirs)
		return env

	async def execute(self, cmd, target, tag, patterns=None, outfile=None, errfile=None):
		if patterns:
			combined_patterns = self.patterns + patterns
		else:
			combined_patterns = self.patterns

		# Setup unified logging for this target if not already done
		if not hasattr(target, '_unified_logger'):
			target._unified_logger = setup_unified_logging(target.address, target.scandir)

		# Extract plugin name for logging
		plugin_name = self._extract_plugin_name(cmd, tag)
		
		# Check if this should use unified logging (skip internal commands)
		if self._should_bypass_unified_logging(cmd):
			# Use original execution path for internal commands
			return await self._execute_original(cmd, target, tag, combined_patterns, outfile, errfile)
		
		# Execute with comprehensive unified logging - this replaces the original system
		enhanced_env = self._get_enhanced_env()
		
		# Check verbosity - only suppress output in quiet mode (verbosity 0)
		from ipcrawler.config import config
		suppress_output = config.get('verbose', 0) == 0
		
		# Use configured timeout (convert from minutes to seconds)
		configured_timeout = config.get('timeout', 120) * 60  # Default 2 hours in seconds
		
		if suppress_output:
			# Use output suppression to capture any plugin print statements
			with target._unified_logger.create_output_suppressor():
				exit_code, stdout_content, stderr_content = await target._unified_logger.execute_with_logging(
					cmd, plugin_name, cwd=target.scandir, env=enhanced_env, timeout=configured_timeout
				)
		else:
			# Allow terminal output to show when verbose mode is enabled
			exit_code, stdout_content, stderr_content = await target._unified_logger.execute_with_logging(
				cmd, plugin_name, cwd=target.scandir, env=enhanced_env, timeout=configured_timeout
			)
		
		# Print clean status message instead of raw output
		target._unified_logger.print_status(plugin_name, exit_code == 0)
		
		# Create enhanced mock process and stream objects for full compatibility
		mock_process = MockProcess(exit_code)
		mock_cout = MockStreamReader(stdout_content, target, tag, combined_patterns, outfile)
		mock_cerr = MockStreamReader(stderr_content, target, tag, combined_patterns, errfile)
		
		return mock_process, mock_cout, mock_cerr

	async def _execute_original(self, cmd, target, tag, combined_patterns, outfile=None, errfile=None):
		"""Original execute method for internal commands that should bypass unified logging."""
		enhanced_env = self._get_enhanced_env()
		
		# Use asyncio.subprocess.DEVNULL instead of synchronous open()
		process = await asyncio.create_subprocess_shell(
			cmd,
			stdin=asyncio.subprocess.DEVNULL,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.PIPE,
			env=enhanced_env,
			limit=1024*1024)  # 1MB limit instead of default 64KB to handle large JSON responses

		cout = CommandStreamReader(process.stdout, target, tag, patterns=combined_patterns, outfile=outfile)
		cerr = CommandStreamReader(process.stderr, target, tag, patterns=combined_patterns, outfile=errfile)

		# Store tasks to prevent premature garbage collection
		# Keep references to prevent tasks from being garbage collected
		self._active_tasks = getattr(self, '_active_tasks', [])
		cout_task = asyncio.create_task(cout._read())
		cerr_task = asyncio.create_task(cerr._read())
		self._active_tasks.extend([cout_task, cerr_task])

		return process, cout, cerr

	def _extract_plugin_name(self, cmd: str, tag: str) -> str:
		"""Extract plugin name from command or tag."""
		# Try to get plugin name from command
		cmd_parts = cmd.strip().split()
		if cmd_parts:
			# Remove common prefixes
			tool_name = cmd_parts[0]
			if tool_name in ['timeout', 'sudo']:
				tool_name = cmd_parts[1] if len(cmd_parts) > 1 else tool_name
			return tool_name
		
		return tag or "unknown"
	
	def _should_bypass_unified_logging(self, cmd: str) -> bool:
		"""Check if command should bypass unified logging."""
		# Skip logging for internal/utility commands
		bypass_commands = ['mkdir', 'chmod', 'chown', 'cp', 'mv', 'ln', 'touch', 'echo', 'cat']
		cmd_parts = cmd.strip().split()
		if cmd_parts and cmd_parts[0] in bypass_commands:
			return True
		return False
