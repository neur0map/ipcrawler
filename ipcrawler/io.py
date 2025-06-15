import asyncio, colorama, os, re, string, sys, unidecode, time, math
from colorama import Fore, Style
from ipcrawler.config import config

# Rich support for enhanced verbosity output (required for new style)
try:
    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.align import Align

    RICH_AVAILABLE = True
    rich_console = Console()
except ImportError:
    RICH_AVAILABLE = False
    rich_console = None


def get_ipcrawler_ascii():
    """Generate creepy ASCII art for ipcrawler startup"""
    return """
    ██▓ ██▓███   ▄████▄   ██▀███   ▄▄▄       █     █░ ██▓    ▓█████  ██▀███  
   ▓██▒▓██░  ██▒▒██▀ ▀█  ▓██ ▒ ██▒▒████▄    ▓█░ █ ░█░▓██▒    ▓█   ▀ ▓██ ▒ ██▒
   ▒██▒▓██░ ██▓▒▒▓█    ▄ ▓██ ░▄█ ▒▒██  ▀█▄  ▒█░ █ ░█ ▒██░    ▒███   ▓██ ░▄█ ▒
   ░██░▒██▄█▓▒ ▒▒▓▓▄ ▄██▒▒██▀▀█▄  ░██▄▄▄▄██ ░█░ █ ░█ ▒██░    ▒▓█  ▄ ▒██▀▀█▄  
   ░██░▒██▒ ░  ░▒ ▓███▀ ░░██▓ ▒██▒ ▓█   ▓██▒░░██▒██▓ ░██████▒░▒████▒░██▓ ▒██▒
   ░▓  ▒▓▒░ ░  ░░ ░▒ ▒  ░░ ▒▓ ░▒▓░ ▒▒   ▓▒█░░ ▓░▒ ▒  ░ ░░▓  ░░░ ▒░ ░░ ▒▓ ░▒▓░
    ▒ ░░▒ ░       ░  ▒     ░▒ ░ ▒░  ▒   ▒▒ ░  ▒ ░ ░  ░ ░ ▒  ░ ░ ░  ░  ░▒ ░ ▒░
    ▒ ░░░       ░          ░░   ░   ░   ▒     ░   ░    ░ ░      ░     ░░   ░ 
    ░           ░ ░         ░           ░  ░    ░        ░  ░   ░  ░   ░     
                ░                                                            

    ⚡ Network Spider - Weaving Through Your Infrastructure ⚡
    """


def show_startup_banner(targets=None, version="2.1.0"):
    """Display feroxbuster-style startup banner"""
    from ipcrawler.config import config

    if not RICH_AVAILABLE or config["accessible"]:
        return

    rich_console.clear()

    # ASCII Art
    ascii_art = get_ipcrawler_ascii()
    rich_console.print(ascii_art, style="bold red")

    # Version and author info
    rich_console.print("By neur0map 🧠 - Inspired by AutoRecon", style="dim")
    rich_console.print(f"ver: {version}", style="dim")
    rich_console.print()

    # Configuration table
    config_table = get_config_display_table(targets)
    rich_console.print(config_table)
    rich_console.print()

    # Scan start message with better formatting
    rich_console.print("─" * 70, style="dim")
    rich_console.print("🚀 [bold green]STARTING RECONNAISSANCE[/bold green]", justify="center")
    rich_console.print("─" * 70, style="dim")
    rich_console.print()


def get_config_display_table(targets=None):
    """Generate configuration display table"""
    if not RICH_AVAILABLE:
        return None

    from ipcrawler.main import VERSION

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Setting", style="dim blue", width=20)
    table.add_column("Value", style="bright_white")

    # Get actual config values
    if targets and len(targets) > 0:
        if len(targets) == 1:
            target_display = targets[0].address
        else:
            target_display = f"{len(targets)} targets"
    else:
        target_display = "Not specified"

    # Build realistic config display from actual values
    configs = [
        ("🎯 Target Url", target_display),
        ("📊 Threads", str(config.get("max_scans", 50))),
        ("📝 Wordlist", "/usr/share/seclists/Discovery/Web-Content/common.txt"),
        ("⏱️  Timeout", f"{config.get('timeout')}m" if config.get("timeout") else "None"),
        ("🔧 Status Codes", "All Status Codes"),
        ("🔍 Timeout (secs)", "7"),
        ("👤 User-Agent", f"ipcrawler/{VERSION}"),
        ("💾 Config File", config.get("global_file", "/etc/ipcrawler/config.toml") or "/etc/ipcrawler/config.toml"),
        ("🔗 Extract Links", "true"),
        ("🌐 HTTP methods", "[GET]"),
        ("📋 Follow Redirects", "true"),
        ("🔄 Recursion Depth", "4"),
    ]

    for setting, value in configs:
        table.add_row(setting, value)

    return table


