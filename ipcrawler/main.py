#!/usr/bin/python3

import argparse, asyncio, importlib.util, inspect, ipaddress, math, os, re, select, shutil, signal, socket, sys, termios, time, traceback, tty
from datetime import datetime

try:
    import colorama, impacket, platformdirs, psutil, requests, toml, unidecode
    from colorama import Fore, Style
except ModuleNotFoundError:
    print(
        "One or more required modules was not installed. Please run or re-run: "
        + ("sudo " if os.getuid() == 0 else "")
        + "python3 -m pip install -r requirements.txt"
    )
    sys.exit(1)

# Rich support for enhanced help (optional)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

colorama.init()

from ipcrawler.config import config, configurable_keys, configurable_boolean_keys
from ipcrawler.io import (
    slugify,
    e,
    fformat,
    cprint,
    debug,
    info,
    warn,
    error,
    fail,
    CommandStreamReader,
    show_startup_banner,
    show_scan_summary,
    progress_manager,
    rich_console,
    start_live_loader,
    stop_live_loader,
    update_live_loader_from_targets,
    add_scan_to_live_loader,
    complete_scan_in_live_loader,
)
from ipcrawler.plugins import Pattern, PortScan, ServiceScan, Report, ipcrawler
from ipcrawler.targets import Target, Service

VERSION = "2.2.0"


def show_rich_help():
    """Display beautiful help output using Rich library"""
    # Header
    rich_console.print(
        Panel.fit(
            "[bold blue]🕷️  ipcrawler[/bold blue] - Network Reconnaissance Tool\n[dim]v"
            + VERSION
            + " - Simplified AutoRecon for OSCP & CTFs[/dim]",
            border_style="blue",
        )
    )

    # Usage
    rich_console.print("\n[bold green]Basic Usage:[/bold green]")
    usage_table = Table(show_header=False, box=None, padding=(0, 2))
    usage_table.add_column("Command", style="cyan")
    usage_table.add_column("Description")

    usage_table.add_row("ipcrawler 10.10.10.1", "Basic scan of single target")
    usage_table.add_row("ipcrawler -v 10.10.10.1", "Verbose scan (shows progress)")
    usage_table.add_row("ipcrawler -p 80,443 target.com", "Scan specific ports only")
    usage_table.add_row("ipcrawler --timeout 30 10.10.10.0/24", "30min scan of subnet")

    rich_console.print(usage_table)

    # Essential Options
    rich_console.print("\n[bold yellow]🎯 Essential Options:[/bold yellow]")
    essential_table = Table(show_header=False, box=None, padding=(0, 1))
    essential_table.add_column("Option", style="cyan", width=25)
    essential_table.add_column("Description", width=55)

    essential_table.add_row(
        "[dim][[/dim][bold cyan]-v[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--verbose[/bold cyan][dim]][/dim]",
        "Show scan progress [dim](use -v, -vv, -vvv)[/dim]",
    )
    essential_table.add_row(
        "[dim][[/dim][bold cyan]-p[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--ports[/bold cyan][dim]][/dim]",
        "Port specification [dim](default: top 1000)[/dim]\n[yellow]Examples:[/yellow] 80,443 or 1-1000 or T:80,U:53",
    )
    essential_table.add_row(
        "[dim][[/dim][bold cyan]-t[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--target-file[/bold cyan][dim]][/dim]",
        "Read targets from file",
    )
    essential_table.add_row(
        "[dim][[/dim][bold cyan]-o[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--output[/bold cyan][dim]][/dim]",
        "Output directory [dim](default: ./results)[/dim]",
    )
    essential_table.add_row("[dim][[/dim][bold cyan]--timeout[/bold cyan][dim]][/dim]", "Max scan time in minutes")
    essential_table.add_row(
        "[dim][[/dim][bold cyan]--exclude-tags[/bold cyan][dim]][/dim]", "Skip plugin types [dim](e.g. bruteforce)[/dim]"
    )

    rich_console.print(essential_table)

    # Advanced Options
    rich_console.print("\n[bold magenta]⚙️  Advanced Options:[/bold magenta]")
    advanced_table = Table(show_header=False, box=None, padding=(0, 1))
    advanced_table.add_column("Option", style="cyan", width=25)
    advanced_table.add_column("Description", width=55)

    advanced_table.add_row(
        "[dim][[/dim][bold cyan]-m[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--max-scans[/bold cyan][dim]][/dim]",
        "Concurrent scan limit [dim](default: 50)[/dim]",
    )
    advanced_table.add_row(
        "[dim][[/dim][bold cyan]--force-services[/bold cyan][dim]][/dim]",
        "Force service detection\n[yellow]Example:[/yellow] tcp/80/http tcp/443/https",
    )
    advanced_table.add_row(
        "[dim][[/dim][bold cyan]--single-target[/bold cyan][dim]][/dim]", "Don't create target subdirectory"
    )
    advanced_table.add_row("[dim][[/dim][bold cyan]--proxychains[/bold cyan][dim]][/dim]", "Use with proxychains")
    advanced_table.add_row("[dim][[/dim][bold cyan]--nmap[/bold cyan][dim]][/dim]", "Override nmap options")
    advanced_table.add_row("[dim][[/dim][bold cyan]--heartbeat[/bold cyan][dim]][/dim]", "Status update interval in seconds")

    rich_console.print(advanced_table)

    # Port Syntax Examples
    rich_console.print("\n[bold cyan]🔌 Port Syntax Examples:[/bold cyan]")
    port_examples = Table(show_header=False, box=None, padding=(0, 1))
    port_examples.add_column("Syntax", style="yellow", width=20)
    port_examples.add_column("Description", width=40)

    port_examples.add_row("80,443,8080", "Specific ports (TCP)")
    port_examples.add_row("1-1000", "Port range")
    port_examples.add_row("T:22,80", "TCP ports only")
    port_examples.add_row("U:53,161", "UDP ports only")
    port_examples.add_row("B:53", "Both TCP and UDP")
    port_examples.add_row("80,T:22,U:53", "Mixed specification")

    rich_console.print(port_examples)

    # Verbosity Levels
    rich_console.print("\n[bold blue]📢 Verbosity Levels:[/bold blue]")
    verb_table = Table(show_header=False, box=None, padding=(0, 1))
    verb_table.add_column("Level", style="green", width=12)
    verb_table.add_column("Description")

    verb_table.add_row("(none)", "Minimal output - start/end announcements only")
    verb_table.add_row("-v", "Show discovered services and plugin starts")
    verb_table.add_row("-vv", "Show commands executed and pattern matches")
    verb_table.add_row("-vvv", "Maximum - live output from all commands")
    verb_table.add_row("--debug", "Debug output for development and troubleshooting")

    rich_console.print(verb_table)

    # Other Options
    rich_console.print("\n[bold green]🔧 Other Options:[/bold green]")
    other_table = Table(show_header=False, box=None, padding=(0, 1))
    other_table.add_column("Option", style="cyan", width=25)
    other_table.add_column("Description")

    other_table.add_row(
        "[dim][[/dim][bold cyan]-l[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--list[/bold cyan][dim]][/dim]",
        "List available plugins [dim](--list, --list port, --list service)[/dim]",
    )
    other_table.add_row("[dim][[/dim][bold cyan]--version[/bold cyan][dim]][/dim]", "Show version and exit")
    other_table.add_row(
        "[dim][[/dim][bold cyan]-h[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--help[/bold cyan][dim]][/dim]",
        "Show this help message",
    )
    other_table.add_row("[dim][[/dim][bold cyan]--help-all[/bold cyan][dim]][/dim]", "Show complete help with all options")

    rich_console.print(other_table)

    # Footer tips
    rich_console.print(
        Panel.fit(
            "[bold green]💡 Pro Tips:[/bold green]\n"
            + "• Start with [cyan]ipcrawler -v target[/cyan] to see progress\n"
            + "• Check [cyan]results/target/scans/_manual_commands.txt[/cyan] for additional tests\n"
            + "• Use [cyan]--timeout 60[/cyan] for time-limited scans (OSCP exam)\n"
            + "• Run [cyan]ipcrawler --list[/cyan] to see all available plugins\n"
            + "• Use [cyan]--help-all[/cyan] for complete reference with all options",
            border_style="green",
        )
    )


