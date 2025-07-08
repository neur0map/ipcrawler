"""
Security validation for inputs and arguments.
"""

import re
import ipaddress
from typing import List, Optional
from urllib.parse import urlparse


class ArgumentValidator:
    """Validates command arguments for security."""
    
    # Dangerous patterns to reject
    DANGEROUS_PATTERNS = [
        r'[;&|`$()]',           # Shell metacharacters
        r'\.\./',               # Directory traversal
        r'[<>]',                # Redirection operators
        r'^\s*$',               # Empty/whitespace only
        r'\\x[0-9a-fA-F]{2}',   # Hex encoded chars
        r'%[0-9a-fA-F]{2}',     # URL encoded chars
        r'[\x00-\x1f\x7f-\x9f]', # Control characters
    ]
    
    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.dat', '.tmp'
    ]
    
    @classmethod
    def validate_argument(cls, arg: str) -> bool:
        """Validate a single argument."""
        if not arg or len(arg) > 1000:
            return False
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, arg):
                return False
        
        # Check for dangerous file extensions
        for ext in cls.DANGEROUS_EXTENSIONS:
            if arg.lower().endswith(ext):
                return False
        
        return True
    
    @classmethod
    def validate_arguments(cls, args: List[str]) -> bool:
        """Validate all arguments."""
        if len(args) > 50:  # Max 50 arguments
            return False
        
        return all(cls.validate_argument(arg) for arg in args)
    
    @classmethod
    def sanitize_argument(cls, arg: str) -> str:
        """Sanitize an argument by removing dangerous characters."""
        # Remove control characters
        arg = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', arg)
        
        # Remove shell metacharacters
        arg = re.sub(r'[;&|`$()<>]', '', arg)
        
        # Limit length
        return arg[:1000]


class TargetValidator:
    """Validates target inputs (IPs, domains, URLs)."""
    
    @classmethod
    def is_valid_ip(cls, target: str) -> bool:
        """Check if target is a valid IP address."""
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return False
    
    @classmethod
    def is_valid_domain(cls, target: str) -> bool:
        """Check if target is a valid domain name."""
        if not target or len(target) > 253:
            return False
        
        # Basic domain validation
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(domain_pattern, target))
    
    @classmethod
    def is_valid_url(cls, target: str) -> bool:
        """Check if target is a valid URL."""
        try:
            result = urlparse(target)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @classmethod
    def validate_target(cls, target: str) -> bool:
        """Validate target is a safe IP, domain, or URL."""
        if not target or len(target) > 500:
            return False
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r'[;&|`$()]',           # Shell metacharacters
            r'\.\./',               # Directory traversal
            r'[\x00-\x1f\x7f-\x9f]', # Control characters
            r'\\x[0-9a-fA-F]{2}',   # Hex encoded
            r'%[0-9a-fA-F]{2}',     # URL encoded
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, target):
                return False
        
        # Must be valid IP, domain, or URL
        return (cls.is_valid_ip(target) or 
                cls.is_valid_domain(target) or 
                cls.is_valid_url(target))
    
    @classmethod
    def sanitize_target(cls, target: str) -> str:
        """Sanitize target by removing dangerous characters."""
        # Remove control characters
        target = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', target)
        
        # Remove shell metacharacters
        target = re.sub(r'[;&|`$()<>]', '', target)
        
        # Limit length
        return target[:500]