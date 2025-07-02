from ipcrawler.plugins import ServiceScan

class NmapHTTP(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Nmap HTTP"
		self.description = "HTTP service enumeration using nmap scripts"
		self.tags = ['default', 'safe', 'http']

	def configure(self):
		self.match_service_name('^http')
		self.match_service_name('ssl/http')
		self.match_service_name('^https')
		self.match_service_name('^nacn_http$', negative_match=True)
		
		# Enhanced HTTP Server Detection with Security Context
		self.add_pattern(r'Server:\s*nginx[/\s]*([\d\.]+)?', description='Nginx Web Server v{match1} detected - reverse proxy/load balancer')
		self.add_pattern(r'Server:\s*Apache[/\s]*([\d\.]+)?', description='Apache HTTP Server v{match1} detected - web server')
		self.add_pattern(r'Server:\s*Microsoft-IIS[/\s]*([\d\.]+)?', description='Microsoft IIS v{match1} detected - Windows web server')
		self.add_pattern(r'Server:\s*cloudflare', description='Cloudflare CDN detected - traffic routing through Cloudflare infrastructure')
		self.add_pattern(r'Server:\s*LiteSpeed[/\s]*([\d\.]+)?', description='LiteSpeed Web Server v{match1} detected - high-performance web server')
		self.add_pattern(r'Server:\s*Caddy[/\s]*([\d\.]+)?', description='Caddy Web Server v{match1} detected - automatic HTTPS server')
		self.add_pattern(r'Server:\s*Jetty[/\s]*([\d\.]+)?', description='Eclipse Jetty v{match1} detected - Java HTTP server')
		self.add_pattern(r'Server:\s*Tomcat[/\s]*([\d\.]+)?', description='Apache Tomcat v{match1} detected - Java servlet container')
		self.add_pattern(r'Server:\s*Kestrel', description='Microsoft Kestrel detected - .NET Core web server')
		self.add_pattern(r'Server:\s*gunicorn[/\s]*([\d\.]+)?', description='Gunicorn v{match1} detected - Python WSGI HTTP server')
		self.add_pattern(r'Server:\s*uvicorn[/\s]*([\d\.]+)?', description='Uvicorn v{match1} detected - Python ASGI server (FastAPI/Starlette)')
		self.add_pattern(r'Server:\s*([^\n\r]+)', description='HTTP Server detected: {match1} - investigate for version vulnerabilities')
		
		# Security Headers Analysis
		self.add_pattern(r'X-Powered-By:\s*([^\n\r]+)', description='Technology Stack disclosed via X-Powered-By: {match1}')
		self.add_pattern(r'X-AspNet-Version:\s*([^\n\r]+)', description='ASP.NET Version disclosed: {match1} - check for known vulnerabilities')
		self.add_pattern(r'X-Frame-Options:\s*([^\n\r]+)', description='X-Frame-Options header present: {match1} - clickjacking protection')
		self.add_pattern(r'Content-Security-Policy:\s*([^\n\r]+)', description='Content Security Policy detected - XSS protection enabled')
		self.add_pattern(r'Strict-Transport-Security:\s*([^\n\r]+)', description='HSTS header present: {match1} - HTTPS enforcement')
		self.add_pattern(r'X-Content-Type-Options:\s*nosniff', description='X-Content-Type-Options: nosniff - MIME type sniffing protection')
		
		# WebDAV and File Access
		self.add_pattern('WebDAV is ENABLED', description='WebDAV enabled - file upload/download capabilities may be accessible')
		self.add_pattern(r'Allow:\s*([^\n\r]*(?:PUT|DELETE|PROPFIND|MKCOL)[^\n\r]*)', description='HTTP methods enabled: {match1} - potential file manipulation')
		
		# Authentication and Session Management
		self.add_pattern(r'WWW-Authenticate:\s*([^\n\r]+)', description='Authentication required: {match1} - credential testing opportunity')
		self.add_pattern(r'Set-Cookie:\s*([^\n\r]*session[^\n\r]*)', description='Session cookie detected: {match1} - session management analysis')
		
		# Cloud and CDN Detection
		self.add_pattern(r'CF-RAY:\s*([a-f0-9\-]+)', description='Cloudflare Ray ID: {match1} - traffic routed through Cloudflare')
		self.add_pattern(r'X-Amz-', description='Amazon AWS infrastructure detected - cloud-hosted application')
		self.add_pattern(r'X-Azure-', description='Microsoft Azure infrastructure detected - cloud-hosted application')
		self.add_pattern(r'X-Goog-', description='Google Cloud Platform detected - cloud-hosted application')
		
		# Application Framework Detection
		self.add_pattern(r'X-Django-Version:\s*([^\n\r]+)', description='Django Framework v{match1} detected - Python web framework')
		self.add_pattern(r'X-Rails-Version:\s*([^\n\r]+)', description='Ruby on Rails v{match1} detected - Ruby web framework')
		self.add_pattern(r'X-Laravel-Version:\s*([^\n\r]+)', description='Laravel Framework v{match1} detected - PHP web framework')
		
		# Additional HTB/CTF Common Patterns
		self.add_pattern(r'(?i)robots\.txt', description='Robots.txt file detected - check for hidden directories and files')
		self.add_pattern(r'(?i)sitemap\.xml', description='Sitemap.xml detected - check for additional endpoints')
		self.add_pattern(r'(?i)backup|\.bak|\.old|\.backup', description='Backup files detected - potential sensitive data exposure')
		self.add_pattern(r'(?i)\.env|environment|config\.', description='Configuration files detected - check for credentials and secrets')
		self.add_pattern(r'(?i)admin|administrator|management|dashboard', description='Administrative interface detected - check for default credentials')
		self.add_pattern(r'(?i)login|signin|auth|authenticate', description='Authentication endpoint detected - test for bypass techniques')
		self.add_pattern(r'(?i)upload|file-upload|uploader', description='File upload functionality detected - test for unrestricted file upload')
		self.add_pattern(r'(?i)search|query|q=', description='Search functionality detected - test for SQL injection, NoSQL injection')
		self.add_pattern(r'(?i)debug|trace|test|dev', description='Debug/Development endpoints detected - potential information disclosure')
		
		# Database and Backend Detection
		self.add_pattern(r'(?i)mysql|mariadb', description='MySQL/MariaDB database detected')
		self.add_pattern(r'(?i)postgresql|postgres', description='PostgreSQL database detected')
		self.add_pattern(r'(?i)mongodb|mongo', description='MongoDB NoSQL database detected')
		self.add_pattern(r'(?i)elasticsearch|elastic', description='Elasticsearch search engine detected')
		self.add_pattern(r'(?i)sqlite', description='SQLite database detected')
		self.add_pattern(r'(?i)oracle|oracledb', description='Oracle Database detected')
		self.add_pattern(r'(?i)mssql|sqlserver', description='Microsoft SQL Server detected')
		
		# Security Misconfigurations
		self.add_pattern(r'(?i)directory.listing|index.of', description='Directory listing enabled - potential information disclosure')
		self.add_pattern(r'(?i)403.forbidden|access.denied', description='Access denied responses - potential hidden content')
		self.add_pattern(r'(?i)500.internal.server.error', description='Internal server errors detected - potential debug information')
		self.add_pattern(r'(?i)timeout|connection.refused', description='Service timeouts detected - potential DoS vulnerability')
		
		# Session and Cookie Analysis
		self.add_pattern(r'PHPSESSID=([A-Za-z0-9]+)', description='PHP Session ID detected: {match1} - session management analysis')
		self.add_pattern(r'JSESSIONID=([A-F0-9]+)', description='Java Session ID detected: {match1} - session management analysis')
		self.add_pattern(r'ASP\.NET_SessionId=([A-Za-z0-9]+)', description='ASP.NET Session ID detected: {match1} - session management analysis')
		self.add_pattern(r'(?i)secure;\s*httponly', description='Secure session cookies detected - good security practice')
		self.add_pattern(r'(?i)samesite=', description='SameSite cookie attribute detected - CSRF protection')
		
		# Error Messages and Information Disclosure
		self.add_pattern(r'(?i)stack.trace|exception|error', description='Error messages detected - potential information disclosure')
		self.add_pattern(r'(?i)sql.syntax|mysql.error|ora-[0-9]+', description='Database error messages detected - potential SQL injection')
		self.add_pattern(r'(?i)path.disclosure|file.not.found', description='Path disclosure detected - filesystem information exposed')
		self.add_pattern(r'(?i)version.information|server.version', description='Version information disclosed - check for known vulnerabilities')

	async def run(self, service):
		await service.execute('nmap {nmap_extra} -T5 --min-rate=5000 --max-rate=10000 -sV -p {port} --script="banner,(http* or ssl*) and not (brute or broadcast or dos or external or http-slowloris* or fuzzer)" -oN "{scandir}/{protocol}_{port}_{http_scheme}_nmap.txt" -oX "{scandir}/xml/{protocol}_{port}_{http_scheme}_nmap.xml" {address}', outfile='{protocol}_{port}_{http_scheme}_nmap.txt')
