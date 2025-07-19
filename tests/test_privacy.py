#!/usr/bin/env python3
"""Test privacy features of the cache system."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.scorer.models import ScoringContext, ScoringResult, ScoreBreakdown, Confidence
from src.core.scorer.cache import cache

# Create test context with sensitive data
test_context = ScoringContext(
    target="192.168.1.100",  # Sensitive IP
    port=443,
    service="nginx 1.20.1",
    tech="nginx",
    os="Linux Ubuntu 20.04",
    version="1.20.1",
    headers={"Server": "nginx/1.20.1"}
)

# Create test result
test_result = ScoringResult(
    score=0.95,
    explanation=ScoreBreakdown(
        exact_match=1.0,
        tech_category=0.8,
        port_context=0.6
    ),
    wordlists=["nginx-locations.txt", "nginx-config.txt", "web-content.txt"],
    matched_rules=["exact:nginx:443", "tech_category:web_server", "port:web_secure"],
    fallback_used=False,
    cache_key="test_key",
    confidence=Confidence.HIGH
)

# Save to cache (should be anonymized)
print("🔒 Testing privacy-safe cache saving...")
entry_id = cache.save_selection(test_context, test_result)
print(f"✅ Saved as: {entry_id}")

# Read it back
print("\n📖 Reading back from cache...")
retrieved = cache.get_selection(entry_id)

if retrieved:
    print("✅ Retrieved successfully")
    print(f"   Port category: {retrieved.context.port_category}")
    print(f"   Tech family: {retrieved.context.tech_family}")
    print(f"   Service fingerprint: {retrieved.context.service_fingerprint}")
    
    # Check for sensitive data
    context_dict = retrieved.context.model_dump()
    if 'target' in context_dict:
        print("❌ ERROR: Target field found in anonymized context!")
    else:
        print("✅ No sensitive target information found")
    
    if any('192.168' in str(v) for v in context_dict.values()):
        print("❌ ERROR: IP address found in anonymized context!")
    else:
        print("✅ No IP addresses found")
else:
    print("❌ Failed to retrieve")

print("\n🎉 Privacy test complete!")