def slugify(name):
    return re.sub(r"[\W_]+", "-", unidecode.unidecode(name).lower()).strip("-")


def e(*args, frame_index=1, **kvargs):
    frame = sys._getframe(frame_index)

    vals = {}

    vals.update(frame.f_globals)
    vals.update(frame.f_locals)
    vals.update(kvargs)

    return string.Formatter().vformat(" ".join(args), args, vals)


def fformat(s):
    return e(s, frame_index=3)


def cprint(
    *args, color=Fore.RESET, char="*", sep=" ", end="\n", frame_index=1, file=sys.stdout, printmsg=True, verbosity=0, **kvargs
):
    if printmsg and verbosity > config["verbose"]:
        return ""
    frame = sys._getframe(frame_index)

    vals = {
        "bgreen": Fore.GREEN + Style.BRIGHT,
        "bred": Fore.RED + Style.BRIGHT,
        "bblue": Fore.BLUE + Style.BRIGHT,
        "byellow": Fore.YELLOW + Style.BRIGHT,
        "bmagenta": Fore.MAGENTA + Style.BRIGHT,
        "green": Fore.GREEN,
        "red": Fore.RED,
        "blue": Fore.BLUE,
        "yellow": Fore.YELLOW,
        "magenta": Fore.MAGENTA,
        "bright": Style.BRIGHT,
        "srst": Style.NORMAL,
        "crst": Fore.RESET,
        "rst": Style.NORMAL + Fore.RESET,
    }

    if config["accessible"]:
        vals = {
            "bgreen": "",
            "bred": "",
            "bblue": "",
            "byellow": "",
            "bmagenta": "",
            "green": "",
            "red": "",
            "blue": "",
            "yellow": "",
            "magenta": "",
            "bright": "",
            "srst": "",
            "crst": "",
            "rst": "",
        }

    vals.update(frame.f_globals)
    vals.update(frame.f_locals)
    vals.update(kvargs)

    unfmt = ""
    if char is not None and not config["accessible"]:
        unfmt += color + "[" + Style.BRIGHT + char + Style.NORMAL + "]" + Fore.RESET + sep
    unfmt += sep.join(args)

    fmted = unfmt

    for attempt in range(10):
        try:
            fmted = string.Formatter().vformat(unfmt, args, vals)
            break
        except KeyError as err:
            key = err.args[0]
            unfmt = unfmt.replace("{" + key + "}", "{{" + key + "}}")

    if printmsg:
        print(fmted, sep=sep, end=end, file=file)
    else:
        return fmted


def debug(*args, color=Fore.GREEN, sep=" ", end="\n", file=sys.stdout, **kvargs):
    from ipcrawler.config import config

    if config["verbose"] >= 2:
        if config["accessible"]:
            args = ("Debug:",) + args
        if RICH_AVAILABLE and not config["accessible"]:
            # Enhanced debug output
            debug_text = Text.assemble(("🐛 DEBUG", "bold green"), " ", (" ".join(str(arg) for arg in args), "dim green"))
            rich_console.print(debug_text)
        else:
            cprint(*args, color=color, char="-", sep=sep, end=end, file=file, frame_index=2, **kvargs)


