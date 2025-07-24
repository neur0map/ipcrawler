"""Jinja2 Template System for IPCrawler Reports

Provides centralized template management with inheritance, custom filters,
and theme support for generating professional reports.
"""

from .engine import TemplateEngine, get_template_engine

__all__ = ['TemplateEngine', 'get_template_engine']