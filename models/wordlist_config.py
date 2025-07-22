"""
Pydantic models for wordlist configuration and validation
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


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
            fallback_wordlists=[
                "/home/cmejia10/SecLists/Passwords/Default-Credentials/ssh-betterdefaultpasslist.txt",
                "/home/cmejia10/SecLists/Passwords/Common-Credentials/top-20-common-SSH-passwords.txt",
                "/usr/share/seclists/Passwords/Default-Credentials/ssh-betterdefaultpasslist.txt",
                "/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt",
                "/usr/share/wordlists/rockyou.txt"
            ],
            inappropriate_patterns=["/cat/language/", "/user-agents/", "/web-content/", "/file-extensions/"],
            tools=["hydra", "ncrack", "medusa"]
        ),
        ServiceType.FTP: ServiceWordlistConfig(
            service_type=ServiceType.FTP,
            preferred_categories=[WordlistCategory.PASSWORDS, WordlistCategory.CREDENTIALS, WordlistCategory.USERNAMES],
            fallback_wordlists=[
                "/home/cmejia10/SecLists/Passwords/Default-Credentials/ftp-betterdefaultpasslist.txt",
                "/usr/share/seclists/Passwords/Default-Credentials/ftp-betterdefaultpasslist.txt",
                "/usr/share/wordlists/rockyou.txt"
            ],
            inappropriate_patterns=["/cat/language/", "/user-agents/", "/web-content/"],
            tools=["hydra", "ncrack", "medusa"]
        ),
        ServiceType.HTTP: ServiceWordlistConfig(
            service_type=ServiceType.HTTP,
            preferred_categories=[WordlistCategory.DIRECTORIES, WordlistCategory.FILES],
            fallback_wordlists=[
                "/home/cmejia10/SecLists/Discovery/Web-Content/common.txt",
                "/usr/share/seclists/Discovery/Web-Content/common.txt",
                "/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt"
            ],
            inappropriate_patterns=["/passwords/", "/credentials/"],
            tools=["feroxbuster", "gobuster", "ffuf"]
        ),
        ServiceType.HTTPS: ServiceWordlistConfig(
            service_type=ServiceType.HTTPS,
            preferred_categories=[WordlistCategory.DIRECTORIES, WordlistCategory.FILES],
            fallback_wordlists=[
                "/home/cmejia10/SecLists/Discovery/Web-Content/common.txt",
                "/usr/share/seclists/Discovery/Web-Content/common.txt",
                "/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt"
            ],
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


# Default instance
DEFAULT_WORDLIST_CONFIG = WordlistValidationConfig()