def info(*args, sep=" ", end="\n", file=sys.stdout, **kvargs):
    # Import config fresh each time to avoid import-time initialization issues
    from ipcrawler.config import config
    import re  # Import re at function level to avoid UnboundLocalError

    if RICH_AVAILABLE and not config["accessible"]:
        message = sep.join(str(arg) for arg in args)

        # Always enhance plugin messages regardless of verbosity
        if "running against" in message and ("Port scan" in message or "Service scan" in message):
            # Extract plugin info
            if "Port scan" in message:
                scan_type = "🔍 PORT"
                color = "blue"
            else:
                scan_type = "🔧 SERVICE"
                color = "green"

            # Parse the message for plugin name and target
            plugin_match = re.search(r"(Port scan|Service scan) ([^{]+?) \(([^)]+)\)", message)
            target_match = re.search(
                r"against ([^{]+?)$", message.replace("{rst}", "").replace("{byellow}", "").replace("{rst}", "")
            )

            if plugin_match and target_match:
                plugin_name = plugin_match.group(2).strip()
                plugin_slug = plugin_match.group(3).strip()
                target = target_match.group(1).strip()

                # Feroxbuster-style output
                status_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    (f"{scan_type:12}", f"bold {color}"),
                    " ",
                    (f"{plugin_name} ", "cyan"),
                    (f"({plugin_slug}) ", "dim"),
                    ("→ ", "bold white"),
                    (f"{target}", "yellow"),
                )
                rich_console.print(status_text)
                return

        # Enhanced discovery messages
        elif "Discovered open port" in message or "Identified service" in message:
            if "Discovered open port" in message:
                port_match = re.search(
                    r"Discovered open port ([^{]+?) on ([^{]+?)$",
                    message.replace("{rst}", "").replace("{bmagenta}", "").replace("{byellow}", ""),
                )
                if port_match:
                    port = port_match.group(1).strip()
                    target = port_match.group(2).strip()

                    # Feroxbuster-style discovery
                    discovery_text = Text.assemble(
                        ("GET", "bold blue"),
                        "    ",
                        ("200", "bold green"),
                        "    ",
                        (f"{port:12}", "cyan"),
                        " ",
                        ("OPEN", "bold green"),
                        " ",
                        (f"{target}", "yellow"),
                    )
                    rich_console.print(discovery_text)
                    return
            elif "Identified service" in message:
                service_match = re.search(
                    r"Identified service ([^{]+?) on ([^{]+?) on ([^{]+?)$",
                    message.replace("{rst}", "").replace("{bmagenta}", "").replace("{byellow}", ""),
                )
                if service_match:
                    service = service_match.group(1).strip()
                    port = service_match.group(2).strip()
                    target = service_match.group(3).strip()

                    # Feroxbuster-style service discovery
                    service_text = Text.assemble(
                        ("GET", "bold blue"),
                        "    ",
                        ("200", "bold green"),
                        "    ",
                        (f"{port:12}", "cyan"),
                        " ",
                        (f"{service:15}", "bold magenta"),
                        " ",
                        (f"{target}", "yellow"),
                    )
                    rich_console.print(service_text)
                    return

        # Enhanced completion messages
        elif "finished in" in message and ("Port scan" in message or "Service scan" in message):
            plugin_match = re.search(r"(Port scan|Service scan) ([^{]+?) \(([^)]+)\)", message)
            target_match = re.search(
                r"against ([^{]+?) finished in (.+)$", message.replace("{rst}", "").replace("{byellow}", "")
            )

            if plugin_match and target_match:
                scan_type = "✅ COMPLETED" if "Port scan" in message else "✅ FINISHED"
                plugin_name = plugin_match.group(2).strip()
                plugin_slug = plugin_match.group(3).strip()
                target = target_match.group(1).strip()
                timing = target_match.group(2).strip()

                completion_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    (f"{scan_type:12}", "bold green"),
                    " ",
                    (f"{plugin_name} ", "cyan"),
                    (f"({plugin_slug}) ", "dim"),
                    ("on ", "dim"),
                    (f"{target} ", "yellow"),
                    ("in ", "dim"),
                    (f"{timing}", "blue"),
                )
                rich_console.print(completion_text)
                return

        # Enhanced general scanning messages
        elif "Scanning target" in message:
            # Clean up color codes first
            clean_message = message.replace("{byellow}", "").replace("{rst}", "")
            target_match = re.search(r"Scanning target ([^\s]+)", clean_message)
            if target_match:
                target = target_match.group(1).strip()
                scan_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    ("🎯 SCANNING", "bold cyan"),
                    "  ",
                    ("Target: ", "dim"),
                    (f"{target}", "yellow"),
                )
                rich_console.print(scan_text)
                return

        # Enhanced finished scanning messages
        elif "Finished scanning target" in message:
            # Clean up all color codes
            clean_message = message.replace("{bright}", "").replace("{rst}", "").replace("{byellow}", "")
            target_match = re.search(r"Finished scanning target ([^\s]+) in (.+)$", clean_message)
            if target_match:
                target = target_match.group(1).strip()
                timing = target_match.group(2).strip()
                finish_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    ("🎉 COMPLETE", "bold green"),
                    "  ",
                    ("Target: ", "dim"),
                    (f"{target} ", "yellow"),
                    ("in ", "dim"),
                    (f"{timing}", "blue"),
                )
                rich_console.print(finish_text)
                return

        # Enhanced pattern match messages
        elif "Matched Pattern:" in message or "pattern" in message.lower():
            pattern_text = Text.assemble(
                ("GET", "bold blue"),
                "    ",
                ("200", "bold green"),
                "    ",
                ("🔍 PATTERN", "bold magenta"),
                " ",
                # Extract the actual pattern content
                (
                    message.replace("{rst}", "")
                    .replace("{bmagenta}", "")
                    .replace("{bright}", "")
                    .replace("{yellow}", "")
                    .replace("{crst}", "")
                    .replace("{bgreen}", ""),
                    "cyan",
                ),
            )
            rich_console.print(pattern_text)
            return

        # Enhanced VHost messages
        elif "VHost discovered:" in message or "vhost" in message.lower():
            clean_message = (
                message.replace("{rst}", "")
                .replace("{bmagenta}", "")
                .replace("{bright}", "")
                .replace("{yellow}", "")
                .replace("{crst}", "")
                .replace("{bgreen}", "")
                .replace("{byellow}", "")
            )

            # Extract VHost information
            vhost_match = re.search(r"VHost discovered:\s*([^\s]+)", clean_message)
            if vhost_match:
                vhost = vhost_match.group(1).strip()
                vhost_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    ("🌐 VHOST", "bold cyan"),
                    "     ",
                    ("discovered: ", "dim"),
                    (f"{vhost}", "bold yellow"),
                )
            else:
                vhost_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    ("🌐 VHOST", "bold cyan"),
                    "     ",
                    (clean_message, "cyan"),
                )
            rich_console.print(vhost_text)
            return

        # Handle verbosity-specific messages
        if "verbosity" in kvargs:
            verbosity_level = kvargs["verbosity"]
            if config["verbose"] < verbosity_level:
                return  # Don't show if verbosity is too low

        # DEFAULT: Convert ALL remaining messages to feroxbuster style
        # Clean up all color codes
        clean_message = message
        for old_code in [
            "{rst}",
            "{bright}",
            "{byellow}",
            "{bmagenta}",
            "{bgreen}",
            "{crst}",
            "{yellow}",
            "{green}",
            "{blue}",
            "{red}",
            "{cyan}",
            "{magenta}",
            "{bblue}",
            "{bred}",
            "{bcyan}",
        ]:
            clean_message = clean_message.replace(old_code, "")

        # Determine message type and icon
        if "[" in clean_message and "]" in clean_message:
            # Extract the bracketed part for target/tag info
            bracket_match = re.search(r"\[([^\]]+)\]", clean_message)
            if bracket_match:
                bracket_content = bracket_match.group(1)
                remaining_message = clean_message.replace(f"[{bracket_content}]", "").strip()

                default_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    ("📡 INFO", "bold cyan"),
                    "      ",
                    (f"[{bracket_content}] ", "dim yellow"),
                    (remaining_message, "white"),
                )
            else:
                default_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    ("📡 INFO", "bold cyan"),
                    "      ",
                    (clean_message, "white"),
                )
        else:
            default_text = Text.assemble(
                ("GET", "bold blue"),
                "    ",
                ("200", "bold green"),
                "    ",
                ("📡 INFO", "bold cyan"),
                "      ",
                (clean_message, "white"),
            )

        rich_console.print(default_text)
        return

    # Only use old style if Rich is not available
    cprint(*args, color=Fore.BLUE, char="*", sep=sep, end=end, file=file, frame_index=2, **kvargs)


