from ipcrawler.plugins import PortScan
import requests
from urllib.parse import urlparse
import urllib3
import os
import platform
import subprocess
import re
from datetime import datetime

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

	def add_to_hosts(self, ip_address, hostname):
		"""Add hostname to /etc/hosts file (runs with sudo privileges)"""
		try:
			hosts_file = '/etc/hosts'
			timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			entry = f"{ip_address} {hostname}  # added by ipcrawler {timestamp}"
			
			# Check if entry already exists
			with open(hosts_file, 'r') as f:
				content = f.read()
				if hostname in content:
					return False  # Already exists
			
			# Add entry to hosts file (we have sudo privileges)
			with open(hosts_file, 'a') as f:
				f.write(f"\n{entry}\n")
			
			return True
		except Exception as e:
			return False

	async def run(self, target):
		"""Run hostname discovery on common HTTP ports"""
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
						# Fallback to unverified connection with warning
						print(f"⚠️ [{target.address}/hostname-discovery] SSL verification failed for {url}, retrying without verification (vulnerable to MITM)")
						with urllib3.warnings.catch_warnings():
							urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
							resp = requests.get(url, verify=False, allow_redirects=False, timeout=5)
					
					if 'Location' in resp.headers:
						location = resp.headers['Location']
						parsed = urlparse(location)
						redirect_host = parsed.hostname
						
						if redirect_host and redirect_host != target.address:
							print(f"🎯 [{target.address}/hostname-discovery] 🔄 Redirect found: {url} → {location}")
							print(f"🎯 [{target.address}/hostname-discovery] 🌐 Hostname discovered: {redirect_host}")
							
							# Check if we should add to /etc/hosts
							if self.is_kali_or_htb():
								if self.add_to_hosts(target.address, redirect_host):
									print(f"🎯 [{target.address}/hostname-discovery] ✅ Added to /etc/hosts: {target.address} {redirect_host}")
								else:
									print(f"🎯 [{target.address}/hostname-discovery] ℹ️ Entry already exists in /etc/hosts: {redirect_host}")
							else:
								print(f"🎯 [{target.address}/hostname-discovery] ℹ️ Not on Kali/HTB system - skipping /etc/hosts modification")
							
							if redirect_host not in discovered_hostnames:
								discovered_hostnames.append(redirect_host)
								# Add to target's discovered hostnames directly
								target.discovered_hostnames.append(redirect_host)
								print(f"🎯 [{target.address}/hostname-discovery] Added discovered hostname: {redirect_host}")
					
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
								# Fallback to unverified connection with warning
								print(f"⚠️ [{target.address}/hostname-discovery] SSL verification failed for {path_url}, retrying without verification (vulnerable to MITM)")
								with urllib3.warnings.catch_warnings():
									urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
									path_resp = requests.get(path_url, verify=False, allow_redirects=False, timeout=3)
							
							if 'Location' in path_resp.headers:
								location = path_resp.headers['Location']
								parsed = urlparse(location)
								redirect_host = parsed.hostname
								
								if redirect_host and redirect_host != target.address and redirect_host not in discovered_hostnames:
									print(f"🎯 [{target.address}/hostname-discovery] 🔄 Redirect found at {path}: {path_url} → {location}")
									print(f"🎯 [{target.address}/hostname-discovery] 🌐 Additional hostname: {redirect_host}")
									
									if self.is_kali_or_htb():
										if self.add_to_hosts(target.address, redirect_host):
											print(f"🎯 [{target.address}/hostname-discovery] ✅ Added to /etc/hosts: {target.address} {redirect_host}")
									
									discovered_hostnames.append(redirect_host)
									# Store hostname in target directly (avoid async call in PortScan)
									target.discovered_hostnames.append(redirect_host)
						except:
							continue  # Skip failed path checks
							
				except requests.exceptions.ConnectTimeout:
					continue  # Port likely closed
				except requests.exceptions.ConnectionError:
					continue  # Port likely closed  
				except Exception as e:
					print(f"❌ [{target.address}/hostname-discovery] Error checking {scheme}://{target.address}:{port}/: {e}")
					continue
		
		if discovered_hostnames:
			print(f"🎯 [{target.address}/hostname-discovery] Total hostnames discovered: {len(discovered_hostnames)}")
			for hostname in discovered_hostnames:
				print(f"🎯 [{target.address}/hostname-discovery]    - {hostname}")
			
			# Write discovered hostnames to file for consolidator to read
			try:
				await target.execute(
					'echo "Discovered hostnames:" > "{scandir}/_hostname_discovery.txt"'
				)
				for hostname in discovered_hostnames:
					await target.execute(
						f'echo "  {hostname}" >> "{{scandir}}/_hostname_discovery.txt"'
					)
				print(f"🎯 [{target.address}/hostname-discovery] ✅ Wrote {len(discovered_hostnames)} hostnames to _hostname_discovery.txt")
			except Exception as e:
				print(f"🎯 [{target.address}/hostname-discovery] ⚠️ Failed to write hostname file: {e}")
		
		return []  # PortScan plugins return services, but we're doing discovery