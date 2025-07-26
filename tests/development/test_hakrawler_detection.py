#!/usr/bin/env python3
"""Test hakrawler detection logic"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflows.mini_spider_04.config import SpiderConfigManager

def test_hakrawler_detection():
    """Test if hakrawler detection is working"""
    
    print("🔍 Testing Hakrawler Detection")
    print("=" * 40)
    
    # Create config manager
    config_manager = SpiderConfigManager()
    
    # Test the detection function
    print("→ Testing _find_hakrawler_path()...")
    hakrawler_path = config_manager._find_hakrawler_path()
    
    if hakrawler_path:
        print(f"✅ Found hakrawler at: {hakrawler_path}")
        
        # Test execution
        print("→ Testing hakrawler execution...")
        is_working = config_manager._test_hakrawler_execution(hakrawler_path)
        if is_working:
            print("✅ Hakrawler execution test passed")
        else:
            print("❌ Hakrawler execution test failed")
    else:
        print("❌ Hakrawler not found")
        
        # Manual checks
        print("\n→ Manual path checks:")
        manual_paths = [
            os.path.expanduser('~/go/bin/hakrawler'),
            '/usr/local/go/bin/hakrawler',
            '/usr/bin/hakrawler',           # apt install location
            '/usr/local/bin/hakrawler',
            '/opt/hakrawler/hakrawler',
            '/opt/go/bin/hakrawler',
            '/usr/share/go/bin/hakrawler',
            '/bin/hakrawler'
        ]
        
        for path in manual_paths:
            exists = os.path.isfile(path)
            executable = os.access(path, os.X_OK) if exists else False
            print(f"  {path}: exists={exists}, executable={executable}")
            
            if exists and executable:
                print(f"    → Testing execution of {path}...")
                is_working = config_manager._test_hakrawler_execution(path)
                print(f"    → Execution test result: {is_working}")
    
    # Check tools_available
    print(f"\n→ Tools available in config:")
    print(f"  hakrawler: {config_manager.tools_available.get('hakrawler')}")
    print(f"  httpx: {config_manager.tools_available.get('httpx')}")
    print(f"  curl: {config_manager.tools_available.get('curl')}")

if __name__ == "__main__":
    test_hakrawler_detection()