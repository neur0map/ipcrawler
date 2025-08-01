#!/usr/bin/env python3

import os
import sys

from src.core.utils.cache_utils import ensure_no_bytecode, clean_project_cache

ensure_no_bytecode()

clean_project_cache()

import asyncio
import sys
from pathlib import Path

import typer
from src.core.ui.console.base import console
from rich.progress import Progress, SpinnerColumn, TextColumn

from workflows.nmap_fast_01.scanner import NmapFastScanner
from workflows.nmap_02.scanner import NmapScanner
from workflows.http_03.scanner import HTTPAdvancedScanner
from workflows.smartlist_05.scanner import SmartListScanner
from workflows.mini_spider_04.scanner import MiniSpiderScanner

from src.core.config import config
from src.core.reporting.orchestrator import reporting_orchestrator
from src.core.utils.cli_utils import preprocess_args, validate_target_input
from src.core.utils.target_utils import resolve_target, is_localhost_target
from src.core.utils.privilege_utils import check_and_offer_sudo_escalation
from src.core.utils.process_utils import cleanup_processes, cleanup_existing_nmap_processes
from src.core.scorer.audit_runner import audit_runner


def version_callback(value: bool):
    """Handle --version flag"""
    if value:
        from src.core.ui.console.base import console
        
        ascii_art_path = Path(__file__).parent / "scripts" / "media" / "ascii-art.txt"
        if ascii_art_path.exists():
            with open(ascii_art_path, 'r') as f:
                ascii_art = f.read()
                console.print(ascii_art, style="cyan")
        else:
            console.print("""
                     ██╗██████╗  ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗ 
                     ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗
                     ██║██████╔╝██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝
                     ██║██╔═══╝ ██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗
                     ██║██║     ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║
                     ╚═╝╚═╝      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝
            """, style="cyan")
        
        console.print(f"\n[bold]IPCrawler SmartList Engine[/bold] version [success]{config.version}[/success]")
        console.print("Intelligent wordlist recommendations powered by target analysis\n")
        raise typer.Exit()


def main_callback(
    version: bool = typer.Option(False, "--version", callback=version_callback, help="Show version information")
):
    """IPCrawler SmartList Engine - Intelligent wordlist recommendations for security testing"""
    pass

app = typer.Typer(
    name="ipcrawler", 
    help="SmartList Engine - Intelligent wordlist recommendations for security testing",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    callback=main_callback
)



