from ipcrawler.plugins import ServiceScan

class CTFHTBPatterns(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "CTF/HTB Pattern Detection"
		self.slug = 'ctf-htb-patterns'
		self.description = "Detects technologies and patterns commonly found in CTF and HackTheBox environments"
		self.priority = 0
		self.tags = ['default', 'safe', 'ctf', 'htb']

	def configure(self):
		# Match all HTTP services for broad coverage
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)
		
		# === HTB/CTF SPECIFIC VULNERABILITY PATTERNS ===
		
		# File Inclusion Vulnerabilities (Very Common in HTB)
		self.add_pattern(r'(?i)include[=\s]*["\']?([^"\'&\s]+\.php)', description='CRITICAL: Potential Local File Inclusion - parameter includes PHP file: {match1}')
		self.add_pattern(r'(?i)file[=\s]*["\']?([^"\'&\s]+)', description='WARNING: File parameter detected - test for LFI/RFI: {match1}')
		self.add_pattern(r'(?i)page[=\s]*["\']?([^"\'&\s]+)', description='INFO: Page parameter detected - test for LFI: {match1}')
		self.add_pattern(r'(?i)path[=\s]*["\']?([^"\'&\s]+)', description='WARNING: Path parameter detected - test for directory traversal: {match1}')
		self.add_pattern(r'(?i)\.\.\/|\.\.\\\\|%2e%2e%2f', description='CRITICAL: Directory traversal pattern detected - path traversal vulnerability')
		
		# SQL Injection Indicators (HTB Staple)
		self.add_pattern(r'(?i)id[=\s]*\d+|user[=\s]*\d+|product[=\s]*\d+', description='INFO: Numeric parameter detected - test for SQL injection')
		self.add_pattern(r'(?i)search[=\s]*["\']?([^"\'&\s]+)', description='INFO: Search parameter detected - test for SQL/NoSQL injection: {match1}')
		self.add_pattern(r'(?i)order[=\s]*["\']?([^"\'&\s]+)', description='WARNING: Order parameter detected - test for SQL injection: {match1}')
		self.add_pattern(r'(?i)sort[=\s]*["\']?([^"\'&\s]+)', description='WARNING: Sort parameter detected - test for SQL injection: {match1}')
		self.add_pattern(r'(?i)mysql_error|ora-\d+|sqlite.*error|postgres.*error', description='CRITICAL: Database error exposed - SQL injection vulnerability likely')
		
		# Command Injection Patterns (Common in HTB)
		self.add_pattern(r'(?i)cmd[=\s]*["\']?([^"\'&\s]+)', description='CRITICAL: Command parameter detected - test for command injection: {match1}')
		self.add_pattern(r'(?i)exec[=\s]*["\']?([^"\'&\s]+)', description='CRITICAL: Exec parameter detected - test for command injection: {match1}')
		self.add_pattern(r'(?i)system[=\s]*["\']?([^"\'&\s]+)', description='CRITICAL: System parameter detected - test for command injection: {match1}')
		self.add_pattern(r'(?i)ping[=\s]*["\']?([^"\'&\s]+)', description='WARNING: Ping parameter detected - test for command injection: {match1}')
		self.add_pattern(r'(?i)nslookup[=\s]*["\']?([^"\'&\s]+)', description='WARNING: NSLookup parameter detected - test for command injection: {match1}')
		
		# Template Injection (SSTI - Popular in Modern HTB)
		self.add_pattern(r'(?i)template[=\s]*["\']?([^"\'&\s]+)', description='WARNING: Template parameter detected - test for SSTI: {match1}')
		self.add_pattern(r'(?i){{.*}}|\${.*}|<%.*%>', description='CRITICAL: Template syntax detected - potential SSTI vulnerability')
		self.add_pattern(r'(?i)jinja2|twig|freemarker|velocity|thymeleaf', description='INFO: Template engine detected - test for SSTI vulnerabilities')
		
		# XXE and XML Vulnerabilities
		self.add_pattern(r'(?i)xml[=\s]*["\']?([^"\'&\s]+)', description='WARNING: XML parameter detected - test for XXE injection: {match1}')
		self.add_pattern(r'(?i)<!DOCTYPE|<!ENTITY', description='WARNING: XML DOCTYPE/ENTITY detected - potential XXE vulnerability')
		self.add_pattern(r'(?i)content-type:\s*.*xml', description='INFO: XML content type detected - test for XXE vulnerabilities')
		
		# Deserialization Vulnerabilities (Java/PHP/Python)
		self.add_pattern(r'(?i)serialized[=\s]*["\']?([^"\'&\s]+)', description='WARNING: Serialized parameter detected - test for deserialization: {match1}')
		self.add_pattern(r'(?i)rO0AB|aced0005', description='CRITICAL: Java serialized object detected - deserialization vulnerability')
		self.add_pattern(r'(?i)O:\d+:|a:\d+:', description='CRITICAL: PHP serialized object detected - deserialization vulnerability')
		self.add_pattern(r'(?i)pickle|__reduce__|cPickle', description='WARNING: Python pickle detected - potential deserialization vulnerability')
		
		# === HTB-SPECIFIC APPLICATION PATTERNS ===
		
		# Custom HTB Applications and Frameworks
		self.add_pattern(r'(?i)htb|hackthebox|hack.the.box', description='HackTheBox environment detected - CTF/practice environment')
		self.add_pattern(r'(?i)vulnhub|vulnhub\.com', description='VulnHub environment detected - vulnerable machine practice')
		self.add_pattern(r'(?i)tryhackme|thm', description='TryHackMe environment detected - cybersecurity training platform')
		self.add_pattern(r'(?i)pentesterlab', description='PentesterLab environment detected - penetration testing exercises')
		
		# Common HTB Box Technologies
		self.add_pattern(r'(?i)flask.*debug|werkzeug.*debugger', description='CRITICAL: Flask debug mode enabled - RCE via Werkzeug debugger')
		self.add_pattern(r'(?i)django.*debug.*true', description='CRITICAL: Django debug mode enabled - sensitive information disclosure')
		self.add_pattern(r'(?i)laravel.*debug.*true|app_debug.*true', description='CRITICAL: Laravel debug mode enabled - error details exposed')
		self.add_pattern(r'(?i)rails.*development|rails.*debug', description='WARNING: Rails development mode detected - potential information disclosure')
		
		# File Upload Vulnerabilities (HTB Favorite)
		self.add_pattern(r'(?i)upload\.php|uploader\.php|fileupload\.php', description='WARNING: PHP file upload script detected - test for unrestricted upload')
		self.add_pattern(r'(?i)upload\.asp|upload\.aspx', description='WARNING: ASP file upload script detected - test for unrestricted upload')
		self.add_pattern(r'(?i)multipart/form-data', description='INFO: File upload form detected - test for upload restrictions bypass')
		self.add_pattern(r'(?i)enctype.*multipart', description='INFO: File upload capability detected - test for malicious file upload')
		
		# Common HTB Backdoors and Shells
		self.add_pattern(r'(?i)shell\.php|cmd\.php|backdoor\.php', description='CRITICAL: Web shell detected - unauthorized access tool')
		self.add_pattern(r'(?i)c99|r57|b374k|wso|p0wny', description='CRITICAL: Known web shell signature detected')
		self.add_pattern(r'(?i)eval\(|system\(|exec\(|passthru\(', description='WARNING: Dangerous PHP functions detected - potential code execution')
		
		# Default Credentials and Weak Authentication (HTB Common)
		self.add_pattern(r'(?i)admin:admin|admin:password|root:root', description='CRITICAL: Default credentials detected - immediate access risk')
		self.add_pattern(r'(?i)guest:guest|test:test|demo:demo', description='WARNING: Weak default credentials detected')
		self.add_pattern(r'(?i)password.*123|password.*admin', description='WARNING: Weak password pattern detected')
		
		# === MODERN CTF/HTB TECHNOLOGIES ===
		
		# Container and Cloud Technologies
		self.add_pattern(r'(?i)docker\.sock|/var/run/docker\.sock', description='CRITICAL: Docker socket exposed - container escape possible')
		self.add_pattern(r'(?i)kubernetes.*token|k8s.*token', description='CRITICAL: Kubernetes token exposed - cluster access risk')
		self.add_pattern(r'(?i)\.dockerenv|/proc/1/cgroup.*docker', description='INFO: Running in Docker container - check for escape vectors')
		
		# API Security Issues (Modern HTB)
		self.add_pattern(r'(?i)api.*key[=\s]*["\']?([a-zA-Z0-9_-]+)', description='CRITICAL: API key exposed: {match1} - unauthorized API access')
		self.add_pattern(r'(?i)jwt[=\s]*["\']?(ey[A-Za-z0-9_-]+)', description='WARNING: JWT token detected: {match1} - check for vulnerabilities')
		self.add_pattern(r'(?i)bearer.*token|authorization.*bearer', description='INFO: Bearer token authentication detected - test for token vulnerabilities')
		
		# NoSQL Injection (Modern Applications)
		self.add_pattern(r'(?i)mongodb|nosql|{\s*"\$', description='INFO: NoSQL database detected - test for NoSQL injection')
		self.add_pattern(r'(?i){\s*"\$ne".*}|{\s*"\$gt".*}', description='WARNING: NoSQL query syntax detected - potential injection point')
		
		# JavaScript/Node.js Vulnerabilities
		self.add_pattern(r'(?i)node.*modules|package\.json', description='INFO: Node.js application detected - check for npm vulnerabilities')
		self.add_pattern(r'(?i)prototype.*pollution|__proto__', description='CRITICAL: Prototype pollution vulnerability pattern detected')
		self.add_pattern(r'(?i)eval\(.*\)|function.*constructor', description='WARNING: Dangerous JavaScript functions detected')
		
		# Cloud Storage Misconfigurations
		self.add_pattern(r'(?i)s3\.amazonaws\.com|s3.*bucket', description='INFO: AWS S3 bucket detected - check for public access')
		self.add_pattern(r'(?i)storage\.googleapis\.com|cloud\.google', description='INFO: Google Cloud Storage detected - check for misconfigurations')
		self.add_pattern(r'(?i)blob\.core\.windows\.net|azure.*storage', description='INFO: Azure Blob Storage detected - check for public access')
		
		# GraphQL Vulnerabilities (Trending in CTFs)
		self.add_pattern(r'(?i)graphql|/graphql|\{.*query.*\}', description='INFO: GraphQL endpoint detected - test for introspection, mutations')
		self.add_pattern(r'(?i)mutation|subscription|__schema', description='WARNING: GraphQL operation detected - check for authorization bypass')
		
		# Modern Authentication Bypass Patterns
		self.add_pattern(r'(?i)oauth|openid|saml', description='INFO: SSO/OAuth detected - test for authentication bypass')
		self.add_pattern(r'(?i)x-forwarded-for|x-real-ip', description='INFO: Proxy headers detected - test for IP bypass techniques')
		self.add_pattern(r'(?i)user-agent.*bypass|x-forwarded.*admin', description='WARNING: Potential authentication bypass headers detected')
		
		# Server-Side Request Forgery (SSRF)
		self.add_pattern(r'(?i)url[=\s]*["\']?(https?://[^"\'&\s]+)', description='WARNING: URL parameter detected - test for SSRF: {match1}')
		self.add_pattern(r'(?i)fetch[=\s]*["\']?([^"\'&\s]+)', description='WARNING: Fetch parameter detected - test for SSRF: {match1}')
		self.add_pattern(r'(?i)redirect[=\s]*["\']?([^"\'&\s]+)', description='WARNING: Redirect parameter detected - test for open redirect/SSRF: {match1}')
		
		# Race Conditions and Logic Flaws
		self.add_pattern(r'(?i)concurrent|parallel|async', description='INFO: Concurrent processing detected - test for race conditions')
		self.add_pattern(r'(?i)coupon|discount|promo|voucher', description='INFO: Promotional system detected - test for logic flaws')
		self.add_pattern(r'(?i)payment|billing|checkout', description='INFO: Payment system detected - test for business logic vulnerabilities')

	async def run(self, service):
		# This plugin only provides pattern matching, no active scanning
		service.info(f"🎯 CTF/HTB pattern detection active for {service.target.address}:{service.port}")
		service.info(f"📋 Monitoring for common CTF/HTB vulnerability patterns and technologies")