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
    # Create a single main console for regular output
    rich_console = Console(stderr=False, force_terminal=True)
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

    🕷️ SPIDER CRAWLER - Weaving Through Digital Networks 🕸️
    ┌─ Stealthy ─ Fast ─ Comprehensive ──────────────────────┐
    │        "Every network has its vulnerabilities..."        │
    └──────────────────────────────────────────────────────────┘
    """


def show_startup_banner(targets=None, version="2.2.0"):
    """Display spider-themed startup banner"""
    from ipcrawler.config import config

    if not RICH_AVAILABLE or config["accessible"]:
        return

    rich_console.clear()

    # ASCII Art with spider theme
    ascii_art = get_ipcrawler_ascii()
    get_console().print(ascii_art, style="bold cyan")

    # Version and author info with spider theme
    get_console().print("🕸️ Web Weaver: neur0map 🧠 | Inspired by AutoRecon", style="dim green")
    get_console().print(f"🔧 Version: {version} | Ready to crawl...", style="dim")
    get_console().print()

    # Configuration table with spider styling
    config_table = get_config_display_table(targets)
    get_console().print(config_table)
    get_console().print()

    # Scan start message with spider theme
    get_console().print("━" * 70, style="dim cyan")
    get_console().print("🕷️ [bold green]SPIDER DEPLOYMENT INITIATED[/bold green] 🕷️", justify="center")
    get_console().print("━" * 70, style="dim cyan")
    get_console().print("🌐 [dim]Weaving through target infrastructure...[/dim]", justify="center")
    get_console().print()


def get_wordlist_status_summary(global_config):
    """Check status of all required wordlists"""
    wordlists = {
        "directory-wordlist": "Directory Scanning",
        "username-wordlist": "Bruteforce (Users)",
        "password-wordlist": "Bruteforce (Passwords)",
        "vhost-wordlist": "VHost Discovery",
        "subdomain-wordlist": "Subdomain Enum",
        "lfi-parameter-wordlist": "LFI Parameters", 
        "lfi-payload-wordlist": "LFI Payloads"
    }
    
    configured_count = 0
    # Don't count as missing since wordlists may exist on target machine
    # missing_count = 0
    
    for key, desc in wordlists.items():
        path = global_config.get("global", {}).get(key)
        if path:
            configured_count += 1
            # Don't check local file existence for global config wordlists
            # if not os.path.isfile(path):
            #     missing_count += 1
    
    if configured_count == 0:
        return "None configured"
    else:
        return f"{configured_count}/{len(wordlists)} configured ✓"


def get_config_display_table(targets=None):
    """Generate configuration display table"""
    if not RICH_AVAILABLE:
        return None

    from ipcrawler.main import VERSION
    import os
    import toml

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

    # Read TOML files directly (no caching)
    try:
        # Find config files
        config_dir = os.path.dirname(os.path.abspath(__file__))
        global_toml_path = os.path.join(config_dir, "global.toml")
        config_toml_path = os.path.join(config_dir, "config.toml")
        
        # Read global.toml directly
        global_config = {}
        if os.path.exists(global_toml_path):
            with open(global_toml_path, 'r') as f:
                global_config = toml.load(f)
        
        # Read config.toml directly  
        local_config = {}
        if os.path.exists(config_toml_path):
            with open(config_toml_path, 'r') as f:
                local_config = toml.load(f)
        
        # Get directory wordlist (show configured wordlist, no fallbacks)
        configured_wordlist = global_config.get("global", {}).get("directory-wordlist")
        
        # Show the configured wordlist (shortened if too long)
        if configured_wordlist:
            if len(configured_wordlist) > 50:
                directory_wordlist = "..." + configured_wordlist[-47:]
            else:
                directory_wordlist = os.path.basename(configured_wordlist)
            
            # For global config wordlists, don't show (missing) since they may exist on target machine
            # Only show (missing) if this is a critical local validation issue
            # if not os.path.isfile(configured_wordlist):
            #     directory_wordlist += " (missing)"
        else:
            directory_wordlist = "Not configured"
        
        # Get other settings from TOML files
        dirbuster_config = local_config.get("dirbuster", {})
        threads = dirbuster_config.get("threads", 15)
        timeout_minutes = local_config.get("timeout", "None")
        if timeout_minutes != "None":
            timeout_minutes = f"{timeout_minutes}m"
        
        recursion_depth = dirbuster_config.get("max_depth", 4)
        
        # Get more dynamic settings from TOML
        dirbuster_timeout_secs = dirbuster_config.get("timeout", 600) // 60  # Convert to minutes for display
        
        # Get HTTP method settings (check if POST scanning is enabled)
        http_methods = "[GET]"  # Default
        post_scanning = dirbuster_config.get("enable-post-scanning", False)
        if post_scanning:
            http_methods = "[GET, POST]"
        
        # Get status codes setting
        status_codes = "All Status Codes"  # Default
        if "status-codes" in dirbuster_config:
            status_codes = f"[{dirbuster_config['status-codes']}]"
        
        # Get extract links setting
        extract_links = "true"  # Default
        if "extract-links" in dirbuster_config:
            extract_links = str(dirbuster_config["extract-links"]).lower()
        
        # Get follow redirects setting
        follow_redirects = "true"  # Default  
        if "follow-redirects" in dirbuster_config:
            follow_redirects = str(dirbuster_config["follow-redirects"]).lower()
        
        # Get global file path
        global_file_path = global_toml_path
        if len(global_file_path) > 50:
            global_file_path = "..." + global_file_path[-47:]
        
        # Check wordlist configuration status
        wordlist_status = get_wordlist_status_summary(global_config)
            
    except Exception as e:
        # Fallback values if TOML reading fails
        directory_wordlist = "Config error"
        threads = 15
        timeout_minutes = "None"
        recursion_depth = 4
        dirbuster_timeout_secs = 10
        http_methods = "[GET]"
        status_codes = "All Status Codes"
        extract_links = "true"
        follow_redirects = "true"
        global_file_path = "config.toml"
        wordlist_status = "Config error"

    # Build config display from actual TOML values
    configs = [
        ("🎯 Target Url", target_display),
        ("📊 Threads", str(threads)),
        ("📝 Directory Wordlist", directory_wordlist),
        ("📚 All Wordlists", wordlist_status),
        ("⏱️  Timeout", timeout_minutes),
        ("🔧 Status Codes", status_codes),
        ("🔍 Timeout (secs)", str(dirbuster_timeout_secs)),
        ("👤 User-Agent", f"ipcrawler/{VERSION}"),
        ("💾 Config File", global_file_path),
        ("🔗 Extract Links", extract_links),
        ("🌐 HTTP methods", http_methods),
        ("📋 Follow Redirects", follow_redirects),
        ("🔄 Recursion Depth", str(recursion_depth)),
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

    # Only show debug output if explicit debug flag is enabled
    if config.get("debug", False):
        if config["accessible"]:
            args = ("Debug:",) + args
        if RICH_AVAILABLE and not config["accessible"]:
            # Enhanced debug output with spider theme
            debug_text = Text.assemble(
                ("🕷️", "bold cyan"),
                ("  DEBUG", "bold green"),
                ("     ", ""),
                ("🐛", "bold green"),
                ("    ", ""),
                ("🔧 TRACE", "bold green"),
                ("     ", ""),
                (" ".join(str(arg) for arg in args), "dim green")
            )
            get_console().print(debug_text)
        else:
            cprint(*args, color=color, char="-", sep=sep, end=end, file=file, frame_index=2, **kvargs)


def process_color_codes(text):
    """Convert color code placeholders to actual colors for Rich display"""
    import re
    
    # Color mappings for Rich
    color_map = {
        "{bgreen}": "[bold green]",
        "{bred}": "[bold red]",
        "{bblue}": "[bold blue]",
        "{byellow}": "[bold yellow]",
        "{bmagenta}": "[bold magenta]",
        "{green}": "[green]",
        "{red}": "[red]",
        "{blue}": "[blue]",
        "{yellow}": "[yellow]",
        "{magenta}": "[magenta]",
        "{bright}": "[bold]",
        "{srst}": "[/bold]",
        "{crst}": "[/]",
        "{rst}": "[/]",
    }
    
    # Replace color codes
    for code, rich_markup in color_map.items():
        text = text.replace(code, rich_markup)
    
    return text


def info(*args, sep=" ", end="\n", file=sys.stdout, **kvargs):
    # Import config fresh each time to avoid import-time initialization issues
    try:
        from ipcrawler.config import config
    except ImportError:
        # Fallback if config not available
        config = {"verbosity": 1, "accessible": False}

    verbosity = kvargs.get("verbosity", 1)

    if config.get("verbosity", 1) >= verbosity:
        # Check if any message contains color codes
        has_color_codes = any(
            any(code in str(arg) for code in ["{bgreen}", "{bred}", "{bblue}", "{byellow}", "{bmagenta}", 
                                              "{green}", "{red}", "{blue}", "{yellow}", "{magenta}", 
                                              "{bright}", "{srst}", "{crst}", "{rst}"])
            for arg in args
        )
        
        # If message has color codes, use cprint for proper color processing
        if has_color_codes:
            cprint(*args, color=Fore.CYAN, char="*", sep=sep, end=end, file=file, frame_index=2, **kvargs)
            return
        
        if RICH_AVAILABLE and not config.get("accessible", False):
            # Build the message parts
            message_parts = []
            for arg in args:
                # Parse and convert color-coded text to Rich markup
                text = str(arg)
                
                # Handle service discovery messages
                if "📡 INFO" in text and "running against" in text:
                    # Extract components for service start message
                    parts = text.split("📡 INFO")
                    if len(parts) > 1:
                        service_text = Text.assemble(
                            ("🕷️", "bold cyan"),
                            ("  CRAWL", "bold green"),
                            ("    ", ""),
                            ("200", "bold green"),
                            ("    ", ""),
                            ("🌐 TARGET", "bold blue"),
                            (parts[1], "white")
                        )
                        # Use main console, not progress console
                        rich_console.print(service_text)
                        return
                
                # Handle port/service discovery
                elif any(indicator in text for indicator in ["tcp/", "udp/", "/tcp", "/udp", "OPEN"]):
                    # Extract components for discovery message
                    discovery_text = Text.assemble(
                        ("🕷️", "bold cyan"),
                        ("  SCAN", "bold green"),
                        ("     ", ""),
                        ("200", "bold green"),
                        ("    ", ""),
                        ("🔍 FOUND", "bold yellow"),
                        ("    ", ""),
                        (text, "yellow")
                    )
                    rich_console.print(discovery_text)
                    return
                
                # Handle service enum starts
                elif "Service scan" in text and "running against" in text:
                    service_text = Text.assemble(
                        ("🕷️", "bold cyan"),
                        ("  ENUM", "bold green"),
                        ("     ", ""),
                        ("200", "bold green"),
                        ("    ", ""),
                        ("🌐 SERVICE", "bold blue"),
                        ("  Service scan", "white"),
                        (text.split("Service scan")[1], "cyan")
                    )
                    rich_console.print(service_text)
                    return
                
                # Handle completion messages
                elif "✅" in text or "Completed:" in text:
                    completion_text = Text.assemble(
                        ("🕷️", "bold cyan"),
                        ("  DONE", "bold green"),
                        ("      ", ""),
                        ("200", "bold green"),
                        ("    ", ""),
                        ("🕸️ SUCCESS", "bold green"),
                        ("   " + text.replace("✅ Completed:", "").strip(), "white")
                    )
                    rich_console.print(completion_text)
                    return
                
                # Handle scan start messages  
                elif "🚀 Started:" in text:
                    scan_text = Text.assemble(
                        ("🕷️", "bold cyan"),
                        ("  INIT", "bold green"),
                        ("      ", ""),
                        ("200", "bold green"),
                        ("    ", ""),
                        ("⚡ DEPLOY", "bold magenta"),
                        ("    " + text.replace("🚀 Started:", "").strip(), "white")
                    )
                    rich_console.print(scan_text)
                    return
                
                # Handle finish messages
                elif "🏁 Finished:" in text:
                    finish_text = Text.assemble(
                        ("🕷️", "bold cyan"),
                        ("  HALT", "bold green"),
                        ("      ", ""),
                        ("200", "bold green"),
                        ("    ", ""),
                        ("🎯 COMPLETE", "bold blue"),
                        ("  " + text.replace("🏁 Finished:", "").strip(), "white")
                    )
                    rich_console.print(finish_text)
                    return
                
                # Handle pattern matches
                elif "🔍 Found:" in text or "Match:" in text:
                    pattern_text = Text.assemble(
                        ("🕷️", "bold cyan"),
                        ("  HUNT", "bold green"),
                        ("      ", ""),
                        ("200", "bold green"),
                        ("    ", ""),
                        ("🎯 PREY", "bold yellow"),
                        ("      " + text.replace("🔍 Found:", "").replace("Match:", "").strip(), "cyan")
                    )
                    rich_console.print(pattern_text)
                    return
                
                # Default case - convert to Rich text
                message_parts.append(str(arg))
            
            # Default rich output for other info messages
            if message_parts:
                default_text = Text.assemble(
                    ("🕷️", "bold cyan"),
                    ("  INFO", "bold green"),
                    ("      ", ""),
                    ("200", "bold green"),
                    ("    ", ""),
                    ("🌐 CRAWL", "bold blue"),
                    ("     " + sep.join(message_parts), "white")
                )
                rich_console.print(default_text)
        else:
            # Fallback to regular output
            cprint(*args, color=Fore.CYAN, char="*", sep=sep, end=end, file=file, **kvargs)


def warn(*args, sep=" ", end="\n", file=sys.stderr, **kvargs):
    # Import config fresh each time to avoid import-time initialization issues
    try:
        from ipcrawler.config import config
    except ImportError:
        config = {"accessible": False}

    # Check if any message contains color codes
    has_color_codes = any(
        any(code in str(arg) for code in ["{bgreen}", "{bred}", "{bblue}", "{byellow}", "{bmagenta}", 
                                          "{green}", "{red}", "{blue}", "{yellow}", "{magenta}", 
                                          "{bright}", "{srst}", "{crst}", "{rst}"])
        for arg in args
    )
    
    # If message has color codes, use cprint for proper color processing
    if has_color_codes:
        cprint(*args, color=Fore.YELLOW, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)
        return

    if RICH_AVAILABLE and not config.get("accessible", False):
        message = sep.join(str(arg) for arg in args)
        
        warning_text = Text.assemble(
            ("🕷️", "bold cyan"),
            ("  WARN", "bold yellow"),
            ("      ", ""),
            ("403", "bold yellow"),
            ("    ", ""),
            ("⚠️  CAUTION", "bold yellow"),
            ("   " + message, "yellow")
        )
        rich_console.print(warning_text)
    else:
        cprint(*args, color=Fore.YELLOW, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)


def error(*args, sep=" ", end="\n", file=sys.stderr, **kvargs):
    # Import config fresh each time to avoid import-time initialization issues
    try:
        from ipcrawler.config import config
    except ImportError:
        config = {"accessible": False}

    # Check if any message contains color codes
    has_color_codes = any(
        any(code in str(arg) for code in ["{bgreen}", "{bred}", "{bblue}", "{byellow}", "{bmagenta}", 
                                          "{green}", "{red}", "{blue}", "{yellow}", "{magenta}", 
                                          "{bright}", "{srst}", "{crst}", "{rst}"])
        for arg in args
    )
    
    # If message has color codes, use cprint for proper color processing
    if has_color_codes:
        cprint(*args, color=Fore.RED, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)
        return

    if RICH_AVAILABLE and not config.get("accessible", False):
        message = sep.join(str(arg) for arg in args)
        
        error_text = Text.assemble(
            ("🕷️", "bold cyan"),
            ("  FAIL", "bold red"),
            ("      ", ""),
            ("500", "bold red"),
            ("    ", ""),
            ("💀 ERROR", "bold red"),
            ("     " + message, "red")
        )
        rich_console.print(error_text)
    else:
        cprint(*args, color=Fore.RED, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)


def fail(*args, sep=" ", end="\n", file=sys.stderr, **kvargs):
    # Import config fresh each time to avoid import-time initialization issues  
    try:
        from ipcrawler.config import config
    except ImportError:
        config = {"accessible": False}

    # Check if any message contains color codes
    has_color_codes = any(
        any(code in str(arg) for code in ["{bgreen}", "{bred}", "{bblue}", "{byellow}", "{bmagenta}", 
                                          "{green}", "{red}", "{blue}", "{yellow}", "{magenta}", 
                                          "{bright}", "{srst}", "{crst}", "{rst}"])
        for arg in args
    )
    
    # If message has color codes, use cprint for proper color processing
    if has_color_codes:
        cprint(*args, color=Fore.RED, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)
        return

    if RICH_AVAILABLE and not config.get("accessible", False):
        message = sep.join(str(arg) for arg in args)
        
        fail_text = Text.assemble(
            ("🕷️", "bold cyan"),
            ("  DEAD", "bold red"),
            ("      ", ""),
            ("666", "bold red on black"),
            ("    ", ""),
            ("☠️  FATAL", "bold red on black"),
            ("    " + message, "bold red")
        )
        rich_console.print(fail_text)
    else:
        cprint(*args, color=Fore.RED, char="!", sep=sep, end=end, file=file, frame_index=2, **kvargs)


def show_scan_summary(target_count, total_time, findings_count=0):
    """Display spider-themed scan completion summary"""
    if not RICH_AVAILABLE or config["accessible"]:
        info(f"Scan completed! {target_count} targets scanned in {total_time}")
        return

    summary_panel = Panel.fit(
        Text.assemble(
            ("🕸️ WEB COMPLETE", "bold green"),
            "\n\n",
            ("📊 Spider Statistics:", "bold"),
            "\n",
            ("  🎯 Targets Crawled: ", "dim"),
            (str(target_count), "cyan"),
            "\n",
            ("  ⏱️  Hunt Duration: ", "dim"),
            (total_time, "cyan"),
            "\n",
            ("  🔍 Vulnerabilities Found: ", "dim"),
            (str(findings_count), "red" if findings_count > 0 else "green"),
            "\n\n",
            ("🕷️ Results cached in web: ", "dim"),
            ("./results/", "yellow"),
            "\n",
            ("📋 Check _manual_commands.txt for deeper crawling!", "bold blue"),
        ),
        title="[bold green]🕸️ Spider Hunt Complete 🕸️[/bold green]",
        border_style="green",
        subtitle="[dim]The web has been thoroughly explored...[/dim]"
    )

    rich_console.print(summary_panel)


class ProgressManager:
    def __init__(self):
        self.active = False
        self.tasks = {}
        self.task_keys = {}  # Track existing progress bars by unique key
        self.progress = None
        self.live = None
        self.console = None
        self._update_lock = None  # Lock to prevent concurrent updates

    def start(self):
        """Start the progress manager with spider theme"""
        debug(
            f"ProgressManager.start() called - RICH_AVAILABLE: {RICH_AVAILABLE}, accessible: {config.get('accessible', False)}",
            verbosity=3,
        )

        if RICH_AVAILABLE and not config.get("accessible", False):
            try:
                import sys
                import os
                
                # Create a dedicated console for progress bars with proper fallback
                try:
                    # Try to use stderr as the output stream for progress bars
                    # This ensures they're visible but separate from regular stdout
                    progress_file = sys.stderr
                except Exception:
                    # Ultimate fallback to stdout if stderr fails
                    progress_file = sys.stdout
                
                # Create a simpler, more robust console for progress only
                self.console = Console(
                    file=progress_file, 
                    force_terminal=True, 
                    width=120,
                    stderr=True
                )
                
                # Create custom spider-themed spinner
                from rich.spinner import Spinner
                spider_frames = ["🕷️ ", "🕸️ ", "🌐 ", "⚡ ", "🔍 ", "🎯 "]
                
                # Create Rich progress display with spider theme
                self.progress = Progress(
                    # Custom spider spinner
                    SpinnerColumn(spinner="dots", style="bold cyan"),
                    # Spider icon and description
                    TextColumn("🕷️ [bold cyan]{task.description}", justify="left"),
                    # Custom web-themed progress bar
                    BarColumn(
                        bar_width=40, 
                        style="dim cyan", 
                        complete_style="bold green", 
                        finished_style="bold green",
                        pulse_style="cyan"
                    ),
                    # Task progress with spider emoji
                    TaskProgressColumn(show_speed=False, text_format="[progress.percentage]{task.percentage:>3.0f}%"),
                    # Time with spider theme
                    TextColumn("🌐"),
                    TimeElapsedColumn(),
                    console=self.console,
                    refresh_per_second=4,  # Higher refresh rate for immediate updates
                    expand=False,
                    speed_estimate_period=30,
                    transient=True,  # Remove completed bars to avoid clutter
                    auto_refresh=True,  # Enable auto refresh
                )
                
                # Use Live display with aggressive refresh settings
                self.live = Live(
                    self.progress,
                    console=self.console,
                    refresh_per_second=4,  # Higher refresh rate for immediate updates
                    redirect_stdout=False,  # Don't interfere with stdout
                    redirect_stderr=False,  # Don't interfere with stderr logging
                    auto_refresh=True,
                    transient=True  # Remove completed display to avoid clutter
                )
                
                # Start the Live display
                self.live.start()
                self.active = True
                debug("🕷️ Spider progress manager deployed (Rich Live mode)", verbosity=3)
                
            except Exception as e:
                debug(f"Failed to deploy spider progress manager: {e}, falling back to text mode", verbosity=3)
                # Fallback to text mode
                self.progress = None
                self.live = None
                self.console = None
                self.active = True
        else:
            # Text mode fallback
            self.progress = None
            self.live = None
            self.console = None  
            self.active = True
            debug("🕷️ Spider progress manager deployed (text mode)", verbosity=3)
        
        # Initialize async lock for thread-safe updates
        import asyncio
        try:
            self._update_lock = asyncio.Lock()
        except RuntimeError:
            # If no event loop, create a basic lock placeholder
            self._update_lock = None

    def add_task(self, description, total=100, task_key=None):
        """Add a new spider task, or reuse existing one if task_key matches"""
        debug(f"🕷️ add_task called: {description}, active: {self.active}, task_key: {task_key}", verbosity=3)
        if not self.active:
            debug("🕸️ Spider manager not deployed, returning None", verbosity=3)
            return None

        # Aggressive deduplication: if task_key exists and has any active task, reuse it
        if task_key and task_key in self.task_keys:
            existing_task_ids = self.task_keys[task_key]
            # Check all tasks with this key
            for existing_task_id in existing_task_ids[:]:  # Create copy to avoid modification during iteration
                if existing_task_id in self.tasks:
                    task = self.tasks[existing_task_id]
                    # If task is not explicitly completed, reuse it
                    if not task.get("completed_flag", False) and not task.get("scan_completed", False):
                        debug(f"🕸️ Reusing active spider thread {existing_task_id} for key {task_key}", verbosity=3)
                        # Reset the task description and total if needed
                        task["description"] = description
                        task["total"] = total
                        task["last_update"] = time.time()
                        return existing_task_id
                else:
                    # Clean up stale task ID from the list
                    existing_task_ids.remove(existing_task_id)
                    debug(f"🧹 Removed stale thread ID {existing_task_id} from web {task_key}", verbosity=3)
            
            # If no active tasks remain, clean up the empty key
            if not existing_task_ids:
                del self.task_keys[task_key]
                debug(f"🧹 Cleaned up empty web node {task_key}", verbosity=3)

        # Clean up any truly stale tasks before creating new ones
        self.clean_stale_tasks()

        if self.progress and self.live and self.live.is_started:
            # Use Rich progress bar with Live display and spider theme
            try:
                # Enhance description with spider terminology
                spider_description = f"Crawling: {description}"
                task_id = self.progress.add_task(spider_description, total=total)
                self.tasks[task_id] = {
                    "description": spider_description,
                    "started": time.time(),
                    "total": total,
                    "completed": 0,
                    "last_update": time.time(),
                    "rich_task": True,
                    "task_key": task_key,
                    "completed_flag": False,
                    "scan_completed": False,
                }
                # Store the mapping for cleanup and deduplication
                if task_key:
                    if task_key not in self.task_keys:
                        self.task_keys[task_key] = []
                    self.task_keys[task_key].append(task_id)
                
                debug(f"🕷️ Spider thread {task_id} deployed: {spider_description}", verbosity=3)
                
                # Start a progress updater for this task
                if hasattr(asyncio, 'create_task'):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(self._progress_updater(task_id, 60))  # 60 second default duration
                    except RuntimeError:
                        # No event loop running
                        pass
                
                return task_id
            except Exception as e:
                debug(f"Error deploying spider thread: {e}", verbosity=3)
                # Fall through to text mode
        else:
            # Fallback to simple tracking with spider theme
            task_id = len(self.tasks) + 1
            spider_description = f"Crawling: {description}"
            self.tasks[task_id] = {
                "description": spider_description,
                "started": time.time(),
                "total": total,
                "completed": 0,
                "last_update": time.time(),
                "rich_task": False,
                "task_key": task_key,
                "completed_flag": False,
                "scan_completed": False,
            }
            # Store the mapping for cleanup and deduplication
            if task_key:
                if task_key not in self.task_keys:
                    self.task_keys[task_key] = []
                self.task_keys[task_key].append(task_id)
                
            info(f"⚡ Spider deployed: {description}", verbosity=2)
            debug(f"🕷️ Text spider {task_id} deployed: {spider_description} (web: {task_key})", verbosity=3)

        return task_id

    def update_task(self, task_id, advance=1):
        """Update progress on a task"""
        if not self.active or task_id is None or task_id not in self.tasks:
            debug(f"update_task: spider {task_id} not found or web inactive", verbosity=3)
            return

        try:
            self.tasks[task_id]["completed"] += advance
            self.tasks[task_id]["last_update"] = time.time()

            if self.tasks[task_id].get("rich_task", False) and self.progress:
                # Update Rich progress bar
                self.progress.update(task_id, advance=advance)
            else:
                # Simple text completion message for non-Rich tasks
                task = self.tasks[task_id]
                if task["completed"] >= task["total"]:
                    info(f"✅ Completed: {task['description']}", verbosity=1)

        except Exception as e:
            debug(f"Error updating spider task {task_id}: {e}", verbosity=3)

    def complete_task(self, task_id):
        """Complete a spider task and schedule its removal"""
        if not self.active or task_id is None or task_id not in self.tasks:
            debug(f"complete_task: spider {task_id} not found or web inactive", verbosity=3)
            return

        try:
            task = self.tasks[task_id]

            # Check if task was already completed
            if task.get("completed_flag", False):
                debug(f"Spider {task_id} already caught prey, skipping duplicate completion", verbosity=3)
                return

            # Mark as completed to prevent duplicate completion
            task["completed_flag"] = True
            task["scan_completed"] = True  # Signal to progress updater to stop
            elapsed = time.time() - task["started"]
            
            debug(f"🕸️ Spider {task_id} task complete: {task.get('description', 'Unknown')} (hunt took {elapsed:.1f}s)", verbosity=3)

            if task.get("rich_task", False) and self.progress:
                try:
                    # Complete Rich progress bar to 100%
                    self.progress.update(task_id, completed=task["total"])
                    debug(f"🕷️ Spider web {task_id} updated to 100%", verbosity=3)
                except Exception as e:
                    debug(f"Error updating spider web {task_id}: {e}", verbosity=3)
            else:
                # Show text completion message with spider theme
                info(f"🕸️ Web complete: {task['description']} (hunt took {elapsed:.1f}s)", verbosity=1)

            # Remove task immediately instead of scheduling delayed removal
            self._remove_task_sync(task_id)
                
        except Exception as e:
            debug(f"Error completing spider task {task_id}: {e}", verbosity=3)

    async def _remove_task_after_delay(self, task_id, delay=0.1):
        """Remove completed task after very short delay"""
        await asyncio.sleep(delay)
        
        # Double-check task still exists and manager is active
        if not self.active or task_id not in self.tasks:
            debug(f"_remove_task_after_delay: spider {task_id} already removed or manager inactive", verbosity=3)
            return
            
        self._remove_task_sync(task_id)

    def _remove_task_sync(self, task_id):
        """Synchronously remove a spider task with immediate Rich display update"""
        if task_id not in self.tasks:
            debug(f"Spider {task_id} already removed from web", verbosity=3)
            return
            
        task = self.tasks[task_id]
        task_key = task.get("task_key")
        
        # Remove from Rich progress - this should immediately hide the progress bar
        if self.progress and hasattr(self.progress, 'remove_task'):
            try:
                self.progress.remove_task(task_id)
                # Force multiple immediate refreshes to ensure the bar disappears
                if self.live and hasattr(self.live, 'refresh'):
                    for _ in range(3):  # Multiple refreshes to force immediate update
                        self.live.refresh()
                debug(f"🕷️ Spider web {task_id} removed successfully", verbosity=3)
            except Exception as e:
                debug(f"Error removing spider web {task_id}: {e}", verbosity=3)
        
        # Clean up task key mapping
        if task_key and task_key in self.task_keys:
            if task_id in self.task_keys[task_key]:
                self.task_keys[task_key].remove(task_id)
                debug(f"🕸️ Spider ID {task_id} removed from web node {task_key}", verbosity=3)
                
                # Remove empty task key mappings
                if not self.task_keys[task_key]:
                    del self.task_keys[task_key]
                    debug(f"🧹 Web node {task_key} removed from mapping (no more spiders)", verbosity=3)
        
        # Remove from internal tracking
        del self.tasks[task_id]
        debug(f"🕷️ Spider task {task_id} removed from web", verbosity=3)

    def simulate_progress(self, task_id, duration=10):
        """Simulate spider crawling progress for long-running tasks"""
        if not self.active or task_id is None or task_id not in self.tasks:
            return

        # Update progress gradually during the scan
        asyncio.create_task(self._progress_updater(task_id, duration))

    async def _progress_updater(self, task_id, duration):
        """Gradually update spider crawling progress over duration"""
        if not self.active or task_id not in self.tasks:
            return

        start_time = time.time()
        last_progress_value = 0
        task = self.tasks[task_id]

        while self.active:
            try:
                # Check if task still exists before accessing it
                if task_id not in self.tasks:
                    debug(f"🕸️ Spider progress updater: thread {task_id} no longer in web, stopping", verbosity=3)
                    break

                # Check if scan has completed
                if self.tasks[task_id].get("scan_completed", False):
                    debug(f"🕷️ Spider progress updater: hunt completed for thread {task_id}, returning to web", verbosity=3)
                    break

                elapsed = time.time() - start_time

                # More realistic spider crawling progress curve
                if elapsed < duration * 0.8:
                    # Fast progress up to 70% within 80% of estimated duration (spider moving quickly)
                    progress_percent = (elapsed / (duration * 0.8)) * 70
                elif elapsed < duration:
                    # Slower progress from 70% to 85% (spider being more careful)
                    remaining_progress = ((elapsed - duration * 0.8) / (duration * 0.2)) * 15
                    progress_percent = 70 + remaining_progress
                else:
                    # After estimated duration, slowly approach 92-95% but leave room for completion
                    overtime = elapsed - duration
                    # Cap at 95% to leave room for actual completion (spider almost done)
                    progress_percent = min(95, 85 + (10 * (1 - math.exp(-overtime / 120))))  # 2min time constant

                # Convert percentage to actual progress value based on task total
                current_progress_value = (progress_percent / 100) * task["total"]
                
                # Calculate how much to advance since last update
                advance_amount = current_progress_value - last_progress_value
                
                if advance_amount > 0:
                    # For Rich tasks, update directly with safe locking
                    if task.get("rich_task", False) and self.progress:
                        try:
                            # Use locking if available to prevent conflicts
                            if self._update_lock:
                                async with self._update_lock:
                                    self.progress.update(task_id, completed=current_progress_value)
                                    self.tasks[task_id]["completed"] = current_progress_value
                                    self.tasks[task_id]["last_update"] = time.time()
                            else:
                                self.progress.update(task_id, completed=current_progress_value)
                                self.tasks[task_id]["completed"] = current_progress_value
                                self.tasks[task_id]["last_update"] = time.time()
                        except Exception as e:
                            debug(f"Error updating spider web thread {task_id}: {e}", verbosity=3)
                    else:
                        # Use the proper update_task method which handles milestones
                        self.update_task(task_id, advance=advance_amount)
                    
                    last_progress_value = current_progress_value

            except Exception as e:
                debug(f"🕷️ Spider progress updater error for thread {task_id}: {e}", verbosity=3)
                break

            # Update every 1 second for responsive progress bars (spider moving)
            await asyncio.sleep(1.0)  
            
            # Periodically clean up stale tasks (every 60 seconds) - web maintenance
            if elapsed % 60 < 1.0:  # Check every 60 seconds
                self.clean_stale_tasks()

        debug(f"🕸️ Spider progress updater for thread {task_id} returned to web", verbosity=3)

    def clean_stale_tasks(self):
        """Clean up any stale or completed spider tasks that weren't properly removed from the web"""
        if not self.active:
            return
            
        current_time = time.time()
        stale_tasks = []
        
        for task_id, task in list(self.tasks.items()):
            # Remove tasks that have been completed immediately (no delay) - spider caught prey
            if task.get("completed_flag", False):
                stale_tasks.append(task_id)
            # Remove tasks that haven't been updated in more than 300 seconds (5 minutes) - spider went missing
            elif current_time - task.get("last_update", current_time) > 300:
                stale_tasks.append(task_id)
        
        for task_id in stale_tasks:
            debug(f"🧹 Cleaning up lost spider {task_id} from web", verbosity=3)
            self._remove_task_sync(task_id)
        
        # Also clean up orphaned task_keys (web nodes with no valid spider IDs)
        orphaned_keys = []
        for task_key, task_id_list in list(self.task_keys.items()):
            valid_task_ids = [tid for tid in task_id_list if tid in self.tasks]
            if not valid_task_ids:
                orphaned_keys.append(task_key)
            elif len(valid_task_ids) != len(task_id_list):
                # Update the list to only contain valid task IDs
                self.task_keys[task_key] = valid_task_ids
                debug(f"🧹 Cleaned up web node {task_key}: removed {len(task_id_list) - len(valid_task_ids)} orphaned spider IDs", verbosity=3)
        
        for key in orphaned_keys:
            del self.task_keys[key]
            debug(f"🧹 Removed orphaned web node: {key}", verbosity=3)
        
        if stale_tasks or orphaned_keys:
            debug(f"🕸️ Web maintenance completed: removed {len(stale_tasks)} lost spiders and {len(orphaned_keys)} orphaned nodes", verbosity=3)

    def refresh_display(self):
        """Manually refresh the spider web display (useful in verbose mode)"""
        if self.active and self.progress and self.live is None:
            try:
                self.progress.console.print(self.progress)
            except Exception as e:
                debug(f"Error refreshing spider web display: {e}", verbosity=3)

    def stop(self):
        """Stop the spider manager and recall all spiders"""
        if self.active:
            self.active = False

            # Complete any remaining spider tasks
            for task_id in list(self.tasks.keys()):
                if not self.tasks[task_id].get("completed_flag", False):
                    self.tasks[task_id]["scan_completed"] = True

            # Stop Rich Live display first (most important) - recall spiders
            if self.live:
                try:
                    if hasattr(self.live, 'is_started') and self.live.is_started:
                        self.live.stop()
                    debug("🕷️ Spider web display recalled", verbosity=3)
                except Exception as e:
                    debug(f"Error recalling spider web display: {e}", verbosity=3)
                    
            # Then stop Rich progress - destroy web
            if self.progress:
                try:
                    if hasattr(self.progress, 'stop'):
                        self.progress.stop()
                    debug("🕸️ Spider web destroyed", verbosity=3)
                except Exception as e:
                    debug(f"Error destroying spider web: {e}", verbosity=3)

            # Clean up references - web cleanup
            self.progress = None
            self.live = None
            self.console = None

            debug("🕷️ Spider manager recalled and web cleaned up", verbosity=3)


