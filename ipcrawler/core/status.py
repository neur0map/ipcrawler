"""
Status display and console output management.
"""

import sys
from typing import Optional, Dict, Any
from datetime import datetime
from ..models.result import ExecutionResult, ScanResult


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