"""
Base console interface for IPCrawler

IPCrawler SmartList Engine - Intelligent wordlist recommendations
GitHub: https://github.com/ipcrawler/ipcrawler
Support: https://patreon.com/ipcrawler
"""

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
        """Display detailed privilege escalation comparison"""
        self.console.print("\n🔐 [bold warning]Sudo Required for Enhanced Scanning[/bold warning]")
        self.console.print("[dim]" + "─" * 55 + "[/dim]")
        
        # Create comparison table
        table = Table(
            show_header=True,
            header_style="primary",
            box=MINIMAL_HEAVY_HEAD,
            padding=(0, 1),
            expand=False
        )
        
        table.add_column("Feature", style="secondary", width=20)
        table.add_column("Without Sudo", style="error", justify="center", width=15)
        table.add_column("With Sudo", style="success", justify="center", width=15)
        
        table.add_row(
            "Scan Method",
            "TCP Connect",
            "SYN Stealth"
        )
        table.add_row(
            "Speed",
            "~2-5 min",
            "~15-30 sec"
        )
        table.add_row(
            "Detection Risk",
            "Higher",
            "Lower"
        )
        table.add_row(
            "OS Detection",
            "❌ Disabled",
            "✅ Full Info"
        )
        table.add_row(
            "Service Accuracy",
            "Basic",
            "Enhanced"
        )
        table.add_row(
            "/etc/hosts Update",
            "❌ Manual",
            "✅ Automatic"
        )
        table.add_row(
            "Raw Socket Access",
            "❌ None",
            "✅ Full"
        )
        
        self.console.print(table)
        
        # Impact summary
        self.console.print("\n[bold error]⚠️  Without Sudo You'll Miss:[/bold error]")
        self.console.print("  • [error]90% slower scanning[/error] (TCP connect vs SYN stealth)")
        self.console.print("  • [error]No OS fingerprinting[/error] (can't identify target OS)")
        self.console.print("  • [error]Higher detection chance[/error] (more intrusive scanning)")
        self.console.print("  • [error]Manual hostname setup[/error] (no automatic /etc/hosts)")
        self.console.print("  • [error]Limited service detection[/error] (basic vs enhanced)")
        
        self.console.print("\n[dim]💡 Run with 'sudo ipcrawler scan <target>' for optimal results[/dim]\n")
    
    def display_target_resolution(self, target: str, target_type: str = None, resolved_ip: str = None, resolving: bool = False):
        """Display target resolution with enhanced visual presentation"""
        
        if resolving:
            return  # Don't show resolving message - too verbose
        
        self.console.print("\n" + "─" * 50)
        
        if resolved_ip and target != resolved_ip:
            # Hostname resolved to IP
            self.console.print(f"🎯 [bold primary]Target:[/bold primary] [secondary]{target}[/secondary] → [primary]{resolved_ip}[/primary]")
        else:
            # Direct IP or hostname
            target_icon = "🌐" if target_type == 'ip' else "🎯"
            self.console.print(f"{target_icon} [bold primary]Target:[/bold primary] [primary]{target}[/primary]")
        
        self.console.print("─" * 50)
    
    def display_workflow_status(self, workflow: str, status: str, message: str = ""):
        """Display workflow progress with enhanced visual formatting"""
        
        # Only show starting status for major workflows
        if status != 'starting':
            return
            
        workflow_config = {
            'port_discovery': {'name': 'Port Discovery', 'icon': '🔍', 'style': 'bold primary'},
            'service_analysis': {'name': 'Service Analysis', 'icon': '🔧', 'style': 'bold secondary'},
            'http_analysis': {'name': 'HTTP Analysis', 'icon': '🌐', 'style': 'bold info'},
            'mini_spider': {'name': 'URL Discovery', 'icon': '🕷️', 'style': 'bold warning'},
            'smartlist_analysis': {'name': 'SmartList Analysis', 'icon': '📋', 'style': 'bold success'}
        }
        
        config = workflow_config.get(workflow, {
            'name': workflow.replace('_', ' ').title(),
            'icon': '⚙️',
            'style': 'bold'
        })
        
        # Enhanced visual presentation
        self.console.print(f"\n{config['icon']} [{config['style']}]{config['name']}[/{config['style']}]")
        if message:
            self.console.print(f"   [dim]{message}[/dim]")
    
    def display_smartlist_recommendations(self, smartlist_data: dict, detailed: bool = False):
        """Display SmartList wordlist recommendations with enhanced presentation"""
        recommendations = smartlist_data.get('wordlist_recommendations', [])
        
        if not recommendations:
            return
        
        # Only show high-confidence recommendations by default
        high_conf_recs = [rec for rec in recommendations if rec.get('confidence', '').upper() == 'HIGH']
        
        if not high_conf_recs and not detailed:
            # If no high-confidence, show top 3 medium confidence
            medium_conf_recs = [rec for rec in recommendations if rec.get('confidence', '').upper() == 'MEDIUM'][:3]
            if medium_conf_recs:
                recommendations = medium_conf_recs
            else:
                return
        else:
            recommendations = high_conf_recs if not detailed else recommendations[:5]
        
        # Enhanced header with visual elements
        self.console.print(f"\n📋 [bold success]Recommended Wordlists[/bold success]")
        self.console.print("[dim]" + "─" * 30 + "[/dim]")
        
        # Display recommendations by service
        for service_rec in recommendations:
            self._display_service_recommendation_minimal(service_rec)
    
    def _display_service_recommendation_minimal(self, service_rec: Dict[str, Any]):
        """Display a single service recommendation with enhanced formatting"""
        service_display = service_rec.get('service_name', service_rec.get('service', 'Unknown'))
        technology = service_rec.get('detected_technology', '')
        confidence = service_rec.get('confidence', 'LOW').upper()
        top_wordlists = service_rec.get('top_wordlists', [])[:3]  # Show max 3
        
        if not top_wordlists:
            return
        
        # Confidence indicators with colors
        confidence_styles = {
            'HIGH': ('🟢', 'success'),
            'MEDIUM': ('🟡', 'warning'),
            'LOW': ('🔴', 'error')
        }
        
        conf_icon, conf_style = confidence_styles.get(confidence, ('⚪', 'muted'))
        
        # Service header with enhanced styling
        tech_display = f" [dim]({technology})[/dim]" if technology else ""
        self.console.print(f"\n  {conf_icon} [bold secondary]{service_display}[/bold secondary]{tech_display} [{conf_style}]{confidence}[/{conf_style}]")
        
        # Show wordlist names with bullet points
        for wl in top_wordlists:
            wl_name = wl.get('wordlist', 'Unknown').split('/')[-1]  # Just filename
            self.console.print(f"    [primary]▸[/primary] [bold]{wl_name}[/bold]")
    
    def display_key_findings(self, data: dict):
        """Display key findings from scan"""
        # This method is now redundant - functionality moved to other methods
        pass
    
    def display_scan_summary(self, data: dict):
        """Display an enhanced scan summary with visual elements"""
        target = data.get('target', 'Unknown')
        
        # Gather essential metrics
        hosts = data.get('hosts', [])
        open_ports = sum(len([p for p in h.get('ports', []) if p.get('state') == 'open']) for h in hosts)
        
        http_scan = data.get('http_scan', {})
        vulnerabilities = len(http_scan.get('vulnerabilities', []))
        
        mini_spider = data.get('mini_spider', {})
        discovered_urls = mini_spider.get('total_discovered_urls', 0)
        
        # Only show summary if there are significant findings
        if open_ports == 0 and vulnerabilities == 0 and discovered_urls == 0:
            return
        
        # Enhanced summary header
        self.console.print(f"\n📊 [bold primary]Scan Results Summary[/bold primary]")
        self.console.print(f"[dim]Target: {target}[/dim]")
        self.console.print("[dim]" + "─" * 35 + "[/dim]")
        
        # Enhanced findings with icons and colors
        if open_ports > 0:
            self.console.print(f"🔍 [bold success]{open_ports}[/bold success] open ports discovered")
        if vulnerabilities > 0:
            color = "error" if vulnerabilities > 5 else "warning"
            self.console.print(f"🚨 [bold {color}]{vulnerabilities}[/bold {color}] security findings")
        if discovered_urls > 0:
            self.console.print(f"🕷️  [bold info]{discovered_urls}[/bold info] URLs discovered")
    
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
        interesting_findings = spider_data.get('interesting_findings', [])
        
        # Only show critical findings
        critical_findings = [f for f in interesting_findings if f.get('severity') == 'critical']
        if critical_findings:
            self.print(f"[bold red]Critical findings:[/bold red] {len(critical_findings)} discovered")
    
    def display_http_summary(self, http_data: dict):
        """Display summary of HTTP scan findings"""
        if not http_data:
            return
        
        # Only show critical findings
        vuln_summary = http_data.get('summary', {}).get('severity_counts', {})
        critical_high = vuln_summary.get('critical', 0) + vuln_summary.get('high', 0)
        
        if critical_high > 0:
            self.print(f"[bold red]Security Alert:[/bold red] {critical_high} critical/high findings")
        
        # Technologies - only if interesting
        techs = http_data.get('summary', {}).get('technologies', [])
        interesting_techs = [t for t in techs if t.lower() in ['wordpress', 'drupal', 'joomla', 'jenkins', 'gitlab', 'apache', 'nginx', 'iis']]
        if interesting_techs:
            self.print(f"[dim]Technologies: {', '.join(interesting_techs[:3])}[/dim]")
    
    def display_minimal_summary(self, data: dict, workspace: 'Path'):
        """Display enhanced analysis summary with visual elements"""
        from pathlib import Path
        
        # Display SmartList recommendations (main focus)
        smartlist_data = data.get('smartlist', {})
        if smartlist_data:
            self.display_smartlist_recommendations(smartlist_data)
        
        # Display scan summary
        self.display_scan_summary(data)
        
        # Enhanced workspace info with visual elements
        self.console.print(f"\n💾 [bold muted]Results Location[/bold muted]")
        self.console.print(f"   [secondary]📁 Workspace:[/secondary] [dim]{workspace}[/dim]")
        self.console.print(f"   [secondary]📋 Wordlists:[/secondary] [dim]{workspace}/wordlists_for_*[/dim]")
        
        # Support message - non-intrusive
        self.console.print("\n[dim]💖 Support IPCrawler development: patreon.com/ipcrawler[/dim]")
        self.console.print("\n" + "─" * 50)
    
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