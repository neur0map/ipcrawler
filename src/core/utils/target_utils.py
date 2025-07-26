"""Target resolution and validation utilities for IPCrawler"""

import asyncio
import socket
import ipaddress
from typing import Optional, Tuple
from src.core.ui.console.base import console


async def resolve_target(target: str) -> str:
    """Resolve target hostname to IP with visual feedback
    
    Args:
        target: Hostname, IP address, or CIDR notation
        
    Returns:
        The original target (IP/CIDR) or hostname with resolution feedback
    """
    # Check if target is already an IP address
    try:
        ipaddress.ip_address(target)
        console.display_target_resolution(target, target_type='ip')
        return target
    except ValueError:
        pass
    
    # Check if target is CIDR notation
    try:
        ipaddress.ip_network(target, strict=False)
        console.display_target_resolution(target, target_type='cidr')
        return target
    except ValueError:
        pass
    
    # It's a hostname, resolve it with visual feedback
    console.display_target_resolution(target, resolving=True)
    
    result = None
    resolved_ip = None
    
    try:
        # Use getaddrinfo for proper async DNS resolution
        result = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: socket.getaddrinfo(target, None, socket.AF_INET)
        )
        
        if result:
            resolved_ip = result[0][4][0]
            
    except Exception as e:
        console.error(f"DNS resolution error: {str(e)}")
        return target
    
    # Display result
    if result and resolved_ip:
        console.display_target_resolution(target, resolved_ip=resolved_ip)
        return target
    else:
        console.error(f"Failed to resolve {target}")
        return target


def validate_target_format(target: str) -> Tuple[bool, Optional[str]]:
    """Validate target format
    
    Args:
        target: Target string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    import re
    
    if not target or target.strip() == "":
        return False, "Target cannot be empty"
    
    # Target patterns for validation
    target_patterns = [
        (r'^[\w\.-]+\.\w+$', 'domain'),          # domain.com
        (r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', 'ip'),  # IP address
        (r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$', 'cidr'),  # CIDR
        (r'^[\w\.-]+$', 'hostname')                # hostname
    ]
    
    for pattern, target_type in target_patterns:
        if re.match(pattern, target):
            return True, None
    
    return False, f"Invalid target format: {target}"


def is_localhost_target(target: str) -> bool:
    """Check if target is localhost or similar
    
    Args:
        target: Target to check
        
    Returns:
        True if target is localhost-like
    """
    localhost_targets = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
    return target.lower() in localhost_targets