"""Default theme for IPCrawler console output

Defines colors, styles, and formatting for consistent UI.
"""

from typing import Dict, Any
from rich.theme import Theme
from rich.style import Style


# Color palette
COLORS = {
    'primary': '#00ff00',      # Green
    'secondary': '#007acc',    # Blue
    'success': '#00ff00',      # Green
    'warning': '#ffaa00',      # Orange
    'error': '#ff0000',        # Red
    'info': '#00aaff',         # Light Blue
    'critical': '#ff0000',     # Red
    'debug': '#888888',        # Gray
    'muted': '#666666',        # Dark Gray
    'highlight': '#ffff00',    # Yellow
    'background': '#000000',   # Black
    'foreground': '#ffffff',   # White
}


# Severity color mapping
SEVERITY_COLORS = {
    'critical': COLORS['critical'],
    'high': COLORS['error'],
    'medium': COLORS['warning'],
    'low': COLORS['info'],
    'info': COLORS['muted']
}


# Status color mapping
STATUS_COLORS = {
    'success': COLORS['success'],
    'running': COLORS['info'],
    'pending': COLORS['muted'],
    'failed': COLORS['error'],
    'warning': COLORS['warning']
}


# Rich theme definition
IPCRAWLER_THEME = Theme({
    # Base styles
    'default': Style(color=COLORS['foreground']),
    'primary': Style(color=COLORS['primary'], bold=True),
    'secondary': Style(color=COLORS['secondary']),
    'muted': Style(color=COLORS['muted']),
    
    # Status styles
    'success': Style(color=COLORS['success']),
    'error': Style(color=COLORS['error'], bold=True),
    'warning': Style(color=COLORS['warning']),
    'info': Style(color=COLORS['info']),
    'critical': Style(color=COLORS['critical'], bold=True, blink=True),
    'debug': Style(color=COLORS['debug'], dim=True),
    
    # Severity styles
    'severity.critical': Style(color=COLORS['critical'], bold=True),
    'severity.high': Style(color=COLORS['error']),
    'severity.medium': Style(color=COLORS['warning']),
    'severity.low': Style(color=COLORS['info']),
    'severity.info': Style(color=COLORS['muted']),
    
    # Component styles
    'header': Style(color=COLORS['primary'], bold=True),
    'subheader': Style(color=COLORS['secondary'], bold=True),
    'label': Style(color=COLORS['secondary']),
    'value': Style(color=COLORS['primary']),
    'highlight': Style(color=COLORS['highlight'], bold=True),
    
    # Table styles
    'table.header': Style(color=COLORS['primary'], bold=True),
    'table.row.odd': Style(color=COLORS['foreground']),
    'table.row.even': Style(color=COLORS['foreground'], dim=True),
    'table.border': Style(color=COLORS['muted']),
    
    # Progress styles
    'progress.percentage': Style(color=COLORS['primary']),
    'progress.remaining': Style(color=COLORS['muted']),
    'progress.spinner': Style(color=COLORS['info']),
    
    # Panel styles
    'panel.border': Style(color=COLORS['primary']),
    'panel.title': Style(color=COLORS['primary'], bold=True),
    
    # Code styles
    'code': Style(color=COLORS['info'], bgcolor='#1a1a1a'),
    'code.keyword': Style(color=COLORS['warning'], bold=True),
    'code.string': Style(color=COLORS['success']),
    'code.comment': Style(color=COLORS['muted'], italic=True),
    
    # Link styles
    'link': Style(color=COLORS['info'], underline=True),
    
    # Workflow styles
    'workflow.nmap': Style(color='#ff6b6b'),
    'workflow.http': Style(color='#4ecdc4'),
    'workflow.spider': Style(color='#ffe66d'),
    'workflow.smartlist': Style(color='#a8e6cf'),
    
    # Special styles
    'bold': Style(bold=True),
    'italic': Style(italic=True),
    'underline': Style(underline=True),
    'strike': Style(strike=True),
    'blink': Style(blink=True),
})


# Icons and symbols
ICONS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'critical': '🚨',
    'debug': '🐛',
    'running': '🔄',
    'pending': '⏳',
    'completed': '✓',
    'failed': '✗',
    'arrow_right': '→',
    'arrow_left': '←',
    'arrow_up': '↑',
    'arrow_down': '↓',
    'bullet': '•',
    'star': '★',
    'lock': '🔒',
    'unlock': '🔓',
    'folder': '📁',
    'file': '📄',
    'search': '🔍',
    'target': '🎯',
    'shield': '🛡️',
    'bug': '🐛',
    'fire': '🔥',
    'rocket': '🚀',
}


# Formatting templates
FORMATS = {
    'header': "[{style}]{icon} {text}[/{style}]",
    'status': "[{style}]{icon} {text}[/{style}]",
    'finding': "[{style}]{severity}: {text}[/{style}]",
    'url': "[link]{text}[/link]",
    'code': "[code]{text}[/code]",
    'label_value': "[label]{label}:[/label] [value]{value}[/value]",
    'progress': "[progress.percentage]{percentage}%[/progress.percentage] [progress.remaining]({remaining})[/progress.remaining]",
}


def get_severity_style(severity: str) -> str:
    """Get style name for severity level"""
    return f"severity.{severity.lower()}"


def get_severity_icon(severity: str) -> str:
    """Get icon for severity level"""
    icons = {
        'critical': ICONS['critical'],
        'high': ICONS['error'],
        'medium': ICONS['warning'],
        'low': ICONS['info'],
        'info': ICONS['info']
    }
    return icons.get(severity.lower(), ICONS['info'])


def get_status_style(status: str) -> str:
    """Get style name for status"""
    return status.lower() if status.lower() in ['success', 'error', 'warning', 'info'] else 'default'


def get_status_icon(status: str) -> str:
    """Get icon for status"""
    return ICONS.get(status.lower(), ICONS['info'])


def format_header(text: str, icon: str = None, style: str = 'header') -> str:
    """Format a header with optional icon"""
    if not icon:
        icon = ICONS['arrow_right']
    return FORMATS['header'].format(style=style, icon=icon, text=text)


def format_status(text: str, status: str) -> str:
    """Format a status message"""
    style = get_status_style(status)
    icon = get_status_icon(status)
    return FORMATS['status'].format(style=style, icon=icon, text=text)


def format_finding(text: str, severity: str) -> str:
    """Format a finding with severity"""
    style = get_severity_style(severity)
    return FORMATS['finding'].format(style=style, severity=severity.upper(), text=text)


def format_label_value(label: str, value: Any) -> str:
    """Format a label-value pair"""
    return FORMATS['label_value'].format(label=label, value=str(value))