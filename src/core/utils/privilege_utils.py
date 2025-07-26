"""Privilege escalation and management utilities for IPCrawler"""

import os
import sys
import subprocess
from typing import Optional, List
from src.core.ui.console.base import console
from src.core.config import config


def is_root() -> bool:
    """Check if running with root privileges"""
    return os.geteuid() == 0


def check_sudo_availability() -> bool:
    """Check if sudo is available and user can use it
    
    Returns:
        True if sudo is available, False otherwise
    """
    try:
        # Check if sudo command exists
        subprocess.run(['which', 'sudo'], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


async def check_and_offer_sudo_escalation(original_args: Optional[List[str]] = None):
    """Check current privileges and offer sudo escalation if beneficial
    
    Args:
        original_args: Original command line arguments to preserve during escalation
    """
    # Skip if already running as root
    if is_root():
        console.print("✓ Running with [success]root privileges[/success] - Enhanced fingerprinting capabilities enabled")
        return
    
    # Check configuration settings
    if not config.prompt_for_sudo and not config.auto_escalate:
        console.print("ℹ Running with [warning]user privileges[/warning] - sudo escalation disabled in config")
        return
    
    # Check if sudo is available
    if not check_sudo_availability():
        console.print("ℹ Running with [warning]user privileges[/warning] - sudo not available")
        console.print("  → TCP connect analysis (slower than SYN fingerprinting)")
        console.print("  → No OS detection capabilities")
        console.print("  → Limited timing optimizations")
        return
    
    # Auto-escalate if configured
    if config.auto_escalate:
        console.print("→ Auto-escalating to sudo (configured in config.yaml)")
        escalate = True
    else:
        # Offer escalation with table display
        console.display_privilege_escalation_prompt()
        
        # Get user choice
        try:
            import typer
            escalate = typer.confirm("Would you like to restart with sudo for enhanced analysis?", default=True)
        except (typer.Abort, KeyboardInterrupt):
            # User pressed Ctrl+C or cancelled
            console.info("Continuing with user privileges...")
            escalate = False
    
    if escalate:
        escalate_to_sudo(original_args)
    else:
        console.print("→ Continuing with user privileges...")


def escalate_to_sudo(original_args: Optional[List[str]] = None):
    """Escalate current process to sudo
    
    Args:
        original_args: Original command line arguments to preserve
    """
    # Build the correct sudo command based on how script was called
    script_path = os.path.abspath(sys.argv[0])
    
    if original_args is None:
        original_args = sys.argv[1:]  # Get arguments without script name
    
    # Build sudo command with explicit Python execution
    sudo_cmd = ['sudo', sys.executable, script_path] + original_args
    
    console.print(f"\n→ Restarting with sudo: [dim]{' '.join(sudo_cmd)}[/dim]")
    
    try:
        os.execvp('sudo', sudo_cmd)
    except Exception as e:
        console.print(f"✗ Failed to escalate privileges: {e}")
        console.print("→ Continuing with user privileges...")


def display_privilege_warnings():
    """Display warnings about running without privileges"""
    if not is_root():
        console.print("ℹ Running with [warning]user privileges[/warning]")
        console.print("  Some features may be limited:")
        console.print("  → TCP connect scan instead of SYN scan")
        console.print("  → No OS detection")
        console.print("  → Cannot update /etc/hosts")
        console.print("  → Slower port scanning")
        console.print()
        console.print("  For full capabilities, run with: [bold]sudo ipcrawler[/bold]")