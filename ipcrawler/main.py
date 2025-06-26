#!/usr/bin/python3

import argparse, asyncio, importlib.util, inspect, ipaddress, math, os, re, select, shutil, signal, socket, sys, termios, time, traceback, tty
from datetime import datetime

try:
	import colorama, impacket, platformdirs, psutil, requests, rich, toml, unidecode
	from colorama import Fore, Style
except ModuleNotFoundError:
	print('One or more required modules was not installed. Please run or re-run: ' + ('sudo ' if os.getuid() == 0 else '') + 'python3 -m pip install -r requirements.txt')
	sys.exit(1)

# Optional Sentry SDK import for development/debugging
# To enable Sentry error tracking and performance monitoring:
# 1. Install sentry-sdk: pip install sentry-sdk
# 2. Set environment variable: export SENTRY_DSN="your_sentry_dsn_here"
# 3. Run ipcrawler normally - Sentry will automatically capture errors and performance data
# Note: This is intended for developers only - end users should not have this enabled
try:
	import sentry_sdk
	SENTRY_AVAILABLE = True
except ModuleNotFoundError:
	SENTRY_AVAILABLE = False

colorama.init()

from ipcrawler.config import config, configurable_keys, configurable_boolean_keys
from ipcrawler.io import slugify, e, fformat, cprint, debug, info, warn, error, fail, CommandStreamReader, show_modern_help, show_modern_version, show_modern_plugin_list, show_ascii_art
from ipcrawler.loading import scan_status
from ipcrawler.plugins import Pattern, PortScan, ServiceScan, Report, ipcrawler
from ipcrawler.targets import Target, Service
from ipcrawler.wordlists import init_wordlist_manager
from ipcrawler.consolidator import IPCrawlerConsolidator

VERSION = "0.1.0-alpha"

class ModernHelpAction(argparse.Action):
	"""Custom help action to display modern UI"""
	def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
		super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)
	
	def __call__(self, parser, namespace, values, option_string=None):
		show_modern_help(VERSION)
		parser.exit()

def copy_tree_ignore_broken_symlinks(src, dst):
	"""Copy directory tree, ignoring broken symlinks"""
	def ignore_broken_symlinks(dir, files):
		ignore = []
		for file in files:
			file_path = os.path.join(dir, file)
			if os.path.islink(file_path) and not os.path.exists(file_path):
				ignore.append(file)
		return ignore
	
	shutil.copytree(src, dst, ignore=ignore_broken_symlinks)

# IPCrawler should only work from git repository directory - no system config caching
# This ensures git pull updates are immediately effective

# if not os.path.exists(config['config_dir']):
# 	shutil.rmtree(config['config_dir'], ignore_errors=True, onerror=None)
# 	os.makedirs(config['config_dir'], exist_ok=True)
# 	open(os.path.join(config['config_dir'], 'VERSION-' + VERSION), 'a').close()
# 	shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.toml'), os.path.join(config['config_dir'], 'config.toml'))
# 	shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'global.toml'), os.path.join(config['config_dir'], 'global.toml'))
# else:
# 	if not os.path.exists(os.path.join(config['config_dir'], 'config.toml')):
# 		shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.toml'), os.path.join(config['config_dir'], 'config.toml'))
# 	if not os.path.exists(os.path.join(config['config_dir'], 'global.toml')):
# 		shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'global.toml'), os.path.join(config['config_dir'], 'global.toml'))
# 	if not os.path.exists(os.path.join(config['config_dir'], 'VERSION-' + VERSION)):
# 		warn('It looks like the config in ' + config['config_dir'] + ' is outdated. Please remove the ' + config['config_dir'] + ' directory and re-run ipcrawler to rebuild it.')


# Create minimal data directory only for wordlists.toml if needed
if not os.path.exists(config['data_dir']):
	os.makedirs(config['data_dir'], exist_ok=True)
# No plugin copying - plugins are loaded directly from git repository


# Saves current terminal settings so we can restore them.
terminal_settings = None

# Global args for consolidator on interruption
consolidator_args_global = None

ipcrawler = ipcrawler()

def calculate_elapsed_time(start_time, short=False):
	elapsed_seconds = round(time.time() - start_time)

	m, s = divmod(elapsed_seconds, 60)
	h, m = divmod(m, 60)

	elapsed_time = []
	if short:
		elapsed_time.append(str(h).zfill(2))
	else:
		if h == 1:
			elapsed_time.append(str(h) + ' hour')
		elif h > 1:
			elapsed_time.append(str(h) + ' hours')

	if short:
		elapsed_time.append(str(m).zfill(2))
	else:
		if m == 1:
			elapsed_time.append(str(m) + ' minute')
		elif m > 1:
			elapsed_time.append(str(m) + ' minutes')

	if short:
		elapsed_time.append(str(s).zfill(2))
	else:
		if s == 1:
			elapsed_time.append(str(s) + ' second')
		elif s > 1:
			elapsed_time.append(str(s) + ' seconds')
		else:
			elapsed_time.append('less than a second')

	if short:
		return ':'.join(elapsed_time)
	else:
		return ', '.join(elapsed_time)

# sig and frame args are only present so the function
# works with signal.signal() and handles Ctrl-C.
# They are not used for any other purpose.
def cancel_all_tasks(sig, frame):
	for task in asyncio.all_tasks():
		task.cancel()
	

	processes = []

	for target in ipcrawler.scanning_targets:
		for process_list in target.running_tasks.values():
			for process_dict in process_list['processes']:
				try:
					parent = psutil.Process(process_dict['process'].pid)
					processes.extend(parent.children(recursive=True))
					processes.append(parent)
				except psutil.NoSuchProcess:
					pass
	
	for process in processes:
		try:
			process.send_signal(signal.SIGKILL)
		except psutil.NoSuchProcess: # Will get raised if the process finishes before we get to killing it.
			pass
					
	_, alive = psutil.wait_procs(processes, timeout=10)
	if len(alive) > 0:
		error('The following process IDs could not be killed: ' + ', '.join([str(x.pid) for x in sorted(alive, key=lambda x: x.pid)]))
	
	# Generate consolidator HTML report on interruption
	if consolidator_args_global is not None:
		try:
			consolidator = IPCrawlerConsolidator(config['output'])
			
			# Set target filter if specified
			if hasattr(consolidator_args_global, 'report_target') and consolidator_args_global.report_target:
				consolidator.specific_target = consolidator_args_global.report_target
			
			# Generate report from existing files
			output_file = getattr(consolidator_args_global, 'report_output', None)
			if hasattr(consolidator_args_global, 'partial') and consolidator_args_global.partial:
				consolidator.generate_partial_report(output_file)
			else:
				consolidator.generate_html_report(output_file)
			
			info('🕷️  HTML report generated after interruption', verbosity=1)
		except Exception as e:
			warn(f'Failed to generate HTML report after interruption: {e}')

	if not config['disable_keyboard_control']:
		# Restore original terminal settings.
		if terminal_settings is not None:
			termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, terminal_settings)

async def start_heartbeat(target, period=60):
	while True:
		await asyncio.sleep(period)
		async with target.lock:
			count = len(target.running_tasks)

			# Show heartbeat messages to provide progress updates
			if config['verbose'] >= 1 and count > 0:
				tasks_list = []
				for tag, task in target.running_tasks.items():
					task_str = tag

					if config['verbose'] >= 3:
						processes = []
						for process_dict in task['processes']:
							if process_dict['process'].returncode is None:
								processes.append(str(process_dict['process'].pid))
								try:
									for child in psutil.Process(process_dict['process'].pid).children(recursive=True):
										processes.append(str(child.pid))
								except psutil.NoSuchProcess:
									pass
						
						if processes:
							task_str += ' (PIDs: ' + ', '.join(processes) + ')'
						
					tasks_list.append(task_str)

				# Create beautiful progress summary
				active_scans = []
				for tag, task in target.running_tasks.items():
					# Calculate duration
					start_time = task.get('start', time.time())
					elapsed = time.time() - start_time
					duration = calculate_elapsed_time(start_time, short=True)
					
					# Extract tool name and target from tag
					parts = tag.split('/')
					if len(parts) >= 2:
						tool_name = task.get('plugin', {}).name if hasattr(task.get('plugin', {}), 'name') else parts[-1]
						target_info = f"{target.address}:{parts[1]}" if parts[1].isdigit() else target.address
					else:
						tool_name = tag
						target_info = target.address
					
					active_scans.append({
						'tool': tool_name,
						'target': target_info,
						'duration': duration
					})
				
				# Show beautiful progress summary
				scan_status.show_progress_summary(active_scans, config['verbose'])

async def keyboard():
	input = ''
	while True:
		if select.select([sys.stdin],[],[],0.1)[0]:
			input += sys.stdin.buffer.read1(-1).decode('utf8')
			while input != '':
				if len(input) >= 3:
					if input[:3] == '\x1b[A':
						input = ''
						if config['verbose'] == 3:
							info('🔊 Verbosity already at maximum level', verbosity=0)
						else:
							config['verbose'] += 1
							info(f'🔊 Verbosity increased to {config["verbose"]}', verbosity=0)
					elif input[:3] == '\x1b[B':
						input = ''
						if config['verbose'] == 0:
							info('🔇 Verbosity already at minimum level', verbosity=0)
						else:
							config['verbose'] -= 1
							info(f'🔉 Verbosity decreased to {config["verbose"]}', verbosity=0)
					else:
						if input[0] != 's':
							input = input[1:]

				if len(input) > 0 and input[0] == 's':
					input = input[1:]
					for target in ipcrawler.scanning_targets:
						async with target.lock:
							count = len(target.running_tasks)

							if count > 0:
								current_time = datetime.now().strftime('%H:%M:%S')
								
								# Simple status display
								tasks_list = []
								for tag, task in target.running_tasks.items():
									elapsed_time = calculate_elapsed_time(task['start'], short=True)
									task_str = f"{tag} ({elapsed_time})"
									
									if config['verbose'] >= 2:
										processes = []
										for process_dict in task['processes']:
											if process_dict['process'].returncode is None:
												processes.append(str(process_dict['process'].pid))
										if processes:
											task_str += f" [PIDs: {', '.join(processes)}]"
									
									tasks_list.append(task_str)

								# Clean status message
								if count > 1:
									info(f'{current_time} - {count} scans active on {target.address}:')
									for task in tasks_list:
										info(f'  • {task}')
								elif count == 1:
									info(f'{current_time} - 1 scan active on {target.address}: {tasks_list[0]}')
				else:
					input = input[1:]
		await asyncio.sleep(0.1)

