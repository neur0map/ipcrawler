from ipcrawler.plugins import ServiceScan
from ipcrawler.config import config
from shutil import which
import os


class DirBuster(ServiceScan):

    def __init__(self):
        super().__init__()
        self.name = "Directory Buster"
        self.slug = "dirbuster"
        self.priority = 0
        self.tags = ["default", "safe", "long", "http"]

    def configure(self):
        self.add_choice_option(
            "tool",
            default="feroxbuster",
            choices=["feroxbuster", "gobuster", "dirsearch", "ffuf", "dirb"],
            help="The tool to use for directory busting. Default: %(default)s",
        )
        self.add_list_option(
            "wordlist",
            default=[os.path.join(config["data_dir"], "wordlists", "dirbuster.txt")],
            help="The wordlist(s) to use when directory busting. Separate multiple wordlists with spaces. Default: %(default)s",
        )
        self.add_option(
            "threads", default=10, help="The number of threads to use when directory busting. Default: %(default)s"
        )
        self.add_option(
            "ext",
            default="txt,html,php,asp,aspx,jsp",
            help="The extensions you wish to fuzz (no dot, comma separated). Default: %(default)s",
        )
        self.add_true_option(
            "recursive",
            help="Enables recursive searching (where available). Warning: This may cause significant increases to scan times. Default: %(default)s",
        )
        self.add_option(
            "extras",
            default="",
            help="Any extra options you wish to pass to the tool when it runs. e.g. --dirbuster.extras='-s 200,301 --discover-backup'",
        )
        self.match_service_name("^http")
        self.match_service_name("^nacn_http$", negative_match=True)

    def check(self):
        # List of tools in order of preference
        tools_to_try = ["feroxbuster", "gobuster", "ffuf", "dirsearch", "dirb"]

        # Get configured tool, defaulting to feroxbuster if not available
        try:
            configured_tool = self.get_option("tool")
        except Exception as e:
            configured_tool = "feroxbuster"  # Default fallback

        # First, check if the configured tool is available
        if which(configured_tool) is not None:
            return True

        # If configured tool isn't available, try to find any available tool
        available_tool = None
        for tool in tools_to_try:
            if which(tool) is not None:
                available_tool = tool
                break

        if available_tool:
            # Auto-switch to the first available tool
            try:
                # Set the option directly in the args namespace
                option_name = self.slug.replace("-", "_") + ".tool"
                setattr(self.ipcrawler.args, option_name, available_tool)
                self.info(f"Switched from {configured_tool} to {available_tool} (auto-detected)")
            except:
                # If setting fails, just continue - the plugin will use the default
                pass
            return True
        else:
            # No directory busting tools found
            self.error("No directory busting tools found. Please install one of: " + ", ".join(tools_to_try))
            self.error("On Kali: sudo apt install feroxbuster gobuster dirsearch dirb")
            self.error("On macOS: brew install feroxbuster gobuster ffuf")
            return False

    async def run(self, service):
        dot_extensions = ",".join(["." + x for x in self.get_option("ext").split(",")])
        for wordlist in self.get_option("wordlist"):
            name = os.path.splitext(os.path.basename(wordlist))[0]
            if self.get_option("tool") == "feroxbuster":
                await service.execute(
                    "feroxbuster -u {http_scheme}://{addressv6}:{port}/ -t "
                    + str(self.get_option("threads"))
                    + ' -w "'
                    + wordlist
                    + '" -x "'
                    + self.get_option("ext")
                    + '" -v -k '
                    + ("" if self.get_option("recursive") else "-n ")
                    + '-q -e -r -o "{scandir}/{protocol}_{port}_{http_scheme}_feroxbuster_'
                    + name
                    + '.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                )

            elif self.get_option("tool") == "gobuster":
                await service.execute(
                    "gobuster dir -u {http_scheme}://{addressv6}:{port}/ -t "
                    + str(self.get_option("threads"))
                    + ' -w "'
                    + wordlist
                    + '" -e -k -x "'
                    + self.get_option("ext")
                    + '" -z -r -o "{scandir}/{protocol}_{port}_{http_scheme}_gobuster_'
                    + name
                    + '.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                )

            elif self.get_option("tool") == "dirsearch":
                if service.target.ipversion == "IPv6":
                    service.error("dirsearch does not support IPv6.")
                else:
                    await service.execute(
                        "dirsearch -u {http_scheme}://{address}:{port}/ -t "
                        + str(self.get_option("threads"))
                        + ' -e "'
                        + self.get_option("ext")
                        + '" -f -q -F '
                        + ("-r " if self.get_option("recursive") else "")
                        + '-w "'
                        + wordlist
                        + '" --format=plain -o "{scandir}/{protocol}_{port}_{http_scheme}_dirsearch_'
                        + name
                        + '.txt"'
                        + (" " + self.get_option("extras") if self.get_option("extras") else "")
                    )

            elif self.get_option("tool") == "ffuf":
                await service.execute(
                    "ffuf -u {http_scheme}://{addressv6}:{port}/FUZZ -t "
                    + str(self.get_option("threads"))
                    + ' -w "'
                    + wordlist
                    + '" -e "'
                    + dot_extensions
                    + '" -v -r '
                    + ("-recursion " if self.get_option("recursive") else "")
                    + "-noninteractive"
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                    + " | tee {scandir}/{protocol}_{port}_{http_scheme}_ffuf_"
                    + name
                    + ".txt"
                )

            elif self.get_option("tool") == "dirb":
                await service.execute(
                    'dirb {http_scheme}://{addressv6}:{port}/ "'
                    + wordlist
                    + '" -l '
                    + ("" if self.get_option("recursive") else "-r ")
                    + '-S -X ",'
                    + dot_extensions
                    + '" -f -o "{scandir}/{protocol}_{port}_{http_scheme}_dirb_'
                    + name
                    + '.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                )

    def manual(self, service, plugin_was_run):
        dot_extensions = ",".join(["." + x for x in self.get_option("ext").split(",")])
        if self.get_option("tool") == "feroxbuster":
            service.add_manual_command(
                "(feroxbuster) Multi-threaded recursive directory/file enumeration for web servers using various wordlists:",
                [
                    "feroxbuster -u {http_scheme}://{addressv6}:{port} -t "
                    + str(self.get_option("threads"))
                    + ' -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x "'
                    + self.get_option("ext")
                    + '" -v -k '
                    + ("" if self.get_option("recursive") else "-n ")
                    + "-e -r -o {scandir}/{protocol}_{port}_{http_scheme}_feroxbuster_dirbuster.txt"
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                ],
            )
        elif self.get_option("tool") == "gobuster":
            service.add_manual_command(
                "(gobuster v3) Multi-threaded directory/file enumeration for web servers using various wordlists:",
                [
                    "gobuster dir -u {http_scheme}://{addressv6}:{port}/ -t "
                    + str(self.get_option("threads"))
                    + ' -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -e -k -x "'
                    + self.get_option("ext")
                    + '" -r -o "{scandir}/{protocol}_{port}_{http_scheme}_gobuster_dirbuster.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                ],
            )
        elif self.get_option("tool") == "dirsearch":
            if service.target.ipversion == "IPv4":
                service.add_manual_command(
                    "(dirsearch) Multi-threaded recursive directory/file enumeration for web servers using various wordlists:",
                    [
                        "dirsearch -u {http_scheme}://{address}:{port}/ -t "
                        + str(self.get_option("threads"))
                        + ' -e "'
                        + self.get_option("ext")
                        + '" -f -F '
                        + ("-r " if self.get_option("recursive") else "")
                        + '-w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt --format=plain --output="{scandir}/{protocol}_{port}_{http_scheme}_dirsearch_dirbuster.txt"'
                        + (" " + self.get_option("extras") if self.get_option("extras") else "")
                    ],
                )
        elif self.get_option("tool") == "ffuf":
            service.add_manual_command(
                "(ffuf) Multi-threaded recursive directory/file enumeration for web servers using various wordlists:",
                [
                    "ffuf -u {http_scheme}://{addressv6}:{port}/FUZZ -t "
                    + str(self.get_option("threads"))
                    + ' -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt -e "'
                    + dot_extensions
                    + '" -v -r '
                    + ("-recursion " if self.get_option("recursive") else "")
                    + "-noninteractive"
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                    + " | tee {scandir}/{protocol}_{port}_{http_scheme}_ffuf_dirbuster.txt"
                ],
            )
        elif self.get_option("tool") == "dirb":
            service.add_manual_command(
                "(dirb) Recursive directory/file enumeration for web servers using various wordlists:",
                [
                    "dirb {http_scheme}://{addressv6}:{port}/ /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -l "
                    + ("" if self.get_option("recursive") else "-r ")
                    + '-X ",'
                    + dot_extensions
                    + '" -f -o "{scandir}/{protocol}_{port}_{http_scheme}_dirb_dirbuster.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                ],
            )
