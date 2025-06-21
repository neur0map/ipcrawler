import asyncio, colorama, os, re, string, sys, unidecode
from colorama import Fore, Style
from ipcrawler.config import config
from ipcrawler.loading import scan_status, is_loading_active, record_tool_activity

# ASCII art imports
try:
	import pyfiglet
	from termcolor import colored
	PYFIGLET_AVAILABLE = True
except ImportError:
	PYFIGLET_AVAILABLE = False

# Modern UI imports
try:
	from typing import List, Dict, Any
	from rich.console import Console
	from rich.table import Table
	from rich.panel import Panel
	from rich.text import Text
	from rich.align import Align
	from rich import box
	
	# Create rich console for modern UI features
	console = Console()
	RICH_AVAILABLE = True
except ImportError:
	RICH_AVAILABLE = False

def slugify(name):
	return re.sub(r'[\W_]+', '-', unidecode.unidecode(name).lower()).strip('-')

def e(*args, frame_index=1, **kvargs):
	frame = sys._getframe(frame_index)

	vals = {}

	vals.update(frame.f_globals)
	vals.update(frame.f_locals)
	vals.update(kvargs)

	return string.Formatter().vformat(' '.join(args), args, vals)

def fformat(s):
	return e(s, frame_index=3)

def cprint(*args, color=Fore.RESET, char='*', sep=' ', end='\n', frame_index=1, file=sys.stdout, printmsg=True, verbosity=0, **kvargs):
	if printmsg and verbosity > config['verbose']:
		return ''
	frame = sys._getframe(frame_index)

	vals = {
		'bgreen':  Fore.GREEN  + Style.BRIGHT,
		'bred':	Fore.RED	+ Style.BRIGHT,
		'bblue':   Fore.BLUE   + Style.BRIGHT,
		'byellow': Fore.YELLOW + Style.BRIGHT,
		'bmagenta': Fore.MAGENTA + Style.BRIGHT,

		'green':  Fore.GREEN,
		'red':	Fore.RED,
		'blue':   Fore.BLUE,
		'yellow': Fore.YELLOW,
		'magenta': Fore.MAGENTA,

		'bright': Style.BRIGHT,
		'srst':   Style.NORMAL,
		'crst':   Fore.RESET,
		'rst':	Style.NORMAL + Fore.RESET
	}

	if config['accessible']:
		vals = {'bgreen':'', 'bred':'', 'bblue':'', 'byellow':'', 'bmagenta':'', 'green':'', 'red':'', 'blue':'', 'yellow':'', 'magenta':'', 'bright':'', 'srst':'', 'crst':'', 'rst':''}

	vals.update(frame.f_globals)
	vals.update(frame.f_locals)
	vals.update(kvargs)

	unfmt = ''
	if char is not None and not config['accessible']:
		unfmt += color + '[' + Style.BRIGHT + char + Style.NORMAL + ']' + Fore.RESET + sep
	unfmt += sep.join(args)

	fmted = unfmt

	for _ in range(10):
		try:
			fmted = string.Formatter().vformat(unfmt, args, vals)
			break
		except KeyError as err:
			key = err.args[0]
			unfmt = unfmt.replace('{' + key + '}', '{{' + key + '}}')

	if printmsg:
		print(fmted, sep=sep, end=end, file=file)
	else:
		return fmted

def debug(*args, color=Fore.GREEN, sep=' ', end='\n', file=sys.stdout, **kvargs):
	if config['verbose'] >= 2:
		if config['accessible']:
			args = ('Debug:',) + args
		cprint(*args, color=color, char=None, sep=sep, end=end, file=file, frame_index=2, **kvargs)

def info(*args, sep=' ', end='\n', file=sys.stdout, **kvargs):
	# Use modern status display if loading is active
	if is_loading_active() and len(args) >= 1:
		# Try to parse target/plugin from the formatted message
		message = ' '.join(str(arg) for arg in args)
		if '[' in message and ']' in message:
			# Extract target and message parts
			parts = message.split(']', 1)
			if len(parts) == 2:
				target_part = parts[0].replace('[', '').strip()
				msg_part = parts[1].strip()
				scan_status.show_scan_result(target_part, "scan", msg_part, "info", config['verbose'])
				return
	
	cprint(*args, color=Fore.BLUE, char=None, sep=sep, end=end, file=file, frame_index=2, **kvargs)

def warn(*args, sep=' ', end='\n', file=sys.stderr,**kvargs):
	if config['accessible']:
		args = ('Warning:',) + args
	cprint(*args, color=Fore.YELLOW, char=None, sep=sep, end=end, file=file, frame_index=2, **kvargs)

