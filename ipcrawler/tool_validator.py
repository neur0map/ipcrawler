#!/usr/bin/env python3
"""
IPCrawler Tool Validator Module
==============================

Validates that all tools expected by the Makefile are installed in the correct locations
and are discoverable by Python's subprocess calls.
"""

import os
import shutil
import platform
from typing import Dict, List, Optional, Tuple

from ipcrawler.io import info, warn, error

# Tool definitions based on Makefile analysis
TOOL_CATEGORIES = {
    "core": [
        "python3", "pip", "curl", "nmap", "git"
    ],
    "directory_busting": [
        "feroxbuster", "gobuster", "ffuf", "dirsearch", "dirb"
    ],
    "network_enumeration": [
        "dnsrecon", "masscan", "nikto", "whatweb", "smbclient", "smbmap", 
        "nbtscan", "snmpwalk", "onesixtyone", "sslscan"
    ],
    "specialized": [
        "enum4linux", "enum4linux-ng", "impacket-scripts", "redis-cli", 
        "oscanner", "tnscmd10g", "sipvicious", "sqlmap"
    ],
    "password_tools": [
        "john", "hashcat", "hydra", "medusa", "ncrack"
    ],
    "web_fuzzing": [
        "wfuzz", "wpscan"
    ],
    "subdomain_enum": [
        "sublist3r", "amass", "fierce"
    ]
}

# Tools not available on macOS according to Makefile
MACOS_UNAVAILABLE = {
    "dnsrecon", "enum4linux", "enum4linux-ng", "impacket-scripts", 
    "nbtscan", "onesixtyone", "oscanner", "smbmap", "tnscmd10g"
}

class ToolValidator:
    def __init__(self):
        self.system = platform.system()
        self.missing_tools = []
        self.found_tools = {}
        self.path_directories = os.environ.get('PATH', '').split(os.pathsep)
        
    def get_expected_paths(self) -> List[str]:
        """Get expected installation paths for current platform."""
        if self.system == "Darwin":
            return [
                "/opt/homebrew/bin",  # Apple Silicon Homebrew
                "/usr/local/bin",     # Intel Homebrew
                "/usr/bin",           # System
                "/bin"                # System
            ]
        elif self.system == "Linux":
            return [
                "/usr/bin",           # APT packages
                "/usr/local/bin",     # Manual/GitHub installs
                "/bin",               # System
                "/usr/sbin",          # System admin tools
                "/sbin"               # System admin tools
            ]
        else:
            return ["/usr/bin", "/usr/local/bin", "/bin"]
    
    def find_tool_path(self, tool_name: str) -> Optional[str]:
        """Find the actual path of a tool using shutil.which()."""
        return shutil.which(tool_name)
    
    def should_skip_tool(self, tool_name: str) -> bool:
        """Check if tool should be skipped on current platform."""
        if self.system == "Darwin" and tool_name in MACOS_UNAVAILABLE:
            return True
        return False
    
    def validate_tool_location(self, tool_name: str, actual_path: str) -> Tuple[bool, str]:
        """Validate if tool is in expected location."""
        expected_paths = self.get_expected_paths()
        
        for expected_dir in expected_paths:
            if actual_path.startswith(expected_dir):
                return True, expected_dir
        
        return False, "unexpected location"
    
    def check_critical_tools(self) -> List[str]:
        """Check for critical tools that are required for IPCrawler to function."""
        critical_missing = []
        
        for tool in TOOL_CATEGORIES["core"]:
            if self.should_skip_tool(tool):
                continue
                
            actual_path = self.find_tool_path(tool)
            if actual_path is None:
                critical_missing.append(tool)
        
        return critical_missing
    
    def validate_subprocess_environment(self) -> bool:
        """Validate that subprocess environment includes all expected directories."""
        expected_paths = self.get_expected_paths()
        missing_paths = []
        
        for expected_path in expected_paths:
            if expected_path not in self.path_directories and os.path.exists(expected_path):
                missing_paths.append(expected_path)
        
        if missing_paths:
            warn(f"Missing expected PATH directories: {', '.join(missing_paths)}")
            return False
        
        return True
    
    def get_tool_report(self) -> Dict[str, any]:
        """Generate a comprehensive tool availability report."""
        report = {
            "platform": self.system,
            "critical_missing": [],
            "missing_tools": [],
            "found_tools": {},
            "unexpected_locations": {},
            "success": True
        }
        
        info(f"🔧 Tool validation for {self.system} platform")
        
        for category, tools in TOOL_CATEGORIES.items():
            for tool in tools:
                if self.should_skip_tool(tool):
                    continue
                
                actual_path = self.find_tool_path(tool)
                
                if actual_path is None:
                    report["missing_tools"].append((category, tool))
                    if category == "core":
                        report["critical_missing"].append(tool)
                        report["success"] = False
                    
                    warn(f"❌ {tool}: not found in PATH")
                else:
                    report["found_tools"][tool] = actual_path
                    is_expected, location_info = self.validate_tool_location(tool, actual_path)
                    
                    if not is_expected:
                        report["unexpected_locations"][tool] = actual_path
                        warn(f"⚠️  {tool}: found at {actual_path} (unexpected location)")
                    else:
                        info(f"✅ {tool}: {actual_path} ({location_info})")
        
        if report["critical_missing"]:
            error(f"Critical tools missing: {', '.join(report['critical_missing'])}")
            error("Run 'make install' to install missing tools")
        
        return report
    
    def fail_fast_if_missing_critical(self) -> bool:
        """Fail fast if critical tools are missing."""
        critical_missing = self.check_critical_tools()
        
        if critical_missing:
            error("❌ Critical tools missing - IPCrawler cannot function without these:")
            for tool in critical_missing:
                error(f"  - {tool}")
            error("")
            error("💡 Installation suggestions:")
            if self.system == "Darwin":
                error("  macOS: Run 'make install' or 'brew install <tool_name>'")
            elif self.system == "Linux":
                error("  Debian/Ubuntu: Run 'make install' or 'sudo apt install <tool_name>'")
            error("")
            return False
        
        return True

def validate_tools() -> bool:
    """Main tool validation function."""
    validator = ToolValidator()
    
    # Fail fast if critical tools are missing
    if not validator.fail_fast_if_missing_critical():
        return False
    
    # Generate detailed report
    report = validator.get_tool_report()
    
    # Validate subprocess environment
    validator.validate_subprocess_environment()
    
    return report["success"]