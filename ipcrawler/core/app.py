"""
Application Controller for IPCrawler
Coordinates all components and manages application lifecycle.
"""

import asyncio
import sys
from typing import Any

from . import ConfigManager, TemplateDiscovery, ResultsManager
from .status import create_status_dispatcher
from .preset_resolver import PresetResolver
from .executor import TemplateOrchestrator
from .chain_resolver import ChainResolver
from .sentry_integration import sentry_manager, with_sentry_context
from .error_handler import ErrorHandler
from ..cli.parser import ArgumentParser
from ..cli.commands import CommandHandler
from ..security import SecureExecutor


class IPCrawlerApp:
    """Main application controller that orchestrates all components."""
    
    def __init__(self):
        # Initialize core components
        self.config_manager = ConfigManager()
        self.template_discovery = TemplateDiscovery("templates")
        self.results_manager = ResultsManager(config_manager=self.config_manager)
        self.preset_resolver = PresetResolver(self.config_manager)
        self.chain_resolver = ChainResolver()
        
        # Create status dispatcher with Rich TUI if enabled
        ui_config = self.config_manager.get_ui_config()
        self.status_dispatcher = create_status_dispatcher(ui_config, False)
        
        # Initialize security components
        self.secure_executor = SecureExecutor(
            timeout=self.config_manager.get_default_timeout(),
            max_output_size=self.config_manager.config.settings.max_output_size
        )
        
        # Initialize orchestrator
        self.orchestrator = TemplateOrchestrator(
            self.config_manager,
            self.results_manager,
            self.preset_resolver,
            self.secure_executor,
            self.status_dispatcher
        )
        
        # Initialize CLI components
        self.argument_parser = ArgumentParser(self.config_manager)
        self.command_handler = CommandHandler(
            self.config_manager,
            self.template_discovery,
            self.results_manager,
            self.preset_resolver,
            self.orchestrator,
            self.status_dispatcher
        )
        
        # Initialize error handler
        self.error_handler = ErrorHandler(self.status_dispatcher)
        
        # Application state
        self.debug_mode = False
    
    def _initialize_debug_mode(self, debug_flag: bool):
        """Initialize debug mode and Sentry integration."""
        self.debug_mode = debug_flag
        self.command_handler.set_debug_mode(debug_flag)
        
        if debug_flag:
            # Initialize Sentry with debug flag
            sentry_initialized = sentry_manager.initialize(debug_flag=True)
            if sentry_initialized:
                sentry_manager.add_breadcrumb("Application startup", data={"debug_mode": True})
                sentry_manager.set_tag("app_mode", "debug")
    
    def _parse_arguments(self) -> Any:
        """Parse command line arguments."""
        return self.argument_parser.parse_arguments(self.status_dispatcher)
    
    @with_sentry_context("main_execution")
    async def run(self) -> None:
        """Main application entry point."""
        try:
            # Parse arguments
            args = self._parse_arguments()
            
            # Initialize debug mode if requested
            debug_flag = getattr(args, 'debug', False)
            self._initialize_debug_mode(debug_flag)
            
            # Check if we have a command to execute
            if not args.command:
                parser = self.argument_parser.create_parser()
                parser.print_help()
                return
            
            # Execute the command
            await self.command_handler.execute_command(args)
            
            # Flush Sentry events before exit
            if self.debug_mode:
                sentry_manager.flush()
        
        except (KeyboardInterrupt, asyncio.CancelledError):
            # Handle Ctrl+C gracefully
            await self.error_handler.handle_keyboard_interrupt(self.debug_mode)
        
        except Exception as e:
            # Handle unexpected errors
            await self.error_handler.handle_unexpected_error(e, args.command if 'args' in locals() else None, self.debug_mode)
            sys.exit(1)
    
    def get_config_manager(self) -> ConfigManager:
        """Get the configuration manager."""
        return self.config_manager
    
    def get_template_discovery(self) -> TemplateDiscovery:
        """Get the template discovery component."""
        return self.template_discovery
    
    def get_results_manager(self) -> ResultsManager:
        """Get the results manager."""
        return self.results_manager
    
    def get_status_dispatcher(self):
        """Get the status dispatcher."""
        return self.status_dispatcher
    
    def get_orchestrator(self) -> TemplateOrchestrator:
        """Get the template orchestrator."""
        return self.orchestrator
    
    def get_command_handler(self) -> CommandHandler:
        """Get the command handler."""
        return self.command_handler