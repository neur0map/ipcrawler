"""Target sanitization utilities for IPCrawler"""

import re
from typing import Optional


def sanitize_target(target: str, replacement: str = '_') -> str:
    """Sanitize target name for safe filesystem usage
    
    Args:
        target: Target hostname, IP, or identifier to sanitize
        replacement: Character to replace unsafe characters with
        
    Returns:
        Sanitized target string safe for filenames and paths
    """
    if not target:
        return 'unknown'
    
    # Preserve dots for IP addresses, only replace truly problematic characters
    safe_target = re.sub(r'[<>:"/\\|?*]', replacement, target)
    
    # Replace remaining problematic characters for filesystem safety
    safe_target = safe_target.replace(':', replacement)
    safe_target = safe_target.replace('/', replacement)
    
    # Collapse multiple replacement characters
    safe_target = re.sub(f'{re.escape(replacement)}+', replacement, safe_target)
    
    # Remove leading/trailing replacement characters
    safe_target = safe_target.strip(replacement)
    
    return safe_target or 'unknown'


def generate_safe_filename(target: str, workflow: str = 'scan', extension: str = 'txt') -> str:
    """Generate a safe filename for reports
    
    Args:
        target: Target hostname or IP
        workflow: Workflow name (e.g., 'nmap', 'http')
        extension: File extension without dot
        
    Returns:
        Safe filename string
    """
    safe_target = sanitize_target(target)
    safe_workflow = sanitize_target(workflow)
    
    if not extension.startswith('.'):
        extension = f'.{extension}'
    
    return f"{safe_workflow}_report_{safe_target}{extension}"


def create_workspace_path(target: str, base_path: str = "workspaces") -> str:
    """Create workspace directory path for target
    
    Args:
        target: Target hostname or IP
        base_path: Base workspace directory
        
    Returns:
        Workspace path string
    """
    safe_target = sanitize_target(target)
    return f"{base_path}/{safe_target}"