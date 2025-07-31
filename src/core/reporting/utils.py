"""Shared utilities for the reporting system"""

from datetime import datetime
from typing import Any


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for datetime and other objects
    
    Args:
        obj: Object to serialize
        
    Returns:
        String representation of the object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    return str(obj)