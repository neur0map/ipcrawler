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
    args: Optional[List[str]] = Field(None, max_items=50)
    preset: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_.-]+$', max_length=100)
    variables: Optional[Dict[str, str]] = Field(None, max_items=10)
    description: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=20)
    tags: Optional[List[str]] = Field(None, max_items=10)
    dependencies: Optional[List[str]] = Field(None, max_items=10)
    env: Optional[Dict[str, str]] = Field(None, max_items=10)
    wordlist: Optional[str] = Field(None, max_length=500)
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
    
    @validator('wordlist')
    def validate_wordlist(cls, v):
        """Validate wordlist path."""
        if not v:
            return v
            
        # Validate wordlist path
        if len(v) > 500:
            raise ValueError('Wordlist path too long')
        # Basic path validation - no dangerous patterns
        if re.search(r'[;&|`$()<>]', v):
            raise ValueError('Wordlist path contains dangerous characters')
        
        return v
    
    @validator('preset')
    def validate_preset(cls, v):
        """Validate preset name format."""
        if not v:
            return v
            
        # Validate preset format (tool.preset_name or global_preset)
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Preset name contains invalid characters')
        
        # Limit total length
        if len(v) > 100:
            raise ValueError('Preset name too long')
            
        return v
    
    @validator('variables')
    def validate_variables(cls, v):
        """Validate custom variables for substitution."""
        if not v:
            return v
            
        for var_name, var_value in v.items():
            # Validate variable name
            if not re.match(r'^\w+$', var_name):
                raise ValueError(f'Invalid variable name: {var_name}')
            if len(var_name) > 50:
                raise ValueError(f'Variable name too long: {var_name}')
            
            # Validate variable value
            if len(str(var_value)) > 500:
                raise ValueError(f'Variable value too long: {var_name}')
            if re.search(r'[;&|`$()<>]', str(var_value)):
                raise ValueError(f'Variable value contains dangerous characters: {var_name}')
        
        return v
    
    @validator('args', always=True)
    def validate_args_or_preset_required(cls, v, values):
        """Ensure either args or preset is provided."""
        preset = values.get('preset')
        # Allow empty args if preset is provided, but not both empty
        if (not v or v == []) and not preset:
            raise ValueError('Either args or preset must be provided')
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