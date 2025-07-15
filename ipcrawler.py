#!/usr/bin/env python3

import os
import sys
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

# Self-cleaning: Remove any cached bytecode to ensure fresh execution
import shutil
from pathlib import Path

def clean_cache():
    """Remove all __pycache__ directories in the project"""
    try:
        project_root = Path(__file__).parent
        for cache_dir in project_root.rglob('__pycache__'):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir, ignore_errors=True)
    except Exception:
        pass  # Fail silently if cache cleanup fails

# Clean cache before imports
clean_cache()

import asyncio
import tempfile
import socket
import signal
import sys
import re
from datetime import datetime
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from workflows.nmap_fast_01.scanner import NmapFastScanner
from workflows.nmap_02.scanner import NmapScanner
from workflows.http_03.scanner import HTTPAdvancedScanner
from config import config
from utils.results import result_manager

app = typer.Typer(
    name="ipcrawler",
    help="CLI orchestrator for reconnaissance workflows",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)

console = Console()

# Global list to track running processes for cleanup
running_processes = []

def cleanup_processes():
    """Clean up any running nmap processes"""
    global running_processes
    for process in running_processes:
        try:
            if process and process.returncode is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except:
                    process.kill()
        except:
            pass
    running_processes.clear()

def signal_handler(signum, frame):
    """Handle Ctrl+C and other signals"""
    console.print("\n⚠ Scan interrupted. Cleaning up...")
    cleanup_processes()
    sys.exit(0)

def cleanup_existing_nmap_processes():
    """Kill any existing nmap processes to prevent conflicts"""
    try:
        import subprocess
        # Kill any existing nmap processes
        subprocess.run(['pkill', '-f', 'nmap'], capture_output=True, check=False)
    except:
        pass  # Ignore errors

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)




@app.command()
def main(
    target: str = typer.Argument(..., help="Target IP address or hostname to scan")
):
    """Run reconnaissance workflow on target"""
    asyncio.run(run_workflow(target))





async def resolve_target(target: str) -> str:
    """Resolve target hostname to IP with visual feedback"""
    import ipaddress
    
    # Check if target is already an IP address
    try:
        ipaddress.ip_address(target)
        console.print(f"▶ Target: [cyan]{target}[/cyan] (IP address)")
        return target
    except ValueError:
        pass
    
    # Check if target is CIDR notation
    try:
        ipaddress.ip_network(target, strict=False)
        console.print(f"▶ Target: [cyan]{target}[/cyan] (CIDR range)")
        return target
    except ValueError:
        pass
    
    # It's a hostname, resolve it
    console.print(f"▶ Resolving [cyan]{target}[/cyan]...")
    
    try:
        # Use getaddrinfo for proper async DNS resolution
        result = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: socket.getaddrinfo(target, None, socket.AF_INET)
        )
        
        if result:
            ip = result[0][4][0]
            console.print(f"  → Resolved to [green]{ip}[/green]")
            return target  # Return original hostname for nmap
        else:
            console.print(f"  ✗ Failed to resolve {target}")
            return target
            
    except Exception as e:
        console.print(f"  ⚠ DNS resolution warning: {str(e)}")
        return target  # Let nmap handle it


