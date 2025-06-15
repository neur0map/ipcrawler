from ipcrawler.plugins import ServiceScan
from shutil import which


class DnsReconSubdomainBruteforce(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "DnsRecon Bruteforce Subdomains"
        self.slug = "dnsrecon-brute"
        self.priority = 0
        self.tags = ["default", "safe", "long", "dns"]

    def configure(self):
        self.add_option(
            "timeout",
            default=1800,
            help="Maximum time in seconds for DNS subdomain bruteforce (30 minutes). Default: %(default)s",
        )
        self.match_service_name("^domain")

    def check(self):
        if which("dnsrecon") is None:
            self.error(
                "The program dnsrecon could not be found. Make sure it is installed. (On Kali, run: sudo apt install dnsrecon)"
            )
            return False
        return True

    def manual(self, service, plugin_was_run):
        domain_name = "<DOMAIN-NAME>"
        timeout_seconds = self.get_option("timeout")
        if self.get_global("domain"):
            domain_name = self.get_global("domain")
        service.add_manual_command(
            "Use dnsrecon to bruteforce subdomains of a DNS domain.",
            [
                "timeout " + str(timeout_seconds) + " dnsrecon -n {address} -d "
                + domain_name
                + " -D /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt -t brt 2>&1 | tee {scandir}/{protocol}_{port}_dnsrecon_subdomain_bruteforce.txt",
            ],
        )
