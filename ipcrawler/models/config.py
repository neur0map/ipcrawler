"""
Application configuration models.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class LoggingConfig(BaseModel):
    """Logging configuration."""
    silent: bool = True


class RetryConfig(BaseModel):
    """Retry configuration."""
    max_attempts: int = Field(3, ge=1, le=10)
    wait_multiplier: float = Field(1.0, ge=0.1, le=10.0)
    wait_max: int = Field(60, ge=1, le=300)


class SettingsConfig(BaseModel):
    """General settings configuration."""
    concurrent_limit: int = Field(10, ge=1, le=100)
    default_timeout: int = Field(60, ge=1, le=300)
    max_output_size: int = Field(1024 * 1024, ge=1024, le=100 * 1024 * 1024)  # 1KB to 100MB


class AppConfig(BaseModel):
    """Main application configuration."""
    templates: Dict[str, str] = Field({}, max_items=50)
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    
    @validator('templates')
    def validate_templates(cls, v):
        """Validate template mappings."""
        for key, value in v.items():
            if len(key) > 50 or len(value) > 100:
                raise ValueError('Template mapping key/value too long')
            if not key.replace('_', '').replace('-', '').isalnum():
                raise ValueError(f'Invalid template key: {key}')
        return v