async def get_semaphore(ipcrawler):
	semaphore = ipcrawler.service_scan_semaphore
	while True:
		# If service scan semaphore is locked, see if we can use port scan semaphore.
		if semaphore.locked():
			if semaphore != ipcrawler.port_scan_semaphore: # This will be true unless user sets max_scans == max_port_scans

				port_scan_task_count = 0
				for target in ipcrawler.scanning_targets:
					for process_list in target.running_tasks.values():
						if issubclass(process_list['plugin'].__class__, PortScan):
							port_scan_task_count += 1

				if not ipcrawler.pending_targets and (config['max_port_scans'] - port_scan_task_count) >= 1: # If no more targets, and we have room, use port scan semaphore.
					if ipcrawler.port_scan_semaphore.locked():
						await asyncio.sleep(1)
						continue
					semaphore = ipcrawler.port_scan_semaphore
					break
				else: # Do some math to see if we can use the port scan semaphore.
					if (config['max_port_scans'] - (port_scan_task_count + (len(ipcrawler.pending_targets) * config['port_scan_plugin_count']))) >= 1:
						if ipcrawler.port_scan_semaphore.locked():
							await asyncio.sleep(1)
							continue
						semaphore = ipcrawler.port_scan_semaphore
						break
					else:
						await asyncio.sleep(1)
			else:
				break
		else:
			break
	return semaphore

async def port_scan(plugin, target):
	if config['ports']:
		if config['ports']['tcp'] or config['ports']['udp']:
			target.ports = {'tcp':None, 'udp':None}
			if config['ports']['tcp']:
				target.ports['tcp'] = ','.join(config['ports']['tcp'])
			if config['ports']['udp']:
				target.ports['udp'] = ','.join(config['ports']['udp'])
			if plugin.specific_ports is False:
				warn(f'⚠️ Port scan {plugin.name} ({plugin.slug}) cannot scan specific ports with --ports. Skipping.', verbosity=2)
				return {'type':'port', 'plugin':plugin, 'result':[]}
			else:
				if plugin.type == 'tcp' and not config['ports']['tcp']:
					warn(f'⚠️ Port scan {plugin.name} ({plugin.slug}) is TCP but no TCP ports set with --ports. Skipping.', verbosity=2)
					return {'type':'port', 'plugin':plugin, 'result':[]}
				elif plugin.type == 'udp' and not config['ports']['udp']:
					warn(f'⚠️ Port scan {plugin.name} ({plugin.slug}) is UDP but no UDP ports set with --ports. Skipping.', verbosity=2)
					return {'type':'port', 'plugin':plugin, 'result':[]}

	async with target.ipcrawler.port_scan_semaphore:
		# Show beautiful scan start message
		scan_status.show_scan_start(target.address, plugin.name, config['verbose'])

		start_time = time.time()

		async with target.lock:
			target.running_tasks[plugin.slug] = {'plugin': plugin, 'processes': [], 'start': start_time}

		try:
			result = await plugin.run(target)
		except Exception as ex:
			exc_type, exc_value, exc_tb = sys.exc_info()
			error_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
			error(f'❌ Port scan {plugin.name} ({plugin.slug}) → {target.address} failed with exception', verbosity=1)
			
			# Send plugin exception to Sentry if available
			if SENTRY_AVAILABLE:
				try:
					import sentry_sdk
					sentry_sdk.capture_exception(
						ex,
						extra={
							'plugin_name': plugin.name,
							'plugin_slug': plugin.slug,
							'target_address': target.address,
							'scan_type': 'port_scan',
							'error_traceback': error_text,
							'plugin_tags': getattr(plugin, 'tags', []),
							'plugin_description': getattr(plugin, 'description', '')
						}
					)
				except Exception:
					pass  # Don't let Sentry errors break the scan
			
			raise Exception(f'Port scan {plugin.name} ({plugin.slug}) → {target.address} exception:\n\n{error_text}')

		for process_dict in target.running_tasks[plugin.slug]['processes']:
			if process_dict['process'].returncode is None:
				warn(f'⚠️ Port scan {plugin.name} ({plugin.slug}) → {target.address} left process running, awaiting completion', verbosity=2)
				await process_dict['process'].wait()

			if process_dict['process'].returncode != 0:
				errors = []
				while True:
					line = await process_dict['stderr'].readline()
					if line is not None:
						errors.append(line + '\n')
					else:
						break
				error_msg = f'❌ Port scan {plugin.name} ({plugin.slug}) → {target.address} exited with code {process_dict["process"].returncode}. Check {target.scandir}/_errors.log'
				error(error_msg, verbosity=2)
				
				# Send exit code error to Sentry if available
				if SENTRY_AVAILABLE:
					try:
						import sentry_sdk
						sentry_sdk.capture_message(
							f'Port scan tool exited with non-zero code',
							level='error',
							extra={
								'plugin_name': plugin.name,
								'plugin_slug': plugin.slug,
								'target_address': target.address,
								'exit_code': process_dict['process'].returncode,
								'command': process_dict['cmd'],
								'stderr_output': ''.join(errors) if errors else 'No stderr output',
								'scan_type': 'port_scan'
							}
						)
					except Exception:
						pass  # Don't let Sentry errors break the scan
				
				async with target.lock:
					with open(os.path.join(target.scandir, '_errors.log'), 'a') as file:
						file.writelines(f'❌ Port scan {plugin.name} ({plugin.slug}) exited with code {process_dict["process"].returncode}\n')
						file.writelines(f'🔧 Command: {process_dict["cmd"]}\n')
						if errors:
							file.writelines(['❌ Error Output:\n'] + errors + ['\n'])
						else:
							file.writelines('\n')

		elapsed_time = calculate_elapsed_time(start_time)

		async with target.lock:
			target.running_tasks.pop(plugin.slug, None)

		# Show beautiful completion message
		scan_status.show_scan_completion(target.address, plugin.name, elapsed_time, True, config['verbose'])
		return {'type':'port', 'plugin':plugin, 'result':result}

async def service_scan(plugin, service):
	semaphore = service.target.ipcrawler.service_scan_semaphore

	if not config['force_services']:
		semaphore = await get_semaphore(service.target.ipcrawler)

	plugin_pending = True

	while plugin_pending:
		global_plugin_count = 0
		target_plugin_count = 0

		if plugin.max_global_instances and plugin.max_global_instances > 0:
			async with service.target.ipcrawler.lock:
				# Count currently running plugin instances.
				for target in service.target.ipcrawler.scanning_targets:
					for task in target.running_tasks.values():
						if plugin == task['plugin']:
							global_plugin_count += 1
							if global_plugin_count >= plugin.max_global_instances:
								break
					if global_plugin_count >= plugin.max_global_instances:
						break
			if global_plugin_count >= plugin.max_global_instances:
				await asyncio.sleep(1)
				continue

		if plugin.max_target_instances and plugin.max_target_instances > 0:
			async with service.target.lock:
				# Count currently running plugin instances.
				for task in service.target.running_tasks.values():
					if plugin == task['plugin']:
						target_plugin_count += 1
						if target_plugin_count >= plugin.max_target_instances:
							break
			if target_plugin_count >= plugin.max_target_instances:
				await asyncio.sleep(1)
				continue

		# If we get here, we can run the plugin.
		plugin_pending = False

		async with semaphore:
			# Create variables for fformat references.
			address = service.target.address
			addressv6 = service.target.address
			ipaddress = service.target.ip
			ipaddressv6 = service.target.ip
			scandir = service.target.scandir
			protocol = service.protocol
			port = service.port
			name = service.name

			if not config['no_port_dirs']:
				scandir = os.path.join(scandir, protocol + str(port))
				os.makedirs(scandir, exist_ok=True)
				os.makedirs(os.path.join(scandir, 'xml'), exist_ok=True)

			# Special cases for HTTP.
			http_scheme = 'https' if 'https' in service.name or service.secure is True else 'http'

			nmap_extra = service.target.ipcrawler.args.nmap
			if service.target.ipcrawler.args.nmap_append:
				nmap_extra += ' ' + service.target.ipcrawler.args.nmap_append

			if protocol == 'udp':
				nmap_extra += ' -sU'

			if service.target.ipversion == 'IPv6':
				nmap_extra += ' -6'
				if addressv6 == service.target.ip:
					addressv6 = '[' + addressv6 + ']'
				ipaddressv6 = '[' + ipaddressv6 + ']'

			if config['proxychains'] and protocol == 'tcp':
				nmap_extra += ' -sT'

			tag = service.tag() + '/' + plugin.slug

			# Show beautiful service scan start message
			scan_status.show_scan_start(f"{service.target.address}:{service.port}", plugin.name, config['verbose'])

			start_time = time.time()

			async with service.target.lock:
				service.target.running_tasks[tag] = {'plugin': plugin, 'processes': [], 'start': start_time}

			try:
				result = await plugin.run(service)
			except Exception as ex:
				exc_type, exc_value, exc_tb = sys.exc_info()
				error_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
				error(f'❌ Service scan {plugin.name} ({tag}) → {service.target.address}:{service.port} failed with exception', verbosity=1)
				
				# Send plugin exception to Sentry if available
				if SENTRY_AVAILABLE:
					try:
						import sentry_sdk
						sentry_sdk.capture_exception(
							ex,
							extra={
								'plugin_name': plugin.name,
								'plugin_slug': plugin.slug,
								'target_address': service.target.address,
								'target_port': service.port,
								'scan_type': 'service_scan',
								'service_name': service.name,
								'protocol': service.protocol,
								'error_traceback': error_text,
								'plugin_tags': getattr(plugin, 'tags', []),
								'plugin_description': getattr(plugin, 'description', '')
							}
						)
					except Exception:
						pass  # Don't let Sentry errors break the scan
				
				raise Exception(f'Service scan {plugin.name} ({tag}) → {service.target.address}:{service.port} exception:\n\n{error_text}')

			for process_dict in service.target.running_tasks[tag]['processes']:
				if process_dict['process'].returncode is None:
					warn(f'⚠️ Service scan {plugin.name} ({tag}) → {service.target.address}:{service.port} left process running, awaiting completion', verbosity=2)
					await process_dict['process'].wait()

				if process_dict['process'].returncode != 0 and not (process_dict['cmd'].startswith('curl') and process_dict['process'].returncode == 22):
					errors = []
					while True:
						line = await process_dict['stderr'].readline()
						if line is not None:
							errors.append(line + '\n')
						else:
							break
					error_msg = f'❌ Service scan {plugin.name} ({tag}) → {service.target.address}:{service.port} exited with code {process_dict["process"].returncode}. Check {service.target.scandir}/_errors.log'
					error(error_msg, verbosity=2)
					
					# Send exit code error to Sentry if available
					if SENTRY_AVAILABLE:
						try:
							import sentry_sdk
							sentry_sdk.capture_message(
								f'Service scan tool exited with non-zero code',
								level='error',
								extra={
									'plugin_name': plugin.name,
									'plugin_slug': plugin.slug,
									'target_address': service.target.address,
									'target_port': service.port,
									'exit_code': process_dict['process'].returncode,
									'command': process_dict['cmd'],
									'stderr_output': ''.join(errors) if errors else 'No stderr output',
									'scan_type': 'service_scan',
									'service_name': service.name,
									'protocol': service.protocol
								}
							)
						except Exception:
							pass  # Don't let Sentry errors break the scan
					
					async with service.target.lock:
						with open(os.path.join(service.target.scandir, '_errors.log'), 'a') as file:
							file.writelines(f'❌ Service scan {plugin.name} ({tag}) exited with code {process_dict["process"].returncode}\n')
							file.writelines(f'🔧 Command: {process_dict["cmd"]}\n')
							if errors:
								file.writelines(['❌ Error Output:\n'] + errors + ['\n'])
							else:
								file.writelines('\n')

			elapsed_time = calculate_elapsed_time(start_time)

			async with service.target.lock:
				service.target.running_tasks.pop(tag, None)

			# Show beautiful service completion message
			scan_status.show_scan_completion(f"{service.target.address}:{service.port}", plugin.name, elapsed_time, True, config['verbose'])
			return {'type':'service', 'plugin':plugin, 'result':result}

