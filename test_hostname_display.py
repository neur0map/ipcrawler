#!/usr/bin/env python3
"""Test script to verify hostname discovery is displayed and saved properly"""

import asyncio
from workflows.nmap_fast_01.scanner import NmapFastScanner
from utils.results import result_manager
from rich.console import Console

console = Console()

async def test_hostname_display():
    """Test that hostname discovery results are displayed"""
    
    # Mock discovery result data that would come from nmap_fast_01
    mock_discovery_data = {
        "tool": "nmap-fast",
        "target": "10.10.11.166",
        "open_ports": [22, 80],
        "port_count": 2,
        "scan_mode": "privileged",
        "hostname_mappings": [
            {"ip": "10.10.11.166", "hostname": "whiterabbit.htb"},
            {"ip": "10.10.11.166", "hostname": "admin.whiterabbit.htb"}
        ],
        "etc_hosts_updated": True
    }
    
    # Test display logic from ipcrawler.py
    console.print("✓ Port discovery completed")
    console.print(f"  Found {mock_discovery_data['port_count']} open ports")
    
    # Display discovered hostnames (new code)
    hostname_mappings = mock_discovery_data.get("hostname_mappings", [])
    if hostname_mappings:
        console.print(f"  → Discovered {len(hostname_mappings)} hostname(s):")
        for mapping in hostname_mappings:
            console.print(f"    • [cyan]{mapping['hostname']}[/cyan] → {mapping['ip']}")
        if mock_discovery_data.get("etc_hosts_updated"):
            console.print("    ✓ [green]/etc/hosts updated[/green]")
    
    # Test that data is saved properly
    console.print("\nTesting result saving...")
    
    # Create mock full scan data that includes hostname mappings
    full_scan_data = {
        "tool": "nmap",
        "target": "10.10.11.166",
        "duration": 45.23,
        "total_hosts": 1,
        "up_hosts": 1,
        "down_hosts": 0,
        "hosts": [{
            "ip": "10.10.11.166",
            "hostname": "whiterabbit.htb",
            "ports": [
                {"port": 22, "protocol": "tcp", "state": "open", "service": "ssh"},
                {"port": 80, "protocol": "tcp", "state": "open", "service": "http"}
            ]
        }],
        "hostname_mappings": mock_discovery_data["hostname_mappings"],
        "discovery_enabled": True,
        "discovered_ports": 2
    }
    
    # Test workspace creation and saving
    workspace = result_manager.create_workspace("10.10.11.166")
    result_manager.save_results(workspace, "10.10.11.166", full_scan_data, formats=['txt'])
    
    console.print(f"✓ Results saved to: [green]{workspace}[/green]")
    
    # Read and display the saved text report
    report_path = workspace / "scan_report.txt"
    if report_path.exists():
        with open(report_path, 'r') as f:
            content = f.read()
        
        # Check if hostname mappings are in the report
        if "Discovered Hostname Mappings" in content:
            console.print("✓ Hostname mappings found in saved report")
            # Show relevant section
            lines = content.split('\n')
            in_hostname_section = False
            for line in lines:
                if "Discovered Hostname Mappings" in line:
                    in_hostname_section = True
                    console.print(f"\n[yellow]{line}[/yellow]")
                elif in_hostname_section and line.startswith("  "):
                    console.print(f"[cyan]{line}[/cyan]")
                elif in_hostname_section and "=" in line:
                    break
        else:
            console.print("✗ Hostname mappings NOT found in saved report")
    else:
        console.print("✗ Report file not found")

if __name__ == "__main__":
    asyncio.run(test_hostname_display())