def error(*args, sep=' ', end='\n', file=sys.stderr, **kvargs):
	if config['accessible']:
		args = ('Error:',) + args
	cprint(*args, color=Fore.RED, char=None, sep=sep, end=end, file=file, frame_index=2, **kvargs)

def fail(*args, sep=' ', end='\n', file=sys.stderr, **kvargs):
	if config['accessible']:
		args = ('Failure:',) + args
	cprint(*args, color=Fore.RED, char=None, sep=sep, end=end, file=file, frame_index=2, **kvargs)
	exit(-1)

class CommandStreamReader(object):

	def __init__(self, stream, target, tag, patterns=None, outfile=None):
		self.stream = stream
		self.target = target
		self.tag = tag
		self.lines = []
		self.patterns = patterns or []
		self.outfile = outfile
		self.ended = False

		# Empty files that already exist.
		if self.outfile != None:
			with open(self.outfile, 'w'): pass

	# Read lines from the stream until it ends.
	async def _read(self):
		while True:
			if self.stream.at_eof():
				break
			try:
				line = (await self.stream.readline()).decode('utf8').rstrip()
			except ValueError:
				error('{bright}[{yellow}' + self.target.address + '{crst}/{bgreen}' + self.tag + '{crst}]{rst} A line was longer than 64 KiB and cannot be processed. Ignoring.')
				continue

			if line != '':
				# Record activity for loading interface
				if is_loading_active():
					record_tool_activity("output")
					scan_status.show_command_output(self.target.address, self.tag, line.strip(), config['verbose'])
				else:
					# Use Rich console for consistency (only at highest verbosity)
					if config['verbose'] >= 3:
						from rich.console import Console
						Console().print(f"📝 [{self.target.address}/{self.tag}] {line.strip()}", style="dim white")

			# Check lines for pattern matches.
			for p in self.patterns:
				description = ''

				# Match and replace entire pattern.
				match = p.pattern.search(line)
				if match:
					if p.description:
						description = p.description.replace('{match}', line[match.start():match.end()])

						# Match and replace substrings.
						matches = p.pattern.findall(line)
						if len(matches) > 0 and isinstance(matches[0], tuple):
							matches = list(matches[0])

						match_count = 1
						for match in matches:
							if p.description:
								description = description.replace('{match' + str(match_count) + '}', match)
							match_count += 1

						async with self.target.lock:
							with open(os.path.join(self.target.scandir, '_patterns.log'), 'a') as file:
								# Record pattern match activity and use modern status display
								if is_loading_active():
									record_tool_activity("pattern_match")
									scan_status.show_pattern_match(self.target.address, self.tag, p.pattern.pattern, description, config['verbose'])
								else:
									scan_status.show_pattern_match(self.target.address, self.tag, p.pattern.pattern, description, config['verbose'])
								file.writelines(description + '\n\n')
					else:
						# Use modern status display for pattern matches (no description)
						match_text = line[match.start():match.end()]
						if is_loading_active():
							record_tool_activity("pattern_match")
							scan_status.show_pattern_match(self.target.address, self.tag, p.pattern.pattern, match_text, config['verbose'])
						else:
							scan_status.show_pattern_match(self.target.address, self.tag, p.pattern.pattern, match_text, config['verbose'])
						async with self.target.lock:
							with open(os.path.join(self.target.scandir, '_patterns.log'), 'a') as file:
								file.writelines('Matched Pattern: ' + match_text + '\n\n')

			if self.outfile is not None:
				with open(self.outfile, 'a') as writer:
					writer.write(line + '\n')
			self.lines.append(line)
		self.ended = True

	# Read a line from the stream cache.
	async def readline(self):
		while True:
			try:
				return self.lines.pop(0)
			except IndexError:
				if self.ended:
					return None
				else:
					await asyncio.sleep(0.1)

	# Read all lines from the stream cache.
	async def readlines(self):
		lines = []
		while True:
			line = await self.readline()
			if line is not None:
				lines.append(line)
			else:
				break
		return lines

