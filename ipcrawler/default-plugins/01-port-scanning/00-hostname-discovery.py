from ipcrawler.plugins import PortScan
import requests
from urllib.parse import urlparse
import urllib3
import os
import platform
import subprocess
from datetime import datetime
from ipcrawler.logger import setup_unified_logging

# Note: SSL warnings are managed per-request for security awareness

class RedirectHostnameDiscovery(PortScan):

	def __init__(self):
		super().__init__()
		self.name = 'Redirect Hostname Discovery'
		self.description = 'Discovers hostnames through HTTP redirects and adds them to /etc/hosts on Kali/HTB systems.'
		self.type = 'tcp'
		self.tags = ['default', 'hostname', 'quick']
		self.priority = -10  # Run before other scans

	def is_kali_or_htb(self):
		"""Detect if running on Kali Linux or Hack The Box environment"""
		try:
			# Check for Kali Linux
			if os.path.exists('/etc/os-release'):
				with open('/etc/os-release', 'r') as f:
					content = f.read().lower()
					if 'kali' in content:
						return True
			
			# Check for HTB environment indicators
			htb_indicators = [
				'/home/kali',  # HTB often uses kali user
				'/root/.htb',  # HTB specific directory
				'/opt/pwnbox'  # HTB Pwnbox indicator
			]
			
			for indicator in htb_indicators:
				if os.path.exists(indicator):
					return True
			
			# Check hostname for HTB patterns
			hostname = platform.node().lower()
			if any(pattern in hostname for pattern in ['htb', 'hackthebox', 'pwnbox']):
				return True
				
			# Check for HTB VPN connection
			try:
				result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
				if '10.10.' in result.stdout:  # HTB VPN typically uses 10.10.x.x
					return True
			except:
				pass
				
			return False
		except Exception:
			return False

	def add_to_hosts(self, ip, hostname):
		"""Add hostname to /etc/hosts file"""
		try:
			# Check if entry already exists
			with open('/etc/hosts', 'r') as f:
				content = f.read()
				if f"{ip} {hostname}" in content or f"{hostname}" in content:
					return 'exists'
			
			# Add new entry
			with open('/etc/hosts', 'a') as f:
				f.write(f"\n{ip} {hostname}\n")
			return 'added'
		except PermissionError:
			return 'permission_denied'
		except FileNotFoundError:
			return 'file_not_found'
		except Exception as e:
			return f'error: {str(e)}'

	async def run(self, target):
		"""Run hostname discovery on common HTTP ports"""
		# Setup unified logging for this plugin
		if not hasattr(target, '_unified_logger'):
			target._unified_logger = setup_unified_logging(target.address, target.scandir)
		
		# Use output suppressor to capture any remaining print statements
		with target._unified_logger.create_output_suppressor():
			discovered_hostnames = []
			common_http_ports = [80, 443, 8080, 8443, 8000, 8001, 9000, 9001]
			
			for port in common_http_ports:
				for secure in [False, True]:
					if (port in [443, 8443] and not secure) or (port not in [443, 8443] and secure):
						continue  # Skip inappropriate combinations
						
					try:
						scheme = 'https' if secure else 'http'
						url = f"{scheme}://{target.address}:{port}/"
						
						# Try to connect and check for redirects
						# Attempt secure connection first, fallback to insecure if needed
						try:
							resp = requests.get(url, verify=True, allow_redirects=False, timeout=5)
						except requests.exceptions.SSLError:
							# SSL verification failed - log this via target logger
							target.warn(f"SSL verification failed for {url}, retrying without verification (vulnerable to MITM)", verbosity=1)
							with urllib3.warnings.catch_warnings():
								urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
								resp = requests.get(url, verify=False, allow_redirects=False, timeout=5)
						
						if 'Location' in resp.headers:
							location = resp.headers['Location']
							parsed = urlparse(location)
							redirect_host = parsed.hostname
							
							if redirect_host and redirect_host != target.address:
								target.info(f"🔄 Redirect found: {url} → {location}", verbosity=1)
								target.info(f"🌐 Hostname discovered: {redirect_host}", verbosity=1)
								
								# Check if we should add to /etc/hosts
								if self.is_kali_or_htb():
									result = self.add_to_hosts(target.address, redirect_host)
									if result == 'added':
										target.info(f"✅ Added to /etc/hosts: {target.address} {redirect_host}", verbosity=1)
									elif result == 'exists':
										target.info(f"ℹ️ Entry already exists in /etc/hosts: {redirect_host}", verbosity=1)
									elif result == 'permission_denied':
										target.warn(f"Cannot modify /etc/hosts (requires sudo): {redirect_host}", verbosity=1)
										target.info(f"💡 Run with sudo to enable /etc/hosts modification", verbosity=1)
									elif result == 'file_not_found':
										target.warn(f"/etc/hosts file not found: {redirect_host}", verbosity=1)
									else:
										target.error(f"Failed to modify /etc/hosts: {result}", verbosity=1)
								else:
									target.info(f"ℹ️ Not on Kali/HTB system - skipping /etc/hosts modification", verbosity=1)
								
								if redirect_host not in discovered_hostnames:
									discovered_hostnames.append(redirect_host)
									# Add to target's discovered hostnames directly
									target.discovered_hostnames.append(redirect_host)
									target.info(f"Added discovered hostname: {redirect_host}", verbosity=1)
						
						# Also check common redirect paths
						redirect_paths = ['/', '/index.html', '/home', '/admin', '/login']
						for path in redirect_paths[:2]:  # Limit to avoid too many requests
							if path == '/':
								continue  # Already checked
								
							try:
								path_url = f"{scheme}://{target.address}:{port}{path}"
								# Attempt secure connection first, fallback to insecure if needed
								try:
									path_resp = requests.get(path_url, verify=True, allow_redirects=False, timeout=3)
								except requests.exceptions.SSLError:
									target.warn(f"SSL verification failed for {path_url}, retrying without verification (vulnerable to MITM)", verbosity=1)
									with urllib3.warnings.catch_warnings():
										urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
										path_resp = requests.get(path_url, verify=False, allow_redirects=False, timeout=3)
								
								if 'Location' in path_resp.headers:
									location = path_resp.headers['Location']
									parsed = urlparse(location)
									redirect_host = parsed.hostname
									
									if redirect_host and redirect_host != target.address and redirect_host not in discovered_hostnames:
										target.info(f"🔄 Redirect found at {path}: {path_url} → {location}", verbosity=1)
										target.info(f"🌐 Additional hostname: {redirect_host}", verbosity=1)
										
										if self.is_kali_or_htb():
											result = self.add_to_hosts(target.address, redirect_host)
											if result == 'added':
												target.info(f"✅ Added to /etc/hosts: {target.address} {redirect_host}", verbosity=1)
											elif result == 'exists':
												target.info(f"ℹ️ Entry already exists in /etc/hosts: {redirect_host}", verbosity=1)
											elif result == 'permission_denied':
												target.warn(f"Cannot modify /etc/hosts (requires sudo): {redirect_host}", verbosity=1)
												target.info(f"💡 Run with sudo to enable /etc/hosts modification", verbosity=1)
											elif result == 'file_not_found':
												target.warn(f"/etc/hosts file not found: {redirect_host}", verbosity=1)
											else:
												target.error(f"Failed to modify /etc/hosts: {result}", verbosity=1)
										else:
											target.info(f"ℹ️ Not on Kali/HTB system - skipping /etc/hosts modification", verbosity=1)
										
										discovered_hostnames.append(redirect_host)
										# Store hostname in target directly (avoid async call in PortScan)
										target.discovered_hostnames.append(redirect_host)
							except requests.exceptions.Timeout:
								continue  # Timeout on redirect check
							except requests.exceptions.ConnectionError:
								continue  # Connection failed
							except Exception:
								continue  # Other errors
							
					except requests.exceptions.Timeout:
						continue  # Port likely closed
					except requests.exceptions.ConnectionError:
						continue  # Port likely closed  
					except Exception as e:
						target.error(f"Error checking {scheme}://{target.address}:{port}/: {e}", verbosity=1)
						continue
		
		if discovered_hostnames:
			target.info(f"Total hostnames discovered: {len(discovered_hostnames)}", verbosity=0)
			for hostname in discovered_hostnames:
				target.info(f"   - {hostname}", verbosity=0)
			
			# Write discovered hostnames to file for consolidator to read
			try:
				await target.execute(
					f'echo "Discovered hostnames for {target.address}:" > "{{scandir}}/_hostname_discovery.txt"'
				)
				for hostname in discovered_hostnames:
					await target.execute(
						f'echo "  {hostname}" >> "{{scandir}}/_hostname_discovery.txt"'
					)
				target.info(f"✅ Wrote {len(discovered_hostnames)} hostnames to _hostname_discovery.txt", verbosity=1)
			except Exception as e:
				target.warn(f"Failed to write hostname file: {e}", verbosity=1)
		
		return []  # PortScan plugins return services, but we're doing discovery