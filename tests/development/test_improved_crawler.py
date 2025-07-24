#!/usr/bin/env python3
"""Test script for improved Mini Spider custom crawler"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from workflows.mini_spider_04.custom_crawler import CustomCrawler
from workflows.mini_spider_04.models import CrawledURL, DiscoverySource
from utils.debug import debug_print, set_debug

async def test_improved_crawler():
    """Test the improved custom crawler with anti-WAF measures"""
    
    # Enable debug output
    set_debug(True)
    
    print("🕷️  Testing Improved Mini Spider Custom Crawler")
    print("=" * 60)
    
    # Test with a known target that responds well
    test_target = "httpbin.org"
    seed_urls = [
        CrawledURL(
            url=f"http://{test_target}/",
            source=DiscoverySource.SEED,
            status_code=200,
            discovered_at=datetime.now()
        )
    ]
    
    print(f"Target: {test_target}")
    print(f"Seed URLs: {[url.url for url in seed_urls]}")
    print()
    
    # Initialize custom crawler
    crawler = CustomCrawler()
    
    print("Crawler Configuration:")
    print(f"  • Max concurrent: {crawler.crawler_config.max_concurrent}")
    print(f"  • Request delay: {crawler.crawler_config.request_delay}s")
    print(f"  • Max retries: {crawler.crawler_config.max_retries}")
    print(f"  • Request timeout: {crawler.crawler_config.request_timeout}s")
    print()
    
    try:
        # Test path discovery with new improvements
        print("→ Starting improved path discovery...")
        discovered_urls = await crawler.discover_paths(seed_urls, max_concurrent=3)
        
        print(f"✅ Discovery completed!")
        print(f"  • URLs discovered: {len(discovered_urls)}")
        
        if discovered_urls:
            print(f"  • Discovered URLs:")
            for i, url in enumerate(discovered_urls):
                print(f"    {i+1}. {url.url} (status: {url.status_code})")
        else:
            print("  ⚠ No URLs discovered")
            
            # Get detailed stats
            stats = crawler.stats
            print(f"  • URLs tested: {stats.urls_tested}")
            print(f"  • Successful requests: {stats.successful_requests}")
            print(f"  • Failed requests: {stats.failed_requests}")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n🔧 Improvements Made:")
    print(f"  ✅ Reduced concurrency (3 instead of 10)")
    print(f"  ✅ Added 0.5s delay between requests")
    print(f"  ✅ Added retry logic with exponential backoff")
    print(f"  ✅ Improved user agents and headers")
    print(f"  ✅ Randomized request order")
    print(f"  ✅ HEAD→GET fallback for blocked requests")
    print(f"  ✅ More accepted status codes (405, 500, 502, 503)")

if __name__ == "__main__":
    asyncio.run(test_improved_crawler())