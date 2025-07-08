"""
ipcrawler - Security Tool Orchestration Framework
"""

from .cli.main import main

def _get_version():
    """Get version from config.toml"""
    try:
        from .core.config import ConfigManager
        config_manager = ConfigManager()
        return config_manager.config.application.version
    except Exception:
        return "2.0.0"  # Fallback version

__version__ = _get_version()
__all__ = ['main']