from ipcrawler.plugins import ServiceScan
from shutil import which
import os, requests, random, string, urllib3

urllib3.disable_warnings()


class VirtualHost(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "Virtual Host Enumeration"
        self.slug = "vhost-enum"
        self.tags = ["default", "safe", "http", "long"]
        self.priority = 5  # Lower priority than VHost Redirect Hunter

    def configure(self):
        self.add_option(
            "hostname",
            help="The hostname to use as the base host (e.g. example.com) for virtual host enumeration. Default: %(default)s",
        )
        
        self.add_list_option(
            "wordlist",
            default=[],
            help="The wordlist(s) to use when enumerating virtual hosts. Uses global.toml vhost-wordlist setting if not specified. Default: from global.toml",
        )
        self.add_option(
            "threads", default=10, help="The number of threads to use when enumerating virtual hosts. Default: %(default)s"
        )
        self.match_service_name("^http")
        self.match_service_name("^nacn_http$", negative_match=True)

    async def run(self, service):
        hostnames = []
        
        # Get configured wordlists using global.toml fallback
        valid_wordlists = self.get_validated_wordlists("wordlist", "vhost", None)
        
        if not valid_wordlists:
            self.error("No valid vhost wordlists found - skipping virtual host enumeration")
            self.error("💡 Configuration required:")
            self.error("  1. Set 'vhost-wordlist' in global.toml with a valid path")
            self.error("  2. Example: vhost-wordlist = '/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt'")
            self.error("  3. Or use --vhost-enum.wordlist '/path/to/your/wordlist.txt'")
            return
        
        if self.get_option("hostname"):
            hostnames.append(self.get_option("hostname"))
        if service.target.type == "hostname" and service.target.address not in hostnames:
            hostnames.append(service.target.address)
        if self.get_global("domain") and self.get_global("domain") not in hostnames:
            hostnames.append(self.get_global("domain"))
        
        # Check for hostnames discovered by VHost Redirect Hunter
        if hasattr(service.target, "discovered_vhosts") and service.target.discovered_vhosts:
            for vhost_info in service.target.discovered_vhosts:
                discovered_hostname = vhost_info.get("hostname")
                if discovered_hostname and discovered_hostname not in hostnames:
                    hostnames.append(discovered_hostname)
                    self.info(f"Using hostname discovered by VHost Redirect Hunter: {discovered_hostname}")

        if not hostnames:
            self.warn("Skipping virtual host enumeration - no hostname available")
            self.info("💡 VHost Redirect Hunter should have discovered hostnames automatically")
            self.info("💡 Alternative options to enable virtual host enumeration:")
            self.info("   1. Use --vhost-enum.hostname=example.com")
            self.info("   2. Set domain in global.toml: [global.domain] default = 'example.com'")
            self.info("   3. Or scan a hostname target instead of an IP")
            return

        self.info(f"Starting virtual host enumeration with {len(valid_wordlists)} wordlist(s) for {len(hostnames)} hostname(s)")

        for wordlist in valid_wordlists:
            name = os.path.splitext(os.path.basename(wordlist))[0]
            for hostname in hostnames:
                try:
                    wildcard = requests.get(
                        ("https" if service.secure else "http")
                        + "://"
                        + service.target.address
                        + ":"
                        + str(service.port)
                        + "/",
                        headers={"Host": "".join(random.choice(string.ascii_letters) for _ in range(20)) + "." + hostname},
                        verify=False,
                        allow_redirects=False,
                    )
                    size = str(len(wildcard.content))
                except requests.exceptions.RequestException as e:
                    service.error(f"[!] Wildcard request failed for {hostname}: {e}")
                    continue

                await service.execute(
                    "ffuf -u {http_scheme}://"
                    + hostname
                    + ":{port}/ -t "
                    + str(self.get_option("threads"))
                    + " -w "
                    + wordlist
                    + ' -H "Host: FUZZ.'
                    + hostname
                    + '" -mc all -fs '
                    + size
                    + ' -r -noninteractive -s | tee "{scandir}/{protocol}_{port}_{http_scheme}_'
                    + hostname
                    + "_vhosts_"
                    + name
                    + '.txt"'
                )