def show_complete_help():
    """Display complete help with all available options"""
    # Header
    rich_console.print(
        Panel.fit(
            "[bold blue]🕷️  ipcrawler[/bold blue] - Complete Reference\n[dim]v" + VERSION + " - All Available Options[/dim]",
            border_style="blue",
        )
    )

    # Note about complete help
    rich_console.print("\n[bold yellow]📖 This is the complete reference showing ALL available options.[/bold yellow]")
    rich_console.print(
        "[dim]For everyday usage, use [cyan]ipcrawler --help[/cyan] which shows the most commonly needed options.[/dim]\n"
    )

    # Show all the same sections as regular help but with complete content
    # Usage
    rich_console.print("[bold green]Basic Usage:[/bold green]")
    usage_table = Table(show_header=False, box=None, padding=(0, 2))
    usage_table.add_column("Command", style="cyan")
    usage_table.add_column("Description")

    usage_table.add_row("ipcrawler 10.10.10.1", "Basic scan of single target")
    usage_table.add_row("ipcrawler -v 10.10.10.1", "Verbose scan (shows progress)")
    usage_table.add_row("ipcrawler -p 80,443 target.com", "Scan specific ports only")
    usage_table.add_row("ipcrawler --timeout 30 10.10.10.0/24", "30min scan of subnet")

    rich_console.print(usage_table)

    # All the sections from the regular help
    # Essential Options
    rich_console.print("\n[bold yellow]🎯 Essential Options:[/bold yellow]")
    essential_table = Table(show_header=False, box=None, padding=(0, 1))
    essential_table.add_column("Option", style="cyan", width=25)
    essential_table.add_column("Description", width=55)

    essential_table.add_row(
        "[dim][[/dim][bold cyan]-v[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--verbose[/bold cyan][dim]][/dim]",
        "Show scan progress [dim](use -v, -vv, -vvv)[/dim]",
    )
    essential_table.add_row(
        "[dim][[/dim][bold cyan]-p[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--ports[/bold cyan][dim]][/dim]",
        "Port specification [dim](default: top 1000)[/dim]\n[yellow]Examples:[/yellow] 80,443 or 1-1000 or T:80,U:53",
    )
    essential_table.add_row(
        "[dim][[/dim][bold cyan]-t[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--target-file[/bold cyan][dim]][/dim]",
        "Read targets from file",
    )
    essential_table.add_row(
        "[dim][[/dim][bold cyan]-o[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--output[/bold cyan][dim]][/dim]",
        "Output directory [dim](default: ./results)[/dim]",
    )
    essential_table.add_row("[dim][[/dim][bold cyan]--timeout[/bold cyan][dim]][/dim]", "Max scan time in minutes")
    essential_table.add_row(
        "[dim][[/dim][bold cyan]--exclude-tags[/bold cyan][dim]][/dim]", "Skip plugin types [dim](e.g. bruteforce)[/dim]"
    )

    rich_console.print(essential_table)

    # Advanced Options
    rich_console.print("\n[bold magenta]⚙️  Advanced Options:[/bold magenta]")
    advanced_table = Table(show_header=False, box=None, padding=(0, 1))
    advanced_table.add_column("Option", style="cyan", width=25)
    advanced_table.add_column("Description", width=55)

    advanced_table.add_row(
        "[dim][[/dim][bold cyan]-m[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--max-scans[/bold cyan][dim]][/dim]",
        "Concurrent scan limit [dim](default: 50)[/dim]",
    )
    advanced_table.add_row(
        "[dim][[/dim][bold cyan]--force-services[/bold cyan][dim]][/dim]",
        "Force service detection\n[yellow]Example:[/yellow] tcp/80/http tcp/443/https",
    )
    advanced_table.add_row(
        "[dim][[/dim][bold cyan]--single-target[/bold cyan][dim]][/dim]", "Don't create target subdirectory"
    )
    advanced_table.add_row("[dim][[/dim][bold cyan]--proxychains[/bold cyan][dim]][/dim]", "Use with proxychains")
    advanced_table.add_row("[dim][[/dim][bold cyan]--nmap[/bold cyan][dim]][/dim]", "Override nmap options")
    advanced_table.add_row("[dim][[/dim][bold cyan]--heartbeat[/bold cyan][dim]][/dim]", "Status update interval in seconds")

    rich_console.print(advanced_table)

    # Expert Options
    rich_console.print("\n[bold magenta]🎛️  Expert Options:[/bold magenta]")
    expert_table = Table(show_header=False, box=None, padding=(0, 1))
    expert_table.add_column("Option", style="cyan", width=25)
    expert_table.add_column("Description", width=55)

    expert_table.add_row(
        "[dim][[/dim][bold cyan]--tags[/bold cyan][dim]][/dim]",
        "Plugin tag selection [dim](default: default)[/dim]\n[yellow]Example:[/yellow] safe+quick,bruteforce",
    )
    expert_table.add_row(
        "[dim][[/dim][bold cyan]--port-scans[/bold cyan][dim]][/dim]",
        "Override port scan plugins [dim](comma separated)[/dim]",
    )
    expert_table.add_row(
        "[dim][[/dim][bold cyan]--service-scans[/bold cyan][dim]][/dim]",
        "Override service scan plugins [dim](comma separated)[/dim]",
    )
    expert_table.add_row(
        "[dim][[/dim][bold cyan]--reports[/bold cyan][dim]][/dim]", "Override report plugins [dim](comma separated)[/dim]"
    )
    expert_table.add_row("[dim][[/dim][bold cyan]--target-timeout[/bold cyan][dim]][/dim]", "Per-target timeout in minutes")
    expert_table.add_row(
        "[dim][[/dim][bold cyan]--max-port-scans[/bold cyan][dim]][/dim]",
        "Concurrent port scan limit [dim](default: 10)[/dim]",
    )

    rich_console.print(expert_table)

    # System Options
    rich_console.print("\n[bold yellow]⚙️  System Options:[/bold yellow]")
    system_table = Table(show_header=False, box=None, padding=(0, 1))
    system_table.add_column("Option", style="cyan", width=25)
    system_table.add_column("Description", width=55)

    system_table.add_row(
        "[dim][[/dim][bold cyan]--only-scans-dir[/bold cyan][dim]][/dim]",
        "Only create scans directory [dim](no exploit/loot/report)[/dim]",
    )
    system_table.add_row(
        "[dim][[/dim][bold cyan]--no-port-dirs[/bold cyan][dim]][/dim]",
        "Don't create port directories [dim](tcp80, udp53)[/dim]",
    )
    system_table.add_row("[dim][[/dim][bold cyan]--nmap-append[/bold cyan][dim]][/dim]", "Append to default nmap options")
    system_table.add_row("[dim][[/dim][bold cyan]--disable-sanity-checks[/bold cyan][dim]][/dim]", "Skip sanity checks")
    system_table.add_row(
        "[dim][[/dim][bold cyan]--disable-keyboard-control[/bold cyan][dim]][/dim]",
        "Disable keyboard controls [dim](SSH/Docker)[/dim]",
    )
    system_table.add_row("[dim][[/dim][bold cyan]--accessible[/bold cyan][dim]][/dim]", "Screenreader accessibility mode")

    rich_console.print(system_table)

    # Configuration Options  
    rich_console.print("\n[bold blue]📁 Configuration Options:[/bold blue]")
    config_table = Table(show_header=False, box=None, padding=(0, 1))
    config_table.add_column("Option", style="cyan", width=25)
    config_table.add_column("Description", width=55)

    config_table.add_row(
        "[dim][[/dim][bold cyan]-c[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--config[/bold cyan][dim]][/dim]",
        "Config file location [dim](config.toml)[/dim]",
    )
    config_table.add_row(
        "[dim][[/dim][bold cyan]-g[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--global-file[/bold cyan][dim]][/dim]",
        "Global file location [dim](global.toml)[/dim]",
    )
    config_table.add_row("[dim][[/dim][bold cyan]--plugins-dir[/bold cyan][dim]][/dim]", "Custom plugins directory")
    config_table.add_row("[dim][[/dim][bold cyan]--add-plugins-dir[/bold cyan][dim]][/dim]", "Additional plugins directory")
    config_table.add_row("[dim][[/dim][bold cyan]--ignore-plugin-checks[/bold cyan][dim]][/dim]", "Ignore plugin errors")

    rich_console.print(config_table)

    # Plugin Control Options
    rich_console.print("\n[bold red]🔌 Plugin Control Options:[/bold red]")
    plugin_table = Table(show_header=False, box=None, padding=(0, 1))
    plugin_table.add_column("Option", style="cyan", width=25)
    plugin_table.add_column("Description", width=55)

    plugin_table.add_row(
        "[dim][[/dim][bold cyan]-mpti[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--max-plugin-target-instances[/bold cyan][dim]][/dim]",
        "Plugin instance limits per target\n[yellow]Example:[/yellow] nmap-http:2 dirbuster:1",
    )
    plugin_table.add_row(
        "[dim][[/dim][bold cyan]-mpgi[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--max-plugin-global-instances[/bold cyan][dim]][/dim]",
        "Global plugin instance limits\n[yellow]Example:[/yellow] nmap-http:2 dirbuster:1",
    )

    rich_console.print(plugin_table)

    # Port Syntax Examples
    rich_console.print("\n[bold cyan]🔌 Port Syntax Examples:[/bold cyan]")
    port_examples = Table(show_header=False, box=None, padding=(0, 1))
    port_examples.add_column("Syntax", style="yellow", width=20)
    port_examples.add_column("Description", width=40)

    port_examples.add_row("80,443,8080", "Specific ports (TCP)")
    port_examples.add_row("1-1000", "Port range")
    port_examples.add_row("T:22,80", "TCP ports only")
    port_examples.add_row("U:53,161", "UDP ports only")
    port_examples.add_row("B:53", "Both TCP and UDP")
    port_examples.add_row("80,T:22,U:53", "Mixed specification")

    rich_console.print(port_examples)

    # Advanced Tag Examples
    rich_console.print("\n[bold red]🚨 Advanced Tag Examples:[/bold red]")
    tag_examples = Table(show_header=False, box=None, padding=(0, 1))
    tag_examples.add_column("Tag Expression", style="yellow", width=30)
    tag_examples.add_column("Description", width=50)

    tag_examples.add_row("default", "Run default plugins only")
    tag_examples.add_row("safe+quick", "Run plugins tagged as both safe AND quick")
    tag_examples.add_row("safe,bruteforce", "Run plugins tagged as safe OR bruteforce")
    tag_examples.add_row("http+safe,smb", "Run (HTTP AND safe) OR SMB plugins")

    rich_console.print(tag_examples)

    # Verbosity Levels
    rich_console.print("\n[bold blue]📢 Verbosity Levels:[/bold blue]")
    verb_table = Table(show_header=False, box=None, padding=(0, 1))
    verb_table.add_column("Level", style="green", width=12)
    verb_table.add_column("Description")

    verb_table.add_row("(none)", "Minimal output - start/end announcements only")
    verb_table.add_row("-v", "Show discovered services and plugin starts")
    verb_table.add_row("-vv", "Show commands executed and pattern matches")
    verb_table.add_row("-vvv", "Maximum - live output from all commands")
    verb_table.add_row("--debug", "Debug output for development and troubleshooting")

    rich_console.print(verb_table)

    # Other Options
    rich_console.print("\n[bold green]🔧 Other Options:[/bold green]")
    other_table = Table(show_header=False, box=None, padding=(0, 1))
    other_table.add_column("Option", style="cyan", width=25)
    other_table.add_column("Description")

    other_table.add_row(
        "[dim][[/dim][bold cyan]-l[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--list[/bold cyan][dim]][/dim]",
        "List available plugins [dim](--list, --list port, --list service)[/dim]",
    )
    other_table.add_row("[dim][[/dim][bold cyan]--version[/bold cyan][dim]][/dim]", "Show version and exit")
    other_table.add_row(
        "[dim][[/dim][bold cyan]-h[/bold cyan][dim]][/dim] [dim][[/dim][bold cyan]--help[/bold cyan][dim]][/dim]",
        "Show essential help message",
    )
    other_table.add_row("[dim][[/dim][bold cyan]--help-all[/bold cyan][dim]][/dim]", "Show this complete reference")

    rich_console.print(other_table)

    # Complete footer
    rich_console.print(
        Panel.fit(
            "[bold yellow]📚 Complete Reference:[/bold yellow]\n"
            + "• This shows ALL available options for power users\n"
            + "• Most users only need the basic options shown in [cyan]--help[/cyan]\n"
            + "• For plugin-specific options, check the global.toml file\n"
            + "• Advanced users can create custom plugins in the plugins directory",
            border_style="yellow",
        )
    )


def show_fallback_help(parser):
    """Fallback help when Rich is not available"""
    print("🕷️  ipcrawler v" + VERSION + " - Network Reconnaissance Tool")
    print("=" * 60)
    print()
    print("USAGE:")
    print("  ipcrawler [options] target1 [target2 ...]")
    print()
    print("EXAMPLES:")
    print("  ipcrawler -v 10.10.10.1                    # Verbose scan")
    print("  ipcrawler -p 80,443 target.com             # Specific ports")
    print("  ipcrawler --timeout 30 10.10.10.0/24      # Time-limited")
    print()
    print("ESSENTIAL OPTIONS:")
    print("  -v, --verbose         Show scan progress (-v, -vv, -vvv)")
    print("  --debug               Debug output for development")
    print("  -p, --ports          Port specification (default: top 1000)")
    print("                       Examples: 80,443 or 1-1000 or T:80,U:53")
    print("  -t, --target-file    Read targets from file")
    print("  -o, --output         Output directory (default: ./results)")
    print("  --timeout           Max scan time in minutes")
    print("  --exclude-tags      Skip plugin types (e.g. bruteforce)")
    print()
    print("For complete options, install Rich: pip install rich")
    print("Then run: ipcrawler --help")
    print()

    # Show standard argparse help as well
    parser.print_help()


def merge_config_preserving_user_changes(source_file, user_file):
    """
    Merge source config with user config, preserving user customizations
    Returns True if user file was updated, False if no changes needed
    """
    try:
        import toml

        # Load source config (new defaults)
        with open(source_file, "r") as f:
            source_config = toml.load(f)

        # Load existing user config if it exists
        user_config = {}
        if os.path.exists(user_file):
            with open(user_file, "r") as f:
                user_config = toml.load(f)

        # Check if merge is needed (compare important settings)
        needs_update = False

        # Check for new top-level keys in source
        for key in source_config:
            if key not in user_config:
                needs_update = True
                break

        # For development: always use source config if we're in a git repo
        script_dir = os.path.dirname(os.path.realpath(__file__))
        if os.path.exists(os.path.join(script_dir, "..", ".git")):
            # In development - always use source files
            debug("Development mode detected - using source config files")
            shutil.copy2(source_file, user_file)
            return True

        if not needs_update:
            return False

        # Preserve user customizations while adding new defaults
        merged_config = source_config.copy()

        # Keep user's custom values for key settings
        preserved_keys = ["tags", "max_scans", "verbose", "nmap_append", "timeout"]
        for key in preserved_keys:
            if key in user_config:
                merged_config[key] = user_config[key]

        # Preserve user's plugin-specific configurations
        for section_name, section_data in user_config.items():
            if isinstance(section_data, dict) and section_name not in ["vhost_discovery"]:
                # Keep user's plugin configurations
                if section_name not in merged_config:
                    merged_config[section_name] = {}
                merged_config[section_name].update(section_data)

        # Write merged config
        with open(user_file, "w") as f:
            toml.dump(merged_config, f)

        return True

    except Exception as e:
        warn(f"Config merge failed: {e}. Using source config as fallback.")
        shutil.copy2(source_file, user_file)
        return True


def setup_config_directories():
    """Setup config and data directories with smart caching and updates"""
    source_dir = os.path.dirname(os.path.realpath(__file__))

    # Setup config directory
    if not os.path.exists(config["config_dir"]):
        info("Creating ipcrawler config directory...")
        os.makedirs(config["config_dir"], exist_ok=True)
        shutil.copy2(os.path.join(source_dir, "config.toml"), os.path.join(config["config_dir"], "config.toml"))
        shutil.copy2(os.path.join(source_dir, "global.toml"), os.path.join(config["config_dir"], "global.toml"))
        open(os.path.join(config["config_dir"], "VERSION-" + VERSION), "a").close()
    else:
        # Update config files intelligently
        config_updated = False

        # Update config.toml with user preservation
        source_config = os.path.join(source_dir, "config.toml")
        user_config = os.path.join(config["config_dir"], "config.toml")
        if merge_config_preserving_user_changes(source_config, user_config):
            config_updated = True

        # Update global.toml (usually safe to overwrite)
        source_global = os.path.join(source_dir, "global.toml")
        user_global = os.path.join(config["config_dir"], "global.toml")
        if not os.path.exists(user_global) or os.path.getmtime(source_global) > os.path.getmtime(user_global):
            shutil.copy2(source_global, user_global)
            config_updated = True

        # Update version marker
        version_file = os.path.join(config["config_dir"], "VERSION-" + VERSION)
        if not os.path.exists(version_file):
            # Clean old version files
            for f in os.listdir(config["config_dir"]):
                if f.startswith("VERSION-"):
                    os.remove(os.path.join(config["config_dir"], f))
            open(version_file, "a").close()
            if config_updated:
                info("Configuration updated to version " + VERSION)

    # Setup data directory (plugins and wordlists)
    if not os.path.exists(config["data_dir"]):
        info("Creating ipcrawler data directory...")
        os.makedirs(config["data_dir"], exist_ok=True)
        shutil.copytree(os.path.join(source_dir, "default-plugins"), os.path.join(config["data_dir"], "plugins"))
        shutil.copytree(os.path.join(source_dir, "wordlists"), os.path.join(config["data_dir"], "wordlists"))
        open(os.path.join(config["data_dir"], "VERSION-" + VERSION), "a").close()
    else:
        # Update plugins if needed
        if not os.path.exists(os.path.join(config["data_dir"], "plugins")):
            shutil.copytree(os.path.join(source_dir, "default-plugins"), os.path.join(config["data_dir"], "plugins"))
        if not os.path.exists(os.path.join(config["data_dir"], "wordlists")):
            shutil.copytree(os.path.join(source_dir, "wordlists"), os.path.join(config["data_dir"], "wordlists"))

        # Update version marker
        version_file = os.path.join(config["data_dir"], "VERSION-" + VERSION)
        if not os.path.exists(version_file):
            # Clean old version files
            for f in os.listdir(config["data_dir"]):
                if f.startswith("VERSION-"):
                    os.remove(os.path.join(config["data_dir"], f))
            open(version_file, "a").close()


# Call the new setup function
setup_config_directories()

# Saves current terminal settings so we can restore them.
terminal_settings = None

ipcrawler = ipcrawler()


def calculate_elapsed_time(start_time, short=False):
    elapsed_seconds = round(time.time() - start_time)

    m, s = divmod(elapsed_seconds, 60)
    h, m = divmod(m, 60)

    elapsed_time = []
    if short:
        elapsed_time.append(str(h).zfill(2))
    else:
        if h == 1:
            elapsed_time.append(str(h) + " hour")
        elif h > 1:
            elapsed_time.append(str(h) + " hours")

    if short:
        elapsed_time.append(str(m).zfill(2))
    else:
        if m == 1:
            elapsed_time.append(str(m) + " minute")
        elif m > 1:
            elapsed_time.append(str(m) + " minutes")

    if short:
        elapsed_time.append(str(s).zfill(2))
    else:
        if s == 1:
            elapsed_time.append(str(s) + " second")
        elif s > 1:
            elapsed_time.append(str(s) + " seconds")
        else:
            elapsed_time.append("less than a second")

    if short:
        return ":".join(elapsed_time)
    else:
        return ", ".join(elapsed_time)


