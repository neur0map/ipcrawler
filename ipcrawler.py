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
import json
import tempfile
import socket
import signal
import sys
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from workflows.nmap_fast_01.scanner import NmapFastScanner
from workflows.nmap_02.scanner import NmapScanner
from workflows.http_03.scanner import HTTPAdvancedScanner
from config import config

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
    workspace = create_workspace(target)
    
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
                save_scan_results(workspace, target, empty_data)
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
        
        # Extract HTTP/HTTPS ports from scan results
        http_ports = []
        for host in result.data.get('hosts', []):
            for port in host.get('ports', []):
                port_num = port.get('port')
                service = port.get('service', '')
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
            console.print(f"\n→ Found {len(http_ports)} HTTP/HTTPS services. Starting advanced HTTP scan...")
            
            http_scanner = HTTPAdvancedScanner()
            http_result = await http_scanner.execute(
                target=resolved_target,
                ports=http_ports
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
        save_scan_results(workspace, target, result.data)
        
        # Display minimal summary only
        display_minimal_summary(result.data, workspace)
    else:
        console.print(f"✗ Scan failed: {result.error}")
        raise typer.Exit(1)
    
    # Clean up processes after scan completion
    cleanup_processes()
    


def create_workspace(target: str) -> Path:
    """Create workspace directory for scan results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_name = f"scan_{target.replace('.', '_')}_{timestamp}"
    
    # Create workspaces directory with proper ownership
    base_path = Path("workspaces")
    workspace_path = base_path / workspace_name
    
    # Create directories
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # If running as sudo, change ownership to the real user
    if os.geteuid() == 0:  # Running as root
        # Get the real user ID from SUDO_UID environment variable
        sudo_uid = os.environ.get('SUDO_UID')
        sudo_gid = os.environ.get('SUDO_GID')
        
        if sudo_uid and sudo_gid:
            # Change ownership of workspaces directory and all subdirectories
            import subprocess
            subprocess.run(['chown', '-R', f'{sudo_uid}:{sudo_gid}', str(base_path)], 
                          capture_output=True, check=False)
    
    return workspace_path


def finalize_scan_data(data: dict) -> dict:
    """Finalize scan data by sorting ports and removing internal indexes"""
    # Sort ports for each host
    for host in data.get("hosts", []):
        if "ports" in host and host["ports"]:
            host["ports"].sort(key=lambda p: p.get("port", 0))
    
    # Remove internal index
    if "hosts_index" in data:
        del data["hosts_index"]
    
    return data


def save_scan_results(workspace: Path, target: str, data: dict):
    """Save scan results in multiple formats"""
    # Finalize data before saving
    data = finalize_scan_data(data)
    
    # Save JSON format
    json_file = workspace / "scan_results.json"
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Save detailed text report
    txt_file = workspace / "scan_report.txt"
    with open(txt_file, 'w') as f:
        f.write(generate_text_report(target, data))
    
    # Save HTML report
    html_file = workspace / "scan_report.html"
    with open(html_file, 'w') as f:
        f.write(generate_html_report(target, data))
    
    # Fix file permissions if running as sudo
    if os.geteuid() == 0:  # Running as root
        sudo_uid = os.environ.get('SUDO_UID')
        sudo_gid = os.environ.get('SUDO_GID')
        
        if sudo_uid and sudo_gid:
            import subprocess
            # Change ownership of all created files
            for file in [json_file, txt_file, html_file]:
                subprocess.run(['chown', f'{sudo_uid}:{sudo_gid}', str(file)], 
                              capture_output=True, check=False)


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


def generate_text_report(target: str, data: dict, is_live: bool = False) -> str:
    """Generate detailed text report"""
    report = []
    report.append(f"IP CRAWLER SCAN REPORT{'S (LIVE - IN PROGRESS)' if is_live else ''}")
    report.append(f"Target: {target}")
    report.append(f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Command: {data.get('command', 'N/A')}")
    report.append(f"Duration: {data.get('duration', 0):.2f} seconds")
    report.append(f"Hosts: {data.get('total_hosts', 0)} total, {data.get('up_hosts', 0)} up, {data.get('down_hosts', 0)} down")
    if is_live:
        report.append(f"Progress: {data.get('batches_completed', 0)} batches completed")
    report.append("=" * 80)
    
    for host in data['hosts']:
        report.append(f"\nHost: {host['ip']}")
        if host['hostname']:
            report.append(f"Hostname: {host['hostname']}")
        if host.get('os'):
            report.append(f"OS: {host['os']} (Accuracy: {host.get('os_accuracy', 'N/A')}%)")
        if host.get('mac_address'):
            report.append(f"MAC: {host['mac_address']} ({host.get('mac_vendor', 'Unknown vendor')})")
        
        # Open ports
        open_ports = [p for p in host['ports'] if p['state'] == 'open']
        if open_ports:
            report.append(f"\nOpen Ports: {len(open_ports)}")
            for port in open_ports:
                report.append(f"  {port['port']}/{port['protocol']} - {port.get('service', 'unknown')}")
                if port.get('version'):
                    report.append(f"    Version: {port['version']}")
                if port.get('product'):
                    report.append(f"    Product: {port['product']}")
                
                # Script results
                if port.get('scripts'):
                    for script in port['scripts']:
                        report.append(f"    Script: {script['id']}")
                        for line in script['output'].strip().split('\n'):
                            report.append(f"      {line}")
        
        report.append("-" * 80)
    
    # Add HTTP scan results if available
    if 'http_scan' in data:
        http_data = data['http_scan']
        report.append("\n" + "=" * 80)
        report.append("HTTP/HTTPS SCAN RESULTS")
        report.append("=" * 80)
        
        # HTTP Services
        services = http_data.get('services', [])
        if services:
            report.append(f"\nHTTP Services Found: {len(services)}")
            for service in services:
                report.append(f"\n  {service.get('url', 'Unknown URL')}")
                report.append(f"    Status: {service.get('status_code', 'N/A')}")
                report.append(f"    Server: {service.get('server', 'Unknown')}")
                if service.get('technologies'):
                    report.append(f"    Technologies: {', '.join(service['technologies'])}")
                if service.get('discovered_paths'):
                    report.append(f"    Discovered Paths: {len(service['discovered_paths'])}")
                    for path in service['discovered_paths'][:5]:
                        report.append(f"      • {path}")
        
        # Vulnerabilities
        vulns = http_data.get('vulnerabilities', [])
        if vulns:
            report.append(f"\nHTTP Vulnerabilities: {len(vulns)}")
            severity_order = ['critical', 'high', 'medium', 'low']
            for severity in severity_order:
                severity_vulns = [v for v in vulns if v.get('severity') == severity]
                if severity_vulns:
                    report.append(f"\n  {severity.upper()} ({len(severity_vulns)})")
                    for vuln in severity_vulns[:3]:  # Show first 3 of each severity
                        report.append(f"    • {vuln.get('description', 'N/A')}")
                        if vuln.get('evidence'):
                            report.append(f"      Evidence: {vuln['evidence']}")
        
        # DNS and Subdomains
        subdomains = http_data.get('subdomains', [])
        if subdomains:
            report.append(f"\nDiscovered Subdomains: {len(subdomains)}")
            for subdomain in subdomains[:10]:
                report.append(f"  • {subdomain}")
        
        dns_records = http_data.get('dns_records', [])
        if dns_records:
            report.append(f"\nDNS Records: {len(dns_records)}")
            for record in dns_records[:10]:
                report.append(f"  {record.get('type', 'N/A')}: {record.get('value', 'N/A')}")
    
    return "\n".join(report)


def generate_html_report(target: str, data: dict, is_live: bool = False) -> str:
    """Generate HTML report"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>IP Crawler Scan Report - {target}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #1e1e1e; color: #e0e0e0; }}
        h1, h2, h3 {{ color: #4fc3f7; }}
        .summary {{ background-color: #2c2c2c; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .host {{ background-color: #2c2c2c; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .port {{ background-color: #3c3c3c; padding: 10px; margin: 10px 0; border-radius: 3px; }}
        .script {{ background-color: #4c4c4c; padding: 8px; margin: 5px 0; border-radius: 3px; font-family: monospace; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #555; }}
        th {{ background-color: #3c3c3c; color: #4fc3f7; }}
        .open {{ color: #4caf50; }}
        .closed {{ color: #f44336; }}
    </style>
</head>
<body>
    <h1>IP Crawler Scan Report{' (LIVE - IN PROGRESS)' if is_live else ''}</h1>
    <div class="summary">
        <h2>Scan Summary</h2>
        <p><strong>Target:</strong> {target}</p>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Duration:</strong> {data.get('duration', 0):.2f} seconds</p>
        <p><strong>Hosts:</strong> {data.get('total_hosts', 0)} total, {data.get('up_hosts', 0)} up, {data.get('down_hosts', 0)} down</p>
        <p><strong>Command:</strong> <code>{data.get('command', 'N/A')}</code></p>
        {f'<p><strong>Progress:</strong> {data.get("batches_completed", 0)} batches completed</p>' if is_live else ''}
    </div>
"""
    
    for host in data['hosts']:
        html += f"""
    <div class="host">
        <h2>Host: {host['ip']}</h2>
"""
        if host['hostname']:
            html += f"        <p><strong>Hostname:</strong> {host['hostname']}</p>\n"
        if host.get('os'):
            html += f"        <p><strong>OS:</strong> {host['os']} (Accuracy: {host.get('os_accuracy', 'N/A')}%)</p>\n"
        if host.get('mac_address'):
            html += f"        <p><strong>MAC:</strong> {host['mac_address']} ({host.get('mac_vendor', 'Unknown vendor')})</p>\n"
        
        open_ports = [p for p in host['ports'] if p['state'] == 'open']
        if open_ports:
            html += f"        <h3>Open Ports ({len(open_ports)})</h3>\n"
            html += "        <table>\n"
            html += "            <tr><th>Port</th><th>Service</th><th>Version</th><th>Product</th></tr>\n"
            
            for port in open_ports:
                html += f"""
            <tr>
                <td class="open">{port['port']}/{port['protocol']}</td>
                <td>{port.get('service', 'unknown')}</td>
                <td>{port.get('version', '-')}</td>
                <td>{port.get('product', '-')}</td>
            </tr>
"""
                
                if port.get('scripts'):
                    html += "            <tr><td colspan='4'>\n"
                    for script in port['scripts']:
                        html += f"                <div class='script'><strong>{script['id']}:</strong><br><pre>{script['output']}</pre></div>\n"
                    html += "            </td></tr>\n"
            
            html += "        </table>\n"
        
        html += "    </div>\n"
    
    # Add HTTP scan results if available
    if 'http_scan' in data:
        http_data = data['http_scan']
        html += """
    <div class="host">
        <h2>HTTP/HTTPS Scan Results</h2>
"""
        
        # HTTP Services
        services = http_data.get('services', [])
        if services:
            html += f"        <h3>HTTP Services ({len(services)})</h3>\n"
            html += "        <table>\n"
            html += "            <tr><th>URL</th><th>Status</th><th>Server</th><th>Technologies</th><th>Paths Found</th></tr>\n"
            for service in services:
                html += f"""
            <tr>
                <td><a href="{service.get('url', '#')}" style="color: #4fc3f7;">{service.get('url', 'N/A')}</a></td>
                <td>{service.get('status_code', 'N/A')}</td>
                <td>{service.get('server', 'Unknown')}</td>
                <td>{', '.join(service.get('technologies', []))}</td>
                <td>{len(service.get('discovered_paths', []))}</td>
            </tr>
"""
            html += "        </table>\n"
        
        # Vulnerabilities
        vulns = http_data.get('vulnerabilities', [])
        if vulns:
            html += f"        <h3>HTTP Vulnerabilities ({len(vulns)})</h3>\n"
            html += "        <table>\n"
            html += "            <tr><th>Severity</th><th>Type</th><th>Description</th><th>URL</th></tr>\n"
            for vuln in vulns:
                severity_color = {'critical': '#f44336', 'high': '#ff9800', 'medium': '#ffeb3b', 'low': '#4caf50'}.get(vuln.get('severity', 'low'), '#4caf50')
                html += f"""
            <tr>
                <td style="color: {severity_color}; font-weight: bold;">{vuln.get('severity', 'N/A').upper()}</td>
                <td>{vuln.get('type', 'N/A')}</td>
                <td>{vuln.get('description', 'N/A')}</td>
                <td>{vuln.get('url', 'N/A')}</td>
            </tr>
"""
            html += "        </table>\n"
        
        # DNS and Subdomains
        subdomains = http_data.get('subdomains', [])
        dns_records = http_data.get('dns_records', [])
        
        if subdomains or dns_records:
            html += "        <h3>DNS Information</h3>\n"
            
            if subdomains:
                html += f"        <p><strong>Discovered Subdomains ({len(subdomains)}):</strong></p>\n"
                html += "        <ul>\n"
                for subdomain in subdomains[:20]:
                    html += f"            <li>{subdomain}</li>\n"
                html += "        </ul>\n"
            
            if dns_records:
                html += "        <table>\n"
                html += "            <tr><th>Record Type</th><th>Value</th></tr>\n"
                for record in dns_records[:20]:
                    html += f"""
            <tr>
                <td>{record.get('type', 'N/A')}</td>
                <td>{record.get('value', 'N/A')}</td>
            </tr>
"""
                html += "        </table>\n"
        
        html += "    </div>\n"
    
    html += """
</body>
</html>
"""
    return html


if __name__ == "__main__":
    app()
