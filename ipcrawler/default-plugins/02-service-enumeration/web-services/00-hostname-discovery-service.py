from ipcrawler.plugins import ServiceScan
import requests
from urllib.parse import urlparse
import urllib3
import os
import platform
import subprocess

urllib3.disable_warnings()

class RedirectHostnameDiscoveryService(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = 'Redirect Hostname Discovery (Service)'
		self.slug = 'hostname-discovery-service'
		self.description = 'Discovers hostnames through HTTP redirects for existing HTTP services.'
		self.tags = ['default', 'hostname', 'quick']
		self.priority = -10  # Run before other service scans

	def configure(self):
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)

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
			entry = f"{ip_address} {hostname}"
			
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

	async def run(self, service):
		"""Run hostname discovery on the discovered HTTP service"""
		service.info(f"🔍 Starting hostname discovery for {service.target.address}:{service.port}")
		discovered_hostnames = []
		
		# Check both HTTP and HTTPS if applicable
		schemes = ['http']
		if service.secure:
			schemes = ['https']
		
		# Also check the alternate scheme if the port allows it
		if service.port in [80, 8080, 8000, 8001, 9000, 9001]:
			if 'https' not in schemes:
				schemes.append('https')
		elif service.port in [443, 8443]:
			if 'http' not in schemes:
				schemes.append('http')
		
		for scheme in schemes:
			try:
				url = f"{scheme}://{service.target.address}:{service.port}/"
				resp = requests.get(url, verify=False, allow_redirects=False, timeout=5)
				
				if 'Location' in resp.headers:
					location = resp.headers['Location']
					parsed = urlparse(location)
					redirect_host = parsed.hostname
					
					if redirect_host and redirect_host != service.target.address:
						service.info(f"🔄 Redirect found: {url} → {location}")
						service.info(f"🌐 Hostname discovered: {redirect_host}")
						
						# Check if we should add to /etc/hosts
						if self.is_kali_or_htb():
							if self.add_to_hosts(service.target.address, redirect_host):
								service.info(f"✅ Added to /etc/hosts: {service.target.address} {redirect_host}")
							else:
								service.info(f"ℹ️ Entry already exists in /etc/hosts: {redirect_host}")
						else:
							service.info(f"ℹ️ Not on Kali/HTB system - skipping /etc/hosts modification")
						
						if redirect_host not in discovered_hostnames:
							discovered_hostnames.append(redirect_host)
							# Store hostname in target for other plugins to use
							await service.target.add_discovered_hostname(redirect_host)
				
				# Also check common redirect paths
				redirect_paths = ['/index.html', '/home', '/admin', '/login']
				for path in redirect_paths[:2]:  # Limit to avoid too many requests
					try:
						path_url = f"{scheme}://{service.target.address}:{service.port}{path}"
						path_resp = requests.get(path_url, verify=False, allow_redirects=False, timeout=3)
						
						if 'Location' in path_resp.headers:
							location = path_resp.headers['Location']
							parsed = urlparse(location)
							redirect_host = parsed.hostname
							
							if redirect_host and redirect_host != service.target.address and redirect_host not in discovered_hostnames:
								service.info(f"🔄 Redirect found at {path}: {path_url} → {location}")
								service.info(f"🌐 Additional hostname: {redirect_host}")
								
								if self.is_kali_or_htb():
									if self.add_to_hosts(service.target.address, redirect_host):
										service.info(f"✅ Added to /etc/hosts: {service.target.address} {redirect_host}")
								
								discovered_hostnames.append(redirect_host)
								# Store hostname in target for other plugins to use
								await service.target.add_discovered_hostname(redirect_host)
					except:
						continue  # Skip failed path checks
						
			except requests.exceptions.ConnectTimeout:
				continue  # Timeout, try next scheme
			except requests.exceptions.ConnectionError:
				continue  # Connection failed, try next scheme  
			except Exception as e:
				service.error(f"Error checking {scheme}://{service.target.address}:{service.port}/: {e}", verbosity=2)
				continue
		
		if discovered_hostnames:
			service.info(f"🎯 Total hostnames discovered for service: {len(discovered_hostnames)}")
			for hostname in discovered_hostnames:
				service.info(f"   - {hostname}")
			service.info(f"🔧 DEBUG: Target now has {len(service.target.discovered_hostnames)} total discovered hostnames")
		else:
			service.info(f"ℹ️ No hostname redirects found for this service")
			service.info(f"🔧 DEBUG: No redirects found, target.discovered_hostnames = {service.target.discovered_hostnames}")