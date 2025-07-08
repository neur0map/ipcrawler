"""
Result and execution models.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import json


class ExecutionResult(BaseModel):
    """Result of a single tool execution."""
    template_name: str = Field(..., max_length=100)
    tool: str = Field(..., max_length=50)
    target: str = Field(..., max_length=500)
    success: bool
    stdout: str = Field('', max_length=1024 * 1024)  # 1MB max
    stderr: str = Field('', max_length=1024 * 1024)  # 1MB max
    return_code: int
    execution_time: float = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = Field(None, max_length=1000)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ScanResult(BaseModel):
    """Collection of scan results for a target."""
    target: str = Field(..., max_length=500)
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_templates: int = Field(0, ge=0)
    successful_templates: int = Field(0, ge=0)
    failed_templates: int = Field(0, ge=0)
    results: List[ExecutionResult] = Field(default_factory=list, max_items=1000)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_templates == 0:
            return 0.0
        return (self.successful_templates / self.total_templates) * 100