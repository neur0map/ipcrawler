from ipcrawler.plugins import ServiceScan
import requests
from urllib.parse import urlparse
import urllib3
import os
import platform
import subprocess
import re
from datetime import datetime

# Note: SSL warnings are managed per-request for security awareness

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
		self.match_service_name('ssl/http')
		self.match_service_name('^https')
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
		"""Add hostname to /etc/hosts file (requires sudo privileges)"""
		try:
			hosts_file = '/etc/hosts'
			timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			entry = f"{ip_address} {hostname}  # added by ipcrawler {timestamp}"
			
			# Check if entry already exists
			with open(hosts_file, 'r') as f:
				content = f.read()
				if hostname in content:
					return 'exists'  # Already exists
			
			# Add entry to hosts file (requires sudo)
			with open(hosts_file, 'a') as f:
				f.write(f"\n{entry}\n")
			
			return 'added'
		except PermissionError:
			return 'permission_denied'
		except FileNotFoundError:
			return 'file_not_found'
		except Exception as e:
			return f'error: {str(e)}'

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
		
		service.info(f"🔧 Will test schemes: {schemes}")
		
		for scheme in schemes:
			try:
				url = f"{scheme}://{service.target.address}:{service.port}/"
				service.info(f"🌐 Testing: {url}")
				
				# Attempt secure connection first, fallback to insecure if needed
				try:
					resp = requests.get(url, verify=True, allow_redirects=False, timeout=10)
				except requests.exceptions.SSLError:
					# Fallback to unverified connection with warning
					service.warn(f"SSL verification failed for {url}, retrying without verification (vulnerable to MITM)", verbosity=1)
					with urllib3.warnings.catch_warnings():
						urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
						resp = requests.get(url, verify=False, allow_redirects=False, timeout=10)
				service.info(f"📊 Response: {resp.status_code} for {url}")
				
				# Check for redirects in Location header
				if 'Location' in resp.headers:
					location = resp.headers['Location']
					parsed = urlparse(location)
					redirect_host = parsed.hostname

					service.info(f"🔄 Redirect found: {url} → {location}")
					service.info(f"🎯 Parsed hostname: {redirect_host}")

					# Validate hostname before using it
					if redirect_host:
						# Basic hostname validation
						import re
						if re.match(r'^[a-zA-Z0-9.-]+$', redirect_host) and '..' not in redirect_host:
							if not redirect_host.endswith('.html') and not redirect_host.endswith('.php'):
								if redirect_host != service.target.address:
									service.info(f"✅ NEW hostname discovered: {redirect_host}")

									# Check if we should add to /etc/hosts
									if self.is_kali_or_htb():
										result = self.add_to_hosts(service.target.address, redirect_host)
										if result == 'added':
											service.info(f"✅ Added to /etc/hosts: {service.target.address} {redirect_host}")
										elif result == 'exists':
											service.info(f"ℹ️ Entry already exists in /etc/hosts: {redirect_host}")
										elif result == 'permission_denied':
											service.info(f"⚠️ Cannot modify /etc/hosts (requires sudo): {redirect_host}")
											service.info(f"💡 Run with sudo to enable /etc/hosts modification")
										elif result == 'file_not_found':
											service.info(f"⚠️ /etc/hosts file not found: {redirect_host}")
										else:
											service.info(f"❌ Failed to modify /etc/hosts: {result}")
									else:
										service.info(f"ℹ️ Not on Kali/HTB system - skipping /etc/hosts modification")

									if redirect_host not in discovered_hostnames:
										discovered_hostnames.append(redirect_host)
										# Store hostname in target for other plugins to use
										await service.target.add_discovered_hostname(redirect_host)
								else:
									service.info(f"🔍 Redirect hostname same as target: {redirect_host}")
							else:
								service.warn(f"⚠️ Invalid hostname detected (looks like file path): {redirect_host}")
						else:
							service.warn(f"⚠️ Invalid hostname format detected: {redirect_host}")
					else:
						service.info(f"🔍 No valid hostname found in redirect location: {location}")
				else:
					service.info(f"🔍 No Location header found in response from {url}")
					
				# Also check for Server header that might contain hostname info
				if 'Server' in resp.headers:
					service.info(f"🔧 Server header: {resp.headers['Server']}")
					
				# Check for any hostname in response content (basic check)
				try:
					content = resp.text[:1000]  # First 1KB only
					if service.target.address not in content:
						# Look for potential hostnames in content
						hostname_pattern = r'(?:https?://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
						matches = re.findall(hostname_pattern, content)
						if matches:
							service.info(f"🔍 Potential hostnames in content: {matches[:3]}")  # Show first 3
				except:
					pass
				
				# Also check common redirect paths
				redirect_paths = ['/index.html', '/home', '/admin', '/login']
				for path in redirect_paths[:2]:  # Limit to avoid too many requests
					try:
						path_url = f"{scheme}://{service.target.address}:{service.port}{path}"
						# Attempt secure connection first, fallback to insecure if needed
						try:
							path_resp = requests.get(path_url, verify=True, allow_redirects=False, timeout=3)
						except requests.exceptions.SSLError:
							# Fallback to unverified connection with warning
							service.warn(f"SSL verification failed for {path_url}, retrying without verification (vulnerable to MITM)", verbosity=1)
							with urllib3.warnings.catch_warnings():
								urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
								path_resp = requests.get(path_url, verify=False, allow_redirects=False, timeout=3)
						
						if 'Location' in path_resp.headers:
							location = path_resp.headers['Location']
							parsed = urlparse(location)
							redirect_host = parsed.hostname

							# Debug the parsing process
							service.info(f"🔧 DEBUG: Location header: {location}")
							service.info(f"🔧 DEBUG: Parsed hostname: {redirect_host}")

							# Validate hostname before using it
							if redirect_host:
								# Basic hostname validation
								import re
								if re.match(r'^[a-zA-Z0-9.-]+$', redirect_host) and '..' not in redirect_host:
									if not redirect_host.endswith('.html') and not redirect_host.endswith('.php'):
										if redirect_host != service.target.address and redirect_host not in discovered_hostnames:
											service.info(f"🔄 Redirect found at {path}: {path_url} → {location}")
											service.info(f"🌐 Additional hostname: {redirect_host}")

											if self.is_kali_or_htb():
												result = self.add_to_hosts(service.target.address, redirect_host)
												if result == 'added':
													service.info(f"✅ Added to /etc/hosts: {service.target.address} {redirect_host}")
												elif result == 'exists':
													service.info(f"ℹ️ Entry already exists in /etc/hosts: {redirect_host}")
												elif result == 'permission_denied':
													service.info(f"⚠️ Cannot modify /etc/hosts (requires sudo): {redirect_host}")
													service.info(f"💡 Run with sudo to enable /etc/hosts modification")
												elif result == 'file_not_found':
													service.info(f"⚠️ /etc/hosts file not found: {redirect_host}")
												else:
													service.info(f"❌ Failed to modify /etc/hosts: {result}")
											else:
												service.info(f"ℹ️ Not on Kali/HTB system - skipping /etc/hosts modification")

											discovered_hostnames.append(redirect_host)
											# Store hostname in target for other plugins to use
											await service.target.add_discovered_hostname(redirect_host)
										else:
											service.info(f"🔍 Redirect hostname same as target or already discovered: {redirect_host}")
									else:
										service.warn(f"⚠️ Invalid hostname detected (looks like file path): {redirect_host}")
								else:
									service.warn(f"⚠️ Invalid hostname format detected: {redirect_host}")
							else:
								service.info(f"🔍 No valid hostname found in redirect location: {location}")
					except:
						continue  # Skip failed path checks
						
			except requests.exceptions.ConnectTimeout as e:
				service.info(f"⏰ Timeout connecting to {scheme}://{service.target.address}:{service.port}/ - {e}")
				continue  # Timeout, try next scheme
			except requests.exceptions.ConnectionError as e:
				service.info(f"❌ Connection failed to {scheme}://{service.target.address}:{service.port}/ - {e}")
				continue  # Connection failed, try next scheme  
			except requests.exceptions.RequestException as e:
				service.info(f"🌐 Request error for {scheme}://{service.target.address}:{service.port}/ - {e}")
				continue
			except Exception as e:
				service.error(f"❌ Unexpected error checking {scheme}://{service.target.address}:{service.port}/: {e}")
				continue
		
		# Final summary
		service.info(f"🔍 Hostname Discovery Summary:")
		service.info(f"   • Schemes tested: {', '.join(schemes)}")
		service.info(f"   • New hostnames found: {len(discovered_hostnames)}")
		
		if discovered_hostnames:
			service.info(f"🎯 Successfully discovered {len(discovered_hostnames)} hostname(s):")
			for hostname in discovered_hostnames:
				service.info(f"   ✅ {hostname}")
			service.info(f"🔧 Target now has {len(service.target.discovered_hostnames)} total discovered hostnames")
		else:
			service.info(f"❌ No hostname redirects found for this service")
			service.info(f"💡 This is normal - many services don't use hostname redirects")
			service.info(f"💡 Web enumeration will proceed using IP address: {service.target.address}")
			service.info(f"🔧 Target.discovered_hostnames = {service.target.discovered_hostnames}")
			
		service.info(f"✅ Hostname discovery completed for {service.target.address}:{service.port}")