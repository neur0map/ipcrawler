"""
Pydantic models for wordlist configuration and validation
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
from pathlib import Path
import os


class ServiceType(str, Enum):
    """Enumeration of service types for wordlist recommendations"""
    SSH = "ssh"
    FTP = "ftp"
    HTTP = "http"
    HTTPS = "https"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MSSQL = "mssql"
    MONGODB = "mongodb"
    REDIS = "redis"
    SMTP = "smtp"
    POP3 = "pop3"
    IMAP = "imap"
    DNS = "dns"
    LDAP = "ldap"
    SMB = "smb"
    RDP = "rdp"
    TELNET = "telnet"
    UNKNOWN = "unknown"


class WordlistCategory(str, Enum):
    """Categories of wordlists for different attack types"""
    PASSWORDS = "passwords"
    USERNAMES = "usernames"
    CREDENTIALS = "credentials"
    DIRECTORIES = "directories"
    FILES = "files"
    SUBDOMAINS = "subdomains"
    FUZZING = "fuzzing"
    XSS = "xss"
    SQLI = "sqli"
    LANGUAGES = "languages"
    USER_AGENTS = "user_agents"
    EXTENSIONS = "extensions"


class WordlistPattern(BaseModel):
    """Pattern matching configuration for wordlist appropriateness"""
    pattern: str = Field(..., description="Pattern to match in wordlist path")
    category: WordlistCategory = Field(..., description="Category this pattern belongs to")
    appropriate_for: List[ServiceType] = Field(..., description="Services this pattern is appropriate for")
    inappropriate_for: List[ServiceType] = Field(default_factory=list, description="Services this pattern is inappropriate for")
    priority: int = Field(default=1, description="Priority (1=highest, 5=lowest)")


class ServiceWordlistConfig(BaseModel):
    """Configuration for service-specific wordlist recommendations"""
    service_type: ServiceType
    preferred_categories: List[WordlistCategory] = Field(..., description="Preferred wordlist categories for this service")
    fallback_wordlists: List[str] = Field(..., description="Fallback wordlist paths if none found")
    inappropriate_patterns: List[str] = Field(default_factory=list, description="Patterns to avoid for this service")
    tools: List[str] = Field(..., description="Recommended tools for this service")


def load_seclists_paths() -> List[str]:
    """Load SecLists paths from .seclists_path file or return common fallbacks"""
    # Try to read from the generated .seclists_path file
    seclists_path_file = Path(".seclists_path")
    detected_path = None
    
    if seclists_path_file.exists():
        try:
            content = seclists_path_file.read_text().strip()
            for line in content.split('\n'):
                if line.startswith('SECLISTS_PATH='):
                    detected_path = line.split('=', 1)[1].strip('"\'')
                    break
        except Exception:
            pass
    
    # Common SecLists locations in order of preference
    common_paths = [
        "/usr/share/seclists",                    # HTB/Kali standard
        "/usr/share/SecLists",                    # Alternative system location
        "/opt/seclists",                          # Alternative system location
        "/opt/SecLists",                          # Alternative system location
        "/usr/share/wordlists/seclists",          # Some distros
        "/usr/local/share/seclists",              # Local installation
        "/usr/local/share/SecLists",              # Local installation
        os.path.expanduser("~/SecLists"),         # User installation
        os.path.expanduser("~/.local/share/SecLists")  # User local
    ]
    
    # If we detected a path, put it first
    if detected_path and detected_path != "":
        return [detected_path] + [p for p in common_paths if p != detected_path]
    
    return common_paths


def get_wordlist_paths(service_type: ServiceType, detected_seclists_path: str = None) -> List[str]:
    """Generate wordlist paths based on detected SecLists installation"""
    if not detected_seclists_path:
        # Try to load from .seclists_path file
        paths = load_seclists_paths()
        detected_seclists_path = paths[0] if paths else "/usr/share/seclists"
    
    base_path = detected_seclists_path
    
    if service_type == ServiceType.SSH:
        return [
            f"{base_path}/Passwords/Default-Credentials/ssh-betterdefaultpasslist.txt",
            f"{base_path}/Passwords/Common-Credentials/top-20-common-SSH-passwords.txt",
            f"{base_path}/Passwords/Common-Credentials/10-million-password-list-top-1000.txt",
            "/usr/share/wordlists/rockyou.txt",  # Common fallback
            f"{base_path}/Passwords/Leaked-Databases/rockyou.txt"
        ]
    elif service_type == ServiceType.FTP:
        return [
            f"{base_path}/Passwords/Default-Credentials/ftp-betterdefaultpasslist.txt",
            f"{base_path}/Passwords/Common-Credentials/10-million-password-list-top-1000.txt",
            "/usr/share/wordlists/rockyou.txt",  # Common fallback
            f"{base_path}/Passwords/Leaked-Databases/rockyou.txt"
        ]
    elif service_type in [ServiceType.HTTP, ServiceType.HTTPS]:
        return [
            f"{base_path}/Discovery/Web-Content/common.txt",
            f"{base_path}/Discovery/Web-Content/directory-list-2.3-medium.txt",
            f"{base_path}/Discovery/Web-Content/big.txt",
            f"{base_path}/Discovery/Web-Content/raft-medium-directories.txt"
        ]
    else:
        # Generic password lists for other services
        return [
            f"{base_path}/Passwords/Common-Credentials/10-million-password-list-top-1000.txt",
            "/usr/share/wordlists/rockyou.txt",
            f"{base_path}/Passwords/Leaked-Databases/rockyou.txt"
        ]


class WordlistValidationConfig(BaseModel):
    """Complete configuration for wordlist validation and recommendations"""
    
    # Pattern definitions
    patterns: List[WordlistPattern] = Field(default_factory=lambda: [
        # Inappropriate patterns for most services
        WordlistPattern(
            pattern="/cat/language/",
            category=WordlistCategory.LANGUAGES,
            appropriate_for=[],
            inappropriate_for=[ServiceType.SSH, ServiceType.FTP, ServiceType.HTTP, ServiceType.HTTPS],
            priority=5
        ),
        WordlistPattern(
            pattern="/user-agents/",
            category=WordlistCategory.USER_AGENTS,
            appropriate_for=[ServiceType.HTTP, ServiceType.HTTPS],
            inappropriate_for=[ServiceType.SSH, ServiceType.FTP],
            priority=3
        ),
        WordlistPattern(
            pattern="/file-extensions/",
            category=WordlistCategory.EXTENSIONS,
            appropriate_for=[ServiceType.HTTP, ServiceType.HTTPS],
            inappropriate_for=[ServiceType.SSH, ServiceType.FTP],
            priority=3
        ),
        WordlistPattern(
            pattern="/fuzzing/",
            category=WordlistCategory.FUZZING,
            appropriate_for=[ServiceType.HTTP, ServiceType.HTTPS],
            inappropriate_for=[ServiceType.SSH, ServiceType.FTP],
            priority=2
        ),
        
        # Appropriate patterns
        WordlistPattern(
            pattern="/passwords/",
            category=WordlistCategory.PASSWORDS,
            appropriate_for=[ServiceType.SSH, ServiceType.FTP, ServiceType.MYSQL, ServiceType.POSTGRESQL],
            inappropriate_for=[],
            priority=1
        ),
        WordlistPattern(
            pattern="/credentials/",
            category=WordlistCategory.CREDENTIALS,
            appropriate_for=[ServiceType.SSH, ServiceType.FTP, ServiceType.MYSQL, ServiceType.POSTGRESQL],
            inappropriate_for=[],
            priority=1
        ),
        WordlistPattern(
            pattern="/web-content/",
            category=WordlistCategory.DIRECTORIES,
            appropriate_for=[ServiceType.HTTP, ServiceType.HTTPS],
            inappropriate_for=[ServiceType.SSH, ServiceType.FTP],
            priority=1
        ),
        WordlistPattern(
            pattern="ssh",
            category=WordlistCategory.CREDENTIALS,
            appropriate_for=[ServiceType.SSH],
            inappropriate_for=[],
            priority=1
        ),
        WordlistPattern(
            pattern="ftp",
            category=WordlistCategory.CREDENTIALS,
            appropriate_for=[ServiceType.FTP],
            inappropriate_for=[],
            priority=1
        ),
        WordlistPattern(
            pattern="rockyou",
            category=WordlistCategory.PASSWORDS,
            appropriate_for=[ServiceType.SSH, ServiceType.FTP, ServiceType.MYSQL, ServiceType.POSTGRESQL],
            inappropriate_for=[],
            priority=1
        ),
        WordlistPattern(
            pattern="password",
            category=WordlistCategory.PASSWORDS,
            appropriate_for=[ServiceType.SSH, ServiceType.FTP, ServiceType.MYSQL, ServiceType.POSTGRESQL],
            inappropriate_for=[],
            priority=1
        )
    ])
    
    # Service-specific configurations
    service_configs: Dict[ServiceType, ServiceWordlistConfig] = Field(default_factory=lambda: {
        ServiceType.SSH: ServiceWordlistConfig(
            service_type=ServiceType.SSH,
            preferred_categories=[WordlistCategory.PASSWORDS, WordlistCategory.CREDENTIALS, WordlistCategory.USERNAMES],
            fallback_wordlists=get_wordlist_paths(ServiceType.SSH),
            inappropriate_patterns=["/cat/language/", "/user-agents/", "/web-content/", "/file-extensions/"],
            tools=["hydra", "ncrack", "medusa"]
        ),
        ServiceType.FTP: ServiceWordlistConfig(
            service_type=ServiceType.FTP,
            preferred_categories=[WordlistCategory.PASSWORDS, WordlistCategory.CREDENTIALS, WordlistCategory.USERNAMES],
            fallback_wordlists=get_wordlist_paths(ServiceType.FTP),
            inappropriate_patterns=["/cat/language/", "/user-agents/", "/web-content/"],
            tools=["hydra", "ncrack", "medusa"]
        ),
        ServiceType.HTTP: ServiceWordlistConfig(
            service_type=ServiceType.HTTP,
            preferred_categories=[WordlistCategory.DIRECTORIES, WordlistCategory.FILES],
            fallback_wordlists=get_wordlist_paths(ServiceType.HTTP),
            inappropriate_patterns=["/passwords/", "/credentials/"],
            tools=["feroxbuster", "gobuster", "ffuf"]
        ),
        ServiceType.HTTPS: ServiceWordlistConfig(
            service_type=ServiceType.HTTPS,
            preferred_categories=[WordlistCategory.DIRECTORIES, WordlistCategory.FILES],
            fallback_wordlists=get_wordlist_paths(ServiceType.HTTPS),
            inappropriate_patterns=["/passwords/", "/credentials/"],
            tools=["feroxbuster", "gobuster", "ffuf"]
        )
    })
    
    def is_wordlist_appropriate(self, wordlist_path: str, service_type: ServiceType) -> bool:
        """Check if a wordlist is appropriate for a given service type"""
        path_lower = wordlist_path.lower()
        
        # Check service-specific inappropriate patterns
        if service_type in self.service_configs:
            config = self.service_configs[service_type]
            for pattern in config.inappropriate_patterns:
                if pattern.lower() in path_lower:
                    return False
        
        # Check global patterns
        for pattern_config in self.patterns:
            if pattern_config.pattern.lower() in path_lower:
                if service_type in pattern_config.inappropriate_for:
                    return False
                if service_type in pattern_config.appropriate_for:
                    return True
        
        # If no specific match, check preferred categories
        if service_type in self.service_configs:
            config = self.service_configs[service_type]
            for category in config.preferred_categories:
                if category.value in path_lower:
                    return True
        
        return False
    
    def get_fallback_wordlist(self, service_type: ServiceType) -> Optional[str]:
        """Get the best fallback wordlist for a service type"""
        if service_type in self.service_configs:
            config = self.service_configs[service_type]
            return config.fallback_wordlists[0] if config.fallback_wordlists else None
        return None
    
    def get_service_tools(self, service_type: ServiceType) -> List[str]:
        """Get recommended tools for a service type"""
        if service_type in self.service_configs:
            return self.service_configs[service_type].tools
        return []
    
    def update_fallback_wordlists(self, detected_seclists_path: str = None):
        """Update fallback wordlists based on detected SecLists installation"""
        if not detected_seclists_path:
            paths = load_seclists_paths()
            detected_seclists_path = paths[0] if paths else "/usr/share/seclists"
        
        for service_type in self.service_configs:
            new_paths = get_wordlist_paths(service_type, detected_seclists_path)
            self.service_configs[service_type].fallback_wordlists = new_paths


# Default instance
DEFAULT_WORDLIST_CONFIG = WordlistValidationConfig()