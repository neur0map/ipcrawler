"""Common enums shared across IPCrawler

Centralized location for all shared enumerations.
"""

from src.core.models.base.model import SerializableEnum


class SeverityLevel(SerializableEnum):
    """Severity levels for findings and vulnerabilities"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    
    @property
    def priority(self) -> int:
        """Get numeric priority (higher = more severe)"""
        priorities = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "info": 1
        }
        return priorities.get(self.value, 0)
    
    @property
    def color(self) -> str:
        """Get color for display"""
        colors = {
            "critical": "red",
            "high": "orange",
            "medium": "yellow",
            "low": "blue",
            "info": "green"
        }
        return colors.get(self.value, "white")


class Confidence(SerializableEnum):
    """Confidence levels for detections"""
    CONFIRMED = "confirmed"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    POSSIBLE = "possible"
    
    @property
    def score(self) -> float:
        """Get numeric score (0.0 - 1.0)"""
        scores = {
            "confirmed": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "possible": 0.2
        }
        return scores.get(self.value, 0.0)


class PortState(SerializableEnum):
    """Port states for network scanning"""
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNFILTERED = "unfiltered"
    OPEN_FILTERED = "open|filtered"
    CLOSED_FILTERED = "closed|filtered"
    UNKNOWN = "unknown"


class Protocol(SerializableEnum):
    """Network protocols"""
    TCP = "tcp"
    UDP = "udp"
    SCTP = "sctp"
    ICMP = "icmp"
    UNKNOWN = "unknown"


class ServiceState(SerializableEnum):
    """Service states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"
    ERROR = "error"


class ScanType(SerializableEnum):
    """Types of scans"""
    FAST = "fast"
    DETAILED = "detailed"
    STEALTH = "stealth"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class DiscoveryMethod(SerializableEnum):
    """Methods of discovery"""
    ACTIVE = "active"
    PASSIVE = "passive"
    HYBRID = "hybrid"
    MANUAL = "manual"


class AuthType(SerializableEnum):
    """Authentication types"""
    NONE = "none"
    BASIC = "basic"
    DIGEST = "digest"
    NTLM = "ntlm"
    OAUTH = "oauth"
    API_KEY = "api_key"
    CERTIFICATE = "certificate"
    CUSTOM = "custom"


class TechnologyType(SerializableEnum):
    """Technology categories"""
    WEB_SERVER = "web_server"
    APPLICATION_SERVER = "application_server"
    DATABASE = "database"
    CMS = "cms"
    FRAMEWORK = "framework"
    LANGUAGE = "language"
    OPERATING_SYSTEM = "operating_system"
    DEVICE = "device"
    SERVICE = "service"
    LIBRARY = "library"
    PLUGIN = "plugin"
    OTHER = "other"


class VulnerabilityType(SerializableEnum):
    """Types of vulnerabilities"""
    INJECTION = "injection"
    XSS = "xss"
    CSRF = "csrf"
    AUTH = "authentication"
    ACCESS_CONTROL = "access_control"
    MISCONFIGURATION = "misconfiguration"
    EXPOSURE = "exposure"
    OUTDATED = "outdated"
    CRYPTOGRAPHY = "cryptography"
    VALIDATION = "validation"
    OTHER = "other"


class ReportFormat(SerializableEnum):
    """Report output formats"""
    JSON = "json"
    HTML = "html"
    TEXT = "txt"
    CSV = "csv"
    XML = "xml"
    PDF = "pdf"
    MARKDOWN = "md"


class LogLevel(SerializableEnum):
    """Logging levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    @property
    def numeric_level(self) -> int:
        """Get numeric logging level"""
        levels = {
            "debug": 10,
            "info": 20,
            "warning": 30,
            "error": 40,
            "critical": 50
        }
        return levels.get(self.value, 0)


class HTTPMethod(SerializableEnum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    TRACE = "TRACE"
    CONNECT = "CONNECT"


class HTTPStatus(SerializableEnum):
    """Common HTTP status codes"""
    OK = "200"
    CREATED = "201"
    NO_CONTENT = "204"
    MOVED_PERMANENTLY = "301"
    FOUND = "302"
    NOT_MODIFIED = "304"
    BAD_REQUEST = "400"
    UNAUTHORIZED = "401"
    FORBIDDEN = "403"
    NOT_FOUND = "404"
    METHOD_NOT_ALLOWED = "405"
    INTERNAL_ERROR = "500"
    BAD_GATEWAY = "502"
    SERVICE_UNAVAILABLE = "503"
    
    @property
    def is_success(self) -> bool:
        """Check if status indicates success"""
        return self.value.startswith("2")
    
    @property
    def is_redirect(self) -> bool:
        """Check if status indicates redirect"""
        return self.value.startswith("3")
    
    @property
    def is_client_error(self) -> bool:
        """Check if status indicates client error"""
        return self.value.startswith("4")
    
    @property
    def is_server_error(self) -> bool:
        """Check if status indicates server error"""
        return self.value.startswith("5")