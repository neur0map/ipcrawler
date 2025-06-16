from ipcrawler.plugins import ServiceScan


class SMTPUserEnum(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "SMTP-User-Enum"
        self.tags = ["default", "safe", "smtp", "email"]

    def configure(self):
        self.match_service_name("^smtp")

    async def run(self, service):
        # Get configured wordlist path from global.toml
        username_wordlist = self.get_global("username-wordlist")
        if not username_wordlist:
            self.error("No username-wordlist configured in global.toml. Please add: username-wordlist = \"/path/to/wordlist\"")
            return
            
        await service.execute(
            'hydra smtp-enum://{addressv6}:{port}/vrfy -L "'
            + username_wordlist
            + '" 2>&1',
            outfile="{protocol}_{port}_smtp_user-enum_hydra_vrfy.txt",
        )
        await service.execute(
            'hydra smtp-enum://{addressv6}:{port}/expn -L "'
            + username_wordlist
            + '" 2>&1',
            outfile="{protocol}_{port}_smtp_user-enum_hydra_expn.txt",
        )

    def manual(self, service, plugin_was_run):
        # Get configured wordlist path from global.toml
        username_wordlist = self.get_global("username-wordlist") or "<username-wordlist-path>"
        
        service.add_manual_command(
            'Try User Enumeration using "RCPT TO". Replace <TARGET-DOMAIN> with the target\'s domain name:',
            [
                'hydra smtp-enum://{addressv6}:{port}/rcpt -L "'
                + username_wordlist
                + '" -o "{scandir}/{protocol}_{port}_smtp_user-enum_hydra_rcpt.txt" -p <TARGET-DOMAIN>'
            ],
        )
