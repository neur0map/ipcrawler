"""
Pydantic models for the ipcrawler port database.
Supports both current structure and enhanced CTF/HTB/OSCP features.
"""

from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
from datetime import date
import re


class ProtocolType(str, Enum):
    """Supported network protocols."""
    TCP = "tcp"
    UDP = "udp"
    TCP_UDP = "tcp/udp"


class ExposureType(str, Enum):
    """Service exposure classification."""
    EXTERNAL = "external"
    INTERNAL = "internal"
    BOTH = "both"


class RiskLevel(str, Enum):
    """Risk and priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ServiceCategory(str, Enum):
    """Service category classifications for CTF/HTB/OSCP."""
    # New CTF/HTB/OSCP focused categories
    WEB_APPLICATION = "web-application"
    DATABASE = "database"
    REMOTE_ACCESS = "remote-access"
    FILE_TRANSFER = "file-transfer"
    FILE_SHARING = "file-sharing"
    WINDOWS_INFRASTRUCTURE = "windows-infrastructure"
    LINUX_SERVICE = "linux-service"
    NETWORK_APPLIANCE = "network-appliance"
    IOT_DEVICE = "iot-device"
    SCADA_INDUSTRIAL = "scada-industrial"
    CLOUD_SERVICE = "cloud-service"
    
    # Existing categories for backwards compatibility
    MAIL_SERVICE = "mail-service"
    PRINT_SERVICE = "print-service"
    REMOTE_EXECUTION = "remote-execution"
    DIRECTORY_SERVICE = "directory-service"
    NETWORK_MANAGEMENT = "network-management"
    NETWORK_SERVICE = "network-service"  # Used in existing DB
    WEB_SERVICE = "web-service"          # Used in existing DB
    WINDOWS_SERVICE = "windows-service"  # Used in existing DB


class TechStack(BaseModel):
    """Technology stack information."""
    language: Optional[str] = Field(None, description="Primary implementation language")
    framework: Optional[str] = Field(None, description="Framework or server implementation")
    http_stack: Optional[str] = Field(None, description="HTTP stack if web-based")


class ServiceIndicators(BaseModel):
    """Detection indicators for the service."""
    ports: List[int] = Field(..., description="Associated port numbers")
    headers: List[str] = Field(default_factory=list, description="HTTP headers for detection")
    paths: List[str] = Field(default_factory=list, description="Common paths/endpoints")
    banners: List[str] = Field(default_factory=list, description="Service banners")

    @validator('ports')
    def validate_ports(cls, v):
        """Validate port numbers are in valid range."""
        for port in v:
            if not (1 <= port <= 65535):
                raise ValueError(f"Port {port} is not in valid range 1-65535")
        return v


class ServiceClassification(BaseModel):
    """Service classification for penetration testing."""
    category: ServiceCategory = Field(..., description="Service category")
    exposure: ExposureType = Field(..., description="Typical exposure level")
    auth_required: bool = Field(..., description="Whether authentication is typically required")
    misuse_potential: RiskLevel = Field(..., description="Potential for misuse/exploitation")


class AttackVectors(BaseModel):
    """Attack vectors and tools for CTF/HTB/OSCP scenarios."""
    primary: List[str] = Field(default_factory=list, description="Primary attack methods")
    secondary: List[str] = Field(default_factory=list, description="Secondary attack vectors")
    tools: List[str] = Field(default_factory=list, description="Recommended penetration testing tools")


class CTFScenarios(BaseModel):
    """CTF/HTB/OSCP scenario difficulty levels."""
    beginner: Optional[str] = Field(None, description="Common easy box scenarios")
    intermediate: Optional[str] = Field(None, description="Medium difficulty exploitation")
    advanced: Optional[str] = Field(None, description="Advanced attack chains")


class AssociatedWordlists(BaseModel):
    """Wordlists for penetration testing."""
    high: List[str] = Field(default_factory=list, description="High-priority specific wordlists")
    medium: List[str] = Field(default_factory=list, description="Medium-priority common wordlists")
    fallback: List[str] = Field(default_factory=list, description="Fallback generic wordlists")


class ExploitationPath(BaseModel):
    """Specific exploitation path information."""
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level (0.0-1.0)")
    risk: RiskLevel = Field(..., description="Risk level of this path")
    technique: str = Field(..., description="Exploitation technique/method")
    tools: List[str] = Field(default_factory=list, description="Tools for this exploitation path")


class PortEntry(BaseModel):
    """Complete port entry model for CTF/HTB/OSCP database."""
    
    # Core service information
    name: str = Field(..., description="Service name and description")
    protocol: ProtocolType = Field(..., description="Network protocol")
    default_service: str = Field(..., description="Default service name")
    alternative_services: List[str] = Field(default_factory=list, description="Alternative implementations")
    description: str = Field(..., description="Service description with CTF/HTB/OSCP context")
    
    # Technical details
    tech_stack: TechStack = Field(default_factory=TechStack, description="Technology stack")
    indicators: ServiceIndicators = Field(..., description="Detection indicators")
    classification: ServiceClassification = Field(..., description="Service classification")
    
    # CTF/HTB/OSCP enhancements
    attack_vectors: Optional[AttackVectors] = Field(None, description="Attack vectors and tools")
    ctf_scenarios: Optional[CTFScenarios] = Field(None, description="CTF scenario descriptions")
    
    # Penetration testing resources
    associated_wordlists: AssociatedWordlists = Field(default_factory=AssociatedWordlists)
    exploitation_paths: Dict[str, ExploitationPath] = Field(default_factory=dict, description="Exploitation paths")
    common_vulnerabilities: List[str] = Field(default_factory=list, description="Known vulnerabilities and CVEs")
    
    # Legacy support
    path_recommendations: Dict[str, Any] = Field(default_factory=dict, description="Legacy path recommendations")
    scoring_modifiers: Dict[str, float] = Field(default_factory=dict, description="Scoring adjustment factors")
    
    # Metadata
    last_updated: Union[str, date] = Field(..., description="Last update date")

    @validator('name')
    def validate_name(cls, v):
        """Ensure name is not empty and follows format."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator('description')
    def validate_description(cls, v):
        """Ensure description includes CTF/HTB/OSCP context."""
        if len(v) < 20:
            raise ValueError("Description must be at least 20 characters")
        return v

    @validator('scoring_modifiers')
    def validate_scoring_modifiers(cls, v):
        """Validate scoring modifier values."""
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Scoring modifier '{key}' must be numeric")
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"Scoring modifier '{key}' must be between 0.0 and 1.0")
        return v

    @validator('last_updated')
    def validate_last_updated(cls, v):
        """Validate and convert date format."""
        if isinstance(v, str):
            # Validate YYYY-MM-DD format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class PortDatabase(BaseModel):
    """Complete port database model."""
    ports: Dict[str, PortEntry] = Field(default_factory=dict, description="Port entries keyed by port number")

    @validator('ports')
    def validate_port_keys(cls, v):
        """Validate port keys are numeric and match port numbers in entries."""
        for port_key, port_entry in v.items():
            # Validate key is numeric
            if not port_key.isdigit():
                raise ValueError(f"Port key '{port_key}' must be numeric")
            
            # Validate key matches primary port in indicators
            port_num = int(port_key)
            if port_num not in port_entry.indicators.ports:
                raise ValueError(f"Port key '{port_key}' must be in indicators.ports")
        
        return v

    def get_port(self, port: Union[int, str]) -> Optional[PortEntry]:
        """Get a port entry by port number."""
        return self.ports.get(str(port))

    def add_port(self, port: Union[int, str], entry: PortEntry) -> None:
        """Add a new port entry."""
        port_str = str(port)
        
        # Ensure port is in indicators
        port_int = int(port_str)
        if port_int not in entry.indicators.ports:
            entry.indicators.ports.append(port_int)
        
        self.ports[port_str] = entry

    def get_ports_by_category(self, category: ServiceCategory) -> Dict[str, PortEntry]:
        """Get all ports in a specific category."""
        return {
            port: entry for port, entry in self.ports.items()
            if entry.classification.category == category
        }

    def get_ports_by_risk(self, risk: RiskLevel) -> Dict[str, PortEntry]:
        """Get all ports with specific risk level."""
        return {
            port: entry for port, entry in self.ports.items()
            if entry.classification.misuse_potential == risk
        }

    def get_external_ports(self) -> Dict[str, PortEntry]:
        """Get all externally exposed ports."""
        return {
            port: entry for port, entry in self.ports.items()
            if entry.classification.exposure in [ExposureType.EXTERNAL, ExposureType.BOTH]
        }

    def get_database_ports(self) -> Dict[str, PortEntry]:
        """Get all database-related ports for CTF/HTB/OSCP."""
        return self.get_ports_by_category(ServiceCategory.DATABASE)

    def get_web_ports(self) -> Dict[str, PortEntry]:
        """Get all web application ports."""
        return self.get_ports_by_category(ServiceCategory.WEB_APPLICATION)

    def get_remote_access_ports(self) -> Dict[str, PortEntry]:
        """Get all remote access ports."""
        return self.get_ports_by_category(ServiceCategory.REMOTE_ACCESS)

    def get_critical_ports(self) -> Dict[str, PortEntry]:
        """Get all critical risk ports."""
        return self.get_ports_by_risk(RiskLevel.CRITICAL)

    def get_completion_stats(self) -> Dict[str, Any]:
        """Get database completion statistics."""
        total_ports = len(self.ports)
        categories = {}
        risk_levels = {}
        
        for entry in self.ports.values():
            cat = entry.classification.category.value
            risk = entry.classification.misuse_potential.value
            categories[cat] = categories.get(cat, 0) + 1
            risk_levels[risk] = risk_levels.get(risk, 0) + 1
        
        return {
            "total_ports": total_ports,
            "target_ports": 100,
            "completion_percentage": round((total_ports / 100) * 100, 1),
            "categories": categories,
            "risk_levels": risk_levels
        }


