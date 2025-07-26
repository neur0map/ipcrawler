"""Nmap utilities shared across workflows"""

import os
from typing import List, Optional


def is_root() -> bool:
    """Check if running with root privileges"""
    return os.geteuid() == 0


def build_nmap_command(
    port_spec: str,
    is_root: bool = None,
    flags: Optional[List[str]] = None,
    scan_type: str = "default"
) -> List[str]:
    """Build nmap command based on privileges and scan type
    
    Args:
        port_spec: Port specification (e.g., "80,443", "1-1000", "-")
        is_root: Override root detection (None = auto-detect)
        flags: Additional nmap flags
        scan_type: Scan type ("fast", "detailed", "default")
        
    Returns:
        Complete nmap command as list of strings
    """
    if is_root is None:
        is_root = is_root()
    
    # Base command
    cmd = ["nmap"]
    
    # Scan technique based on privileges
    if is_root:
        cmd.extend(["-sS"])  # SYN scan (requires root)
    else:
        cmd.extend(["-sT"])  # TCP connect scan
    
    # Scan type specific options
    if scan_type == "fast":
        cmd.extend([
            "-T4",                  # Aggressive timing
            "--min-rate", "1000" if is_root else "500",
            "--max-retries", "2",
            "--max-rtt-timeout", "100ms",
            "--host-timeout", "5m",
            "--open",               # Only show open ports
            "-Pn",                  # Skip ping
            "-n",                   # No DNS resolution
            "-v"                    # Verbose
        ])
    elif scan_type == "detailed":
        from src.core.config import config
        
        cmd.extend([
            "-sV",                  # Version detection
            "--version-intensity", "5",  # Reduced intensity (default is 7)
        ])
        
        # Only add scripts if fast_detailed_scan is not enabled
        if not config.fast_detailed_scan:
            cmd.extend([
                "-sC",                  # Default scripts
                "--script-timeout", "10s",   # Limit script execution time
            ])
        
        cmd.extend([
            "-T4",                  # Aggressive timing
            "--max-retries", "2",   # Limit retries
            "--host-timeout", "10m", # Overall host timeout
            "-Pn",                  # Skip ping for faster scanning
            "-n",                   # No DNS resolution
        ])
    else:  # default
        cmd.extend([
            "-sV",                  # Version detection
            "-sC",                  # Default scripts
            "-T4",                  # Aggressive timing
        ])
    
    # Port specification
    cmd.extend([f"-p{port_spec}"])
    
    # XML output to stdout
    cmd.extend(["-oX", "-"])
    
    # Additional flags
    if flags:
        cmd.extend(flags)
    
    return cmd


def build_fast_discovery_command(target: str, output_file: str, is_root: bool = None) -> List[str]:
    """Build fast port discovery command
    
    Args:
        target: Target to scan
        output_file: Output file path for grepable format
        is_root: Override root detection
        
    Returns:
        Complete nmap command for fast discovery
    """
    if is_root is None:
        is_root = is_root()
    
    cmd = ["nmap", "-p-"]  # All ports
    
    if is_root:
        cmd.extend([
            "-sS",                  # SYN scan
            "--min-rate", "1000",
        ])
    else:
        cmd.extend([
            "-sT",                  # TCP connect
            "--min-rate", "500",
        ])
    
    cmd.extend([
        "-T4",                      # Aggressive timing
        "--max-retries", "2",
        "--max-rtt-timeout", "100ms",
        "--host-timeout", "5m",
        "--open",                   # Only open ports
        "-Pn",                      # Skip ping
        "-n",                       # No DNS resolution
        "-v",                       # Verbose
        "-oG", output_file,         # Grepable output
        target
    ])
    
    return cmd


def build_hostname_discovery_command(target: str, ports: List[int], output_file: str) -> List[str]:
    """Build hostname discovery command for HTTP ports
    
    Args:
        target: Target to scan
        ports: List of HTTP ports to check
        output_file: Output file path
        
    Returns:
        Complete nmap command for hostname discovery
    """
    port_list = ','.join(map(str, ports))
    
    return [
        "nmap",
        "-p", port_list,
        "-sC",                              # Default scripts
        "--script", "http-title,http-headers,http-methods,http-enum,ssl-cert",
        "-T4",                              # Fast timing
        "--max-retries", "1",
        "--host-timeout", "30s",
        "-Pn",                              # Skip ping
        "-oN", output_file,                 # Normal output
        target
    ]