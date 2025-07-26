#!/usr/bin/env python3

import os
import sys

# Import cache utilities and ensure no bytecode
from src.core.utils.cache_utils import ensure_no_bytecode, clean_project_cache

# Configure Python to not write bytecode
ensure_no_bytecode()

# Clean cache before imports
clean_project_cache()

import asyncio
import sys
from pathlib import Path

import typer
from src.core.ui.console.base import console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import workflows
from workflows.nmap_fast_01.scanner import NmapFastScanner
from workflows.nmap_02.scanner import NmapScanner
from workflows.http_03.scanner import HTTPAdvancedScanner
from workflows.smartlist_05.scanner import SmartListScanner
from workflows.mini_spider_04.scanner import MiniSpiderScanner

# Import utilities
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
        # Import console here to avoid circular imports
        from src.core.ui.console.base import console
        
        # Read ASCII art from correct location
        ascii_art_path = Path(__file__).parent / "scripts" / "media" / "ascii-art.txt"
        if ascii_art_path.exists():
            with open(ascii_art_path, 'r') as f:
                ascii_art = f.read()
                console.print(ascii_art, style="cyan")
        else:
            # Fallback ASCII art if file not found
            console.print("""
                     ██╗██████╗  ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗ 
                     ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗
                     ██║██████╔╝██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝
                     ██║██╔═══╝ ██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗
                     ██║██║     ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║
                     ╚═╝╚═╝      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝
            """, style="cyan")
        
        # Display version from config
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

# Using centralized console from src.core.ui.console.base


