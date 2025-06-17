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
            choices=["feroxbuster", "gobuster", "ffuf", "dirsearch", "dirb"],
            default="feroxbuster",
            help="The tool to use for directory busting. Default: %(default)s",
        )
        
        # Use global directory wordlist from global.toml - no hardcoded defaults
        global_wordlist = self.get_global("directory-wordlist")
        default_wordlist = [global_wordlist] if global_wordlist else []
        
        self.add_list_option(
            "wordlist",
            default=default_wordlist,
            help="The wordlist(s) to use when directory busting. Separate multiple wordlists with spaces. Global setting takes priority. Default: %(default)s",
        )
        self.add_option(
            "threads", default=15, help="The number of threads to use when directory busting. Default: %(default)s"
        )
        self.add_option(
            "ext",
            default="txt,html,php,asp,aspx,jsp",
            help="The extensions you wish to fuzz (comma separated). Default: %(default)s",
        )
        self.add_true_option("recursive", help="Enable recursive directory busting. Default: %(default)s")
        self.add_option(
            "timeout",
            default=600,
            help="Maximum time in seconds for directory busting (10 minutes). Default: %(default)s",
        )
        self.add_true_option(
            "parallel-wordlists",
            help="Run multiple wordlists in parallel instead of sequentially. Default: %(default)s"
        )
        self.add_option(
            "max_depth",
            default=3,
            help="Maximum recursion depth to prevent infinite loops. Default: %(default)s",
        )
        self.add_option(
            "request_timeout",
            default=10,
            help="Request timeout in seconds for each HTTP request. Default: %(default)s",
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
        timeout_seconds = self.get_option("timeout")
        max_depth = self.get_option("max_depth")
        
        # Respect user configuration - only use wordlists specified in global.toml/config
        # No hardcoded fallbacks - if user wants specific wordlists, they configure them
        valid_wordlists = self.get_validated_wordlists("wordlist", "directory", None)
        
        if not valid_wordlists:
            self.error("No valid directory wordlists found - skipping directory busting")
            self.error("💡 Configuration required:")
            self.error("  1. Set 'directory-wordlist' in global.toml with a valid path")
            self.error("  2. Example: directory-wordlist = '/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-small.txt'")
            self.error("  3. Or use --dirbuster.wordlist '/path/to/your/wordlist.txt'")
            return
        
        self.info(f"Starting directory busting with {len(valid_wordlists)} wordlist(s)")
        
        # Check if parallel wordlists is enabled
        if self.get_option("parallel-wordlists") and len(valid_wordlists) > 1:
            await self._run_parallel_wordlists(service, valid_wordlists, timeout_seconds, max_depth, dot_extensions)
        else:
            await self._run_sequential_wordlists(service, valid_wordlists, timeout_seconds, max_depth, dot_extensions)

    async def _run_sequential_wordlists(self, service, valid_wordlists, timeout_seconds, max_depth, dot_extensions):
        """Run wordlists sequentially (original behavior)"""
        for wordlist in valid_wordlists:
            name = os.path.splitext(os.path.basename(wordlist))[0]
            if self.get_option("tool") == "feroxbuster":
                cmd = (
                    "timeout " + str(timeout_seconds) + " feroxbuster -u {http_scheme}://{addressv6}:{port}/ -t "
                    + str(self.get_option("threads"))
                    + ' -w "'
                    + wordlist
                    + '" -x "'
                    + self.get_option("ext")
                    + '" -v -k '
                    + ("--depth " + str(max_depth) + " " if self.get_option("recursive") else "-n ")
                    + '--timeout ' + str(self.get_option("request_timeout")) + ' '
                    + '--rate-limit 300 '  # Prevent overwhelming HTB machines
                    + '--auto-bail '  # Stop if too many errors
                    + '-q -e -r -o "{scandir}/{protocol}_{port}_{http_scheme}_feroxbuster_'
                    + name
                    + '.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                )
                await service.execute(cmd)

            elif self.get_option("tool") == "gobuster":
                cmd = (
                    "timeout " + str(timeout_seconds) + " gobuster dir -u {http_scheme}://{addressv6}:{port}/ -t "
                    + str(self.get_option("threads"))
                    + ' -w "'
                    + wordlist
                    + '" -e -k -x "'
                    + self.get_option("ext")
                    + '" --timeout ' + str(self.get_option("request_timeout")) + 's '
                    + '--delay 200ms '  # Small delay to prevent overwhelming
                    + '-z -r -o "{scandir}/{protocol}_{port}_{http_scheme}_gobuster_'
                    + name
                    + '.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                )
                await service.execute(cmd)

            elif self.get_option("tool") == "dirsearch":
                if service.target.ipversion == "IPv6":
                    service.error("dirsearch does not support IPv6.")
                else:
                    cmd = (
                        "timeout " + str(timeout_seconds) + " dirsearch -u {http_scheme}://{address}:{port}/ -t "
                        + str(self.get_option("threads"))
                        + ' -e "'
                        + self.get_option("ext")
                        + '" -f -q -F '
                        + ("-r --max-recursion-depth=" + str(max_depth) + " " if self.get_option("recursive") else "")
                        + '-w "'
                        + wordlist
                        + '" --format=plain -o "{scandir}/{protocol}_{port}_{http_scheme}_dirsearch_'
                        + name
                        + '.txt"'
                        + (" " + self.get_option("extras") if self.get_option("extras") else "")
                    )
                    await service.execute(cmd)

            elif self.get_option("tool") == "ffuf":
                cmd = (
                    "timeout " + str(timeout_seconds) + " ffuf -u {http_scheme}://{addressv6}:{port}/FUZZ -t "
                    + str(self.get_option("threads"))
                    + ' -w "'
                    + wordlist
                    + '" -e "'
                    + dot_extensions
                    + '" -v -r '
                    + ("-recursion -recursion-depth " + str(max_depth) + " " if self.get_option("recursive") else "")
                    + "-noninteractive"
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                    + " | tee {scandir}/{protocol}_{port}_{http_scheme}_ffuf_"
                    + name
                    + ".txt"
                )
                await service.execute(cmd)

            elif self.get_option("tool") == "dirb":
                cmd = (
                    'timeout ' + str(timeout_seconds) + ' dirb {http_scheme}://{addressv6}:{port}/ "'
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
                await service.execute(cmd)

    def manual(self, service, plugin_was_run):
        dot_extensions = ",".join(["." + x for x in self.get_option("ext").split(",")])
        
        # Get configured wordlist path - use global setting if available
        global_wordlist = self.get_global("directory-wordlist")
        wordlist_path = global_wordlist if global_wordlist else "<specify-wordlist-path>"
        
        if self.get_option("tool") == "feroxbuster":
            service.add_manual_command(
                "(feroxbuster) Multi-threaded recursive directory/file enumeration for web servers using various wordlists:",
                [
                    "feroxbuster -u {http_scheme}://{addressv6}:{port} -t "
                    + str(self.get_option("threads"))
                    + ' -w "'
                    + wordlist_path
                    + '" -x "'
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
                    + ' -w "'
                    + wordlist_path
                    + '" -e -k -x "'
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
                        + '-w "'
                        + wordlist_path
                        + '" --format=plain --output="{scandir}/{protocol}_{port}_{http_scheme}_dirsearch_dirbuster.txt"'
                        + (" " + self.get_option("extras") if self.get_option("extras") else "")
                    ],
                )
        elif self.get_option("tool") == "ffuf":
            service.add_manual_command(
                "(ffuf) Multi-threaded recursive directory/file enumeration for web servers using various wordlists:",
                [
                    "ffuf -u {http_scheme}://{addressv6}:{port}/FUZZ -t "
                    + str(self.get_option("threads"))
                    + ' -w "'
                    + wordlist_path
                    + '" -e "'
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
                    "dirb {http_scheme}://{addressv6}:{port}/ \""
                    + wordlist_path
                    + "\" -l "
                    + ("" if self.get_option("recursive") else "-r ")
                    + '-X ",'
                    + dot_extensions
                    + '" -f -o "{scandir}/{protocol}_{port}_{http_scheme}_dirb_dirbuster.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                ],
            )

    async def _run_parallel_wordlists(self, service, valid_wordlists, timeout_seconds, max_depth, dot_extensions):
        """Run multiple wordlists in parallel"""
        import asyncio
        
        service.info(f"🔄 Running {len(valid_wordlists)} wordlists in parallel")
        
        # Create tasks for each wordlist
        tasks = []
        for wordlist in valid_wordlists:
            task = self._run_single_wordlist(service, wordlist, timeout_seconds, max_depth, dot_extensions)
            tasks.append(task)
        
        # Run all wordlists in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Report results
        successful = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service.error(f"Wordlist {valid_wordlists[i]} failed: {result}")
            else:
                successful += 1
        
        service.info(f"✅ Completed parallel directory busting - {successful}/{len(valid_wordlists)} wordlists successful")

    async def _run_single_wordlist(self, service, wordlist, timeout_seconds, max_depth, dot_extensions):
        """Run directory busting with a single wordlist"""
        name = os.path.splitext(os.path.basename(wordlist))[0]
        
        # Reduce timeout for parallel runs to prevent one wordlist from blocking others
        parallel_timeout = min(timeout_seconds // 3, 300)  # Max 5 minutes per wordlist in parallel mode
        
        if self.get_option("tool") == "feroxbuster":
            cmd = (
                "timeout " + str(parallel_timeout) + " feroxbuster -u {http_scheme}://{addressv6}:{port}/ -t "
                + str(self.get_option("threads"))
                + ' -w "'
                + wordlist
                + '" -x "'
                + self.get_option("ext")
                + '" -v -k '
                + ("--depth " + str(max_depth) + " " if self.get_option("recursive") else "-n ")
                + '--timeout ' + str(self.get_option("request_timeout")) + ' '
                + '--rate-limit 300 '  # Prevent overwhelming HTB machines
                + '--auto-bail '  # Stop if too many errors
                + '-q -e -r -o "{scandir}/{protocol}_{port}_{http_scheme}_feroxbuster_'
                + name
                + '.txt"'
                + (" " + self.get_option("extras") if self.get_option("extras") else "")
            )
            await service.execute(cmd)

        elif self.get_option("tool") == "gobuster":
            cmd = (
                "timeout " + str(parallel_timeout) + " gobuster dir -u {http_scheme}://{addressv6}:{port}/ -t "
                + str(self.get_option("threads"))
                + ' -w "'
                + wordlist
                + '" -e -k -x "'
                + self.get_option("ext")
                + '" --timeout ' + str(self.get_option("request_timeout")) + 's '
                + '--delay 200ms '  # Small delay to prevent overwhelming
                + '-z -r -o "{scandir}/{protocol}_{port}_{http_scheme}_gobuster_'
                + name
                + '.txt"'
                + (" " + self.get_option("extras") if self.get_option("extras") else "")
            )
            await service.execute(cmd)

        elif self.get_option("tool") == "dirsearch":
            if service.target.ipversion == "IPv6":
                service.error("dirsearch does not support IPv6.")
            else:
                cmd = (
                    "timeout " + str(parallel_timeout) + " dirsearch -u {http_scheme}://{address}:{port}/ -t "
                    + str(self.get_option("threads"))
                    + ' -e "'
                    + self.get_option("ext")
                    + '" -f -q -F '
                    + ("-r --max-recursion-depth=" + str(max_depth) + " " if self.get_option("recursive") else "")
                    + '-w "'
                    + wordlist
                    + '" --format=plain -o "{scandir}/{protocol}_{port}_{http_scheme}_dirsearch_'
                    + name
                    + '.txt"'
                    + (" " + self.get_option("extras") if self.get_option("extras") else "")
                )
                await service.execute(cmd)

        elif self.get_option("tool") == "ffuf":
            cmd = (
                "timeout " + str(parallel_timeout) + " ffuf -u {http_scheme}://{addressv6}:{port}/FUZZ -t "
                + str(self.get_option("threads"))
                + ' -w "'
                + wordlist
                + '" -e "'
                + dot_extensions
                + '" -v -r '
                + ("-recursion -recursion-depth " + str(max_depth) + " " if self.get_option("recursive") else "")
                + "-noninteractive"
                + (" " + self.get_option("extras") if self.get_option("extras") else "")
                + " | tee {scandir}/{protocol}_{port}_{http_scheme}_ffuf_"
                + name
                + ".txt"
            )
            await service.execute(cmd)

        elif self.get_option("tool") == "dirb":
            cmd = (
                'timeout ' + str(parallel_timeout) + ' dirb {http_scheme}://{addressv6}:{port}/ "'
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
            await service.execute(cmd)
