# SmartList Algorithm Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Scoring Algorithm](#scoring-algorithm)
5. [Rule Hierarchy](#rule-hierarchy)
6. [Implementation Guide](#implementation-guide)
7. [Workflow Integration](#workflow-integration)
8. [API Reference](#api-reference)
9. [Examples](#examples)
10. [Performance & Optimization](#performance--optimization)

## Overview

**SmartList** is an intelligent wordlist scoring and recommendation algorithm designed to automatically select the most appropriate wordlists for web fuzzing based on service context. The algorithm uses a three-tier architecture with proper separation of concerns, ensuring optimal wordlist selection for any scenario.

### Key Features
- **Three-Tier Architecture**: Port Database + Rule-based Scorer + SecLists Catalog
- **Context-Aware Scoring**: Considers technology stack, port numbers, service banners, and HTTP headers
- **Port Database Integration**: Automatic technology extraction from service detection
- **SecLists Integration**: Real file paths and comprehensive wordlist metadata
- **Transparent Scoring**: Detailed breakdown of scoring decisions for debugging and optimization
- **Caching System**: Tracks selections and outcomes for continuous improvement
- **Confidence Levels**: HIGH, MEDIUM, LOW confidence ratings based on match quality

## Architecture

### Three-Tier System Design

The SmartList algorithm employs a **separation of concerns** architecture with three distinct tiers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SmartList Algorithm                          │
├─────────────────────┬─────────────────────┬─────────────────────┤
│   Port Database     │   Rule-based        │   SecLists          │
│   (Context)         │   Scorer            │   Catalog           │
│                     │   (Logic)           │   (Data)            │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ • Technology Stack  │ • Exact Matches     │ • File Paths        │
│ • Service Info      │ • Tech Categories   │ • Wordlist Metadata │
│ • Attack Vectors    │ • Port Categories   │ • Quality Ratings   │
│ • Risk Assessment   │ • Keyword Rules     │ • Compatibility     │
│ • CTF/HTB Context   │ • Fallback Logic    │ • Sample Entries    │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

### Tier 1: Port Database (Technology & Service Intelligence)

**Purpose**: Provides comprehensive service and technology context without wordlist metadata.

**Responsibilities**:
- **Technology Extraction**: Extract tech stack from service detection (`mysql`, `apache`, `wordpress`)
- **Service Classification**: Categorize services (web, database, remote-access) 
- **Risk Assessment**: Evaluate exploitation potential and exposure levels
- **CTF/HTB Context**: Provide scenario-specific attack vectors and techniques

**What it DOESN'T contain**:
- ❌ Wordlist recommendations 
- ❌ File paths
- ❌ Scoring modifiers

### Tier 2: Rule-based Scorer (Intelligent Selection Logic)

**Purpose**: Core algorithm that applies hierarchical rules to select appropriate wordlists.

**Responsibilities**:
- **Context Enrichment**: Enhance scoring context with port database information
- **Hierarchical Matching**: Apply 5-level rule hierarchy (exact → tech → port → keywords → fallback)
- **Scoring Logic**: Calculate relevance scores and confidence levels
- **Rule Management**: Maintain hardcoded technology/port/service mappings

### Tier 3: SecLists Catalog (Wordlist Data & Metadata)

**Purpose**: Comprehensive wordlist database with actual file paths and enhanced metadata.

**Responsibilities**:
- **File Path Resolution**: Convert wordlist names to actual filesystem paths
- **Metadata Management**: Quality ratings, compatibility info, sample entries
- **Fuzzy Matching**: Handle naming variations and similar wordlists
- **Relevance Scoring**: Advanced scoring based on technology and port context

### System Components

```
SmartList Algorithm
├── Port Database (database/ports/)
│   ├── port_db.json - Service and technology data
│   ├── models.py - Port entry models and utilities
│   └── db.md - Documentation and port status
├── Rule-based Scorer (database/scorer/)
│   ├── scorer_engine.py - Main scoring algorithm
│   ├── rules.py - Rule application engine
│   ├── mappings.py - Hardcoded rule mappings
│   ├── models.py - Scoring context and result models
│   └── cache.py - Selection tracking and caching
└── SecLists Catalog (database/wordlists/)
    ├── resolver.py - Wordlist path resolution
    ├── models.py - Catalog and entry models
    ├── generate_catalog.py - Catalog generation from SecLists
    └── seclists_catalog.json - Generated wordlist metadata
```

### Data Flow

```
1. Input: ScoringContext(target, port, service, tech?)
   │
2. Port Database Enhancement
   │ ┌─ Extract technology stack from port database
   │ └─ Enrich context with service classification
   │
3. Rule-based Scoring
   │ ┌─ Apply exact match rules (tech + port)
   │ ├─ Apply technology category rules  
   │ ├─ Apply port category rules
   │ ├─ Apply service keyword rules
   │ └─ Apply generic fallback if needed
   │
4. SecLists Catalog Resolution
   │ ┌─ Resolve wordlist names to file paths
   │ ├─ Apply fuzzy matching for similar names
   │ ├─ Score entries by relevance
   │ └─ Return top-ranked wordlists with paths
   │
5. Output: ScoringResult(wordlists, paths, explanation)
```

## Core Components

### 1. ScoringContext (Input Model)

The `ScoringContext` model captures all relevant information about a target service:

```python
from database.scorer.models import ScoringContext

context = ScoringContext(
    target="example.com",           # Target IP or hostname
    port=443,                       # Port number (1-65535)
    service="nginx/1.21.0",         # Service banner from scan
    tech="wordpress",               # Detected technology (optional)
    os="Linux",                     # Operating system (optional)
    version="5.8.1",                # Service version (optional)
    headers={                       # HTTP headers (optional)
        "Server": "nginx/1.21.0",
        "X-Powered-By": "PHP/7.4"
    }
)
```

### 2. ScoringResult (Output Model)

The algorithm returns a `ScoringResult` containing:

```python
class ScoringResult:
    score: float                    # Final score (0.0-1.0)
    explanation: ScoreBreakdown     # Detailed score breakdown
    wordlists: List[str]            # Recommended wordlist names
    matched_rules: List[str]        # Rules that matched
    fallback_used: bool             # Whether generic fallback was used
    cache_key: str                  # Unique cache identifier
    confidence: Confidence          # HIGH, MEDIUM, or LOW
```

### 3. ScoreBreakdown

Detailed breakdown of scoring components:

```python
class ScoreBreakdown:
    exact_match: float          # Score from exact tech+port match (0.0-1.0)
    tech_category: float        # Score from technology category match
    port_context: float         # Score from port-based category
    service_keywords: float     # Score from service keyword matching
    generic_fallback: float     # Score from generic fallback
```

## Scoring Algorithm

### Algorithm Flow

```python
def score_wordlists(context: ScoringContext) -> ScoringResult:
    """
    Main scoring algorithm with 5-level hierarchy:
    
    1. Exact Match (tech + port) - Score: 1.0
    2. Technology Category - Score: 0.8
    3. Port Category - Score: 0.6
    4. Service Keywords - Score: 0.5
    5. Generic Fallback - Score: 0.4
    """
```

### Detailed Algorithm Steps

1. **Initialization**
   ```python
   breakdown = ScoreBreakdown()
   all_wordlists = set()
   matched_rules = []
   ```

2. **Level 1: Exact Match Rules**
   - Checks for exact technology + port combinations
   - Example: `("wordpress", 443)` → `["wordpress-https.txt", "wp-plugins.txt"]`
   - Highest priority (score: 1.0)

3. **Level 2: Technology Category Rules**
   - Groups similar technologies
   - Example: CMS category includes WordPress, Drupal, Joomla
   - Fallback pattern matching on service banners
   - Score: 0.8 (0.6 for pattern matches)

4. **Level 3: Port Category Rules**
   - Port-based categorization
   - Example: Ports 80, 443, 8080 → "web" category
   - Always applied for fallback support
   - Score: 0.6

5. **Level 4: Service Keyword Matching**
   - Searches for keywords in service descriptions
   - Example: "admin" in service → admin-related wordlists
   - Score: 0.5

6. **Level 5: Generic Fallback**
   - Applied only if no other rules matched
   - Returns basic wordlists: `["common.txt", "discovery.txt", "dirs.txt", "files.txt"]`
   - Score: 0.4

7. **Final Score Calculation**
   ```python
   final_score = max([
       breakdown.exact_match,
       breakdown.tech_category,
       breakdown.port_context,
       breakdown.service_keywords,
       breakdown.generic_fallback
   ])
   ```

8. **Confidence Determination**
   - HIGH: Exact matches or score ≥ 0.8
   - MEDIUM: Score ≥ 0.6
   - LOW: Fallback used or score < 0.6

## Rule Hierarchy

### 1. Exact Match Rules

Located in `mappings.py:EXACT_MATCH_RULES`:

```python
EXACT_MATCH_RULES = {
    ("wordpress", 443): ["wordpress-https.txt", "wp-plugins.txt", "wp-themes.txt"],
    ("tomcat", 8080): ["tomcat-manager.txt", "java-servlets.txt", "tomcat-examples.txt"],
    ("mysql", 3306): ["mysql-admin.txt", "phpmyadmin.txt"],
    # ... 50+ exact combinations
}
```

### 2. Technology Category Rules

Located in `mappings.py:TECH_CATEGORY_RULES`:

```python
TECH_CATEGORY_RULES = {
    "cms": {
        "matches": ["wordpress", "drupal", "joomla", ...],
        "wordlists": ["cms-common.txt", "cms-plugins.txt"],
        "fallback_pattern": r"(cms|content\s*management|blog)",
        "weight": 0.8
    },
    # ... 11 technology categories
}
```

### 3. Port Category Rules

Located in `mappings.py:PORT_CATEGORY_RULES`:

```python
PORT_CATEGORY_RULES = {
    "web": {
        "ports": [80, 443, 8080, 8443, 8000, ...],
        "wordlists": ["common.txt", "dirs.txt", "web-content.txt"],
        "weight": 0.6
    },
    # ... 8 port categories
}
```

### 4. Service Keyword Rules

Located in `mappings.py:SERVICE_KEYWORD_RULES`:

```python
SERVICE_KEYWORD_RULES = {
    "admin": ["admin-panels.txt", "admin-dirs.txt"],
    "api": ["api-endpoints.txt", "rest-api.txt", "graphql.txt"],
    # ... 16 keyword mappings
}
```

## Implementation Guide

### Basic Usage

```python
from database.scorer import score_wordlists, ScoringContext

# 1. Create context from scan results
context = ScoringContext(
    target="192.168.1.100",
    port=8080,
    service="Apache Tomcat/9.0.54",
    tech="tomcat"  # Detected from banner/headers
)

# 2. Score wordlists
result = score_wordlists(context)

# 3. Use recommended wordlists
for wordlist in result.wordlists:
    print(f"Recommended: {wordlist}")

# 4. Check confidence
if result.confidence == "HIGH":
    print("High confidence in recommendations")
```

### Enhanced Usage with Catalog

```python
from database.scorer import score_wordlists_with_catalog, get_wordlist_paths

# 1. Score with SecLists catalog integration
result = score_wordlists_with_catalog(context)

# 2. Get actual file paths
paths = get_wordlist_paths(
    result.wordlists,
    tech=context.tech,
    port=context.port
)

# 3. Use paths in fuzzing tool
for path in paths:
    run_fuzzer(target_url, wordlist_path=path)
```

### Explaining Results

```python
from database.scorer import explain_scoring

# Get human-readable explanation
explanation = explain_scoring(result)
print(explanation)

# Output:
# Wordlist Scoring Result (Score: 1.000, Confidence: HIGH)
# ============================================================
# Matched Rules:
#   • exact:tomcat:8080
# 
# Score Breakdown:
#   • Exact Match: 1.000
# 
# Recommended Wordlists (3):
#    1. tomcat-manager.txt
#    2. java-servlets.txt
#    3. tomcat-examples.txt
```

## Workflow Integration

### Correct Architecture Integration

The SmartList algorithm integrates all three tiers automatically through a single function call:

```python
class WebScanner(BaseWorkflow):
    def _get_intelligent_wordlists(self, context: ScoringContext) -> List[str]:
        """
        Get wordlists using the three-tier SmartList architecture.
        
        This single call automatically:
        1. Enriches context with port database information
        2. Applies rule-based scoring logic  
        3. Resolves wordlists through SecLists catalog
        """
        # Single function call handles all three tiers
        result = score_wordlists_with_catalog(context)
        
        # Get actual file paths for fuzzing tools
        paths = get_wordlist_paths(
            result.wordlists,
            tech=context.tech,
            port=context.port
        )
        
        return paths[:10]  # Top 10 wordlist paths
```

### Enhanced Context Building

The algorithm can now automatically extract technology information from service detection:

```python
def _build_scoring_context(self, service: Dict[str, Any], 
                          previous_results: Dict[str, Any]) -> ScoringContext:
    """Build scoring context - let port database enhance technology info."""
    
    # Basic context from scan results
    context = ScoringContext(
        target=service["target"],
        port=service["port"],
        service=service.get("banner", ""),
        tech=None,  # Let port database provide this automatically
        headers=service.get("headers", {})
    )
    
    # Port database will automatically enhance with:
    # - Technology stack extraction
    # - Service classification
    # - Risk assessment information
    
    return context
```

### Building Context from Scan Results

```python
def _build_scoring_context(self, service: Dict[str, Any], 
                          previous_results: Dict[str, Any]) -> ScoringContext:
    """Build scoring context from service information."""
    
    # Extract technology from various sources
    tech = None
    
    # 1. From Wappalyzer results
    if "wappalyzer" in previous_results:
        techs = previous_results["wappalyzer"].get("technologies", [])
        if techs:
            tech = techs[0]["name"].lower()
    
    # 2. From HTTP headers
    if "http_headers" in service:
        headers = service["http_headers"]
        if "X-Powered-By" in headers:
            tech = headers["X-Powered-By"].split("/")[0].lower()
    
    return ScoringContext(
        target=service["host"],
        port=service["port"],
        service=service.get("service", ""),
        tech=tech,
        headers=service.get("http_headers")
    )
```

### Caching Results

```python
from database.scorer.cache import cache_selection

# Cache the selection for tracking
entry_id = cache_selection(context, result)

# Later, update with outcomes
from database.scorer.cache import cache

outcome = {
    "findings": 47,  # Number of discovered paths
    "wordlists_used": ["tomcat-manager.txt"],
    "execution_time": 120.5,
    "success": True
}

cache.update_outcome(entry_id, outcome)
```

## API Reference

### Core Functions

#### `score_wordlists(context: ScoringContext) -> ScoringResult`
Main scoring function using rule-based system.

**Parameters:**
- `context`: ScoringContext with target information

**Returns:**
- ScoringResult with recommendations and explanations

**Example:**
```python
result = score_wordlists(context)
print(f"Score: {result.score}, Wordlists: {result.wordlists}")
```

#### `score_wordlists_with_catalog(context: ScoringContext) -> ScoringResult`
Enhanced scoring with SecLists catalog integration.

**Parameters:**
- `context`: ScoringContext with target information

**Returns:**
- ScoringResult with catalog-enhanced recommendations

#### `get_wordlist_paths(wordlist_names: List[str], tech: str = None, port: int = None) -> List[str]`
Convert wordlist names to actual file paths.

**Parameters:**
- `wordlist_names`: List of wordlist names

#### `get_port_context(port: int) -> dict`
Extract technology and service context from port database.

**Parameters:**
- `port`: Port number to lookup

**Returns:**
- Dict with port context including technologies, service info, risk level

**Example:**
```python
from database.scorer import get_port_context

context = get_port_context(3306)
print(f"Technologies: {context['technologies']}")
print(f"Service: {context['service_name']}")
print(f"Category: {context['category']}")
```
- `tech`: Technology context (optional)
- `port`: Port context (optional)

**Returns:**
- List of file paths

#### `explain_scoring(result: ScoringResult) -> str`
Generate human-readable explanation of scoring result.

**Parameters:**
- `result`: ScoringResult to explain

**Returns:**
- Formatted explanation string

#### `get_scoring_stats() -> dict`
Get statistics about the scoring system.

**Returns:**
- Dictionary with system statistics

### Models

#### `ScoringContext`
```python
class ScoringContext(BaseModel):
    target: str                     # Required
    port: int                       # Required (1-65535)
    service: str                    # Required
    tech: Optional[str]             # Optional, normalized to lowercase
    os: Optional[str]               # Optional
    version: Optional[str]          # Optional
    headers: Optional[Dict[str, str]]  # Optional HTTP headers
```

#### `ScoringResult`
```python
class ScoringResult(BaseModel):
    score: float                    # 0.0-1.0
    explanation: ScoreBreakdown     # Component scores
    wordlists: List[str]            # Recommendations
    matched_rules: List[str]        # Rule names
    fallback_used: bool             # Generic fallback indicator
    cache_key: str                  # Unique identifier
    confidence: Confidence          # HIGH/MEDIUM/LOW
```

### Cache Functions

#### `cache_selection(context, result, outcome=None) -> str`
Cache a wordlist selection.

**Parameters:**
- `context`: ScoringContext
- `result`: ScoringResult
- `outcome`: Optional outcome data

**Returns:**
- Cache entry ID

#### `cache.search_selections(tech=None, port=None, days_back=30) -> List[CacheEntry]`
Search cached selections.

#### `cache.get_successful_patterns(min_findings=5) -> List[Dict]`
Get patterns of successful wordlist selections.

## Examples

### Example 1: WordPress Site

```python
# WordPress on HTTPS
context = ScoringContext(
    target="blog.example.com",
    port=443,
    service="nginx/1.20.1",
    tech="wordpress",
    headers={
        "Server": "nginx/1.20.1",
        "X-Powered-By": "PHP/7.4.25"
    }
)

result = score_wordlists(context)

# Result:
# Score: 1.0 (Exact match)
# Confidence: HIGH
# Wordlists: ["wordpress-https.txt", "wp-plugins.txt", "wp-themes.txt"]
# Matched Rules: ["exact:wordpress:443"]
```

### Example 2: Unknown CMS

```python
# Unknown CMS with pattern detection
context = ScoringContext(
    target="site.example.com",
    port=80,
    service="Apache/2.4.41 (Ubuntu) - Content Management System",
    tech=None  # Technology not detected
)

result = score_wordlists(context)

# Result:
# Score: 0.6 (Pattern match on "Content Management")
# Confidence: MEDIUM
# Wordlists: ["cms-common.txt", "cms-plugins.txt", "cms-themes.txt"]
# Matched Rules: ["tech_pattern:cms"]
```

### Example 3: Custom Application

```python
# Custom application on non-standard port
context = ScoringContext(
    target="api.internal.com",
    port=9999,
    service="Custom API Server v2.1",
    tech=None
)

result = score_wordlists(context)

# Result:
# Score: 0.4 (Generic fallback)
# Confidence: LOW
# Wordlists: ["common.txt", "discovery.txt", "dirs.txt", "files.txt"]
# Matched Rules: ["generic_fallback"]
# Fallback Used: True
```

### Example 4: Complete Workflow Integration

```python
from database.scorer import score_wordlists_with_catalog, get_wordlist_paths
from database.scorer.cache import cache_selection
import subprocess

def smart_fuzzing_workflow(target_url, scan_results):
    """Complete fuzzing workflow with SmartList."""
    
    # 1. Build context from scan results
    context = ScoringContext(
        target=scan_results["host"],
        port=scan_results["port"],
        service=scan_results["service_banner"],
        tech=scan_results.get("detected_tech"),
        headers=scan_results.get("http_headers")
    )
    
    # 2. Get smart wordlist recommendations
    result = score_wordlists_with_catalog(context)
    
    # 3. Log the selection
    print(f"SmartList Score: {result.score} ({result.confidence})")
    print(f"Using wordlists: {result.wordlists[:5]}")
    
    # 4. Cache the selection
    entry_id = cache_selection(context, result)
    
    # 5. Get actual file paths
    wordlist_paths = get_wordlist_paths(
        result.wordlists[:5],  # Top 5
        tech=context.tech,
        port=context.port
    )
    
    # 6. Run fuzzing with each wordlist
    all_findings = []
    for path in wordlist_paths:
        print(f"Fuzzing with: {path}")
        
        # Run web scanner
        cmd = [
            "scanner_tool",
            "-u", target_url,
            "-w", path,
            "--json",
            "-t", "50"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        findings = parse_scanner_output(result.stdout)
        all_findings.extend(findings)
    
    # 7. Update cache with outcomes
    from database.scorer.cache import cache
    
    outcome = {
        "findings": len(all_findings),
        "wordlists_used": [p.name for p in wordlist_paths],
        "unique_paths": list(set(f["path"] for f in all_findings)),
        "success": len(all_findings) > 0
    }
    
    cache.update_outcome(entry_id, outcome)
    
    return all_findings
```

## Performance & Optimization

### Performance Characteristics

1. **Time Complexity**: O(1) for exact matches, O(n) for pattern matching
2. **Memory Usage**: Minimal - rules are loaded once at startup
3. **Cache Overhead**: Negligible - async writes, indexed lookups

### Optimization Tips

1. **Pre-populate Technology Detection**
   - Use Wappalyzer or similar tools
   - Parse HTTP headers thoroughly
   - Check for technology-specific endpoints

2. **Cache Warming**
   ```python
   # Pre-cache common scenarios
   common_contexts = [
       ("wordpress", 443),
       ("apache", 80),
       ("nginx", 443)
   ]
   
   for tech, port in common_contexts:
       context = ScoringContext(
           target="cache-warm",
           port=port,
           service=f"{tech} service",
           tech=tech
       )
       score_wordlists(context)
   ```

3. **Batch Processing**
   ```python
   # Process multiple targets efficiently
   contexts = [build_context(target) for target in targets]
   results = [score_wordlists(ctx) for ctx in contexts]
   ```

4. **Rule Customization**
   - Add custom rules to `mappings.py`
   - Adjust weights based on your environment
   - Track success rates and optimize

### Monitoring & Analytics

```python
from database.scorer import get_scoring_stats
from database.scorer.cache import cache

# Get system statistics
stats = get_scoring_stats()
print(f"Total rules: {stats['exact_rules'] + stats['tech_categories']}")
print(f"Catalog available: {stats['catalog_available']}")

# Analyze successful patterns
patterns = cache.get_successful_patterns(min_findings=10)
for pattern in patterns[:5]:
    print(f"{pattern['tech']}:{pattern['port']} -> {pattern['findings']} findings")
```

## Conclusion

The SmartList algorithm provides intelligent, context-aware wordlist selection for web fuzzing operations. By combining hierarchical rules, pattern matching, and optional catalog integration, it ensures optimal wordlist selection for any target while maintaining transparency and explainability in its decision-making process.

For questions or contributions, refer to the IPCrawler repository documentation.