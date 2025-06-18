from ipcrawler.plugins import ServiceScan
import requests
from urllib.parse import urlparse
import urllib3

urllib3.disable_warnings()


class RedirectHostnameDiscovery(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "Redirect Hostname Discovery"
        self.slug = "redirect-host-discovery"
        self.tags = ["default", "http", "quick"]
        self.priority = 2  # Lower priority number = higher priority = runs before VHost enumeration (5)

    def configure(self):
        self.match_service_name("^http")
        self.match_service_name("^nacn_http$", negative_match=True)

    async def run(self, service):
        try:
            url = f"{'https' if service.secure else 'http'}://{service.target.address}:{service.port}/"
            resp = requests.get(url, verify=False, allow_redirects=False)

            if "Location" in resp.headers:
                location = resp.headers["Location"]
                parsed = urlparse(location)
                redirect_host = parsed.hostname

                if redirect_host:
                    service.info(f"[+] Redirect detected: {url} → {location}")
                    service.info(f"[+] Hostname found in redirect: {redirect_host}")
                    
                    # Store discovered hostname for other plugins to use
                    if not hasattr(service.target, "discovered_vhosts"):
                        service.target.discovered_vhosts = []
                    
                    vhost_info = {
                        "hostname": redirect_host,
                        "ip": service.target.address,
                        "port": service.port,
                        "scheme": "https" if service.secure else "http",
                        "original_url": url,
                        "redirect_url": location,
                        "status_code": resp.status_code,
                        "discovered_by": "redirect-host-discovery"
                    }
                    
                    service.target.discovered_vhosts.append(vhost_info)
                    service.info(f"[+] Hostname stored for virtual host enumeration: {redirect_host}")
                else:
                    service.info(f"[+] Redirect detected, but no hostname could be parsed: {location}")
            else:
                service.info(f"[-] No redirect detected at {url}")

        except Exception as e:
            service.error(f"[!] Error during redirect check on {service.target.address}:{service.port} — {e}")
