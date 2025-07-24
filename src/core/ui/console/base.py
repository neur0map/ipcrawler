"""Base console interface for IPCrawler

Provides a centralized interface for all console output operations.
"""

from typing import Any, Optional, Dict, List, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from contextlib import contextmanager
import sys


class IPCrawlerConsole:
    """Centralized console interface for consistent output across IPCrawler"""
    
    def __init__(self, 
                 stderr: bool = False,
                 force_terminal: Optional[bool] = None,
                 force_jupyter: Optional[bool] = None,
                 theme: Optional[str] = None):
        """Initialize console with configuration
        
        Args:
            stderr: Whether to output to stderr instead of stdout
            force_terminal: Force terminal mode
            force_jupyter: Force Jupyter mode
            theme: Color theme to use
        """
        self.console = Console(
            stderr=stderr,
            force_terminal=force_terminal,
            force_jupyter=force_jupyter
        )
        self.theme = theme or "default"
        self._load_theme()
    
    def _load_theme(self):
        """Load color theme configuration"""
        # Theme will be loaded from themes module
        pass
    
    def print(self, *args, **kwargs):
        """Print to console with Rich formatting"""
        self.console.print(*args, **kwargs)
    
    def success(self, message: str, internal: bool = False, **kwargs):
        """Print success message
        
        Args:
            message: Message to print
            internal: If True, only show in debug mode (for internal operations)
            **kwargs: Additional Rich formatting options
        """
        if internal and not self._is_debug_enabled():
            return
        self.console.print(f"✅ {message}", style="green", **kwargs)
    
    def error(self, message: str, internal: bool = False, **kwargs):
        """Print error message
        
        Args:
            message: Message to print
            internal: If True, only show in debug mode (for internal operations)
            **kwargs: Additional Rich formatting options
        """
        if internal and not self._is_debug_enabled():
            return
        self.console.print(f"❌ {message}", style="red", **kwargs)
    
    def warning(self, message: str, internal: bool = False, **kwargs):
        """Print warning message
        
        Args:
            message: Message to print
            internal: If True, only show in debug mode (for internal operations)
            **kwargs: Additional Rich formatting options
        """
        if internal and not self._is_debug_enabled():
            return
        self.console.print(f"⚠️  {message}", style="yellow", **kwargs)
    
    def info(self, message: str, internal: bool = False, **kwargs):
        """Print info message
        
        Args:
            message: Message to print
            internal: If True, only show in debug mode (for internal operations)
            **kwargs: Additional Rich formatting options
        """
        if internal and not self._is_debug_enabled():
            return
        self.console.print(f"ℹ️  {message}", style="blue", **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Print critical message (always shown)"""
        self.console.print(f"🚨 {message}", style="bold red", **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Print debug message (only shown in debug mode)"""
        if self._is_debug_enabled():
            self.console.print(f"🐛 {message}", style="dim", **kwargs)
    
    def _is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        try:
            from ...utils.debugging import is_debug_enabled
            return is_debug_enabled()
        except ImportError:
            return False
    
    def rule(self, title: Optional[str] = None, **kwargs):
        """Print a horizontal rule"""
        self.console.rule(title, **kwargs)
    
    def panel(self, content: Any, title: Optional[str] = None, **kwargs):
        """Display content in a panel"""
        panel = Panel(content, title=title, **kwargs)
        self.console.print(panel)
    
    def table(self, title: Optional[str] = None, **kwargs) -> Table:
        """Create a new table"""
        return Table(title=title, **kwargs)
    
    def print_table(self, table: Table):
        """Print a table to console"""
        self.console.print(table)
    
    def code(self, code: str, lexer: str = "python", **kwargs):
        """Print syntax-highlighted code"""
        syntax = Syntax(code, lexer, **kwargs)
        self.console.print(syntax)
    
    @contextmanager
    def progress(self, description: str = "Processing..."):
        """Context manager for progress display"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(description, total=None)
            yield progress
    
    @contextmanager
    def status(self, status: str, spinner: str = "dots"):
        """Context manager for status display"""
        with self.console.status(status, spinner=spinner):
            yield
    
    def clear(self):
        """Clear the console"""
        self.console.clear()
    
    def save_html(self, path: str, clear: bool = True):
        """Save console output as HTML"""
        self.console.save_html(path, clear=clear)
    
    def save_text(self, path: str, clear: bool = True):
        """Save console output as text"""
        self.console.save_text(path, clear=clear)
    
    def get_time(self):
        """Get current time (required by Rich Progress)"""
        return self.console.get_time()
    
    def __enter__(self):
        """Context manager entry (required by Rich components)"""
        return self.console.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (required by Rich components)"""
        return self.console.__exit__(exc_type, exc_val, exc_tb)
        
    def __getattr__(self, name):
        """Delegate any missing attributes to the underlying Rich Console"""
        return getattr(self.console, name)
    
    # === Specialized Display Methods ===
    
    def display_section_header(self, title: str, icon: str = "🎯", subtitle: str = None):
        """Display a clean section header with proper spacing"""
        self.console.print()  # Add spacing
        header_text = f"{icon} [bold cyan]{title}[/bold cyan]"
        if subtitle:
            header_text += f"\n[dim]{subtitle}[/dim]"
        
        self.console.print(Panel(
            header_text,
            border_style="cyan",
            padding=(0, 1)
        ))
    
    def display_smartlist_recommendations(self, smartlist_data: Dict[str, Any], detailed: bool = False):
        """Display SmartList wordlist recommendations in a clean, readable format"""
        recommendations = smartlist_data.get('wordlist_recommendations', [])
        if not recommendations:
            self.warning("No wordlist recommendations available")
            return
        
        # Calculate summary stats
        total_services = len(recommendations)
        total_wordlists = sum(len(rec.get('top_wordlists', [])) for rec in recommendations)
        high_confidence = sum(1 for rec in recommendations if rec.get('confidence', '').upper() == 'HIGH')
        
        # Display header with stats
        stats = f"[dim]{total_services} services analyzed • {total_wordlists} wordlists recommended • {high_confidence} high confidence[/dim]"
        self.display_section_header("SmartList Wordlist Recommendations", "📋", stats)
        
        # Display recommendations by service
        for i, service_rec in enumerate(recommendations, 1):
            self._display_service_recommendation(service_rec, i, detailed)
        
        # Display usage tip
        if not detailed and any(len(rec.get('top_wordlists', [])) > 2 for rec in recommendations):
            self.console.print("\n[dim]💡 Tip: Use --detailed flag for complete wordlist recommendations[/dim]")
    
    def _display_service_recommendation(self, service_rec: Dict[str, Any], index: int, detailed: bool = False):
        """Display a single service recommendation"""
        service_name = service_rec.get('service', 'Unknown')
        service_display = service_rec.get('service_name', service_name)
        technology = service_rec.get('detected_technology', '')
        confidence = service_rec.get('confidence', 'LOW').upper()
        total_score = service_rec.get('total_score', 0)
        top_wordlists = service_rec.get('top_wordlists', [])
        
        if not top_wordlists:
            return
        
        # Confidence color mapping
        confidence_colors = {
            'HIGH': 'green',
            'MEDIUM': 'yellow', 
            'LOW': 'red'
        }
        confidence_color = confidence_colors.get(confidence, 'white')
        
        # Service header
        tech_display = f" ({technology})" if technology else ""
        confidence_badge = f"[{confidence_color}]{confidence}[/{confidence_color}]"
        
        self.console.print(f"\n[bold]{index}. {service_display}[/bold]{tech_display}")
        self.console.print(f"   Confidence: {confidence_badge} | Score: [dim]{total_score}[/dim]")
        
        # Display wordlists (limit to 3 in normal mode, all in detailed mode)
        display_limit = len(top_wordlists) if detailed else min(3, len(top_wordlists))
        
        for j, wordlist in enumerate(top_wordlists[:display_limit], 1):
            wl_name = wordlist.get('wordlist', 'Unknown')
            wl_confidence = wordlist.get('confidence', 'LOW')
            wl_reason = wordlist.get('reason', 'No reason provided')
            wl_score = wordlist.get('score', 0)
            
            wl_conf_color = confidence_colors.get(wl_confidence.upper(), 'white')
            confidence_indicator = f"[{wl_conf_color}]●[/{wl_conf_color}]"
            
            # Clean up wordlist name (remove path prefix if present)
            clean_name = wl_name.split('/')[-1] if '/' in wl_name else wl_name
            
            self.console.print(f"   {confidence_indicator} [cyan]{clean_name}[/cyan] [dim]({wl_score})[/dim]")
            if detailed:
                self.console.print(f"     [dim]{wl_reason}[/dim]")
            else:
                # Truncate reason for brevity
                short_reason = wl_reason[:60] + "..." if len(wl_reason) > 60 else wl_reason
                self.console.print(f"     [dim]{short_reason}[/dim]")
        
        if len(top_wordlists) > display_limit:
            remaining = len(top_wordlists) - display_limit
            self.console.print(f"   [dim]... and {remaining} more wordlists[/dim]")
    
    def display_scan_summary(self, data: Dict[str, Any]):
        """Display a clean scan summary focused on key findings"""
        target = data.get('target', 'Unknown')
        
        # Collect key metrics
        hosts = data.get('hosts', [])
        total_hosts = len(hosts)
        up_hosts = len([h for h in hosts if h.get('status') == 'up'])
        
        # Count services and ports
        total_ports = 0
        open_ports = 0
        services = set()
        
        for host in hosts:
            ports = host.get('ports', [])
            total_ports += len(ports)
            for port in ports:
                if port.get('state') == 'open':
                    open_ports += 1
                    if port.get('service'):
                        services.add(port['service'])
        
        # HTTP findings
        http_scan = data.get('http_scan', {})
        vulnerabilities = len(http_scan.get('vulnerabilities', []))
        http_services = len(http_scan.get('services', []))
        
        # SmartList findings
        smartlist = data.get('smartlist', {})
        wordlist_recs = len(smartlist.get('wordlist_recommendations', []))
        
        # Mini Spider findings
        mini_spider = data.get('mini_spider', {})
        discovered_urls = mini_spider.get('total_discovered_urls', 0)
        
        # Create summary table
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="bold white")
        
        summary_table.add_row("Target", target)
        if total_hosts > 0:
            summary_table.add_row("Hosts Up", f"{up_hosts}/{total_hosts}")
            summary_table.add_row("Open Ports", f"{open_ports}")
            summary_table.add_row("Services", f"{len(services)}")
        if http_services > 0:
            summary_table.add_row("HTTP Services", f"{http_services}")
        if vulnerabilities > 0:
            summary_table.add_row("Vulnerabilities", f"[red]{vulnerabilities}[/red]")
        if discovered_urls > 0:
            summary_table.add_row("URLs Discovered", f"{discovered_urls}")
        if wordlist_recs > 0:
            summary_table.add_row("Wordlist Recommendations", f"[green]{wordlist_recs}[/green]")
        
        self.display_section_header("Scan Summary", "📊")
        self.console.print(summary_table)
    
    def display_key_findings(self, data: Dict[str, Any]):
        """Display only the most important findings to avoid clutter"""
        findings = []
        
        # High-priority vulnerabilities
        http_scan = data.get('http_scan', {})
        if 'vulnerabilities' in http_scan:
            high_vulns = [v for v in http_scan['vulnerabilities'] 
                         if v.get('severity', '').lower() in ['critical', 'high']]
            if high_vulns:
                findings.append(f"🚨 {len(high_vulns)} high-priority vulnerabilities found")
        
        # Interesting services
        hosts = data.get('hosts', [])
        interesting_services = set()
        for host in hosts:
            for port in host.get('ports', []):
                if port.get('state') == 'open':
                    service = port.get('service', '').lower()
                    if service in ['ssh', 'ftp', 'telnet', 'smtp', 'pop3', 'imap', 'mysql', 'postgresql', 'mssql', 'oracle']:
                        interesting_services.add(f"{service}:{port.get('port')}")
        
        if interesting_services:
            services_str = ", ".join(sorted(interesting_services)[:3])
            if len(interesting_services) > 3:
                services_str += f" (+{len(interesting_services)-3} more)"
            findings.append(f"🔍 Notable services: {services_str}")
        
        # URLs discovered
        mini_spider = data.get('mini_spider', {})
        url_count = mini_spider.get('total_discovered_urls', 0)
        if url_count > 10:
            findings.append(f"🕷️  {url_count} URLs discovered")
        
        # Display findings if any
        if findings:
            self.display_section_header("Key Findings", "⚡")
            for finding in findings[:3]:  # Limit to top 3 findings
                self.console.print(f"  {finding}")
    
    def display_workflow_status(self, workflow: str, status: str, message: str = ""):
        """Display workflow progress with consistent formatting"""
        from rich.table import Table
        from rich.box import SIMPLE
        
        status_icons = {
            'starting': '🚀',
            'running': '⚙️',
            'completed': '✅',
            'failed': '❌',
            'skipped': '⏭️'
        }
        
        status_colors = {
            'starting': 'blue',
            'running': 'yellow', 
            'completed': 'green',
            'failed': 'red',
            'skipped': 'dim'
        }
        
        icon = status_icons.get(status, '•')
        color = status_colors.get(status, 'white')
        
        # Create a simple inline table for cleaner display
        table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
        table.add_column("Icon", width=2)
        table.add_column("Workflow", style=f"bold {color}")
        table.add_column("Details", style="dim")
        
        workflow_display = workflow.replace('_', ' ').title()
        table.add_row(icon, workflow_display, message if message else "")
        
        self.console.print()
        self.console.print(table)
    
    def display_progress_summary(self, current_step: int, total_steps: int, step_name: str):
        """Display clean progress indicator"""
        progress_bar = "█" * current_step + "░" * (total_steps - current_step)
        percentage = int((current_step / total_steps) * 100)
        
        self.console.print(f"[cyan]{progress_bar}[/cyan] {percentage}% [dim]({current_step}/{total_steps})[/dim] {step_name}")
    
    def display_quiet_mode_summary(self, data: Dict[str, Any]):
        """Display minimal summary for quiet mode - focus only on SmartList results"""
        target = data.get('target', 'Unknown')
        
        self.console.print(f"\n[bold cyan]IPCrawler Results for {target}[/bold cyan]")
        
        # Just show SmartList recommendations
        smartlist_data = data.get('smartlist', {})
        if smartlist_data:
            self.display_smartlist_recommendations(smartlist_data)
        else:
            self.warning("No wordlist recommendations generated")
        
        # Show critical findings only
        http_scan = data.get('http_scan', {})
        if 'vulnerabilities' in http_scan:
            critical_vulns = [v for v in http_scan['vulnerabilities'] 
                             if v.get('severity', '').lower() == 'critical']
            if critical_vulns:
                self.console.print(f"\n🚨 [red]{len(critical_vulns)} critical vulnerabilities found[/red]")
                for vuln in critical_vulns[:2]:  # Show max 2
                    self.console.print(f"  • {vuln.get('title', 'Unknown vulnerability')}")
        
        self.console.print()  # Final spacing
    
    def display_target_resolution(self, target: str, target_type: str = None, resolved_ip: str = None, resolving: bool = False):
        """Display target resolution in a clean format with visual feedback
        
        Args:
            target: The target hostname/IP/CIDR
            target_type: Type of target ('ip', 'cidr', 'hostname', or None for resolving)
            resolved_ip: The resolved IP address (for hostnames)
            resolving: Whether we're currently resolving (shows simple message)
        """
        from rich.panel import Panel
        from rich.align import Align
        
        if resolving:
            # Simple resolving message for all terminals
            self.console.print(f"\n[bold cyan]Resolving {target}...[/bold cyan]")
            return
        
        if target_type == 'ip':
            # Direct IP address
            content = f"[bold cyan]{target}[/bold cyan]\n[dim]Direct IP address[/dim]"
            panel = Panel(
                Align.center(content),
                title="🎯 Target",
                border_style="cyan",
                padding=(0, 2)
            )
            self.console.print(panel)
            
        elif target_type == 'cidr':
            # CIDR range
            content = f"[bold cyan]{target}[/bold cyan]\n[dim]CIDR network range[/dim]"
            panel = Panel(
                Align.center(content),
                title="🎯 Target",
                border_style="cyan",
                padding=(0, 2)
            )
            self.console.print(panel)
            
        elif resolved_ip:
            # Successfully resolved hostname
            content = f"[bold cyan]{target}[/bold cyan]\n[dim]↓[/dim]\n[bold green]{resolved_ip}[/bold green]"
            panel = Panel(
                Align.center(content),
                title="🎯 Target Resolved",
                border_style="green",
                padding=(0, 2)
            )
            self.console.print(panel)
    
    def safe_status(self, message: str, spinner: str = "dots"):
        """Create a safe status display that works in all terminals
        
        Note: Some macOS terminals (like Terminal.app) may not display spinners
        correctly. This method provides fallbacks for better compatibility.
        
        Args:
            message: Status message to display
            spinner: Spinner type (defaults to 'dots')
            
        Returns:
            Status context manager or None for unsupported terminals
        """
        # Check if terminal supports advanced features
        if not self.console.is_terminal or self.console.is_dumb_terminal:
            # Fallback for basic terminals
            self.console.print(message)
            return None
        
        # For terminals that might not support spinners well (like macOS Terminal.app)
        # we can use a simpler spinner or just the message
        if self._is_basic_terminal():
            # Use simpler spinner or no spinner
            return self.console.status(message, spinner=None)
        
        # Full featured terminals get the nice spinner
        return self.console.status(message, spinner=spinner)
    
    def _is_basic_terminal(self) -> bool:
        """Detect if we're running in a basic terminal that might not support spinners well"""
        import os
        term = os.environ.get('TERM', '').lower()
        term_program = os.environ.get('TERM_PROGRAM', '').lower()
        
        # Known terminals with limited spinner support
        basic_terminals = ['dumb', 'cons25', 'emacs']
        basic_programs = ['apple_terminal', 'terminal.app']
        
        return (term in basic_terminals or 
                term_program in basic_programs or
                term.startswith('screen') and not term.endswith('256color'))
    
    def safe_progress(self, *columns, **kwargs):
        """Create a safe progress display that works in all terminals
        
        Returns a Progress object configured for the current terminal capabilities
        """
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        
        # Check terminal capabilities
        if not self.console.is_terminal or self.console.is_dumb_terminal:
            # Return None for basic terminals - caller should handle
            return None
        
        # For basic terminals, use simpler progress without spinners
        if self._is_basic_terminal():
            # Use simple progress without spinner
            if not columns:
                columns = (
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                )
            # Remove SpinnerColumn if present
            columns = tuple(col for col in columns if not isinstance(col, SpinnerColumn))
        else:
            # Full featured terminals get all the bells and whistles
            if not columns:
                columns = (
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                )
        
        return Progress(*columns, console=self.console, **kwargs)
    
    def display_simple_message(self, message: str, style: str = ""):
        """Display a simple message that works in all terminals
        
        Args:
            message: Message to display
            style: Rich style to apply (optional)
        """
        if style:
            self.console.print(f"[{style}]{message}[/{style}]")
        else:
            self.console.print(message)
    
    def display_privilege_escalation_prompt(self):
        """Display privilege escalation options in a clean table format"""
        from rich.box import ROUNDED
        
        # Header
        self.console.print("\n🔒 [bold]Privilege Escalation Available[/bold]\n")
        
        # Create comparison table
        table = Table(
            show_header=True,
            header_style="bold",
            box=ROUNDED,
            padding=(0, 1),
            expand=False
        )
        
        # Add columns
        table.add_column("Feature", style="cyan", no_wrap=True)
        table.add_column("With Sudo", style="green", justify="center")
        table.add_column("Without Sudo", style="yellow", justify="center")
        
        # Add feature comparison rows
        table.add_row(
            "Scanning Method",
            "SYN stealth (fast, accurate)",
            "TCP connect (slower)"
        )
        table.add_row(
            "OS Detection",
            "✓ Full fingerprinting",
            "✗ Not available"
        )
        table.add_row(
            "Timing Control",
            "✓ Advanced optimization",
            "Limited"
        )
        table.add_row(
            "Raw Sockets",
            "✓ Direct access",
            "✗ No access"
        )
        table.add_row(
            "Service Detection",
            "✓ Enhanced accuracy",
            "Basic"
        )
        table.add_row(
            "Hostname Resolution",
            "✓ Auto /etc/hosts update",
            "Manual only"
        )
        table.add_row(
            "Port Scan Speed",
            "~10x faster",
            "Standard"
        )
        
        self.console.print(table)
        self.console.print()  # Add spacing before prompt


# Global console instance
console = IPCrawlerConsole()


# Convenience functions
def print_success(message: str, **kwargs):
    """Print success message"""
    console.success(message, **kwargs)


def print_error(message: str, **kwargs):
    """Print error message"""
    console.error(message, **kwargs)


def print_warning(message: str, **kwargs):
    """Print warning message"""
    console.warning(message, **kwargs)


def print_info(message: str, **kwargs):
    """Print info message"""
    console.info(message, **kwargs)


def print_critical(message: str, **kwargs):
    """Print critical message"""
    console.critical(message, **kwargs)


def print_debug(message: str, **kwargs):
    """Print debug message"""
    console.debug(message, **kwargs)