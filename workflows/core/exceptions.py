"""
Enhanced error handling system for IPCrawler workflows.

This module provides a comprehensive error hierarchy with structured error objects,
severity levels, and detailed context capture for improved debugging and error recovery.
"""

import datetime
import traceback
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    CRITICAL = "critical"  # System-breaking errors
    ERROR = "error"       # Workflow-blocking errors  
    WARNING = "warning"   # Non-blocking issues
    INFO = "info"         # Informational messages


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    NETWORK = "network"           # Network connectivity, DNS, timeouts
    VALIDATION = "validation"     # Input validation, parameter errors
    TOOL = "tool"                # External tool execution failures
    CONFIGURATION = "configuration"  # Config file, environment issues
    FILESYSTEM = "filesystem"    # File I/O, permissions, disk space
    AUTHENTICATION = "authentication"  # Auth, credentials, permissions
    RESOURCE = "resource"        # Memory, CPU, disk space limits
    PARSING = "parsing"          # XML, JSON, output parsing errors
    DEPENDENCY = "dependency"    # Missing dependencies, imports
    WORKFLOW = "workflow"        # Workflow logic, sequencing errors
    UNKNOWN = "unknown"          # Unclassified errors


class ErrorContext(BaseModel):
    """Detailed error context information"""
    workflow_name: str
    operation: str
    target: Optional[str] = None
    parameters: Dict[str, Any] = {}
    timestamp: datetime.datetime = datetime.datetime.now()
    stack_trace: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat()
        }


class IPCrawlerError(Exception):
    """
    Base exception class for all IPCrawler errors.
    
    Provides structured error information with severity, category, and context.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext(workflow_name="unknown", operation="unknown")
        self.cause = cause
        self.suggestions = suggestions or []
        self.timestamp = datetime.datetime.now()
        
        # Capture stack trace
        if not self.context.stack_trace:
            self.context.stack_trace = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization"""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context.model_dump() if self.context else None,
            "cause": str(self.cause) if self.cause else None,
            "suggestions": self.suggestions,
            "type": self.__class__.__name__
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class NetworkError(IPCrawlerError):
    """Network-related errors (connectivity, DNS, timeouts)"""
    
    def __init__(self, message: str, error_code: str = "NET_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.NETWORK,
            **kwargs
        )


class ValidationError(IPCrawlerError):
    """Input validation and parameter errors"""
    
    def __init__(self, message: str, error_code: str = "VAL_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.VALIDATION,
            **kwargs
        )