def warn(*args, sep=" ", end="\n", file=sys.stderr, **kvargs):
    if config["accessible"]:
        args = ("Warning:",) + args
    if RICH_AVAILABLE and not config["accessible"]:
        # Format the message properly before displaying
        message = cprint(
            *args, color=Fore.YELLOW, char="!", sep=sep, end="", file=file, frame_index=2, printmsg=False, **kvargs
        )
        if message:
            # Clean up color codes for Rich display
            clean_message = message.replace("{byellow}", "").replace("{rst}", "").replace("{bright}", "").replace("{crst}", "")
            warning_text = Text.assemble(("⚠️  WARN", "bold yellow"), " ", (clean_message, "yellow"))
            rich_console.print(warning_text)
        else:
            # Fallback to standard warning
            cprint(*args, color=Fore.YELLOW, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)
    else:
        cprint(*args, color=Fore.YELLOW, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)


def error(*args, sep=" ", end="\n", file=sys.stderr, **kvargs):
    if config["accessible"]:
        args = ("Error:",) + args
    if RICH_AVAILABLE and not config["accessible"]:
        # Format the message properly before displaying
        message = cprint(*args, color=Fore.RED, char="!", sep=sep, end="", file=file, frame_index=2, printmsg=False, **kvargs)
        if message:
            # Clean up color codes for Rich display
            clean_message = message.replace("{bright}", "").replace("{bgreen}", "").replace("{crst}", "").replace("{rst}", "")
            error_text = Text.assemble(("🚨 ERROR", "bold red"), " ", (clean_message, "red"))
            rich_console.print(error_text)
        else:
            # Fallback to standard error
            cprint(*args, color=Fore.RED, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)
    else:
        cprint(*args, color=Fore.RED, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)