async def run_workflow(target: str):
    """Execute reconnaissance workflow on target"""
    # Clean up any existing nmap processes first
    cleanup_existing_nmap_processes()
    
    # Resolve target first
    resolved_target = await resolve_target(target)
    
    # Create workspace directory
    workspace = result_manager.create_workspace(target)
    
    # IMPORTANT: Default behavior is to scan ONLY discovered ports
    # Full 65535 port scan only happens when fast_port_discovery is explicitly set to false
    discovered_ports = None
    total_execution_time = 0.0
    
    if config.fast_port_discovery:
        console.print("→ Starting fast port discovery...")
        
        # Track discovered ports for real-time display
        discovered_ports_live = []
        
        def port_discovered(port: int, protocol: str):
            """Callback for when a port is discovered"""
            discovered_ports_live.append(port)
            console.print(f"  ✓ Found open port: [green]{port}/{protocol}[/green]")
        
        # Run port discovery with live updates
        discovery_scanner = NmapFastScanner()
        discovery_result = await discovery_scanner.execute(
            target=resolved_target,
            progress_callback=port_discovered
        )
        
        if discovery_result.success and discovery_result.data:
            discovered_ports = discovery_result.data.get("open_ports", [])
            port_count = len(discovered_ports)
            total_execution_time += discovery_result.execution_time or 0.0
            
            console.print(f"✓ Port discovery completed in {(discovery_result.execution_time or 0.0):.2f}s")
            console.print(f"  Found {port_count} open ports using {discovery_result.data.get('tool', 'unknown')}")
            
            if port_count == 0:
                console.print("⚠ No open ports found. Skipping detailed scan.")
                # Save empty results
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
                result_manager.save_results(workspace, target, empty_data)
                display_minimal_summary(empty_data, workspace)
                return
            
            if port_count > config.max_detailed_ports:
                console.print(f"⚠ Found {port_count} ports, limiting detailed scan to top {config.max_detailed_ports}")
                discovered_ports = discovered_ports[:config.max_detailed_ports]
        else:
            console.print(f"✗ Port discovery failed: {discovery_result.error}")
            console.print("⚠ Cannot proceed without port discovery. Exiting.")
            console.print("  To scan all ports, set 'fast_port_discovery: false' in config.yaml")
            return
    
    # Run detailed nmap scan
    console.print("→ Starting detailed scan...")
    scanner = NmapScanner(batch_size=config.batch_size, ports_per_batch=config.ports_per_batch)
    
    # Create simple progress callback without queue to avoid hanging
    progress_count = 0
    
    def simple_progress_callback():
        nonlocal progress_count
        progress_count += 1
        if discovered_ports:
            console.print(f"→ Port range {progress_count} completed")
        else:
            console.print(f"→ Batch {progress_count}/10 completed")
    
    # Execute with simple progress tracking
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        if discovered_ports is not None:
            task = progress.add_task(f"Detailed scan of {len(discovered_ports)} discovered ports...", total=None)
        else:
            task = progress.add_task(f"Full scan of all 65535 ports (10 parallel batches)...", total=None)
        
        # Run scanner without progress_queue to avoid hanging
        result = await scanner.execute(
            target=resolved_target,
            ports=discovered_ports
        )
        
        progress.update(task, completed=True)
    
    if result.success and result.data:
        total_execution_time += result.execution_time or 0.0
        console.print(f"✓ Nmap scan completed in {total_execution_time:.2f}s")
        
        # Add discovery info to results
        if discovered_ports is not None:
            result.data['discovery_enabled'] = True
            result.data['discovered_ports'] = len(discovered_ports)
        else:
            result.data['discovery_enabled'] = False
        
        # Extract HTTP/HTTPS ports and discovered hostnames from scan results
        http_ports = []
        discovered_hostnames = set()  # Use set to avoid duplicates
        
        for host in result.data.get('hosts', []):
            # Add main hostname if available
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
                    'http' in service.lower() or
                    'https' in service.lower() or
                    'web' in service.lower()
                ):
                    http_ports.append(port_num)
        
        # Run HTTP advanced scan if HTTP services found
        http_scan_data = None
        if http_ports:
            http_ports = list(set(http_ports))  # Remove duplicates
            hostnames_list = list(discovered_hostnames)
            
            console.print(f"\n→ Found {len(http_ports)} HTTP/HTTPS services. Starting advanced HTTP scan...")
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
                console.print(f"✓ HTTP scan completed in {http_result.execution_time:.2f}s")
                http_scan_data = http_result.data
                
                # Display HTTP findings
                display_http_summary(http_result.data)
            else:
                error_msg = http_result.error or (http_result.errors[0] if http_result.errors else "Unknown error")
                console.print(f"⚠ HTTP scan failed: {error_msg}")
        
        # Merge all scan results
        result.data['total_execution_time'] = total_execution_time
        
        # Add HTTP scan results to main data
        if http_scan_data:
            result.data['http_scan'] = http_scan_data
            
            # Also merge key findings into main summary
            if 'summary' not in result.data:
                result.data['summary'] = {}
            
            result.data['summary']['http_vulnerabilities'] = len(http_scan_data.get('vulnerabilities', []))
            result.data['summary']['http_services'] = len(http_scan_data.get('services', []))
            result.data['summary']['discovered_subdomains'] = len(http_scan_data.get('subdomains', []))
            result.data['summary']['discovered_paths'] = len(http_scan_data.get('summary', {}).get('discovered_paths', []))
        
        console.print(f"\n✓ All scans completed in {total_execution_time:.2f}s total")
        
        # Save consolidated results
        result_manager.save_results(workspace, target, result.data)
        
        # Display minimal summary only
        display_minimal_summary(result.data, workspace)
    else:
        console.print(f"✗ Scan failed: {result.error}")
        raise typer.Exit(1)
    
    # Clean up processes after scan completion
    cleanup_processes()
    


