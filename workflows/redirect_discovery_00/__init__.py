"""
Redirect Discovery Workflow (00)

Quick redirect and hostname discovery workflow that automatically updates /etc/hosts
when running with sudo privileges, optimizing subsequent scanning workflows.
"""

from .scanner import RedirectDiscoveryScanner

__all__ = ['RedirectDiscoveryScanner'] 