def fail(*args, sep=" ", end="\n", file=sys.stderr, **kvargs):
    if config["accessible"]:
        args = ("Failure:",) + args
    if RICH_AVAILABLE and not config["accessible"]:
        fail_text = Text.assemble(("💀 FATAL", "bold red"), " ", (" ".join(str(arg) for arg in args), "red"))
        rich_console.print(fail_text)
    else:
        cprint(*args, color=Fore.RED, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)
    exit(-1)


def show_scan_summary(target_count, total_time, findings_count=0):
    """Display feroxbuster-style scan completion summary"""
    if not RICH_AVAILABLE or config["accessible"]:
        info(f"Scan completed! {target_count} targets scanned in {total_time}")
        return

    summary_panel = Panel.fit(
        Text.assemble(
            ("🎉 SCAN COMPLETED", "bold green"),
            "\n\n",
            ("📊 Statistics:", "bold"),
            "\n",
            ("  • Targets Scanned: ", "dim"),
            (str(target_count), "cyan"),
            "\n",
            ("  • Total Time: ", "dim"),
            (total_time, "cyan"),
            "\n",
            ("  • Findings: ", "dim"),
            (str(findings_count), "red" if findings_count > 0 else "green"),
            "\n\n",
            ("📁 Results saved to: ", "dim"),
            ("./results/", "yellow"),
            "\n",
            ("📋 Check _manual_commands.txt for additional tests!", "bold blue"),
        ),
        title="[bold green]Scan Complete[/bold green]",
        border_style="green",
    )

    rich_console.print(summary_panel)