async def generate_report(plugin, targets):
	semaphore = ipcrawler.service_scan_semaphore

	if not config['force_services']:
		semaphore = await get_semaphore(ipcrawler)

	async with semaphore:
		try:
			result = await plugin.run(targets)
		except Exception as ex:
			exc_type, exc_value, exc_tb = sys.exc_info()
			error_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
			error(f'❌ Report plugin {plugin.name} ({plugin.slug}) failed with exception', verbosity=1)
			raise Exception(f'Report plugin {plugin.name} ({plugin.slug}) exception:\n\n{error_text}')

async def scan_target(target):
	os.makedirs(os.path.abspath(config['output']), exist_ok=True)

	if config['single_target']:
		basedir = os.path.abspath(config['output'])
	else:
		basedir = os.path.abspath(os.path.join(config['output'], target.address))
		os.makedirs(basedir, exist_ok=True)

	target.basedir = basedir

	scandir = os.path.join(basedir, 'scans')
	target.scandir = scandir
	os.makedirs(scandir, exist_ok=True)

	os.makedirs(os.path.join(scandir, 'xml'), exist_ok=True)

	if not config['only_scans_dir']:
		exploitdir = os.path.join(basedir, 'exploit')
		os.makedirs(exploitdir, exist_ok=True)

		lootdir = os.path.join(basedir, 'loot')
		os.makedirs(lootdir, exist_ok=True)

		reportdir = os.path.join(basedir, 'report')
		os.makedirs(reportdir, exist_ok=True)

		open(os.path.join(reportdir, 'local.txt'), 'a').close()
		open(os.path.join(reportdir, 'proof.txt'), 'a').close()

		screenshotdir = os.path.join(reportdir, 'screenshots')
		os.makedirs(screenshotdir, exist_ok=True)
	else:
		reportdir = scandir

	target.reportdir = reportdir

	pending = []

	heartbeat = asyncio.create_task(start_heartbeat(target, period=config['heartbeat']))

	services = []
	if config['force_services']:
		forced_services = [x.strip().lower() for x in config['force_services']]

		for forced_service in forced_services:
			match = re.search(r'(?P<protocol>(tcp|udp))\/(?P<port>\d+)\/(?P<service>[\w\-]+)(\/(?P<secure>secure|insecure))?', forced_service)
			if match:
				protocol = match.group('protocol')
				if config['proxychains'] and protocol == 'udp':
					error('The service ' + forced_service + ' uses UDP and --proxychains is enabled. Skipping.', verbosity=2)
					continue
				port = int(match.group('port'))
				service = match.group('service')
				secure = True if match.group('secure') == 'secure' else False
				service = Service(protocol, port, service, secure)
				service.target = target
				services.append(service)

		if services:
			pending.append(asyncio.create_task(asyncio.sleep(0)))
		else:
			error('No services were defined. Please check your service syntax: [tcp|udp]/<port>/<service-name>/[secure|insecure]')
			heartbeat.cancel()
			ipcrawler.errors = True
			return
	else:
		for plugin in target.ipcrawler.plugin_types['port']:
			if config['proxychains'] and plugin.type == 'udp':
				continue

			if config['port_scans'] and plugin.slug in config['port_scans']:
				matching_tags = True
				excluded_tags = False
			else:
				plugin_tag_set = set(plugin.tags)

				matching_tags = False
				for tag_group in target.ipcrawler.tags:
					if set(tag_group).issubset(plugin_tag_set):
						matching_tags = True
						break

				excluded_tags = False
				for tag_group in target.ipcrawler.excluded_tags:
					if set(tag_group).issubset(plugin_tag_set):
						excluded_tags = True
						break

			if matching_tags and not excluded_tags:
				target.scans['ports'][plugin.slug] = {'plugin':plugin, 'commands':[]}
				pending.append(asyncio.create_task(port_scan(plugin, target)))

	async with ipcrawler.lock:
		ipcrawler.scanning_targets.append(target)

	start_time = time.time()
	info(f'🎯 Scanning target: {target.address}', verbosity=1)

	timed_out = False
	while pending:
		done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=1)

		# Check if global timeout has occurred.
		if config['target_timeout'] is not None:
			elapsed_seconds = round(time.time() - start_time)
			m, s = divmod(elapsed_seconds, 60)
			if m >= config['target_timeout']:
				timed_out = True
				break

		if not config['force_services']:
			# Extract Services
			services = []

			async with target.lock:
				while target.pending_services:
					services.append(target.pending_services.pop(0))

			for task in done:
				try:
					if task.exception():
						print(task.exception())
						continue
				except asyncio.InvalidStateError:
					pass

				if task.result()['type'] == 'port':
					for service in (task.result()['result'] or []):
						services.append(service)

		for service in services:
			if service.full_tag() not in target.services:
				target.services.append(service.full_tag())
			else:
				continue

			# Show beautiful service discovery message
			scan_status.show_service_discovery(target.address, service.name, service.protocol, service.port, config['verbose'])

			if not config['only_scans_dir']:
				with open(os.path.join(target.reportdir, 'notes.txt'), 'a') as file:
					file.writelines(f'🎯 {service.name} found on {service.protocol}/{service.port}\n\n\n\n')

			service.target = target

			# Create variables for command references.
			address = target.address
			addressv6 = target.address
			ipaddress = target.ip
			ipaddressv6 = target.ip
			scandir = target.scandir
			protocol = service.protocol
			port = service.port

			if not config['no_port_dirs']:
				scandir = os.path.join(scandir, protocol + str(port))
				os.makedirs(scandir, exist_ok=True)
				os.makedirs(os.path.join(scandir, 'xml'), exist_ok=True)

			# Special cases for HTTP.
			http_scheme = 'https' if 'https' in service.name or service.secure is True else 'http'

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

			service_match = False
			matching_plugins = []
			heading = False

			for plugin in target.ipcrawler.plugin_types['service']:
				plugin_was_run = False
				plugin_service_match = False
				plugin_tag = service.tag() + '/' + plugin.slug

				for service_dict in plugin.services:
					if service_dict['protocol'] == protocol and port in service_dict['port']:
						for name in service_dict['name']:
							if service_dict['negative_match']:
								if name not in plugin.ignore_service_names:
									plugin.ignore_service_names.append(name)
							else:
								if name not in plugin.service_names:
									plugin.service_names.append(name)
					else:
						continue

				# Check if this plugin matches the discovered service
				for s in plugin.service_names:
					if re.search(s, service.name):
						plugin_service_match = True
						break

				# Only process the plugin if it matched the service
				if plugin_service_match:
					if config['service_scans'] and plugin.slug in config['service_scans']:
						matching_tags = True
						excluded_tags = False
					else:
						plugin_tag_set = set(plugin.tags)

						matching_tags = False
						for tag_group in target.ipcrawler.tags:
							if set(tag_group).issubset(plugin_tag_set):
								matching_tags = True
								break

						excluded_tags = False
						for tag_group in target.ipcrawler.excluded_tags:
							if set(tag_group).issubset(plugin_tag_set):
								excluded_tags = True
								break

					# TODO: Maybe make this less messy, keep manual-only plugins separate?
					plugin_is_runnable = False
					for member_name, _ in inspect.getmembers(plugin, predicate=inspect.ismethod):
						if member_name == 'run':
							plugin_is_runnable = True
							break

					if plugin_is_runnable and matching_tags and not excluded_tags:
						# Skip plugin if run_once_boolean and plugin already in target scans
						if plugin.run_once_boolean:
							plugin_queued = False
							for s in target.scans['services']:
								if plugin.slug in target.scans['services'][s]:
									plugin_queued = True
									warn(f'⚠️ Plugin {plugin_tag} → {target.address} already queued (run_once). Skipping.', verbosity=2)
									break
							if plugin_queued:
								continue  # Skip this plugin but continue with manual commands

						# Skip plugin if require_ssl_boolean and port is not secure
						if plugin.require_ssl_boolean and not service.secure:
							plugin_service_match = False
						# Skip plugin if service port is in ignore_ports:
						elif port in plugin.ignore_ports[protocol]:
							plugin_service_match = False
							warn(f'⚠️ Plugin {plugin_tag} → {target.address} cannot run on {protocol} port {port}. Skipping.', verbosity=2)
						# Skip plugin if plugin has required ports and service port is not in them:
						elif plugin.ports[protocol] and port not in plugin.ports[protocol]:
							plugin_service_match = False
							warn(f'⚠️ Plugin {plugin_tag} → {target.address} restricted to specific ports. Skipping.', verbosity=2)
						else:
							# Check ignore_service_names
							plugin_blocked = False
							for i in plugin.ignore_service_names:
								if re.search(i, service.name):
									warn(f'⚠️ Plugin {plugin_tag} → {target.address} cannot run against service {service.name}. Skipping.', verbosity=2)
									plugin_blocked = True
									break

							if not plugin_blocked:
								# Plugin is good to run!
								plugin_was_run = True
								matching_plugins.append(plugin)

					# Always generate manual commands for matching plugins
					for member_name, _ in inspect.getmembers(plugin, predicate=inspect.ismethod):
						if member_name == 'manual':
							try:
								plugin.manual(service, plugin_was_run)
							except Exception as ex:
								exc_type, exc_value, exc_tb = sys.exc_info()
								error_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
								error(f'❌ Service scan {plugin.name} ({plugin_tag}) → {target.address} failed generating manual commands', verbosity=1)

							if service.manual_commands:
								plugin_run = False
								for s in target.scans['services']:
									if plugin.slug in target.scans['services'][s]:
										plugin_run = True
										break
								if not plugin.run_once_boolean or (plugin.run_once_boolean and not plugin_run):
									with open(os.path.join(target.scandir, '_manual_commands.txt'), 'a') as file:
										if not heading:
											file.write(e('🎯 {service.name} on {service.protocol}/{service.port}\n\n'))
											heading = True
										for description, commands in service.manual_commands.items():
											try:
												file.write('\t🔧 ' + e(description) + '\n\n')
												for command in commands:
													file.write('\t\t' + e(command) + '\n\n')
											except Exception as ex:
												exc_type, exc_value, exc_tb = sys.exc_info()
												error_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
												error(f'❌ Service scan {plugin.name} ({plugin_tag}) → {target.address} failed evaluating manual commands', verbosity=1)
										file.flush()

							service.manual_commands = {}
							break

				if plugin_service_match:
					service_match = True

			for plugin in matching_plugins:
				plugin_tag = service.tag() + '/' + plugin.slug

				if plugin.run_once_boolean:
					plugin_tag = plugin.slug

				plugin_queued = False
				if service in target.scans['services']:
					for s in target.scans['services']:
						if plugin_tag in target.scans['services'][s]:
							plugin_queued = True
							warn(f'⚠️ Plugin {plugin_tag} → {target.address} already queued (not run_once). Possible duplicate? Skipping.', verbosity=2)
							break

				if plugin_queued:
					continue
				else:
					if service not in target.scans['services']:
						target.scans['services'][service] = {}
					target.scans['services'][service][plugin_tag] = {'plugin':plugin, 'commands':[]}

				pending.add(asyncio.create_task(service_scan(plugin, service)))

			if not service_match:
				warn(f'⚠️ [{target.address}] Service {service.full_tag()} did not match any plugins', verbosity=2)
				if service.name not in config['service_exceptions'] and service.full_tag() not in target.ipcrawler.missing_services:
					target.ipcrawler.missing_services.append(service.full_tag())

	for plugin in target.ipcrawler.plugin_types['report']:
		if config['reports'] and plugin.slug in config['reports']:
			matching_tags = True
			excluded_tags = False
		else:
			plugin_tag_set = set(plugin.tags)

			matching_tags = False
			for tag_group in target.ipcrawler.tags:
				if set(tag_group).issubset(plugin_tag_set):
					matching_tags = True
					break

			excluded_tags = False
			for tag_group in target.ipcrawler.excluded_tags:
				if set(tag_group).issubset(plugin_tag_set):
					excluded_tags = True
					break

		if matching_tags and not excluded_tags:
			pending.add(asyncio.create_task(generate_report(plugin, [target])))

	while pending:
		done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=1)

	heartbeat.cancel()
	elapsed_time = calculate_elapsed_time(start_time)

	if timed_out:

		for task in pending:
			task.cancel()

		for process_list in target.running_tasks.values():
			for process_dict in process_list['processes']:
				try:
					process_dict['process'].kill()
				except ProcessLookupError:
					pass

		warn(f'⏰ Target {target.address} timeout ({config["target_timeout"]} min). Moving to next target.', verbosity=0)
	else:
		info(f'✅ Target {target.address} completed in {elapsed_time}', verbosity=1)

	async with ipcrawler.lock:
		ipcrawler.completed_targets.append(target)
		ipcrawler.scanning_targets.remove(target)

