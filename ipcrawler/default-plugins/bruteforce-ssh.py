from ipcrawler.plugins import ServiceScan


class BruteforceSSH(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "Bruteforce SSH"
        self.tags = ["default", "ssh"]

    def configure(self):
        self.match_service_name("ssh")

    def manual(self, service, plugin_was_run):
        # Get configured wordlist paths from global.toml
        username_wordlist = self.get_global("username-wordlist") or "<username-wordlist-path>"
        password_wordlist = self.get_global("password-wordlist") or "<password-wordlist-path>"
        
        service.add_manual_command(
            "Bruteforce logins:",
            [
                'hydra -L "'
                + username_wordlist
                + '" -P "'
                + password_wordlist
                + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_ssh_hydra.txt" ssh://{addressv6}',
                'medusa -U "'
                + username_wordlist
                + '" -P "'
                + password_wordlist
                + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_ssh_medusa.txt" -M ssh -h {addressv6}',
            ],
        )
