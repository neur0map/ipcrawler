"""Reporting Commands Module

Available commands for report generation and workspace management.
"""

from .generate_master_report import MasterReportCommand
from .workspace_list import WorkspaceListCommand
from .workspace_clean import WorkspaceCleanCommand

# Available reporting commands
AVAILABLE_COMMANDS = {
    'master-report': MasterReportCommand,
    'list-workspaces': WorkspaceListCommand, 
    'clean-workspaces': WorkspaceCleanCommand
}


def get_command(name: str):
    """Get command class by name
    
    Args:
        name: Command name
        
    Returns:
        Command class or None
    """
    return AVAILABLE_COMMANDS.get(name)


def list_commands():
    """Get list of available command names
    
    Returns:
        List of command names
    """
    return list(AVAILABLE_COMMANDS.keys())


__all__ = ['MasterReportCommand', 'WorkspaceListCommand', 'WorkspaceCleanCommand', 
           'get_command', 'list_commands']