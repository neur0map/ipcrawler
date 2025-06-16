from ipcrawler.plugins import ServiceScan
import os


class SubdomainEnumeration(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "Subdomain Enumeration"
        self.slug = "subdomain-enum"
        self.tags = ["default", "safe", "long", "dns"]

    def configure(self):
        self.add_option(
            "domain",
            help="The domain to use as the base domain (e.g. example.com) for subdomain enumeration. Default: %(default)s",
        )
        
        # Get configured subdomain wordlist from global.toml (no fallbacks)
        global_wordlist = self.get_global("subdomain-wordlist")
        default_wordlist = [global_wordlist] if global_wordlist else []
        
        self.add_list_option(
            "wordlist",
            default=default_wordlist,
            help="The wordlist(s) to use when enumerating subdomains. Separate multiple wordlists with spaces. Configure subdomain-wordlist in global.toml. Default: %(default)s",
        )
        self.add_option(
            "threads", default=10, help="The number of threads to use when enumerating subdomains. Default: %(default)s"
        )
        self.add_option(
            "timeout",
            default=1800,
            help="Maximum time in seconds for subdomain enumeration (30 minutes). Default: %(default)s",
        )
        self.match_service_name("^domain")

    async def run(self, service):
        domains = []
        
        # Get configured wordlists (no hardcoded fallbacks)
        configured_wordlists = self.get_option("wordlist")
        if not configured_wordlists:
            self.error("No subdomain-wordlist configured in global.toml. Please add: subdomain-wordlist = \"/path/to/wordlist\"")
            return
            
        # Validate configured wordlists exist
        valid_wordlists = []
        for wordlist in configured_wordlists:
            if os.path.exists(wordlist):
                valid_wordlists.append(wordlist)
            else:
                self.error(f"Wordlist not found: {wordlist}")
                
        if not valid_wordlists:
            self.error("No valid wordlists found - check your subdomain-wordlist configuration in global.toml")
            return

        if self.get_option("domain"):
            domains.append(self.get_option("domain"))

        if self.get_global("domain") and self.get_global("domain") not in domains:
            domains.append(self.get_global("domain"))

        if not domains:
            self.error("No domain specified for subdomain enumeration.")
            self.error("Please specify a domain using --subdomain-enum.domain or set it in global.toml")
            return

        self.info(f"Starting subdomain enumeration with {len(valid_wordlists)} wordlist(s) for {len(domains)} domain(s)")

        for domain in domains:
            for wordlist in valid_wordlists:
                name = os.path.splitext(os.path.basename(wordlist))[0]
                timeout_seconds = self.get_option("timeout")
                
                cmd = (
                    "timeout " + str(timeout_seconds) + " dnsrecon -n {address} -d "
                    + domain
                    + " -D "
                    + wordlist
                    + " -t brt --threads "
                    + str(self.get_option("threads"))
                    + " 2>&1 | tee {scandir}/{protocol}_{port}_dnsrecon_subdomain_"
                    + name
                    + "_"
                    + domain.replace(".", "_")
                    + ".txt"
                )
                await service.execute(cmd)
