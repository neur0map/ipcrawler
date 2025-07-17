#!/usr/bin/env python3
"""
Test script for SecLists integration and wordlist scoring system.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.scorer import score_wordlists, score_wordlists_with_catalog, ScoringContext, get_scoring_stats
from database.wordlists.resolver import resolver


def test_basic_scorer():
    """Test basic scorer functionality without catalog."""
    print("=== Testing Basic Scorer (No Catalog) ===")
    
    context = ScoringContext(
        target="example.com",
        port=443,
        service="nginx/1.18.0 (Ubuntu)",
        tech="wordpress"
    )
    
    result = score_wordlists(context)
    print(f"Score: {result.score}")
    print(f"Confidence: {result.confidence}")
    print(f"Wordlists: {result.wordlists[:5]}")
    print(f"Rules: {result.matched_rules}")
    print()


def test_enhanced_scorer():
    """Test enhanced scorer with catalog (if available)."""
    print("=== Testing Enhanced Scorer (With Catalog) ===")
    
    context = ScoringContext(
        target="example.com",
        port=443,
        service="nginx/1.18.0 (Ubuntu)",
        tech="wordpress"
    )
    
    result = score_wordlists_with_catalog(context)
    print(f"Score: {result.score}")
    print(f"Confidence: {result.confidence}")
    print(f"Wordlists: {result.wordlists[:5]}")
    print(f"Rules: {result.matched_rules}")
    
    # Check if catalog metadata is available
    if hasattr(result, 'catalog_metadata'):
        print(f"Catalog Enhanced: {result.catalog_metadata.get('catalog_enhanced', False)}")
        print(f"Catalog Entries: {result.catalog_metadata.get('catalog_entries_count', 0)}")
    print()


def test_catalog_availability():
    """Test catalog availability and stats."""
    print("=== Catalog Availability Test ===")
    
    is_available = resolver.is_available()
    print(f"Catalog Available: {is_available}")
    
    if is_available:
        stats = resolver.get_catalog_stats()
        print(f"Total Wordlists: {stats.get('total_wordlists', 0)}")
        print(f"Categories: {stats.get('categories', 0)}")
        print(f"Technologies: {stats.get('technologies', 0)}")
    else:
        print("Catalog not loaded - this is normal if SecLists isn't installed yet")
    
    print()


def test_scoring_stats():
    """Test scoring system statistics."""
    print("=== Scoring System Statistics ===")
    
    stats = get_scoring_stats()
    print(f"Exact Rules: {stats['exact_rules']}")
    print(f"Tech Categories: {stats['tech_categories']}")
    print(f"Port Categories: {stats['port_categories']}")
    print(f"Total Wordlists (rules): {stats['total_wordlists']}")
    print(f"Catalog Available: {stats['catalog_available']}")
    
    if 'catalog_stats' in stats:
        catalog_stats = stats['catalog_stats']
        print(f"Catalog Wordlists: {catalog_stats.get('total_wordlists', 0)}")
    
    print()


def test_different_contexts():
    """Test scorer with different service contexts."""
    print("=== Testing Different Service Contexts ===")
    
    test_cases = [
        {
            "name": "WordPress HTTPS",
            "context": ScoringContext(
                target="site.com", port=443, service="nginx", tech="wordpress"
            )
        },
        {
            "name": "MySQL Database",
            "context": ScoringContext(
                target="db.company.com", port=3306, service="MySQL 8.0", tech="mysql"
            )
        },
        {
            "name": "Jenkins CI/CD",
            "context": ScoringContext(
                target="jenkins.company.com", port=8080, service="Jetty", tech="jenkins"
            )
        },
        {
            "name": "Unknown Service",
            "context": ScoringContext(
                target="unknown.com", port=9999, service="Custom service", tech=None
            )
        }
    ]
    
    for test_case in test_cases:
        print(f"{test_case['name']}:")
        result = score_wordlists_with_catalog(test_case['context'])
        print(f"  Score: {result.score:.3f} ({result.confidence})")
        print(f"  Top wordlists: {result.wordlists[:3]}")
        print(f"  Rules: {result.matched_rules}")
        print()


def test_seclists_check():
    """Test SecLists installation check."""
    print("=== SecLists Installation Check ===")
    
    # Check if .seclists_path file exists
    seclists_path_file = Path(".seclists_path")
    if seclists_path_file.exists():
        try:
            with open(seclists_path_file, 'r') as f:
                content = f.read().strip()
                print(f"SecLists path file content: {content}")
        except Exception as e:
            print(f"Error reading .seclists_path: {e}")
    else:
        print("No .seclists_path file found")
    
    # Check catalog file
    catalog_file = Path("database/wordlists/seclists_catalog.json")
    if catalog_file.exists():
        size_mb = catalog_file.stat().st_size / (1024 * 1024)
        print(f"Catalog file exists: {catalog_file} ({size_mb:.1f}MB)")
    else:
        print("No catalog file found - will be generated after SecLists installation")
    
    print()


def main():
    """Run all tests."""
    print("SecLists Integration Test Suite")
    print("=" * 50)
    print()
    
    try:
        test_seclists_check()
        test_basic_scorer()
        test_enhanced_scorer()
        test_catalog_availability()
        test_scoring_stats()
        test_different_contexts()
        
        print("✅ All tests completed!")
        print()
        print("Next Steps:")
        print("1. Run 'make install' to set up SecLists and generate catalog")
        print("2. Enhanced scoring will automatically use catalog when available")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())