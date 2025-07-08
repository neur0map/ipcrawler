"""
Template data models with strict security validation.
"""

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator
import re


class ToolTemplate(BaseModel):
    """Secure template definition for a security tool."""
    name: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$', max_length=100)
    tool: str = Field(..., pattern=r'^[a-zA-Z0-9_/-]+$', max_length=50)
    args: List[str] = Field(..., max_items=50)
    description: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=20)
    tags: Optional[List[str]] = Field(None, max_items=10)
    dependencies: Optional[List[str]] = Field(None, max_items=10)
    env: Optional[Dict[str, str]] = Field(None, max_items=10)
    timeout: int = Field(60, ge=1, le=300)
    target_types: Optional[List[str]] = Field(None, max_items=5)
    severity: Optional[Literal['low', 'medium', 'high']] = None
    stealth: Optional[bool] = None
    parallel_safe: Optional[bool] = True
    
    @validator('tool')
    def validate_tool(cls, v):
        """Validate tool name contains only safe characters."""
        if not re.match(r'^[a-zA-Z0-9_/-]+$', v):
            raise ValueError('Tool name contains invalid characters')
        return v
    
    @validator('args', each_item=True)
    def validate_args(cls, v):
        """Validate each argument for security."""
        # Reject dangerous characters and patterns
        dangerous_patterns = [
            r'[;&|`$()]',  # Shell metacharacters
            r'\.\./',      # Directory traversal
            r'[<>]',       # Redirection operators
            r'^\s*$',      # Empty/whitespace only
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError(f'Argument contains dangerous pattern: {pattern}')
        
        # Limit argument length
        if len(v) > 1000:
            raise ValueError('Argument too long')
            
        return v
    
    @validator('env')
    def validate_env(cls, v):
        """Validate environment variables."""
        if not v:
            return v
            
        for key, value in v.items():
            if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                raise ValueError(f'Invalid environment variable name: {key}')
            if len(value) > 1000:
                raise ValueError(f'Environment variable value too long: {key}')
        
        return v


class TemplateConfig(BaseModel):
    """Configuration for template discovery and loading."""
    base_path: str = Field(..., max_length=500)
    allowed_extensions: List[str] = Field(['.json'], max_items=5)
    max_template_size: int = Field(1024 * 1024, ge=1024, le=10 * 1024 * 1024)  # 1KB to 10MB
    validate_on_load: bool = True
    
    @validator('allowed_extensions', each_item=True)
    def validate_extensions(cls, v):
        """Validate file extensions."""
        if not v.startswith('.'):
            raise ValueError('Extension must start with dot')
        if not re.match(r'^\.[a-z]+$', v):
            raise ValueError('Extension contains invalid characters')
        return v