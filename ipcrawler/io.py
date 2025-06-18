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

# Import our clean live status system
try:
    from ipcrawler.live_status import (
        live_status, start_live_status, stop_live_status, 
        update_status, add_scan, complete_scan, add_finding
    )
    LIVE_STATUS_AVAILABLE = True
except ImportError:
    LIVE_STATUS_AVAILABLE = False


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
            message = sep.join(str(arg) for arg in args)
            
            # Plugin execution start - clean format with live status update
            if "running against" in message and any(x in message for x in ["Service scan", "Port scan"]):
                # Extract plugin name and target from message
                plugin_name = "Unknown"
                target_info = "target"
                
                if "Service scan" in message:
                    parts = message.split("Service scan")
                    if len(parts) > 1:
                        remaining = parts[1].strip()
                        if " running against " in remaining:
                            plugin_part, target_part = remaining.split(" running against ", 1)
                            plugin_name = plugin_part.strip()
                            target_info = target_part.strip()
                elif "Port scan" in message:
                    parts = message.split("Port scan")
                    if len(parts) > 1:
                        remaining = parts[1].strip()
                        if " running against " in remaining:
                            plugin_part, target_part = remaining.split(" running against ", 1)
                            plugin_name = plugin_part.strip()
                            target_info = target_part.strip()
                
                # Update live status instead of printing
                if LIVE_STATUS_AVAILABLE:
                    add_scan(plugin_name, target_info)
                
                # Only show in verbose mode 2+
                if config.get("verbose", 0) >= 2:
                    plugin_text = Text.assemble(
                        ("▶", "green"),
                        (" ", ""),
                        (plugin_name, "white"),
                        (" → ", "dim"),
                        (target_info, "cyan")
                    )
                    rich_console.print(plugin_text)
                return
            
            # Command execution start - update live status
            elif "Starting:" in message or "🚀 Started:" in message:
                command_info = message.replace("🚀 Started:", "").replace("Starting:", "").strip()
                
                # Update live status
                if LIVE_STATUS_AVAILABLE:
                    # Extract tool and target from command
                    cmd_parts = command_info.split()
                    tool = cmd_parts[0] if cmd_parts else "unknown"
                    update_status(tool=tool)
                
                # Only show in verbose mode 2+
                if config.get("verbose", 0) >= 2:
                    cmd_text = Text.assemble(
                        ("▶", "green"),
                        (" ", ""),
                        (command_info[:60] + "..." if len(command_info) > 60 else command_info, "white")
                    )
                    rich_console.print(cmd_text)
                return
            
            # Command completion - update live status
            elif "✅" in message or "Completed:" in message or "🏁 Finished:" in message:
                result_info = message.replace("✅ Completed:", "").replace("🏁 Finished:", "").strip()
                
                # Update live status
                if LIVE_STATUS_AVAILABLE:
                    # Try to extract tool and target for completion
                    parts = result_info.split()
                    if len(parts) >= 2:
                        tool = parts[0]
                        target = parts[-1] if ":" in parts[-1] else "unknown"
                        complete_scan(tool, target)
                
                # Only show in verbose mode 2+
                if config.get("verbose", 0) >= 2:
                    result_text = Text.assemble(
                        ("✓", "green"),
                        (" ", ""),
                        (result_info, "dim")
                    )
                    rich_console.print(result_text)
                return
            
            # Discovery results - clean format with live status update
            elif any(indicator in message for indicator in ["tcp/", "udp/", "/tcp", "/udp", "OPEN", "Found:", "Discovered"]):
                # Update findings counter
                if LIVE_STATUS_AVAILABLE:
                    add_finding()
                
                # Clean discovery format - only show significant discoveries
                if config.get("verbose", 0) >= 1:
                    # Extract the important part
                    if "OPEN" in message or "Found:" in message or "Discovered" in message:
                        discovery_text = Text.assemble(
                            ("●", "yellow"),
                            (" ", ""),
                            (message, "white")
                        )
                        rich_console.print(discovery_text)
                return
            
            # Pattern matches - important findings
            elif "🔍 Found:" in message or "Match:" in message or "Matched Pattern:" in message:
                pattern_info = message.replace("🔍 Found:", "").replace("Match:", "").replace("Matched Pattern:", "").strip()
                
                # Update findings counter
                if LIVE_STATUS_AVAILABLE:
                    add_finding()
                
                # Show pattern matches - these are important
                if config.get("verbose", 0) >= 1:
                    pattern_text = Text.assemble(
                        ("●", "magenta"),
                        (" MATCH ", "magenta"),
                        (pattern_info, "white")
                    )
                    rich_console.print(pattern_text)
                return
            
            # Error conditions - always show errors
            elif any(error_word in message.lower() for error_word in ["error", "failed", "timeout", "refused"]):
                error_text = Text.assemble(
                    ("✗", "red"),
                    (" ", ""),
                    (message, "red")
                )
                rich_console.print(error_text)
                return
            
            # Warning conditions - show in verbose mode
            elif any(warn_word in message.lower() for warn_word in ["warning", "skipping", "disabled"]):
                if config.get("verbose", 0) >= 2:
                    warn_text = Text.assemble(
                        ("⚠", "yellow"),
                        (" ", ""),
                        (message, "dim")
                    )
                    rich_console.print(warn_text)
                return
            
            # Default info message - only in high verbosity
            else:
                if config.get("verbose", 0) >= 3:
                    info_text = Text.assemble(
                        ("·", "dim"),
                        (" ", ""),
                        (message, "dim")
                    )
                    rich_console.print(info_text)
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


