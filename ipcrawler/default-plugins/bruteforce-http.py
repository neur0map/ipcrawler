from ipcrawler.plugins import ServiceScan


class BruteforceHTTP(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "Bruteforce HTTP"
        self.tags = ["default", "http"]

    def configure(self):
        self.match_service_name("^http")
        self.match_service_name("^nacn_http$", negative_match=True)

    def manual(self, service, plugin_was_run):
        # Get configured wordlist paths from global.toml
        username_wordlist = self.get_global("username-wordlist") or "<username-wordlist-path>"
        password_wordlist = self.get_global("password-wordlist") or "<password-wordlist-path>"
        
        service.add_manual_commands(
            "Credential bruteforcing commands (don't run these without modifying them):",
            [
                'hydra -L "'
                + username_wordlist
                + '" -P "'
                + password_wordlist
                + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_{http_scheme}_auth_hydra.txt" {http_scheme}-get://{addressv6}/path/to/auth/area',
                'medusa -U "'
                + username_wordlist
                + '" -P "'
                + password_wordlist
                + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_{http_scheme}_auth_medusa.txt" -M http -h {addressv6} -m DIR:/path/to/auth/area',
                'hydra -L "'
                + username_wordlist
                + '" -P "'
                + password_wordlist
                + '" -e nsr -s {port} -o "{scandir}/{protocol}_{port}_{http_scheme}_form_hydra.txt" {http_scheme}-post-form://{addressv6}/path/to/login.php:"username=^USER^&password=^PASS^":"invalid-login-message"',
                'medusa -U "'
                + username_wordlist
                + '" -P "'
                + password_wordlist
                + '" -e ns -n {port} -O "{scandir}/{protocol}_{port}_{http_scheme}_form_medusa.txt" -M web-form -h {addressv6} -m FORM:/path/to/login.php -m FORM-DATA:"post?username=&password=" -m DENY-SIGNAL:"invalid login message"',
            ],
        )
