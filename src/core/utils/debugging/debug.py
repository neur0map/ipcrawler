"""Debug utilities for controlling debug output

Provides backward compatibility with legacy debug utilities while
integrating with the centralized console system.
"""

from typing import Optional
import sys

from ...ui.console.base import console

# Global debug state
_debug_enabled = False


def set_debug(enabled: bool):
    """Set global debug state"""
    global _debug_enabled
    _debug_enabled = enabled


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled"""
    return _debug_enabled


def debug_print(*args, **kwargs):
    """Print only if debug mode is enabled
    
    This function provides backward compatibility with legacy debug_print usage
    while redirecting to the centralized console system.
    """
    if _debug_enabled:
        # Join all arguments into a message
        message = ' '.join(str(arg) for arg in args)
        
        # Check for level specification in kwargs
        level = kwargs.pop('level', 'DEBUG').upper()
        
        # Route to appropriate console method based on level
        if level == 'ERROR':
            console.error(message)
        elif level == 'WARNING' or level == 'WARN':
            console.warning(message)
        elif level == 'INFO':
            console.info(message)
        elif level == 'SUCCESS':
            console.success(message)
        else:
            console.debug(message)


def debug_error(*args, **kwargs):
    """Print error debug messages to stderr if debug enabled"""
    if _debug_enabled:
        # Join all arguments into a message
        message = ' '.join(str(arg) for arg in args)
        console.error(message)


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