from ipcrawler.plugins import ServiceScan


class BruteforceRDP(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "Bruteforce RDP"
        self.tags = ["default", "rdp"]

    def configure(self):
        self.match_service_name(["^rdp", "^ms\-wbt\-server", "^ms\-term\-serv"])

    def manual(self, service, plugin_was_run):
        # Get configured wordlist paths from global.toml
        username_wordlist = self.get_global("username-wordlist") or "<username-wordlist-path>"
        password_wordlist = self.get_global("password-wordlist") or "<password-wordlist-path>"
        
        service.add_manual_commands(
            "Bruteforce logins:",
            [
                'hydra -L "'
                + username_wordlist
                + '" -P "'
                + password_wordlist
                + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_rdp_hydra.txt" rdp://{addressv6}',
                'medusa -U "'
                + username_wordlist
                + '" -P "'
                + password_wordlist
                + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_rdp_medusa.txt" -M rdp -h {addressv6}',
            ],
        )
