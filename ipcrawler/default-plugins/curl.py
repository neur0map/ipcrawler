from ipcrawler.plugins import ServiceScan
from ipcrawler.io import vhost_manager
import os
import re


class Curl(ServiceScan):

    def __init__(self):
        super().__init__()
        self.name = "Curl"
        self.tags = ["default", "safe", "http"]

    def configure(self):
        self.add_option("path", default="/", help="The path on the web server to curl. Default: %(default)s")
        self.match_service_name("^http")
        self.match_service_name("^nacn_http$", negative_match=True)
        self.add_pattern("(?i)powered[ -]by[^\n]+")

    async def run(self, service):
        # Standard curl scan
        await service.execute(
            'curl -sSik {http_scheme}://{addressv6}:{port}/ -m 10 2>&1 | tee "{scandir}/{protocol}_{port}_{http_scheme}_index.html"'
        )

        # Try to detect vhosts from response - read the output file
        try:
            index_file = f"{service.target.scandir}/{service.protocol}_{service.port}_{'https' if service.secure else 'http'}_index.html"
            if os.path.exists(index_file):
                with open(index_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Look for common vhost patterns in response
                vhost_patterns = [
                    r"Server\s*Name\s*[:\s]+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",  # Server Name: example.com
                    r"Host\s*:\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",  # Host: example.com
                    r'href=[\'"]+https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # href="http://example.com"
                    r'action=[\'"]+https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # action="http://example.com"
                    r"<title>[^<]*([a-zA-Z0-9.-]+\.htb)[^<]*</title>",  # HTB machines often have .htb in title
                    r"Location:\s*https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",  # Location header
                ]

                for pattern in vhost_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for hostname in matches:
                        hostname = hostname.strip().lower()
                        # Filter out obvious false positives
                        if (
                            hostname != service.target.address
                            and len(hostname) > 3
                            and "." in hostname
                            and not hostname.startswith("www.example")
                            and not hostname.endswith(".local")
                        ):

                            service.info(f"🌐 Potential VHost detected in response: {hostname}")

                            # Try to auto-add if conditions are met
                            success = vhost_manager.add_vhost_entry(service.target.address, hostname)
                            if not success and not vhost_manager.auto_add_enabled:
                                vhost_manager.suggest_manual_add(service.target.address, hostname)

        except Exception as e:
            service.debug(f"VHost detection error: {e}")

    def manual(self, service, plugin_was_run):
        if not plugin_was_run:
            service.add_manual_command("(curl) query the index page:", "curl -sSik {http_scheme}://{addressv6}:{port}/")
