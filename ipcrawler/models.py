#!/usr/bin/env python3

"""
Pydantic Models for IPCrawler Report Validation

This module defines the schema for validating parsed.yaml files generated
by Phase 2 parsing. Ensures data consistency and prepares for report rendering.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
import re


class Port(BaseModel):
    """Model for network port information from nmap scans."""
    port: int = Field(..., ge=1, le=65535, description="Port number (1-65535)")
    service: str = Field(..., min_length=1, description="Service name")
    version: str = Field(default="", description="Service version information")
    
    @validator('service')
    def service_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError('Service name cannot be empty')
        return v.strip()


class Endpoint(BaseModel):
    """Model for web endpoints discovered via directory enumeration."""
    path: str = Field(..., min_length=1, description="URL path")
    status: int = Field(..., ge=100, le=599, description="HTTP status code")
    size: int = Field(..., ge=0, description="Response size in bytes")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    
    @validator('path')
    def path_must_start_with_slash(cls, v):
        if not v.startswith('/'):
            raise ValueError('Path must start with /')
        return v


class CMS(BaseModel):
    """Model for Content Management System detection."""
    name: str = Field(..., min_length=1, description="CMS name")
    confidence: str = Field(..., description="Detection confidence or version")
    
    @validator('name')
    def name_must_be_valid_cms(cls, v):
        valid_cms = ['WordPress', 'Drupal', 'Joomla', 'Magento', 'Shopify', 'Wix', 'Squarespace']
        if v not in valid_cms:
            # Allow any CMS name but ensure it's not empty
            if not v or v.strip() == "":
                raise ValueError('CMS name cannot be empty')
        return v.strip()


class ErrorEntry(BaseModel):
    """Model for plugin execution errors."""
    plugin: str = Field(..., min_length=1, description="Plugin name that generated the error")
    message: str = Field(..., min_length=1, description="Error message")
    severity: Literal['high', 'medium', 'low'] = Field(default='medium', description="Error severity level")
    command: Optional[str] = Field(default=None, description="Command that caused the error")
    exit_code: Optional[int] = Field(default=None, description="Exit code of failed command")
    timestamp: Optional[str] = Field(default=None, description="Error timestamp")
    target: Optional[str] = Field(default=None, description="Target associated with error")


class Summary(BaseModel):
    """Model for scan summary statistics."""
    tools_run: int = Field(..., ge=0, description="Number of tools executed")
    errors: int = Field(..., ge=0, description="Total number of errors")
    endpoints_found: int = Field(..., ge=0, description="Number of endpoints discovered")
    cms_detected: Optional[str] = Field(default=None, description="Detected CMS name")
    ports_open: int = Field(..., ge=0, description="Number of open ports found")


class IPCrawlerReport(BaseModel):
    """Main model for the complete IPCrawler scan report."""
    target: str = Field(..., min_length=1, description="Target IP address or hostname")
    date: str = Field(..., description="Scan date in YYYY-MM-DD format")
    ports: List[Port] = Field(default_factory=list, description="List of discovered ports")
    endpoints: List[Endpoint] = Field(default_factory=list, description="List of discovered endpoints")
    cms: Optional[CMS] = Field(default=None, description="Detected CMS information")
    errors: List[ErrorEntry] = Field(default_factory=list, description="List of errors encountered")
    summary: Summary = Field(..., description="Scan summary statistics")
    
    @validator('date')
    def date_must_be_valid_format(cls, v):
        # Validate YYYY-MM-DD format
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(date_pattern, v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v
    
    @validator('target')
    def target_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError('Target cannot be empty')
        return v.strip()
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"  # Reject extra fields not defined in schema