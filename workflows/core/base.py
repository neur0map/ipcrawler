from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
import datetime
from pydantic import BaseModel, Field
from .command_logger import log_workflow_start, log_workflow_end, log_command
from .exceptions import IPCrawlerError, ErrorSeverity
from .error_collector import collect_error, collect_exception


class ErrorDetail(BaseModel):
    """Structured error detail for WorkflowResult"""
    occurrence_id: str
    error_code: str
    message: str
    severity: str
    category: str
    workflow_name: str
    operation: str
    target: Optional[str] = None
    timestamp: str
    suggestions: List[str] = []


class WorkflowResult(BaseModel):
    """
    Enhanced workflow result model with structured error handling.
    
    Maintains backward compatibility while adding comprehensive error tracking.
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    
    # Enhanced error handling
    error_details: List[ErrorDetail] = Field(default_factory=list, description="Structured error information")
    
    # Backward compatibility fields
    error: Optional[str] = Field(None, description="Primary error message (for compatibility)")
    errors: Optional[List[str]] = Field(None, description="List of error messages (for compatibility)")
    
    @classmethod
    def success_result(
        cls, 
        data: Optional[Dict[str, Any]] = None, 
        execution_time: Optional[float] = None
    ) -> "WorkflowResult":
        """Create a successful workflow result"""
        return cls(
            success=True,
            data=data,
            execution_time=execution_time
        )
    
    @classmethod
    def error_result(
        cls,
        error: Union[str, IPCrawlerError, Exception],
        workflow_name: str,
        operation: str = "unknown",
        target: Optional[str] = None,
        execution_time: Optional[float] = None,
        **context_params
    ) -> "WorkflowResult":
        """
        Create an error workflow result with structured error handling.
        
        Args:
            error: Error message, IPCrawlerError, or generic Exception
            workflow_name: Name of the workflow that failed
            operation: Operation that failed
            target: Target being processed (optional)
            execution_time: Execution time before failure
            **context_params: Additional context parameters
        """
        result = cls(
            success=False,
            execution_time=execution_time
        )
        
        result.add_error(error, workflow_name, operation, target, **context_params)
        
        return result
    
    def add_error(
        self,
        error: Union[str, IPCrawlerError, Exception],
        workflow_name: str,
        operation: str = "unknown",
        target: Optional[str] = None,
        **context_params
    ) -> str:
        """
        Add an error to the result with automatic collection and structured storage.
        
        Returns:
            str: Occurrence ID of the collected error
        """
        if isinstance(error, str):
            # Create IPCrawlerError from string message
            from .exceptions import create_error_context
            context = create_error_context(workflow_name, operation, target, **context_params)
            ipc_error = IPCrawlerError(
                message=error,
                error_code="WORKFLOW_ERROR",
                severity=ErrorSeverity.ERROR,
                context=context
            )
        elif isinstance(error, IPCrawlerError):
            ipc_error = error
        else:
            # Handle generic exceptions
            occurrence_id = collect_exception(
                error, workflow_name, operation, target, **context_params
            )
            
            # Convert to simple error for compatibility
            self._update_compatibility_fields(str(error))
            
            # For generic exceptions, we can't easily create ErrorDetail without loading from collector
            # So we'll add a simplified error detail
            error_detail = ErrorDetail(
                occurrence_id=occurrence_id,
                error_code="UNKNOWN_ERROR",
                message=str(error),
                severity="error",
                category="unknown",
                workflow_name=workflow_name,
                operation=operation,
                target=target,
                timestamp=datetime.datetime.now().isoformat(),
                suggestions=[]
            )
            self.error_details.append(error_detail)
            return occurrence_id
        
        # Collect the IPCrawlerError
        occurrence_id = collect_error(ipc_error)
        
        # Create structured error detail
        error_detail = ErrorDetail(
            occurrence_id=occurrence_id,
            error_code=ipc_error.error_code,
            message=ipc_error.message,
            severity=ipc_error.severity.value,
            category=ipc_error.category.value,
            workflow_name=ipc_error.context.workflow_name,
            operation=ipc_error.context.operation,
            target=ipc_error.context.target,
            timestamp=ipc_error.timestamp.isoformat(),
            suggestions=ipc_error.suggestions
        )
        
        self.error_details.append(error_detail)
        
        # Update compatibility fields
        self._update_compatibility_fields(ipc_error.message)
        
        # Mark as failed
        self.success = False
        
        return occurrence_id
    
    def _update_compatibility_fields(self, error_message: str):
        """Update backward compatibility error fields"""
        # Set primary error (first error or most recent)
        if not self.error:
            self.error = error_message
        
        # Add to errors list
        if self.errors is None:
            self.errors = []
        self.errors.append(error_message)
    
    def has_critical_errors(self) -> bool:
        """Check if result contains critical errors"""
        return any(
            detail.severity == ErrorSeverity.CRITICAL.value 
            for detail in self.error_details
        )
    
    def get_error_summary(self) -> str:
        """Get a summary of all errors"""
        if not self.error_details:
            return self.error or "Unknown error"
        
        if len(self.error_details) == 1:
            return self.error_details[0].message
        
        summary_parts = []
        by_category = {}
        
        for detail in self.error_details:
            category = detail.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(detail)
        
        for category, details in by_category.items():
            if len(details) == 1:
                summary_parts.append(f"{category}: {details[0].message}")
            else:
                summary_parts.append(f"{category}: {len(details)} errors")
        
        return "; ".join(summary_parts)
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy result format for backward compatibility"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "errors": self.errors,
            "execution_time": self.execution_time
        }


class BaseWorkflow(ABC):
    """
    Abstract base class for all workflows with enhanced error handling.
    
    Provides structured error handling, logging integration, and 
    standardized workflow execution patterns.
    """
    
    def __init__(self, name: str):
        self.name = name
    
    def log_command(self, command: str, status: str = "started", output: Optional[str] = None, error: Optional[str] = None):
        """Log a command execution"""
        log_command(self.name, command, status, output, error)
    
    def log_start(self, target: Optional[str] = None):
        """Log workflow start"""
        log_workflow_start(self.name, target)
    
    def log_end(self, success: bool, execution_time: Optional[float] = None):
        """Log workflow end"""
        log_workflow_end(self.name, success, execution_time)
    
    def create_success_result(
        self, 
        data: Optional[Dict[str, Any]] = None, 
        execution_time: Optional[float] = None
    ) -> WorkflowResult:
        """Create a successful workflow result"""
        return WorkflowResult.success_result(data, execution_time)
    
    def create_error_result(
        self,
        error: Union[str, IPCrawlerError, Exception],
        operation: str = "execute",
        target: Optional[str] = None,
        execution_time: Optional[float] = None,
        **context_params
    ) -> WorkflowResult:
        """Create an error workflow result with structured error handling"""
        return WorkflowResult.error_result(
            error=error,
            workflow_name=self.name,
            operation=operation,
            target=target,
            execution_time=execution_time,
            **context_params
        )
    
    def handle_exception(
        self,
        exc: Exception,
        operation: str = "execute",
        target: Optional[str] = None,
        **context_params
    ) -> WorkflowResult:
        """
        Handle exceptions and convert them to structured error results.
        
        This method should be used in try-except blocks to ensure
        consistent error handling across all workflows.
        """
        return self.create_error_result(
            error=exc,
            operation=operation,
            target=target,
            **context_params
        )
    
    async def safe_execute(self, **kwargs) -> WorkflowResult:
        """
        Safe execution wrapper with automatic error handling.
        
        This method wraps the execute() method with try-catch logic
        to ensure that all exceptions are properly handled and structured.
        """
        start_time = datetime.datetime.now()
        target = kwargs.get('target', 'unknown')
        
        try:
            # Log workflow start
            self.log_start(target)
            
            # Validate input first
            if not self.validate_input(**kwargs):
                return self.create_error_result(
                    error="Input validation failed",
                    operation="input_validation",
                    target=target
                )
            
            # Execute the workflow
            result = await self.execute(**kwargs)
            
            # Calculate execution time
            execution_time = (datetime.datetime.now() - start_time).total_seconds()
            
            # Update execution time if not already set
            if result.execution_time is None:
                result.execution_time = execution_time
            
            # Log workflow end
            self.log_end(result.success, execution_time)
            
            return result
            
        except Exception as exc:
            # Calculate execution time
            execution_time = (datetime.datetime.now() - start_time).total_seconds()
            
            # Log workflow end as failed
            self.log_end(False, execution_time)
            
            # Handle the exception
            return self.handle_exception(
                exc=exc,
                operation="execute",
                target=target,
                execution_time=execution_time,
                **kwargs
            )
    
    @abstractmethod
    async def execute(self, **kwargs) -> WorkflowResult:
        """
        Execute the workflow with given parameters.
        
        This method should contain the core workflow logic.
        Use create_success_result() and create_error_result() 
        to return structured results.
        """
        pass
    
    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """
        Validate input parameters.
        
        Returns:
            bool: True if input is valid, False otherwise
        """
        pass