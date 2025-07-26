"""Base exception classes for IPCrawler

"""



    """Base exception for all IPCrawler errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize exception
        
        """
        self.message = message
        self.details = details or {}
    


    """Base exception for workflow-related errors"""
    
    def __init__(self, workflow: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize workflow exception
        
        """
        self.workflow = workflow


    """Exception for configuration-related errors"""


    """Exception for validation errors"""
    
        """Initialize validation exception
        
        """
        details = {'field': field, 'value': value}
        self.field = field
        self.value = value


    """Exception for network-related errors"""
    
    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None):
        """Initialize network exception
        
        """
        details = {}
            details['host'] = host
            details['port'] = port


    """Exception for external tool errors"""
    
    def __init__(self, tool: str, message: str, return_code: Optional[int] = None):
        """Initialize tool exception
        
        """
        details = {'tool': tool}
            details['return_code'] = return_code
        self.tool = tool
        self.return_code = return_code


    """Exception for scan-related errors"""


    """Exception for report generation errors"""


    """Exception for data processing errors"""


    """Exception for timeout errors"""
    
        """Initialize timeout exception
        
        """
            {'operation': operation, 'timeout': timeout}
        )
        self.operation = operation
        self.timeout = timeout


    """Exception for missing dependencies"""
    
        """Initialize dependency exception
        
        """
            {'dependency': dependency, 'required_by': required_by}
        )
        self.dependency = dependency
        self.required_by = required_by


    """Base class for recoverable errors"""
    
    def __init__(self, message: str, recovery_action: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Initialize recoverable exception
        
        """
        self.recovery_action = recovery_action