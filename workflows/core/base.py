from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


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
    
    @abstractmethod
    async def execute(self, **kwargs) -> WorkflowResult:
        """Execute the workflow with given parameters"""
        pass
    
    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters"""
        pass