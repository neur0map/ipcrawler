from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel
from .command_logger import log_workflow_start, log_workflow_end, log_command


class WorkflowResult(BaseModel):
    """Base model for workflow results"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    errors: Optional[list] = None  # For compatibility
    execution_time: Optional[float] = None


class BaseWorkflow(ABC):
    """Abstract base class for all workflows"""
    
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
    
    @abstractmethod
    async def execute(self, **kwargs) -> WorkflowResult:
        """Execute the workflow with given parameters"""
        pass
    
    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters"""
        pass