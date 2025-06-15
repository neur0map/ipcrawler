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
        
        # Check for global vhost wordlist first, fallback to plugin default
        global_wordlist = self.get_global("vhost-wordlist")
        default_wordlist = [global_wordlist] if global_wordlist else ["/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt"]
        
        self.add_list_option(
            "wordlist",
            default=default_wordlist,
            help="The wordlist(s) to use when enumerating virtual hosts. Separate multiple wordlists with spaces. Global setting takes priority. Default: %(default)s",
        )
        self.add_option(
            "threads", default=10, help="The number of threads to use when enumerating virtual hosts. Default: %(default)s"
        )
        self.match_service_name("^http")
        self.match_service_name("^nacn_http$", negative_match=True)

    async def run(self, service):
        hostnames = []
        
        # Validate wordlists before running
        fallback_wordlists = [
            "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
            "/usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt",
            "/usr/share/wordlists/dnsrecon/namelist.txt",
            "/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt"
        ]
        
        valid_wordlists = self.get_validated_wordlists("wordlist", "virtual host", fallback_wordlists)
        
        if not valid_wordlists:
            self.error("No valid virtual host wordlists found - skipping virtual host enumeration")
            self.error("Please check your wordlist paths in global.toml or config.toml")
            return
        
        if self.get_option("hostname"):
            hostnames.append(self.get_option("hostname"))
        if service.target.type == "hostname" and service.target.address not in hostnames:
            hostnames.append(service.target.address)
        if self.get_global("domain") and self.get_global("domain") not in hostnames:
            hostnames.append(self.get_global("domain"))

        if not hostnames:
            self.error("No hostname specified for virtual host enumeration.")
            self.error("Please specify a hostname using --vhost-enum.hostname or set domain in global.toml")
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