# sig and frame args are only present so the function
# works with signal.signal() and handles Ctrl-C.
# They are not used for any other purpose.
def cancel_all_tasks(sig, frame):
    for task in asyncio.all_tasks():
        task.cancel()

    processes = []

    for target in ipcrawler.scanning_targets:
        for process_list in target.running_tasks.values():
            for process_dict in process_list["processes"]:
                try:
                    parent = psutil.Process(process_dict["process"].pid)
                    processes.extend(parent.children(recursive=True))
                    processes.append(parent)
                except psutil.NoSuchProcess:
                    pass

    for process in processes:
        try:
            process.send_signal(signal.SIGKILL)
        except psutil.NoSuchProcess:  # Will get raised if the process finishes before we get to killing it.
            pass

    _, alive = psutil.wait_procs(processes, timeout=10)
    if len(alive) > 0:
        error(
            "The following process IDs could not be killed: "
            + ", ".join([str(x.pid) for x in sorted(alive, key=lambda x: x.pid)])
        )

    if not config["disable_keyboard_control"]:
        # Restore original terminal settings.
        if terminal_settings is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, terminal_settings)


async def start_heartbeat(target, period=60):
    while True:
        await asyncio.sleep(period)
        async with target.lock:
            # Clean up completed tasks that may have been missed
            completed_tasks = []
            for tag, task in list(target.running_tasks.items()):  # Use list() to avoid dict size change during iteration
                try:
                    # Check if all processes are completed
                    all_processes_done = True
                    active_processes = 0

                    for process_dict in task["processes"]:
                        if process_dict["process"].returncode is None:
                            all_processes_done = False
                            active_processes += 1

                    # If no processes or all processes are done, mark for cleanup
                    if not task["processes"] or all_processes_done:
                        # Check if this task has been running for a long time without processes
                        elapsed = time.time() - task["start"]
                        if elapsed > 60:  # 1 minute without active processes (reduced from 3)
                            completed_tasks.append(tag)
                    # Also clean up tasks that have been stuck with 0 active processes for too long
                    elif active_processes == 0:
                        elapsed = time.time() - task["start"]
                        if elapsed > 30:  # 30 seconds with no active processes (reduced from 2 minutes)
                            completed_tasks.append(tag)
                except Exception:
                    # If any error accessing task data, mark for cleanup
                    completed_tasks.append(tag)

            # Remove completed tasks and their progress bars
            for tag in completed_tasks:
                if tag in target.running_tasks:
                    # Complete the progress bar if it exists
                    try:
                        if "progress_task" in target.running_tasks[tag] and target.running_tasks[tag]["progress_task"]:
                            progress_manager.complete_task(target.running_tasks[tag]["progress_task"])
                    except Exception:
                        pass  # Ignore errors in progress cleanup
                    # Remove from live loader as well
                    complete_scan_in_live_loader(target.address, tag)
                    target.running_tasks.pop(tag, None)
                    warn(f"Cleaned up stale task: {tag}", verbosity=2)

            # Update live loader with current running tasks
            update_live_loader_from_targets([target])

            count = len(target.running_tasks)

            if config["verbose"] >= 1:
                tasks_list = []
                for tag, task in target.running_tasks.items():
                    task_str = tag

                    if config["verbose"] >= 2:
                        processes = []
                        for process_dict in task["processes"]:
                            if process_dict["process"].returncode is None:
                                processes.append(str(process_dict["process"].pid))
                                try:
                                    for child in psutil.Process(process_dict["process"].pid).children(recursive=True):
                                        processes.append(str(child.pid))
                                except psutil.NoSuchProcess:
                                    pass

                        if processes:
                            task_str += " (PID" + ("s" if len(processes) > 1 else "") + ": " + ", ".join(processes) + ")"

                    tasks_list.append(task_str)

                tasks_list = ": {bblue}" + ", ".join(tasks_list) + "{rst}"
            else:
                tasks_list = ""

            current_time = datetime.now().strftime("%H:%M:%S")

            if count > 1:
                info(
                    "{bgreen}"
                    + current_time
                    + "{rst} - There are {byellow}"
                    + str(count)
                    + "{rst} scans still running against {byellow}"
                    + target.address
                    + "{rst}"
                    + tasks_list
                )
            elif count == 1:
                info(
                    "{bgreen}"
                    + current_time
                    + "{rst} - There is {byellow}1{rst} scan still running against {byellow}"
                    + target.address
                    + "{rst}"
                    + tasks_list
                )


async def keyboard():
    input = ""
    while True:
        if select.select([sys.stdin], [], [], 0.1)[0]:
            input += sys.stdin.buffer.read1(-1).decode("utf8")
            while input != "":
                if len(input) >= 3:
                    if input[:3] == "\x1b[A":
                        input = ""
                        if config["verbose"] == 3:
                            info("Verbosity is already at the highest level.")
                        else:
                            config["verbose"] += 1
                            info("Verbosity increased to " + str(config["verbose"]))
                    elif input[:3] == "\x1b[B":
                        input = ""
                        if config["verbose"] == 0:
                            info("Verbosity is already at the lowest level.")
                        else:
                            config["verbose"] -= 1
                            info("Verbosity decreased to " + str(config["verbose"]))
                    else:
                        if input[0] != "s":
                            input = input[1:]

                if len(input) > 0 and input[0] == "s":
                    input = input[1:]
                    for target in ipcrawler.scanning_targets:
                        async with target.lock:
                            count = len(target.running_tasks)

                            tasks_list = []
                            if config["verbose"] >= 1:
                                for tag, task in target.running_tasks.items():
                                    elapsed_time = calculate_elapsed_time(task["start"], short=True)

                                    task_str = "{bblue}" + tag + "{rst}" + " (elapsed: " + elapsed_time + ")"

                                    if config["verbose"] >= 2:
                                        processes = []
                                        for process_dict in task["processes"]:
                                            if process_dict["process"].returncode is None:
                                                processes.append(str(process_dict["process"].pid))
                                                try:
                                                    for child in psutil.Process(process_dict["process"].pid).children(
                                                        recursive=True
                                                    ):
                                                        processes.append(str(child.pid))
                                                except psutil.NoSuchProcess:
                                                    pass

                                        if processes:
                                            task_str += (
                                                " (PID"
                                                + ("s" if len(processes) > 1 else "")
                                                + ": "
                                                + ", ".join(processes)
                                                + ")"
                                            )

                                    tasks_list.append(task_str)

                                tasks_list = ":\n    " + "\n    ".join(tasks_list)
                            else:
                                tasks_list = ""

                            current_time = datetime.now().strftime("%H:%M:%S")

                            if count > 1:
                                info(
                                    "{bgreen}"
                                    + current_time
                                    + "{rst} - There are {byellow}"
                                    + str(count)
                                    + "{rst} scans still running against {byellow}"
                                    + target.address
                                    + "{rst}"
                                    + tasks_list
                                )
                            elif count == 1:
                                info(
                                    "{bgreen}"
                                    + current_time
                                    + "{rst} - There is {byellow}1{rst} scan still running against {byellow}"
                                    + target.address
                                    + "{rst}"
                                    + tasks_list
                                )
                else:
                    input = input[1:]
        await asyncio.sleep(0.1)


async def get_semaphore(ipcrawler):
    semaphore = ipcrawler.service_scan_semaphore
    while True:
        # If service scan semaphore is locked, see if we can use port scan semaphore.
        if semaphore.locked():
            if semaphore != ipcrawler.port_scan_semaphore:  # This will be true unless user sets max_scans == max_port_scans
                port_scan_task_count = 0
                for target in ipcrawler.scanning_targets:
                    for process_list in target.running_tasks.values():
                        if issubclass(process_list["plugin"].__class__, PortScan):
                            port_scan_task_count += 1

                if (
                    not ipcrawler.pending_targets and (config["max_port_scans"] - port_scan_task_count) >= 1
                ):  # If no more targets, and we have room, use port scan semaphore.
                    if ipcrawler.port_scan_semaphore.locked():
                        await asyncio.sleep(1)
                        continue
                    semaphore = ipcrawler.port_scan_semaphore
                    break
                else:  # Do some math to see if we can use the port scan semaphore.
                    if (
                        config["max_port_scans"]
                        - (port_scan_task_count + (len(ipcrawler.pending_targets) * config["port_scan_plugin_count"]))
                    ) >= 1:
                        if ipcrawler.port_scan_semaphore.locked():
                            await asyncio.sleep(1)
                            continue
                        semaphore = ipcrawler.port_scan_semaphore
                        break
                    else:
                        await asyncio.sleep(1)
            else:
                break
        else:
            break
    return semaphore


async def port_scan(plugin, target):
    if config["ports"]:
        if config["ports"]["tcp"] or config["ports"]["udp"]:
            target.ports = {"tcp": None, "udp": None}
            if config["ports"]["tcp"]:
                target.ports["tcp"] = ",".join(config["ports"]["tcp"])
            if config["ports"]["udp"]:
                target.ports["udp"] = ",".join(config["ports"]["udp"])
            if plugin.specific_ports is False:
                warn(
                    "Port scan {bblue}"
                    + plugin.name
                    + " {green}("
                    + plugin.slug
                    + "){rst} cannot be used to scan specific ports, and --ports was used. Skipping.",
                    verbosity=2,
                )
                return {"type": "port", "plugin": plugin, "result": []}
            else:
                if plugin.type == "tcp" and not config["ports"]["tcp"]:
                    warn(
                        "Port scan {bblue}"
                        + plugin.name
                        + " {green}("
                        + plugin.slug
                        + "){rst} is a TCP port scan but no TCP ports were set using --ports. Skipping",
                        verbosity=2,
                    )
                    return {"type": "port", "plugin": plugin, "result": []}
                elif plugin.type == "udp" and not config["ports"]["udp"]:
                    warn(
                        "Port scan {bblue}"
                        + plugin.name
                        + " {green}("
                        + plugin.slug
                        + "){rst} is a UDP port scan but no UDP ports were set using --ports. Skipping",
                        verbosity=2,
                    )
                    return {"type": "port", "plugin": plugin, "result": []}

    async with target.ipcrawler.port_scan_semaphore:
        info(
            "Port scan {bblue}"
            + plugin.name
            + " {green}("
            + plugin.slug
            + "){rst} running against {byellow}"
            + target.address
            + "{rst}",
            verbosity=1,
        )

        # Add progress bar for port scans (with deduplication key)
        task_key = f"port_scan_{plugin.slug}_{target.address}"
        task_id = progress_manager.add_task(f"🔍 Scanning {plugin.name} on {target.address}", total=100, task_key=task_key)

        # Start progress simulation (more realistic estimate: 60 seconds for port scan)
        progress_manager.simulate_progress(task_id, 60)

        start_time = time.time()

        async with target.lock:
            target.running_tasks[plugin.slug] = {
                "plugin": plugin,
                "processes": [],
                "start": start_time,
                "progress_task": task_id,
            }

        # Add to live loader
        add_scan_to_live_loader(target.address, plugin.slug, plugin.name)

        try:
            result = await plugin.run(target)
        except Exception as ex:
            # Clean up task on exception
            if task_id:
                progress_manager.complete_task(task_id)
            async with target.lock:
                if plugin.slug in target.running_tasks:
                    target.running_tasks.pop(plugin.slug, None)

            exc_type, exc_value, exc_tb = sys.exc_info()
            error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
            raise Exception(
                cprint(
                    "Error: Port scan {bblue}"
                    + plugin.name
                    + " {green}("
                    + plugin.slug
                    + "){rst} running against {byellow}"
                    + target.address
                    + "{rst} produced an exception:\n\n"
                    + error_text,
                    color=Fore.RED,
                    char="!",
                    printmsg=False,
                )
            )

        for process_dict in target.running_tasks[plugin.slug]["processes"]:
            if process_dict["process"].returncode is None:
                warn(
                    "A process was left running after port scan {bblue}"
                    + plugin.name
                    + " {green}("
                    + plugin.slug
                    + "){rst} against {byellow}"
                    + target.address
                    + "{rst} finished. Please ensure non-blocking processes are awaited before the run coroutine finishes. Awaiting now.",
                    verbosity=2,
                )
                await process_dict["process"].wait()

            if process_dict["process"].returncode != 0:
                errors = []
                while True:
                    line = await process_dict["stderr"].readline()
                    if line is not None:
                        errors.append(line + "\n")
                    else:
                        break
                error(
                    "Port scan {bblue}"
                    + plugin.name
                    + " {green}("
                    + plugin.slug
                    + "){rst} ran a command against {byellow}"
                    + target.address
                    + "{rst} which returned a non-zero exit code ("
                    + str(process_dict["process"].returncode)
                    + "). Check "
                    + target.scandir
                    + "/_errors.log for more details.",
                    verbosity=2,
                )
                async with target.lock:
                    with open(os.path.join(target.scandir, "_errors.log"), "a") as file:
                        file.writelines(
                            "[*] Port scan "
                            + plugin.name
                            + " ("
                            + plugin.slug
                            + ") ran a command which returned a non-zero exit code ("
                            + str(process_dict["process"].returncode)
                            + ").\n"
                        )
                        file.writelines("[-] Command: " + process_dict["cmd"] + "\n")
                        if errors:
                            file.writelines(["[-] Error Output:\n"] + errors + ["\n"])
                        else:
                            file.writelines("\n")

        elapsed_time = calculate_elapsed_time(start_time)

        # Complete progress bar and cleanup tasks - ALWAYS do this
        if task_id:
            try:
                progress_manager.complete_task(task_id)
                debug(f"Port scan progress task {task_id} completed successfully", verbosity=3)
            except Exception as e:
                debug(f"Error completing port scan progress task {task_id}: {e}", verbosity=3)

        async with target.lock:
            # Ensure task is removed from running_tasks
            if plugin.slug in target.running_tasks:
                try:
                    target.running_tasks.pop(plugin.slug, None)
                    debug(f"Port scan task {plugin.slug} removed from running_tasks", verbosity=3)
                except Exception as e:
                    debug(f"Error removing port scan task {plugin.slug} from running_tasks: {e}", verbosity=3)

        # Remove from live loader
        complete_scan_in_live_loader(target.address, plugin.slug)

        info(
            "Port scan {bblue}"
            + plugin.name
            + " {green}("
            + plugin.slug
            + "){rst} against {byellow}"
            + target.address
            + "{rst} finished in "
            + elapsed_time,
            verbosity=2,
        )
        return {"type": "port", "plugin": plugin, "result": result}