# Modern UI Functions (requires rich library)
def show_modern_help(version: str = "0.1.0-alpha"):
	"""Display modern help interface using rich"""
	if not RICH_AVAILABLE:
		print("ipcrawler help - install rich library for enhanced interface")
		return
		
	# Spider theme colors
	theme_color = "cyan"
	accent_color = "bright_magenta"
	success_color = "green"
	
	# Banner
	banner_text = Text()
	banner_text.append("🕷️  ipcrawler", style=f"bold {theme_color}")
	banner_text.append("  🕸️", style=f"dim {accent_color}")
	subtitle = Text("Smart Network Reconnaissance Made Simple", style=f"italic {accent_color}")
	
	console.print(Panel(
		Align.center(Text.assemble(banner_text, "\n", subtitle)),
		box=box.DOUBLE, border_style=theme_color, padding=(1, 2)
	))
	console.print()
	
	# Usage
	usage_text = Text.assemble(
		("Usage: ", "bold white"), ("ipcrawler ", f"bold {theme_color}"),
		("[OPTIONS] ", f"{accent_color}"), ("TARGET(S)", f"bold {success_color}")
	)
	console.print(Panel(usage_text, title="🎯 Usage", border_style=theme_color, box=box.ROUNDED))
	console.print()
	
	# Examples
	examples = [
		("Single target", "ipcrawler 192.168.1.100"),
		("CIDR range", "ipcrawler 192.168.1.0/24"),
		("Multiple targets", "ipcrawler 10.0.0.1 10.0.0.2 target.com"),
		("From file", "ipcrawler -t targets.txt"),
		("Custom ports", "ipcrawler -p 80,443,8080 target.com"),
		("Verbose scan", "ipcrawler -vv target.com"),
		("Fast scan", "ipcrawler --fast target.com"),
		("CTF mode", "ipcrawler --ctf target.com"),
		("Stealth scan", "ipcrawler --stealth target.com")
	]
	
	examples_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
	examples_table.add_column("Description", style=f"{accent_color}")
	examples_table.add_column("Command", style=f"bold {theme_color}")
	
	for desc, cmd in examples:
		examples_table.add_row(f"🔸 {desc}", cmd)
	
	console.print(Panel(examples_table, title="⚡ Quick Examples", border_style=theme_color, box=box.ROUNDED))
	console.print()
	
	# Core options
	core_options = [
		("-t, --target-file", "Read targets from file", "FILE"),
		("-p, --ports", "Custom ports to scan", "PORTS"),
		("-o, --output", "Output directory for results", "DIR"),
		("-m, --max-scans", "Max concurrent scans", "NUM"),
		("-v, --verbose", "Verbose output (repeat for more)", ""),
		("-l, --list", "List available plugins", "[TYPE]"),
		("--tags", "Include plugins with tags", "TAGS"),
		("--exclude-tags", "Exclude plugins with tags", "TAGS"),
		("--timeout", "Max scan time in minutes", "MIN"),
		("--target-timeout", "Max time per target in minutes", "MIN"),
		("--heartbeat", "Status update interval in seconds", "SEC"),
		("--proxychains", "Run through proxychains", ""),
		("--accessible", "Screenreader-friendly output", ""),
		("--version", "Show version and exit", ""),
		("-h, --help", "Show this help message", "")
	]
	
	options_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
	options_table.add_column("Option", style=f"bold {theme_color}", width=22)
	options_table.add_column("Description", style="white", width=35)
	options_table.add_column("Value", style=f"dim {accent_color}", width=8)
	
	for option, desc, value in core_options:
		options_table.add_row(option, desc, value)
	
	console.print(Panel(options_table, title="🛠️  Core Options", border_style=theme_color, box=box.ROUNDED))
	console.print()
	
	# Scan scenarios
	speed_options = [
		("--fast", "Quick scans with small wordlists", "5-15 min/service"),
		("--comprehensive", "Thorough scans with large wordlists", "30-120 min/service"),
		("--wordlist-size SIZE", "Manual wordlist size selection", "fast|default|comprehensive"),
		("(default)", "Medium wordlists when no flags used", "15-45 min/service")
	]
	
	speed_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
	speed_table.add_column("Option", style=f"bold {success_color}", width=22)
	speed_table.add_column("Description", style="white", width=35)
	speed_table.add_column("Time", style=f"dim {accent_color}", width=20)
	
	for option, desc, time in speed_options:
		speed_table.add_row(option, desc, time)
	
	console.print(Panel(speed_table, title="⚡ Speed Control", border_style=success_color, box=box.ROUNDED))
	console.print()
	
	# Scenario presets
	scenario_options = [
		("--ctf", "CTF/lab mode: balanced + high threads", "Practice environments"),
		("--pentest", "Penetration testing mode", "Real-world assessments"),
		("--recon", "Quick reconnaissance mode", "Initial discovery"),
		("--stealth", "Stealth mode: reduced threads", "Evasive scanning"),
		("(default)", "Standard scan with default plugins", "Balanced approach")
	]
	
	scenario_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
	scenario_table.add_column("Option", style=f"bold {accent_color}", width=22)
	scenario_table.add_column("Description", style="white", width=35)
	scenario_table.add_column("Use Case", style=f"dim {success_color}", width=20)
	
	for option, desc, use_case in scenario_options:
		scenario_table.add_row(option, desc, use_case)
	
	console.print(Panel(scenario_table, title="🎯 Scan Scenarios", border_style=accent_color, box=box.ROUNDED))
	console.print()
	
	# Default behavior explanation
	default_info = [
		("🔸 Without flags", "Uses medium-sized wordlists and balanced settings"),
		("🔸 Plugin selection", "Runs 'default' tagged plugins (most common tools)"),
		("🔸 Wordlist sources", "Auto-detects SecLists or falls back to built-in lists"),
		("🔸 Time estimate", "~15-45 minutes per service depending on findings")
	]
	
	default_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
	default_table.add_column("Behavior", style=f"{success_color}", width=20)
	default_table.add_column("Description", style="dim white", width=45)
	
	for behavior, desc in default_info:
		default_table.add_row(behavior, desc)
	
	console.print(Panel(default_table, title="ℹ️  Default Behavior", border_style=f"dim {success_color}", box=box.ROUNDED))
	console.print()
	
	# Footer
	footer_text = Text.assemble(
		(f"ipcrawler v{version}", f"bold {theme_color}"),
		(" | Built for the cybersecurity community ", "dim white"),
		("🕷️", f"{accent_color}")
	)
	console.print(Panel(Align.center(footer_text), border_style=f"dim {accent_color}", box=box.SIMPLE))

