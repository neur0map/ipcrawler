"""Cache management utilities for IPCrawler"""

import shutil
from pathlib import Path
from typing import Optional


def clean_project_cache(project_root: Optional[Path] = None):
    """Remove all __pycache__ directories in the project
    
    Args:
        project_root: Root directory of the project. If None, uses current file's parent.
    """
    try:
        if project_root is None:
            # Go up from utils -> core -> src -> project root
            project_root = Path(__file__).parent.parent.parent.parent
        
        for cache_dir in project_root.rglob('__pycache__'):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir, ignore_errors=True)
    except Exception:
        pass  # Fail silently if cache cleanup fails


def ensure_no_bytecode():
    """Ensure Python doesn't write bytecode files"""
    import os
    import sys
    
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    sys.dont_write_bytecode = True