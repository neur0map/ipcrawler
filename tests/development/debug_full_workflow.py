#!/usr/bin/env python3
"""Debug the full Mini Spider workflow to understand why 0 URLs are found"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from workflows.mini_spider_04.scanner import MiniSpiderScanner
from workflows.mini_spider_04.models import CrawledURL, DiscoverySource
from src.core.utils.debugging import set_debug

async def debug_full_workflow():
    """Debug the complete Mini Spider workflow"""
    
    # Enable debug output
    set_debug(True)
    
    print("🔍 Debugging Full Mini Spider Workflow")
    print("=" * 60)
    
    # Create scanner
    scanner = MiniSpiderScanner()
    
    # Test with a target that should work
    target = "httpbin.org"
    
    print(f"Target: {target}")
    print()
    
    # Simulate previous HTTP results (like what the user sees)
    mock_http_results = {
        "success": True,
        "data": {
            "target": target,
            "services": [
                {
                    "url": f"http://{target}/",
                    "status_code": 200,
                    "headers": {"content-type": "text/html"},
                    "technologies": ["nginx"],
                    "discovered_paths": [
                        "/config.php",
                        "/api/v2/",
                        "/api-docs/",
                        "/nginx_status",
                        "lib/owlcarousel/assets/owl.carousel.min.css"
                    ]
                }
            ]
        }
    }
    
    print("📋 Mock HTTP Results:")
    print(f"  • Services: {len(mock_http_results['data']['services'])}")
    print(f"  • First service URL: {mock_http_results['data']['services'][0]['url']}")
    print(f"  • Discovered paths: {mock_http_results['data']['services'][0]['discovered_paths']}")
    print()
    
    # Test URL extraction
    print("→ Testing URL extraction from HTTP results...")
    extracted_urls = await scanner.url_extractor.extract_from_http_results(mock_http_results)
    print(f"  ✓ Extracted {len(extracted_urls)} URLs:")
    for i, url in enumerate(extracted_urls[:5]):
        print(f"    {i+1}. {url.url} (source: {url.source})")
    if len(extracted_urls) > 5:
        print(f"    ... and {len(extracted_urls) - 5} more")
    print()
    
    # Test seed URL validation
    print("→ Testing seed URL validation...")
    if extracted_urls:
        active_urls = await scanner.custom_crawler._validate_seed_urls(extracted_urls)
        print(f"  ✓ Active URLs: {len(active_urls)}")
        for url in active_urls:
            print(f"    • {url}")
    else:
        print("  ⚠ No extracted URLs to validate")
        # Create basic seed URLs
        print("  → Creating basic seed URLs...")
        seed_urls = scanner._create_seed_urls(target)
        print(f"  ✓ Created {len(seed_urls)} seed URLs")
        active_urls = await scanner.custom_crawler._validate_seed_urls(seed_urls)
        print(f"  ✓ Active URLs: {len(active_urls)}")
        for url in active_urls:
            print(f"    • {url}")
    print()
    
    if active_urls:
        # Test a few common paths manually
        print("→ Testing a few common paths manually...")
        test_paths = ["/robots.txt", "/api/", "/config.php", "/admin/"]
        
        for path in test_paths:
            full_url = f"{active_urls[0]}{path.lstrip('/')}"
            result = await scanner.custom_crawler._test_single_path(active_urls[0], path)
            if result:
                print(f"  ✅ {full_url} -> {result.status_code}")
            else:
                print(f"  ❌ {full_url} -> failed")
        print()
    
    # Test the full workflow
    print("→ Running full Mini Spider workflow...")
    result = await scanner.execute(target, previous_results={'http_03': mock_http_results})
    
    print(f"✅ Workflow completed!")
    print(f"  • Success: {result.success}")
    if result.success and 'discovered_urls' in result.data:
        print(f"  • URLs discovered: {len(result.data['discovered_urls'])}")
    else:
        print(f"  • Error: {result.error if not result.success else 'No URLs in result'}")

if __name__ == "__main__":
    asyncio.run(debug_full_workflow())