# Utility functions for database operations

def load_port_database(json_data: Dict[str, Any]) -> PortDatabase:
    """Load port database from JSON data."""
    port_entries = {}
    
    for port_str, port_data in json_data.items():
        try:
            port_entries[port_str] = PortEntry(**port_data)
        except Exception as e:
            raise ValueError(f"Failed to parse port {port_str}: {e}")
    
    return PortDatabase(ports=port_entries)


def create_empty_port_entry(port: int, name: str, protocol: ProtocolType) -> PortEntry:
    """Create a minimal port entry template for new ports."""
    return PortEntry(
        name=name,
        protocol=protocol,
        default_service=name.lower().split()[0],
        description=f"{name} - CTF/HTB/OSCP context needed",
        indicators=ServiceIndicators(ports=[port]),
        classification=ServiceClassification(
            category=ServiceCategory.NETWORK_APPLIANCE,  # Default category
            exposure=ExposureType.EXTERNAL,
            auth_required=True,
            misuse_potential=RiskLevel.MEDIUM
        ),
        last_updated=date.today().isoformat()
    )


# Export all models and utilities
__all__ = [
    'ProtocolType', 'ExposureType', 'RiskLevel', 'ServiceCategory',
    'TechStack', 'ServiceIndicators', 'ServiceClassification',
    'AttackVectors', 'CTFScenarios', 'AssociatedWordlists', 'ExploitationPath',
    'PortEntry', 'PortDatabase',
    'load_port_database', 'create_empty_port_entry'
] 