class ToolExecutionError(IPCrawlerError):
    """External tool execution failures"""
    
    def __init__(self, message: str, tool_name: str, error_code: str = "TOOL_ERROR", **kwargs):
        self.tool_name = tool_name
        super().__init__(
            message=f"{tool_name}: {message}",
            error_code=error_code,
            category=ErrorCategory.TOOL,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["tool_name"] = self.tool_name
        return result


class ConfigurationError(IPCrawlerError):
    """Configuration and environment errors"""
    
    def __init__(self, message: str, error_code: str = "CFG_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.CONFIGURATION,
            **kwargs
        )


class FilesystemError(IPCrawlerError):
    """Filesystem, I/O, and permission errors"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, error_code: str = "FS_ERROR", **kwargs):
        self.file_path = file_path
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.FILESYSTEM,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["file_path"] = self.file_path
        return result


class AuthenticationError(IPCrawlerError):
    """Authentication and authorization errors"""
    
    def __init__(self, message: str, error_code: str = "AUTH_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


class ResourceError(IPCrawlerError):
    """Resource exhaustion errors (memory, CPU, disk)"""
    
    def __init__(self, message: str, resource_type: str, error_code: str = "RES_ERROR", **kwargs):
        self.resource_type = resource_type
        super().__init__(
            message=f"{resource_type} resource error: {message}",
            error_code=error_code,
            category=ErrorCategory.RESOURCE,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["resource_type"] = self.resource_type
        return result


class ParsingError(IPCrawlerError):
    """Data parsing and format errors"""
    
    def __init__(self, message: str, data_format: str, error_code: str = "PARSE_ERROR", **kwargs):
        self.data_format = data_format
        super().__init__(
            message=f"{data_format} parsing error: {message}",
            error_code=error_code,
            category=ErrorCategory.PARSING,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["data_format"] = self.data_format
        return result


class DependencyError(IPCrawlerError):
    """Missing dependency and import errors"""
    
    def __init__(self, message: str, dependency_name: str, error_code: str = "DEP_ERROR", **kwargs):
        self.dependency_name = dependency_name
        super().__init__(
            message=f"Dependency '{dependency_name}': {message}",
            error_code=error_code,
            category=ErrorCategory.DEPENDENCY,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["dependency_name"] = self.dependency_name
        return result


class WorkflowError(IPCrawlerError):
    """Workflow logic and sequencing errors"""
    
    def __init__(self, message: str, workflow_stage: str, error_code: str = "WF_ERROR", **kwargs):
        self.workflow_stage = workflow_stage
        super().__init__(
            message=f"Workflow stage '{workflow_stage}': {message}",
            error_code=error_code,
            category=ErrorCategory.WORKFLOW,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["workflow_stage"] = self.workflow_stage
        return result


# Common error code constants
class ErrorCodes:
    """Standard error codes for consistent error handling"""
    
    # Network errors
    NETWORK_TIMEOUT = "NET_TIMEOUT"
    DNS_RESOLUTION_FAILED = "NET_DNS_FAIL"
    CONNECTION_REFUSED = "NET_CONN_REFUSED"
    NETWORK_UNREACHABLE = "NET_UNREACHABLE"
    
    # Tool errors
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_FAILED = "TOOL_EXEC_FAIL"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_PERMISSION_DENIED = "TOOL_PERM_DENIED"
    
    # Validation errors
    INVALID_TARGET = "VAL_INVALID_TARGET"
    INVALID_PORT_RANGE = "VAL_INVALID_PORT"
    MISSING_REQUIRED_PARAM = "VAL_MISSING_PARAM"
    
    # Configuration errors
    CONFIG_FILE_NOT_FOUND = "CFG_FILE_NOT_FOUND"
    CONFIG_PARSE_ERROR = "CFG_PARSE_ERROR"
    INVALID_CONFIG_VALUE = "CFG_INVALID_VALUE"
    
    # Filesystem errors
    FILE_NOT_FOUND = "FS_FILE_NOT_FOUND"
    PERMISSION_DENIED = "FS_PERM_DENIED"
    DISK_FULL = "FS_DISK_FULL"
    
    # Parsing errors
    XML_PARSE_ERROR = "PARSE_XML_ERROR"
    JSON_PARSE_ERROR = "PARSE_JSON_ERROR"
    OUTPUT_PARSE_ERROR = "PARSE_OUTPUT_ERROR"


def create_error_context(
    workflow_name: str,
    operation: str,
    target: Optional[str] = None,
    **parameters
) -> ErrorContext:
    """Helper function to create error context"""
    return ErrorContext(
        workflow_name=workflow_name,
        operation=operation,
        target=target,
        parameters=parameters
    )


def handle_exception(
    exc: Exception,
    workflow_name: str,
    operation: str,
    target: Optional[str] = None,
    **parameters
) -> IPCrawlerError:
    """
    Convert generic exceptions to IPCrawlerError with proper categorization.
    
    This function analyzes the exception type and message to determine
    the appropriate error category and provides structured error information.
    """
    context = create_error_context(workflow_name, operation, target, **parameters)
    
    # Map common exception types to IPCrawler errors
    if isinstance(exc, FileNotFoundError):
        return FilesystemError(
            message=str(exc),
            file_path=getattr(exc, 'filename', None),
            error_code=ErrorCodes.FILE_NOT_FOUND,
            context=context,
            cause=exc
        )
    
    elif isinstance(exc, PermissionError):
        return FilesystemError(
            message=str(exc),
            file_path=getattr(exc, 'filename', None),
            error_code=ErrorCodes.PERMISSION_DENIED,
            context=context,
            cause=exc
        )
    
    elif isinstance(exc, ImportError):
        return DependencyError(
            message=str(exc),
            dependency_name=getattr(exc, 'name', 'unknown'),
            error_code="DEP_IMPORT_ERROR",
            context=context,
            cause=exc
        )
    
    elif isinstance(exc, (ConnectionError, OSError)):
        return NetworkError(
            message=str(exc),
            error_code=ErrorCodes.CONNECTION_REFUSED,
            context=context,
            cause=exc
        )
    
    elif isinstance(exc, TimeoutError):
        return NetworkError(
            message=str(exc),
            error_code=ErrorCodes.NETWORK_TIMEOUT,
            context=context,
            cause=exc
        )
    
    elif isinstance(exc, ValueError):
        return ValidationError(
            message=str(exc),
            error_code="VAL_VALUE_ERROR",
            context=context,
            cause=exc
        )
    
    else:
        # Generic fallback for unknown exceptions
        return IPCrawlerError(
            message=str(exc),
            error_code="UNKNOWN_ERROR",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.UNKNOWN,
            context=context,
            cause=exc
        )