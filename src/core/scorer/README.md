# Wordlist Scorer System

A rule-based scoring engine for intelligent wordlist recommendation in penetration testing and reconnaissance workflows.

## Overview

The Wordlist Scorer System analyzes service context (technology stack, ports, service descriptions) and recommends the most relevant wordlists using a hierarchical rule-based approach with graceful fallbacks.

## Key Features

- **Hierarchical Rule System**: Exact matches → Tech categories → Port categories → Generic fallback
- **Transparent Scoring**: Full breakdown of why specific wordlists were chosen
- **Graceful Fallbacks**: Never fails to provide useful recommendations
- **Cache System**: Tracks selections and outcomes for continuous improvement
- **Explainable Results**: Clear reasoning for all recommendations
- **High Performance**: Fast lookups with deterministic results

## Quick Start

```python
from src.core.scorer import score_wordlists, ScoringContext

# Create context from scan results
context = ScoringContext(
    target="example.com",
    port=443,
    service="nginx/1.18.0 (Ubuntu)",
    tech="wordpress"
)

# Get wordlist recommendations
result = score_wordlists(context)

print(f"Score: {result.score} ({result.confidence})")
print(f"Wordlists: {result.wordlists}")
print(f"Rules matched: {result.matched_rules}")
```

## Rule Hierarchy

### Level 1: Exact Match (weight: 1.0)
Direct tech + port combinations:
- `wordpress` + `443` → wordpress-https.txt, wp-plugins.txt
- `tomcat` + `8080` → tomcat-manager.txt, java-servlets.txt
- `mysql` + `3306` → mysql-admin.txt, phpmyadmin.txt

### Level 2: Tech Category (weight: 0.8)
Technology pattern matching:
- **CMS**: wordpress, drupal, joomla → cms-common.txt
- **Web Server**: apache, nginx, iis → common-web.txt
- **Database**: mysql, postgres, mongodb → database-admin.txt
- **Framework**: django, rails, laravel → framework-common.txt

### Level 3: Port Category (weight: 0.6)
Port-based categorization:
- **Web**: 80, 443, 8080 → common.txt, dirs.txt
- **Database**: 3306, 5432, 27017 → database-common.txt
- **Admin**: 8080, 9090, 10000 → admin-panels.txt

### Level 4: Generic Fallback (weight: 0.4)
Always-applicable wordlists:
- common.txt, discovery.txt, dirs.txt, files.txt

## Architecture

```
src/core/scorer/
├── __init__.py          # Main module exports
├── models.py            # Pydantic data models
├── scorer_engine.py     # Core scoring logic
├── rules.py             # Rule engine and management
├── mappings.py          # Rule definitions and mappings
├── cache.py             # Selection tracking and caching
└── README.md           # This file

database/scorer/
└── contributions/       # Cache storage
    ├── selections/      # Daily selection records
    └── index.json       # Cache statistics
```

## Scoring Examples

### High Confidence (0.8+)
```python
# Exact match
context = ScoringContext(target="site.com", port=443, tech="wordpress")
# Result: score=1.0, confidence=HIGH
```

### Medium Confidence (0.6-0.8)
```python
# Pattern matching
context = ScoringContext(target="site.com", port=80, service="CMS Platform v2.1")
# Result: score=0.6, confidence=MEDIUM (tech_pattern:cms)
```

### Low Confidence (0.4-0.6)
```python
# Generic fallback
context = ScoringContext(target="site.com", port=9999, service="Unknown service")
# Result: score=0.4, confidence=LOW (generic_fallback)
```

## Cache System

The scorer automatically tracks all selections for analysis:

```python
from src.core.scorer import cache

# Get recent selections
entries = cache.search_selections(tech="wordpress", days_back=30)

# Get successful patterns
patterns = cache.get_successful_patterns(min_findings=5)

# Get cache statistics
stats = cache.get_stats()
```

### Cache Storage Format

```json
{
  "timestamp": "2024-01-16T10:30:00Z",
  "context": {
    "target": "example.com",
    "port": 443,
    "service": "nginx/1.18.0",
    "tech": "wordpress"
  },
  "result": {
    "score": 1.0,
    "wordlists": ["wordpress-https.txt", "wp-plugins.txt"],
    "matched_rules": ["exact:wordpress:443"]
  },
  "outcome": {
    "wordlists_used": ["wordpress-https.txt"],
    "findings": 23,
    "success": true
  }
}
```

## API Reference

### Main Functions

- `score_wordlists(context)` → `ScoringResult`
- `explain_scoring(result)` → `str`
- `get_scoring_stats()` → `dict`

### Core Models

- `ScoringContext`: Input context (target, port, service, tech)
- `ScoringResult`: Complete scoring result with explanation
- `ScoreBreakdown`: Detailed score components
- `Confidence`: HIGH, MEDIUM, LOW

## Configuration

### Adding New Rules

Add exact matches in `mappings.py`:
```python
EXACT_MATCH_RULES[("newtech", 8080)] = ["newtech-paths.txt"]
```

Add tech categories:
```python
TECH_CATEGORY_RULES["new_category"] = {
    "matches": ["tech1", "tech2"],
    "wordlists": ["category-wordlist.txt"],
    "fallback_pattern": r"(pattern)",
    "weight": 0.8
}
```

### Rule Validation

```python
from src.core.scorer.rules import rule_engine

issues = rule_engine.validate_rules()
print(issues["warnings"])  # Potential issues
print(issues["errors"])    # Critical errors
```

## Performance

- **Lookups**: O(1) for exact matches, O(n) for pattern matching
- **Memory**: Minimal - rules loaded once at startup
- **Caching**: Automatic background caching with no performance impact
- **Throughput**: >1000 requests/second on typical hardware

## Integration

### With IPCrawler

```python
# In your scanning workflow
from src.core.scorer import score_wordlists, ScoringContext

def get_wordlist_recommendations(scan_result):
    context = ScoringContext(
        target=scan_result.target,
        port=scan_result.port,
        service=scan_result.service_banner,
        tech=scan_result.detected_tech
    )
    
    result = score_wordlists(context)
    return result.wordlists[:5]  # Top 5 recommendations
```

### With Custom Tools

```python
# Simple integration
def recommend_wordlists(target, port, service):
    context = ScoringContext(target=target, port=port, service=service)
    result = score_wordlists(context)
    
    return {
        "wordlists": result.wordlists,
        "confidence": result.confidence,
        "reasoning": result.matched_rules
    }
```

## Future Enhancements

When the SecLists catalog is integrated:
1. **Enhanced Mappings**: More specific wordlist mappings
2. **Scoring Refinement**: Feedback-based weight adjustments  
3. **Success Tracking**: Learning from actual findings
4. **Dynamic Rules**: Auto-generated rules from successful patterns

## Testing

Run tests:
```bash
python tests/development/test_scorer.py
```

Run examples:
```bash
# Examples are integrated in the test files
```

## Troubleshooting

### Common Issues

**No wordlists returned**:
- Check if `ScoringContext` has valid data
- Generic fallback should always provide wordlists

**Low confidence scores**:
- Add specific rules for your technology stack
- Check if service description contains detectable patterns

**Cache errors**:
- Verify write permissions in `cache/` directory
- Check disk space for cache storage

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now scorer will output detailed debug information
result = score_wordlists(context)
```

## License

Part of IPCrawler - Internal reconnaissance tool.