def show_ascii_art():
	"""Display clean ASCII art for ipcrawler - uses single consistent design"""
	if PYFIGLET_AVAILABLE and RICH_AVAILABLE:
		# Create modern ASCII art with pyfiglet and rich styling
		ascii_text = pyfiglet.figlet_format("IPCRAWLER", font="slant")
		
		console.print("═" * 75, style="dim cyan")
		console.print()
		
		# Split lines and apply gradient colors
		lines = ascii_text.split('\n')
		colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'magenta']
		
		for i, line in enumerate(lines):
			if line.strip():
				color = colors[i % len(colors)]
				console.print(line, style=f"bold {color}")
			else:
				console.print(line)
		
		console.print()
		console.print("    🕷️  Multi-threaded Network Reconnaissance & Service Crawler  🕷️", style="bold bright_magenta")
		console.print()
		console.print("═" * 75, style="dim cyan")
		console.print()
		
	elif PYFIGLET_AVAILABLE:
		# Fallback to basic pyfiglet with termcolor if rich not available
		ascii_text = pyfiglet.figlet_format("IPCRAWLER", font="slant")
		
		print(colored("═" * 75, 'cyan'))
		print()
		
		lines = ascii_text.split('\n')
		colors = ['red', 'yellow', 'green', 'cyan', 'magenta', 'white']
		
		for i, line in enumerate(lines):
			if line.strip():
				color = colors[i % len(colors)]
				print(colored(line, color, attrs=['bold']))
			else:
				print(line)
		
		print()
		print(colored("    🕷️  Multi-threaded Network Reconnaissance & Service Crawler  🕷️", 'magenta', attrs=['bold']))
		print()
		print(colored("═" * 75, 'cyan'))
		print()
		
	else:
		# Final fallback - simple text banner
		banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║  ██╗██████╗  ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗        ║
║  ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗       ║
║  ██║██████╔╝██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝       ║
║  ██║██╔═══╝ ██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗       ║
║  ██║██║     ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║       ║
║  ╚═╝╚═╝      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝       ║
║                                                                              ║
║       🕷️  Multi-threaded Network Reconnaissance & Service Crawler  🕷️        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
		if RICH_AVAILABLE:
			console.print(banner, style="bold cyan")
		else:
			print(banner)

def show_modern_version(version: str = "0.1.0-alpha"):
	"""Display modern version using rich (includes ASCII art)"""
	show_ascii_art()
	print()
	
	if not RICH_AVAILABLE:
		print(f"ipcrawler v{version}")
		return
		
	version_text = Text.assemble(
		("🕷️  ", "cyan"), ("ipcrawler ", "bold cyan"),
		(f"v{version}", "bold green"), ("  🕸️", "dim bright_magenta")
	)
	console.print(Panel(Align.center(version_text), border_style="cyan", box=box.DOUBLE, padding=(1, 2)))