class ProgressManager:
    def __init__(self):
        self.active = False
        self.tasks = {}
        self.task_keys = {}  # Track existing progress bars by unique key
        self.progress = None
        self.live = None

    def start(self):
        """Start the progress manager"""
        debug(
            f"ProgressManager.start() called - RICH_AVAILABLE: {RICH_AVAILABLE}, accessible: {config.get('accessible', False)}",
            verbosity=3,
        )

        if RICH_AVAILABLE and not config.get("accessible", False):
            # Use modern Rich progress bars with live updates
            self.progress = Progress(
                SpinnerColumn(spinner_name="dots", style="cyan", speed=1.0),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40, style="cyan", complete_style="green"),
                TaskProgressColumn(style="bold magenta"),
                TimeElapsedColumn(),
                console=rich_console,
                transient=True,  # Progress bars disappear when complete
            )
            self.live = Live(self.progress, console=rich_console, refresh_per_second=10)
            self.live.start()
            self.active = True
            debug("Progress manager started successfully (Rich mode)", verbosity=3)
        else:
            # Fallback to simple text-based progress
            self.active = True
            debug("Progress manager started successfully (text mode)", verbosity=3)

    def add_task(self, description, total=100, task_key=None):
        """Add a new progress task, or reuse existing one if task_key matches"""
        debug(f"add_task called: {description}, active: {self.active}, task_key: {task_key}", verbosity=3)
        if not self.active:
            debug("Progress manager not active, returning None", verbosity=3)
            return None

        # Check if we already have a task with this key
        if task_key and task_key in self.task_keys:
            existing_task_id = self.task_keys[task_key]
            debug(f"🔄 Reusing existing progress bar {existing_task_id} for {task_key}", verbosity=2)
            return existing_task_id

        if self.progress:
            # Use Rich progress bar
            task_id = self.progress.add_task(description, total=total)
            self.tasks[task_id] = {
                "description": description,
                "started": time.time(),
                "total": total,
                "completed": 0,
                "last_update": time.time(),
                "rich_task": True,
                "task_key": task_key,
            }
            # Store the mapping if we have a key
            if task_key:
                self.task_keys[task_key] = task_id
            debug(f"Rich task {task_id} created: {description}", verbosity=3)
        else:
            # Fallback to simple tracking
            task_id = len(self.tasks) + 1
            self.tasks[task_id] = {
                "description": description,
                "started": time.time(),
                "total": total,
                "completed": 0,
                "last_update": time.time(),
                "rich_task": False,
                "task_key": task_key,
            }
            # Store the mapping if we have a key
            if task_key:
                self.task_keys[task_key] = task_id
            info(f"🚀 Started: {description}", verbosity=2)
            debug(f"Text task {task_id} created: {description}", verbosity=3)

        return task_id

    def update_task(self, task_id, advance=1):
        """Update progress on a task"""
        if not self.active or task_id is None or task_id not in self.tasks:
            return

        self.tasks[task_id]["completed"] += advance
        self.tasks[task_id]["last_update"] = time.time()

        if self.tasks[task_id].get("rich_task", False) and self.progress:
            # Update Rich progress bar
            self.progress.update(task_id, advance=advance)
        else:
            # Show text progress update occasionally
            if self.tasks[task_id]["completed"] % 20 == 0:  # Every 20%
                progress_percent = min(100, self.tasks[task_id]["completed"])
                info(f"⏳ Progress: {self.tasks[task_id]['description']} - {progress_percent:.0f}%", verbosity=2)

    def complete_task(self, task_id):
        """Complete a task and schedule its removal"""
        if not self.active or task_id is None or task_id not in self.tasks:
            return

        task = self.tasks[task_id]

        # Check if task was already completed
        if task.get("completed_flag", False):
            debug(f"Task {task_id} already completed, skipping", verbosity=3)
            return

        # Mark as completed to prevent duplicate completion
        task["completed_flag"] = True
        elapsed = time.time() - task["started"]

        if task.get("rich_task", False) and self.progress:
            # Complete Rich progress bar
            self.progress.update(task_id, completed=task["total"])
            # Let Rich handle the completion display
        else:
            # Show text completion message
            info(f"✅ Completed: {task['description']} (took {elapsed:.1f}s)", verbosity=2)

        # Schedule removal
        asyncio.create_task(self._remove_task_after_delay(task_id))

    async def _remove_task_after_delay(self, task_id, delay=2):
        """Remove completed task after delay"""
        await asyncio.sleep(delay)
        if self.active and task_id in self.tasks:
            task = self.tasks[task_id]

            # Remove from Rich progress if it's a Rich task
            if task.get("rich_task", False) and self.progress:
                try:
                    self.progress.remove_task(task_id)
                except:
                    pass  # Task might already be removed

            # Remove from task_keys mapping if it has a key
            task_key = task.get("task_key")
            if task_key and task_key in self.task_keys:
                del self.task_keys[task_key]

            # Remove from our internal tracking
            del self.tasks[task_id]

    def simulate_progress(self, task_id, duration=10):
        """Simulate progress for long-running tasks"""
        if not self.active or task_id is None or task_id not in self.tasks:
            return

        # Update progress gradually during the scan
        asyncio.create_task(self._progress_updater(task_id, duration))

    async def _progress_updater(self, task_id, duration):
        """Gradually update progress over duration"""
        if not self.active or task_id not in self.tasks:
            return

        start_time = time.time()
        update_count = 0
        last_progress_report = 0
        task = self.tasks[task_id]

        while self.active:
            try:
                # Check if task still exists before accessing it
                if task_id not in self.tasks:
                    break

                elapsed = time.time() - start_time

                # More realistic progress curve that approaches 100% asymptotically
                if elapsed < duration:
                    # Normal progress up to 90% within estimated duration
                    progress_percent = min(90, (elapsed / duration) * 90)
                else:
                    # After estimated duration, slowly approach 95-98% but never 100%
                    overtime = elapsed - duration
                    # Asymptotic approach: starts at 90%, slowly approaches 98%
                    progress_percent = 90 + (8 * (1 - math.exp(-overtime / 60)))  # 60s time constant

                if task.get("rich_task", False) and self.progress:
                    # Update Rich progress bar
                    progress_value = (progress_percent / 100) * task["total"]
                    self.progress.update(task_id, completed=progress_value)
                else:
                    # Update our internal tracking for text mode
                    self.tasks[task_id]["completed"] = progress_percent
                    self.tasks[task_id]["last_update"] = time.time()

                    # Show progress updates every 30% or so
                    if progress_percent - last_progress_report >= 30:
                        info(f"⏳ Progress: {self.tasks[task_id]['description']} - {progress_percent:.0f}%", verbosity=2)
                        last_progress_report = progress_percent
                        update_count += 1

            except Exception as e:
                debug(f"Progress updater error for task {task_id}: {e}", verbosity=3)
                break

            await asyncio.sleep(1.0)  # Update every second

    def stop(self):
        """Stop the progress manager"""
        if self.active:
            self.active = False

            # Stop Rich live display
            if self.live:
                self.live.stop()
                self.live = None

            # Clear progress, tasks, and task keys
            self.progress = None
            self.tasks.clear()
            self.task_keys.clear()
            debug("Progress manager stopped", verbosity=3)


# Global progress manager instance
progress_manager = ProgressManager()


