"""Core utilities for IPCrawler

Centralized utility functions and classes used across workflows.
"""

# Re-export result management for backward compatibility
from .results import result_manager, DateTimeJSONEncoder, ResultManager

# Re-export debugging utilities for backward compatibility  
from .debugging import debug_print, set_debug, is_debug_enabled, debug_error, DebugContext

__all__ = [
    'result_manager',
    'DateTimeJSONEncoder', 
    'ResultManager',
    'debug_print',
    'set_debug', 
    'is_debug_enabled',
    'debug_error',
    'DebugContext'
]