@app.command("scan", help="Analyze target and recommend optimal wordlists for security testing")
def main_command(
    target: str = typer.Argument(..., help="Target IP address or hostname to analyze for wordlist recommendations"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output")
):
    """Main scanning command"""
    # Validate target format
    if not validate_target_input(target):
        raise typer.Exit(1)
        
    # Additional validation for common mistakes
    if is_localhost_target(target):
        console.warning(f"Scanning {target} - make sure this is intended")
        if not typer.confirm(f"Continue scanning {target}?", default=False):
            console.info("Scan cancelled")
            raise typer.Exit(0)
    
    try:
        asyncio.run(run_workflow(target, debug))
    except KeyboardInterrupt:
        console.warning("Scan interrupted by user")
        raise typer.Exit(130)  # Standard exit code for SIGINT
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
    # Set debug mode
    from src.core.utils.debugging import set_debug
    set_debug(debug)
    
    # Clean up any existing nmap processes first
    cleanup_existing_nmap_processes()
    
    # Check if we should offer sudo escalation BEFORE starting any workflows
    await check_and_offer_sudo_escalation(sys.argv[1:])
    
    # Resolve target first
    resolved_target = await resolve_target(target)
    
    console.display_workflow_status('port_discovery', 'starting', 'Hostname discovery and port scanning')
    
    workspace = reporting_orchestrator.create_versioned_workspace(target, enable_versioning=True)
    
    # IMPORTANT: Default behavior is to scan ONLY discovered ports
    # Full 65535 port scan only happens when fast_port_discovery is explicitly set to false
    discovered_ports = None
    total_execution_time = 0.0
    
    if config.fast_port_discovery:
        # Fast discovery phase details are shown in progress below
        
        discovery_scanner = NmapFastScanner()
        discovery_result = await discovery_scanner.execute(
            target=resolved_target
        )
        
        if discovery_result.success and discovery_result.data:
            discovered_ports = discovery_result.data.get("open_ports", [])
            port_count = len(discovered_ports)
            total_execution_time += discovery_result.execution_time or 0.0
            
            console.print(f"✓ Port discovery completed in {(discovery_result.execution_time or 0.0):.2f}s")
            console.print(f"  Found {port_count} open ports using {discovery_result.data.get('tool', 'unknown')}")
            
            # Display discovered hostnames from fast scan
            hostname_mappings = discovery_result.data.get("hostname_mappings", [])
            if hostname_mappings:
                console.print(f"  → Discovered {len(hostname_mappings)} hostname(s):")
                for mapping in hostname_mappings:
                    console.print(f"    • [secondary]{mapping['hostname']}[/secondary] → {mapping['ip']}")
                if discovery_result.data.get("etc_hosts_updated"):
                    console.print("    ✓ [success]/etc/hosts updated[/success]")
                elif discovery_result.data.get("scan_mode") == "unprivileged":
                    console.print("    ℹ️  [warning]Restart with 'sudo' to update /etc/hosts[/warning]")
            
            if port_count == 0:
                console.print("⚠ No open ports found. Skipping detailed analysis.")
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
            
            # Save fast discovery results (text only)
            reporting_orchestrator.generate_workflow_reports(workspace, 'nmap_fast_01', discovery_result.data)
            
            if port_count > config.max_detailed_ports:
                console.print(f"⚠ Found {port_count} services, limiting detailed analysis to top {config.max_detailed_ports}")
                discovered_ports = discovered_ports[:config.max_detailed_ports]
        else:
            console.print(f"✗ Port discovery failed: {discovery_result.error}")
            console.print("⚠ Cannot proceed without port discovery. Exiting.")
            console.print("  To analyze all services, set 'fast_port_discovery: false' in config.yaml")
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
            # Estimate time based on port count
            estimated_time = len(discovered_ports) * 10  # ~10 seconds per port with scripts
            if config.fast_detailed_scan:
                estimated_time = len(discovered_ports) * 3  # ~3 seconds per port without scripts
            
            time_msg = f" (~{estimated_time//60}m {estimated_time%60}s)" if estimated_time > 60 else f" (~{estimated_time}s)"
            task = progress.add_task(f"Detailed analysis of {len(discovered_ports)} discovered services{time_msg}...", total=None)
            
            if not config.fast_detailed_scan and len(discovered_ports) > 10:
                console.print("[yellow]💡 Tip: Enable 'fast_detailed_scan' in config for 3x faster scans (disables scripts)[/yellow]")
        else:
            task = progress.add_task(f"Full analysis of all 65535 ports (10 parallel batches)...", total=None)
        
        result = await scanner.execute(
            target=resolved_target,
            ports=discovered_ports
        )
        
        progress.update(task, completed=True)
    
    if result.success and result.data:
        total_execution_time += result.execution_time or 0.0
        # Service analysis completed
        
        if discovered_ports is not None:
            result.data['discovery_enabled'] = True
            result.data['discovered_ports'] = len(discovered_ports)
            # Include hostname mappings from fast scan in final results
            if 'discovery_result' in locals() and discovery_result.data.get('hostname_mappings'):
                result.data['hostname_mappings'] = discovery_result.data['hostname_mappings']
        else:
            result.data['discovery_enabled'] = False
        
        # Extract HTTP/HTTPS ports and discovered hostnames from scan results
        http_ports = []
        discovered_hostnames = set()  # Use set to avoid duplicates
        
        # First, add any hostnames discovered during fast scan
        if discovered_ports is not None and 'discovery_result' in locals() and discovery_result.data.get('hostname_mappings'):
            for mapping in discovery_result.data.get('hostname_mappings', []):
                discovered_hostnames.add(mapping['hostname'])
        
        for host in result.data.get('hosts', []):
            if host.get('hostname'):
                discovered_hostnames.add(host['hostname'])
            
            for port in host.get('ports', []):
                port_num = port.get('port')
                service = port.get('service', '')
                
                # Extract hostnames from script outputs
                for script in port.get('scripts', []):
                    if script.get('id') == 'http-title' and script.get('output'):
                        # Look for redirect patterns in http-title output
                        import re
                        redirect_match = re.search(r'redirect to ([^\s]+)', script['output'])
                        if redirect_match:
                            redirect_url = redirect_match.group(1)
                            # Extract hostname from URL
                            from urllib.parse import urlparse
                            parsed = urlparse(redirect_url)
                            if parsed.hostname:
                                discovered_hostnames.add(parsed.hostname)
                
                # Check if it's an HTTP service
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
            if discovered_hostnames:
                console.print(f"  → Discovered hostnames: {', '.join(hostnames_list)}")
            
            http_scanner = HTTPAdvancedScanner()
            http_result = await http_scanner.execute(
                target=resolved_target,
                ports=http_ports,
                discovered_hostnames=hostnames_list
            )
            
            if http_result.success and http_result.data:
                total_execution_time += http_result.execution_time or 0.0
                # HTTP analysis completed
                http_scan_data = http_result.data
                
                # Display HTTP findings
                display_http_summary(http_result.data)
            else:
                error_msg = http_result.error or (http_result.errors[0] if http_result.errors else "Unknown error")
                console.print(f"⚠ HTTP analysis failed: {error_msg}")
        

        # Run Mini Spider analysis after HTTP scan if we have services
        spider_data = None
        if http_scan_data and http_scan_data.get('services'):
            console.display_workflow_status('mini_spider', 'starting', 'URL discovery and crawling')
            
            # Prepare previous results for Mini Spider
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
                console.print(f"⚠ Mini Spider analysis failed: {error_msg}")

        # Run SmartList analysis after Mini Spider if we have services
        smartlist_data = None
        if http_scan_data and http_scan_data.get('services'):
            console.display_workflow_status('smartlist_analysis', 'starting', 'Generating wordlist recommendations')
            
            # Prepare enhanced previous results for SmartList
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
            
            # Add Mini Spider data if available
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
                console.print(f"⚠ SmartList analysis failed: {error_msg}")

        # Merge all scan results
        result.data['total_execution_time'] = total_execution_time
        
        if http_scan_data:
            result.data['http_scan'] = http_scan_data
            
            # Also merge key findings into main summary
            if 'summary' not in result.data:
                result.data['summary'] = {}
            
            result.data['summary']['http_vulnerabilities'] = len(http_scan_data.get('vulnerabilities', []))
            result.data['summary']['http_services'] = len(http_scan_data.get('services', []))
            result.data['summary']['discovered_subdomains'] = len(http_scan_data.get('subdomains', []))
            result.data['summary']['discovered_paths'] = len(http_scan_data.get('summary', {}).get('discovered_paths', []))
        
        if spider_data:
            result.data['mini_spider'] = spider_data
            
            # Add mini spider summary to main summary
            if 'summary' not in result.data:
                result.data['summary'] = {}
            
            result.data['summary']['discovered_urls'] = len(spider_data.get('discovered_urls', []))
            result.data['summary']['interesting_findings'] = len(spider_data.get('interesting_findings', []))
            result.data['summary']['url_categories'] = len(spider_data.get('categorized_results', {}))
        
        if smartlist_data:
            result.data['smartlist'] = smartlist_data
        

        
        # All analysis completed - Save each workflow's results separately
        
        # Save base nmap scan results (text only)
        nmap_data_with_target = result.data.copy()
        nmap_data_with_target['target'] = resolved_target
        reporting_orchestrator.generate_workflow_reports(workspace, 'nmap_02', nmap_data_with_target)
        
        # Save HTTP scan results if available (text only)
        if http_scan_data:
            http_data_with_target = http_scan_data.copy()
            http_data_with_target['target'] = resolved_target
            reporting_orchestrator.generate_workflow_reports(workspace, 'http_03', http_data_with_target)
        
        # Save Mini Spider results if available (text only)
        if spider_data:
            spider_data_with_target = spider_data.copy()
            spider_data_with_target['target'] = resolved_target
            reporting_orchestrator.generate_workflow_reports(workspace, 'mini_spider_04', spider_data_with_target)
        
        # Save SmartList results with wordlist file (text + wordlist only)
        if smartlist_data:
            smartlist_data_with_target = smartlist_data.copy()
            smartlist_data_with_target['target'] = resolved_target
            reporting_orchestrator.generate_workflow_reports(workspace, 'smartlist_05', smartlist_data_with_target)
        
        # Generate master TXT report and wordlist recommendations
        try:
            # Collect all workflow data for final report generation
            all_workflow_data = {
                'target': resolved_target,  # Ensure target is included
                'nmap_fast_01': discovery_result.data if 'discovery_result' in locals() else None,
                'nmap_02': result.data,
                'http_03': http_scan_data,
                'mini_spider_04': spider_data, 
                'smartlist_05': smartlist_data
            }
            
            # Generate final master report and wordlist recommendations
            report_paths = reporting_orchestrator.generate_all_reports(workspace, all_workflow_data)
            
            if 'master_report' in report_paths:
                console.print(f"📊 Master TXT report: [secondary]{report_paths['master_report']}[/secondary]")
                
        except Exception as e:
            console.error(f"Failed to generate final reports: {e}")
        
        # Display minimal summary only
        display_minimal_summary(result.data, workspace)
    else:
        console.print(f"✗ Scan failed: {result.error}")
        raise typer.Exit(1)
    
    # Clean up processes after scan completion
    cleanup_processes()
    


def display_spider_summary(spider_data: dict):
    """Display Mini Spider findings summary"""
    console.display_spider_summary(spider_data)


# display_smartlist_summary already moved to console


def display_minimal_summary(data: dict, workspace: Path):
    """Display clean analysis summary using new console methods"""
    console.display_minimal_summary(data, workspace)



def display_http_summary(http_data: dict):
    """Display summary of HTTP scan findings"""
    console.display_http_summary(http_data)


# Add report command subgroup
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
    preprocess_args()  # This function is imported from cli_utils
    app()
