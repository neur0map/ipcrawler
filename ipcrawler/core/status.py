"""
Status display and console output management.
"""

import sys
from typing import Optional, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime
from ..models.result import ExecutionResult, ScanResult

if TYPE_CHECKING:
    from ..ui.rich_status import RichStatusDispatcher


def create_status_dispatcher(config: Dict[str, Any], silent: bool = False) -> Union['StatusDispatcher', 'RichStatusDispatcher']:
    """Factory function to create appropriate status dispatcher."""
    try:
        # Try to import and use Rich TUI if enabled
        if config.get("enable_rich_ui", True):
            from ..ui.rich_status import RichStatusDispatcher
            return RichStatusDispatcher(config, silent)
    except ImportError:
        # Fall back to basic status dispatcher if Rich is not available
        pass
    
    # Use basic status dispatcher
    return StatusDispatcher(silent)


class StatusDispatcher:
    """Manages console output and status display."""
    
    def __init__(self, silent: bool = False):
        self.silent = silent
        self.start_time = None
        self.total_templates = 0
        self.completed_templates = 0
    
    def start_scan(self, target: str, template_count: int, folder: Optional[str] = None) -> None:
        """Start a new scan session."""
        self.start_time = datetime.now()
        self.total_templates = template_count
        self.completed_templates = 0
        
        if not self.silent:
            if folder:
                print(f"Running template flag '{folder}' (folder: {folder}) on target: {target}")
            print(f"Running {template_count} scans concurrently on target: {target}")
    
    def template_starting(self, tool: str, template_path: str, target: str) -> None:
        """Display template starting message."""
        if not self.silent:
            print(f"[→] {tool} ({template_path}) on {target}...")
    
    def template_completed(self, result: ExecutionResult) -> None:
        """Display template completion message."""
        if not self.silent:
            status = "✓" if result.success else "✗"
            if result.success:
                print(f"[{status}] {result.tool} ({result.template_name}) completed successfully")
            else:
                print(f"[{status}] {result.tool} ({result.template_name}) failed (exit code {result.return_code})")
    
    def update_progress(self, result: ExecutionResult) -> None:
        """Update progress with a completed result."""
        self.completed_templates += 1
        self.template_completed(result)
    
    def finish_scan(self, scan_result: ScanResult) -> None:
        """Finish scan and display summary."""
        if not self.silent:
            print()
            print("--- Scan Summary ---")
            print(f"Total scans: {scan_result.total_templates}")
            print(f"Successful: {scan_result.successful_templates}")
            print(f"Failed: {scan_result.failed_templates}")
    
    def display_results(self, results: list) -> None:
        """Display scan results."""
        if not self.silent:
            print(f"\\nFound {len(results)} results:")
            for result in results:
                status = "✓" if result.success else "✗"
                print(f"  {status} {result.template_name} - {result.tool}")
    
    def display_templates(self, templates: list) -> None:
        """Display available templates."""
        if not self.silent:
            print(f"\\nAvailable templates ({len(templates)}):")
            for template in templates:
                print(f"  - {template.name}: {template.description or 'No description'}")
    
    def display_config(self, config: Dict[str, Any]) -> None:
        """Display configuration."""
        if not self.silent:
            print("\\nConfiguration:")
            self._print_dict(config, indent=2)
    
    def display_schema(self, schema: str) -> None:
        """Display JSON schema."""
        if not self.silent:
            print("\\nTemplate JSON Schema:")
            print(schema)
    
    def display_error(self, message: str) -> None:
        """Display error message."""
        print(f"Error: {message}", file=sys.stderr)
    
    def display_warning(self, message: str) -> None:
        """Display warning message."""
        if not self.silent:
            print(f"Warning: {message}", file=sys.stderr)
    
    def display_info(self, message: str) -> None:
        """Display info message."""
        if not self.silent:
            print(f"Info: {message}")
    
    def _print_dict(self, data: Dict[str, Any], indent: int = 0) -> None:
        """Print dictionary with indentation."""
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{' ' * indent}{key}:")
                self._print_dict(value, indent + 2)
            else:
                print(f"{' ' * indent}{key}: {value}")
    
    def set_silent(self, silent: bool) -> None:
        """Enable or disable silent mode."""
        self.silent = silent

    def display_version(self, version: str, app_name: str = "ipcrawler") -> None:
        """Display version information."""
        if not self.silent:
            print(f"\n{app_name} version {version}")
            print("Security Tool Orchestration Framework")
            print("Copyright (c) 2024 - Open Source")

    def display_help(self, app_name: str = "ipcrawler") -> None:
        """Display help information."""
        if not self.silent:
            print(f"\n{app_name} - Security Tool Orchestration Framework")
            print("\nUSAGE:")
            print("  python ipcrawler.py [OPTIONS] COMMAND [ARGS]")
            print("\nCOMMANDS:")
            print("  run TEMPLATE TARGET        Run a specific template")
            print("  scan-folder FOLDER TARGET  Run all templates in a folder")
            print("  scan-all TARGET           Run all templates")
            print("  list [--category CAT]     List available templates")
            print("  results TARGET            Show results for a target")
            print("  export TARGET             Export results")
            print("  config                    Show configuration")
            print("  schema                    Show template JSON schema")
            print("  validate                  Validate templates")
            print("\nSHORTCUTS:")
            print("  -default TARGET           Run default templates")
            print("  -recon TARGET             Run reconnaissance templates")
            print("  -custom TARGET            Run custom templates")
            print("  -htb TARGET               Run HTB/CTF templates")
            print("  -wiz, -wizard             Launch template creation wizard")
            print("\nOPTIONS:")
            print("  -debug, --debug           Enable debug mode")
            print("  --version                 Show version information")
            print("  -h, --help                Show this help message")
            print("\nEXAMPLES:")
            print("  python ipcrawler.py list")
            print("  python ipcrawler.py run custom/robots-txt-fetch example.com")
            print("  python ipcrawler.py -recon example.com")
            print("  python ipcrawler.py -debug scan-all example.com")