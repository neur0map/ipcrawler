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
        
        self.add_list_option(
            "wordlist",
            default=[],
            help="The wordlist(s) to use when enumerating subdomains. Uses global.toml subdomain-wordlist setting if not specified. Default: from global.toml",
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
        
        # Get configured wordlists using global.toml fallback
        valid_wordlists = self.get_validated_wordlists("wordlist", "subdomain", None)
        
        if not valid_wordlists:
            self.error("No valid subdomain wordlists found - skipping subdomain enumeration")
            self.error("💡 Configuration required:")
            self.error("  1. Set 'subdomain-wordlist' in global.toml with a valid path")
            self.error("  2. Example: subdomain-wordlist = '/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt'")
            self.error("  3. Or use --subdomain-enum.wordlist '/path/to/your/wordlist.txt'")
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
