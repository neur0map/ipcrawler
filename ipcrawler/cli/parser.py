"""
CLI Argument Parser for IPCrawler
Handles command-line argument parsing, flag-style commands, and argument validation.
"""

import argparse
import sys
from types import SimpleNamespace
from typing import Any

from ..core import ConfigManager


class ArgumentParser:
    """Handles CLI argument parsing and command routing."""
    
    TARGET_HELP = 'Target (IP, domain, or URL)'
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create command-line argument parser."""
        parser = argparse.ArgumentParser(
            description="ipcrawler - Security Tool Orchestration Framework",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False  # We'll handle help manually
        )
        
        # Add global debug flag
        parser.add_argument(
            '-debug', '--debug',
            action='store_true',
            help='Enable debug mode with Sentry error tracking (requires .env with SENTRY_DSN)'
        )
        
        # Add version flag (handled manually, but keep for compatibility)
        parser.add_argument(
            '--version',
            action='store_true',
            help='Show version information'
        )
        
        # Add help flag (handled manually, but keep for compatibility)
        parser.add_argument(
            '-h', '--help',
            action='store_true',
            help='Show this help message'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Run command
        run_parser = subparsers.add_parser('run', help='Run a specific template')
        run_parser.add_argument('template', help='Template name (category/template)')
        run_parser.add_argument('target', help=self.TARGET_HELP)
        
        # Scan-folder command
        scan_parser = subparsers.add_parser('scan-folder', help='Run all templates in a folder')
        scan_parser.add_argument('folder', help='Template folder path')
        scan_parser.add_argument('target', help=self.TARGET_HELP)
        
        # Scan-all command
        scan_all_parser = subparsers.add_parser('scan-all', help='Run all templates')
        scan_all_parser.add_argument('target', help=self.TARGET_HELP)
        
        # List command
        list_parser = subparsers.add_parser('list', help='List available templates')
        list_parser.add_argument('--category', help='Filter by category')
        
        # Results command
        results_parser = subparsers.add_parser('results', help='Show results for a target')
        results_parser.add_argument('target', help='Target to show results for')
        
        # Export command
        export_parser = subparsers.add_parser('export', help='Export results')
        export_parser.add_argument('target', help='Target to export results for')
        export_parser.add_argument('--format', choices=['txt', 'json', 'jsonl', 'md'], default='txt')
        export_parser.add_argument('--output', help='Output file path')
        
        # Config command
        subparsers.add_parser('config', help='Show configuration')
        
        # Schema command
        subparsers.add_parser('schema', help='Show template JSON schema')
        
        # Validate command
        validate_parser = subparsers.add_parser('validate', help='Validate templates')
        validate_parser.add_argument('--category', help='Validate specific category')
        
        # Add flags for category shortcuts
        templates_config = self.config_manager.get_templates_config()
        if templates_config and "categories" in templates_config:
            for flag, folder in templates_config["categories"].items():
                if flag in ['wiz', 'wizard']:
                    # Wizard commands don't need a target
                    flag_parser = subparsers.add_parser(f'-{flag}', help='Launch template creation wizard')
                else:
                    # Regular category shortcuts need a target
                    flag_parser = subparsers.add_parser(f'-{flag}', help=f'Run all templates in {folder}')
                    flag_parser.add_argument('target', help=self.TARGET_HELP)
        
        return parser
    
    def _create_flag_args(self, command: str, target: str = None, debug_flag: bool = False) -> SimpleNamespace:
        """Create args object for flag-style commands."""
        return SimpleNamespace(
            command=command,
            target=target,
            debug=debug_flag,
            template=None,
            folder=None,
            category=None,
            format=None,
            output=None
        )
    
    def parse_arguments(self, status_dispatcher) -> Any:
        """Parse command line arguments, handling flag-style commands."""
        # Handle version and help first (before any other parsing)
        if '--version' in sys.argv:
            status_dispatcher.display_version(
                self.config_manager.config.application.version,
                self.config_manager.config.application.name
            )
            sys.exit(0)
        
        if '-h' in sys.argv or '--help' in sys.argv:
            status_dispatcher.display_help(self.config_manager.config.application.name)
            sys.exit(0)
        
        # Check for debug flag first (can appear anywhere)
        debug_flag = '-debug' in sys.argv or '--debug' in sys.argv
        
        # Handle flag-style commands (category shortcuts and wizard)
        if len(sys.argv) >= 2:
            for i, arg in enumerate(sys.argv[1:], 1):
                if arg.startswith('-') and arg not in ['-debug', '--debug']:
                    flag = arg[1:]  # Remove the '-' prefix
                    # Check if this flag maps to a template category
                    templates_config = self.config_manager.get_templates_config()
                    if templates_config and "categories" in templates_config and flag in templates_config["categories"]:
                        # Handle wizard commands (no target required)
                        if flag in ['wiz', 'wizard']:
                            return self._create_flag_args(arg, None, debug_flag)
                        # Handle regular category shortcuts (target required)
                        elif len(sys.argv) >= 3:
                            # Find the target (next non-debug argument)
                            for j in range(i + 1, len(sys.argv)):
                                if sys.argv[j] not in ['-debug', '--debug']:
                                    return self._create_flag_args(arg, sys.argv[j], debug_flag)
        
        # Normal parsing for other commands
        parser = self.create_parser()
        return parser.parse_args()