"""
Pydantic validation models for IP Crawler project

This module provides validation for all data structures used throughout the project,
ensuring data integrity and type safety.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ScanStatus(str, Enum):
    """Scan status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PortState(str, Enum):
    """Port state enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"


class ServiceInfo(BaseModel):
    """Service information model"""
    name: str = Field(..., description="Service name")
    product: Optional[str] = Field(None, description="Product name")
    version: Optional[str] = Field(None, description="Product version")
    extra_info: Optional[str] = Field(None, description="Additional service information")


class PortInfo(BaseModel):
    """Port information model"""
    port: int = Field(..., ge=1, le=65535, description="Port number")
    protocol: str = Field("tcp", description="Protocol (tcp/udp)")
    state: PortState = Field(..., description="Port state")
    service: Optional[ServiceInfo] = Field(None, description="Service information")
    scripts: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Script results")


class HostInfo(BaseModel):
    """Host information model"""
    ip: str = Field(..., description="IP address")
    hostname: Optional[str] = Field(None, description="Hostname")
    ports: List[PortInfo] = Field(default_factory=list, description="Port information")
    os_info: Optional[Dict[str, Any]] = Field(None, description="OS detection information")


class ScanResult(BaseModel):
    """Base scan result model"""
    success: bool = Field(..., description="Whether the scan was successful")
    target: str = Field(..., description="Scan target")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Scan timestamp")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    data: Optional[Dict[str, Any]] = Field(None, description="Scan data")
    error: Optional[str] = Field(None, description="Error message if scan failed")


class FeroxbusterFinding(BaseModel):
    """Feroxbuster scan finding model"""
    url: str = Field(..., description="Found URL")
    status: int = Field(..., ge=100, le=599, description="HTTP status code")
    content_length: int = Field(..., ge=0, description="Content length in bytes")
    word_count: Optional[int] = Field(None, description="Word count")
    line_count: Optional[int] = Field(None, description="Line count")


class FeroxbusterResult(BaseModel):
    """Feroxbuster scan result model"""
    target: str = Field(..., description="Target URL")
    wordlist: str = Field(..., description="Wordlist used")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    score: float = Field(..., ge=0.0, description="Scoring result")
    matched_rules: List[str] = Field(default_factory=list, description="Matched scoring rules")
    findings: List[FeroxbusterFinding] = Field(default_factory=list, description="Scan findings")
    error: Optional[str] = Field(None, description="Error message if scan failed")


class WorkflowResult(BaseModel):
    """Workflow execution result model"""
    success: bool = Field(..., description="Whether the workflow was successful")
    workflow_name: str = Field(..., description="Name of the executed workflow")
    target: str = Field(..., description="Workflow target")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    data: Optional[Dict[str, Any]] = Field(None, description="Workflow data")
    error: Optional[str] = Field(None, description="Error message if workflow failed")
    status: ScanStatus = Field(ScanStatus.COMPLETED, description="Workflow status")

    @validator('execution_time')
    def validate_execution_time(cls, v):
        if v is not None and v < 0:
            raise ValueError('Execution time cannot be negative')
        return v


class ConfigValidation(BaseModel):
    """Configuration validation model"""
    version: str = Field(..., description="Application version")
    scan: Dict[str, Any] = Field(..., description="Scan settings")
    privileges: Dict[str, Any] = Field(..., description="Privilege settings")
    parallel: Dict[str, Any] = Field(..., description="Parallel processing settings")
    output: Dict[str, Any] = Field(..., description="Output settings")
    tools: Dict[str, Any] = Field(..., description="Tool paths")
    fuzzing: Dict[str, Any] = Field(..., description="Fuzzing settings")

    @validator('scan')
    def validate_scan_settings(cls, v):
        required_keys = ['fast_port_discovery', 'max_detailed_ports']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'Missing required scan setting: {key}')
        return v

    @validator('fuzzing')
    def validate_fuzzing_settings(cls, v):
        if 'enable_feroxbuster' not in v:
            raise ValueError('Missing required fuzzing setting: enable_feroxbuster')
        return v


def validate_scan_result(data: Dict[str, Any]) -> ScanResult:
    """Validate scan result data"""
    return ScanResult(**data)


def validate_workflow_result(data: Dict[str, Any]) -> WorkflowResult:
    """Validate workflow result data"""
    return WorkflowResult(**data)


def validate_feroxbuster_result(data: Dict[str, Any]) -> FeroxbusterResult:
    """Validate feroxbuster result data"""
    return FeroxbusterResult(**data)


def validate_config(config_data: Dict[str, Any]) -> ConfigValidation:
    """Validate configuration data"""
    return ConfigValidation(**config_data) 