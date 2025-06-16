from ipcrawler.plugins import ServiceScan


class BruteforceSMB(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "Bruteforce SMB"
        self.tags = ["default", "safe", "active-directory"]

    def configure(self):
        self.match_service("tcp", 445, "^microsoft\-ds")
        self.match_service("tcp", 139, "^netbios")

    def manual(self, service, plugin_was_run):
        # Get configured wordlist paths from global.toml
        username_wordlist = self.get_global("username-wordlist") or "<username-wordlist-path>"
        password_wordlist = self.get_global("password-wordlist") or "<password-wordlist-path>"
        
        service.add_manual_command(
            "Bruteforce SMB",
            [
                'crackmapexec smb {address} --port={port} -u "'
                + username_wordlist
                + '" -p "'
                + password_wordlist
                + '"'
            ],
        )
