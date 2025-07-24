"""Template Engine for IPCrawler Reports

Centralized Jinja2 template management with custom filters, inheritance,
and theme support.
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError

from src.core.ui.console.base import console
from src.core.ui.themes.default import COLORS, ICONS


class TemplateEngine:
    """Advanced Jinja2 template engine with IPCrawler-specific features"""
    
    def __init__(self, template_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize template engine
        
        Args:
            template_dir: Directory containing templates (defaults to src/core/reporting/templates)
            theme: Theme name to use for styling
        """
        if template_dir is None:
            template_dir = Path(__file__).parent
        
        self.template_dir = Path(template_dir)
        self.theme = theme
        self._setup_environment()
        self._register_custom_filters()
        
        console.debug(f"Template engine initialized with theme '{theme}' at {self.template_dir}")
    
    def _setup_environment(self):
        """Setup Jinja2 environment with security and features"""
        try:
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
                enable_async=False
            )
            
            # Add global variables
            self.env.globals.update({
                'colors': COLORS,
                'icons': ICONS,
                'theme': self.theme,
                'now': datetime.now(),
                'version': '1.2.0'
            })
            
        except Exception as e:
            console.error(f"Failed to setup template environment: {e}")
            raise
    
    def _register_custom_filters(self):
        """Register custom Jinja2 filters for IPCrawler"""
        
        def format_datetime(value: Union[datetime, str], fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
            """Format datetime objects with custom format"""
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    return str(value)
            elif not isinstance(value, datetime):
                return str(value)
            return value.strftime(fmt)
        
        def severity_class(severity: str) -> str:
            """Get CSS class for severity level"""
            severity_map = {
                'critical': 'severity-critical',
                'high': 'severity-high', 
                'medium': 'severity-medium',
                'low': 'severity-low',
                'info': 'severity-info'
            }
            return severity_map.get(str(severity).lower(), 'severity-info')
        
        def format_bytes(bytes_value: Union[int, str]) -> str:
            """Format bytes into human readable format"""
            try:
                bytes_value = int(bytes_value)
            except (ValueError, TypeError):
                return str(bytes_value)
            
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} PB"
        
        def truncate_smart(text: str, length: int = 100, suffix: str = '...') -> str:
            """Smart text truncation at word boundaries"""
            if not text or len(text) <= length:
                return text
            
            # Find last space within length limit
            truncated = text[:length - len(suffix)]
            last_space = truncated.rfind(' ')
            
            if last_space > length * 0.7:  # Only break at word if not too short
                truncated = truncated[:last_space]
            
            return truncated + suffix
        
        def highlight_urls(text: str) -> str:
            """Highlight URLs in text for HTML output"""
            url_pattern = re.compile(r'https?://[^\s<>"]+')
            return url_pattern.sub(r'<a href="\\g<0>" class="url-link">\\g<0></a>', text)
        
        def port_state_class(state: str) -> str:
            """Get CSS class for port state"""
            state_map = {
                'open': 'port-open',
                'closed': 'port-closed',
                'filtered': 'port-filtered',
                'unfiltered': 'port-unfiltered'
            }
            return state_map.get(str(state).lower(), 'port-unknown')
        
        def confidence_badge(confidence: str) -> str:
            """Get confidence level badge class"""
            confidence_map = {
                'high': 'confidence-high',
                'medium': 'confidence-medium',
                'low': 'confidence-low'
            }
            return confidence_map.get(str(confidence).lower(), 'confidence-unknown')
        
        def json_pretty(value: Any, indent: int = 2) -> str:
            """Pretty print JSON with proper formatting"""
            try:
                return json.dumps(value, indent=indent, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                return str(value)
        
        def list_unique(items: List[Any]) -> List[Any]:
            """Get unique items from list while preserving order"""
            seen = set()
            result = []
            for item in items:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result
        
        def dict_sort(dict_value: Dict[Any, Any], by: str = 'key', reverse: bool = False) -> List[tuple]:
            """Sort dictionary by key or value"""
            if by == 'value':
                return sorted(dict_value.items(), key=lambda x: x[1], reverse=reverse)
            return sorted(dict_value.items(), key=lambda x: x[0], reverse=reverse)
        
        # Register all filters
        self.env.filters['format_datetime'] = format_datetime
        self.env.filters['severity_class'] = severity_class
        self.env.filters['format_bytes'] = format_bytes
        self.env.filters['truncate_smart'] = truncate_smart
        self.env.filters['highlight_urls'] = highlight_urls
        self.env.filters['port_state_class'] = port_state_class
        self.env.filters['confidence_badge'] = confidence_badge
        self.env.filters['json_pretty'] = json_pretty
        self.env.filters['list_unique'] = list_unique
        self.env.filters['dict_sort'] = dict_sort
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with context data
        
        Args:
            template_name: Name of template to render (e.g., 'base/layout.html.j2')
            context: Data to pass to template
            
        Returns:
            Rendered template content
            
        Raises:
            TemplateNotFound: If template doesn't exist
            TemplateSyntaxError: If template has syntax errors
        """
        try:
            template = self.env.get_template(template_name)
            
            # Add common context
            full_context = {
                'metadata': {
                    'generator': 'IPCrawler Template Engine',
                    'timestamp': datetime.now(),
                    'template': template_name,
                    'theme': self.theme,
                    'version': '1.2.0'
                },
                'theme': {
                    'colors': COLORS,
                    'icons': ICONS,
                    'name': self.theme
                },
                **context
            }
            
            rendered = template.render(**full_context)
            console.debug(f"Successfully rendered template '{template_name}'")
            return rendered
            
        except TemplateNotFound as e:
            console.error(f"Template not found: {template_name}")
            raise
        except TemplateSyntaxError as e:
            console.error(f"Template syntax error in '{template_name}': {e}")
            raise
        except Exception as e:
            console.error(f"Failed to render template '{template_name}': {e}")
            raise
    
    def get_template(self, template_name: str) -> Template:
        """Get template object for advanced usage
        
        Args:
            template_name: Name of template to get
            
        Returns:
            Jinja2 Template object
        """
        return self.env.get_template(template_name)
    
    def list_templates(self, pattern: str = '*.j2') -> List[str]:
        """List available templates matching pattern
        
        Args:
            pattern: Glob pattern to match templates
            
        Returns:
            List of template names
        """
        try:
            templates = []
            for template_file in self.template_dir.rglob(pattern):
                rel_path = template_file.relative_to(self.template_dir)
                templates.append(str(rel_path))
            return sorted(templates)
        except Exception as e:
            console.error(f"Failed to list templates: {e}")
            return []
    
    def validate_template(self, template_name: str) -> tuple[bool, Optional[str]]:
        """Validate template syntax
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            template = self.env.get_template(template_name)
            # Try to render with minimal context to check for syntax errors
            template.render({})
            return True, None
        except TemplateSyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def set_theme(self, theme: str):
        """Change theme and update globals
        
        Args:
            theme: New theme name
        """
        self.theme = theme
        self.env.globals['theme'] = theme
        console.debug(f"Theme changed to '{theme}'")
    
    def add_filter(self, name: str, func: callable):
        """Add custom filter to environment
        
        Args:
            name: Filter name
            func: Filter function
        """
        self.env.filters[name] = func
        console.debug(f"Added custom filter '{name}'")
    
    def add_global(self, name: str, value: Any):
        """Add global variable to environment
        
        Args:
            name: Variable name
            value: Variable value
        """
        self.env.globals[name] = value
        console.debug(f"Added global variable '{name}'")


# Global template engine instance
_template_engine: Optional[TemplateEngine] = None


def get_template_engine(theme: str = 'default') -> TemplateEngine:
    """Get global template engine instance
    
    Args:
        theme: Theme to use (only used for first initialization)
        
    Returns:
        TemplateEngine instance
    """
    global _template_engine
    if _template_engine is None:
        _template_engine = TemplateEngine(theme=theme)
    return _template_engine