def is_expected_error(cmd, returncode):
    """
    Check if a command error is expected and should be ignored.
    
    Args:
        cmd: The command that was executed
        returncode: The return code from the process
        
    Returns:
        bool: True if the error is expected and should be ignored
    """
    # Handle curl commands with common exit codes
    if cmd.startswith("curl"):
        # Exit code 22: HTTP page not retrieved (404, 403, etc.)
        # Exit code 56: Failure in receiving network data
        # Exit code 7: Failed to connect to host
        # Exit code 28: Operation timeout
        if returncode in [7, 22, 28, 56]:
            return True
    
    # Handle whatweb commands - they often return 1 for various reasons but still provide useful output
    if "whatweb" in cmd:
        # whatweb exit code 1 is often just warnings or non-critical issues
        if returncode == 1:
            return True
    
    # Add other expected error patterns here as needed
    return False


async def service_scan(plugin, service):
    semaphore = service.target.ipcrawler.service_scan_semaphore

    if not config["force_services"]:
        semaphore = await get_semaphore(service.target.ipcrawler)

    plugin_pending = True

    while plugin_pending:
        global_plugin_count = 0
        target_plugin_count = 0

        if plugin.max_global_instances and plugin.max_global_instances > 0:
            async with service.target.ipcrawler.lock:
                # Count currently running plugin instances.
                for target in service.target.ipcrawler.scanning_targets:
                    for task in target.running_tasks.values():
                        if plugin == task["plugin"]:
                            global_plugin_count += 1
                            if global_plugin_count >= plugin.max_global_instances:
                                break
                    if global_plugin_count >= plugin.max_global_instances:
                        break
            if global_plugin_count >= plugin.max_global_instances:
                await asyncio.sleep(1)
                continue

        if plugin.max_target_instances and plugin.max_target_instances > 0:
            async with service.target.lock:
                # Count currently running plugin instances.
                for task in service.target.running_tasks.values():
                    if plugin == task["plugin"]:
                        target_plugin_count += 1
                        if target_plugin_count >= plugin.max_target_instances:
                            break
            if target_plugin_count >= plugin.max_target_instances:
                await asyncio.sleep(1)
                continue

        # If we get here, we can run the plugin.
        plugin_pending = False

        async with semaphore:
            # Create variables for fformat references.
            address = service.target.address
            addressv6 = service.target.address
            ipaddress = service.target.ip
            ipaddressv6 = service.target.ip
            scandir = service.target.scandir
            protocol = service.protocol
            port = service.port
            name = service.name

            if not config["no_port_dirs"]:
                scandir = os.path.join(scandir, protocol + str(port))
                os.makedirs(scandir, exist_ok=True)
                os.makedirs(os.path.join(scandir, "xml"), exist_ok=True)

            # Special cases for HTTP.
            http_scheme = "https" if "https" in service.name or service.secure is True else "http"

            nmap_extra = service.target.ipcrawler.args.nmap
            if service.target.ipcrawler.args.nmap_append:
                nmap_extra += " " + service.target.ipcrawler.args.nmap_append

            if protocol == "udp":
                nmap_extra += " -sU"

            if service.target.ipversion == "IPv6":
                nmap_extra += " -6"
                if addressv6 == service.target.ip:
                    addressv6 = "[" + addressv6 + "]"
                ipaddressv6 = "[" + ipaddressv6 + "]"

            if config["proxychains"] and protocol == "tcp":
                nmap_extra += " -sT"

            tag = service.tag() + "/" + plugin.slug

            info(
                "Service scan {bblue}"
                + plugin.name
                + " {green}("
                + tag
                + "){rst} running against {byellow}"
                + service.target.address
                + "{rst}",
                verbosity=1,
            )

            # Add progress bar for service scans (with deduplication key)
            task_key = f"service_scan_{plugin.slug}_{service.target.address}_{service.port}"
            task_id = progress_manager.add_task(
                f"🔧 {plugin.name} on {service.target.address}:{service.port}", total=100, task_key=task_key
            )

            # Start progress simulation (estimate varies by service type)
            # Directory busters and web scanners take longer
            if any(tool in plugin.slug.lower() for tool in ["nikto", "gobuster", "dirb", "dirbuster", "feroxbuster", "ffuf", "dirsearch"]):
                estimated_duration = 180  # 3 minutes for directory/web scans
            elif "nmap" in plugin.slug.lower():
                estimated_duration = 120  # 2 minutes for nmap scans  
            elif any(tool in plugin.slug.lower() for tool in ["lfi", "xss", "sqli"]):
                estimated_duration = 150  # 2.5 minutes for vulnerability testing
            else:
                estimated_duration = 60  # 1 minute for other scans
            progress_manager.simulate_progress(task_id, estimated_duration)

            start_time = time.time()

            async with service.target.lock:
                service.target.running_tasks[tag] = {
                    "plugin": plugin,
                    "processes": [],
                    "start": start_time,
                    "progress_task": task_id,
                }

            # Add to live loader
            add_scan_to_live_loader(service.target.address, tag, plugin.name)

            try:
                result = await plugin.run(service)
            except Exception as ex:
                # Clean up task on exception
                if task_id:
                    progress_manager.complete_task(task_id)
                async with service.target.lock:
                    if tag in service.target.running_tasks:
                        service.target.running_tasks.pop(tag, None)

                exc_type, exc_value, exc_tb = sys.exc_info()
                error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
                raise Exception(
                    cprint(
                        "Error: Service scan {bblue}"
                        + plugin.name
                        + " {green}("
                        + tag
                        + "){rst} running against {byellow}"
                        + service.target.address
                        + "{rst} produced an exception:\n\n"
                        + error_text,
                        color=Fore.RED,
                        char="!",
                        printmsg=False,
                    )
                )

            for process_dict in service.target.running_tasks[tag]["processes"]:
                if process_dict["process"].returncode is None:
                    warn(
                        "A process was left running after service scan {bblue}"
                        + plugin.name
                        + " {green}("
                        + tag
                        + "){rst} against {byellow}"
                        + service.target.address
                        + "{rst} finished. Please ensure non-blocking processes are awaited before the run coroutine finishes. Awaiting now.",
                        verbosity=2,
                    )
                    await process_dict["process"].wait()

                if process_dict["process"].returncode != 0 and not is_expected_error(process_dict["cmd"], process_dict["process"].returncode):
                    errors = []
                    while True:
                        line = await process_dict["stderr"].readline()
                        if line is not None:
                            errors.append(line + "\n")
                        else:
                            break
                    error(
                        "Service scan {bblue}"
                        + plugin.name
                        + " {green}("
                        + tag
                        + "){rst} ran a command against {byellow}"
                        + service.target.address
                        + "{rst} which returned a non-zero exit code ("
                        + str(process_dict["process"].returncode)
                        + "). Check "
                        + service.target.scandir
                        + "/_errors.log for more details.",
                        verbosity=2,
                    )
                    async with service.target.lock:
                        with open(os.path.join(service.target.scandir, "_errors.log"), "a") as file:
                            file.writelines(
                                "[*] Service scan "
                                + plugin.name
                                + " ("
                                + tag
                                + ") ran a command which returned a non-zero exit code ("
                                + str(process_dict["process"].returncode)
                                + ").\n"
                            )
                            file.writelines("[-] Command: " + process_dict["cmd"] + "\n")
                            if errors:
                                file.writelines(["[-] Error Output:\n"] + errors + ["\n"])
                            else:
                                file.writelines("\n")

            elapsed_time = calculate_elapsed_time(start_time)

            # Complete progress bar and cleanup tasks - ALWAYS do this
            if task_id:
                try:
                    progress_manager.complete_task(task_id)
                    debug(f"Service scan progress task {task_id} completed successfully", verbosity=3)
                except Exception as e:
                    debug(f"Error completing service scan progress task {task_id}: {e}", verbosity=3)

            async with service.target.lock:
                # Ensure task is removed from running_tasks
                if tag in service.target.running_tasks:
                    try:
                        service.target.running_tasks.pop(tag, None)
                        debug(f"Service scan task {tag} removed from running_tasks", verbosity=3)
                    except Exception as e:
                        debug(f"Error removing service scan task {tag} from running_tasks: {e}", verbosity=3)

            # Remove from live loader
            complete_scan_in_live_loader(service.target.address, tag)

            info(
                "Service scan {bblue}"
                + plugin.name
                + " {green}("
                + tag
                + "){rst} against {byellow}"
                + service.target.address
                + "{rst} finished in "
                + elapsed_time,
                verbosity=2,
            )
            return {"type": "service", "plugin": plugin, "result": result}


async def generate_report(plugin, targets):
    semaphore = ipcrawler.service_scan_semaphore

    if not config["force_services"]:
        semaphore = await get_semaphore(ipcrawler)

    async with semaphore:
        try:
            result = await plugin.run(targets)
        except Exception as ex:
            exc_type, exc_value, exc_tb = sys.exc_info()
            error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
            raise Exception(
                cprint(
                    "Error: Report plugin {bblue}"
                    + plugin.name
                    + " {green}("
                    + plugin.slug
                    + "){rst} produced an exception:\n\n"
                    + error_text,
                    color=Fore.RED,
                    char="!",
                    printmsg=False,
                )
            )


