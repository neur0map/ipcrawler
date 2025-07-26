"""Debug utilities for controlling debug output"""

import os
from ...ui.console import console

# Global debug state
_debug_enabled = False


def set_debug(enabled: bool) -> None:
    """Set global debug state"""
    global _debug_enabled
    _debug_enabled = enabled


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled"""
    return _debug_enabled or os.getenv('DEBUG', '').lower() in ('1', 'true', 'yes')


def debug_print(*args, **kwargs) -> None:
    """Print only if debug mode is enabled"""
    if not is_debug_enabled():
        return
        
    # Join all arguments into a message
    message = ' '.join(str(arg) for arg in args)
    
    # Check for level specification in kwargs
    level = kwargs.pop('level', 'DEBUG').upper()
    
    # Route to appropriate console method based on level
    if level == 'ERROR':
        console.error(f"[DEBUG] {message}", **kwargs)
    elif level == 'WARNING' or level == 'WARN':
        console.warning(f"[DEBUG] {message}", **kwargs)
    elif level == 'INFO':
        console.info(f"[DEBUG] {message}", **kwargs)
    elif level == 'SUCCESS':
        console.success(f"[DEBUG] {message}", **kwargs)
    else:
        console.debug(message, **kwargs)


def debug_error(*args, **kwargs) -> None:
    """Print error debug messages to stderr if debug enabled"""
    if not is_debug_enabled():
        return
        
    # Join all arguments into a message
    message = ' '.join(str(arg) for arg in args)
    console.error(f"[DEBUG ERROR] {message}", **kwargs)


class DebugContext:
    """Context manager for temporary debug mode"""
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.old_state = None
    
    def __enter__(self):
        self.old_state = _debug_enabled
        set_debug(self.enabled)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        set_debug(self.old_state)


# Legacy compatibility exports
__all__ = [
    'set_debug',
    'is_debug_enabled', 
    'debug_print',
    'debug_error',
    'DebugContext'
]