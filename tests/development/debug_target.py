#!/usr/bin/env python3
"""Debug script to test what responses we're getting from the target"""

import asyncio
import httpx
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.debug import set_debug

async def test_target_responses():
    """Test what responses we're getting from common paths"""
    
    set_debug(True)
    
    # From the output, it looks like they're testing a target that responds
    # Let's use a target IP that might be accessible in HTB environment
    # For now, let's test with paths that typically exist
    
    target_base = "http://10.10.11.23"  # Based on user's previous runs
    
    # Test some common paths that should exist
    test_paths = [
        "/",
        "/robots.txt",
        "/index.php", 
        "/console",
        "/.well-known/security.txt",
        "/admin",
        "/api",
        "/login"
    ]
    
    print(f"🔍 Testing target responses for {target_base}")
    print("=" * 50)
    
    async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(10.0)) as client:
        for path in test_paths:
            url = f"{target_base}{path}"
            try:
                print(f"\n→ Testing: {url}")
                response = await client.head(url, follow_redirects=False)
                print(f"  Status: {response.status_code}")
                print(f"  Headers: {dict(list(response.headers.items())[:3])}")  # First 3 headers
                
                # Check what our current logic would do
                if response.status_code in [200, 201, 202, 204, 301, 302, 307, 308, 401, 403]:
                    print(f"  ✅ Would be ACCEPTED by custom crawler")
                else:
                    print(f"  ❌ Would be REJECTED by custom crawler")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    print(f"\n" + "=" * 50)
    print("If many paths are returning 404 but you see paths in the initial scan,")
    print("the issue might be:")
    print("1. Different target being used")
    print("2. WAF/firewall blocking HEAD requests") 
    print("3. Target only responds to GET requests")
    print("4. Target requires specific headers")

if __name__ == "__main__":
    asyncio.run(test_target_responses())