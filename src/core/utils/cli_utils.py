"""CLI utilities for IPCrawler command processing"""

import sys
import re
from typing import List, Optional
from src.core.ui.console.base import console


def preprocess_args(argv: Optional[List[str]] = None):
    """Preprocess command line arguments to handle direct target execution
    
    This allows users to run 'ipcrawler target.com' instead of 'ipcrawler scan target.com'
    
    Args:
        argv: Command line arguments. If None, uses sys.argv.
    """
    if argv is None:
        argv = sys.argv
    
    # If no arguments, let typer handle it (will show help)
    if len(argv) == 1:
        return
        
    # If first argument is a known command, let typer handle it normally
    known_commands = ['scan', 'audit', 'report', '--help', '-h', '--version']
    if len(argv) > 1 and argv[1] in known_commands:
        return
        
    # If first argument starts with '-', it's a flag, let typer handle it
    if len(argv) > 1 and argv[1].startswith('-'):
        return
        
    # Otherwise, assume first argument is a target and prepend 'scan'
    if len(argv) > 1:
        potential_target = argv[1]
        
        # Basic validation - check if it looks like a target
        if looks_like_target(potential_target) and potential_target not in known_commands:
            # Insert 'scan' command before the target
            argv.insert(1, 'scan')
        elif not looks_like_target(potential_target):
            # Provide helpful error message for invalid targets
            console.error(f"Invalid target format: {potential_target}")
            console.info("Valid target formats:")
            console.info("  • Domain: hackerhub.me")
            console.info("  • IP: 192.168.1.1") 
            console.info("  • CIDR: 192.168.1.0/24")
            console.info("  • Hostname: localhost")
            console.info("\nFor help: ipcrawler --help")
            sys.exit(1)


def looks_like_target(value: str) -> bool:
    """Check if a value looks like a valid target
    
    Args:
        value: String to check
        
    Returns:
        True if value appears to be a valid target format
    """
    target_patterns = [
        r'^[\w\.-]+\.\w+$',          # domain.com
        r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',  # IP address
        r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$',  # CIDR
        r'^[\w\.-]+$'                # hostname
    ]
    
    return any(re.match(pattern, value) for pattern in target_patterns)


def validate_target_input(target: str) -> bool:
    """Validate target input from user
    
    Args:
        target: Target string to validate
        
    Returns:
        True if valid, exits with error if invalid
    """
    if not target or target.strip() == "":
        console.error("Target cannot be empty")
        console.info("Usage: ipcrawler <target>")
        console.info("Example: ipcrawler hackerhub.me")
        return False
    
    return True