# VHost Auto-Discovery System
class VHostManager:
    def __init__(self):
        self.auto_add_enabled = False
        self.discovered_hosts = set()
        self.backup_created = False

    def check_auto_add_conditions(self):
        """Check if we should auto-add vhosts to /etc/hosts"""
        import os
        import subprocess

        # First check config file setting - if disabled, skip auto-add and use post-scan prompts
        vhost_config = config.get("vhost_discovery", {})
        if not vhost_config.get("auto_add_hosts", True):
            debug("Auto VHost: Disabled in config.toml - will use post-scan interactive prompts", verbosity=2)
            self.auto_add_enabled = False
            return False

        # Check if we're root or have sudo access
        if os.geteuid() == 0:
            self.auto_add_enabled = True
            debug("Auto VHost: Running as root - enabling auto-add", verbosity=2)
            return True

        # Check sudo access
        try:
            result = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=2)
            if result.returncode == 0:
                self.auto_add_enabled = True
                debug("Auto VHost: Sudo access detected - enabling auto-add", verbosity=2)
                return True
        except:
            pass

        # Check for HTB indicators
        try:
            with open("/etc/hosts", "r") as f:
                hosts_content = f.read().lower()
                if any(indicator in hosts_content for indicator in ["htb", "hackthebox", ".htb", "machine"]):
                    # Try sudo for HTB scenarios
                    try:
                        result = subprocess.run(["sudo", "-v"], capture_output=True, timeout=5)
                        if result.returncode == 0:
                            self.auto_add_enabled = True
                            info("🎯 HTB environment detected - enabling auto VHost discovery!", verbosity=1)
                            return True
                    except:
                        pass
        except:
            pass

        debug("Auto VHost: Conditions not met - manual mode only", verbosity=2)
        return False

    def create_backup(self):
        """Create backup of /etc/hosts"""
        if self.backup_created:
            return True

        import shutil
        import subprocess
        import os
        from datetime import datetime

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"/etc/hosts.ipcrawler.backup.{timestamp}"

            if os.geteuid() == 0:
                shutil.copy2("/etc/hosts", backup_path)
            else:
                subprocess.run(["sudo", "cp", "/etc/hosts", backup_path], check=True, timeout=10)

            info(f"📋 Created /etc/hosts backup: {backup_path}", verbosity=2)
            self.backup_created = True
            return True
        except Exception as e:
            warn(f"⚠️  Could not create hosts backup: {e}", verbosity=1)
            return False

    def add_vhost_entry(self, ip, hostname):
        """Add a single vhost entry to /etc/hosts"""
        if not self.auto_add_enabled:
            return False

        # Avoid duplicates
        host_key = f"{ip}:{hostname}"
        if host_key in self.discovered_hosts:
            return True

        # Create backup on first addition
        if not self.backup_created:
            if not self.create_backup():
                return False

        try:
            import subprocess
            import os
            from datetime import datetime

            # Check if entry already exists
            try:
                with open("/etc/hosts", "r") as f:
                    content = f.read()
                    if hostname in content:
                        debug(f"VHost {hostname} already in hosts file", verbosity=2)
                        self.discovered_hosts.add(host_key)
                        return True
            except:
                pass

            # Add the entry
            entry = f"\n# Added by ipcrawler - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{ip} {hostname}\n"

            if os.geteuid() == 0:
                with open("/etc/hosts", "a") as f:
                    f.write(entry)
            else:
                process = subprocess.Popen(
                    ["sudo", "tee", "-a", "/etc/hosts"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                process.communicate(input=entry)

                if process.returncode != 0:
                    return False

            self.discovered_hosts.add(host_key)
            info(f"✅ Auto-added to /etc/hosts: {ip} {hostname}", verbosity=1)

            # Also show in Rich if available
            if RICH_AVAILABLE and not config.get("accessible", False):
                from rich.text import Text

                vhost_text = Text.assemble(
                    ("GET", "bold blue"),
                    "    ",
                    ("200", "bold green"),
                    "    ",
                    ("🌐 VHOST ADDED", "bold magenta"),
                    " ",
                    (f"{hostname}", "cyan"),
                    (" → ", "dim"),
                    (f"{ip}", "yellow"),
                )
                rich_console.print(vhost_text)

            return True

        except Exception as e:
            warn(f"❌ Failed to add VHost {hostname}: {e}", verbosity=1)
            return False

    def suggest_manual_add(self, ip, hostname):
        """Suggest manual command for adding vhost"""
        manual_cmd = f'echo "{ip} {hostname}" | sudo tee -a /etc/hosts'
        info(f"💡 Manual VHost add: {manual_cmd}", verbosity=1)


# Global VHost manager instance
vhost_manager = VHostManager()


class CommandStreamReader(object):
    def __init__(self, stream, target, tag, patterns=None, outfile=None):
        self.stream = stream
        self.target = target
        self.tag = tag
        self.lines = []
        self.patterns = patterns or []
        self.outfile = outfile
        self.ended = False

        # Empty files that already exist.
        if self.outfile != None:
            with open(self.outfile, "w"):
                pass

    # Read lines from the stream until it ends.
    async def _read(self):
        # Handle None stream (dummy process)
        if self.stream is None:
            self.ended = True
            return
            
        while True:
            if self.stream.at_eof():
                break
            try:
                # Add timeout to readline to prevent hanging
                line_bytes = await asyncio.wait_for(self.stream.readline(), timeout=30)
                line = line_bytes.decode("utf8").rstrip()
            except asyncio.TimeoutError:
                warn(f"Stream readline timeout for {self.target.address}/{self.tag}", verbosity=2)
                break
            except ValueError:
                error(
                    "{bright}[{yellow}"
                    + self.target.address
                    + "{crst}/{bgreen}"
                    + self.tag
                    + "{crst}]{rst} A line was longer than 64 KiB and cannot be processed. Ignoring."
                )
                continue
            except Exception as e:
                warn(f"Stream read error for {self.target.address}/{self.tag}: {e}", verbosity=2)
                break

            if line != "":
                # For verbosity 3, enhance with feroxbuster-style output
                if RICH_AVAILABLE and config["verbose"] >= 3 and not config["accessible"]:
                    # Feroxbuster-style live output
                    live_text = Text.assemble(
                        ("│", "dim blue"),
                        (" ", ""),
                        (f"[{self.target.address}/{self.tag}]", "dim"),
                        (" ", ""),
                        (line.strip(), "white"),
                    )
                    rich_console.print(live_text)
                else:
                    info(
                        "{bright}[{yellow}"
                        + self.target.address
                        + "{crst}/{bgreen}"
                        + self.tag
                        + "{crst}]{rst} "
                        + line.strip().replace("{", "{{").replace("}", "}}"),
                        verbosity=3,
                    )

            # Check lines for pattern matches.
            for p in self.patterns:
                description = ""

                # Match and replace entire pattern.
                match = p.pattern.search(line)
                if match:
                    if p.description:
                        description = p.description.replace("{match}", line[match.start() : match.end()])

                        # Match and replace substrings.
                        matches = p.pattern.findall(line)
                        if len(matches) > 0 and isinstance(matches[0], tuple):
                            matches = list(matches[0])

                        match_count = 1
                        for match in matches:
                            if p.description:
                                description = description.replace("{match" + str(match_count) + "}", match)
                            match_count += 1

                        async with self.target.lock:
                            with open(os.path.join(self.target.scandir, "_patterns.log"), "a") as file:
                                if RICH_AVAILABLE and not config["accessible"]:
                                    # Feroxbuster-style pattern match
                                    pattern_text = Text.assemble(
                                        ("GET", "bold blue"),
                                        "    ",
                                        ("200", "bold green"),
                                        "    ",
                                        ("🔍 PATTERN", "bold magenta"),
                                        " ",
                                        (description, "cyan"),
                                    )
                                    rich_console.print(pattern_text)
                                else:
                                    info(
                                        "{bright}[{yellow}"
                                        + self.target.address
                                        + "{crst}/{bgreen}"
                                        + self.tag
                                        + "{crst}]{rst} {bmagenta}"
                                        + description
                                        + "{rst}",
                                        verbosity=2,
                                    )
                                file.writelines(description + "\n\n")
                    else:
                        pattern_match = line[match.start() : match.end()]
                        if RICH_AVAILABLE and not config["accessible"]:
                            # Feroxbuster-style pattern match
                            pattern_text = Text.assemble(
                                ("GET", "bold blue"),
                                "    ",
                                ("200", "bold green"),
                                "    ",
                                ("🔍 PATTERN", "bold magenta"),
                                " ",
                                (f"Matched: {pattern_match}", "cyan"),
                            )
                            rich_console.print(pattern_text)
                        else:
                            info(
                                "{bright}[{yellow}"
                                + self.target.address
                                + "{crst}/{bgreen}"
                                + self.tag
                                + "{crst}]{rst} {bmagenta}Matched Pattern: "
                                + pattern_match
                                + "{rst}",
                                verbosity=2,
                            )
                        async with self.target.lock:
                            with open(os.path.join(self.target.scandir, "_patterns.log"), "a") as file:
                                file.writelines("Matched Pattern: " + pattern_match + "\n\n")

            if self.outfile is not None:
                with open(self.outfile, "a") as writer:
                    writer.write(line + "\n")
            self.lines.append(line)
        self.ended = True

    # Read a line from the stream cache.
    async def readline(self):
        while True:
            try:
                return self.lines.pop(0)
            except IndexError:
                if self.ended:
                    return None
                else:
                    await asyncio.sleep(0.1)

    # Read all lines from the stream cache.
    async def readlines(self):
        lines = []
        while True:
            line = await self.readline()
            if line is not None:
                lines.append(line)
            else:
                break
        return lines
