"""
Error Handler for IPCrawler
Centralized error handling and graceful shutdown management.
"""

import sys
from typing import Optional

from .sentry_integration import sentry_manager


class ErrorHandler:
    """Centralized error handling and graceful shutdown management."""
    
    def __init__(self, status_dispatcher):
        self.status_dispatcher = status_dispatcher
    
    async def handle_keyboard_interrupt(self, debug_mode: bool = False):
        """Handle Ctrl+C gracefully."""
        self.status_dispatcher.display_info("\\n🛑 Execution interrupted by user")
        self.status_dispatcher.display_info("📊 Check results directory for any completed scans")
        
        if debug_mode:
            sentry_manager.capture_message("User interrupted execution", "info")
            sentry_manager.flush()
        
        # Exit gracefully without traceback
        sys.exit(0)
    
    async def handle_unexpected_error(self, error: Exception, command: Optional[str] = None, 
                                    debug_mode: bool = False):
        """Handle unexpected errors."""
        self.status_dispatcher.display_error(f"Unexpected error: {error}")
        
        if debug_mode:
            sentry_manager.capture_exception(error, {
                "error_context": {
                    "command": command,
                    "debug_mode": debug_mode,
                    "error_type": type(error).__name__
                }
            })
            sentry_manager.flush()
    
    def handle_template_error(self, template_name: str, error: Exception, 
                            target: str = None, debug_mode: bool = False):
        """Handle template execution errors."""
        self.status_dispatcher.display_error(f"Template error in {template_name}: {error}")
        
        if debug_mode:
            sentry_manager.capture_exception(error, {
                "template_error": {
                    "template_name": template_name,
                    "target": target,
                    "error_type": type(error).__name__
                }
            })
    
    def handle_configuration_error(self, error: Exception, debug_mode: bool = False):
        """Handle configuration-related errors."""
        self.status_dispatcher.display_error(f"Configuration error: {error}")
        
        if debug_mode:
            sentry_manager.capture_exception(error, {
                "configuration_error": {
                    "error_type": type(error).__name__
                }
            })
    
    def handle_validation_error(self, error: Exception, context: str = None, 
                              debug_mode: bool = False):
        """Handle validation errors."""
        error_msg = f"Validation error: {error}"
        if context:
            error_msg = f"Validation error in {context}: {error}"
        
        self.status_dispatcher.display_error(error_msg)
        
        if debug_mode:
            sentry_manager.capture_exception(error, {
                "validation_error": {
                    "context": context,
                    "error_type": type(error).__name__
                }
            })
    
    def handle_security_error(self, error: Exception, template_name: str = None, 
                            debug_mode: bool = False):
        """Handle security-related errors."""
        error_msg = f"Security error: {error}"
        if template_name:
            error_msg = f"Security error in {template_name}: {error}"
        
        self.status_dispatcher.display_error(error_msg)
        
        if debug_mode:
            sentry_manager.capture_exception(error, {
                "security_error": {
                    "template_name": template_name,
                    "error_type": type(error).__name__
                }
            })
    
    def handle_file_system_error(self, error: Exception, file_path: str = None, 
                               debug_mode: bool = False):
        """Handle file system errors."""
        error_msg = f"File system error: {error}"
        if file_path:
            error_msg = f"File system error with {file_path}: {error}"
        
        self.status_dispatcher.display_error(error_msg)
        
        if debug_mode:
            sentry_manager.capture_exception(error, {
                "file_system_error": {
                    "file_path": file_path,
                    "error_type": type(error).__name__
                }
            })
    
    def handle_network_error(self, error: Exception, target: str = None, 
                           debug_mode: bool = False):
        """Handle network-related errors."""
        error_msg = f"Network error: {error}"
        if target:
            error_msg = f"Network error connecting to {target}: {error}"
        
        self.status_dispatcher.display_error(error_msg)
        
        if debug_mode:
            sentry_manager.capture_exception(error, {
                "network_error": {
                    "target": target,
                    "error_type": type(error).__name__
                }
            })
    
    def log_warning(self, message: str, context: dict = None, debug_mode: bool = False):
        """Log warning messages."""
        self.status_dispatcher.display_info(f"⚠️  {message}")
        
        if debug_mode:
            sentry_manager.capture_message(message, "warning", context or {})
    
    def log_info(self, message: str, context: dict = None, debug_mode: bool = False):
        """Log informational messages."""
        self.status_dispatcher.display_info(message)
        
        if debug_mode:
            sentry_manager.add_breadcrumb(message, data=context or {})