def show_version_only(version: str = "0.1.0-alpha"):
	"""Display just version info without ASCII art"""
	if not RICH_AVAILABLE:
		print(f"ipcrawler v{version}")
		return
		
	version_text = Text.assemble(
		("🕷️  ", "cyan"), ("ipcrawler ", "bold cyan"),
		(f"v{version}", "bold green"), ("  🕸️", "dim bright_magenta")
	)
	console.print(Panel(Align.center(version_text), border_style="cyan", box=box.DOUBLE, padding=(1, 2)))

def show_modern_plugin_list(plugin_types: Dict[str, List[Any]], list_type: str = "plugins"):
	"""Display modern plugin listing using rich"""
	if not RICH_AVAILABLE:
		print("Plugin list - install rich library for enhanced interface")
		return
		
	theme_color = "cyan"
	accent_color = "bright_magenta"
	
	# Banner
	banner_text = Text()
	banner_text.append("🕷️  ipcrawler", style=f"bold {theme_color}")
	banner_text.append("  🕸️", style=f"dim {accent_color}")
	subtitle = Text("Smart Network Reconnaissance Made Simple", style=f"italic {accent_color}")
	
	console.print(Panel(
		Align.center(Text.assemble(banner_text, "\n", subtitle)),
		box=box.DOUBLE, border_style=theme_color, padding=(1, 2)
	))
	console.print()
	
	# Determine what to show
	type_lower = list_type.lower()
	show_port = type_lower in ['plugin', 'plugins', 'port', 'ports', 'portscan', 'portscans']
	show_service = type_lower in ['plugin', 'plugins', 'service', 'services', 'servicescan', 'servicescans']
	show_report = type_lower in ['plugin', 'plugins', 'report', 'reports', 'reporting']
	
	# Port scan plugins
	if show_port and 'port' in plugin_types:
		port_table = Table(box=box.ROUNDED, show_header=True, header_style=f"bold {theme_color}")
		port_table.add_column("🎯 Plugin Name", style="bold white", width=25)
		port_table.add_column("Slug", style=f"{accent_color}", width=20)
		port_table.add_column("Description", style="dim white", width=50)
		
		for plugin in plugin_types['port']:
			description = plugin.description if hasattr(plugin, 'description') and plugin.description else "No description available"
			port_table.add_row(plugin.name, plugin.slug, description)
		
		console.print(Panel(port_table, title="🔍 Port Scan Plugins", border_style=theme_color, box=box.DOUBLE))
		console.print()
	
	# Service scan plugins
	if show_service and 'service' in plugin_types:
		service_table = Table(box=box.ROUNDED, show_header=True, header_style=f"bold {theme_color}")
		service_table.add_column("🎯 Plugin Name", style="bold white", width=25)
		service_table.add_column("Slug", style=f"{accent_color}", width=20)
		service_table.add_column("Description", style="dim white", width=50)
		
		for plugin in plugin_types['service']:
			description = plugin.description if hasattr(plugin, 'description') and plugin.description else "No description available"
			service_table.add_row(plugin.name, plugin.slug, description)
		
		console.print(Panel(service_table, title="🛠️  Service Scan Plugins", border_style=theme_color, box=box.DOUBLE))
		console.print()
	
	# Report plugins
	if show_report and 'report' in plugin_types:
		report_table = Table(box=box.ROUNDED, show_header=True, header_style=f"bold {theme_color}")
		report_table.add_column("🎯 Plugin Name", style="bold white", width=25)
		report_table.add_column("Slug", style=f"{accent_color}", width=20)
		report_table.add_column("Description", style="dim white", width=50)
		
		for plugin in plugin_types['report']:
			description = plugin.description if hasattr(plugin, 'description') and plugin.description else "No description available"
			report_table.add_row(plugin.name, plugin.slug, description)
		
		console.print(Panel(report_table, title="📋 Report Plugins", border_style=theme_color, box=box.DOUBLE))
		console.print()
	
	# Usage tips
	tips = [
		("🔸 Use tags to filter:", "--tags safe,web"),
		("🔸 Exclude specific types:", "--exclude-tags slow"),
		("🔸 Override plugin selection:", "--service-scans dirbuster,nikto"),
		("🔸 List specific types:", "-l service, -l port, -l report")
	]
	
	tips_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
	tips_table.add_column("Tip", style=f"{accent_color}", width=25)
	tips_table.add_column("Example", style=f"bold {theme_color}", width=35)
	
	for tip, example in tips:
		tips_table.add_row(tip, example)
	
	console.print(Panel(tips_table, title="💡 Plugin Usage Tips", border_style=f"dim {accent_color}", box=box.ROUNDED))