async def run():
	# Find config file - use from git repository directly, no system caching
	git_config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.toml')
	if os.path.isfile(git_config_file):
		config_file = git_config_file
	else:
		config_file = None

	# Find global file - use from git repository directly, no system caching
	git_global_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'global.toml')
	if os.path.isfile(git_global_file):
		config['global_file'] = git_global_file
	else:
		config['global_file'] = None

	# Plugins are now loaded directly from git repository - no system directory needed
	# config['plugins_dir'] already set in config.py to the git repository location

	parser = argparse.ArgumentParser(prog='ipcrawler', add_help=False, allow_abbrev=False, description='Network reconnaissance tool to port scan and automatically enumerate services found on multiple targets.')
	parser.add_argument('targets', action='store', help='IP addresses (e.g. 10.0.0.1), CIDR notation (e.g. 10.0.0.1/24), or resolvable hostnames (e.g. foo.bar) to scan.', nargs='*')
	parser.add_argument('-t', '--target-file', action='store', type=str, default='', help='Read targets from file.')
	parser.add_argument('-p', '--ports', action='store', type=str, help='Comma separated list of ports / port ranges to scan. Specify TCP/UDP ports by prepending list with T:/U: To scan both TCP/UDP, put port(s) at start or specify B: e.g. 53,T:21-25,80,U:123,B:123. Default: %(default)s')
	parser.add_argument('-m', '--max-scans', action='store', type=int, help='The maximum number of concurrent scans to run. Default: %(default)s')
	parser.add_argument('-mp', '--max-port-scans', action='store', type=int, help='The maximum number of concurrent port scans to run. Default: 10 (approx 20%% of max-scans unless specified)')
	parser.add_argument('-c', '--config', action='store', type=str, default=config_file, dest='config_file', help='Location of ipcrawler\'s config file. Default: %(default)s')
	parser.add_argument('-g', '--global-file', action='store', type=str, help='Location of ipcrawler\'s global file. Default: %(default)s')
	parser.add_argument('--tags', action='store', type=str, default='default', help='Tags to determine which plugins should be included. Separate tags by a plus symbol (+) to group tags together. Separate groups with a comma (,) to create multiple groups. For a plugin to be included, it must have all the tags specified in at least one group. Default: %(default)s')
	parser.add_argument('--exclude-tags', action='store', type=str, default='', metavar='TAGS', help='Tags to determine which plugins should be excluded. Separate tags by a plus symbol (+) to group tags together. Separate groups with a comma (,) to create multiple groups. For a plugin to be excluded, it must have all the tags specified in at least one group. Default: %(default)s')
	parser.add_argument('--port-scans', action='store', type=str, metavar='PLUGINS', help='Override --tags / --exclude-tags for the listed PortScan plugins (comma separated). Default: %(default)s')
	parser.add_argument('--service-scans', action='store', type=str, metavar='PLUGINS', help='Override --tags / --exclude-tags for the listed ServiceScan plugins (comma separated). Default: %(default)s')
	parser.add_argument('--reports', action='store', type=str, metavar='PLUGINS', help='Override --tags / --exclude-tags for the listed Report plugins (comma separated). Default: %(default)s')
	parser.add_argument('--plugins-dir', action='store', type=str, help='The location of the plugins directory. Default: %(default)s')
	parser.add_argument('--add-plugins-dir', action='store', type=str, metavar='PLUGINS_DIR', help='The location of an additional plugins directory to add to the main one. Default: %(default)s')
	parser.add_argument('-l', '--list', action='store', nargs='?', const='plugins', metavar='TYPE', help='List all plugins or plugins of a specific type. Use --list consolidator to show consolidator usage. e.g. --list, --list port, --list service, --list consolidator')
	parser.add_argument('-o', '--output', action='store', help='The output directory for results. Default: %(default)s')
	parser.add_argument('--single-target', action='store_true', help='Only scan a single target. A directory named after the target will not be created. Instead, the directory structure will be created within the output directory. Default: %(default)s')
	parser.add_argument('--only-scans-dir', action='store_true', help='Only create the "scans" directory for results. Other directories (e.g. exploit, loot, report) will not be created. Default: %(default)s')
	parser.add_argument('--no-port-dirs', action='store_true', help='Don\'t create directories for ports (e.g. scans/tcp80, scans/udp53). Instead store all results in the "scans" directory itself. Default: %(default)s')
	parser.add_argument('--heartbeat', action='store', type=int, help='Specifies the heartbeat interval (in seconds) for scan status messages. Default: %(default)s')
	parser.add_argument('--timeout', action='store', type=int, help='Specifies the maximum amount of time in minutes that ipcrawler should run for. Default: %(default)s')
	parser.add_argument('--target-timeout', action='store', type=int, help='Specifies the maximum amount of time in minutes that a target should be scanned for before abandoning it and moving on. Default: %(default)s')
	nmap_group = parser.add_mutually_exclusive_group()
	nmap_group.add_argument('--nmap', action='store', help='Override the {nmap_extra} variable in scans. Default: %(default)s')
	nmap_group.add_argument('--nmap-append', action='store', help='Append to the default {nmap_extra} variable in scans. Default: %(default)s')
	parser.add_argument('--proxychains', action='store_true', help='Use if you are running ipcrawler via proxychains. Default: %(default)s')
	parser.add_argument('--disable-sanity-checks', action='store_true', help='Disable sanity checks that would otherwise prevent the scans from running. Default: %(default)s')
	parser.add_argument('--disable-keyboard-control', action='store_true', help='Disables keyboard control ([s]tatus, Up, Down) if you are in SSH or Docker.')
	parser.add_argument('--ignore-plugin-checks', action='store_true', help='Ignores errors from plugin check functions that would otherwise prevent ipcrawler from running. Default: %(default)s')
	parser.add_argument('--force-services', action='store', nargs='+', metavar='SERVICE', help='A space separated list of services in the following style: tcp/80/http tcp/443/https/secure')
	parser.add_argument('-mpti', '--max-plugin-target-instances', action='store', nargs='+', metavar='PLUGIN:NUMBER', help='A space separated list of plugin slugs with the max number of instances (per target) in the following style: nmap-http:2 dirbuster:1. Default: %(default)s')
	parser.add_argument('-mpgi', '--max-plugin-global-instances', action='store', nargs='+', metavar='PLUGIN:NUMBER', help='A space separated list of plugin slugs with the max number of global instances in the following style: nmap-http:2 dirbuster:1. Default: %(default)s')
	parser.add_argument('--accessible', action='store_true', help='Attempts to make ipcrawler output more accessible to screenreaders. Default: %(default)s')
	
	# Wordlist management arguments
	wordlist_group = parser.add_argument_group('wordlist management', 'Options for customizing wordlist paths')
	wordlist_group.add_argument('--wordlist-usernames', action='store', metavar='PATH', help='Override the usernames wordlist path')
	wordlist_group.add_argument('--wordlist-passwords', action='store', metavar='PATH', help='Override the passwords wordlist path')
	wordlist_group.add_argument('--wordlist-web-directories', action='store', metavar='PATH', help='Override the web directories wordlist path')
	wordlist_group.add_argument('--wordlist-web-files', action='store', metavar='PATH', help='Override the web files wordlist path')
	wordlist_group.add_argument('--wordlist-subdomains', action='store', metavar='PATH', help='Override the subdomains wordlist path')
	wordlist_group.add_argument('--wordlist-snmp-communities', action='store', metavar='PATH', help='Override the SNMP community strings wordlist path')
	wordlist_group.add_argument('--wordlist-dns-servers', action='store', metavar='PATH', help='Override the DNS servers wordlist path')
	wordlist_group.add_argument('--wordlist-vhosts', action='store', metavar='PATH', help='Override the virtual hosts wordlist path')
	
	# Scan speed and scenario arguments
	scan_group = parser.add_argument_group('scan scenarios', 'Predefined scan configurations for different scenarios')
	scan_speed_group = scan_group.add_mutually_exclusive_group()
	scan_speed_group.add_argument('--fast', action='store_true', help='Fast scan mode using smaller wordlists (5-15 min per service). Great for initial reconnaissance.')
	scan_speed_group.add_argument('--comprehensive', action='store_true', help='Comprehensive scan mode using large wordlists (30-120 min per service). Best for thorough enumeration.')
	scan_speed_group.add_argument('--wordlist-size', choices=['fast', 'default', 'comprehensive'], metavar='SIZE', help='Set wordlist size preference: fast, default, or comprehensive')
	
	# Scenario-based scan presets
	scenario_group = scan_group.add_mutually_exclusive_group()
	scenario_group.add_argument('--ctf', action='store_true', help='CTF/lab mode: balanced wordlists with higher threads for practice environments')
	scenario_group.add_argument('--pentest', action='store_true', help='Penetration testing mode: comprehensive wordlists optimized for real-world assessment')
	scenario_group.add_argument('--recon', action='store_true', help='Quick reconnaissance mode: fast wordlists for initial target discovery')
	scenario_group.add_argument('--stealth', action='store_true', help='Stealth mode: slower scans with reduced threads to avoid detection')
	parser.add_argument('-w', '--watch', action='store_true', help='Watch mode: continuously update HTML reports as scans progress')
	parser.add_argument('-d', '--daemon', action='store_true', help='Daemon mode: real-time monitoring and live HTML report generation')
	parser.add_argument('--partial', action='store_true', help='Generate partial HTML report from incomplete/interrupted scans')
	parser.add_argument('-r', '--report-target', type=str, metavar='TARGET', help='Generate HTML report for specific target only')
	parser.add_argument('--report-output', action='store', metavar='FILE', help='Custom output file for HTML report')
	
	parser.add_argument('-v', '--verbose', action='count', help='Enable verbose output. Repeat for more verbosity.')
	parser.add_argument('--debug', action='store_true', help='Enable debug mode with detailed plugin output. Automatically loads .env file for Sentry monitoring if available. Default: %(default)s')
	parser.add_argument('--version', action='store_true', help='Prints the ipcrawler version and exits.')
	parser.error = lambda s: fail(s[0].upper() + s[1:])
	args, unknown = parser.parse_known_args()

	errors = False

	ipcrawler.argparse = parser

	if args.version:
		show_modern_version(VERSION)
		sys.exit(0)

	def unknown_help():
		if '-h' in unknown:
			parser.print_help()
			print()

	# Parse config file and args for global.toml first.
	if not args.config_file:
		unknown_help()
		fail('Error: Could not find config.toml in the git repository directory.')

	if not os.path.isfile(args.config_file):
		unknown_help()
		fail('Error: Specified config file "' + args.config_file + '" does not exist.')

	with open(args.config_file) as c:
		try:
			config_toml = toml.load(c)
			for key, val in config_toml.items():
				key = slugify(key)
				if key == 'global-file':
					config['global_file'] = val
				elif key == 'plugins-dir':
					config['plugins_dir'] = val
				elif key == 'add-plugins-dir':
					config['add_plugins_dir'] = val
		except toml.decoder.TomlDecodeError:
			unknown_help()
			fail('Error: Couldn\'t parse ' + args.config_file + ' config file. Check syntax.')

	args_dict = vars(args)
	for key in args_dict:
		key = slugify(key)
		if key == 'global-file' and args_dict['global_file'] is not None:
			config['global_file'] = args_dict['global_file']
		elif key == 'plugins-dir' and args_dict['plugins_dir'] is not None:
			config['plugins_dir'] = args_dict['plugins_dir']
		elif key == 'add-plugins-dir' and args_dict['add_plugins_dir'] is not None:
			config['add_plugins_dir'] = args_dict['add_plugins_dir']

	if not config['plugins_dir']:
		unknown_help()
		fail('Error: Could not find plugins directory in the git repository.')

	if not os.path.isdir(config['plugins_dir']):
		unknown_help()
		fail('Error: Specified plugins directory "' + config['plugins_dir'] + '" does not exist.')

	if config['add_plugins_dir'] and not os.path.isdir(config['add_plugins_dir']):
		unknown_help()
		fail('Error: Specified additional plugins directory "' + config['add_plugins_dir'] + '" does not exist.')

	plugins_dirs = [config['plugins_dir']]
	if config['add_plugins_dir']:
		plugins_dirs.append(config['add_plugins_dir'])

	def load_plugins_from_directory(plugins_dir):
		"""Recursively load plugins from directory and subdirectories"""
		plugin_files = []
		
		# Walk through directory recursively to find all .py files
		for root, dirs, files in os.walk(plugins_dir):
			# Skip hidden directories
			dirs[:] = [d for d in dirs if not d.startswith('_')]
			
			for file in sorted(files):
				if not file.startswith('_') and file.endswith('.py'):
					plugin_files.append(os.path.join(root, file))
		
		# Sort all plugin files to maintain consistent loading order
		plugin_files.sort()
		
		for plugin_path in plugin_files:
			dirname, filename = os.path.split(plugin_path)
			dirname = os.path.abspath(dirname)
			
			try:
				spec = importlib.util.spec_from_file_location("ipcrawler." + filename[:-3], plugin_path)
				plugin = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(plugin)

				clsmembers = inspect.getmembers(plugin, predicate=inspect.isclass)
				for (_, c) in clsmembers:
					if c.__module__ in ['ipcrawler.plugins', 'ipcrawler.targets']:
						continue

					if c.__name__.lower() in config['protected_classes']:
						unknown_help()
						print('Plugin "' + c.__name__ + '" in ' + filename + ' is using a protected class name. Please change it.')
						sys.exit(1)

					# Only add classes that are a sub class of either PortScan, ServiceScan, or Report
					if issubclass(c, PortScan) or issubclass(c, ServiceScan) or issubclass(c, Report):
						ipcrawler.register(c(), filename)
					else:
						print('Plugin "' + c.__name__ + '" in ' + filename + ' is not a subclass of either PortScan, ServiceScan, or Report.')
			except (ImportError, SyntaxError) as ex:
				unknown_help()
				print('cannot import ' + filename + ' plugin')
				print(ex)
				sys.exit(1)

	for plugins_dir in plugins_dirs:
		load_plugins_from_directory(plugins_dir)

	for plugin in ipcrawler.plugins.values():
		if plugin.slug in ipcrawler.taglist:
			unknown_help()
			fail('Plugin ' + plugin.name + ' has a slug (' + plugin.slug + ') with the same name as a tag. Please either change the plugin name or override the slug.')
		# Add plugin slug to tags.
		plugin.tags += [plugin.slug]

	if len(ipcrawler.plugin_types['port']) == 0:
		unknown_help()
		fail('Error: There are no valid PortScan plugins in the plugins directory "' + config['plugins_dir'] + '".')

	# Sort plugins by priority.
	ipcrawler.plugin_types['port'].sort(key=lambda x: x.priority)
	ipcrawler.plugin_types['service'].sort(key=lambda x: x.priority)
	ipcrawler.plugin_types['report'].sort(key=lambda x: x.priority)

	if not config['global_file']:
		unknown_help()
		fail('Error: Could not find global.toml in the git repository directory.')

	if not os.path.isfile(config['global_file']):
		unknown_help()
		fail('Error: Specified global file "' + config['global_file'] + '" does not exist.')

	global_plugin_args = None
	with open(config['global_file']) as g:
		try:
			global_toml = toml.load(g)
			for key, val in global_toml.items():
				if key == 'global' and isinstance(val, dict): # Process global plugin options.
					for gkey, gvals in global_toml['global'].items():
						if isinstance(gvals, dict):
							options = {'metavar':'VALUE'}

							if 'default' in gvals:
								options['default'] = gvals['default']

							if 'metavar' in gvals:
								options['metavar'] = gvals['metavar']

							if 'help' in gvals:
								options['help'] = gvals['help']

							if 'type' in gvals:
								gtype = gvals['type'].lower()
								if gtype == 'constant':
									if 'constant' not in gvals:
										fail('Global constant option ' + gkey + ' has no constant value set.')
									else:
										options['action'] = 'store_const'
										options['const'] = gvals['constant']
								elif gtype == 'true':
									options['action'] = 'store_true'
									options.pop('metavar', None)
									options.pop('default', None)
								elif gtype == 'false':
									options['action'] = 'store_false'
									options.pop('metavar', None)
									options.pop('default', None)
								elif gtype == 'list':
									options['nargs'] = '+'
								elif gtype == 'choice':
									if 'choices' not in gvals:
										fail('Global choice option ' + gkey + ' has no choices value set.')
									else:
										if not isinstance(gvals['choices'], list):
											fail('The \'choices\' value for global choice option ' + gkey + ' should be a list.')
										options['choices'] = gvals['choices']
										options.pop('metavar', None)

							if global_plugin_args is None:
								global_plugin_args = parser.add_argument_group("global plugin arguments", description="These are optional arguments that can be used by all plugins.")

							global_plugin_args.add_argument('--global.' + slugify(gkey), **options)
				elif key == 'pattern' and isinstance(val, list): # Process global patterns.
					for pattern in val:
						if 'pattern' in pattern:
							try:
								compiled = re.compile(pattern['pattern'])
								if 'description' in pattern:
									ipcrawler.patterns.append(Pattern(compiled, description=pattern['description']))
								else:
									ipcrawler.patterns.append(Pattern(compiled))
							except re.error:
								unknown_help()
								fail('Error: The pattern "' + pattern['pattern'] + '" in the global file is invalid regex.')
						else:
							unknown_help()
							fail('Error: A [[pattern]] in the global file doesn\'t have a required pattern variable.')

		except toml.decoder.TomlDecodeError:
			unknown_help()
			fail('Error: Couldn\'t parse ' + g.name + ' file. Check syntax.')

	other_options = []
	for key, val in config_toml.items():
		if key == 'global' and isinstance(val, dict): # Process global plugin options.
			for gkey, gval in config_toml['global'].items():
				if isinstance(gval, bool):
					for action in ipcrawler.argparse._actions:
						if action.dest == 'global.' + slugify(gkey).replace('-', '_'):
							if action.const is True:
								action.__setattr__('default', gval)
							break
				else:
					if ipcrawler.argparse.get_default('global.' + slugify(gkey).replace('-', '_')):
						ipcrawler.argparse.set_defaults(**{'global.' + slugify(gkey).replace('-', '_'): gval})
		elif isinstance(val, dict): # Process potential plugin arguments.
			for pkey, pval in config_toml[key].items():
				if ipcrawler.argparse.get_default(slugify(key).replace('-', '_') + '.' + slugify(pkey).replace('-', '_')) is not None:
					for action in ipcrawler.argparse._actions:
						if action.dest == slugify(key).replace('-', '_') + '.' + slugify(pkey).replace('-', '_'):
							if action.const and pval != action.const:
								if action.const in [True, False]:
									error('Config option [' + slugify(key) + '] ' + slugify(pkey) + ': invalid value: \'' + pval + '\' (should be ' + str(action.const).lower() + ' {no quotes})')
								else:
									error('Config option [' + slugify(key) + '] ' + slugify(pkey) + ': invalid value: \'' + pval + '\' (should be ' + str(action.const) + ')')
								errors = True
							elif action.choices and pval not in action.choices:
								error('Config option [' + slugify(key) + '] ' + slugify(pkey) + ': invalid choice: \'' + pval + '\' (choose from \'' + '\', \''.join(action.choices) + '\')')
								errors = True
							elif isinstance(action.default, list) and not isinstance(pval, list):
								error('Config option [' + slugify(key) + '] ' + slugify(pkey) + ': invalid value: \'' + pval + '\' (should be a list e.g. [\'' + pval + '\'])')
								errors = True
							break
					ipcrawler.argparse.set_defaults(**{slugify(key).replace('-', '_') + '.' + slugify(pkey).replace('-', '_'): pval})
		else: # Process potential other options.
			key = key.replace('-', '_')
			if key in configurable_keys:
				other_options.append(key)
				config[key] = val
				ipcrawler.argparse.set_defaults(**{key: val})

	for key, val in config.items():
		if key not in other_options:
			ipcrawler.argparse.set_defaults(**{key: val})

	parser.add_argument('-h', '--help', action=ModernHelpAction, help='Show this help message and exit.')
	parser.error = lambda s: fail(s[0].upper() + s[1:])
	args = parser.parse_args()

	args_dict = vars(args)
	for key in args_dict:
		if key in configurable_keys and args_dict[key] is not None:
			# Special case for booleans
			if key in configurable_boolean_keys and config[key]:
				continue
			config[key] = args_dict[key]
	ipcrawler.args = args

	# Initialize WordlistManager and perform auto-detection on first run
	wordlist_manager = init_wordlist_manager(config['config_dir'])
	if wordlist_manager.load_config().get('mode', {}).get('auto_update', True):
		if wordlist_manager.update_detected_paths():
			info('📚 SecLists detected - wordlists configured automatically', verbosity=1)
		else:
			debug('📚 No SecLists installation detected. Install SecLists for wordlist functionality.')
	
	# Process wordlist CLI overrides
	wordlist_overrides = {
		'usernames': getattr(args, 'wordlist_usernames', None),
		'passwords': getattr(args, 'wordlist_passwords', None),
		'web_directories': getattr(args, 'wordlist_web_directories', None),
		'web_files': getattr(args, 'wordlist_web_files', None),
		'subdomains': getattr(args, 'wordlist_subdomains', None),
		'snmp_communities': getattr(args, 'wordlist_snmp_communities', None),
		'dns_servers': getattr(args, 'wordlist_dns_servers', None),
		'vhosts': getattr(args, 'wordlist_vhosts', None)
	}
	
	for category, path in wordlist_overrides.items():
		if path:
			if not wordlist_manager.validate_wordlist_path(path):
				fail(f'Error: Wordlist path for {category} does not exist or is not readable: {path}')
			wordlist_manager.set_cli_override(category, path)
			debug(f'CLI override set for {category}: {path}')
	
	# Process scan scenario flags
	if args.fast:
		wordlist_manager.set_wordlist_size('fast')
		info('⚡ Fast scan mode: using smaller wordlists for quicker scans', verbosity=1)
	elif args.comprehensive:
		wordlist_manager.set_wordlist_size('comprehensive')
		info('🔍 Comprehensive scan mode: using large wordlists for thorough enumeration', verbosity=1)
	elif getattr(args, 'wordlist_size', None):
		wordlist_manager.set_wordlist_size(args.wordlist_size)
		info(f'📝 Wordlist size: {args.wordlist_size}', verbosity=1)
	
	# Process scenario presets
	if args.ctf:
		wordlist_manager.set_wordlist_size('default')
		config['max_scans'] = config.get('max_scans', 20) + 10  # Higher concurrency
		info('CTF mode enabled: balanced wordlists with higher concurrency for lab environments.')
	elif args.pentest:
		wordlist_manager.set_wordlist_size('comprehensive')
		info('Penetration testing mode enabled: comprehensive wordlists for real-world assessment.')
	elif args.recon:
		wordlist_manager.set_wordlist_size('fast')
		config['tags'] = 'default+safe'  # Focus on safe, quick scans
		info('Quick reconnaissance mode enabled: fast wordlists for initial target discovery.')
	elif args.stealth:
		wordlist_manager.set_wordlist_size('default')
		# Reduce thread counts for stealth (will be applied to individual plugins)
		config['stealth_mode'] = True
		info('Stealth mode enabled: slower scans with reduced threads to avoid detection.')

	if args.list:
		if args.list == 'consolidator':
			print('\n🕷️ ipcrawler Consolidator Usage:')
			print('='*50)
			print('Generate comprehensive HTML reports from scan results')
			print()
			print('📝 Basic Usage:')
			print('  --consolidator-output FILE    Custom output file for HTML report')
			print('  --consolidator-target TARGET  Generate report for specific target only')
			print()
			print('🔄 Live Modes:')
			print('  --consolidator-watch          Watch mode: continuously update report as scans progress')
			print('  --consolidator-daemon         Daemon mode: real-time monitoring and live reports')
			print('  --consolidator-partial        Generate partial report from interrupted scans')
			print()
			print('⏱️  Timing:')
			print('  --consolidator-interval N     Update interval in seconds (default: 30 for watch, 5 for daemon)')
			print()
			print('📄 Examples:')
			print('  ipcrawler 192.168.1.1 --consolidator-watch')
			print('  ipcrawler 192.168.1.0/24 --consolidator-daemon --consolidator-interval 10')
			print('  ipcrawler 192.168.1.1 --consolidator-target 192.168.1.1 --consolidator-output custom.html')
			print()
		else:
			show_modern_plugin_list(ipcrawler.plugin_types, args.list)
		sys.exit(0)

	max_plugin_target_instances = {}
	if config['max_plugin_target_instances']:
		for plugin_instance in config['max_plugin_target_instances']:
			plugin_instance = plugin_instance.split(':', 1)
			if len(plugin_instance) == 2:
				if plugin_instance[0] not in ipcrawler.plugins:
					error('Invalid plugin slug (' + plugin_instance[0] + ':' + plugin_instance[1] + ') provided to --max-plugin-target-instances.')
					errors = True
				elif not plugin_instance[1].isdigit() or int(plugin_instance[1]) == 0:
					error('Invalid number of instances (' + plugin_instance[0] + ':' + plugin_instance[1] + ') provided to --max-plugin-target-instances. Must be a non-zero positive integer.')
					errors = True
				else:
					max_plugin_target_instances[plugin_instance[0]] = int(plugin_instance[1])
			else:
				error('Invalid value provided to --max-plugin-target-instances. Values must be in the format PLUGIN:NUMBER.')

	max_plugin_global_instances = {}
	if config['max_plugin_global_instances']:
		for plugin_instance in config['max_plugin_global_instances']:
			plugin_instance = plugin_instance.split(':', 1)
			if len(plugin_instance) == 2:
				if plugin_instance[0] not in ipcrawler.plugins:
					error('Invalid plugin slug (' + plugin_instance[0] + ':' + plugin_instance[1] + ') provided to --max-plugin-global-instances.')
					errors = True
				elif not plugin_instance[1].isdigit() or int(plugin_instance[1]) == 0:
					error('Invalid number of instances (' + plugin_instance[0] + ':' + plugin_instance[1] + ') provided to --max-plugin-global-instances. Must be a non-zero positive integer.')
					errors = True
				else:
					max_plugin_global_instances[plugin_instance[0]] = int(plugin_instance[1])
			else:
				error('Invalid value provided to --max-plugin-global-instances. Values must be in the format PLUGIN:NUMBER.')

	failed_check_plugin_slugs = []
	for slug, plugin in ipcrawler.plugins.items():
		if hasattr(plugin, 'max_target_instances') and plugin.slug in max_plugin_target_instances:
			plugin.max_target_instances = max_plugin_target_instances[plugin.slug]

		if hasattr(plugin, 'max_global_instances') and plugin.slug in max_plugin_global_instances:
			plugin.max_global_instances = max_plugin_global_instances[plugin.slug]

		for member_name, _ in inspect.getmembers(plugin, predicate=inspect.ismethod):
			if member_name == 'check':
				try:
					if plugin.check() == False:
						failed_check_plugin_slugs.append(slug)
						continue
				except Exception as e:
					# Send plugin check failure to Sentry if available
					if SENTRY_AVAILABLE:
						try:
							import sentry_sdk
							sentry_sdk.capture_exception(
								e,
								extra={
									'plugin_slug': slug,
									'plugin_name': getattr(plugin, 'name', slug),
									'error_type': 'plugin_check_failure',
									'ignore_plugin_checks': config['ignore_plugin_checks'],
									'plugin_tags': getattr(plugin, 'tags', []),
									'plugin_description': getattr(plugin, 'description', '')
								}
							)
						except Exception:
							pass  # Don't let Sentry errors break the scan
					
					if config['ignore_plugin_checks']:
						failed_check_plugin_slugs.append(slug)
						warn(f'Plugin {slug} check failed ({e}), but --ignore-plugin-checks is enabled. Plugin will be disabled.', verbosity=1)
						continue
					else:
						error(f'Plugin {slug} check failed: {e}')
						failed_check_plugin_slugs.append(slug)
						continue
				continue
	
	# Check for any failed plugin checks.
	for slug in failed_check_plugin_slugs:
		# If plugin checks should be ignored, remove the affected plugins at runtime.
		if config['ignore_plugin_checks']:
			ipcrawler.plugins.pop(slug)
		else:
			print()
			error('The following plugins failed checks that prevent ipcrawler from running: ' + ', '.join(failed_check_plugin_slugs))
			error('Check above output to fix these issues, disable relevant plugins, or run ipcrawler with --ignore-plugin-checks to disable failed plugins at runtime.')
			print()
			errors = True
			break

	if config['ports']:
		ports_to_scan = {'tcp':[], 'udp':[]}
		unique = {'tcp':[], 'udp':[]}

		ports = config['ports'].split(',')
		mode = 'both'
		for port in ports:
			port = port.strip()
			if port == '':
				continue

			if port.startswith('B:'):
				mode = 'both'
				port = port.split('B:')[1]
			elif port.startswith('T:'):
				mode = 'tcp'
				port = port.split('T:')[1]
			elif port.startswith('U:'):
				mode = 'udp'
				port = port.split('U:')[1]

			match = re.search(r'^([0-9]+)\-([0-9]+)$', port)
			if match:
				num1 = int(match.group(1))
				num2 = int(match.group(2))

				if num1 > 65535:
					fail('Error: A provided port number was too high: ' + str(num1))

				if num2 > 65535:
					fail('Error: A provided port number was too high: ' + str(num2))

				if num1 == num2:
					port_range = [num1]

				if num2 > num1:
					port_range = list(range(num1, num2 + 1, 1))
				else:
					port_range = list(range(num2, num1 + 1, 1))
					num1 = num1 + num2
					num2 = num1 - num2
					num1 = num1 - num2

				if mode == 'tcp' or mode == 'both':
					for num in port_range:
						if num in ports_to_scan['tcp']:
							ports_to_scan['tcp'].remove(num)
					ports_to_scan['tcp'].append(str(num1) + '-' + str(num2))
					unique['tcp'] = list(set(unique['tcp'] + port_range))

				if mode == 'udp' or mode == 'both':
					for num in port_range:
						if num in ports_to_scan['udp']:
							ports_to_scan['udp'].remove(num)
					ports_to_scan['udp'].append(str(num1) + '-' + str(num2))
					unique['udp'] = list(set(unique['tcp'] + port_range))
			else:
				match = re.search('^[0-9]+$', port)
				if match:
					num = int(port)

					if num > 65535:
						fail('Error: A provided port number was too high: ' + str(num))

					if mode == 'tcp' or mode == 'both':
						ports_to_scan['tcp'].append(str(num)) if num not in unique['tcp'] else ports_to_scan['tcp']
						unique['tcp'].append(num)

					if mode == 'udp' or mode == 'both':
						ports_to_scan['udp'].append(str(num)) if num not in unique['udp'] else ports_to_scan['udp']
						unique['udp'].append(num)
				else:
					fail('Error: Invalid port number: ' + str(port))
		config['ports'] = ports_to_scan

	if config['max_scans'] <= 0:
		error('Argument -m/--max-scans must be at least 1.')
		errors = True

	if config['max_port_scans'] is None:
		config['max_port_scans'] = max(1, round(config['max_scans'] * 0.2))
	else:
		if config['max_port_scans'] <= 0:
			error('Argument -mp/--max-port-scans must be at least 1.')
			errors = True

		if config['max_port_scans'] > config['max_scans']:
			error('Argument -mp/--max-port-scans cannot be greater than argument -m/--max-scans.')
			errors = True

	if config['heartbeat'] <= 0:
		error('Argument --heartbeat must be at least 1.')
		errors = True

	if config['timeout'] is not None and config['timeout'] <= 0:
		error('Argument --timeout must be at least 1.')
		errors = True

	if config['target_timeout'] is not None and config['target_timeout'] <= 0:
		error('Argument --target-timeout must be at least 1.')
		errors = True

	if config['timeout'] is not None and config['target_timeout'] is not None and config['timeout'] < config['target_timeout']:
		error('Argument --timeout cannot be less than --target-timeout.')
		errors = True

	if not errors:
		if config['force_services']:
			ipcrawler.service_scan_semaphore = asyncio.Semaphore(config['max_scans'])
		else:
			ipcrawler.port_scan_semaphore = asyncio.Semaphore(config['max_port_scans'])
			# If max scans and max port scans is the same, the service scan semaphore and port scan semaphore should be the same object
			if config['max_scans'] == config['max_port_scans']:
				ipcrawler.service_scan_semaphore = ipcrawler.port_scan_semaphore
			else:
				ipcrawler.service_scan_semaphore = asyncio.Semaphore(config['max_scans'] - config['max_port_scans'])

	tags = []
	for tag_group in list(set(filter(None, args.tags.lower().split(',')))):
		tags.append(list(set(filter(None, tag_group.split('+')))))

	# Remove duplicate lists from list.
	[ipcrawler.tags.append(t) for t in tags if t not in ipcrawler.tags]

	excluded_tags = []
	if args.exclude_tags is None:
		args.exclude_tags = ''
	if args.exclude_tags != '':
		for tag_group in list(set(filter(None, args.exclude_tags.lower().split(',')))):
			excluded_tags.append(list(set(filter(None, tag_group.split('+')))))

		# Remove duplicate lists from list.
		[ipcrawler.excluded_tags.append(t) for t in excluded_tags if t not in ipcrawler.excluded_tags]

	if config['port_scans']:
		config['port_scans'] = [x.strip().lower() for x in config['port_scans'].split(',')]

	if config['service_scans']:
		config['service_scans'] = [x.strip().lower() for x in config['service_scans'].split(',')]

	if config['reports']:
		config['reports'] = [x.strip().lower() for x in config['reports'].split(',')]

	raw_targets = args.targets

	if len(args.target_file) > 0:
		if not os.path.isfile(args.target_file):
			error('The target file "' + args.target_file + '" was not found.')
			sys.exit(1)
		try:
			with open(args.target_file, 'r') as f:
				lines = f.read()
				for line in lines.splitlines():
					line = line.strip()
					if line.startswith('#'): continue
					match = re.match('([^#]+)#', line)
					if match:
						line = match.group(1).strip()
					if len(line) == 0: continue
					if line not in raw_targets:
						raw_targets.append(line)
		except OSError:
			error('The target file ' + args.target_file + ' could not be read.')
			sys.exit(1)

	unresolvable_targets = False
	for target in raw_targets:
		try:
			ip = ipaddress.ip_address(target)
			ip_str = str(ip)

			found = False
			for t in ipcrawler.pending_targets:
				if t.address == ip_str:
					found = True
					break

			if found:
				continue

			if isinstance(ip, ipaddress.IPv4Address):
				ipcrawler.pending_targets.append(Target(ip_str, ip_str, 'IPv4', 'ip', ipcrawler))
			elif isinstance(ip, ipaddress.IPv6Address):
				ipcrawler.pending_targets.append(Target(ip_str, ip_str, 'IPv6', 'ip', ipcrawler))
			else:
				fail('This should never happen unless IPv8 is invented.')
		except ValueError:

			try:
				target_range = ipaddress.ip_network(target, strict=False)
				if not args.disable_sanity_checks and target_range.num_addresses > 256:
					fail(target + ' contains ' + str(target_range.num_addresses) + ' addresses. Check that your CIDR notation is correct. If it is, re-run with the --disable-sanity-checks option to suppress this check.')
					errors = True
				else:
					for ip in target_range.hosts():
						ip_str = str(ip)

						found = False
						for t in ipcrawler.pending_targets:
							if t.address == ip_str:
								found = True
								break

						if found:
							continue

						if isinstance(ip, ipaddress.IPv4Address):
							ipcrawler.pending_targets.append(Target(ip_str, ip_str, 'IPv4', 'ip', ipcrawler))
						elif isinstance(ip, ipaddress.IPv6Address):
							ipcrawler.pending_targets.append(Target(ip_str, ip_str, 'IPv6', 'ip', ipcrawler))
						else:
							fail('This should never happen unless IPv8 is invented.')

			except ValueError:

				try:
					addresses = socket.getaddrinfo(target, None, socket.AF_INET)
					ip = addresses[0][4][0]

					found = False
					for t in ipcrawler.pending_targets:
						if t.address == target:
							found = True
							break

					if found:
						continue

					ipcrawler.pending_targets.append(Target(target, ip, 'IPv4', 'hostname', ipcrawler))
				except socket.gaierror:
					try:
						addresses = socket.getaddrinfo(target, None, socket.AF_INET6)
						ip = addresses[0][4][0]

						found = False
						for t in ipcrawler.pending_targets:
							if t.address == target:
								found = True
								break

						if found:
							continue

						ipcrawler.pending_targets.append(Target(target, ip, 'IPv6', 'hostname', ipcrawler))
					except socket.gaierror:
						unresolvable_targets = True
						error(target + ' does not appear to be a valid IP address, IP range, or resolvable hostname.')

	if not args.disable_sanity_checks and unresolvable_targets == True:
		error('ipcrawler will not run if any targets are invalid / unresolvable. To override this, re-run with the --disable-sanity-checks option.')
		errors = True

	if len(ipcrawler.pending_targets) == 0:
		error('You must specify at least one target to scan!')
		errors = True

	if config['single_target'] and len(ipcrawler.pending_targets) != 1:
		error('You cannot provide more than one target when scanning in single-target mode.')
		errors = True

	if not args.disable_sanity_checks and len(ipcrawler.pending_targets) > 256:
		error('A total of ' + str(len(ipcrawler.pending_targets)) + ' targets would be scanned. If this is correct, re-run with the --disable-sanity-checks option to suppress this check.')
		errors = True

	if not config['force_services']:
		port_scan_plugin_count = 0
		for plugin in ipcrawler.plugin_types['port']:
			if config['port_scans'] and plugin.slug in config['port_scans']:
				matching_tags = True
				excluded_tags = False
			else:
				matching_tags = False
				for tag_group in ipcrawler.tags:
					if set(tag_group).issubset(set(plugin.tags)):
						matching_tags = True
						break

				excluded_tags = False
				for tag_group in ipcrawler.excluded_tags:
					if set(tag_group).issubset(set(plugin.tags)):
						excluded_tags = True
						break

			if matching_tags and not excluded_tags:
				port_scan_plugin_count += 1

		if port_scan_plugin_count == 0:
			error('There are no port scan plugins that match the tags specified.')
			errors = True
	else:
		port_scan_plugin_count = config['max_port_scans'] / 5

	if errors:
		sys.exit(1)

	config['port_scan_plugin_count'] = port_scan_plugin_count

	num_initial_targets = max(1, math.ceil(config['max_port_scans'] / port_scan_plugin_count))

	# Display ASCII art and give user time to admire it
	show_ascii_art()
	print()
	info(f'🚀 Starting scan of {len(ipcrawler.pending_targets)} target(s)...')
	print()
	info('⏳ Initializing scan engines... (5 seconds)')
	
	
	await asyncio.sleep(5)
	print()

	start_time = time.time()
	
	# Store args globally for Ctrl+C report generation
	global consolidator_args_global
	consolidator_args_global = args
	
	# Show message about HTML report generation
	flags = []
	if hasattr(args, 'watch') and args.watch:
		flags.append('-w')
	if hasattr(args, 'daemon') and args.daemon:
		flags.append('-d')
	if hasattr(args, 'partial') and args.partial:
		flags.append('--partial')
	
	if flags:
		info(f'🕷️  HTML report will be generated on scan completion or Ctrl+C (flags: {" ".join(flags)})', verbosity=1)
	else:
		info('🕷️  HTML report will be generated on scan completion or Ctrl+C', verbosity=1)

	if not config['disable_keyboard_control']:
		try:
			terminal_settings = termios.tcgetattr(sys.stdin.fileno())
		except (OSError, IOError) as e:
			# Handle cases where stdin is not connected to a terminal (Docker, redirected input, etc.)
			warn(f'Terminal keyboard control disabled: {e}', verbosity=2)
			config['disable_keyboard_control'] = True
			terminal_settings = None

	pending = []
	i = 0
	while ipcrawler.pending_targets:
		pending.append(asyncio.create_task(scan_target(ipcrawler.pending_targets.pop(0))))
		i+=1
		if i >= num_initial_targets:
			break

	if not config['disable_keyboard_control']:
		tty.setcbreak(sys.stdin.fileno())
		keyboard_monitor = asyncio.create_task(keyboard())

	timed_out = False
	while pending:
		done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=1)

		# If something failed in scan_target, ipcrawler.errors will be true.
		if ipcrawler.errors:
			cancel_all_tasks(None, None)
			sys.exit(1)

		# Check if global timeout has occurred.
		if config['timeout'] is not None:
			elapsed_seconds = round(time.time() - start_time)
			m, s = divmod(elapsed_seconds, 60)
			if m >= config['timeout']:
				timed_out = True
				break

		for task in done:
			if ipcrawler.pending_targets:
				pending.add(asyncio.create_task(scan_target(ipcrawler.pending_targets.pop(0))))
			if task in pending:
				pending.remove(task)

		port_scan_task_count = 0
		for targ in ipcrawler.scanning_targets:
			for process_list in targ.running_tasks.values():
				# If we're not scanning ports, count ServiceScans instead.
				if config['force_services']:
					if issubclass(process_list['plugin'].__class__, ServiceScan): # TODO should we really count ServiceScans? Test...
						port_scan_task_count += 1
				else:
					if issubclass(process_list['plugin'].__class__, PortScan):
						port_scan_task_count += 1

		num_new_targets = math.ceil((config['max_port_scans'] - port_scan_task_count) / port_scan_plugin_count)
		if num_new_targets > 0:
			i = 0
			while ipcrawler.pending_targets:
				pending.add(asyncio.create_task(scan_target(ipcrawler.pending_targets.pop(0))))
				i+=1
				if i >= num_new_targets:
					break

	if not config['disable_keyboard_control']:
		keyboard_monitor.cancel()

	# If there's only one target we don't need a combined report
	if len(ipcrawler.completed_targets) > 1:
		for plugin in ipcrawler.plugin_types['report']:
			if config['reports'] and plugin.slug in config['reports']:
				matching_tags = True
				excluded_tags = False
			else:
				plugin_tag_set = set(plugin.tags)

				matching_tags = False
				for tag_group in ipcrawler.tags:
					if set(tag_group).issubset(plugin_tag_set):
						matching_tags = True
						break

				excluded_tags = False
				for tag_group in ipcrawler.excluded_tags:
					if set(tag_group).issubset(plugin_tag_set):
						excluded_tags = True
						break

			if matching_tags and not excluded_tags:
				pending.add(asyncio.create_task(generate_report(plugin, ipcrawler.completed_targets)))

		while pending:
			done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=1)

	if timed_out:
		cancel_all_tasks(None, None)

		elapsed_time = calculate_elapsed_time(start_time)
		warn(f'⏰ Timeout reached ({config["timeout"]} min). Cancelling all scans and exiting.', verbosity=0)
	else:
		while len(asyncio.all_tasks()) > 1: # this code runs in the main() task so it will be the only task left running
			await asyncio.sleep(1)

		elapsed_time = calculate_elapsed_time(start_time)
		info(f'✅ All targets completed in {elapsed_time}!', verbosity=1)
		info('📄 Check _manual_commands.txt files for additional commands to run manually', verbosity=1)
		
		# Generate consolidator HTML report
		try:
			consolidator = IPCrawlerConsolidator(config['output'])
			
			# Set target filter if specified
			if hasattr(args, 'report_target') and args.report_target:
				consolidator.specific_target = args.report_target
			
			# Generate report from existing files
			output_file = getattr(args, 'report_output', None)
			if hasattr(args, 'partial') and args.partial:
				info('🕷️  Generating partial HTML report from scan results...', verbosity=1)
				consolidator.generate_partial_report(output_file)
			else:
				info('🕷️  Generating HTML report from scan results...', verbosity=1)
				consolidator.generate_html_report(output_file)
			
			info('📄 HTML report generated successfully', verbosity=1)
		except Exception as e:
			warn(f'⚠️ Failed to generate HTML report: {e}', verbosity=1)
			debug(f'Consolidator error details: {str(e)}', verbosity=2)


	if ipcrawler.missing_services:
		warn(f'⚠️ Unmatched services found: {", ".join(ipcrawler.missing_services)}', verbosity=1)

	if not config['disable_keyboard_control']:
		# Restore original terminal settings.
		if terminal_settings is not None:
			try:
				termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, terminal_settings)
			except (OSError, IOError) as e:
				# Handle cases where stdin is not connected to a terminal
				debug(f'Could not restore terminal settings: {e}', verbosity=2)