async def scan_target(target):
    os.makedirs(os.path.abspath(config["output"]), exist_ok=True)

    if config["single_target"]:
        basedir = os.path.abspath(config["output"])
    else:
        basedir = os.path.abspath(os.path.join(config["output"], target.address))
        os.makedirs(basedir, exist_ok=True)

    target.basedir = basedir

    scandir = os.path.join(basedir, "scans")
    target.scandir = scandir
    os.makedirs(scandir, exist_ok=True)

    os.makedirs(os.path.join(scandir, "xml"), exist_ok=True)

    if not config["only_scans_dir"]:
        exploitdir = os.path.join(basedir, "exploit")
        os.makedirs(exploitdir, exist_ok=True)

        lootdir = os.path.join(basedir, "loot")
        os.makedirs(lootdir, exist_ok=True)

        reportdir = os.path.join(basedir, "report")
        os.makedirs(reportdir, exist_ok=True)

        open(os.path.join(reportdir, "local.txt"), "a").close()
        open(os.path.join(reportdir, "proof.txt"), "a").close()

        screenshotdir = os.path.join(reportdir, "screenshots")
        os.makedirs(screenshotdir, exist_ok=True)
    else:
        reportdir = scandir

    target.reportdir = reportdir

    pending = []

    heartbeat = asyncio.create_task(start_heartbeat(target, period=config["heartbeat"]))

    services = []
    if config["force_services"]:
        forced_services = [x.strip().lower() for x in config["force_services"]]

        for forced_service in forced_services:
            match = re.search(
                r"(?P<protocol>(tcp|udp))\/(?P<port>\d+)\/(?P<service>[\w\-]+)(\/(?P<secure>secure|insecure))?", forced_service
            )
            if match:
                protocol = match.group("protocol")
                if config["proxychains"] and protocol == "udp":
                    error("The service " + forced_service + " uses UDP and --proxychains is enabled. Skipping.", verbosity=2)
                    continue
                port = int(match.group("port"))
                service = match.group("service")
                secure = True if match.group("secure") == "secure" else False
                service = Service(protocol, port, service, secure)
                service.target = target
                services.append(service)

        if services:
            pending.append(asyncio.create_task(asyncio.sleep(0)))
        else:
            error(
                "No services were defined. Please check your service syntax: [tcp|udp]/<port>/<service-name>/[secure|insecure]"
            )
            heartbeat.cancel()
            ipcrawler.errors = True
            return
    else:
        for plugin in target.ipcrawler.plugin_types["port"]:
            if config["proxychains"] and plugin.type == "udp":
                continue

            if config["port_scans"] and plugin.slug in config["port_scans"]:
                matching_tags = True
                excluded_tags = False
            else:
                plugin_tag_set = set(plugin.tags)

                matching_tags = False
                for tag_group in target.ipcrawler.tags:
                    if set(tag_group).issubset(plugin_tag_set):
                        matching_tags = True
                        break

                excluded_tags = False
                for tag_group in target.ipcrawler.excluded_tags:
                    if set(tag_group).issubset(plugin_tag_set):
                        excluded_tags = True
                        break

            if matching_tags and not excluded_tags:
                target.scans["ports"][plugin.slug] = {"plugin": plugin, "commands": []}
                pending.append(asyncio.create_task(port_scan(plugin, target)))

    async with ipcrawler.lock:
        ipcrawler.scanning_targets.append(target)

    start_time = time.time()
    info("Scanning target {byellow}" + target.address + "{rst}")

    timed_out = False
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=1)

        # Check if global timeout has occurred.
        if config["target_timeout"] is not None:
            elapsed_seconds = round(time.time() - start_time)
            m, s = divmod(elapsed_seconds, 60)
            if m >= config["target_timeout"]:
                timed_out = True
                break

        if not config["force_services"]:
            # Extract Services - only from newly completed tasks
            services = []

            async with target.lock:
                while target.pending_services:
                    services.append(target.pending_services.pop(0))

            # Only process services from tasks that just completed in this iteration
            for task in done:
                try:
                    if task.exception():
                        print(task.exception())
                        continue
                except asyncio.InvalidStateError:
                    pass

                if task.result() and task.result()["type"] == "port":
                    for service in task.result()["result"] or []:
                        # Only add service if not already processed
                        if service.full_tag() not in target.services:
                            services.append(service)

        for service in services:
            # Double-check service hasn't been processed (race condition protection)
            if service.full_tag() not in target.services:
                target.services.append(service.full_tag())
            else:
                # Service already processed, skip entirely
                continue

            info(
                "Identified service {bmagenta}"
                + service.name
                + "{rst} on {bmagenta}"
                + service.protocol
                + "/"
                + str(service.port)
                + "{rst} on {byellow}"
                + target.address
                + "{rst}",
                verbosity=1,
            )

            if not config["only_scans_dir"]:
                with open(os.path.join(target.reportdir, "notes.txt"), "a") as file:
                    file.writelines(
                        "[*] " + service.name + " found on " + service.protocol + "/" + str(service.port) + ".\n\n\n\n"
                    )

            service.target = target

            # Create variables for command references.
            address = target.address
            addressv6 = target.address
            ipaddress = target.ip
            ipaddressv6 = target.ip
            scandir = target.scandir
            protocol = service.protocol
            port = service.port

            if not config["no_port_dirs"]:
                scandir = os.path.join(scandir, protocol + str(port))
                os.makedirs(scandir, exist_ok=True)
                os.makedirs(os.path.join(scandir, "xml"), exist_ok=True)

            # Special cases for HTTP.
            http_scheme = "https" if "https" in service.name or service.secure is True else "http"

            nmap_extra = target.ipcrawler.args.nmap
            if target.ipcrawler.args.nmap_append:
                nmap_extra += " " + target.ipcrawler.args.nmap_append

            if protocol == "udp":
                nmap_extra += " -sU"

            if target.ipversion == "IPv6":
                nmap_extra += " -6"
                if addressv6 == target.ip:
                    addressv6 = "[" + addressv6 + "]"
                ipaddressv6 = "[" + ipaddressv6 + "]"

            if config["proxychains"] and protocol == "tcp":
                nmap_extra += " -sT"

            service_match = False
            matching_plugins = []
            heading = False

            for plugin in target.ipcrawler.plugin_types["service"]:
                plugin_was_run = False
                plugin_service_match = False
                plugin_tag = service.tag() + "/" + plugin.slug

                for service_dict in plugin.services:
                    if service_dict["protocol"] == protocol and port in service_dict["port"]:
                        for name in service_dict["name"]:
                            if service_dict["negative_match"]:
                                if name not in plugin.ignore_service_names:
                                    plugin.ignore_service_names.append(name)
                            else:
                                if name not in plugin.service_names:
                                    plugin.service_names.append(name)
                    else:
                        continue

                for s in plugin.service_names:
                    if re.search(s, service.name):
                        plugin_service_match = True

                if plugin_service_match:
                    if config["service_scans"] and plugin.slug in config["service_scans"]:
                        matching_tags = True
                        excluded_tags = False
                    else:
                        plugin_tag_set = set(plugin.tags)

                        matching_tags = False
                        for tag_group in target.ipcrawler.tags:
                            if set(tag_group).issubset(plugin_tag_set):
                                matching_tags = True
                                break

                        excluded_tags = False
                        for tag_group in target.ipcrawler.excluded_tags:
                            if set(tag_group).issubset(plugin_tag_set):
                                excluded_tags = True
                                break

                    # TODO: Maybe make this less messy, keep manual-only plugins separate?
                    plugin_is_runnable = False
                    for member_name, _ in inspect.getmembers(plugin, predicate=inspect.ismethod):
                        if member_name == "run":
                            plugin_is_runnable = True
                            break

                    if plugin_is_runnable and matching_tags and not excluded_tags:
                        # Skip plugin if run_once_boolean and plugin already in target scans
                        if plugin.run_once_boolean:
                            plugin_queued = False
                            for s in target.scans["services"]:
                                if plugin.slug in target.scans["services"][s]:
                                    plugin_queued = True
                                    warn(
                                        "{byellow}["
                                        + plugin_tag
                                        + " against "
                                        + target.address
                                        + "]{srst} Plugin should only be run once and it appears to have already been queued. Skipping.{rst}",
                                        verbosity=2,
                                    )
                                    break
                            if plugin_queued:
                                break

                        # Skip plugin if require_ssl_boolean and port is not secure
                        if plugin.require_ssl_boolean and not service.secure:
                            plugin_service_match = False
                            break

                        # Skip plugin if service port is in ignore_ports:
                        if port in plugin.ignore_ports[protocol]:
                            plugin_service_match = False
                            warn(
                                "{byellow}["
                                + plugin_tag
                                + " against "
                                + target.address
                                + "]{srst} Plugin cannot be run against "
                                + protocol
                                + " port "
                                + str(port)
                                + ". Skipping.{rst}",
                                verbosity=2,
                            )
                            break

                        # Skip plugin if plugin has required ports and service port is not in them:
                        if plugin.ports[protocol] and port not in plugin.ports[protocol]:
                            plugin_service_match = False
                            warn(
                                "{byellow}["
                                + plugin_tag
                                + " against "
                                + target.address
                                + "]{srst} Plugin can only run on specific ports. Skipping.{rst}",
                                verbosity=2,
                            )
                            break

                        for i in plugin.ignore_service_names:
                            if re.search(i, service.name):
                                warn(
                                    "{byellow}["
                                    + plugin_tag
                                    + " against "
                                    + target.address
                                    + "]{srst} Plugin cannot be run against this service. Skipping.{rst}",
                                    verbosity=2,
                                )
                                break

                        # TODO: check if plugin matches tags, BUT run manual commands anyway!
                        plugin_was_run = True
                        matching_plugins.append(plugin)

                for member_name, _ in inspect.getmembers(plugin, predicate=inspect.ismethod):
                    if member_name == "manual":
                        try:
                            plugin.manual(service, plugin_was_run)
                        except Exception as ex:
                            exc_type, exc_value, exc_tb = sys.exc_info()
                            error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)[-2:])
                            cprint(
                                "Error: Service scan {bblue}"
                                + plugin.name
                                + " {green}("
                                + plugin_tag
                                + "){rst} running against {byellow}"
                                + target.address
                                + "{rst} produced an exception when generating manual commands:\n\n"
                                + error_text,
                                color=Fore.RED,
                                char="!",
                                printmsg=True,
                            )

                        if service.manual_commands:
                            plugin_run = False
                            for s in target.scans["services"]:
                                if plugin.slug in target.scans["services"][s]:
                                    plugin_run = True
                                    break
                            if not plugin.run_once_boolean or (plugin.run_once_boolean and not plugin_run):
                                with open(os.path.join(target.scandir, "_manual_commands.txt"), "a") as file:
                                    if not heading:
                                        file.write(e("[*] {service.name} on {service.protocol}/{service.port}\n\n"))
                                        heading = True
                                    for description, commands in service.manual_commands.items():
                                        try:
                                            file.write("\t[-] " + e(description) + "\n\n")
                                            for command in commands:
                                                file.write("\t\t" + e(command) + "\n\n")
                                        except Exception as ex:
                                            exc_type, exc_value, exc_tb = sys.exc_info()
                                            error_text = "".join(
                                                traceback.format_exception(exc_type, exc_value, exc_tb)[-2:]
                                            )
                                            cprint(
                                                "Error: Service scan {bblue}"
                                                + plugin.name
                                                + " {green}("
                                                + plugin_tag
                                                + "){rst} running against {byellow}"
                                                + target.address
                                                + "{rst} produced an exception when evaluating manual commands:\n\n"
                                                + error_text,
                                                color=Fore.RED,
                                                char="!",
                                                printmsg=True,
                                            )
                                    file.flush()

                        service.manual_commands = {}
                        break

                        break

                if plugin_service_match:
                    service_match = True

            for plugin in matching_plugins:
                plugin_tag = service.tag() + "/" + plugin.slug

                if plugin.run_once_boolean:
                    plugin_tag = plugin.slug

                # Check if plugin already queued for this specific service or globally (for run_once plugins)
                plugin_queued = False

                # For run_once plugins, check if already queued globally across all services
                if plugin.run_once_boolean:
                    for s in target.scans["services"]:
                        if plugin.slug in target.scans["services"][s]:
                            plugin_queued = True
                            warn(
                                "{byellow}["
                                + plugin_tag
                                + " against "
                                + target.address
                                + "]{srst} Plugin is marked as run_once and appears to have already been queued. Skipping.{rst}",
                                verbosity=2,
                            )
                            break
                    # Also check if already in running_tasks
                    if not plugin_queued:
                        async with target.lock:
                            if plugin.slug in target.running_tasks:
                                plugin_queued = True
                                warn(
                                    "{byellow}["
                                    + plugin_tag
                                    + " against "
                                    + target.address
                                    + "]{srst} Plugin is marked as run_once and is already running. Skipping.{rst}",
                                    verbosity=2,
                                )
                else:
                    # For regular plugins, check if already queued for this specific service
                    if service in target.scans["services"] and plugin_tag in target.scans["services"][service]:
                        plugin_queued = True
                        warn(
                            "{byellow}["
                            + plugin_tag
                            + " against "
                            + target.address
                            + "]{srst} Plugin appears to have already been queued for this service. Skipping.{rst}",
                            verbosity=2,
                        )
                    # Also check if already in running_tasks
                    if not plugin_queued:
                        async with target.lock:
                            if plugin_tag in target.running_tasks:
                                plugin_queued = True
                                warn(
                                    "{byellow}["
                                    + plugin_tag
                                    + " against "
                                    + target.address
                                    + "]{srst} Plugin is already running for this service. Skipping.{rst}",
                                    verbosity=2,
                                )

                if plugin_queued:
                    continue
                else:
                    if service not in target.scans["services"]:
                        target.scans["services"][service] = {}
                    target.scans["services"][service][plugin_tag] = {"plugin": plugin, "commands": []}

                pending.add(asyncio.create_task(service_scan(plugin, service)))

            if not service_match:
                warn(
                    "{byellow}["
                    + target.address
                    + "]{srst} Service "
                    + service.full_tag()
                    + " did not match any plugins based on the service name.{rst}",
                    verbosity=2,
                )
                if (
                    service.name not in config["service_exceptions"]
                    and service.full_tag() not in target.ipcrawler.missing_services
                ):
                    target.ipcrawler.missing_services.append(service.full_tag())

    for plugin in target.ipcrawler.plugin_types["report"]:
        if config["reports"] and plugin.slug in config["reports"]:
            matching_tags = True
            excluded_tags = False
        else:
            plugin_tag_set = set(plugin.tags)

            matching_tags = False
            for tag_group in target.ipcrawler.tags:
                if set(tag_group).issubset(plugin_tag_set):
                    matching_tags = True
                    break

            excluded_tags = False
            for tag_group in target.ipcrawler.excluded_tags:
                if set(tag_group).issubset(plugin_tag_set):
                    excluded_tags = True
                    break

        if matching_tags and not excluded_tags:
            pending.add(asyncio.create_task(generate_report(plugin, [target])))

    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=1)

    heartbeat.cancel()
    elapsed_time = calculate_elapsed_time(start_time)

    if timed_out:
        for task in pending:
            task.cancel()

        for process_list in target.running_tasks.values():
            for process_dict in process_list["processes"]:
                try:
                    process_dict["process"].kill()
                except ProcessLookupError:
                    pass

        warn(
            "{byellow}Scanning target "
            + target.address
            + " took longer than the specified target period ("
            + str(config["target_timeout"])
            + " min). Cancelling scans and moving to next target.{rst}"
        )
    else:
        info("Finished scanning target {byellow}" + target.address + "{rst} in " + elapsed_time)

    # Clean up timeout tasks
    if hasattr(target, 'timeout_tasks'):
        for timeout_task in target.timeout_tasks:
            if not timeout_task.done():
                timeout_task.cancel()
        target.timeout_tasks.clear()

    # Clean up any remaining progress tasks for this target
    async with target.lock:
        for task_info in list(target.running_tasks.values()):
            if "progress_task" in task_info and task_info["progress_task"]:
                progress_manager.complete_task(task_info["progress_task"])
        target.running_tasks.clear()

    async with ipcrawler.lock:
        ipcrawler.completed_targets.append(target)
        ipcrawler.scanning_targets.remove(target)