def display_minimal_summary(data: dict, workspace: Path):
    """Display minimal scan summary"""
    scan_result = data
    
    # Count open ports
    total_open_ports = 0
    for host in scan_result.get('hosts', []):
        total_open_ports += sum(1 for p in host.get('ports', []) if p.get('state') == 'open')
    
    # Minimal summary
    scan_mode = scan_result.get('scan_mode', 'unknown')
    
    summary = Table(show_header=False, box=None, padding=(0, 1))
    summary.add_column("Key", style="dim")
    summary.add_column("Value")
    
    summary.add_row("Target", f"[green]{scan_result.get('hosts', [{}])[0].get('ip', 'Unknown') if scan_result.get('hosts') else 'Unknown'}[/green]")
    summary.add_row("Scan Mode", scan_mode)
    
    # Show discovery info if enabled
    if scan_result.get('discovery_enabled'):
        summary.add_row("Port Discovery", f"Enabled ({scan_result.get('discovered_ports', 0)} ports found)")
    else:
        summary.add_row("Port Discovery", "Disabled (full scan)")
    
    summary.add_row("Duration", f"{scan_result['duration']:.2f}s")
    summary.add_row("Hosts Found", f"{scan_result['up_hosts']} up, {scan_result['down_hosts']} down")
    summary.add_row("Open Ports", str(total_open_ports))
    summary.add_row("Results Saved", f"[green]{workspace}[/green]")
    
    console.print("\n", summary, "\n")
    console.print("View detailed results in the workspace directory")



def display_http_summary(http_data: dict):
    """Display summary of HTTP scan findings"""
    if not http_data:
        return
    
    # Vulnerabilities summary
    vuln_summary = http_data.get('summary', {}).get('severity_counts', {})
    total_vulns = sum(vuln_summary.values())
    
    if total_vulns > 0:
        console.print(f"\n[yellow]⚠ Found {total_vulns} potential vulnerabilities:[/yellow]")
        if vuln_summary.get('critical', 0) > 0:
            console.print(f"  [red]● Critical: {vuln_summary['critical']}[/red]")
        if vuln_summary.get('high', 0) > 0:
            console.print(f"  [red]● High: {vuln_summary['high']}[/red]")
        if vuln_summary.get('medium', 0) > 0:
            console.print(f"  [yellow]● Medium: {vuln_summary['medium']}[/yellow]")
        if vuln_summary.get('low', 0) > 0:
            console.print(f"  [blue]● Low: {vuln_summary['low']}[/blue]")
    
    # Technologies detected
    techs = http_data.get('summary', {}).get('technologies', [])
    if techs:
        console.print(f"\n[cyan]Technologies detected:[/cyan] {', '.join(techs)}")
    
    # Discovered paths
    paths = http_data.get('summary', {}).get('discovered_paths', [])
    if paths:
        console.print(f"\n[green]Discovered {len(paths)} paths[/green]")
        for path in paths[:5]:  # Show first 5
            console.print(f"  • {path}")
        if len(paths) > 5:
            console.print(f"  ... and {len(paths) - 5} more")
    
    # Subdomains
    subdomains = http_data.get('subdomains', [])
    if subdomains:
        console.print(f"\n[magenta]Found {len(subdomains)} subdomains[/magenta]")
        for subdomain in subdomains[:5]:  # Show first 5
            console.print(f"  • {subdomain}")
        if len(subdomains) > 5:
            console.print(f"  ... and {len(subdomains) - 5} more")


if __name__ == "__main__":
    app()
