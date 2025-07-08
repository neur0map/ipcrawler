"""
Sentry integration for comprehensive error tracking and debugging.
Only activates when debug flag is used AND Sentry DSN is configured.
"""

import os
import sys
import traceback
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.threading import ThreadingIntegration
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    sentry_sdk = None


class SentryManager:
    """
    Manages Sentry integration for deep error tracking throughout ipcrawler.
    
    Requirements:
    1. -debug flag must be used in CLI
    2. .env file must exist with SENTRY_DSN
    """
    
    def __init__(self):
        self.enabled = False
        self.initialized = False
        self.debug_mode = False
        self.env_file_path = Path.cwd() / ".env"
        self.sentry_dsn = None
        
    def check_requirements(self, debug_flag: bool = False) -> tuple[bool, str]:
        """
        Check if Sentry can be enabled based on requirements.
        
        Args:
            debug_flag: Whether -debug flag was used
            
        Returns:
            tuple: (can_enable, error_message)
        """
        if not SENTRY_AVAILABLE:
            return False, "Sentry SDK not available. Install with: pip install sentry-sdk>=1.40.0"
        
        # Check requirement 1: Debug flag
        if not debug_flag:
            return False, "Debug mode not enabled. Use -debug flag to enable Sentry error tracking."
        
        # Check requirement 2: .env file with SENTRY_DSN
        if not self.env_file_path.exists():
            return False, f"Environment file not found at {self.env_file_path}. Create .env file with SENTRY_DSN=<your-dsn>"
        
        # Load environment variables from .env file
        try:
            self._load_env_file()
        except Exception as e:
            return False, f"Failed to load .env file: {e}"
        
        # Check for SENTRY_DSN
        self.sentry_dsn = os.getenv("SENTRY_DSN")
        if not self.sentry_dsn:
            return False, "SENTRY_DSN not found in .env file. Add: SENTRY_DSN=<your-sentry-dsn>"
        
        if not self.sentry_dsn.startswith(("https://", "http://")):
            return False, "Invalid SENTRY_DSN format. Must be a valid Sentry DSN URL."
        
        return True, "Sentry requirements met"
    
    def _load_env_file(self):
        """Load environment variables from .env file."""
        try:
            with open(self.env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
        except Exception as e:
            raise Exception(f"Error reading .env file: {e}")
    
    def initialize(self, debug_flag: bool = False) -> bool:
        """
        Initialize Sentry integration if requirements are met.
        
        Args:
            debug_flag: Whether -debug flag was used
            
        Returns:
            bool: True if successfully initialized
        """
        if self.initialized:
            return self.enabled
        
        can_enable, error_message = self.check_requirements(debug_flag)
        
        if not can_enable:
            if debug_flag:
                # Only show error if debug flag was used
                print(f"❌ Sentry Debug Mode: {error_message}")
            return False
        
        try:
            # Configure Sentry with comprehensive integrations
            sentry_sdk.init(
                dsn=self.sentry_dsn,
                traces_sample_rate=1.0,  # Capture all transactions for debugging
                profiles_sample_rate=1.0,  # Capture all profiles
                debug=True,  # Enable debug output
                environment=os.getenv("SENTRY_ENVIRONMENT", "debug"),
                release=os.getenv("SENTRY_RELEASE", "ipcrawler-dev"),
                integrations=[
                    LoggingIntegration(
                        level=logging.INFO,  # Capture info and above
                        event_level=logging.ERROR  # Send errors as events
                    ),
                    ThreadingIntegration(propagate_hub=True),
                    AsyncioIntegration(),
                ],
                before_send=self._before_send_hook,
                max_breadcrumbs=100,  # Keep more breadcrumbs for debugging
                attach_stacktrace=True,
                send_default_pii=True,  # Send user IP, etc. for debugging
            )
            
            self.enabled = True
            self.initialized = True
            self.debug_mode = debug_flag
            
            # Send initialization event
            sentry_sdk.add_breadcrumb(
                message="Sentry debug mode initialized",
                level="info",
                data={
                    "debug_flag": debug_flag,
                    "env_file": str(self.env_file_path),
                    "dsn_configured": bool(self.sentry_dsn)
                }
            )
            
            print(f"✅ Sentry Debug Mode: Enabled - All errors will be tracked")
            print(f"📡 Sentry DSN: {self.sentry_dsn[:50]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Sentry Debug Mode: Failed to initialize - {e}")
            return False
    
    def _before_send_hook(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Hook called before sending events to Sentry.
        Adds additional context and filtering.
        """
        if not self.enabled:
            return None
        
        # Add ipcrawler-specific context
        event.setdefault("tags", {}).update({
            "component": "ipcrawler",
            "debug_mode": "true"
        })
        
        # Add extra context about the error
        if "contexts" not in event:
            event["contexts"] = {}
        
        event["contexts"]["ipcrawler"] = {
            "version": "2.0",
            "debug_mode": True,
            "env_file_exists": self.env_file_path.exists()
        }
        
        return event
    
    def capture_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Capture an exception with additional context.
        
        Args:
            exception: The exception to capture
            context: Additional context data
        """
        if not self.enabled:
            return
        
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            
            scope.set_tag("error_type", "ipcrawler_exception")
            sentry_sdk.capture_exception(exception)
    
    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
        """
        Capture a message with additional context.
        
        Args:
            message: The message to capture
            level: Log level (info, warning, error, fatal)
            context: Additional context data
        """
        if not self.enabled:
            return
        
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            
            scope.set_tag("message_type", "ipcrawler_message")
            sentry_sdk.capture_message(message, level)
    
    def add_breadcrumb(self, message: str, category: str = "ipcrawler", level: str = "info", data: Optional[Dict[str, Any]] = None):
        """
        Add a breadcrumb for debugging context.
        
        Args:
            message: Breadcrumb message
            category: Breadcrumb category
            level: Log level
            data: Additional data
        """
        if not self.enabled:
            return
        
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
    
    def set_user_context(self, user_data: Dict[str, Any]):
        """Set user context for debugging."""
        if not self.enabled:
            return
        
        sentry_sdk.set_user(user_data)
    
    def set_tag(self, key: str, value: str):
        """Set a tag for all future events."""
        if not self.enabled:
            return
        
        sentry_sdk.set_tag(key, value)
    
    def flush(self, timeout: int = 10):
        """Flush all pending events to Sentry."""
        if not self.enabled:
            return
        
        sentry_sdk.flush(timeout)


# Global instance
sentry_manager = SentryManager()


def with_sentry_context(context_name: str):
    """
    Decorator to wrap functions with Sentry context and error capture.
    
    Args:
        context_name: Name of the context for debugging
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not sentry_manager.enabled:
                return func(*args, **kwargs)
            
            sentry_manager.add_breadcrumb(
                message=f"Entering {context_name}",
                category="function_call",
                data={
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs)
                }
            )
            
            try:
                result = func(*args, **kwargs)
                sentry_manager.add_breadcrumb(
                    message=f"Exiting {context_name} successfully",
                    category="function_call"
                )
                return result
            except Exception as e:
                sentry_manager.capture_exception(e, {
                    "function_context": {
                        "name": func.__name__,
                        "context": context_name,
                        "args": str(args)[:500],  # Truncate for safety
                        "kwargs": str(kwargs)[:500]
                    }
                })
                raise
        
        return wrapper
    return decorator


def capture_template_execution_error(template_name: str, tool: str, error: Exception, context: Dict[str, Any] = None):
    """
    Specialized function for capturing template execution errors.
    
    Args:
        template_name: Name of the template that failed
        tool: Tool that was being executed
        error: The error that occurred
        context: Additional context about the execution
    """
    if not sentry_manager.enabled:
        return
    
    full_context = {
        "template_execution": {
            "template_name": template_name,
            "tool": tool,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
    }
    
    if context:
        full_context["execution_context"] = context
    
    sentry_manager.capture_exception(error, full_context)


def capture_preset_resolution_error(preset_name: str, error: Exception, context: Dict[str, Any] = None):
    """
    Specialized function for capturing preset resolution errors.
    
    Args:
        preset_name: Name of the preset that failed to resolve
        error: The error that occurred
        context: Additional context about the resolution
    """
    if not sentry_manager.enabled:
        return
    
    full_context = {
        "preset_resolution": {
            "preset_name": preset_name,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
    }
    
    if context:
        full_context["resolution_context"] = context
    
    sentry_manager.capture_exception(error, full_context)


def capture_validation_error(validation_type: str, error: Exception, context: Dict[str, Any] = None):
    """
    Specialized function for capturing validation errors.
    
    Args:
        validation_type: Type of validation that failed
        error: The error that occurred
        context: Additional context about the validation
    """
    if not sentry_manager.enabled:
        return
    
    full_context = {
        "validation_error": {
            "validation_type": validation_type,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
    }
    
    if context:
        full_context["validation_context"] = context
    
    sentry_manager.capture_exception(error, full_context)