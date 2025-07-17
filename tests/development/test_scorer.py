#!/usr/bin/env python3
"""
Simple test script for the wordlist scorer system.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.scorer import score_wordlists, ScoringContext
from database.scorer.scorer_engine import explain_scoring, get_scoring_stats


def test_exact_match():
    """Test exact match rules."""
    print("=== Test: Exact Match (WordPress on HTTPS) ===")
    
    context = ScoringContext(
        target="example.com",
        port=443,
        service="Apache/2.4.41 (Ubuntu) OpenSSL/1.1.1f",
        tech="wordpress"
    )
    
    result = score_wordlists(context)
    print(f"Score: {result.score}")
    print(f"Confidence: {result.confidence}")
    print(f"Wordlists: {result.wordlists}")
    print(f"Rules: {result.matched_rules}")
    print()


def test_tech_category():
    """Test technology category fallback."""
    print("=== Test: Tech Category (Unknown CMS) ===")
    
    context = ScoringContext(
        target="example.com",
        port=80,
        service="Some CMS system v2.1",
        tech="unknowncms"
    )
    
    result = score_wordlists(context)
    print(f"Score: {result.score}")
    print(f"Confidence: {result.confidence}")
    print(f"Wordlists: {result.wordlists}")
    print(f"Rules: {result.matched_rules}")
    print()


def test_pattern_fallback():
    """Test pattern matching fallback."""
    print("=== Test: Pattern Fallback (Content Management in Service) ===")
    
    context = ScoringContext(
        target="example.com",
        port=80,
        service="Custom Content Management System v1.0",
        tech=None
    )
    
    result = score_wordlists(context)
    print(f"Score: {result.score}")
    print(f"Confidence: {result.confidence}")
    print(f"Wordlists: {result.wordlists}")
    print(f"Rules: {result.matched_rules}")
    print()


def test_port_category():
    """Test port category rules."""
    print("=== Test: Port Category (Database Port) ===")
    
    context = ScoringContext(
        target="192.168.1.100",
        port=3306,
        service="MySQL Community Server v8.0.28",
        tech=None
    )
    
    result = score_wordlists(context)
    print(f"Score: {result.score}")
    print(f"Confidence: {result.confidence}")
    print(f"Wordlists: {result.wordlists}")
    print(f"Rules: {result.matched_rules}")
    print()


def test_generic_fallback():
    """Test generic fallback."""
    print("=== Test: Generic Fallback (Unknown Service) ===")
    
    context = ScoringContext(
        target="192.168.1.200",
        port=9999,
        service="Unknown service on custom port",
        tech=None
    )
    
    result = score_wordlists(context)
    print(f"Score: {result.score}")
    print(f"Confidence: {result.confidence}")
    print(f"Wordlists: {result.wordlists}")
    print(f"Rules: {result.matched_rules}")
    print(f"Fallback used: {result.fallback_used}")
    print()


def test_detailed_explanation():
    """Test detailed explanation output."""
    print("=== Test: Detailed Explanation ===")
    
    context = ScoringContext(
        target="example.com",
        port=8080,
        service="Apache Tomcat/9.0.50 with admin panel",
        tech="tomcat"
    )
    
    result = score_wordlists(context)
    explanation = explain_scoring(result)
    print(explanation)
    print()


def test_scoring_stats():
    """Test scoring system statistics."""
    print("=== Scoring System Statistics ===")
    
    stats = get_scoring_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    print()


def main():
    """Run all tests."""
    print("Wordlist Scorer System Test")
    print("=" * 50)
    print()
    
    try:
        test_exact_match()
        test_tech_category()
        test_pattern_fallback()
        test_port_category()
        test_generic_fallback()
        test_detailed_explanation()
        test_scoring_stats()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())