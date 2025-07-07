import asyncio, colorama, os, re, string, sys, unidecode
from colorama import Fore, Style
from ipcrawler.config import config

# Import UserDisplay but handle circular import
try:
    from ipcrawler.user_display import user_display
    USER_DISPLAY_AVAILABLE = True
except ImportError:
    USER_DISPLAY_AVAILABLE = False
    user_display = None

# ASCII art imports
try:
	import pyfiglet
	from termcolor import colored
	PYFIGLET_AVAILABLE = True
except ImportError:
	PYFIGLET_AVAILABLE = False

# Rich availability check (for basic fallbacks only)
try:
	from rich.console import Console
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

def cprint(*args, color=Fore.RESET, char='*', sep=' ', end='\n', frame_index=1, file=sys.stdout, printmsg=True, **kvargs):
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
	# Format the message
	message = sep.join(str(arg) for arg in args)
	
	# Use new UserDisplay if available
	if USER_DISPLAY_AVAILABLE and user_display:
		user_display.status_debug(message)
	else:
		# Fallback to old system
		if config['accessible']:
			args = ('Debug:',) + args
		cprint(*args, color=color, char=None, sep=sep, end=end, file=file, frame_index=2, **kvargs)

def info(*args, sep=' ', end='\n', file=sys.stdout, **kvargs):
	# Format the message
	message = sep.join(str(arg) for arg in args)
	
	# Use new UserDisplay if available
	if USER_DISPLAY_AVAILABLE and user_display:
		user_display.status_info(message)
	else:
		# Fallback to old system
		cprint(*args, color=Fore.BLUE, char=None, sep=sep, end=end, file=file, frame_index=2, **kvargs)

def warn(*args, sep=' ', end='\n', file=sys.stderr,**kvargs):
	# Format the message
	message = sep.join(str(arg) for arg in args)
	
	# Use new UserDisplay if available
	if USER_DISPLAY_AVAILABLE and user_display:
		user_display.status_warning(message)
	else:
		# Fallback to old system
		if config['accessible']:
			args = ('Warning:',) + args
		cprint(*args, color=Fore.YELLOW, char=None, sep=sep, end=end, file=file, frame_index=2, **kvargs)