async def run():
    # Find config file.
    if os.path.isfile(os.path.join(config["config_dir"], "config.toml")):
        config_file = os.path.join(config["config_dir"], "config.toml")
    else:
        config_file = None

    # Find global file.
    if os.path.isfile(os.path.join(config["config_dir"], "global.toml")):
        config["global_file"] = os.path.join(config["config_dir"], "global.toml")
    else:
        config["global_file"] = None

    # Find plugins.
    if os.path.isdir(os.path.join(config["data_dir"], "plugins")):
        config["plugins_dir"] = os.path.join(config["data_dir"], "plugins")
    else:
        config["plugins_dir"] = None

    parser = argparse.ArgumentParser(
        add_help=False,
        allow_abbrev=False,
        description="Network reconnaissance tool to port scan and automatically enumerate services found on multiple targets.",
    )
    parser.add_argument(
        "targets",
        action="store",
        help="IP addresses (e.g. 10.0.0.1), CIDR notation (e.g. 10.0.0.1/24), or resolvable hostnames (e.g. foo.bar) to scan.",
        nargs="*",
    )
    parser.add_argument("-t", "--target-file", action="store", type=str, default="", help="Read targets from file.")
    parser.add_argument(
        "-p",
        "--ports",
        action="store",
        type=str,
        help="Comma separated list of ports / port ranges to scan. Specify TCP/UDP ports by prepending list with T:/U: To scan both TCP/UDP, put port(s) at start or specify B: e.g. 53,T:21-25,80,U:123,B:123. Default: %(default)s",
    )
    parser.add_argument(
        "-m",
        "--max-scans",
        action="store",
        type=int,
        help="The maximum number of concurrent scans to run. Default: %(default)s",
    )
    parser.add_argument(
        "-mp",
        "--max-port-scans",
        action="store",
        type=int,
        help="The maximum number of concurrent port scans to run. Default: 10 (approx 20%% of max-scans unless specified)",
    )
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        type=str,
        default=config_file,
        dest="config_file",
        help="Location of ipcrawler's config file. Default: %(default)s",
    )
    parser.add_argument(
        "-g", "--global-file", action="store", type=str, help="Location of ipcrawler's global file. Default: %(default)s"
    )
    parser.add_argument(
        "--tags",
        action="store",
        type=str,
        default="default",
        help="Tags to determine which plugins should be included. Separate tags by a plus symbol (+) to group tags together. Separate groups with a comma (,) to create multiple groups. For a plugin to be included, it must have all the tags specified in at least one group. Default: %(default)s",
    )
    parser.add_argument(
        "--exclude-tags",
        action="store",
        type=str,
        default="",
        metavar="TAGS",
        help="Tags to determine which plugins should be excluded. Separate tags by a plus symbol (+) to group tags together. Separate groups with a comma (,) to create multiple groups. For a plugin to be excluded, it must have all the tags specified in at least one group. Default: %(default)s",
    )
    parser.add_argument(
        "--port-scans",
        action="store",
        type=str,
        metavar="PLUGINS",
        help="Override --tags / --exclude-tags for the listed PortScan plugins (comma separated). Default: %(default)s",
    )
    parser.add_argument(
        "--service-scans",
        action="store",
        type=str,
        metavar="PLUGINS",
        help="Override --tags / --exclude-tags for the listed ServiceScan plugins (comma separated). Default: %(default)s",
    )
    parser.add_argument(
        "--reports",
        action="store",
        type=str,
        metavar="PLUGINS",
        help="Override --tags / --exclude-tags for the listed Report plugins (comma separated). Default: %(default)s",
    )
    parser.add_argument(
        "--plugins-dir", action="store", type=str, help="The location of the plugins directory. Default: %(default)s"
    )
    parser.add_argument(
        "--add-plugins-dir",
        action="store",
        type=str,
        metavar="PLUGINS_DIR",
        help="The location of an additional plugins directory to add to the main one. Default: %(default)s",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store",
        nargs="?",
        const="plugins",
        metavar="TYPE",
        help="List all plugins or plugins of a specific type. e.g. --list, --list port, --list service",
    )
    parser.add_argument("-o", "--output", action="store", help="The output directory for results. Default: %(default)s")
    parser.add_argument(
        "--single-target",
        action="store_true",
        help="Only scan a single target. A directory named after the target will not be created. Instead, the directory structure will be created within the output directory. Default: %(default)s",
    )
    parser.add_argument(
        "--only-scans-dir",
        action="store_true",
        help='Only create the "scans" directory for results. Other directories (e.g. exploit, loot, report) will not be created. Default: %(default)s',
    )
    parser.add_argument(
        "--no-port-dirs",
        action="store_true",
        help='Don\'t create directories for ports (e.g. scans/tcp80, scans/udp53). Instead store all results in the "scans" directory itself. Default: %(default)s',
    )
    parser.add_argument(
        "--heartbeat",
        action="store",
        type=int,
        help="Specifies the heartbeat interval (in seconds) for scan status messages. Default: %(default)s",
    )
    parser.add_argument(
        "--timeout",
        action="store",
        type=int,
        help="Specifies the maximum amount of time in minutes that ipcrawler should run for. Default: %(default)s",
    )
    parser.add_argument(
        "--target-timeout",
        action="store",
        type=int,
        help="Specifies the maximum amount of time in minutes that a target should be scanned for before abandoning it and moving on. Default: %(default)s",
    )
    nmap_group = parser.add_mutually_exclusive_group()
    nmap_group.add_argument("--nmap", action="store", help="Override the {nmap_extra} variable in scans. Default: %(default)s")
    nmap_group.add_argument(
        "--nmap-append", action="store", help="Append to the default {nmap_extra} variable in scans. Default: %(default)s"
    )
    parser.add_argument(
        "--proxychains", action="store_true", help="Use if you are running ipcrawler via proxychains. Default: %(default)s"
    )
    parser.add_argument(
        "--disable-sanity-checks",
        action="store_true",
        help="Disable sanity checks that would otherwise prevent the scans from running. Default: %(default)s",
    )
    parser.add_argument(
        "--disable-keyboard-control",
        action="store_true",
        help="Disables keyboard control ([s]tatus, Up, Down) if you are in SSH or Docker.",
    )
    parser.add_argument(
        "--ignore-plugin-checks",
        action="store_true",
        help="Ignores errors from plugin check functions that would otherwise prevent ipcrawler from running. Default: %(default)s",
    )
    parser.add_argument(
        "--force-services",
        action="store",
        nargs="+",
        metavar="SERVICE",
        help="A space separated list of services in the following style: tcp/80/http tcp/443/https/secure",
    )
    parser.add_argument(
        "-mpti",
        "--max-plugin-target-instances",
        action="store",
        nargs="+",
        metavar="PLUGIN:NUMBER",
        help="A space separated list of plugin slugs with the max number of instances (per target) in the following style: nmap-http:2 dirbuster:1. Default: %(default)s",
    )
    parser.add_argument(
        "-mpgi",
        "--max-plugin-global-instances",
        action="store",
        nargs="+",
        metavar="PLUGIN:NUMBER",
        help="A space separated list of plugin slugs with the max number of global instances in the following style: nmap-http:2 dirbuster:1. Default: %(default)s",
    )
    parser.add_argument(
        "--accessible",
        action="store_true",
        help="Attempts to make ipcrawler output more accessible to screenreaders. Default: %(default)s",
    )
    parser.add_argument("-v", "--verbose", action="count", help="Enable verbose output. Repeat for more verbosity.")
    parser.add_argument("--debug", action="store_true", help="Enable debug output for development and troubleshooting.")
    parser.add_argument("--version", action="store_true", help="Prints the ipcrawler version and exits.")
    parser.error = lambda s: fail(s[0].upper() + s[1:])
    args, unknown = parser.parse_known_args()

    errors = False

    ipcrawler.argparse = parser

    if args.version:
        print("ipcrawler v" + VERSION)
        sys.exit(0)

    def unknown_help():
        if "-h" in unknown:
            parser.print_help()
            print()

    # Parse config file and args for global.toml first.
    if not args.config_file:
        unknown_help()
        fail("Error: Could not find config.toml in the current directory or ~/.config/ipcrawler.")

    if not os.path.isfile(args.config_file):
        unknown_help()
        fail('Error: Specified config file "' + args.config_file + '" does not exist.')

    with open(args.config_file) as c:
        try:
            config_toml = toml.load(c)
            for key, val in config_toml.items():
                key = slugify(key)
                if key == "global-file":
                    config["global_file"] = val
                elif key == "plugins-dir":
                    config["plugins_dir"] = val
                elif key == "add-plugins-dir":
                    config["add_plugins_dir"] = val
                elif key == "scan" and isinstance(val, dict):  # Process scan configuration
                    for skey, sval in val.items():
                        # Convert hyphenated keys to underscored config keys
                        skey_config = skey.replace("-", "_")
                        if skey_config in config:
                            config[skey_config] = sval
        except toml.decoder.TomlDecodeError:
            unknown_help()
            fail("Error: Couldn't parse " + args.config_file + " config file. Check syntax.")

    args_dict = vars(args)
    for key in args_dict:
        key = slugify(key)
        if key == "global-file" and args_dict["global_file"] is not None:
            config["global_file"] = args_dict["global_file"]
        elif key == "plugins-dir" and args_dict["plugins_dir"] is not None:
            config["plugins_dir"] = args_dict["plugins_dir"]
        elif key == "add-plugins-dir" and args_dict["add_plugins_dir"] is not None:
            config["add_plugins_dir"] = args_dict["add_plugins_dir"]

    if not config["plugins_dir"]:
        unknown_help()
        fail("Error: Could not find plugins directory in the current directory or ~/.config/ipcrawler.")

    if not os.path.isdir(config["plugins_dir"]):
        unknown_help()
        fail('Error: Specified plugins directory "' + config["plugins_dir"] + '" does not exist.')

    if config["add_plugins_dir"] and not os.path.isdir(config["add_plugins_dir"]):
        unknown_help()
        fail('Error: Specified additional plugins directory "' + config["add_plugins_dir"] + '" does not exist.')

    plugins_dirs = [config["plugins_dir"]]
    if config["add_plugins_dir"]:
        plugins_dirs.append(config["add_plugins_dir"])

    for plugins_dir in plugins_dirs:
        for plugin_file in sorted(os.listdir(plugins_dir)):
            if not plugin_file.startswith("_") and plugin_file.endswith(".py"):
                dirname, filename = os.path.split(os.path.join(plugins_dir, plugin_file))
                dirname = os.path.abspath(dirname)

                try:
                    spec = importlib.util.spec_from_file_location(
                        "ipcrawler." + filename[:-3], os.path.join(dirname, filename)
                    )
                    plugin = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin)

                    clsmembers = inspect.getmembers(plugin, predicate=inspect.isclass)
                    for _, c in clsmembers:
                        if c.__module__ in ["ipcrawler.plugins", "ipcrawler.targets"]:
                            continue

                        # Skip imported classes (only process classes defined in this plugin file)
                        if c.__module__ != plugin.__name__:
                            continue

                        if c.__name__.lower() in config["protected_classes"]:
                            unknown_help()
                            print(
                                'Plugin "'
                                + c.__name__
                                + '" in '
                                + filename
                                + " is using a protected class name. Please change it."
                            )
                            sys.exit(1)

                        # Only add classes that are a sub class of either PortScan, ServiceScan, or Report
                        if issubclass(c, PortScan) or issubclass(c, ServiceScan) or issubclass(c, Report):
                            ipcrawler.register(c(), filename)
                        else:
                            print(
                                'Plugin "'
                                + c.__name__
                                + '" in '
                                + filename
                                + " is not a subclass of either PortScan, ServiceScan, or Report."
                            )
                except (ImportError, SyntaxError) as ex:
                    unknown_help()
                    print("cannot import " + filename + " plugin")
                    print(ex)
                    sys.exit(1)

    for plugin in ipcrawler.plugins.values():
        if plugin.slug in ipcrawler.taglist:
            unknown_help()
            fail(
                "Plugin "
                + plugin.name
                + " has a slug ("
                + plugin.slug
                + ") with the same name as a tag. Please either change the plugin name or override the slug."
            )
        # Add plugin slug to tags.
        plugin.tags += [plugin.slug]

    if len(ipcrawler.plugin_types["port"]) == 0:
        unknown_help()
        fail('Error: There are no valid PortScan plugins in the plugins directory "' + config["plugins_dir"] + '".')

    # Sort plugins by priority.
    ipcrawler.plugin_types["port"].sort(key=lambda x: x.priority)
    ipcrawler.plugin_types["service"].sort(key=lambda x: x.priority)
    ipcrawler.plugin_types["report"].sort(key=lambda x: x.priority)

    if not config["global_file"]:
        unknown_help()
        fail("Error: Could not find global.toml in the current directory or ~/.config/ipcrawler.")

    if not os.path.isfile(config["global_file"]):
        unknown_help()
        fail('Error: Specified global file "' + config["global_file"] + '" does not exist.')

    global_plugin_args = None
    with open(config["global_file"]) as g:
        try:
            global_toml = toml.load(g)
            for key, val in global_toml.items():
                if key == "global" and isinstance(val, dict):  # Process global plugin options.
                    for gkey, gvals in global_toml["global"].items():
                        if isinstance(gvals, dict):
                            options = {"metavar": "VALUE"}

                            if "default" in gvals:
                                options["default"] = gvals["default"]

                            if "metavar" in gvals:
                                options["metavar"] = gvals["metavar"]

                            if "help" in gvals:
                                options["help"] = gvals["help"]

                            if "type" in gvals:
                                gtype = gvals["type"].lower()
                                if gtype == "constant":
                                    if "constant" not in gvals:
                                        fail("Global constant option " + gkey + " has no constant value set.")
                                    else:
                                        options["action"] = "store_const"
                                        options["const"] = gvals["constant"]
                                elif gtype == "true":
                                    options["action"] = "store_true"
                                    options.pop("metavar", None)
                                    options.pop("default", None)
                                elif gtype == "false":
                                    options["action"] = "store_false"
                                    options.pop("metavar", None)
                                    options.pop("default", None)
                                elif gtype == "list":
                                    options["nargs"] = "+"
                                elif gtype == "choice":
                                    if "choices" not in gvals:
                                        fail("Global choice option " + gkey + " has no choices value set.")
                                    else:
                                        if not isinstance(gvals["choices"], list):
                                            fail("The 'choices' value for global choice option " + gkey + " should be a list.")
                                        options["choices"] = gvals["choices"]
                                        options.pop("metavar", None)

                            if global_plugin_args is None:
                                global_plugin_args = parser.add_argument_group(
                                    "global plugin arguments",
                                    description="These are optional arguments that can be used by all plugins.",
                                )

                            global_plugin_args.add_argument("--global." + slugify(gkey), **options)
                elif key == "pattern" and isinstance(val, list):  # Process global patterns.
                    for pattern in val:
                        if "pattern" in pattern:
                            try:
                                compiled = re.compile(pattern["pattern"])
                                if "description" in pattern:
                                    ipcrawler.patterns.append(Pattern(compiled, description=pattern["description"]))
                                else:
                                    ipcrawler.patterns.append(Pattern(compiled))
                            except re.error:
                                unknown_help()
                                fail('Error: The pattern "' + pattern["pattern"] + '" in the global file is invalid regex.')
                        else:
                            unknown_help()
                            fail("Error: A [[pattern]] in the global file doesn't have a required pattern variable.")

        except toml.decoder.TomlDecodeError:
            unknown_help()
            fail("Error: Couldn't parse " + g.name + " file. Check syntax.")

    other_options = []
    for key, val in config_toml.items():
        if key == "global" and isinstance(val, dict):  # Process global plugin options.
            for gkey, gval in config_toml["global"].items():
                if isinstance(gval, bool):
                    for action in ipcrawler.argparse._actions:
                        if action.dest == "global." + slugify(gkey).replace("-", "_"):
                            if action.const is True:
                                action.__setattr__("default", gval)
                            break
                else:
                    if ipcrawler.argparse.get_default("global." + slugify(gkey).replace("-", "_")):
                        ipcrawler.argparse.set_defaults(**{"global." + slugify(gkey).replace("-", "_"): gval})
        elif isinstance(val, dict):  # Process potential plugin arguments.
            for pkey, pval in config_toml[key].items():
                if (
                    ipcrawler.argparse.get_default(slugify(key).replace("-", "_") + "." + slugify(pkey).replace("-", "_"))
                    is not None
                ):
                    for action in ipcrawler.argparse._actions:
                        if action.dest == slugify(key).replace("-", "_") + "." + slugify(pkey).replace("-", "_"):
                            if action.const and pval != action.const:
                                if action.const in [True, False]:
                                    error(
                                        "Config option ["
                                        + slugify(key)
                                        + "] "
                                        + slugify(pkey)
                                        + ": invalid value: '"
                                        + str(pval)
                                        + "' (should be "
                                        + str(action.const).lower()
                                        + " {no quotes})"
                                    )
                                else:
                                    error(
                                        "Config option ["
                                        + slugify(key)
                                        + "] "
                                        + slugify(pkey)
                                        + ": invalid value: '"
                                        + str(pval)
                                        + "' (should be "
                                        + str(action.const)
                                        + ")"
                                    )
                                errors = True
                            elif action.choices and pval not in action.choices:
                                error(
                                    "Config option ["
                                    + slugify(key)
                                    + "] "
                                    + slugify(pkey)
                                    + ": invalid choice: '"
                                    + str(pval)
                                    + "' (choose from '"
                                    + "', '".join(action.choices)
                                    + "')"
                                )
                                errors = True
                            elif isinstance(action.default, list) and not isinstance(pval, list):
                                error(
                                    "Config option ["
                                    + slugify(key)
                                    + "] "
                                    + slugify(pkey)
                                    + ": invalid value: '"
                                    + str(pval)
                                    + "' (should be a list e.g. ['"
                                    + str(pval)
                                    + "'])"
                                )
                                errors = True
                            break
                    ipcrawler.argparse.set_defaults(
                        **{slugify(key).replace("-", "_") + "." + slugify(pkey).replace("-", "_"): pval}
                    )
        else:  # Process potential other options.
            key = key.replace("-", "_")
            if key in configurable_keys:
                other_options.append(key)
                config[key] = val
                ipcrawler.argparse.set_defaults(**{key: val})

    for key, val in config.items():
        if key not in other_options:
            ipcrawler.argparse.set_defaults(**{key: val})

    # Custom help handling
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit.")
    parser.add_argument("--help-all", action="store_true", help="Show complete help with all available options.")
    parser.error = lambda s: fail(s[0].upper() + s[1:])
    args = parser.parse_args()

    # Handle custom help
    if args.help:
        if RICH_AVAILABLE:
            show_rich_help()
        else:
            show_fallback_help(parser)
        sys.exit(0)

    # Handle complete help
    if hasattr(args, "help_all") and args.help_all:
        if RICH_AVAILABLE:
            show_complete_help()
        else:
            print("Complete help requires Rich library. Install with: pip install rich")
            show_fallback_help(parser)
        sys.exit(0)

    args_dict = vars(args)
    for key in args_dict:
        if key in configurable_keys and args_dict[key] is not None:
            # Special case for booleans
            if key in configurable_boolean_keys and config[key]:
                continue
            config[key] = args_dict[key]
    ipcrawler.args = args

    # Process tags before listing so --list shows accurate results
    tags = []
    for tag_group in list(set(filter(None, args.tags.lower().split(",")))):
        tags.append(list(set(filter(None, tag_group.split("+")))))

    # Remove duplicate lists from list.
    [ipcrawler.tags.append(t) for t in tags if t not in ipcrawler.tags]

    excluded_tags = []
    if args.exclude_tags is None:
        args.exclude_tags = ""
    # If exclude_tags wasn't explicitly provided via command line, use config file value
    if args.exclude_tags == "" and config["exclude_tags"]:
        args.exclude_tags = config["exclude_tags"]
    if args.exclude_tags != "":
        for tag_group in list(set(filter(None, args.exclude_tags.lower().split(",")))):
            excluded_tags.append(list(set(filter(None, tag_group.split("+")))))

        # Remove duplicate lists from list.
        [ipcrawler.excluded_tags.append(t) for t in excluded_tags if t not in ipcrawler.excluded_tags]

    def check_plugin_tags(plugin):
        """Check if plugin matches current tag filtering"""
        if config["port_scans"] and plugin.slug in config["port_scans"]:
            return True
        if config["service_scans"] and plugin.slug in config["service_scans"]:
            return True
        if config["reports"] and plugin.slug in config["reports"]:
            return True

        plugin_tag_set = set(plugin.tags)

        # Check if plugin matches any tag group
        matching_tags = False
        for tag_group in ipcrawler.tags:
            if set(tag_group).issubset(plugin_tag_set):
                matching_tags = True
                break

        # Check if plugin is excluded by any excluded tag group
        excluded_tags = False
        for tag_group in ipcrawler.excluded_tags:
            if set(tag_group).issubset(plugin_tag_set):
                excluded_tags = True
                break

        return matching_tags and not excluded_tags

    if args.list:
        from rich.table import Table
        from rich.panel import Panel

        type = args.list.lower()

        # Create a table for plugin listing
        table = Table(show_header=True, header_style="bold cyan", border_style="dim blue")
        table.add_column("Plugin Type", style="green", min_width=10)
        table.add_column("Name", style="cyan", min_width=20)
        table.add_column("Slug", style="magenta", min_width=15)
        table.add_column("Description", style="dim white")

        plugin_count = 0
        excluded_count = 0

        if type in ["plugin", "plugins", "port", "ports", "portscan", "portscans"]:
            for p in sorted(ipcrawler.plugin_types["port"], key=lambda x: x.name.lower()):
                if check_plugin_tags(p):
                    table.add_row(
                        "🔍 PortScan",
                        p.name,
                        f"[dim]{p.slug}[/dim]",
                        p.description if p.description else "[dim]No description[/dim]",
                    )
                    plugin_count += 1
                else:
                    excluded_count += 1

        if type in ["plugin", "plugins", "service", "services", "servicescan", "servicescans"]:
            for p in sorted(ipcrawler.plugin_types["service"], key=lambda x: x.name.lower()):
                if check_plugin_tags(p):
                    table.add_row(
                        "🔧 ServiceScan",
                        p.name,
                        f"[dim]{p.slug}[/dim]",
                        p.description if p.description else "[dim]No description[/dim]",
                    )
                    plugin_count += 1
                else:
                    excluded_count += 1

        if type in ["plugin", "plugins", "report", "reports", "reporting"]:
            for p in sorted(ipcrawler.plugin_types["report"], key=lambda x: x.name.lower()):
                if check_plugin_tags(p):
                    table.add_row(
                        "📊 Report",
                        p.name,
                        f"[dim]{p.slug}[/dim]",
                        p.description if p.description else "[dim]No description[/dim]",
                    )
                    plugin_count += 1
                else:
                    excluded_count += 1

        # Display the results in a styled panel
        title = f"Available Plugins"
        if type not in ["plugin", "plugins"]:
            title += f" - {type.title()} Type"

        # Create subtitle with filtering info
        subtitle_parts = [f"[green]Active: {plugin_count}[/green]"]
        if excluded_count > 0:
            subtitle_parts.append(f"[red]Excluded: {excluded_count}[/red]")
        if len(ipcrawler.tags) > 0:
            tag_display = " + ".join(["+".join(tag_group) for tag_group in ipcrawler.tags])
            subtitle_parts.append(f"[yellow]Tags: {tag_display}[/yellow]")
        subtitle = " | ".join(subtitle_parts)

        panel = Panel(
            table,
            title=f"[bold green]{title}[/bold green]",
            subtitle=f"[dim]{subtitle}[/dim]",
            border_style="green",
            padding=(1, 2),
        )

        rich_console.print()
        rich_console.print(panel)
        rich_console.print()

        # Show usage examples
        examples_table = Table(show_header=False, border_style="dim", show_edge=False)
        examples_table.add_column("", style="dim cyan", min_width=20)
        examples_table.add_column("", style="dim")
        examples_table.add_row("--list", "Show all plugins")
        examples_table.add_row("--list port", "Show only port scan plugins")
        examples_table.add_row("--list service", "Show only service scan plugins")
        examples_table.add_row("--list report", "Show only report plugins")

        rich_console.print(
            Panel(examples_table, title="[dim]💡 Usage Examples[/dim]", border_style="dim blue", padding=(0, 1))
        )
        rich_console.print()

        sys.exit(0)

    max_plugin_target_instances = {}
    if config["max_plugin_target_instances"]:
        for plugin_instance in config["max_plugin_target_instances"]:
            plugin_instance = plugin_instance.split(":", 1)
            if len(plugin_instance) == 2:
                if plugin_instance[0] not in ipcrawler.plugins:
                    error(
                        "Invalid plugin slug ("
                        + plugin_instance[0]
                        + ":"
                        + plugin_instance[1]
                        + ") provided to --max-plugin-target-instances."
                    )
                    errors = True
                elif not plugin_instance[1].isdigit() or int(plugin_instance[1]) == 0:
                    error(
                        "Invalid number of instances ("
                        + plugin_instance[0]
                        + ":"
                        + plugin_instance[1]
                        + ") provided to --max-plugin-target-instances. Must be a non-zero positive integer."
                    )
                    errors = True
                else:
                    max_plugin_target_instances[plugin_instance[0]] = int(plugin_instance[1])
            else:
                error("Invalid value provided to --max-plugin-target-instances. Values must be in the format PLUGIN:NUMBER.")

    max_plugin_global_instances = {}
    if config["max_plugin_global_instances"]:
        for plugin_instance in config["max_plugin_global_instances"]:
            plugin_instance = plugin_instance.split(":", 1)
            if len(plugin_instance) == 2:
                if plugin_instance[0] not in ipcrawler.plugins:
                    error(
                        "Invalid plugin slug ("
                        + plugin_instance[0]
                        + ":"
                        + plugin_instance[1]
                        + ") provided to --max-plugin-global-instances."
                    )
                    errors = True
                elif not plugin_instance[1].isdigit() or int(plugin_instance[1]) == 0:
                    error(
                        "Invalid number of instances ("
                        + plugin_instance[0]
                        + ":"
                        + plugin_instance[1]
                        + ") provided to --max-plugin-global-instances. Must be a non-zero positive integer."
                    )
                    errors = True
                else:
                    max_plugin_global_instances[plugin_instance[0]] = int(plugin_instance[1])
            else:
                error("Invalid value provided to --max-plugin-global-instances. Values must be in the format PLUGIN:NUMBER.")

    failed_check_plugin_slugs = []
    for slug, plugin in ipcrawler.plugins.items():
        if hasattr(plugin, "max_target_instances") and plugin.slug in max_plugin_target_instances:
            plugin.max_target_instances = max_plugin_target_instances[plugin.slug]

        if hasattr(plugin, "max_global_instances") and plugin.slug in max_plugin_global_instances:
            plugin.max_global_instances = max_plugin_global_instances[plugin.slug]

        for member_name, _ in inspect.getmembers(plugin, predicate=inspect.ismethod):
            if member_name == "check":
                if plugin.check() == False:
                    failed_check_plugin_slugs.append(slug)
                    continue
                continue

    # Check for any failed plugin checks.
    for slug in failed_check_plugin_slugs:
        # If plugin checks should be ignored, remove the affected plugins at runtime.
        if config["ignore_plugin_checks"]:
            ipcrawler.plugins.pop(slug)
        else:
            print()
            error(
                "The following plugins failed checks that prevent ipcrawler from running: "
                + ", ".join(failed_check_plugin_slugs)
            )
            error(
                "Check above output to fix these issues, disable relevant plugins, or run ipcrawler with --ignore-plugin-checks to disable failed plugins at runtime."
            )
            print()
            errors = True
            break

    if config["ports"]:
        ports_to_scan = {"tcp": [], "udp": []}
        unique = {"tcp": [], "udp": []}

        ports = config["ports"].split(",")
        mode = "both"
        for port in ports:
            port = port.strip()
            if port == "":
                continue

            if port.startswith("B:"):
                mode = "both"
                port = port.split("B:")[1]
            elif port.startswith("T:"):
                mode = "tcp"
                port = port.split("T:")[1]
            elif port.startswith("U:"):
                mode = "udp"
                port = port.split("U:")[1]

            match = re.search(r"^([0-9]+)\-([0-9]+)$", port)
            if match:
                num1 = int(match.group(1))
                num2 = int(match.group(2))

                if num1 > 65535:
                    fail("Error: A provided port number was too high: " + str(num1))

                if num2 > 65535:
                    fail("Error: A provided port number was too high: " + str(num2))

                if num1 == num2:
                    port_range = [num1]

                if num2 > num1:
                    port_range = list(range(num1, num2 + 1, 1))
                else:
                    port_range = list(range(num2, num1 + 1, 1))
                    num1 = num1 + num2
                    num2 = num1 - num2
                    num1 = num1 - num2

                if mode == "tcp" or mode == "both":
                    for num in port_range:
                        if num in ports_to_scan["tcp"]:
                            ports_to_scan["tcp"].remove(num)
                    ports_to_scan["tcp"].append(str(num1) + "-" + str(num2))
                    unique["tcp"] = list(set(unique["tcp"] + port_range))

                if mode == "udp" or mode == "both":
                    for num in port_range:
                        if num in ports_to_scan["udp"]:
                            ports_to_scan["udp"].remove(num)
                    ports_to_scan["udp"].append(str(num1) + "-" + str(num2))
                    unique["udp"] = list(set(unique["tcp"] + port_range))
            else:
                match = re.search("^[0-9]+$", port)
                if match:
                    num = int(port)

                    if num > 65535:
                        fail("Error: A provided port number was too high: " + str(num))

                    if mode == "tcp" or mode == "both":
                        ports_to_scan["tcp"].append(str(num)) if num not in unique["tcp"] else ports_to_scan["tcp"]
                        unique["tcp"].append(num)

                    if mode == "udp" or mode == "both":
                        ports_to_scan["udp"].append(str(num)) if num not in unique["udp"] else ports_to_scan["udp"]
                        unique["udp"].append(num)
                else:
                    fail("Error: Invalid port number: " + str(port))
        config["ports"] = ports_to_scan

    if config["max_scans"] <= 0:
        error("Argument -m/--max-scans must be at least 1.")
        errors = True

    if config["max_port_scans"] is None:
        config["max_port_scans"] = max(1, round(config["max_scans"] * 0.2))
    else:
        if config["max_port_scans"] <= 0:
            error("Argument -mp/--max-port-scans must be at least 1.")
            errors = True

        if config["max_port_scans"] > config["max_scans"]:
            error("Argument -mp/--max-port-scans cannot be greater than argument -m/--max-scans.")
            errors = True

    if config["heartbeat"] <= 0:
        error("Argument --heartbeat must be at least 1.")
        errors = True

    if config["timeout"] is not None and config["timeout"] <= 0:
        error("Argument --timeout must be at least 1.")
        errors = True

    if config["target_timeout"] is not None and config["target_timeout"] <= 0:
        error("Argument --target-timeout must be at least 1.")
        errors = True

    if config["timeout"] is not None and config["target_timeout"] is not None and config["timeout"] < config["target_timeout"]:
        error("Argument --timeout cannot be less than --target-timeout.")
        errors = True

    if not errors:
        if config["force_services"]:
            ipcrawler.service_scan_semaphore = asyncio.Semaphore(config["max_scans"])
        else:
            ipcrawler.port_scan_semaphore = asyncio.Semaphore(config["max_port_scans"])
            # If max scans and max port scans is the same, the service scan semaphore and port scan semaphore should be the same object
            if config["max_scans"] == config["max_port_scans"]:
                ipcrawler.service_scan_semaphore = ipcrawler.port_scan_semaphore
            else:
                ipcrawler.service_scan_semaphore = asyncio.Semaphore(config["max_scans"] - config["max_port_scans"])

    if config["port_scans"]:
        config["port_scans"] = [x.strip().lower() for x in config["port_scans"].split(",")]

    if config["service_scans"]:
        config["service_scans"] = [x.strip().lower() for x in config["service_scans"].split(",")]

    if config["reports"]:
        config["reports"] = [x.strip().lower() for x in config["reports"].split(",")]

    raw_targets = args.targets

    if len(args.target_file) > 0:
        if not os.path.isfile(args.target_file):
            error('The target file "' + args.target_file + '" was not found.')
            sys.exit(1)
        try:
            with open(args.target_file, "r") as f:
                lines = f.read()
                for line in lines.splitlines():
                    line = line.strip()
                    if line.startswith("#"):
                        continue
                    match = re.match("([^#]+)#", line)
                    if match:
                        line = match.group(1).strip()
                    if len(line) == 0:
                        continue
                    if line not in raw_targets:
                        raw_targets.append(line)
        except OSError:
            error("The target file " + args.target_file + " could not be read.")
            sys.exit(1)

    unresolvable_targets = False
    for target in raw_targets:
        try:
            ip = ipaddress.ip_address(target)
            ip_str = str(ip)

            found = False
            for t in ipcrawler.pending_targets:
                if t.address == ip_str:
                    found = True
                    break

            if found:
                continue

            if isinstance(ip, ipaddress.IPv4Address):
                ipcrawler.pending_targets.append(Target(ip_str, ip_str, "IPv4", "ip", ipcrawler))
            elif isinstance(ip, ipaddress.IPv6Address):
                ipcrawler.pending_targets.append(Target(ip_str, ip_str, "IPv6", "ip", ipcrawler))
            else:
                fail("This should never happen unless IPv8 is invented.")
        except ValueError:
            try:
                target_range = ipaddress.ip_network(target, strict=False)
                if not args.disable_sanity_checks and target_range.num_addresses > 256:
                    fail(
                        target
                        + " contains "
                        + str(target_range.num_addresses)
                        + " addresses. Check that your CIDR notation is correct. If it is, re-run with the --disable-sanity-checks option to suppress this check."
                    )
                    errors = True
                else:
                    for ip in target_range.hosts():
                        ip_str = str(ip)

                        found = False
                        for t in ipcrawler.pending_targets:
                            if t.address == ip_str:
                                found = True
                                break

                        if found:
                            continue

                        if isinstance(ip, ipaddress.IPv4Address):
                            ipcrawler.pending_targets.append(Target(ip_str, ip_str, "IPv4", "ip", ipcrawler))
                        elif isinstance(ip, ipaddress.IPv6Address):
                            ipcrawler.pending_targets.append(Target(ip_str, ip_str, "IPv6", "ip", ipcrawler))
                        else:
                            fail("This should never happen unless IPv8 is invented.")

            except ValueError:
                try:
                    addresses = socket.getaddrinfo(target, None, socket.AF_INET)
                    ip = addresses[0][4][0]

                    found = False
                    for t in ipcrawler.pending_targets:
                        if t.address == target:
                            found = True
                            break

                    if found:
                        continue

                    ipcrawler.pending_targets.append(Target(target, ip, "IPv4", "hostname", ipcrawler))
                except socket.gaierror:
                    try:
                        addresses = socket.getaddrinfo(target, None, socket.AF_INET6)
                        ip = addresses[0][4][0]

                        found = False
                        for t in ipcrawler.pending_targets:
                            if t.address == target:
                                found = True
                                break

                        if found:
                            continue

                        ipcrawler.pending_targets.append(Target(target, ip, "IPv6", "hostname", ipcrawler))
                    except socket.gaierror:
                        unresolvable_targets = True
                        error(target + " does not appear to be a valid IP address, IP range, or resolvable hostname.")

    if not args.disable_sanity_checks and unresolvable_targets == True:
        error(
            "ipcrawler will not run if any targets are invalid / unresolvable. To override this, re-run with the --disable-sanity-checks option."
        )
        errors = True

    if len(ipcrawler.pending_targets) == 0:
        error("You must specify at least one target to scan!")
        errors = True

    if config["single_target"] and len(ipcrawler.pending_targets) != 1:
        error("You cannot provide more than one target when scanning in single-target mode.")
        errors = True

    if not args.disable_sanity_checks and len(ipcrawler.pending_targets) > 256:
        error(
            "A total of "
            + str(len(ipcrawler.pending_targets))
            + " targets would be scanned. If this is correct, re-run with the --disable-sanity-checks option to suppress this check."
        )
        errors = True
    if not config["force_services"]:
        port_scan_plugin_count = 0
        for plugin in ipcrawler.plugin_types["port"]:
            if config["port_scans"] and plugin.slug in config["port_scans"]:
                matching_tags = True
                excluded_tags = False
            else:
                matching_tags = False
                for tag_group in ipcrawler.tags:
                    if set(tag_group).issubset(set(plugin.tags)):
                        matching_tags = True
                        break

                excluded_tags = False
                for tag_group in ipcrawler.excluded_tags:
                    if set(tag_group).issubset(set(plugin.tags)):
                        excluded_tags = True
                        break

            if matching_tags and not excluded_tags:
                port_scan_plugin_count += 1

        if port_scan_plugin_count == 0:
            error("There are no port scan plugins that match the tags specified.")
            errors = True
    else:
        port_scan_plugin_count = config["max_port_scans"] / 5

    if errors:
        sys.exit(1)

    config["port_scan_plugin_count"] = port_scan_plugin_count

    num_initial_targets = max(1, math.ceil(config["max_port_scans"] / port_scan_plugin_count))

    # Show startup banner with spider-themed interface
    show_startup_banner(ipcrawler.pending_targets, VERSION)

    # Start progress manager for long scans
    progress_manager.start()

    # Start live scan loader for real-time scan display
    start_live_loader()

    # Initialize VHost auto-discovery system
    from ipcrawler.io import vhost_manager

    vhost_manager.check_auto_add_conditions()

    start_time = time.time()

    if not config["disable_keyboard_control"]:
        terminal_settings = termios.tcgetattr(sys.stdin.fileno())

    pending = []
    i = 0
    while ipcrawler.pending_targets:
        pending.append(asyncio.create_task(scan_target(ipcrawler.pending_targets.pop(0))))
        i += 1
        if i >= num_initial_targets:
            break

    if not config["disable_keyboard_control"]:
        tty.setcbreak(sys.stdin.fileno())
        keyboard_monitor = asyncio.create_task(keyboard())

    timed_out = False
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=1)

        # If something failed in scan_target, ipcrawler.errors will be true.
        if ipcrawler.errors:
            cancel_all_tasks(None, None)
            sys.exit(1)

        # Check if global timeout has occurred.
        if config["timeout"] is not None:
            elapsed_seconds = round(time.time() - start_time)
            m, s = divmod(elapsed_seconds, 60)
            if m >= config["timeout"]:
                timed_out = True
                break

        for task in done:
            if ipcrawler.pending_targets:
                pending.add(asyncio.create_task(scan_target(ipcrawler.pending_targets.pop(0))))
            if task in pending:
                pending.remove(task)

        port_scan_task_count = 0
        for targ in ipcrawler.scanning_targets:
            for process_list in targ.running_tasks.values():
                # If we're not scanning ports, count ServiceScans instead.
                if config["force_services"]:
                    if issubclass(
                        process_list["plugin"].__class__, ServiceScan
                    ):  # TODO should we really count ServiceScans? Test...
                        port_scan_task_count += 1
                else:
                    if issubclass(process_list["plugin"].__class__, PortScan):
                        port_scan_task_count += 1

        num_new_targets = math.ceil((config["max_port_scans"] - port_scan_task_count) / port_scan_plugin_count)
        if num_new_targets > 0:
            i = 0
            while ipcrawler.pending_targets:
                pending.add(asyncio.create_task(scan_target(ipcrawler.pending_targets.pop(0))))
                i += 1
                if i >= num_new_targets:
                    break

    if not config["disable_keyboard_control"]:
        keyboard_monitor.cancel()

    # Stop progress manager
    progress_manager.stop()

    # Stop live scan loader
    stop_live_loader()

    # If there's only one target we don't need a combined report
    if len(ipcrawler.completed_targets) > 1:
        for plugin in ipcrawler.plugin_types["report"]:
            if config["reports"] and plugin.slug in config["reports"]:
                matching_tags = True
                excluded_tags = False
            else:
                plugin_tag_set = set(plugin.tags)

                matching_tags = False
                for tag_group in ipcrawler.tags:
                    if set(tag_group).issubset(plugin_tag_set):
                        matching_tags = True
                        break

                excluded_tags = False
                for tag_group in ipcrawler.excluded_tags:
                    if set(tag_group).issubset(plugin_tag_set):
                        excluded_tags = True
                        break

            if matching_tags and not excluded_tags:
                pending.add(asyncio.create_task(generate_report(plugin, ipcrawler.completed_targets)))

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=1)

    if timed_out:
        cancel_all_tasks(None, None)

        elapsed_time = calculate_elapsed_time(start_time)
        warn(
            "{byellow}ipcrawler took longer than the specified timeout period ("
            + str(config["timeout"])
            + " min). Cancelling all scans and exiting.{rst}"
        )
    else:
        while len(asyncio.all_tasks()) > 1:  # this code runs in the main() task so it will be the only task left running
            await asyncio.sleep(1)

        elapsed_time = calculate_elapsed_time(start_time)

        # Use enhanced scan summary
        target_count = len(ipcrawler.completed_targets)
        show_scan_summary(target_count, elapsed_time)

        # Fallback to standard message if Rich not available
        if not RICH_AVAILABLE or config["accessible"]:
            info("{bright}Finished scanning all targets in " + elapsed_time + "!{rst}")
            info(
                "{bright}Don't forget to check out more commands to run manually in the _manual_commands.txt file in each target's scans directory!"
            )

        # VHost Discovery Post-Processing
        if config.get("vhost_discovery", {}).get("enabled", True):
            try:
                from ipcrawler.vhost_post_processor import VHostPostProcessor
                from ipcrawler.io import vhost_manager

                # Check if any VHost files were created and collect all scan directories
                vhost_files_found = False
                scan_directories = []

                for target in ipcrawler.completed_targets:
                    scan_directories.append(target.scandir)
                    for root, dirs, files in os.walk(target.scandir):
                        if any(f.startswith("vhost_redirects_") and f.endswith(".txt") for f in files):
                            vhost_files_found = True

                # Run post-processing if:
                # 1. VHost files were found AND
                # 2. Auto-add was disabled in config OR auto-add failed due to no privileges
                vhost_config = config.get("vhost_discovery", {})
                auto_add_setting = vhost_config.get("auto_add_hosts", True)

                if vhost_files_found and (not auto_add_setting or not vhost_manager.auto_add_enabled):
                    if not auto_add_setting:
                        info("{bright}🌐 Running VHost Discovery Post-Processing (auto-add disabled)...{rst}")
                    else:
                        info("{bright}🌐 Running VHost Discovery Post-Processing (no privileges for auto-add)...{rst}")

                    # Pass all scan directories to the processor
                    processor = VHostPostProcessor(scan_directories)
                    processor.run_interactive_session()
                elif vhost_files_found and auto_add_setting and vhost_manager.auto_add_enabled:
                    info("{bright}🌐 VHosts discovered and auto-added during scanning. Check /etc/hosts for entries.{rst}")

            except ImportError:
                warn("VHost post-processor not available. Skipping VHost management.")
            except Exception as e:
                warn(f"VHost post-processing failed: {e}")

    if ipcrawler.missing_services:
        warn(
            "{byellow}ipcrawler identified the following services, but could not match them to any plugins based on the service name. Please report these to neur0map: "
            + ", ".join(ipcrawler.missing_services)
            + "{rst}"
        )

    if not config["disable_keyboard_control"]:
        # Restore original terminal settings.
        if terminal_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, terminal_settings)


def main():
    # Capture Ctrl+C and cancel everything.
    signal.signal(signal.SIGINT, cancel_all_tasks)
    try:
        asyncio.run(run())
    except asyncio.exceptions.CancelledError:
        pass
    except RuntimeError:
        pass


if __name__ == "__main__":
    main()
