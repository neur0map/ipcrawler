"""Base exception classes for IPCrawler

Provides a hierarchy of custom exceptions for better error handling.
"""

from typing import Optional, Dict, Any


class IPCrawlerError(Exception):
    """Base exception for all IPCrawler errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class WorkflowError(IPCrawlerError):
    """Base exception for workflow-related errors"""
    
    def __init__(self, workflow: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize workflow exception
        
        Args:
            workflow: Workflow name
            message: Error message
            details: Additional error details
        """
        super().__init__(f"[{workflow}] {message}", details)
        self.workflow = workflow


class ConfigurationError(IPCrawlerError):
    """Exception for configuration-related errors"""
    pass


class ValidationError(IPCrawlerError):
    """Exception for validation errors"""
    
    def __init__(self, field: str, value: Any, message: str):
        """Initialize validation exception
        
        Args:
            field: Field that failed validation
            value: Invalid value
            message: Error message
        """
        details = {'field': field, 'value': value}
        super().__init__(f"Validation failed for {field}: {message}", details)
        self.field = field
        self.value = value


class NetworkError(IPCrawlerError):
    """Exception for network-related errors"""
    
    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None):
        """Initialize network exception
        
        Args:
            message: Error message
            host: Target host
            port: Target port
        """
        details = {}
        if host:
            details['host'] = host
        if port:
            details['port'] = port
        super().__init__(message, details)


class ToolError(IPCrawlerError):
    """Exception for external tool errors"""
    
    def __init__(self, tool: str, message: str, return_code: Optional[int] = None):
        """Initialize tool exception
        
        Args:
            tool: Tool name
            message: Error message
            return_code: Tool return code
        """
        details = {'tool': tool}
        if return_code is not None:
            details['return_code'] = return_code
        super().__init__(f"Tool '{tool}' error: {message}", details)
        self.tool = tool
        self.return_code = return_code


class ScanError(WorkflowError):
    """Exception for scan-related errors"""
    pass


class ReportError(IPCrawlerError):
    """Exception for report generation errors"""
    pass


class DataError(IPCrawlerError):
    """Exception for data processing errors"""
    pass


class TimeoutError(IPCrawlerError):
    """Exception for timeout errors"""
    
    def __init__(self, operation: str, timeout: float):
        """Initialize timeout exception
        
        Args:
            operation: Operation that timed out
            timeout: Timeout value in seconds
        """
        super().__init__(
            f"Operation '{operation}' timed out after {timeout} seconds",
            {'operation': operation, 'timeout': timeout}
        )
        self.operation = operation
        self.timeout = timeout


class DependencyError(IPCrawlerError):
    """Exception for missing dependencies"""
    
    def __init__(self, dependency: str, required_by: str):
        """Initialize dependency exception
        
        Args:
            dependency: Missing dependency
            required_by: Component requiring the dependency
        """
        super().__init__(
            f"Missing dependency '{dependency}' required by {required_by}",
            {'dependency': dependency, 'required_by': required_by}
        )
        self.dependency = dependency
        self.required_by = required_by


class RecoverableError(IPCrawlerError):
    """Base class for recoverable errors"""
    
    def __init__(self, message: str, recovery_action: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Initialize recoverable exception
        
        Args:
            message: Error message
            recovery_action: Suggested recovery action
            details: Additional error details
        """
        super().__init__(message, details)
        self.recovery_action = recovery_action