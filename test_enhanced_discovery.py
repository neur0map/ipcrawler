#!/usr/bin/env python3
"""
Test script to demonstrate enhanced path discovery with validation and logging
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path  
sys.path.insert(0, str(Path(__file__).parent))

from workflows.http_03.models import HTTPService
from workflows.http_03.scanner import HTTPAdvancedScanner

async def test_enhanced_discovery():
    """Test enhanced discovery with detailed logging and validation"""
    print("🔧 Testing Enhanced Path Discovery & Validation")
    print("=" * 60)
    
    # Create scanner instance
    scanner = HTTPAdvancedScanner()
    
    # Mock a Caddy service (like your real test)
    service = HTTPService(
        port=80,
        scheme="http", 
        url="http://httpbin.org",  # Using httpbin for testing
        server="Caddy",
        technologies=["caddy"],
        headers={"Server": "Caddy"},
        response_body='<html><head><title>HTTPBin</title></head><body><h1>HTTPBin Test Service</h1></body></html>'
    )
    
    scanner.original_ip = "httpbin.org"
    
    print(f"🎯 Target: {service.url}")
    print(f"🏷️  Technology: {service.technologies}")
    print(f"🖥️  Server: {service.server}")
    
    print("\\n📋 Configuration:")
    config = scanner.config
    smartlist_config = config.get('smartlist', {})
    discovery_config = config.get('discovery', {})
    
    print(f"   SmartList enabled: {smartlist_config.get('enabled')}")
    print(f"   Validation strictness: {discovery_config.get('validation_strictness')}")
    print(f"   Filter false positives: {discovery_config.get('filter_false_positives')}")
    print(f"   Max concurrent requests: {smartlist_config.get('max_concurrent_requests')}")
    
    print("\\n🚀 Starting enhanced path discovery...")
    print("=" * 60)
    
    try:
        # Run enhanced discovery
        discovered_paths = await scanner._discover_paths(service)
        
        print("\\n📊 Discovery Results:")
        print("-" * 40)
        print(f"Total paths discovered: {len(discovered_paths)}")
        
        if service.discovery_metadata:
            metadata = service.discovery_metadata
            print(f"Discovery method: {metadata.discovery_method}")
            print(f"Wordlist used: {metadata.wordlist_used or 'N/A'}")
            print(f"Confidence: {metadata.confidence or 'N/A'}")
            print(f"Total paths tested: {metadata.total_paths_tested}")
            print(f"Successful paths: {metadata.successful_paths}")
            print(f"Discovery time: {metadata.discovery_time:.2f}s")
        
        if service.smartlist_recommendations:
            print(f"\\n🎯 SmartList Recommendations ({len(service.smartlist_recommendations)}):")
            for i, rec in enumerate(service.smartlist_recommendations[:3]):
                print(f"   {i+1}. {rec.get('wordlist', 'Unknown')} (confidence: {rec.get('confidence')}, score: {rec.get('score')})")
        
        if discovered_paths:
            print(f"\\n📁 Sample Discovered Paths (showing first 10):")
            for path in discovered_paths[:10]:
                print(f"   ✓ {path}")
            
            if len(discovered_paths) > 10:
                print(f"   ... and {len(discovered_paths) - 10} more")
        
        print(f"\\n✅ Enhanced discovery completed successfully!")
        print(f"   Instead of potentially 300+ unvalidated paths,")
        print(f"   you now have {len(discovered_paths)} validated, meaningful paths.")
        
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function"""
    print("🧪 Enhanced HTTP Discovery Test")
    print("This test demonstrates the new features:")
    print("• Detailed command logging of SmartList operations")
    print("• Intelligent path validation and filtering")
    print("• Statistical tracking of discovery performance")
    print("• Configurable validation strictness")
    print("")
    
    try:
        asyncio.run(test_enhanced_discovery())
    except KeyboardInterrupt:
        print("\\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()