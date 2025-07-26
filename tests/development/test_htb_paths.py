#!/usr/bin/env python3
"""Test simulation of HTB/Kali paths for hakrawler detection"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflows.mini_spider_04.config import SpiderConfigManager

def simulate_htb_detection():
    """Simulate hakrawler detection on HTB/Kali machine"""
    
    print("🔍 Simulating HTB/Kali Hakrawler Detection")
    print("=" * 50)
    
    # Create a test config manager
    config_manager = SpiderConfigManager()
    
    # Show the search paths that would be checked
    print("→ HTB/Kali paths that will be checked:")
    
    htb_paths = [
        '/usr/bin/hakrawler',           # apt install hakrawler puts it here
        '/usr/local/bin/hakrawler',     # Manual installations
        '/opt/hakrawler/hakrawler',     # Custom /opt installations
        '/opt/go/bin/hakrawler',        # Go tools in /opt
        '/snap/bin/hakrawler',          # Snap packages
        '/usr/share/go/bin/hakrawler',  # Alternative Go bin path
        '/bin/hakrawler',               # System binary path
        '/sbin/hakrawler',              # System sbin path
    ]
    
    for path in htb_paths:
        exists = os.path.isfile(path)
        executable = os.access(path, os.X_OK) if exists else False
        status = "✅ FOUND" if (exists and executable) else "❌ not found"
        print(f"  {path}: {status}")
    
    print("\n→ Additional user paths:")
    user_paths = [
        os.path.expanduser('~/go/bin/hakrawler'),
        os.path.expanduser('~/.local/bin/hakrawler'),
        os.path.expanduser('~/tools/hakrawler'),
        os.path.expanduser('~/bin/hakrawler'),
    ]
    
    for path in user_paths:
        exists = os.path.isfile(path)
        executable = os.access(path, os.X_OK) if exists else False
        status = "✅ FOUND" if (exists and executable) else "❌ not found"
        print(f"  {path}: {status}")
    
    print("\n→ Current detection result:")
    hakrawler_path = config_manager._find_hakrawler_path()
    if hakrawler_path:
        print(f"✅ Hakrawler found at: {hakrawler_path}")
    else:
        print("❌ Hakrawler not found in any location")
    
    print("\n💡 Installation instructions for HTB/Kali:")
    print("  • apt update && apt install hakrawler")
    print("  • go install github.com/hakluke/hakrawler@latest")
    print("  • wget -O /usr/local/bin/hakrawler https://github.com/hakluke/hakrawler/releases/...")

if __name__ == "__main__":
    simulate_htb_detection()