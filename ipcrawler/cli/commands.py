"""
CLI Command Handler for IPCrawler
Handles individual command execution and business logic.
"""

from typing import Optional

from ..core import ConfigManager, TemplateDiscovery, ResultsManager
from ..core.schema import TemplateSchema
from ..core.preset_resolver import PresetResolver
from ..core.sentry_integration import sentry_manager, with_sentry_context
from ..core.executor import TemplateOrchestrator
from ..wizard.template_wizard import TemplateWizard


class CommandHandler:
    """Handles CLI command execution and business logic."""
    
    def __init__(self, config_manager: ConfigManager, template_discovery: TemplateDiscovery, 
                 results_manager: ResultsManager, preset_resolver: PresetResolver,
                 orchestrator: TemplateOrchestrator, status_dispatcher):
        self.config_manager = config_manager
        self.template_discovery = template_discovery
        self.results_manager = results_manager
        self.preset_resolver = preset_resolver
        self.orchestrator = orchestrator
        self.status_dispatcher = status_dispatcher
        self.debug_mode = False
    
    def set_debug_mode(self, debug_mode: bool):
        """Set debug mode for error tracking."""
        self.debug_mode = debug_mode
    
    @with_sentry_context("run_template")
    async def run_template(self, template_name: str, target: str) -> None:
        """Run a specific template."""
        if self.debug_mode:
            sentry_manager.add_breadcrumb(
                f"Running template: {template_name}",
                data={"template": template_name, "target": target}
            )
        
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
            
            # Execute template using orchestrator
            await self.orchestrator.run_templates([template], target)
            
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to run template: {e}")
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "template_execution": {
                        "template_name": template_name,
                        "target": target,
                        "execution_type": "single_template"
                    }
                })
    
    @with_sentry_context("run_folder")
    async def run_folder(self, folder: str, target: str) -> None:
        """Run all templates in a folder."""
        if self.debug_mode:
            sentry_manager.add_breadcrumb(
                f"Running folder: {folder}",
                data={"folder": folder, "target": target}
            )
        
        try:
            # Normalize folder path - strip 'templates/' prefix if present
            if folder.startswith('templates/'):
                folder = folder[10:]  # Remove 'templates/' prefix
            
            templates = self.template_discovery.discover_templates(folder)
            
            if not templates:
                self.status_dispatcher.display_error(f"No templates found in folder: {folder}")
                return
            
            await self.orchestrator.run_templates(templates, target, folder)
            
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to run folder: {e}")
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "template_execution": {
                        "folder": folder,
                        "target": target,
                        "execution_type": "folder"
                    }
                })
    
    async def run_all(self, target: str) -> None:
        """Run all available templates."""
        try:
            templates = self.template_discovery.discover_templates()
            
            if not templates:
                self.status_dispatcher.display_error("No templates found")
                return
            
            await self.orchestrator.run_templates(templates, target)
            
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to run all templates: {e}")
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "template_execution": {
                        "target": target,
                        "execution_type": "all_templates"
                    }
                })
    
    def list_templates(self, category: Optional[str] = None) -> None:
        """List available templates."""
        try:
            templates = self.template_discovery.discover_templates(category)
            self.status_dispatcher.display_templates(templates)
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to list templates: {e}")
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "command": "list_templates",
                    "category": category
                })
    
    def show_results(self, target: str) -> None:
        """Show results for a target."""
        try:
            results = self.results_manager.get_results(target)
            self.status_dispatcher.display_results(results)
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to show results: {e}")
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "command": "show_results",
                    "target": target
                })
    
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
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "command": "export_results",
                    "target": target,
                    "format": format,
                    "output": output
                })
    
    def show_config(self) -> None:
        """Show configuration."""
        try:
            self.status_dispatcher.display_config(self.config_manager.to_dict())
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to show config: {e}")
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "command": "show_config"
                })
    
    def show_schema(self) -> None:
        """Show JSON schema."""
        try:
            self.status_dispatcher.display_schema(TemplateSchema.get_schema_json())
        except Exception as e:
            self.status_dispatcher.display_error(f"Failed to show schema: {e}")
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "command": "show_schema"
                })
    
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
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "command": "validate_templates",
                    "category": category
                })
    
    @with_sentry_context("launch_wizard")
    def launch_wizard(self) -> None:
        """Launch the interactive template creation wizard."""
        if self.debug_mode:
            sentry_manager.add_breadcrumb(
                "Launching template wizard",
                data={"wizard_type": "template_creation"}
            )
        
        try:
            # Get UI config for wizard theming
            ui_config = self.config_manager.get_ui_config() or {}
            
            # Create and run enhanced wizard
            wizard = TemplateWizard(ui_config)
            success = wizard.run()
            
            if success:
                self.status_dispatcher.display_info("Template created successfully!")
            else:
                self.status_dispatcher.display_info("Template creation cancelled or failed.")
                
        except Exception as e:
            self.status_dispatcher.display_error(f"Wizard failed: {e}")
            if self.debug_mode:
                sentry_manager.capture_exception(e, {
                    "wizard_execution": {
                        "wizard_type": "template_creation",
                        "execution_stage": "wizard_launch"
                    }
                })
    
    async def execute_command(self, args):
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
            # Handle category shortcuts and special commands
            flag = args.command[1:]
            
            # Handle wizard commands
            if flag in ['wiz', 'wizard']:
                self.launch_wizard()
                return
            
            # Handle other category shortcuts
            templates_config = self.config_manager.get_templates_config()
            if templates_config and "categories" in templates_config:
                folder = templates_config["categories"].get(flag, flag)
                await self.run_folder(folder, args.target)
        else:
            # This shouldn't happen with proper argument parsing
            self.status_dispatcher.display_error(f"Unknown command: {args.command}")