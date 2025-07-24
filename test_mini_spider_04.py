#!/usr/bin/env python3
"""Test script for Mini Spider workflow validation"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported successfully"""
    print("Testing imports...")
    
    try:
        # Test basic imports
        from workflows.mini_spider_04.scanner import MiniSpiderScanner
        print("✅ MiniSpiderScanner imported successfully")
        
        from workflows.mini_spider_04.config import get_spider_config, validate_tools
        print("✅ Configuration imports successful")
        
        from workflows.mini_spider_04.models import (
            MiniSpiderResult, CrawledURL, InterestingFinding,
            DiscoverySource, URLCategory, SeverityLevel
        )
        print("✅ Models imported successfully")
        
        from workflows.mini_spider_04.utils import (
            validate_input, deduplicate_urls, URLFilter
        )
        print("✅ Utils imported successfully")
        
        from workflows.mini_spider_04.url_extractor import URLExtractor
        print("✅ URLExtractor imported successfully")
        
        from workflows.mini_spider_04.custom_crawler import CustomCrawler
        print("✅ CustomCrawler imported successfully")
        
        from workflows.mini_spider_04.hakrawler_wrapper import HakrawlerWrapper
        print("✅ HakrawlerWrapper imported successfully")
        
        from workflows.mini_spider_04.result_processor import ResultProcessor
        print("✅ ResultProcessor imported successfully")
        
        from workflows.mini_spider_04.core.url_deduplicator import AdvancedURLDeduplicator
        print("✅ AdvancedURLDeduplicator imported successfully")
        
        from workflows.mini_spider_04.core.response_filter import ResponseFilter
        print("✅ ResponseFilter imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_instantiation():
    """Test that classes can be instantiated"""
    print("\nTesting instantiation...")
    
    try:
        from workflows.mini_spider_04.scanner import MiniSpiderScanner
        from workflows.mini_spider_04.config import get_spider_config
        from workflows.mini_spider_04.models import CrawledURL, DiscoverySource
        
        # Test scanner instantiation
        scanner = MiniSpiderScanner()
        print(f"✅ MiniSpiderScanner instantiated: {scanner.name}")
        
        # Test configuration
        config = get_spider_config()
        print(f"✅ Spider config loaded: max_urls={config.max_total_urls}")
        
        # Test model creation
        test_url = CrawledURL(
            url="https://example.com/test",
            source=DiscoverySource.SEED
        )
        print(f"✅ CrawledURL created: {test_url.url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Instantiation error: {e}")
        traceback.print_exc()
        return False

def test_input_validation():
    """Test input validation"""
    print("\nTesting input validation...")
    
    try:
        from workflows.mini_spider_04.utils import validate_input
        
        # Valid input
        is_valid, errors = validate_input("example.com")
        if is_valid:
            print("✅ Valid input passed validation")
        else:
            print(f"❌ Valid input failed: {errors}")
            return False
        
        # Invalid input
        is_valid, errors = validate_input("")
        if not is_valid:
            print("✅ Invalid input correctly rejected")
        else:
            print("❌ Invalid input incorrectly accepted")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        traceback.print_exc()
        return False

def test_tool_availability():
    """Test tool availability checking"""
    print("\nTesting tool availability...")
    
    try:
        from workflows.mini_spider_04.config import validate_tools
        
        tools = validate_tools()
        print(f"✅ Tool availability checked:")
        for tool, available in tools.items():
            status = "✅" if available else "⚠️"
            print(f"   {status} {tool}: {available}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool validation error: {e}")
        traceback.print_exc()
        return False

def test_url_processing():
    """Test URL processing utilities"""
    print("\nTesting URL processing...")
    
    try:
        from workflows.mini_spider_04.models import CrawledURL, DiscoverySource
        from workflows.mini_spider_04.utils import deduplicate_urls
        from workflows.mini_spider_04.core.url_deduplicator import deduplicate_urls_advanced
        
        # Create test URLs
        test_urls = [
            CrawledURL(url="https://example.com/", source=DiscoverySource.SEED),
            CrawledURL(url="https://example.com/admin", source=DiscoverySource.CUSTOM_CRAWLER),
            CrawledURL(url="https://example.com/", source=DiscoverySource.HAKRAWLER),  # Duplicate
            CrawledURL(url="https://example.com/api/", source=DiscoverySource.HTTP_03),
        ]
        
        # Test basic deduplication
        unique_urls = deduplicate_urls(test_urls)
        print(f"✅ Basic deduplication: {len(test_urls)} -> {len(unique_urls)} URLs")
        
        # Test advanced deduplication
        advanced_unique, stats = deduplicate_urls_advanced(test_urls)
        print(f"✅ Advanced deduplication: {len(test_urls)} -> {len(advanced_unique)} URLs")
        print(f"   Stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ URL processing error: {e}")
        traceback.print_exc()
        return False

async def test_workflow_execution():
    """Test basic workflow execution (without external dependencies)"""
    print("\nTesting workflow execution...")
    
    try:
        from workflows.mini_spider_04.scanner import MiniSpiderScanner
        
        scanner = MiniSpiderScanner()
        
        # Test input validation
        is_valid, errors = scanner.validate_input("example.com")
        if is_valid:
            print("✅ Workflow input validation passed")
        else:
            print(f"❌ Workflow input validation failed: {errors}")
            return False
        
        # Mock HTTP_03 results for testing
        mock_http_results = {
            "success": True,
            "data": {
                "target": "example.com",
                "services": [
                    {
                        "url": "https://example.com/",
                        "port": 443,
                        "scheme": "https",
                        "status_code": 200,
                        "headers": {"server": "nginx"},
                        "discovered_paths": ["/admin", "/api"]
                    }
                ],
                "dns_records": [],
                "subdomains": []
            }
        }
        
        # Test URL extraction from HTTP results
        from workflows.mini_spider_04.url_extractor import URLExtractor
        extractor = URLExtractor()
        extracted_urls = await extractor.extract_from_http_results(mock_http_results)
        print(f"✅ URL extraction: {len(extracted_urls)} URLs extracted from mock data")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow execution error: {e}")
        traceback.print_exc()
        return False

async def test_result_processing():
    """Test result processing"""
    print("\nTesting result processing...")
    
    try:
        from workflows.mini_spider_04.models import CrawledURL, DiscoverySource
        from workflows.mini_spider_04.result_processor import ResultProcessor
        
        processor = ResultProcessor()
        
        # Create test URLs
        test_urls = [
            CrawledURL(url="https://example.com/admin", source=DiscoverySource.CUSTOM_CRAWLER, status_code=200),
            CrawledURL(url="https://example.com/api/v1", source=DiscoverySource.HAKRAWLER, status_code=401),
            CrawledURL(url="https://example.com/.git/config", source=DiscoverySource.HTTP_03, status_code=200),
        ]
        
        # Process results
        results = await processor.process_results(test_urls, "example.com")
        
        print(f"✅ Result processing completed:")
        print(f"   Categories: {list(results['categories'].keys())}")
        print(f"   Interesting findings: {len(results['interesting'])}")
        print(f"   Statistics: {results['statistics']['total_discovered_urls']} URLs processed")
        
        return True
        
    except Exception as e:
        print(f"❌ Result processing error: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🕷️  Mini Spider Workflow Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Instantiation Tests", test_instantiation),
        ("Input Validation Tests", test_input_validation),
        ("Tool Availability Tests", test_tool_availability),
        ("URL Processing Tests", test_url_processing),
        ("Workflow Execution Tests", test_workflow_execution),
        ("Result Processing Tests", test_result_processing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Mini Spider workflow is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)