# Global progress manager instance
progress_manager = ProgressManager()


def get_console():
    """Get the main rich console for regular output (not progress)"""
    return rich_console


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
            info(f"🕸️ Web extended: {ip} {hostname}", verbosity=1)

            # Also show in Rich if available with spider theme
            if RICH_AVAILABLE and not config.get("accessible", False):
                from rich.text import Text

                vhost_text = Text.assemble(
                    ("🕷️", "bold cyan"),
                    ("  WEB", "bold green"),
                    ("       ", ""),
                    ("200", "bold green"),
                    ("    ", ""),
                    ("🌐 VHOST", "bold magenta"),
                    ("    ", ""),
                    (f"{hostname}", "cyan"),
                    (" → ", "dim"),
                    (f"{ip}", "yellow"),
                )
                rich_console.print(vhost_text)

            return True

        except Exception as e:
            warn(f"🚨 Failed to extend web for {hostname}: {e}", verbosity=1)
            return False

    def suggest_manual_add(self, ip, hostname):
        """Suggest manual command for adding vhost with spider theme"""
        manual_cmd = f'echo "{ip} {hostname}" | sudo tee -a /etc/hosts'
        info(f"💡 Manual web extension: {manual_cmd}", verbosity=1)


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
                # Silently handle timeout - no warning needed as this is normal for long-running scans
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
                # For verbosity 3, enhance with spider-style live output
                if RICH_AVAILABLE and config["verbose"] >= 3 and not config["accessible"]:
                    # Spider-style live output with web theme
                    live_text = Text.assemble(
                        ("🕷️", "bold cyan"),
                        ("  LIVE", "bold green"),
                        ("      ", ""),
                        ("📡", "bold blue"),
                        ("    ", ""),
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

            # Check lines for pattern matches with spider theme.
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
                                    # Spider-style pattern match
                                    pattern_text = Text.assemble(
                                        ("🕷️", "bold cyan"),
                                        ("  HUNT", "bold green"),
                                        ("      ", ""),
                                        ("200", "bold green"),
                                        ("    ", ""),
                                        ("🎯 PREY", "bold magenta"),
                                        ("      ", ""),
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
                            # Spider-style pattern match
                            pattern_text = Text.assemble(
                                ("🕷️", "bold cyan"),
                                ("  HUNT", "bold green"),
                                ("      ", ""),
                                ("200", "bold green"),
                                ("    ", ""),
                                ("🎯 PREY", "bold magenta"),
                                ("      ", ""),
                                (f"Caught: {pattern_match}", "cyan"),
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


class LiveScanLoader:
    """Live loader showing currently working scans with spider theme"""
    
    def __init__(self):
        self.active = False
        self.live_display = None
        self.console = None
        self.current_scans = {}
        self.start_time = time.time()
        self._update_task = None
        
    def start(self):
        """Start the live scan loader with spider theme"""
        if not RICH_AVAILABLE or config.get("accessible", False):
            self.active = True
            return
            
        try:
            from rich.live import Live
            from rich.text import Text
            import sys
            
            # Create dedicated console for live loader
            self.console = Console(
                file=sys.stderr,
                force_terminal=True,
                width=120,
                height=1  # Keep it to one line
            )
            
            # Start with simple text display
            initial_text = Text("🕷️ Spider web ready... 🕸️", style="dim cyan")
            
            # Start Live display - single line, transient
            self.live_display = Live(
                initial_text,
                console=self.console,
                refresh_per_second=1,  # Reduced refresh rate
                redirect_stdout=False,
                redirect_stderr=False,
                auto_refresh=True,
                transient=True  # Don't persist when stopped
            )
            
            self.live_display.start()
            self.active = True
            
            # Start update task
            if hasattr(asyncio, 'create_task'):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self._update_task = loop.create_task(self._update_loop())
                except RuntimeError:
                    pass
                    
            debug("🕷️ Live scan loader deployed (compact mode)", verbosity=3)
            
        except Exception as e:
            debug(f"Failed to deploy live scan loader: {e}", verbosity=3)
            self.active = True  # Fallback to simple mode
    
    def update_scan_status(self, target_address, scan_tag, status="running", command=None, elapsed=None):
        """Update the status of a running scan"""
        if not self.active:
            return
            
        scan_key = f"{target_address}:{scan_tag}"
        
        if status == "running":
            self.current_scans[scan_key] = {
                "target": target_address,
                "scan": scan_tag,
                "command": command or scan_tag,
                "start_time": time.time() if scan_key not in self.current_scans else self.current_scans[scan_key].get("start_time", time.time()),
                "status": "running",
                "last_update": time.time()
            }
        elif status == "completed":
            if scan_key in self.current_scans:
                del self.current_scans[scan_key]
        
        if RICH_AVAILABLE and not config.get("accessible", False) and self.live_display:
            self._update_display()
    
    def _update_display(self):
        """Update the live display with current scan status - highly visible format"""
        if not self.live_display or not self.active:
            return
            
        try:
            from rich.text import Text
            
            # Create highly visible single-line status with background and enhanced styling
            if not self.current_scans:
                # No active scans - highly visible idle display
                status_text = Text.assemble(
                    ("  ", ""),
                    ("╔", "bold bright_cyan on black"),
                    ("🕷️", "bold bright_cyan on black"),
                    ("╗", "bold bright_cyan on black"),
                    ("  ", "bold bright_green on black"),
                    ("WEB DORMANT", "bold bright_green on black"),
                    ("  ", "bold bright_green on black"),
                    ("╚", "bold bright_cyan on black"),
                    ("🕸️", "bold bright_cyan on black"),
                    ("╝", "bold bright_cyan on black"),
                    ("  ", "")
                )
            else:
                # Active scans - highly visible format with background
                total_elapsed = time.time() - self.start_time
                minutes, seconds = divmod(int(total_elapsed), 60)
                elapsed_str = f"{minutes:02d}:{seconds:02d}"
                
                # Rotating spider animation with enhanced visibility
                spinner_frames = ["🕷️", "🕸️", "🌐", "⚡", "🔍", "🎯"]
                current_frame = int(time.time() * 2) % len(spinner_frames)
                spider_icon = spinner_frames[current_frame]
                
                # Build highly visible scan list
                scan_count = len(self.current_scans)
                
                if scan_count == 1:
                    # Single scan - show detailed info with background
                    scan_info = list(self.current_scans.values())[0]
                    scan_elapsed = time.time() - scan_info["start_time"]
                    scan_minutes, scan_seconds = divmod(int(scan_elapsed), 60)
                    scan_duration = f"{scan_minutes:02d}:{scan_seconds:02d}"
                    
                    command = scan_info["command"]
                    if len(command) > 14:
                        command = command[:11] + "..."
                    
                    status_text = Text.assemble(
                        ("  ", ""),
                        ("╔", "bold bright_cyan on black"),
                        (spider_icon, "bold bright_cyan on black"),
                        ("╗", "bold bright_cyan on black"),
                        ("  ❬", "bold bright_white on black"),
                        (f"{command.upper()}", "bold bright_green on black"),
                        ("❭  ", "bold bright_white on black"),
                        ("➤", "bold bright_magenta on black"),
                        ("  ", "bold bright_magenta on black"),
                        (f"{scan_info['target']}", "bold bright_yellow on black"),
                        ("  ⏱", "bold bright_blue on black"),
                        (f"{scan_duration}", "bold bright_blue on black"),
                        ("  ", "bold bright_blue on black"),
                        ("╚", "bold bright_cyan on black"),
                        ("🕸️", "bold bright_cyan on black"),
                        ("╝", "bold bright_cyan on black"),
                        ("  ", "")
                    )
                else:
                    # Multiple scans - show summary with enhanced visibility
                    # Get most recent scan for display
                    latest_scan = max(self.current_scans.values(), key=lambda x: x.get("last_update", 0))
                    command = latest_scan["command"]
                    if len(command) > 10:
                        command = command[:7] + "..."
                    
                    status_text = Text.assemble(
                        ("  ", ""),
                        ("╔", "bold bright_cyan on black"),
                        (spider_icon, "bold bright_cyan on black"),
                        ("╗", "bold bright_cyan on black"),
                        ("  ❬", "bold bright_white on black"),
                        (f"{scan_count}", "bold bright_green on black"),
                        (" SPIDERS", "bold bright_green on black"),
                        ("❭  ", "bold bright_white on black"),
                        ("⦿", "bold bright_magenta on black"),
                        (" LATEST: ", "bold bright_magenta on black"),
                        (f"{command.upper()}", "bold bright_yellow on black"),
                        ("  ⏱", "bold bright_blue on black"),
                        (f"{elapsed_str}", "bold bright_blue on black"),
                        ("  ", "bold bright_blue on black"),
                        ("╚", "bold bright_cyan on black"),
                        ("🕸️", "bold bright_cyan on black"),
                        ("╝", "bold bright_cyan on black"),
                        ("  ", "")
                    )
            
            # Update the live display
            self.live_display.update(status_text)
            
        except Exception as e:
            debug(f"Error updating live scan display: {e}", verbosity=3)
    
    async def _update_loop(self):
        """Continuously update the display"""
        while self.active and self.live_display:
            try:
                # Clean up stale scans (older than 5 minutes without update)
                current_time = time.time()
                stale_scans = []
                
                for scan_key, scan_info in self.current_scans.items():
                    if current_time - scan_info.get("last_update", current_time) > 300:  # 5 minutes
                        stale_scans.append(scan_key)
                
                for scan_key in stale_scans:
                    del self.current_scans[scan_key]
                    debug(f"🧹 Cleaned up stale scan: {scan_key}", verbosity=3)
                
                # Update display
                if RICH_AVAILABLE and not config.get("accessible", False):
                    self._update_display()
                    
                await asyncio.sleep(1.0)  # Update every 1 second for smooth animation
                
            except Exception as e:
                debug(f"Error in live scan loader update loop: {e}", verbosity=3)
                break
    
    def add_scan(self, target_address, scan_tag, command=None):
        """Add a new scan to the live loader"""
        if not self.active:
            return
            
        self.update_scan_status(target_address, scan_tag, "running", command)
        debug(f"🕷️ Added scan to live loader: {target_address}/{scan_tag}", verbosity=3)
    
    def complete_scan(self, target_address, scan_tag):
        """Mark a scan as completed and remove from display"""
        if not self.active:
            return
            
        self.update_scan_status(target_address, scan_tag, "completed")
        debug(f"🕸️ Completed scan in live loader: {target_address}/{scan_tag}", verbosity=3)
    
    def update_from_running_tasks(self, targets):
        """Update the loader from the main running_tasks data structure"""
        if not self.active:
            return
            
        try:
            # Get current scans from all targets
            current_keys = set()
            
            for target in targets:
                if hasattr(target, 'running_tasks'):
                    for tag, task_info in target.running_tasks.items():
                        scan_key = f"{target.address}:{tag}"
                        current_keys.add(scan_key)
                        
                        # Extract command from task info if available
                        command = tag
                        if "processes" in task_info and task_info["processes"]:
                            try:
                                cmd = task_info["processes"][0].get("cmd", "")
                                if cmd:
                                    # Extract the main command name
                                    cmd_parts = cmd.split()
                                    if cmd_parts:
                                        command = cmd_parts[0].split('/')[-1]  # Get just the binary name
                            except:
                                pass
                        
                        self.update_scan_status(target.address, tag, "running", command)
            
            # Remove scans that are no longer running
            to_remove = []
            for scan_key in self.current_scans.keys():
                if scan_key not in current_keys:
                    to_remove.append(scan_key)
            
            for scan_key in to_remove:
                target_addr, scan_tag = scan_key.split(':', 1)
                self.complete_scan(target_addr, scan_tag)
                
        except Exception as e:
            debug(f"Error updating live loader from running tasks: {e}", verbosity=3)
    
    def stop(self):
        """Stop the live scan loader"""
        if self.active:
            self.active = False
            
            # Cancel update task
            if self._update_task:
                try:
                    self._update_task.cancel()
                except:
                    pass
            
            # Stop Live display
            if self.live_display:
                try:
                    self.live_display.stop()
                    debug("🕷️ Live scan loader recalled", verbosity=3)
                except Exception as e:
                    debug(f"Error stopping live scan loader: {e}", verbosity=3)
            
            # Clean up references
            self.live_display = None
            self.console = None
            self.current_scans.clear()
            
            debug("🕸️ Live scan loader stopped and web cleaned up", verbosity=3)


# Global live scan loader instance
live_scan_loader = LiveScanLoader()


def start_live_loader():
    """Start the live scan loader - call this at the beginning of scanning"""
    # Check verbosity level properly - should work with -v (verbose >= 1), -vv (verbose >= 2), -vvv (verbose >= 3)
    if config.get("verbose", 0) >= 1:  # Only show live loader if any verbose mode is enabled
        live_scan_loader.start()
        debug(f"🕷️ Live loader started for verbosity level: {config.get('verbose', 0)}", verbosity=2)
    else:
        debug("🕸️ Live loader disabled - verbose mode required (-v, -vv, or -vvv)", verbosity=1)


def stop_live_loader():
    """Stop the live scan loader - call this at the end of scanning"""
    live_scan_loader.stop()


def update_live_loader_from_targets(targets):
    """Update the live loader with current running tasks from all targets"""
    # Only update if verbose mode is enabled
    if config.get("verbose", 0) >= 1:
        live_scan_loader.update_from_running_tasks(targets)


def add_scan_to_live_loader(target_address, scan_tag, command=None):
    """Add a scan to the live loader display"""
    # Only add if verbose mode is enabled
    if config.get("verbose", 0) >= 1:
        live_scan_loader.add_scan(target_address, scan_tag, command)


def complete_scan_in_live_loader(target_address, scan_tag):
    """Mark a scan as completed in the live loader"""
    # Only complete if verbose mode is enabled
    if config.get("verbose", 0) >= 1:
        live_scan_loader.complete_scan(target_address, scan_tag)
