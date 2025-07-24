"""Base error handlers for IPCrawler

Provides error handling strategies and recovery mechanisms.
"""

from abc import ABC, abstractmethod
from typing import Type, Optional, Callable, Dict, Any, List
import traceback
from datetime import datetime
import sys

from .exceptions import IPCrawlerError, RecoverableError


class ErrorHandler(ABC):
    """Abstract base class for error handlers"""
    
    def __init__(self, logger: Optional[Any] = None):
        """Initialize error handler
        
        Args:
            logger: Logger instance for error logging
        """
        self.logger = logger
        self.error_count = 0
        self.error_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle an error
        
        Args:
            error: The exception to handle
            context: Additional context about the error
            
        Returns:
            True if error was handled, False otherwise
        """
        pass
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log error details"""
        self.error_count += 1
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'type': type(error).__name__,
            'message': str(error),
            'context': context or {},
            'traceback': traceback.format_exc()
        }
        self.error_history.append(error_info)
        
        if self.logger:
            self.logger.error(f"{error_info['type']}: {error_info['message']}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of handled errors"""
        return {
            'total_errors': self.error_count,
            'error_types': self._count_error_types(),
            'recent_errors': self.error_history[-10:]  # Last 10 errors
        }
    
    def _count_error_types(self) -> Dict[str, int]:
        """Count errors by type"""
        counts = {}
        for error in self.error_history:
            error_type = error['type']
            counts[error_type] = counts.get(error_type, 0) + 1
        return counts


class ChainedErrorHandler(ErrorHandler):
    """Error handler that chains multiple handlers"""
    
    def __init__(self, handlers: List[ErrorHandler], logger: Optional[Any] = None):
        """Initialize chained handler
        
        Args:
            handlers: List of handlers to chain
            logger: Logger instance
        """
        super().__init__(logger)
        self.handlers = handlers
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle error by trying each handler in sequence"""
        self.log_error(error, context)
        
        for handler in self.handlers:
            try:
                if handler.handle(error, context):
                    return True
            except Exception as e:
                # Log handler failure but continue
                if self.logger:
                    self.logger.warning(f"Handler {handler.__class__.__name__} failed: {e}")
        
        return False
    
    def add_handler(self, handler: ErrorHandler):
        """Add a handler to the chain"""
        self.handlers.append(handler)
    
    def remove_handler(self, handler_type: Type[ErrorHandler]):
        """Remove handlers of specific type"""
        self.handlers = [h for h in self.handlers if not isinstance(h, handler_type)]


class RetryHandler(ErrorHandler):
    """Error handler that implements retry logic"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0, 
                 recoverable_errors: Optional[List[Type[Exception]]] = None,
                 logger: Optional[Any] = None):
        """Initialize retry handler
        
        Args:
            max_retries: Maximum number of retries
            backoff_factor: Exponential backoff factor
            recoverable_errors: List of error types that are recoverable
            logger: Logger instance
        """
        super().__init__(logger)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.recoverable_errors = recoverable_errors or [RecoverableError]
        self.retry_counts: Dict[str, int] = {}
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle error with retry logic"""
        if not self._is_recoverable(error):
            return False
        
        operation = context.get('operation', 'unknown') if context else 'unknown'
        retry_count = self.retry_counts.get(operation, 0)
        
        if retry_count >= self.max_retries:
            if self.logger:
                self.logger.error(f"Max retries ({self.max_retries}) reached for {operation}")
            return False
        
        self.retry_counts[operation] = retry_count + 1
        
        # Calculate backoff
        wait_time = self.backoff_factor ** retry_count
        
        if self.logger:
            self.logger.info(f"Retrying {operation} (attempt {retry_count + 1}/{self.max_retries}) "
                           f"after {wait_time}s")
        
        # Store retry info in context
        if context:
            context['retry_count'] = retry_count + 1
            context['wait_time'] = wait_time
        
        return True
    
    def _is_recoverable(self, error: Exception) -> bool:
        """Check if error is recoverable"""
        return any(isinstance(error, err_type) for err_type in self.recoverable_errors)
    
    def reset_retry_count(self, operation: str):
        """Reset retry count for an operation"""
        if operation in self.retry_counts:
            del self.retry_counts[operation]


class FallbackHandler(ErrorHandler):
    """Error handler that provides fallback behavior"""
    
    def __init__(self, fallback_actions: Dict[Type[Exception], Callable],
                 logger: Optional[Any] = None):
        """Initialize fallback handler
        
        Args:
            fallback_actions: Mapping of error types to fallback functions
            logger: Logger instance
        """
        super().__init__(logger)
        self.fallback_actions = fallback_actions
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle error by executing fallback action"""
        error_type = type(error)
        
        # Check for exact match first
        if error_type in self.fallback_actions:
            return self._execute_fallback(self.fallback_actions[error_type], error, context)
        
        # Check for subclass matches
        for registered_type, action in self.fallback_actions.items():
            if isinstance(error, registered_type):
                return self._execute_fallback(action, error, context)
        
        return False
    
    def _execute_fallback(self, action: Callable, error: Exception, 
                         context: Optional[Dict[str, Any]]) -> bool:
        """Execute fallback action"""
        try:
            if context:
                action(error, context)
            else:
                action(error)
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fallback action failed: {e}")
            return False
    
    def register_fallback(self, error_type: Type[Exception], action: Callable):
        """Register a fallback action for an error type"""
        self.fallback_actions[error_type] = action


class GlobalErrorHandler:
    """Global error handler for the application"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.handlers: List[ErrorHandler] = []
            self.initialized = True
    
    def register_handler(self, handler: ErrorHandler):
        """Register a global error handler"""
        self.handlers.append(handler)
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle error using registered handlers"""
        for handler in self.handlers:
            try:
                if handler.handle(error, context):
                    return True
            except Exception:
                pass  # Continue with next handler
        
        # No handler could handle the error
        return False
    
    def install_exception_hook(self):
        """Install global exception hook"""
        def exception_hook(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Try to handle with registered handlers
            if not self.handle_error(exc_value):
                # Fall back to default behavior
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
        sys.excepthook = exception_hook


# Global instance
global_error_handler = GlobalErrorHandler()