@app.command("scan", help="Analyze target and recommend optimal wordlists for security testing")
def main_command(
    target: str = typer.Argument(..., help="Target IP address or hostname to analyze for wordlist recommendations"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output")
):
    """Main scanning command"""
    # Validate target format
    if not validate_target_input(target):
        raise typer.Exit(1)
        
    if is_localhost_target(target):
        console.warning(f"Scanning {target} - make sure this is intended")
        if not typer.confirm(f"Continue scanning {target}?", default=False):
            console.info("Scan cancelled")
            raise typer.Exit(0)
    
    try:
        asyncio.run(run_workflow(target, debug))
    except KeyboardInterrupt:
        console.warning("Scan interrupted by user")
        raise typer.Exit(130)
    except Exception as e:
        console.error(f"Scan failed: {e}")
        if debug:
            import traceback
            console.error("Stack trace:")
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command("audit")  
def audit_command(
    details: bool = typer.Option(False, "--details", help="Show detailed conflict analysis")
):
    """Run comprehensive SmartList audit (rules, entropy, usage)"""
    exit_code = run_comprehensive_audit(show_details=details)
    raise typer.Exit(exit_code)

def run_comprehensive_audit(show_details: bool = False):
    """Run enhanced comprehensive SmartList audit with advanced flaw detection"""
    return audit_runner.run_comprehensive_audit(show_details)

def run_legacy_audit():
    """Legacy audit system as fallback"""
    return audit_runner.run_legacy_audit()


def run_entropy_audit(days_back: int = 30, context_tech: str = None, context_port: int = None):
    """Run entropy analysis portion of the audit"""
    try:
        audit_runner.run_entropy_audit(days_back, context_tech, context_port)
    except Exception:
        raise typer.Exit(1)


# Moved to src.core.utils.target_utils


# Moved to src.core.utils.privilege_utils


async def run_workflow(target: str, debug: bool = False):
    """Execute SmartList analysis workflow on target"""
    from src.core.utils.debugging import set_debug
    set_debug(debug)
    
    cleanup_existing_nmap_processes()
    
    await check_and_offer_sudo_escalation(sys.argv[1:])
    
    resolved_target = await resolve_target(target)
    
    console.display_workflow_status('port_discovery', 'starting', 'Hostname discovery and port scanning')
    
    workspace = reporting_orchestrator.create_versioned_workspace(target, enable_versioning=True)
    
    discovered_ports = None
    total_execution_time = 0.0
    
    if config.fast_port_discovery:
        
        discovery_scanner = NmapFastScanner()
        discovery_result = await discovery_scanner.execute(
            target=resolved_target
        )
        
        if discovery_result.success and discovery_result.data:
            discovered_ports = discovery_result.data.get("open_ports", [])
            port_count = len(discovered_ports)
            total_execution_time += discovery_result.execution_time or 0.0
            
            # Enhanced results display
            if port_count > 0:
                console.print(f"\n✓ [bold success]Port Discovery Complete[/bold success] - [primary]{port_count}[/primary] open ports found")
            else:
                console.print(f"\n✓ [bold muted]Port Discovery Complete[/bold muted] - No open ports found")
            
            hostname_mappings = discovery_result.data.get("hostname_mappings", [])
            if hostname_mappings:
                # Enhanced hostname display
                if len(hostname_mappings) <= 3:
                    hostnames = ", ".join(f"[secondary]{m['hostname']}[/secondary]" for m in hostname_mappings)
                    console.print(f"  🌐 Hostnames: {hostnames}")
                else:
                    console.print(f"  🌐 Discovered [primary]{len(hostname_mappings)}[/primary] hostnames")
                    
                # Show /etc/hosts update status
                if discovery_result.data.get("etc_hosts_updated"):
                    console.print(f"  ✓ [success]/etc/hosts updated[/success]")
                elif discovery_result.data.get("scan_mode") == "unprivileged":
                    console.print(f"  ⚠️  [dim]Run with sudo to update /etc/hosts[/dim]")
            
            if port_count == 0:
                console.print("\n[dim]⚠️  No open ports detected - analysis complete[/dim]")
                empty_data = {
                    "tool": "nmap",
                    "target": resolved_target,
                    "start_time": discovery_result.data.get("start_time"),
                    "end_time": discovery_result.data.get("end_time"), 
                    "duration": total_execution_time,
                    "hosts": [],
                    "total_hosts": 0,
                    "up_hosts": 0,
                    "down_hosts": 0,
                    "discovery_enabled": True,
                    "discovered_ports": 0
                }
                reporting_orchestrator.generate_workflow_reports(workspace, 'nmap_fast_01', empty_data)
                display_minimal_summary(empty_data, workspace)
                return
            
            reporting_orchestrator.generate_workflow_reports(workspace, 'nmap_fast_01', discovery_result.data)
            
            if port_count > config.max_detailed_ports:
                discovered_ports = discovered_ports[:config.max_detailed_ports]
        else:
            console.print(f"\n✗ [bold error]Port Discovery Failed[/bold error]: {discovery_result.error}")
            console.print("[dim]Cannot proceed without successful port discovery[/dim]")
            return
    
    console.display_workflow_status('service_analysis', 'starting', 'Detailed service fingerprinting')
    scanner = NmapScanner(batch_size=config.batch_size, ports_per_batch=config.ports_per_batch)
    
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        if discovered_ports is not None:
            estimated_time = len(discovered_ports) * 10
            if config.fast_detailed_scan:
                estimated_time = len(discovered_ports) * 3
            
            time_msg = f" (~{estimated_time//60}m {estimated_time%60}s)" if estimated_time > 60 else f" (~{estimated_time}s)"
            task = progress.add_task(f"Detailed analysis of {len(discovered_ports)} discovered services{time_msg}...", total=None)
            
            # Remove tip - too verbose
        else:
            task = progress.add_task(f"Full analysis of all 65535 ports (10 parallel batches)...", total=None)
        
        result = await scanner.execute(
            target=resolved_target,
            ports=discovered_ports
        )
        
        progress.update(task, completed=True)
    
    if result.success and result.data:
        total_execution_time += result.execution_time or 0.0
        
        if discovered_ports is not None:
            result.data['discovery_enabled'] = True
            result.data['discovered_ports'] = len(discovered_ports)
            if 'discovery_result' in locals() and discovery_result.data.get('hostname_mappings'):
                result.data['hostname_mappings'] = discovery_result.data['hostname_mappings']
        else:
            result.data['discovery_enabled'] = False
        
        http_ports = []
        discovered_hostnames = set()
        
        if discovered_ports is not None and 'discovery_result' in locals() and discovery_result.data.get('hostname_mappings'):
            for mapping in discovery_result.data.get('hostname_mappings', []):
                discovered_hostnames.add(mapping['hostname'])
        
        for host in result.data.get('hosts', []):
            if host.get('hostname'):
                discovered_hostnames.add(host['hostname'])
            
            for port in host.get('ports', []):
                port_num = port.get('port')
                service = port.get('service', '')
                
                for script in port.get('scripts', []):
                    if script.get('id') == 'http-title' and script.get('output'):
                        import re
                        redirect_match = re.search(r'redirect to ([^\s]+)', script['output'])
                        if redirect_match:
                            redirect_url = redirect_match.group(1)
                            from urllib.parse import urlparse
                            parsed = urlparse(redirect_url)
                            if parsed.hostname:
                                discovered_hostnames.add(parsed.hostname)
                
                if port_num and (
                    port_num in [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000] or
                    (service and 'http' in service.lower()) or
                    (service and 'https' in service.lower()) or
                    (service and 'web' in service.lower())
                ):
                    http_ports.append(port_num)
        
        http_scan_data = None
        if http_ports:
            http_ports = list(set(http_ports))
            hostnames_list = list(discovered_hostnames)
            
            console.display_workflow_status('http_analysis', 'starting', f'Found {len(http_ports)} HTTP/HTTPS services')
            # Hostname info already shown earlier
            
            http_scanner = HTTPAdvancedScanner()
            http_result = await http_scanner.execute(
                target=resolved_target,
                ports=http_ports,
                discovered_hostnames=hostnames_list
            )
            
            if http_result.success and http_result.data:
                total_execution_time += http_result.execution_time or 0.0
                http_scan_data = http_result.data
                
                display_http_summary(http_result.data)
            else:
                error_msg = http_result.error or (http_result.errors[0] if http_result.errors else "Unknown error")
                # Silently continue - error already logged internally
        

        spider_data = None
        if http_scan_data and http_scan_data.get('services'):
            console.display_workflow_status('mini_spider', 'starting', 'URL discovery and crawling')
            
            spider_previous_results = {
                'http_03': {
                    'success': True,
                    'data': http_scan_data
                }
            }
            
            spider_scanner = MiniSpiderScanner()
            spider_result = await spider_scanner.execute(
                target=resolved_target,
                previous_results=spider_previous_results
            )
            
            if spider_result.success and spider_result.data:
                total_execution_time += spider_result.execution_time or 0.0
                # Mini Spider analysis completed
                spider_data = spider_result.data
                
                # Display Mini Spider findings
                display_spider_summary(spider_data)
            else:
                error_msg = spider_result.error or "Unknown error"
                # Silently continue - error already logged internally

        smartlist_data = None
        if http_scan_data and http_scan_data.get('services'):
            console.display_workflow_status('smartlist_analysis', 'starting', 'Generating wordlist recommendations')
            
            previous_results = {
                'nmap_fast_01': {
                    'success': True,
                    'data': {
                        'hosts': result.data.get('hosts', [])
                    }
                },
                'nmap_02': {
                    'success': True,
                    'data': result.data
                },
                'http_03': {
                    'success': True,
                    'data': http_scan_data
                }
            }
            
            if spider_data:
                previous_results['mini_spider_04'] = {
                    'success': True,
                    'data': spider_data
                }
            
            smartlist_scanner = SmartListScanner()
            smartlist_result = await smartlist_scanner.execute(
                target=resolved_target,
                previous_results=previous_results
            )
            
            if smartlist_result.success and smartlist_result.data:
                total_execution_time += smartlist_result.execution_time or 0.0
                # SmartList analysis completed
                smartlist_data = smartlist_result.data
            else:
                error_msg = smartlist_result.error or "Unknown error"
                # Silently continue - error already logged internally

        result.data['total_execution_time'] = total_execution_time
        
        if http_scan_data:
            result.data['http_scan'] = http_scan_data
            
            if 'summary' not in result.data:
                result.data['summary'] = {}
            
            result.data['summary']['http_vulnerabilities'] = len(http_scan_data.get('vulnerabilities', []))
            result.data['summary']['http_services'] = len(http_scan_data.get('services', []))
            result.data['summary']['discovered_subdomains'] = len(http_scan_data.get('subdomains', []))
            result.data['summary']['discovered_paths'] = len(http_scan_data.get('summary', {}).get('discovered_paths', []))
        
        if spider_data:
            result.data['mini_spider'] = spider_data
            
            if 'summary' not in result.data:
                result.data['summary'] = {}
            
            result.data['summary']['discovered_urls'] = len(spider_data.get('discovered_urls', []))
            result.data['summary']['interesting_findings'] = len(spider_data.get('interesting_findings', []))
            result.data['summary']['url_categories'] = len(spider_data.get('categorized_results', {}))
        
        if smartlist_data:
            result.data['smartlist'] = smartlist_data
        

        
        
        nmap_data_with_target = result.data.copy()
        nmap_data_with_target['target'] = resolved_target
        reporting_orchestrator.generate_workflow_reports(workspace, 'nmap_02', nmap_data_with_target)
        
        if http_scan_data:
            http_data_with_target = http_scan_data.copy()
            http_data_with_target['target'] = resolved_target
            reporting_orchestrator.generate_workflow_reports(workspace, 'http_03', http_data_with_target)
        
        if spider_data:
            spider_data_with_target = spider_data.copy()
            spider_data_with_target['target'] = resolved_target
            reporting_orchestrator.generate_workflow_reports(workspace, 'mini_spider_04', spider_data_with_target)
        
        if smartlist_data:
            smartlist_data_with_target = smartlist_data.copy()
            smartlist_data_with_target['target'] = resolved_target
            reporting_orchestrator.generate_workflow_reports(workspace, 'smartlist_05', smartlist_data_with_target)
        
        try:
            # Format workflow data properly for the new ReportingEngine
            all_workflow_data = {
                'target': resolved_target,
                'nmap_fast_01': {
                    'success': discovery_result is not None and discovery_result.success if 'discovery_result' in locals() else False,
                    'data': discovery_result.data if 'discovery_result' in locals() and discovery_result else {},
                    'execution_time': discovery_result.execution_time if 'discovery_result' in locals() and discovery_result else 0
                },
                'nmap_02': {
                    'success': result is not None and result.success,
                    'data': result.data if result else {},
                    'execution_time': result.execution_time if result else 0
                },
                'http_03': {
                    'success': http_scan_data is not None,
                    'data': http_scan_data if http_scan_data else {},
                    'execution_time': getattr(locals().get('http_result'), 'execution_time', 0) if 'http_result' in locals() else 0
                },
                'mini_spider_04': {
                    'success': spider_data is not None,
                    'data': spider_data if spider_data else {},
                    'execution_time': getattr(locals().get('spider_result'), 'execution_time', 0) if 'spider_result' in locals() else 0
                },
                'smartlist_05': {
                    'success': smartlist_data is not None,
                    'data': smartlist_data if smartlist_data else {},
                    'execution_time': getattr(locals().get('smartlist_result'), 'execution_time', 0) if 'smartlist_result' in locals() else 0
                }
            }
            
            report_paths = reporting_orchestrator.generate_all_reports(workspace, all_workflow_data)
            
            if 'master_report' in report_paths:
                console.print(f"\n📊 [bold success]Master Report Generated[/bold success]")
                console.print(f"   [dim]{report_paths['master_report']}[/dim]")
                
        except Exception as e:
            console.error(f"Failed to generate final reports: {e}")
        
        display_minimal_summary(result.data, workspace)
    else:
        console.print(f"✗ Scan failed: {result.error}")
        raise typer.Exit(1)
    
    cleanup_processes()
    


def display_spider_summary(spider_data: dict):
    """Display Mini Spider findings summary"""
    console.display_spider_summary(spider_data)




def display_minimal_summary(data: dict, workspace: Path):
    """Display clean analysis summary using new console methods"""
    console.display_minimal_summary(data, workspace)



def display_http_summary(http_data: dict):
    """Display summary of HTTP scan findings"""
    console.display_http_summary(http_data)


report_app = typer.Typer(
    name="report",
    help="Report generation and management commands",
    no_args_is_help=True
)
app.add_typer(report_app)

@report_app.command("master-report")
def generate_master_report(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name to generate report from")
):
    """Generate master report from workspace data"""
    from src.core.reporting.commands.generate_master_report import MasterReportCommand
    
    command = MasterReportCommand()
    result = command.execute(workspace)
    
    if not result:
        raise typer.Exit(1)

@report_app.command("list-workspaces")
def list_workspaces(
    target: str = typer.Option(None, "--target", "-t", help="Filter by target name"),
    details: bool = typer.Option(False, "--details", "-d", help="Show detailed information")
):
    """List available workspaces"""
    from src.core.reporting.commands.workspace_list import WorkspaceListCommand
    
    options = {'details': details}
    command = WorkspaceListCommand()
    result = command.execute(target, options)
    
    if not result:
        raise typer.Exit(1)

@report_app.command("clean-workspaces")
def clean_workspaces(
    target: str = typer.Option(None, "--target", "-t", help="Clean only specified target"),
    keep: int = typer.Option(5, "--keep", "-k", help="Number of workspaces to keep per target"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be removed without deleting")
):
    """Clean up old workspaces"""
    from src.core.reporting.commands.workspace_clean import WorkspaceCleanCommand
    
    options = {'keep_count': keep, 'dry_run': dry_run}
    command = WorkspaceCleanCommand()
    result = command.execute(target, options)
    
    if not result:
        raise typer.Exit(1)

# Moved to src.core.utils.cli_utils


if __name__ == "__main__":
    preprocess_args()
    app()
