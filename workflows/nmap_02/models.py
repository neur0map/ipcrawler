from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class NmapPort(BaseModel):
    """Model for nmap port information"""
    port: int
    protocol: str
    state: str
    service: Optional[str] = None
    version: Optional[str] = None
    product: Optional[str] = None
    extra_info: Optional[str] = None
    scripts: List[Dict[str, Any]] = Field(default_factory=list)
    cpe: List[str] = Field(default_factory=list)


class NmapHost(BaseModel):
    """Model for nmap host information"""
    ip: str
    hostname: Optional[str] = None
    state: str
    ports: List[NmapPort] = Field(default_factory=list)
    os: Optional[str] = None
    os_accuracy: Optional[int] = None
    os_details: List[Dict[str, Any]] = Field(default_factory=list)
    mac_address: Optional[str] = None
    mac_vendor: Optional[str] = None
    scripts: List[Dict[str, Any]] = Field(default_factory=list)
    traceroute: List[Dict[str, Any]] = Field(default_factory=list)
    uptime: Optional[str] = None
    distance: Optional[int] = None


class NmapScanResult(BaseModel):
    """Model for complete nmap scan results"""
    command: str
    scan_type: str
    start_time: str
    end_time: str
    duration: float
    hosts: List[NmapHost] = Field(default_factory=list)
    total_hosts: int = 0
    up_hosts: int = 0
    down_hosts: int = 0
    nmap_version: Optional[str] = None
    scan_args: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    scan_stats: Dict[str, Any] = Field(default_factory=dict)
    raw_output: Optional[str] = None