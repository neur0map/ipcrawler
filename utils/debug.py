"""Debug utilities for controlling debug output"""
from typing import Optional
import sys

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
    """Print only if debug mode is enabled"""
    if _debug_enabled:
        # Prefix debug messages with [DEBUG] if not already present
        message = ' '.join(str(arg) for arg in args)
        if not message.startswith('[DEBUG]'):
            print('[DEBUG]', message, **kwargs)
        else:
            print(message, **kwargs)


def debug_error(*args, **kwargs):
    """Print error debug messages to stderr if debug enabled"""
    if _debug_enabled:
        kwargs['file'] = sys.stderr
        debug_print(*args, **kwargs)


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