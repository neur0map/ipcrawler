"""Default theme for IPCrawler console output - Modern Monochrome Edition"""

from rich.theme import Theme
from rich.style import Style
from typing import Optional

# Modern Monochrome Color Palette
COLORS = {
    'primary': '#f5f5f5',      # Off-white
    'secondary': '#d4d4d4',    # Light gray
    'success': '#ffffff',      # Pure white
    'warning': '#b3b3b3',      # Medium-light gray
    'error': '#ff0000',        # Bright red (critical visibility)
    'info': '#c0c0c0',         # Silver
    'critical': '#606060',     # Dark gray
    'debug': '#909090',        # Light medium gray
    'muted': '#707070',        # Darker gray
    'highlight': '#ffffff',    # Pure white (for emphasis)
    'background': '#000000',   # Pure black
    'foreground': '#e0e0e0',   # Very light gray
    'accent': '#a0a0a0',       # Medium-light gray accent
    'subtle': '#4a4a4a',       # Dark gray for subtle elements
}


# Severity color mapping - monochrome gradation with bright red for critical
SEVERITY_COLORS = {
    'critical': '#ff0000',         # Bright red for critical items
    'high': COLORS['primary'],
    'medium': COLORS['accent'],
    'low': COLORS['muted'],
    'info': COLORS['subtle']
}


# Status color mapping - using grayscale progression
STATUS_COLORS = {
    'success': COLORS['success'],
    'running': COLORS['accent'],
    'pending': COLORS['muted'],
    'failed': COLORS['subtle'],
    'warning': COLORS['warning']
}


# Rich theme definition - Modern Monochrome
IPCRAWLER_THEME = Theme({
    # Base styles - refined monochrome
    'default': Style(color=COLORS['foreground']),
    'primary': Style(color=COLORS['primary'], bold=True),
    'secondary': Style(color=COLORS['secondary']),
    'muted': Style(color=COLORS['muted']),
    
    # Status styles - elegant grayscale progression
    'success': Style(color=COLORS['success'], bold=True),
    'error': Style(color=COLORS['error'], bold=True, italic=True),
    'warning': Style(color=COLORS['warning'], bold=True),
    'info': Style(color=COLORS['info']),
    'critical': Style(color='#ff0000', bold=True, underline=True),
    'debug': Style(color=COLORS['debug'], dim=True, italic=True),
    
    # Bold status variants for workflow display
    'bold_success': Style(color=COLORS['success'], bold=True),
    'bold_error': Style(color=COLORS['error'], bold=True, italic=True),
    'bold_warning': Style(color=COLORS['warning'], bold=True),
    'bold_info': Style(color=COLORS['info'], bold=True),
    'bold_muted': Style(color=COLORS['muted'], bold=True),
    
    # Severity styles - monochrome intensity mapping with bright red for critical
    'severity.critical': Style(color='#ff0000', bold=True, underline=True),
    'severity.high': Style(color=COLORS['primary'], bold=True),
    'severity.medium': Style(color=COLORS['accent']),
    'severity.low': Style(color=COLORS['muted']),
    'severity.info': Style(color=COLORS['subtle'], dim=True),
    
    # Component styles - modern hierarchy
    'header': Style(color=COLORS['primary'], bold=True, underline=True),
    'subheader': Style(color=COLORS['secondary'], bold=True),
    'label': Style(color=COLORS['accent'], italic=True),
    'value': Style(color=COLORS['primary']),
    'highlight': Style(color=COLORS['highlight'], bold=True, reverse=True),
    
    # Table styles - subtle monochrome grid
    'table.header': Style(color=COLORS['primary'], bold=True, underline=True),
    'table.row.odd': Style(color=COLORS['foreground']),
    'table.row.even': Style(color=COLORS['secondary'], dim=True),
    'table.border': Style(color=COLORS['subtle']),
    
    # Progress styles - refined indicators
    'progress.percentage': Style(color=COLORS['primary'], bold=True),
    'progress.remaining': Style(color=COLORS['muted'], italic=True),
    'progress.spinner': Style(color=COLORS['accent']),
    
    # Panel styles - clean borders
    'panel.border': Style(color=COLORS['accent']),
    'panel.title': Style(color=COLORS['primary'], bold=True),
    
    # Code styles - monochrome syntax
    'code': Style(color=COLORS['info'], bgcolor='#1a1a1a'),
    'code.keyword': Style(color=COLORS['primary'], bold=True),
    'code.string': Style(color=COLORS['secondary'], italic=True),
    'code.comment': Style(color=COLORS['muted'], italic=True, dim=True),
    
    # Link styles - understated elegance
    'link': Style(color=COLORS['accent'], underline=True),
    
    # Workflow styles - grayscale differentiation
    'workflow.nmap': Style(color=COLORS['primary'], bold=True),
    'workflow.http': Style(color=COLORS['secondary']),
    'workflow.spider': Style(color=COLORS['accent']),
    'workflow.smartlist': Style(color=COLORS['foreground']),
    
    # Special styles - refined emphasis
    'bold': Style(bold=True),
    'italic': Style(italic=True),
    'underline': Style(underline=True),
    'strike': Style(strike=True),
    'blink': Style(blink=False),  # Disabled for modern aesthetic
    'dim': Style(dim=True),
    'reverse': Style(reverse=True),
})


# Modern minimalist icons - ASCII compatible
ICONS = {
    'success': '✓',
    'error': '✗',
    'warning': '!',
    'info': 'i',
    'critical': '‼',
    'debug': '?',
    'running': '○',
    'pending': '◦',
    'completed': '●',
    'failed': '◯',
    'arrow_right': '→',
    'arrow_left': '←',
    'arrow_up': '↑',
    'arrow_down': '↓',
    'bullet': '•',
    'star': '★',
    'lock': '■',
    'unlock': '□',
    'folder': '▶',
    'file': '▪',
    'search': '◉',
    'target': '◎',
    'shield': '▣',
    'bug': '△',
    'fire': '▲',
    'rocket': '▸',
    'checkmark': '✓',
    'cross': '✗',
    'dash': '−',
    'plus': '+',
    'equals': '=',
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
    return status.lower()


def get_status_icon(status: str) -> str:
    """Get icon for status"""
    return ICONS.get(status.lower(), ICONS['bullet'])


def format_header(text: str, icon: str = None, style: str = 'header') -> str:
    """Format a header with optional icon"""
    if icon is None:
        icon = ICONS['arrow_right']
    return FORMATS['header'].format(style=style, icon=icon, text=text)


def format_status(status: str, text: str) -> str:
    """Format a status message"""
    style = get_status_style(status)
    icon = get_status_icon(status)
    return FORMATS['status'].format(style=style, icon=icon, text=text)


def format_finding(severity: str, text: str) -> str:
    """Format a finding with severity"""
    style = get_severity_style(severity)
    return FORMATS['finding'].format(style=style, severity=severity.upper(), text=text)


def format_label_value(label: str, value: any) -> str:
    """Format a label-value pair"""
    return FORMATS['label_value'].format(label=label, value=str(value))