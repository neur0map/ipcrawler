#!/usr/bin/env python3
"""Debug script to see what seed URLs are being generated"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from workflows.mini_spider_04.scanner import MiniSpiderScanner
from utils.debug import set_debug

async def debug_seed_urls():
    """Debug seed URL generation and validation"""
    
    set_debug(True)
    
    print("🔍 Debugging Mini Spider Seed URL Generation")
    print("=" * 60)
    
    # Create scanner instance
    scanner = MiniSpiderScanner()
    
    # Test with a known target
    target = "10.10.11.23"
    
    print(f"Target: {target}")
    print()
    
    # Test seed URL creation when no previous results
    print("→ Testing seed URL creation (no previous results)...")
    seed_urls = scanner._create_seed_urls(target)
    
    print(f"Generated {len(seed_urls)} seed URLs:")
    for i, url in enumerate(seed_urls):
        print(f"  {i+1}. {url.url}")
    
    print()
    print("→ Testing seed URL validation...")
    
    # Test custom crawler validation
    active_urls = await scanner.custom_crawler._validate_seed_urls(seed_urls)
    print(f"Active URLs: {len(active_urls)}")
    for url in active_urls:
        print(f"  ✓ {url}")
    
    if len(active_urls) == 0:
        print("\n❌ No seed URLs are responding")
        print("This could be because:")
        print("1. Target is not accessible")
        print("2. Target only responds on specific ports")
        print("3. Target requires HTTPS")
        print("4. Target blocks HEAD requests")
        print("5. Network connectivity issues")
        
        # Test a simple connectivity check
        print("\n→ Testing basic connectivity...")
        import subprocess
        try:
            result = subprocess.run(['ping', '-c', '1', target], 
                                  capture_output=True, 
                                  timeout=5)
            if result.returncode == 0:
                print(f"  ✓ {target} is reachable via ping")
            else:
                print(f"  ❌ {target} is not reachable via ping")
        except Exception as e:
            print(f"  ❌ Ping test failed: {e}")
    else:
        print(f"\n✅ {len(active_urls)} URLs are responding and ready for discovery")

if __name__ == "__main__":
    asyncio.run(debug_seed_urls())