"""Common enums shared across IPCrawler"""

from enum import Enum


class SeverityLevel(Enum):
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
    
    def __str__(self) -> str:
        return self.value


class ScanStatus(Enum):
    """Status of scan operations"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    def __str__(self) -> str:
        return self.value


class PortState(Enum):
    """Port states from nmap scanning"""
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNFILTERED = "unfiltered"
    OPEN_FILTERED = "open|filtered"
    CLOSED_FILTERED = "closed|filtered"
    
    def __str__(self) -> str:
        return self.value