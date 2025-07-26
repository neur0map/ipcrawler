"""Base error handlers for IPCrawler

"""




    """Abstract base class for error handlers"""
    
    def __init__(self, logger: Optional[Any] = None):
        """Initialize error handler
        
        """
        self.logger = logger
        self.error_count = 0
        self.error_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle an error
        
            
        """
    
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
        
    
        """Get summary of handled errors"""
            'total_errors': self.error_count,
            'error_types': self._count_error_types(),
            'recent_errors': self.error_history[-10:]  # Last 10 errors
        }
    
        """Count errors by type"""
        counts = {}
            error_type = error['type']
            counts[error_type] = counts.get(error_type, 0) + 1


    """Error handler that chains multiple handlers"""
    
    def __init__(self, handlers: List[ErrorHandler], logger: Optional[Any] = None):
        """Initialize chained handler
        
        """
        self.handlers = handlers
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle error by trying each handler in sequence"""
        
                # Log handler failure but continue
        
    
        """Add a handler to the chain"""
    
        """Remove handlers of specific type"""
        self.handlers = [h for h in self.handlers if not isinstance(h, handler_type)]


    """Error handler that implements retry logic"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0, 
                 recoverable_errors: Optional[List[Type[Exception]]] = None,
                 logger: Optional[Any] = None):
        """Initialize retry handler
        
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.recoverable_errors = recoverable_errors or [RecoverableError]
        self.retry_counts: Dict[str, int] = {}
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle error with retry logic"""
        
        operation = context.get('operation', 'unknown') if context else 'unknown'
        retry_count = self.retry_counts.get(operation, 0)
        
        if retry_count >= self.max_retries:
        
        self.retry_counts[operation] = retry_count + 1
        
        # Calculate backoff
        wait_time = self.backoff_factor ** retry_count
        
        
        # Store retry info in context
            context['retry_count'] = retry_count + 1
            context['wait_time'] = wait_time
        
    
        """Check if error is recoverable"""
    
        """Reset retry count for an operation"""


    """Error handler that provides fallback behavior"""
    
                 logger: Optional[Any] = None):
        """Initialize fallback handler
        
        """
        self.fallback_actions = fallback_actions
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle error by executing fallback action"""
        error_type = type(error)
        
        # Check for exact match first
        
        # Check for subclass matches
        
    
        """Execute fallback action"""
    
        """Register a fallback action for an error type"""
        self.fallback_actions[error_type] = action


    """Global error handler for the application"""
    
    _instance = None
    
            cls._instance = super().__new__(cls)
    
            self.handlers: List[ErrorHandler] = []
            self.initialized = True
    
        """Register a global error handler"""
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle error using registered handlers"""
        
        # No handler could handle the error
    
        """Install global exception hook"""
            
            # Try to handle with registered handlers
                # Fall back to default behavior
        
        sys.excepthook = exception_hook


# Global instance
global_error_handler = GlobalErrorHandler()