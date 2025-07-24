#!/usr/bin/env python3
"""
Hakrawler Detection and Setup Helper
Help diagnose and fix hakrawler detection issues for IPCrawler
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    print("🔍 Hakrawler Detection and Setup Helper")
    print("=" * 50)
    
    # Check if hakrawler is in PATH
    print("\n1. Checking PATH...")
    hakrawler_in_path = shutil.which('hakrawler')
    if hakrawler_in_path:
        print(f"✅ Found hakrawler in PATH: {hakrawler_in_path}")
    else:
        print("❌ Hakrawler not found in PATH")
    
    # Check common installation locations
    print("\n2. Checking common installation locations...")
    common_paths = [
        os.path.expanduser('~/go/bin/hakrawler'),
        '/usr/local/go/bin/hakrawler',
        '/usr/bin/hakrawler',
        '/usr/local/bin/hakrawler',
        '/opt/hakrawler/hakrawler',
        '/opt/go/bin/hakrawler',
        '/snap/bin/hakrawler',
        os.path.expanduser('~/.local/bin/hakrawler'),
        os.path.expanduser('~/tools/hakrawler'),
        os.path.expanduser('~/bin/hakrawler'),
    ]
    
    found_installations = []
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            print(f"✅ Found: {path}")
            found_installations.append(path)
            
            # Test if it works
            try:
                result = subprocess.run([path], input='', capture_output=True, 
                                      text=True, timeout=2)
                print(f"   → Execution test: PASSED")
            except subprocess.TimeoutExpired:
                print(f"   → Execution test: PASSED (timeout expected)")
            except Exception as e:
                print(f"   → Execution test: FAILED ({e})")
        else:
            print(f"❌ Not found: {path}")
    
    # Check if Go is installed
    print("\n3. Checking Go installation...")
    go_path = shutil.which('go')
    if go_path:
        print(f"✅ Go found at: {go_path}")
        try:
            result = subprocess.run(['go', 'version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"   → Version: {result.stdout.strip()}")
            else:
                print(f"   → Version check failed")
        except Exception as e:
            print(f"   → Version check error: {e}")
    else:
        print("❌ Go not found in PATH")
    
    # Check GOPATH and GOROOT
    print("\n4. Checking Go environment...")
    gopath = os.environ.get('GOPATH')
    goroot = os.environ.get('GOROOT')
    
    if gopath:
        print(f"✅ GOPATH: {gopath}")
        gopath_bin = os.path.join(gopath, 'bin', 'hakrawler')
        if os.path.isfile(gopath_bin):
            print(f"   → Found hakrawler: {gopath_bin}")
            found_installations.append(gopath_bin)
    else:
        print("ℹ GOPATH not set (using default ~/go)")
    
    if goroot:
        print(f"✅ GOROOT: {goroot}")
    else:
        print("ℹ GOROOT not set (using Go default)")
    
    # Recommendations
    print("\n5. Recommendations:")
    
    if not found_installations:
        print("❌ Hakrawler not found anywhere!")
        print("\n📦 Installation options:")
        print("   • Go install: go install github.com/hakluke/hakrawler@latest")
        print("   • Kali/Ubuntu: apt update && apt install hakrawler")
        print("   • Manual: Download from https://github.com/hakluke/hakrawler/releases")
        
    elif not hakrawler_in_path:
        print("⚠ Hakrawler found but not in PATH")
        print("\n🔧 PATH Fix options:")
        
        # Check if ~/go/bin exists and has hakrawler
        go_bin = os.path.expanduser('~/go/bin')
        if os.path.join(go_bin, 'hakrawler') in found_installations:
            print(f"   • Add to shell profile: echo 'export PATH=\"$PATH:{go_bin}\"' >> ~/.zshrc")
            print(f"   • Temporary fix: export PATH=\"$PATH:{go_bin}\"")
        
        print(f"   • Create symlink: sudo ln -s {found_installations[0]} /usr/local/bin/hakrawler")
        
    else:
        print("✅ Hakrawler is properly installed and accessible!")
    
    # Test with IPCrawler
    print("\n6. Testing with IPCrawler...")
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from workflows.mini_spider_04.config import get_config_manager
        
        cm = get_config_manager()
        detected_path = cm.tools_available.get('hakrawler')
        validation_result = cm.validate_hakrawler_installation()
        
        if detected_path:
            print(f"✅ IPCrawler detected hakrawler: {detected_path}")
            if validation_result:
                print("✅ IPCrawler validation: PASSED")
            else:
                print("❌ IPCrawler validation: FAILED")
        else:
            print("❌ IPCrawler did not detect hakrawler")
            
    except Exception as e:
        print(f"❌ IPCrawler test failed: {e}")
    
    print("\n" + "=" * 50)
    print("💡 If hakrawler is still not detected after following the recommendations,")
    print("   restart your terminal or run: source ~/.zshrc (or ~/.bashrc)")

if __name__ == "__main__":
    main() 