def main():
	# Initialize Sentry for error tracking and performance monitoring (developer only)
	# Check if --debug flag is used, and if so, automatically load .env file for Sentry
	sentry_dsn = os.environ.get('SENTRY_DSN')
	
	# Quick check for --debug flag before full arg parsing
	debug_mode = '--debug' in sys.argv
	
	if debug_mode and SENTRY_AVAILABLE and not sentry_dsn:
		# Try to load .env file automatically when --debug is used
		env_file = '.env'
		if os.path.exists(env_file):
			try:
				with open(env_file, 'r') as f:
					for line in f:
						line = line.strip()
						if line.startswith('SENTRY_DSN=') and not line.startswith('#'):
							sentry_dsn = line.split('=', 1)[1].strip().strip('"\'')
							break
				if sentry_dsn:
					info('🔧 Debug mode: Automatically loaded Sentry DSN from .env file', verbosity=0)
			except Exception as e:
				warn(f'⚠️ Debug mode: Could not load .env file: {e}', verbosity=0)
	
	# Initialize Sentry if DSN is available (from environment or .env file)
	if SENTRY_AVAILABLE and sentry_dsn:
		sentry_sdk.init(
			dsn=sentry_dsn,
			# Set traces_sample_rate to 1.0 to capture 100%
			# of transactions for tracing.
			traces_sample_rate=1.0,
			# Set profiles_sample_rate to 1.0 to profile 100%
			# of sampled transactions.
			# We recommend adjusting this value in production.
			profiles_sample_rate=1.0,
		)
		if debug_mode:
			info('🚀 Debug mode: Sentry monitoring enabled - capturing ALL errors and performance data', verbosity=0)
	
	# Capture Ctrl+C and cancel everything.
	signal.signal(signal.SIGINT, cancel_all_tasks)
	try:
		asyncio.run(run())
	except asyncio.exceptions.CancelledError:
		pass
	except RuntimeError as e:
		# Handle "Event loop is closed" errors gracefully
		if "Event loop is closed" in str(e):
			pass  # This is expected during shutdown
		else:
			raise  # Re-raise other RuntimeErrors

if __name__ == '__main__':
	main()
