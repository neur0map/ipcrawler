"""Result management utilities"""

from .formatters import (
    DateTimeJSONEncoder,
    BaseFormatter, 
    JSONFormatter,
    TextFormatter,
)
from .manager import ResultManager

# Legacy compatibility exports
result_manager_compat = ResultManager()
result_manager = result_manager_compat

__all__ = [
    'DateTimeJSONEncoder',
    'BaseFormatter', 
    'JSONFormatter',
    'TextFormatter',
    'ResultManager',
    'result_manager',
    'result_manager_compat'
]