def show_phase_header(phase_name, description=None, target_info=None, verbosity=1):
    """Display a clear phase header for major scanning stages only"""
    # Only show phase headers for verbosity 1 or higher, and only for major phases
    if config.get("verbose", 0) < verbosity:
        return
        
    if not RICH_AVAILABLE or config.get("accessible", False):
        info(f"=== {phase_name} ===")
        if description:
            info(description)
        return

    # Create a clean phase separator for major phases only
    phase_text = Text.assemble(
        ("\n", ""),
        ("━━━ ", "bold cyan"),
        (phase_name.upper(), "bold white"),
        (" ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "bold cyan"),
        ("\n", "")
    )
    
    if description:
        phase_text.append(f"    {description}\n", style="dim")
    
    if target_info:
        phase_text.append(f"    Target: {target_info}\n", style="blue")
    
    rich_console.print(phase_text)


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


class SimpleProgressManager:
    """Simplified progress manager that integrates with live status"""
    def __init__(self):
        self.active = False

    def start(self):
        """Start the simplified progress manager"""
        self.active = True
        # Start our clean live status instead
        if LIVE_STATUS_AVAILABLE:
            start_live_status()

    def add_task(self, description, total=100, task_key=None):
        """Simplified task addition - just return a dummy task ID"""
        if not self.active:
            return None
        
        # Just return a simple task ID
        return f"task_{int(time.time() * 1000)}"

    def update_task(self, task_id, advance=1):
        """Simplified task update - does nothing""" 
        pass

    def complete_task(self, task_id):
        """Simplified task completion - does nothing"""
        pass

    def stop(self):
        """Stop the progress manager"""
        self.active = False
        if LIVE_STATUS_AVAILABLE:
            stop_live_status()

    def clean_stale_tasks(self):
        """Simplified cleanup - does nothing"""
        pass

    def simulate_progress(self, task_id, duration=10):
        """Simplified progress simulation - does nothing"""
        pass

    def refresh_display(self):
        """Simplified display refresh - does nothing"""
        pass


# Replace old complex ProgressManager with our simple one
progress_manager = SimpleProgressManager()


# Keep all old function names for backward compatibility
def start_live_loader():
    """Legacy function - start live status display"""
    if LIVE_STATUS_AVAILABLE and config.get("verbose", 0) >= 1:
        start_live_status()

def stop_live_loader():
    """Legacy function - stop live status display"""
    if LIVE_STATUS_AVAILABLE:
        stop_live_status()

def update_live_loader_from_targets(targets):
    """Legacy function - does nothing in new system"""
    pass

def add_scan_to_live_loader(target_address, scan_tag, command=None):
    """Legacy function - add scan to live status"""
    if LIVE_STATUS_AVAILABLE:
        add_scan(scan_tag, target_address)  # tool, target

def complete_scan_in_live_loader(target_address, scan_tag):
    """Legacy function - complete scan in live status"""
    if LIVE_STATUS_AVAILABLE:
        complete_scan(scan_tag, target_address)  # tool, target


# Clean up - removed old complex ProgressManager code


# Note: progress_manager defined above with SimpleProgressManager


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
                # For verbosity 3, enhanced clean live output
                if RICH_AVAILABLE and config["verbose"] >= 3 and not config["accessible"]:
                    # Clean live output format with minimal visual noise
                    trimmed_line = line.strip()
                    if len(trimmed_line) > 80:
                        trimmed_line = trimmed_line[:77] + "..."
                    
                    live_text = Text.assemble(
                        ("    ", ""),
                        ("│", "dim cyan"),
                        (" ", ""),
                        (f"{self.tag[:8]:<8}", "dim blue"),
                        (" │ ", "dim"),
                        (trimmed_line, "white")
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
                                    # Clean pattern match display
                                    pattern_text = Text.assemble(
                                        ("  ", ""),
                                        ("🎯", "bold magenta"),
                                        (" MATCH", "bold magenta"),
                                        (" │ ", "dim"),
                                        (f"{self.tag}", "dim blue"),
                                        (" │ ", "dim"),
                                        (description, "magenta")
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
                            # Clean pattern match display
                            pattern_text = Text.assemble(
                                ("  ", ""),
                                ("🎯", "bold magenta"),
                                (" MATCH", "bold magenta"),
                                (" │ ", "dim"),
                                (f"{self.tag}", "dim blue"),
                                (" │ ", "dim"),
                                (f"Pattern: {pattern_match}", "magenta")
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
    """Disabled - replaced by clean LiveStatus system"""
    
    def __init__(self):
        self.active = False
        
    def start(self):
        """Disabled - using new LiveStatus instead"""
        pass
    
    def update_scan_status(self, target_address, scan_tag, status="running", command=None, elapsed=None):
        """Disabled"""
        pass
    
    def add_scan(self, target_address, scan_tag, command=None):
        """Disabled"""
        pass
    
    def complete_scan(self, target_address, scan_tag):
        """Disabled"""
        pass
    
    def update_from_running_tasks(self, targets):
        """Disabled"""
        pass
    
    def stop(self):
        """Disabled"""
        pass


# Old LiveScanLoader completely disabled - using clean LiveStatus system


# Global live scan loader instance (disabled)
live_scan_loader = LiveScanLoader()