def error(*args, sep=' ', end='\n', file=sys.stderr, **kvargs):
	# Format the message
	message = sep.join(str(arg) for arg in args)
	
	# Use new UserDisplay if available
	if USER_DISPLAY_AVAILABLE and user_display:
		user_display.status_error(message)
	else:
		# Fallback to old system
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
			except (ValueError, asyncio.LimitOverrunError) as e:
				# Handle lines longer than 64KB (common with large JSON responses from Spring Boot actuator)
				if ("line is longer than" in str(e) or "too long" in str(e) or 
				    "Separator is not found, and chunk exceed the limit" in str(e) or
				    "Separator is found, but chunk is longer than limit" in str(e)):
					try:
						# Try to read the oversized line in chunks
						line_chunks = []
						chunk_size = 32768  # 32KB chunks
						
						# Read data until we find a newline or EOF
						while True:
							chunk_data = await self.stream.read(chunk_size)
							if not chunk_data:
								break
								
							try:
								chunk = chunk_data.decode('utf8')
								line_chunks.append(chunk)
								
								# If we find a newline, we've got the complete line
								if '\n' in chunk:
									# Split on newline and keep the first part
									chunk_lines = chunk.split('\n')
									line_chunks[-1] = chunk_lines[0]  # Replace last chunk with part before newline
									
									# Put back any remaining data after the newline
									remaining_data = '\n'.join(chunk_lines[1:])
									if remaining_data:
										# This is tricky - we can't easily put data back into the stream
										# For now, we'll log this and continue
										pass
									break
							except UnicodeDecodeError:
								# Skip invalid UTF-8 chunks
								continue
						
						# Reconstruct the full line
						line = ''.join(line_chunks).rstrip()
						
						# Log that we handled a large line
						if line:
							info(f'[{self.target.address}/{self.tag}] 📥 Processed large response ({len(line)} bytes) - likely JSON from actuator endpoint')
						else:
							# If we still can't read it, skip and continue
							warn(f'[{self.target.address}/{self.tag}] ⚠️ Skipped oversized line that could not be processed')
							continue
							
					except Exception as chunk_error:
						# If chunk reading also fails, log and skip
						warn(f'[{self.target.address}/{self.tag}] ⚠️ Could not process large line: {str(chunk_error)[:100]}...')
						continue
				else:
					# Other ValueError, re-raise
					raise e

			if line != '':
				# Check for nmap timing output and display it prominently
				import re
				# Match various nmap timing formats
				nmap_timing_patterns = [
					r'(?:.*Timing: )?About\s+([\d.]+)%\s+done.*?ETC:\s+(\d{1,2}:\d{2})\s+\(([^)]+)\s+remaining\)',
					r'SYN\s+Stealth\s+Scan\s+Timing:\s+About\s+([\d.]+)%\s+done.*?ETC:\s+(\d{1,2}:\d{2})\s+\(([^)]+)\s+remaining\)',
					r'Stats:\s+.*?(\d+:\d+:\d+)\s+elapsed.*?ETC:\s+(\d{1,2}:\d{2})'
				]
				
				timing_match = None
				for pattern in nmap_timing_patterns:
					timing_match = re.search(pattern, line)
					if timing_match:
						break
				
				if timing_match:
					# Extract timing info based on what was matched
					groups = timing_match.groups()
					
					# Display nmap timing prominently - this should stay visible
					from rich.console import Console
					from rich.text import Text
					timing_console = Console()
					
					timing_text = Text()
					timing_text.append("📝 ", style="cyan bold")
					timing_text.append(f"[{self.target.address}/{self.tag}] ", style="yellow")
					
					# Handle different timing formats
					if len(groups) >= 3 and groups[0] and groups[1] and groups[2]:
						# Full timing with percentage, ETC, and remaining
						percentage, etc_time, remaining = groups[0], groups[1], groups[2]
						timing_text.append("SYN Stealth Scan Timing: ", style="white")
						timing_text.append(f"About {percentage}% done", style="green bold")
						timing_text.append(f"; ETC: {etc_time} ", style="white")
						timing_text.append(f"({remaining} remaining)", style="cyan")
					elif len(groups) >= 2:
						# Simplified timing with just ETC
						timing_text.append("Nmap Scan Progress: ", style="white")
						timing_text.append(f"ETC: {groups[1]}", style="cyan")
					else:
						# Fallback - show the original line
						timing_text.append("Nmap Timing: ", style="white")
						timing_text.append(line.strip(), style="dim white")
					
					timing_console.print(timing_text)
				else:
					# Record activity for loading interface
					if USER_DISPLAY_AVAILABLE and user_display:
						if user_display.is_loading_active():
							user_display.record_activity("output")
							# Only show command output for tools that don't have pattern matching
							# or for debugging when explicitly requested
							if not self.patterns or config.get('show_all_output', False):
								user_display.show_command_output(self.target.address, self.tag, line.strip())
					else:
						# Use Rich console for consistency (only when explicitly requested)
						if config.get('show_all_output', False):
							from rich.console import Console
							Console().print(f"📝 [{self.target.address}/{self.tag}] {line.strip()}", style="dim white")

			# Check lines for pattern matches with deduplication
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

						# Pattern deduplication: Check if we've already seen this exact description
						if not hasattr(self.target, '_seen_patterns'):
							self.target._seen_patterns = set()
						
						pattern_key = f"{self.tag}:{description}"
						if pattern_key not in self.target._seen_patterns:
							self.target._seen_patterns.add(pattern_key)
							
							async with self.target.lock:
								with open(os.path.join(self.target.scandir, '_patterns.log'), 'a') as file:
									# Record pattern match activity and use modern status display
									if USER_DISPLAY_AVAILABLE and user_display:
										if user_display.is_loading_active():
											user_display.record_activity("pattern_match")
										user_display.show_pattern_match(self.target.address, self.tag, p.pattern.pattern, description)
									file.writelines(description + '\n\n')
						else:
							# Pattern already seen - increment counter if needed
							if not hasattr(self.target, '_pattern_counts'):
								self.target._pattern_counts = {}
							
							if pattern_key not in self.target._pattern_counts:
								self.target._pattern_counts[pattern_key] = 2  # First duplicate
							else:
								self.target._pattern_counts[pattern_key] += 1
							
							# Only log the first few duplicates to avoid spam
							if self.target._pattern_counts[pattern_key] <= 3:
								async with self.target.lock:
									with open(os.path.join(self.target.scandir, '_patterns.log'), 'a') as file:
										if self.target._pattern_counts[pattern_key] == 2:
											file.writelines(f"[DUPLICATE] {description} (seen {self.target._pattern_counts[pattern_key]}x total)\n\n")
										elif self.target._pattern_counts[pattern_key] == 3:
											file.writelines(f"[DUPLICATE] {description} (seen {self.target._pattern_counts[pattern_key]}x total - suppressing further duplicates)\n\n")
					else:
						# Use modern status display for pattern matches (no description)
						match_text = line[match.start():match.end()]
						
						# Pattern deduplication for non-description patterns
						if not hasattr(self.target, '_seen_patterns'):
							self.target._seen_patterns = set()
						
						pattern_key = f"{self.tag}:Matched Pattern: {match_text}"
						if pattern_key not in self.target._seen_patterns:
							self.target._seen_patterns.add(pattern_key)
							
							if USER_DISPLAY_AVAILABLE and user_display:
								if user_display.is_loading_active():
									user_display.record_activity("pattern_match")
								user_display.show_pattern_match(self.target.address, self.tag, p.pattern.pattern, match_text)
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

# Modern UI functions moved to user_display.py to avoid duplication

# ASCII art functions moved to user_display.py to avoid duplication

# Version and plugin list functions moved to user_display.py to avoid duplication
