"""Base console interface for IPCrawler"""

import os
from contextlib import contextmanager
from typing import Optional, Any, Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.box import ROUNDED, MINIMAL_HEAVY_HEAD
from rich.text import Text
from rich.align import Align

from ..themes.default import (
    IPCRAWLER_THEME, COLORS, ICONS, FORMATS,
    get_severity_style, get_severity_icon, get_status_style, get_status_icon,
    format_header, format_status, format_finding, format_label_value
)


class IPCrawlerConsole:
    """Centralized console interface for consistent output across IPCrawler"""
    
    def __init__(self,
                 stderr: bool = False,
                 force_terminal: Optional[bool] = None,
                 force_jupyter: Optional[bool] = None,
                 theme: Optional[str] = None):
        """Initialize console with configuration"""
        self.console = Console(
            stderr=stderr,
            force_terminal=force_terminal,
            force_jupyter=force_jupyter,
            theme=IPCRAWLER_THEME
        )
        self.theme = theme or "default"
    
    def _load_theme(self):
        """Load color theme configuration"""
        pass
    
    def print(self, *args, **kwargs):
        """Print to console with Rich formatting"""
        self.console.print(*args, **kwargs)
    
    def success(self, message: str, internal: bool = False, **kwargs):
        """Print success message"""
        formatted = format_status('success', message)
        self.console.print(formatted, **kwargs)
    
    def error(self, message: str, internal: bool = False, **kwargs):
        """Print error message"""
        formatted = format_status('error', message)
        self.console.print(formatted, **kwargs)
    
    def warning(self, message: str, internal: bool = False, **kwargs):
        """Print warning message"""
        formatted = format_status('warning', message)
        self.console.print(formatted, **kwargs)
    
    def info(self, message: str, internal: bool = False, **kwargs):
        """Print info message"""
        formatted = format_status('info', message)
        self.console.print(formatted, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Print critical message (always shown)"""
        formatted = format_status('critical', message)  
        self.console.print(formatted, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Print debug message (only shown in debug mode)"""
        if self._is_debug_enabled():
            formatted = format_status('debug', message)
            self.console.print(formatted, **kwargs)
    
    def _is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return os.getenv('DEBUG', '').lower() in ('1', 'true', 'yes')
    
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
            yield progress, task
    
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
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (required by Rich components)"""
        pass
        
    def display_privilege_escalation_prompt(self):
        """Display privilege escalation options in a clean table format"""
        
        # Header
        header = format_header("🔐 Enhanced Analysis Requires Elevated Privileges", style="header")
        self.console.print(header)
        self.console.print()
        
        table = Table(
            show_header=True,
            header_style="success",  # Use theme style instead of direct color
            box=ROUNDED,
            padding=(0, 1),
            expand=False
        )
        
        table.add_column("Feature", style="secondary", no_wrap=True)
        table.add_column("With Sudo", style="success", justify="center")
        table.add_column("Without Sudo", style="warning", justify="center")
        
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
        self.console.print()
    
    def display_target_resolution(self, target: str, target_type: str = None, resolved_ip: str = None, resolving: bool = False):
        """Display target resolution in a clean format with visual feedback"""
        
        if resolving:
            # Simple resolving message for all terminals
            self.info(f"Resolving target: {target}")
            return
        
        if target_type == 'ip':
            # Direct IP address
            content = f"[bold secondary]{target}[/bold secondary]\n[dim]Direct IP address[/dim]"
            panel = Panel(
                content,
                title=f"{ICONS['target']} Target",
                border_style="secondary",
                padding=(0, 2)
            )
            self.console.print(panel)
            
        elif target_type == 'cidr':
            # CIDR range
            content = f"[bold secondary]{target}[/bold secondary]\n[dim]CIDR network range[/dim]"
            panel = Panel(
                content,
                title=f"{ICONS['target']} Target",
                border_style="secondary",
                padding=(0, 2)
            )
            self.console.print(panel)
            
        elif resolved_ip:
            # Successfully resolved hostname
            content = f"[bold secondary]{target}[/bold secondary]\n[dim]↓[/dim]\n[bold primary]{resolved_ip}[/bold primary]"
            centered_content = Align.center(content)
            panel = Panel(
                centered_content,
                title=f"{ICONS['target']} Target Resolved",
                border_style="primary",
                padding=(0, 2)
            )
            self.console.print(panel)
        else:
            self.info(f"Target: {target}")
    
    def display_workflow_status(self, workflow: str, status: str, message: str = ""):
        """Display workflow progress with consistent formatting"""
        
        status_icons = {
            'starting': ICONS['rocket'],
            'running': ICONS['running'],
            'completed': ICONS['success'],
            'failed': ICONS['error'],
            'skipped': '⏭️'
        }
        
        status_styles = {
            'starting': 'bold_info',
            'running': 'bold_warning', 
            'completed': 'bold_success',
            'failed': 'bold_error',
            'skipped': 'bold_muted'
        }
        
        icon = status_icons.get(status, ICONS['bullet'])
        style = status_styles.get(status, 'default')
        
        table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
        table.add_column("Icon", width=2)
        table.add_column("Workflow", style=style)
        table.add_column("Details", style="muted")
        
        workflow_display = workflow.replace('_', ' ').title()
        
        table.add_row(icon, workflow_display, message)
        self.console.print(table)
    
    def display_smartlist_recommendations(self, smartlist_data: dict, detailed: bool = False):
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
        header = format_header(f"📋 SmartList Wordlist Recommendations", style="header")
        self.console.print(header)
        
        stats = f"[muted]{total_services} services analyzed • {total_wordlists} wordlists recommended • {high_confidence} high confidence[/muted]"
        self.console.print(stats)
        self.console.print()
        
        # Display recommendations by service
        for i, service_rec in enumerate(recommendations, 1):
            self._display_service_recommendation(service_rec, i, detailed)
        
        # Display usage tip
        self.console.print()
        self.console.print("[muted]💡 Tip: Wordlists are saved to workspaces/{target}/wordlists_for_{target}/[/muted]")
    
    def _display_service_recommendation(self, service_rec: Dict[str, Any], index: int, detailed: bool = False):
        """Display a single service recommendation"""
        service_name = service_rec.get('service', 'Unknown')
        service_display = service_rec.get('service_name', service_name)
        technology = service_rec.get('detected_technology', '')
        confidence = service_rec.get('confidence', 'LOW').upper()
        total_score = service_rec.get('total_score', 0)
        top_wordlists = service_rec.get('top_wordlists', [])
        
        
        # Confidence style mapping using theme styles
        confidence_styles = {
            'HIGH': 'success',
            'MEDIUM': 'warning', 
            'LOW': 'error'
        }
        confidence_style = confidence_styles.get(confidence, 'default')
        
        # Service header
        tech_display = f" ({technology})" if technology else ""
        confidence_badge = f"[{confidence_style}]{confidence}[/{confidence_style}]"
        
        self.console.print(f"[bold secondary]{index}. {service_display}{tech_display}[/bold secondary] {confidence_badge}")
        
        # Display wordlists (limit to 3 in normal mode, all in detailed mode)
        display_limit = len(top_wordlists) if detailed else min(3, len(top_wordlists))
        
        for wl in top_wordlists[:display_limit]:
            wl_name = wl.get('wordlist', 'Unknown')
            wl_confidence = wl.get('confidence', 'LOW')
            wl_reason = wl.get('reason', 'No reason provided')
            wl_score = wl.get('score', 0)
            
            wl_conf_style = confidence_styles.get(wl_confidence.upper(), 'default')
            confidence_indicator = f"[{wl_conf_style}]●[/{wl_conf_style}]"
            
            # Clean up wordlist name (remove path prefix if present)
            clean_name = wl_name.split('/')[-1] if '/' in wl_name else wl_name
            
            if detailed:
                # Truncate reason for brevity
                short_reason = wl_reason[:60] + "..." if len(wl_reason) > 60 else wl_reason
                self.console.print(f"   {confidence_indicator} [bold]{clean_name}[/bold] [muted]({short_reason})[/muted]")
            else:
                self.console.print(f"   {confidence_indicator} [bold]{clean_name}[/bold]")
        
        if len(top_wordlists) > display_limit:
            remaining = len(top_wordlists) - display_limit
            self.console.print(f"   [muted]... and {remaining} more wordlists[/muted]")
        
        self.console.print()
    
    def display_key_findings(self, data: dict):
        """Display key findings from scan"""
        hosts = data.get('hosts', [])
        if hosts:
            total_ports = sum(len(host.get('ports', [])) for host in hosts)
            open_ports = sum(len([p for p in host.get('ports', []) if p.get('state') == 'open']) for host in hosts)
            self.info(f"🔍 Found {len(hosts)} hosts, {open_ports} open ports")
    
    def display_scan_summary(self, data: dict):
        """Display a clean scan summary focused on key findings"""
        target = data.get('target', 'Unknown')
        
        # Header
        header = format_header(f"📊 Scan Summary - {target}", style="header")
        self.console.print(header)
        self.console.print()
        
        hosts = data.get('hosts', [])
        total_hosts = len(hosts)
        up_hosts = len([h for h in hosts if h.get('status') == 'up'])
        
        total_ports = 0
        open_ports = 0
        services = set()
        
        for host in hosts:
            ports = host.get('ports', [])
            total_ports += len(ports)
            for port in ports:
                if port.get('state') == 'open':
                    open_ports += 1
                    service = port.get('service', 'unknown')
                    if service != 'unknown':
                        services.add(service)
        
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
        
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Metric", style="secondary")
        summary_table.add_column("Value", style="success")
        
        summary_table.add_row("Hosts Discovered", f"{up_hosts}/{total_hosts}")
        summary_table.add_row("Open Ports", f"{open_ports}")
        summary_table.add_row("Services Identified", f"{len(services)}")
        summary_table.add_row("HTTP Services", f"{http_services}")
        summary_table.add_row("Security Findings", f"{vulnerabilities}")
        summary_table.add_row("URLs Discovered", f"{discovered_urls}")
        summary_table.add_row("Wordlist Recommendations", f"{wordlist_recs}")
        
        self.console.print(summary_table)
        self.console.print()
        
        # Display key findings
        self._display_key_findings_brief(data)
    
    def _display_key_findings_brief(self, data: dict):
        """Display only the most important findings to avoid clutter"""
        findings = []
        
        # High-priority vulnerabilities
        http_scan = data.get('http_scan', {})
        if 'vulnerabilities' in http_scan:
            high_vulns = [v for v in http_scan['vulnerabilities'] 
                         if v.get('severity', '').lower() in ['critical', 'high']]
            if high_vulns:
                findings.append(f"🚨 {len(high_vulns)} critical/high severity findings")
        
        # Interesting services
        hosts = data.get('hosts', [])
        interesting_services = set()
        for host in hosts:
            for port in host.get('ports', []):
                if port.get('state') == 'open':
                    service = (port.get('service') or '').lower()
                    if service in ['ssh', 'ftp', 'telnet', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch']:
                        interesting_services.add(service)
        
        if interesting_services:
            services_str = ", ".join(sorted(interesting_services)[:3])
            if len(interesting_services) > 3:
                services_str += f" (+{len(interesting_services)-3} more)"
            findings.append(f"🔍 Interesting services: {services_str}")
        
        # URLs discovered
        mini_spider = data.get('mini_spider', {})
        url_count = mini_spider.get('total_discovered_urls', 0)
        if url_count > 0:
            findings.append(f"🕷️  {url_count} URLs discovered")
        
        # Display findings if any
        if findings:
            self.console.print("[bold]Key Findings:[/bold]")
            for finding in findings:
                self.console.print(f"  {finding}")
            self.console.print()
    
    def display_spider_summary(self, spider_data: dict):
        """Display Mini Spider findings summary"""
        discovered_urls = spider_data.get('discovered_urls', [])
        interesting_findings = spider_data.get('interesting_findings', [])
        
        if not discovered_urls:
            return
        
        # Show only critical and high priority findings
        if interesting_findings:
            critical_findings = [f for f in interesting_findings if f.get('severity') == 'critical']
            high_findings = [f for f in interesting_findings if f.get('severity') == 'high']
            
            if critical_findings:
                self.print(f"🚨 {len(critical_findings)} Critical findings")
                for finding in critical_findings[:3]:
                    self.print(f"  • {finding.get('finding_type', 'Unknown')}: {finding.get('url', '')}")
            
            if high_findings:
                self.print(f"⚠️  {len(high_findings)} High priority findings")
                for finding in high_findings[:2]:
                    self.print(f"  • {finding.get('finding_type', 'Unknown')}: {finding.get('url', '')}")
    
    def display_http_summary(self, http_data: dict):
        """Display summary of HTTP scan findings"""
        if not http_data:
            return
        
        # Vulnerabilities summary
        vuln_summary = http_data.get('summary', {}).get('severity_counts', {})
        total_vulns = sum(vuln_summary.values())
        
        if total_vulns > 0:
            self.print(f"\n[yellow]⚠ Found {total_vulns} potential vulnerabilities:[/yellow]")
            if vuln_summary.get('critical', 0) > 0:
                self.print(f"  [red]● Critical: {vuln_summary['critical']}[/red]")
            if vuln_summary.get('high', 0) > 0:
                self.print(f"  [red]● High: {vuln_summary['high']}[/red]")
            if vuln_summary.get('medium', 0) > 0:
                self.print(f"  [yellow]● Medium: {vuln_summary['medium']}[/yellow]")
            if vuln_summary.get('low', 0) > 0:
                self.print(f"  [blue]● Low: {vuln_summary['low']}[/blue]")
        
        # Technologies detected
        techs = http_data.get('summary', {}).get('technologies', [])
        if techs:
            self.print(f"\n[secondary]Technologies detected:[/secondary] {', '.join(techs)}")
        
        # Discovered paths
        paths = http_data.get('summary', {}).get('discovered_paths', [])
        if paths:
            self.print(f"\n[success]Discovered {len(paths)} paths[/success]")
            for path in paths[:5]:  # Show first 5
                self.print(f"  • {path}")
            if len(paths) > 5:
                self.print(f"  ... and {len(paths) - 5} more")
        
        # Subdomains
        subdomains = http_data.get('subdomains', [])
        if subdomains:
            self.print(f"\n[magenta]Found {len(subdomains)} subdomains[/magenta]")
            for subdomain in subdomains[:5]:  # Show first 5
                self.print(f"  • {subdomain}")
            if len(subdomains) > 5:
                self.print(f"  ... and {len(subdomains) - 5} more")
    
    def display_minimal_summary(self, data: dict, workspace: 'Path'):
        """Display clean analysis summary"""
        from pathlib import Path
        
        # Display key findings first
        self.display_key_findings(data)
        
        # Display SmartList recommendations (main focus)
        smartlist_data = data.get('smartlist', {})
        if smartlist_data:
            self.display_smartlist_recommendations(smartlist_data)
        
        # Display scan summary
        self.display_scan_summary(data)
        
        # Add workspace info with new structure
        self.print(f"\n[dim]📁 Results saved to: [secondary]{workspace}[/secondary][/dim]")
        self.print("[dim]   ├── nmap_fast_01_results.json    (Port discovery data)[/dim]")
        self.print("[dim]   ├── nmap_02_results.json         (Service fingerprinting data)[/dim]")
        self.print("[dim]   ├── http_03_results.json         (HTTP analysis data)[/dim]")
        self.print("[dim]   ├── mini_spider_04_results.json  (URL discovery data)[/dim]")
        self.print("[dim]   ├── smartlist_05_results.json    (Wordlist recommendations data)[/dim]")
        self.print("[dim]   ├── master_report.txt            (📊 Comprehensive TXT report)[/dim]")
        self.print("[dim]   └── wordlists_for_{target}/      (📋 Recommended wordlists)[/dim]")
    
    def __getattr__(self, name):
        """Delegate any missing attributes to the underlying Rich Console"""
        return getattr(self.console, name)


# Global console instance
console = IPCrawlerConsole()


# Convenience functions
def success(message: str, **kwargs):
    """Print success message"""
    console.success(message, **kwargs)


def error(message: str, **kwargs):
    """Print error message"""
    console.error(message, **kwargs)


def warning(message: str, **kwargs):
    """Print warning message"""
    console.warning(message, **kwargs)


def info(message: str, **kwargs):
    """Print info message"""
    console.info(message, **kwargs)


def critical(message: str, **kwargs):
    """Print critical message"""
    console.critical(message, **kwargs)


def debug(message: str, **kwargs):
    """Print debug message"""
    console.debug(message, **kwargs)