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
import json
from datetime import datetime
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from workflows.nmap_fast_01.scanner import NmapFastScanner
from workflows.nmap_02.scanner import NmapScanner
from workflows.http_03.scanner import HTTPAdvancedScanner
from workflows.smartlist_04.scanner import SmartListScanner

from config import config
from utils.results import result_manager
from utils.next_steps_generator import generate_next_steps
from utils.debug import debug_print
from models.wordlist_config import DEFAULT_WORDLIST_CONFIG, ServiceType

app = typer.Typer(
    name="ipcrawler",
    help="SmartList Engine - Intelligent wordlist recommendations for security testing",
    no_args_is_help=True,
    add_completion=False,
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


def version_callback(value: bool):
    """Handle --version flag"""
    if value:
        # Read ASCII art
        ascii_art_path = Path(__file__).parent / "media" / "ascii-art.txt"
        if ascii_art_path.exists():
            with open(ascii_art_path, 'r') as f:
                ascii_art = f.read()
                console.print(ascii_art, style="cyan")
        
        # Display version from config
        console.print(f"\n[bold]IPCrawler SmartList Engine[/bold] version [green]{config.version}[/green]")
        console.print("Intelligent wordlist recommendations powered by target analysis\n")
        raise typer.Exit()


@app.command()
def main(
    target: str = typer.Argument(None, help="Target IP address or hostname to analyze for wordlist recommendations"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output"),
    audit: bool = typer.Option(False, "--audit", help="Run comprehensive SmartList audit (rules, entropy, usage)"),
    details: bool = typer.Option(False, "--details", help="Show detailed conflict analysis (use with --audit)"),
    version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Show version information")
):
    """Analyze target and recommend optimal wordlists for security testing"""
    if audit:
        # Run comprehensive audit instead of normal workflow
        exit_code = run_comprehensive_audit(show_details=details)
        raise typer.Exit(exit_code)
    
    if target is None:
        console.print("[red]Error:[/red] Target is required")
        raise typer.Exit(1)
    asyncio.run(run_workflow(target, debug))

def run_comprehensive_audit(show_details: bool = False):
    """Run enhanced comprehensive SmartList audit with advanced flaw detection"""
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # Run enhanced audit script as module
        result = subprocess.run([sys.executable, "-m", "src.core.scorer.enhanced_audit"], 
                              capture_output=True, text=True, cwd=Path(__file__).parent)
        
        # Display the output directly (enhanced audit handles its own formatting)
        if result.stdout:
            console.print(result.stdout)
        
        if result.stderr:
            console.print(f"[red]Audit warnings:[/red] {result.stderr}")
            
        # If details requested, run the conflict analyzer
        if show_details and result.returncode == 0:
            console.print("\n[bold cyan]🔍 Running Detailed Conflict Analysis...[/bold cyan]")
            detail_result = subprocess.run([sys.executable, "-m", "src.core.scorer.conflict_analyzer", "--detailed"], 
                                         capture_output=True, text=True, cwd=Path(__file__).parent)
            
            if detail_result.stdout:
                console.print(detail_result.stdout)
            if detail_result.stderr:
                console.print(f"[red]Detail analysis errors:[/red] {detail_result.stderr}")
        
        # Exit with the same code as the audit
        if result.returncode != 0:
            console.print(f"\n[yellow]⚠ Audit completed with issues (exit code: {result.returncode})[/yellow]")
        
        return result.returncode
        
    except Exception as e:
        console.print(f"[red]Enhanced audit failed:[/red] {e}")
        console.print("[yellow]Falling back to legacy audit...[/yellow]")
        return run_legacy_audit()

def run_legacy_audit():
    """Legacy audit system as fallback"""
    console.print("🔍 [bold cyan]SmartList Comprehensive Audit[/bold cyan]")
    console.print("=" * 60)
    console.print()
    
    # Part 1: Rule Quality Audit
    console.print("[bold]📋 Part 1: Rule Quality Analysis[/bold]")
    console.print("-" * 50)
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # Run rule audit script as module
        result = subprocess.run([sys.executable, "-m", "src.core.scorer.rule_audit"], 
                              capture_output=True, text=True, cwd=Path(__file__).parent)
        
        # Parse and display key findings
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if any(keyword in line for keyword in ['❌', '⚠️', '🔄', '✅', '📊']):
                console.print(line)
    except Exception as e:
        console.print(f"[red]Rule audit failed:[/red] {e}")
    
    console.print()
    
    # Part 2: Entropy Analysis
    console.print("[bold]📊 Part 2: Entropy & Diversity Analysis[/bold]")
    console.print("-" * 50)
    run_entropy_audit(days_back=30)
    
    console.print()
    
    # Part 3: Scoring Statistics
    console.print("[bold]📈 Part 3: Scoring System Statistics[/bold]")
    console.print("-" * 50)
    try:
        from src.core.scorer.scorer_engine import get_scoring_stats
        from src.core.scorer.rules import get_rule_frequency_stats
        
        # Get scoring stats
        stats = get_scoring_stats()
        console.print(f"   Exact Rules: {stats.get('exact_rules', 0)}")
        console.print(f"   Tech Categories: {stats.get('tech_categories', 0)}")
        console.print(f"   Port Categories: {stats.get('port_categories', 0)}")
        console.print(f"   Total Wordlists: {stats.get('total_wordlists', 0)}")
        console.print(f"   Wordlist Alternatives: {stats.get('wordlist_alternatives', 0)}")
        
        # Get frequency stats
        freq_stats = get_rule_frequency_stats()
        if freq_stats['total_rules'] > 0:
            console.print(f"\n   [bold]Rule Frequency Analysis:[/bold]")
            console.print(f"   Rules Tracked: {freq_stats['total_rules']}")
            console.print(f"   Average Frequency: {freq_stats['average_frequency']:.3f}")
            
            if freq_stats['most_frequent']:
                console.print(f"\n   🔥 Most Frequent Rules:")
                for rule, freq in freq_stats['most_frequent'][:3]:
                    console.print(f"      {rule}: {freq:.2%}")
            
            if freq_stats['least_frequent']:
                console.print(f"\n   ❄️  Least Frequent Rules:")
                for rule, freq in freq_stats['least_frequent'][:3]:
                    console.print(f"      {rule}: {freq:.2%}")
    except Exception as e:
        console.print(f"[red]Stats analysis failed:[/red] {e}")
    
    console.print()
    console.print("[bold green]✅ Audit Complete![/bold green]")
    console.print()
    console.print("💡 [bold]Next Steps:[/bold]")
    console.print("   1. Review and fix any ❌ ERROR issues first")
    console.print("   2. Address ⚠️  WARNING items to improve quality")
    console.print("   3. Monitor entropy scores regularly")
    console.print("   4. Update wordlist alternatives for overused items")


def run_entropy_audit(days_back: int = 30, context_tech: str = None, context_port: int = None):
    """Run entropy analysis portion of the audit"""
    
    try:
        from src.core.scorer.entropy import analyzer
        from src.core.scorer.models import ScoringContext
        from src.core.scorer.cache import cache
        
        # Create context filter if specified
        context_filter = None
        if context_tech or context_port:
            context_filter = ScoringContext(
                target="audit",
                port=context_port or 80,
                service="audit",
                tech=context_tech
            )
        
        # Run entropy analysis
        console.print(f"\n📊 Analyzing {days_back} days of recommendation data...")
        metrics = analyzer.analyze_recent_selections(days_back, context_filter)
        
        # Display results
        console.print(f"\n📈 [bold]Entropy Analysis Results[/bold]")
        console.print(f"   Entropy Score: [{'green' if metrics.entropy_score > 0.7 else 'yellow' if metrics.entropy_score > 0.4 else 'red'}]{metrics.entropy_score:.3f}[/]")
        console.print(f"   Quality: [{'green' if metrics.recommendation_quality in ['excellent', 'good'] else 'yellow' if metrics.recommendation_quality == 'acceptable' else 'red'}]{metrics.recommendation_quality}[/]")
        console.print(f"   Total Recommendations: {metrics.total_recommendations}")
        console.print(f"   Unique Wordlists: {metrics.unique_wordlists}")
        console.print(f"   Clustering: {metrics.clustering_percentage:.1f}%")
        console.print(f"   Context Diversity: {metrics.context_diversity:.3f}")
        
        if metrics.warning_message:
            console.print(f"\n⚠️  [yellow]{metrics.warning_message}[/]")
        
        # Show most common wordlists
        if metrics.most_common_wordlists:
            console.print(f"\n🔄 [bold]Most Common Wordlists:[/bold]")
            for wordlist, count in metrics.most_common_wordlists[:5]:
                percentage = (count / metrics.total_recommendations) * 100
                icon = "🔥" if percentage > 50 else "📈" if percentage > 25 else "📊"
                console.print(f"   {icon} {wordlist}: {count} times ({percentage:.1f}%)")
        
        # Show context clusters
        console.print(f"\n🎯 [bold]Context Clustering Analysis:[/bold]")
        clusters = analyzer.detect_context_clusters(days_back)
        
        if clusters:
            for cluster in clusters[:5]:  # Top 5 clusters
                console.print(f"\n   📦 {cluster.tech or 'Unknown'}:{cluster.port_category}")
                console.print(f"      Count: {cluster.count} contexts")
                console.print(f"      Common wordlists: {', '.join(cluster.wordlists[:3])}")
        else:
            console.print("   ✅ No significant clustering detected")
        
        # Cache statistics
        try:
            cache_stats = cache.get_stats()
            console.print(f"\n💾 [bold]Cache Statistics:[/bold]")
            console.print(f"   Total Files: {cache_stats['total_files']}")
            console.print(f"   Date Directories: {cache_stats['date_directories']}")
        except Exception as e:
            console.print(f"\n⚠️  Could not get cache stats: {e}")
        
        # Recommendations
        console.print(f"\n💡 [bold]Recommendations:[/bold]")
        if metrics.entropy_score < 0.5:
            console.print("   🔧 Critical: Enable diversification alternatives")
            console.print("   📝 Review rule mappings for overlap reduction")
        elif metrics.entropy_score < 0.7:
            console.print("   ⚠️  Consider adding more specific wordlist alternatives")
        else:
            console.print("   ✅ Entropy levels are healthy")
        
        if metrics.clustering_percentage > 50:
            console.print("   🎯 High clustering detected - review port/tech categorization")
        
    except ImportError as e:
        console.print(f"[red]Error:[/red] Entropy analysis not available: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Audit failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)


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
            return target
        else:
            console.print(f"  ✗ Failed to resolve {target}")
            return target
            
    except Exception as e:
        console.print(f"  ⚠ DNS resolution warning: {str(e)}")
        return target  # Let nmap handle it


async def check_and_offer_sudo_escalation():
    """Check current privileges and offer sudo escalation if beneficial"""
    import os
    import subprocess
    import sys
    
    # Skip if already running as root
    if os.geteuid() == 0:
        console.print("✓ Running with [green]root privileges[/green] - Enhanced fingerprinting capabilities enabled")
        return
    
    # Check configuration settings
    if not config.prompt_for_sudo and not config.auto_escalate:
        console.print("ℹ Running with [yellow]user privileges[/yellow] - sudo escalation disabled in config")
        return
    
    # Check if sudo is available
    try:
        # Check if sudo command exists
        subprocess.run(['which', 'sudo'], capture_output=True, check=True)
        
        # Check if user is in sudoers (can use sudo with or without password)
        # This approach assumes sudo is available if the command exists and user is not root
        # sudo availability check assumes user can use sudo if command exists
        sudo_available = True
        
    except (FileNotFoundError, subprocess.CalledProcessError):
        sudo_available = False
    
    if not sudo_available:
        console.print("ℹ Running with [yellow]user privileges[/yellow] - sudo not available")
        console.print("  → TCP connect analysis (slower than SYN fingerprinting)")
        console.print("  → No OS detection capabilities")
        console.print("  → Limited timing optimizations")
        return
    
    # Auto-escalate if configured
    if config.auto_escalate:
        console.print("→ Auto-escalating to sudo (configured in config.yaml)")
        escalate = True
    else:
        # Offer escalation
        console.print("\n🔒 [bold]Privilege Escalation Available[/bold]")
        console.print("\n[green]Enhanced capabilities with sudo:[/green]")
        console.print("  ✓ SYN stealth fingerprinting (faster, more accurate)")
        console.print("  ✓ OS detection and fingerprinting") 
        console.print("  ✓ Advanced timing optimizations")
        console.print("  ✓ Raw socket access")
        console.print("  ✓ Service detection optimizations")
        console.print("  ✓ Automatic /etc/hosts updates for hostname mapping")
        
        console.print("\n[yellow]Current limitations:[/yellow]")
        console.print("  • TCP connect analysis only (slower)")
        console.print("  • No OS detection")
        console.print("  • Limited nmap capabilities")
        
        # Get user choice
        escalate = typer.confirm("\nWould you like to restart with sudo for enhanced analysis?", default=True)
    
    if escalate:
        # Build the correct sudo command based on how script was called
        script_path = os.path.abspath(__file__)
        original_args = sys.argv[1:]  # Get arguments without script name
        
        # Build sudo command with explicit Python execution
        sudo_cmd = ['sudo', sys.executable, script_path] + original_args
        
        console.print(f"\n→ Restarting with sudo: [dim]{' '.join(sudo_cmd)}[/dim]")
        
        try:
            os.execvp('sudo', sudo_cmd)
        except Exception as e:
            console.print(f"✗ Failed to escalate privileges: {e}")
            console.print("→ Continuing with user privileges...")
    else:
        console.print("→ Continuing with user privileges...")


async def run_workflow(target: str, debug: bool = False):
    """Execute SmartList analysis workflow on target"""
    # Set debug mode
    from utils.debug import set_debug
    set_debug(debug)
    
    # Clean up any existing nmap processes first
    cleanup_existing_nmap_processes()
    
    # Check if we should offer sudo escalation BEFORE starting any workflows
    await check_and_offer_sudo_escalation()
    
    # Resolve target first
    resolved_target = await resolve_target(target)
    
    console.print("→ Starting port discovery with hostname discovery...")
    
    workspace = result_manager.create_workspace(target)
    
    # IMPORTANT: Default behavior is to scan ONLY discovered ports
    # Full 65535 port scan only happens when fast_port_discovery is explicitly set to false
    discovered_ports = None
    total_execution_time = 0.0
    
    if config.fast_port_discovery:
        console.print("→ Starting fast port discovery...")
        
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
                    console.print(f"    • [cyan]{mapping['hostname']}[/cyan] → {mapping['ip']}")
                if discovery_result.data.get("etc_hosts_updated"):
                    console.print("    ✓ [green]/etc/hosts updated[/green]")
                elif discovery_result.data.get("scan_mode") == "unprivileged":
                    console.print("    ℹ️  [yellow]Restart with 'sudo' to update /etc/hosts[/yellow]")
            
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
                result_manager.save_results(workspace, target, empty_data)
                display_minimal_summary(empty_data, workspace)
                return
            
            if port_count > config.max_detailed_ports:
                console.print(f"⚠ Found {port_count} services, limiting detailed analysis to top {config.max_detailed_ports}")
                discovered_ports = discovered_ports[:config.max_detailed_ports]
        else:
            console.print(f"✗ Port discovery failed: {discovery_result.error}")
            console.print("⚠ Cannot proceed without port discovery. Exiting.")
            console.print("  To analyze all services, set 'fast_port_discovery: false' in config.yaml")
            return
    
    console.print("→ Starting detailed service analysis...")
    scanner = NmapScanner(batch_size=config.batch_size, ports_per_batch=config.ports_per_batch)
    
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        if discovered_ports is not None:
            task = progress.add_task(f"Detailed analysis of {len(discovered_ports)} discovered services...", total=None)
        else:
            task = progress.add_task(f"Full analysis of all 65535 ports (10 parallel batches)...", total=None)
        
        result = await scanner.execute(
            target=resolved_target,
            ports=discovered_ports
        )
        
        progress.update(task, completed=True)
    
    if result.success and result.data:
        total_execution_time += result.execution_time or 0.0
        console.print(f"✓ Service analysis completed in {total_execution_time:.2f}s")
        
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
            
            console.print(f"\n→ Found {len(http_ports)} HTTP/HTTPS services. Starting advanced web analysis...")
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
                console.print(f"✓ HTTP analysis completed in {http_result.execution_time:.2f}s")
                http_scan_data = http_result.data
                
                # Display HTTP findings
                display_http_summary(http_result.data)
            else:
                error_msg = http_result.error or (http_result.errors[0] if http_result.errors else "Unknown error")
                console.print(f"⚠ HTTP analysis failed: {error_msg}")
        

        # Run SmartList analysis after HTTP scan if we have services
        smartlist_data = None
        if http_scan_data and http_scan_data.get('services'):
            console.print(f"\n→ Analyzing services for wordlist recommendations...")
            
            # Prepare previous results for SmartList
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
            
            smartlist_scanner = SmartListScanner()
            smartlist_result = await smartlist_scanner.execute(
                target=resolved_target,
                previous_results=previous_results
            )
            
            if smartlist_result.success and smartlist_result.data:
                total_execution_time += smartlist_result.execution_time or 0.0
                console.print(f"✓ SmartList analysis completed in {smartlist_result.execution_time:.2f}s")
                smartlist_data = smartlist_result.data
                
                # Display top wordlist recommendations
                display_smartlist_summary(smartlist_data)
                
                # Save wordlist paths to an easy-to-use file
                save_wordlist_paths(smartlist_data, workspace, http_scan_data)
                
                # Generate next-steps commands
                generate_next_steps_file(workspace)
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
        
        if smartlist_data:
            result.data['smartlist'] = smartlist_data
        

        
        console.print(f"\n✓ All analysis completed in {total_execution_time:.2f}s total")
        
        result_manager.save_results(workspace, target, result.data)
        
        # Generate next-steps file even if SmartList didn't run
        if not smartlist_data:
            console.print(f"\n→ Generating next-steps commands based on discovered services...")
            generate_next_steps_file(workspace)
        
        # Display minimal summary only
        display_minimal_summary(result.data, workspace)
    else:
        console.print(f"✗ Scan failed: {result.error}")
        raise typer.Exit(1)
    
    # Clean up processes after scan completion
    cleanup_processes()
    


def generate_next_steps_file(workspace: Path):
    """Generate comprehensive next-steps commands file"""
    try:
        next_steps_file = generate_next_steps(workspace)
        if next_steps_file:
            console.print(f"\n🚀 Next steps saved to: [bold]{next_steps_file}[/bold]")
            console.print("   Ready-to-use commands for your next testing phase!")
        else:
            console.print("\n⚠ Could not generate next-steps file")
    except Exception as e:
        console.print(f"\n⚠ Error generating next-steps: {e}")


def save_wordlist_paths(smartlist_data: dict, workspace: Path, http_scan_data: dict = None):
    """Save recommended wordlist paths and complete tool commands to a file for easy copy-paste"""
    try:
        recommendations = smartlist_data.get('wordlist_recommendations', [])
        if not recommendations:
            return
        
        # Extract target IP for commands
        target_ip = smartlist_data.get('target', 'TARGET')
        
        # Extract discovered hostnames from passed HTTP scan data
        discovered_hostnames = []
        hostname_debug_info = []
        
        try:
            if http_scan_data:
                hostname_debug_info.append("Using provided HTTP scan data")
                
                # Get tested hostnames from HTTP scan (same logic as NextStepsGenerator)
                tested_hostnames = http_scan_data.get('tested_hostnames', [])
                hostname_debug_info.append(f"Tested hostnames: {tested_hostnames}")
                
                # Filter to get actual hostnames (not IPs)
                for hostname in tested_hostnames:
                    if (hostname and 
                        not hostname.replace('.', '').isdigit() and  # Not an IP
                        '.' in hostname and  # Has domain structure
                        hostname != target_ip):  # Different from target IP
                        discovered_hostnames.append(hostname)
                
                # Remove duplicates while preserving order
                seen = set()
                unique_hostnames = []
                for hostname in discovered_hostnames:
                    if hostname not in seen:
                        seen.add(hostname)
                        unique_hostnames.append(hostname)
                discovered_hostnames = unique_hostnames[:5]  # Limit to top 5
                
                hostname_debug_info.append(f"Final discovered hostnames: {discovered_hostnames}")
            else:
                hostname_debug_info.append("No HTTP scan data provided")
                    
        except Exception as e:
            hostname_debug_info.append(f"Error extracting hostnames: {e}")
            # Continue with IP if hostname extraction fails
            
        wordlists_file = workspace / "recommended_wordlists.txt"
        
        with open(wordlists_file, 'w', encoding='utf-8') as f:
            f.write("# IPCrawler Recommended Wordlists\n")
            f.write("# Ready-to-copy commands with recommended wordlists\n")
            f.write(f"# Target IP: {target_ip}\n")
            if discovered_hostnames:
                f.write(f"# Discovered Hostnames: {', '.join(discovered_hostnames)}\n")
                f.write(f"# Using hostname-based URLs for better enumeration\n")
            else:
                f.write("# No hostnames discovered - using IP addresses\n")
                f.write("# Debug info: " + " | ".join(hostname_debug_info) + "\n")
            f.write("\n")
            
            for service_rec in recommendations:
                service_name = service_rec['service']
                tech = service_rec.get('detected_technology', 'Unknown')
                top_wordlists = service_rec.get('top_wordlists', [])[:3]  # Top 3
                
                if top_wordlists:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"# {service_name.upper()} ({tech})\n")
                    f.write(f"{'='*60}\n\n")
                    
                    # Extract port and protocol for URLs
                    if ':' in service_name:
                        host_port = service_name.split(':')
                        if len(host_port) == 2:
                            host, port = host_port[0], host_port[1]
                            port_num = int(port) if port.isdigit() else 80
                            
                            # Check if this is a non-web service that needs different tools
                            is_non_web_service = port_num not in [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]
                            
                            if is_non_web_service:
                                f.write(f"# Port {port} ({service_rec.get('service_name', 'unknown')}) - Non-web service\n")
                                f.write(f"# Appropriate tools for {service_rec.get('service_name', 'unknown')}:\n\n")
                                
                                # Process wordlists for non-web services
                                for i, wl in enumerate(top_wordlists, 1):
                                    wordlist_path = wl.get('path', '').strip()
                                    wordlist_name = wl.get('wordlist', '').strip()
                                    
                                    # Clean up path
                                    if wordlist_path.endswith('\\\\'):
                                        wordlist_path = wordlist_path[:-1]
                                    
                                    # Use fallback if no path available OR if path is inappropriate for SSH
                                    if not wordlist_path:
                                        if port_num == 22:
                                            wordlist_path = f"/usr/share/seclists/Passwords/Default-Credentials/{wordlist_name}"
                                        else:
                                            wordlist_path = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                                    elif port_num == 22 and not DEFAULT_WORDLIST_CONFIG.is_wordlist_appropriate(wordlist_path, ServiceType.SSH):
                                        # Override inappropriate SSH wordlists
                                        f.write(f"# WARNING: SmartList suggested inappropriate wordlist for SSH: {wordlist_path}\n")
                                        f.write(f"# Using appropriate SSH credential wordlist instead\n")
                                        wordlist_path = DEFAULT_WORDLIST_CONFIG.get_fallback_wordlist(ServiceType.SSH)
                                        wordlist_name = "ssh-default-passwords.txt"
                                    
                                    f.write(f"# {i}. {wl['confidence']} CONFIDENCE - {wl['reason']}\n")
                                    f.write(f"# Wordlist: {wordlist_name}\n")
                                    f.write(f"# Path: {wordlist_path}\n\n")
                                    
                                    # Determine service type for tool selection
                                    service_type = ServiceType.UNKNOWN
                                    if port_num == 22 or 'ssh' in service_rec.get('service_name', '').lower():
                                        service_type = ServiceType.SSH
                                    elif port_num == 21 or 'ftp' in service_rec.get('service_name', '').lower():
                                        service_type = ServiceType.FTP
                                    elif port_num == 3306 or 'mysql' in service_rec.get('service_name', '').lower():
                                        service_type = ServiceType.MYSQL
                                    elif port_num == 5432 or 'postgres' in service_rec.get('service_name', '').lower():
                                        service_type = ServiceType.POSTGRESQL
                                    elif port_num == 1433 or 'mssql' in service_rec.get('service_name', '').lower():
                                        service_type = ServiceType.MSSQL
                                    
                                    # Generate appropriate commands based on service type
                                    if service_type == ServiceType.SSH:
                                        f.write(f"# SSH Brute Force:\n")
                                        f.write(f"hydra -l admin -P \"{wordlist_path}\" ssh://{host}\n")
                                        f.write(f"ncrack -p22 --user admin -P \"{wordlist_path}\" {host}\n")
                                        f.write(f"medusa -h {host} -u admin -P \"{wordlist_path}\" -M ssh\n\n")
                                    elif service_type == ServiceType.FTP:
                                        f.write(f"# FTP Brute Force:\n")
                                        f.write(f"hydra -l anonymous -P \"{wordlist_path}\" ftp://{host}\n")
                                        f.write(f"ncrack -p21 --user anonymous -P \"{wordlist_path}\" {host}\n\n")
                                    elif service_type in [ServiceType.MYSQL, ServiceType.POSTGRESQL, ServiceType.MSSQL]:
                                        f.write(f"# Database Brute Force:\n")
                                        if service_type == ServiceType.MYSQL:
                                            f.write(f"hydra -l root -P \"{wordlist_path}\" mysql://{host}\n\n")
                                        elif service_type == ServiceType.POSTGRESQL:
                                            f.write(f"hydra -l postgres -P \"{wordlist_path}\" postgres://{host}\n\n")
                                        else:  # MSSQL
                                            f.write(f"hydra -l sa -P \"{wordlist_path}\" mssql://{host}\n\n")
                                    else:
                                        f.write(f"# Generic service enumeration - manual investigation required\n")
                                        f.write(f"# Service type: {service_type.value}\n\n")
                                    
                                    f.write(f"{'='*40}\n\n")
                                
                                continue  # Skip web fuzzing for non-web services
                            
                            # Use discovered hostname if available, otherwise use the host from service
                            target_host = host
                            if discovered_hostnames:
                                # Use the first discovered hostname (usually the main one)
                                target_host = discovered_hostnames[0]
                                f.write(f"# Using discovered hostname: {target_host} (instead of {host})\n")
                            
                            # Determine protocol for web services
                            if port_num in [443, 8443]:
                                if port_num == 443:
                                    url = f"https://{target_host}"  # Standard HTTPS port
                                else:
                                    url = f"https://{target_host}:{port}"
                            else:
                                if port_num == 80:
                                    url = f"http://{target_host}"  # Standard HTTP port
                                else:
                                    url = f"http://{target_host}:{port}"
                        else:
                            url = f"http://{service_name}"
                    else:
                        url = f"http://{service_name}"
                    
                    for i, wl in enumerate(top_wordlists, 1):
                        wordlist_path = wl.get('path', '').strip()
                        wordlist_name = wl.get('wordlist', '').strip()
                        
                        # Remove any trailing characters that might cause issues
                        if wordlist_path.endswith('\\'):
                            wordlist_path = wordlist_path[:-1]
                        
                        # Validate path matches wordlist name
                        if wordlist_path and wordlist_name:
                            # Check if the filename in the path matches the wordlist name
                            import os
                            path_filename = os.path.basename(wordlist_path)
                            if path_filename != wordlist_name:
                                f.write(f"# WARNING: Wordlist name mismatch - Name: {wordlist_name}, Path points to: {path_filename}\\n")
                                # Use the path since it's likely more accurate
                                actual_wordlist_name = path_filename
                            else:
                                actual_wordlist_name = wordlist_name
                        else:
                            actual_wordlist_name = wordlist_name or "unknown.txt"
                        
                        # Use fallback if no path available
                        if not wordlist_path:
                            wordlist_path = f"/usr/share/seclists/Discovery/Web-Content/{actual_wordlist_name}"
                        
                        confidence = wl['confidence']
                        reason = wl['reason']
                        
                        f.write(f"# {i}. {confidence} CONFIDENCE - {reason}\n")
                        f.write(f"# Wordlist: {actual_wordlist_name}\n")
                        f.write(f"# Path: {wordlist_path}\n\n")
                        
                        # Create safe filename for output (remove extension and special chars)
                        safe_filename = actual_wordlist_name.replace('.txt', '').replace('.', '_').replace('/', '_')
                        
                        # Add multiple tool command examples
                        f.write("# FEROXBUSTER (Recommended):\n")
                        f.write(f"feroxbuster --url {url} --wordlist \"{wordlist_path}\" -x php,html,txt,js,asp,aspx,jsp -t 50 --depth 3 -o ferox_{safe_filename}_results.txt\n\n")
                        
                        f.write("# GOBUSTER:\n")
                        f.write(f"gobuster dir -u {url} -w \"{wordlist_path}\" -x php,html,txt,js,asp,aspx,jsp -t 50 -b 301,302,403 -o gobuster_{safe_filename}_results.txt\n\n")
                        
                        f.write("# FFUF:\n")
                        f.write(f"ffuf -u {url}/FUZZ -w \"{wordlist_path}\" -e .php,.html,.txt,.js,.asp,.aspx,.jsp -t 50 -fc 301,302,403 -o ffuf_{safe_filename}_results.json\n\n")
                        
                        f.write(f"{'='*40}\n\n")
        
        console.print(f"\n📁 Wordlist commands saved to: [bold]{wordlists_file}[/bold]")
        console.print("   Complete feroxbuster/gobuster/ffuf commands ready to copy-paste")
        
    except Exception as e:
        # Don't fail the whole process if file saving fails
        debug_print(f"Failed to save wordlist paths: {e}")


# Wordlist validation functions have been moved to models/wordlist_config.py
# This provides a cleaner, more maintainable Pydantic-based configuration system


def display_smartlist_summary(smartlist_data: dict):
    """Display SmartList wordlist recommendations"""
    recommendations = smartlist_data.get('wordlist_recommendations', [])
    if not recommendations:
        return
    
    console.print("\n📋 Recommended wordlists:")
    
    for service_rec in recommendations:
        top_wordlists = service_rec.get('top_wordlists', [])[:2]  # Only top 2
        if not top_wordlists:
            continue
            
        service_name = service_rec['service']
        tech = service_rec.get('detected_technology', 'Unknown')
        confidence = service_rec.get('confidence', 'LOW')
        
        console.print(f"  {service_name} ({tech}):")
        for i, wl in enumerate(top_wordlists, 1):
            confidence_color = "green" if wl['confidence'] == "HIGH" else "yellow" if wl['confidence'] == "MEDIUM" else "red"
            # Show just the filename for compact display, full paths are in the saved file
            wordlist_name = wl['wordlist']
            wordlist_path = wl.get('path')
            
            if wordlist_path:
                # Show compact version: just filename with note about full path
                console.print(f"    {i}. [bold]{wordlist_name}[/bold] ([{confidence_color}]{wl['confidence']}[/{confidence_color}] - {wl['reason']})")
                console.print(f"       → Full path saved to recommended_wordlists.txt")
            else:
                console.print(f"    {i}. [bold]{wordlist_name}[/bold] ([{confidence_color}]{wl['confidence']}[/{confidence_color}] - {wl['reason']})")


def display_minimal_summary(data: dict, workspace: Path):
    """Display minimal analysis summary"""
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
    
    # Show discovered hostnames
    if scan_result.get('hostname_mappings'):
        hostnames = [m['hostname'] for m in scan_result['hostname_mappings']]
        summary.add_row("Discovered Hostnames", ", ".join(hostnames))
    
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
