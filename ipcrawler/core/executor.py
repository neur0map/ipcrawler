"""
Template Execution Orchestrator for IPCrawler
Handles template execution coordination, progress tracking, and result management.
"""

import asyncio
import os
from typing import List, Optional

from . import ConfigManager, ResultsManager
from .preset_resolver import PresetResolver
from ..security import SecureExecutor
from ..models.template import ToolTemplate


class TemplateOrchestrator:
    """Orchestrates template execution with progress tracking and result management."""
    
    def __init__(self, config_manager: ConfigManager, results_manager: ResultsManager,
                 preset_resolver: PresetResolver, secure_executor: SecureExecutor, 
                 status_dispatcher):
        self.config_manager = config_manager
        self.results_manager = results_manager
        self.preset_resolver = preset_resolver
        self.secure_executor = secure_executor
        self.status_dispatcher = status_dispatcher
    
    async def run_templates(self, templates: List[ToolTemplate], target: str, 
                          folder: Optional[str] = None) -> None:
        """Run multiple templates with Rich TUI support."""
        # Check if this is a Rich TUI status dispatcher
        is_rich_ui = hasattr(self.status_dispatcher, '__aenter__')
        
        # Use Rich TUI context if available, otherwise run normally
        if is_rich_ui:
            try:
                async with self.status_dispatcher:
                    await self._execute_templates(templates, target, folder)
            except AttributeError:
                # Fallback if context manager not properly implemented
                await self._execute_templates(templates, target, folder)
        else:
            await self._execute_templates(templates, target, folder)
    
    async def _execute_templates(self, templates: List[ToolTemplate], target: str, 
                               folder: Optional[str] = None) -> None:
        """Execute templates with proper progress tracking."""
        # Start new scan session for real-time results
        self.results_manager.start_new_scan_session(target)
        
        # Check for sudo plugins and notify user
        self._check_and_notify_sudo_plugins(templates)
        
        self.status_dispatcher.start_scan(target, len(templates), folder)
        
        # Initialize plugins in the Rich status dispatcher if available
        if hasattr(self.status_dispatcher, 'initialize_plugins'):
            try:
                self.status_dispatcher.initialize_plugins(templates)
            except AttributeError:
                pass  # Skip if method not available
        
        # Execute all templates
        await self._execute_template_phase(templates, target, {})
        
        # Generate summary (this will create readable files) - always run this
        try:
            summary = self.results_manager.generate_summary(target)
            self.status_dispatcher.finish_scan(summary)
        except Exception as e:
            self.status_dispatcher.display_error(f"Error generating summary: {e}")
    
    async def _execute_template_phase(self, templates: List[ToolTemplate], target: str, 
                                    chain_variables: dict) -> None:
        """Execute a phase of templates with optional chain variables."""
        semaphore = asyncio.Semaphore(self.config_manager.get_concurrent_limit())
        
        async def execute_single_template(template: ToolTemplate):
            async with semaphore:
                # Show starting message when actually starting
                self.status_dispatcher.template_starting(template.tool, template.name, target)
                
                try:
                    result = await self.secure_executor.execute_template(
                        template_name=template.name,
                        tool=template.tool,
                        args=template.args,
                        target=target,
                        env=template.env,
                        wordlist=template.wordlist,
                        timeout=template.timeout,
                        preset=template.preset,
                        variables=template.variables,
                        preset_resolver=self.preset_resolver,
                        requires_sudo=template.requires_sudo or False,
                        chain_variables=chain_variables
                    )
                    
                    # Save and show completion immediately
                    self.results_manager.save_result(result, target)
                    self.status_dispatcher.update_progress(result)
                    
                except asyncio.CancelledError:
                    # Handle cancellation gracefully - don't save incomplete results
                    self.status_dispatcher.display_info(f"🚫 {template.name} cancelled")
                    raise
                    
                except Exception as e:
                    self.status_dispatcher.display_error(f"Execution error for {template.name}: {e}")
        
        # Create tasks for all templates
        tasks = [asyncio.create_task(execute_single_template(template)) for template in templates]
        
        try:
            # Wait for all to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            self.status_dispatcher.display_info("\\n⚠️  Scan cancelled by user")
            self.status_dispatcher.display_info("💾 Saving results from completed scans...")
            
            # Cancel any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait a bit for tasks to clean up
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                pass  # Ignore errors during cleanup
            
            # Re-raise to propagate the cancellation
            raise
    
    def _check_and_notify_sudo_plugins(self, templates: List[ToolTemplate]) -> None:
        """Check for sudo plugins and notify user if needed."""
        sudo_plugins = [t for t in templates if getattr(t, 'requires_sudo', False)]
        
        if not sudo_plugins:
            return
            
        # Check if running as root
        try:
            is_root = os.geteuid() == 0
        except AttributeError:
            is_root = False
        
        if not is_root:
            sudo_plugin_names = [p.name for p in sudo_plugins]
            self.status_dispatcher.display_info(
                f"⚠️  {len(sudo_plugins)} plugin(s) require sudo privileges: {', '.join(sudo_plugin_names)}"
            )
            self.status_dispatcher.display_info(
                "   These plugins will be skipped. Run with 'sudo' to execute them."
            )
        else:
            self.status_dispatcher.display_info(
                f"🔐 Running with sudo privileges - {len(sudo_plugins)} privileged plugin(s) will execute"
            )