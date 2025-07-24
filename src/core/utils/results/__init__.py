"""Result management utilities

Provides compatibility with legacy utils/results.py while integrating
with the centralized reporting system.
"""

from .compatibility import (
    DateTimeJSONEncoder,
    BaseFormatter,
    JSONFormatter,
    TextFormatter,
    HTMLFormatter,
    ResultManager,
    result_manager_compat
)

# Legacy compatibility exports
result_manager = result_manager_compat

__all__ = [
    'DateTimeJSONEncoder',
    'BaseFormatter', 
    'JSONFormatter',
    'TextFormatter',
    'HTMLFormatter',
    'ResultManager',
    'result_manager',
    'result_manager_compat'
]