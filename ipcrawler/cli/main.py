"""
Main CLI application for ipcrawler.
"""

import argparse
import asyncio
from typing import List, Optional

from ..core import ConfigManager, TemplateDiscovery, ResultsManager, StatusDispatcher
from ..core.schema import TemplateSchema
from ..security import SecureExecutor
from ..models.template import ToolTemplate


class IPCrawlerCLI:
    """Main CLI application class."""
    
    # Constants
    TARGET_HELP = 'Target (IP, domain, or URL)'
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.template_discovery = TemplateDiscovery("templates")
        self.results_manager = ResultsManager()
        self.status_dispatcher = StatusDispatcher(False)  # Always show scan output
        self.executor = SecureExecutor(
            timeout=self.config_manager.get_default_timeout(),
            max_output_size=self.config_manager.config.settings.max_output_size
        )
        
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create command-line argument parser."""
        parser = argparse.ArgumentParser(
            description="ipcrawler - Security Tool Orchestration Framework",
            formatter_class=argparse.RawDescriptionHelpFormatter
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
        export_parser.add_argument('--format', choices=['txt', 'json', 'md'], default='txt')
        export_parser.add_argument('--output', help='Output file path')
        
        # Config command
        subparsers.add_parser('config', help='Show configuration')
        
        # Schema command
        subparsers.add_parser('schema', help='Show template JSON schema')
        
        # Validate command
        validate_parser = subparsers.add_parser('validate', help='Validate templates')
        validate_parser.add_argument('--category', help='Validate specific category')
        
        # Add flags for category shortcuts
        for flag, folder in self.config_manager.config.templates.items():
            flag_parser = subparsers.add_parser(f'-{flag}', help=f'Run all templates in {folder}')
            flag_parser.add_argument('target', help=self.TARGET_HELP)
        
        return parser
    
    async def run_template(self, template_name: str, target: str) -> None:
        """Run a specific template."""
        try:
            # Parse template path
            if '/' in template_name:
                category, name = template_name.split('/', 1)
                template = self.template_discovery.get_template_by_name(name, category)
            else:
                template = self.template_discovery.get_template_by_name(template_name)
            
            if not template:
                self.status_dispatcher.display_error(f"Template not found: {template_name}")
                return
            
            # Execute template
            self.status_dispatcher.start_scan(target, 1)
            
            result = await self.executor.execute_template(
                template_name=template.name,
                tool=template.tool,
                args=template.args,
                target=target,
                env=template.env,
                timeout=template.timeout
            )
            
            # Save and display result
            self.results_manager.save_result(result, target)
            self.status_dispatcher.update_progress(result)
            
            summary = self.results_manager.generate_summary(target)
            self.status_dispatcher.finish_scan(summary)
            
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to run template: {e}")
    
    async def run_folder(self, folder: str, target: str) -> None:
        """Run all templates in a folder."""
        try:
            templates = self.template_discovery.discover_templates(folder)
            
            if not templates:
                self.status_dispatcher.display_error(f"No templates found in folder: {folder}")
                return
            
            await self._run_templates(templates, target, folder)
            
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to run folder: {e}")
    
    async def run_all(self, target: str) -> None:
        """Run all available templates."""
        try:
            templates = self.template_discovery.discover_templates()
            
            if not templates:
                self.status_dispatcher.display_error("No templates found")
                return
            
            await self._run_templates(templates, target)
            
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to run all templates: {e}")
    
    async def _run_templates(self, templates: List[ToolTemplate], target: str, folder: Optional[str] = None) -> None:
        """Run multiple templates."""
        self.status_dispatcher.start_scan(target, len(templates), folder)
        
        # Create async tasks for real-time execution
        semaphore = asyncio.Semaphore(self.config_manager.get_concurrent_limit())
        tasks = []
        results = []
        
        async def execute_single_template(template: ToolTemplate):
            async with semaphore:
                # Show starting message when actually starting
                self.status_dispatcher.template_starting(template.tool, template.name, target)
                
                try:
                    result = await self.executor.execute_template(
                        template_name=template.name,
                        tool=template.tool,
                        args=template.args,
                        target=target,
                        env=template.env,
                        timeout=template.timeout
                    )
                    
                    # Save and show completion immediately
                    self.results_manager.save_result(result, target)
                    self.status_dispatcher.update_progress(result)
                    results.append(result)
                    return result
                    
                except Exception as e:
                    self.status_dispatcher.display_error(f"Execution error for {template.name}: {e}")
                    return e
        
        # Create tasks for all templates
        tasks = [execute_single_template(template) for template in templates]
        
        # Wait for all to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Generate summary (this will create readable files)
        summary = self.results_manager.generate_summary(target)
        self.status_dispatcher.finish_scan(summary)
    
    def list_templates(self, category: Optional[str] = None) -> None:
        """List available templates."""
        try:
            templates = self.template_discovery.discover_templates(category)
            self.status_dispatcher.display_templates(templates)
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to list templates: {e}")
    
    def show_results(self, target: str) -> None:
        """Show results for a target."""
        try:
            results = self.results_manager.get_results(target)
            self.status_dispatcher.display_results(results)
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to show results: {e}")
    
    def export_results(self, target: str, format: str, output: Optional[str] = None) -> None:
        """Export results."""
        try:
            exported = self.results_manager.export_results(target, format)
            
            if output:
                with open(output, 'w') as f:
                    f.write(exported)
                self.status_dispatcher.display_info(f"Results exported to {output}")
            else:
                print(exported)
                
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to export results: {e}")
    
    def show_config(self) -> None:
        """Show configuration."""
        self.status_dispatcher.display_config(self.config_manager.to_dict())
    
    def show_schema(self) -> None:
        """Show JSON schema."""
        self.status_dispatcher.display_schema(TemplateSchema.get_schema_json())
    
    def validate_templates(self, category: Optional[str] = None) -> None:
        """Validate templates."""
        try:
            if category:
                templates = self.template_discovery.discover_templates(category)
                self.status_dispatcher.display_info(f"Validated {len(templates)} templates in {category}")
            else:
                results = self.template_discovery.validate_all_templates()
                self.status_dispatcher.display_info(f"Valid templates: {len(results['valid'])}")
                self.status_dispatcher.display_info(f"Invalid templates: {len(results['invalid'])}")
                
                for invalid in results['invalid']:
                    self.status_dispatcher.display_error(invalid)
                    
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to validate templates: {e}")
    
    def _parse_arguments(self):
        """Parse command line arguments, handling flag-style commands."""
        import sys
        
        # Handle flag-style commands manually due to argparse limitations
        if len(sys.argv) >= 3 and sys.argv[1].startswith('-'):
            command = sys.argv[1]
            target = sys.argv[2]
            flag = command[1:]  # Remove the '-' prefix
            
            if flag in self.config_manager.config.templates:
                return self._create_flag_args(command, target)
        
        # Normal parsing for other commands
        parser = self.create_parser()
        return parser.parse_args()
    
    def _create_flag_args(self, command: str, target: str):
        """Create args object for flag-style commands."""
        class Args:
            def __init__(self, command, target):
                self.command = command
                self.target = target
                self.template = None
                self.folder = None
                self.category = None
                self.format = None
                self.output = None
        
        return Args(command, target)
    
    async def _execute_command(self, args):
        """Execute the parsed command."""
        if args.command == 'run':
            await self.run_template(args.template or '', args.target)
        elif args.command == 'scan-folder':
            await self.run_folder(args.folder or '', args.target)
        elif args.command == 'scan-all':
            await self.run_all(args.target)
        elif args.command == 'list':
            self.list_templates(getattr(args, 'category', None))
        elif args.command == 'results':
            self.show_results(args.target)
        elif args.command == 'export':
            self.export_results(args.target, args.format or 'txt', getattr(args, 'output', None))
        elif args.command == 'config':
            self.show_config()
        elif args.command == 'schema':
            self.show_schema()
        elif args.command == 'validate':
            self.validate_templates(getattr(args, 'category', None))
        elif args.command.startswith('-'):
            # Handle category shortcuts
            flag = args.command[1:]
            folder = self.config_manager.get_template_folder(flag)
            await self.run_folder(folder, args.target)
        else:
            parser = self.create_parser()
            parser.print_help()
    
    async def main(self) -> None:
        """Main entry point."""
        import sys
        
        args = self._parse_arguments()
        
        if not args.command:
            parser = self.create_parser()
            parser.print_help()
            return
        
        try:
            await self._execute_command(args)
        except KeyboardInterrupt:
            self.status_dispatcher.display_info("Interrupted by user")
        except Exception as e:
            self.status_dispatcher.display_error(f"Unexpected error: {e}")
            sys.exit(1)


def main():
    """Entry point for the application."""
    cli = IPCrawlerCLI()
    asyncio.run(cli.main())