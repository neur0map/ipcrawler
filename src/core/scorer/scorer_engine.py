"""
Core scoring engine for wordlist recommendation.
"""

from typing import List, Set, Optional, Dict, Any, Tuple
import logging
from .models import ScoringContext, ScoringResult, ScoreBreakdown, Confidence
from .rules import rule_engine
from .mappings import GENERIC_FALLBACK, get_wordlist_alternatives
from .cache import cache_selection

# Import wordlist resolver
try:
    from ..tools.catalog.resolver import resolver as wordlist_resolver
    WORDLIST_RESOLVER_AVAILABLE = True
except ImportError:
    WORDLIST_RESOLVER_AVAILABLE = False
    wordlist_resolver = None

# Import port database
try:
    import json
    import sys
    from pathlib import Path
    
    # Define project root first
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    from database.ports import PortDatabase, load_port_database
    
    # Load port database on module import
    port_db_path = project_root / "database" / "ports" / "port_db.json"
    if port_db_path.exists():
        with open(port_db_path, 'r', encoding='utf-8') as f:
            port_db_data = json.load(f)
        port_database = load_port_database(port_db_data)
        PORT_DATABASE_AVAILABLE = True
    else:
        port_database = None
        PORT_DATABASE_AVAILABLE = False
except ImportError:
    port_database = None
    PORT_DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)


def enrich_context_with_port_data(context: ScoringContext) -> ScoringContext:
    """
    Enrich scoring context with technology information from port database.
    
    Args:
        context: Original scoring context
        
    Returns:
        Enhanced context with port database technology information
    """
    if not PORT_DATABASE_AVAILABLE or not port_database:
        logger.debug("Port database not available - using original context")
        return context
    
    # Get port entry from database
    port_entry = port_database.get_port(context.port)
    if not port_entry:
        logger.debug(f"No port entry found for port {context.port}")
        return context
    
    # Extract technology information
    tech_stack = port_entry.get_technology_stack()
    
    # If no tech specified in context, try to extract from port database
    enhanced_tech = context.tech
    if not enhanced_tech and tech_stack:
        # Use the most specific technology from the stack
        enhanced_tech = tech_stack[0] if tech_stack else None
        logger.debug(f"Enhanced tech from port DB: {enhanced_tech}")
    
    # Create enhanced context
    enhanced_context = ScoringContext(
        target=context.target,
        port=context.port,
        service=context.service,
        tech=enhanced_tech,
        os=context.os,
        version=context.version,
        headers=context.headers
    )
    
    logger.debug(f"Context enriched with port DB data: tech={enhanced_tech}, stack={tech_stack}")
    return enhanced_context


def score_wordlists(context: ScoringContext) -> ScoringResult:
    """
    Main function to score wordlists based on context with entropy checking.
    
    Args:
        context: ScoringContext with target information
        
    Returns:
        ScoringResult with recommendations and explanations
    """
    # Enrich context with port database information
    enriched_context = enrich_context_with_port_data(context)
    
    logger.debug(f"Scoring wordlists for {enriched_context.target}:{enriched_context.port}")
    
    # Initialize scoring components
    breakdown = ScoreBreakdown()
    all_wordlists: Set[str] = set()
    matched_rules: List[str] = []
    frequency_adjustments: Dict[str, float] = {}
    synergy_bonuses: Dict[str, float] = {}
    
    # Level 1: Exact match rules (highest priority)
    exact_wordlists, exact_rules, exact_score = rule_engine.apply_exact_match(enriched_context)
    if exact_wordlists:
        breakdown.exact_match = exact_score
        all_wordlists.update(exact_wordlists)
        matched_rules.extend(exact_rules)
        logger.debug(f"Exact match: {exact_rules} -> {exact_wordlists}")
    
    # Level 2: Technology category rules
    tech_wordlists, tech_rules, tech_score = rule_engine.apply_tech_category(enriched_context)
    if tech_wordlists:
        breakdown.tech_category = tech_score
        all_wordlists.update(tech_wordlists)
        matched_rules.extend(tech_rules)
        logger.debug(f"Tech category: {tech_rules} -> {tech_wordlists}")
    
    # Level 3: Port category rules (always apply for fallback)
    port_wordlists, port_rules, port_score = rule_engine.apply_port_category(enriched_context)
    if port_wordlists:
        breakdown.port_context = port_score
        all_wordlists.update(port_wordlists)
        matched_rules.extend(port_rules)
        logger.debug(f"Port category: {port_rules} -> {port_wordlists}")
    
    # Level 4: Service keyword matching
    keyword_wordlists, keyword_rules, keyword_score = rule_engine.apply_service_keywords(enriched_context)
    if keyword_wordlists:
        breakdown.service_keywords = keyword_score
        all_wordlists.update(keyword_wordlists)
        matched_rules.extend(keyword_rules)
        logger.debug(f"Service keywords: {keyword_rules} -> {keyword_wordlists}")
    
    # Level 5: Generic fallback if nothing matched
    fallback_used = False
    if not all_wordlists:
        breakdown.generic_fallback = 0.4
        all_wordlists.update(GENERIC_FALLBACK)
        matched_rules.append("generic_fallback")
        fallback_used = True
        logger.debug(f"Generic fallback: {GENERIC_FALLBACK}")
    
    # Calculate final score (take the highest component score)
    final_score = max([
        breakdown.exact_match,
        breakdown.tech_category,
        breakdown.port_context,
        breakdown.service_keywords,
        breakdown.generic_fallback
    ])
    
    # Remove duplicates and sort wordlists
    initial_wordlists = rule_engine.deduplicate_wordlists(list(all_wordlists))
    
    # Apply entropy-based diversification if needed
    final_wordlists, diversification_applied, entropy_score = _apply_entropy_diversification(
        initial_wordlists, enriched_context
    )
    
    # Determine confidence level
    confidence = _determine_confidence(final_score, fallback_used, matched_rules)
    
    # Generate cache key
    cache_key = enriched_context.get_cache_key()
    
    # Create result with entropy data
    result = ScoringResult(
        score=final_score,
        explanation=breakdown,
        wordlists=final_wordlists,
        matched_rules=matched_rules,
        fallback_used=fallback_used,
        cache_key=cache_key,
        confidence=confidence,
        entropy_score=entropy_score,
        diversification_applied=diversification_applied,
        frequency_adjustments=frequency_adjustments or None,
        synergy_bonuses=synergy_bonuses or None
    )
    
    # Format entropy score properly
    entropy_display = f"{entropy_score:.3f}" if entropy_score is not None else "N/A"
    
    logger.info(
        f"Scored {len(final_wordlists)} wordlists for {enriched_context.target}:{enriched_context.port} "
        f"(score: {final_score:.3f}, confidence: {confidence}, entropy: {entropy_display})"
    )
    
    # Cache the selection for tracking
    try:
        cache_selection(enriched_context, result)
    except Exception as e:
        logger.warning(f"Failed to cache selection: {e}")
    
    return result


def _determine_confidence(score: float, fallback_used: bool, matched_rules: List[str]) -> Confidence:
    """
    Determine confidence level based on score and matching conditions.
    
    Args:
        score: Final score
        fallback_used: Whether generic fallback was used
        matched_rules: List of matched rule names
        
    Returns:
        Confidence level
    """
    # If we used fallback, confidence is always low
    if fallback_used:
        return Confidence.LOW
    
    # If we have exact matches, confidence is high
    if any(rule.startswith("exact:") for rule in matched_rules):
        return Confidence.HIGH
    
    # Otherwise use score thresholds
    if score >= 0.8:
        return Confidence.HIGH
    elif score >= 0.6:
        return Confidence.MEDIUM
    else:
        return Confidence.LOW


def explain_scoring(result: ScoringResult) -> str:
    """
    Generate a human-readable explanation of the scoring result.
    
    Args:
        result: ScoringResult to explain
        
    Returns:
        Formatted explanation string
    """
    lines = [
        f"Wordlist Scoring Result (Score: {result.score:.3f}, Confidence: {result.confidence})",
        "=" * 60
    ]
    
    # Add matched rules
    lines.append("Matched Rules:")
    for rule in result.matched_rules:
        lines.append(f"  • {rule}")
    
    lines.append("")
    
    # Add score breakdown
    lines.append("Score Breakdown:")
    breakdown = result.explanation
    
    if breakdown.exact_match > 0:
        lines.append(f"  • Exact Match: {breakdown.exact_match:.3f}")
    
    if breakdown.tech_category > 0:
        lines.append(f"  • Tech Category: {breakdown.tech_category:.3f}")
    
    if breakdown.port_context > 0:
        lines.append(f"  • Port Context: {breakdown.port_context:.3f}")
    
    if breakdown.service_keywords > 0:
        lines.append(f"  • Service Keywords: {breakdown.service_keywords:.3f}")
    
    if breakdown.generic_fallback > 0:
        lines.append(f"  • Generic Fallback: {breakdown.generic_fallback:.3f}")
    
    lines.append("")
    
    # Add recommended wordlists
    lines.append(f"Recommended Wordlists ({len(result.wordlists)}):")
    for i, wordlist in enumerate(result.wordlists, 1):
        lines.append(f"  {i:2d}. {wordlist}")
    
    if result.fallback_used:
        lines.append("")
        lines.append("⚠️  Generic fallback was used - consider adding specific rules for this service")
    
    return "\n".join(lines)


def validate_context(context: ScoringContext) -> List[str]:
    """
    Validate scoring context and return any warnings.
    
    Args:
        context: ScoringContext to validate
        
    Returns:
        List of validation warnings
    """
    warnings = []
    
    # Check for common issues
    if not context.service.strip():
        warnings.append("Empty service description - results may be generic")
    
    if context.tech and len(context.tech) < 2:
        warnings.append("Very short tech name - might not match rules properly")
    
    # Check for common port/service mismatches
    web_ports = [80, 443, 8080, 8443]
    if context.port in web_ports and context.tech:
        if context.tech in ["mysql", "postgresql", "mongodb"]:
            warnings.append(f"Database tech '{context.tech}' on web port {context.port} - unusual configuration")
    
    # Check for unusual port ranges
    if context.port > 50000:
        warnings.append(f"High port number {context.port} - results may be generic")
    
    return warnings


def _apply_entropy_diversification(wordlists: List[str], 
                                  context: ScoringContext) -> Tuple[List[str], bool, Optional[float]]:
    """
    Apply entropy-based diversification to wordlist recommendations.
    
    Args:
        wordlists: Initial wordlist recommendations
        context: Scoring context
        
    Returns:
        Tuple of (diversified_wordlists, diversification_applied, entropy_score)
    """
    try:
        # Import here to avoid circular imports
        from .entropy import analyzer, should_diversify
        
        # Analyze current entropy
        entropy_metrics = analyzer.analyze_recent_selections(days_back=7, context=context)
        entropy_score = entropy_metrics.entropy_score
        
        # Check if diversification is needed
        if should_diversify(wordlists, context, entropy_threshold=0.7):
            logger.debug(f"Applying entropy diversification (entropy: {entropy_score:.3f})")
            
            # Get diversification alternatives
            diversified = analyzer.get_diversification_candidates(
                wordlists, 
                context, 
                get_wordlist_alternatives_dict()
            )
            
            if diversified != wordlists:
                logger.info(f"Diversified wordlists: {len(set(wordlists) - set(diversified))} replaced")
                return diversified, True, entropy_score
        
        return wordlists, False, entropy_score
        
    except Exception as e:
        logger.warning(f"Entropy diversification failed: {e}")
        return wordlists, False, None


def get_wordlist_alternatives_dict() -> Dict[str, List[str]]:
    """
    Get wordlist alternatives mapping for diversification.
    
    Returns:
        Dict mapping wordlist names to their alternatives
    """
    from .mappings import WORDLIST_ALTERNATIVES
    return WORDLIST_ALTERNATIVES


def score_wordlists_with_catalog(context: ScoringContext) -> ScoringResult:
    """
    Enhanced scoring function that uses SecLists catalog when available.
    Falls back to original rule-based scoring if catalog unavailable.
    
    Args:
        context: ScoringContext with target information
        
    Returns:
        ScoringResult with enhanced wordlist recommendations
    """
    if WORDLIST_RESOLVER_AVAILABLE and wordlist_resolver.is_available():
        return _score_with_catalog(context)
    else:
        logger.info("SecLists catalog not available, using rule-based scoring")
        return score_wordlists(context)


def _score_with_catalog(context: ScoringContext) -> ScoringResult:
    """
    Score wordlists using SecLists catalog for enhanced accuracy.
    
    Args:
        context: ScoringContext with target information
        
    Returns:
        ScoringResult with catalog-enhanced recommendations
    """
    # Enrich context with port database information  
    enriched_context = enrich_context_with_port_data(context)
    
    logger.debug(f"Scoring with catalog for {enriched_context.target}:{enriched_context.port}")
    
    # First get rule-based recommendations (using enriched context)
    rule_result = score_wordlists(context)  # This will internally enrich again, but that's okay
    
    # Enhance with catalog wordlists
    catalog_wordlists = wordlist_resolver.get_wordlists_for_context(
        tech=enriched_context.tech,
        port=enriched_context.port,
        max_results=15
    )
    
    # Resolve rule-based wordlists through catalog
    resolved_wordlists = wordlist_resolver.resolve_scorer_recommendations(
        scorer_wordlists=rule_result.wordlists,
        tech=enriched_context.tech,
        port=enriched_context.port,
        max_results=10
    )
    
    # Combine and deduplicate
    all_catalog_entries = {}
    
    # Add resolved rule-based wordlists (higher priority)
    for entry in resolved_wordlists:
        all_catalog_entries[entry.name] = entry
    
    # Add context-based wordlists
    for entry in catalog_wordlists:
        if entry.name not in all_catalog_entries:
            all_catalog_entries[entry.name] = entry
    
    # Score and rank all entries
    scored_entries = []
    for entry in all_catalog_entries.values():
        relevance_score = entry.get_relevance_score(enriched_context.tech, enriched_context.port)
        scored_entries.append((entry, relevance_score))
    
    # Sort by relevance
    scored_entries.sort(key=lambda x: x[1], reverse=True)
    
    # Extract final wordlist names and paths
    final_wordlists = []
    wordlist_paths = []
    
    for entry, score in scored_entries[:10]:  # Top 10
        final_wordlists.append(entry.name)
        wordlist_paths.append(entry.full_path)
    
    # Calculate enhanced scoring breakdown
    breakdown = rule_result.explanation
    
    # Boost confidence if we have catalog matches
    enhanced_score = rule_result.score
    if scored_entries:
        # Boost score based on catalog match quality
        avg_relevance = sum(score for _, score in scored_entries[:5]) / min(5, len(scored_entries))
        catalog_boost = min(0.2, avg_relevance * 0.2)
        enhanced_score = min(1.0, rule_result.score + catalog_boost)
    
    # Update matched rules to indicate catalog enhancement
    enhanced_rules = rule_result.matched_rules.copy()
    if scored_entries:
        enhanced_rules.append(f"catalog_enhanced:{len(scored_entries)}_matches")
    
    # Create enhanced result with catalog wordlists
    enhanced_result = ScoringResult(
        score=enhanced_score,
        explanation=breakdown,
        wordlists=final_wordlists,
        matched_rules=enhanced_rules,
        fallback_used=rule_result.fallback_used,
        cache_key=rule_result.cache_key,
        confidence=_determine_confidence(enhanced_score, rule_result.fallback_used, enhanced_rules)
    )
    
    return enhanced_result


def get_wordlist_paths(wordlist_names: List[str], 
                      tech: Optional[str] = None, 
                      port: Optional[int] = None) -> List[str]:
    """
    Get actual file paths for wordlist names.
    
    Args:
        wordlist_names: List of wordlist names
        tech: Technology context for better matching
        port: Port context for better matching
        
    Returns:
        List of file paths
    """
    if not WORDLIST_RESOLVER_AVAILABLE or not wordlist_resolver.is_available():
        logger.debug("Catalog not available - returning wordlist names as paths")
        return wordlist_names
    
    # Resolve through catalog
    entries = wordlist_resolver.resolve_scorer_recommendations(
        scorer_wordlists=wordlist_names,
        tech=tech,
        port=port,
        max_results=len(wordlist_names)
    )
    
    return [entry.full_path for entry in entries]


def get_port_context(port: int) -> dict:
    """
    Get port context information from the port database.
    
    Args:
        port: Port number to lookup
        
    Returns:
        Dict with port context information including technologies, service info, etc.
    """
    if not PORT_DATABASE_AVAILABLE or not port_database:
        return {
            "available": False,
            "technologies": [],
            "service_name": None,
            "category": None,
            "risk_level": None
        }
    
    port_entry = port_database.get_port(port)
    if not port_entry:
        return {
            "available": False,
            "technologies": [],
            "service_name": None,
            "category": None,
            "risk_level": None
        }
    
    return {
        "available": True,
        "technologies": port_entry.get_technology_stack(),
        "service_name": port_entry.default_service,
        "category": port_entry.classification.category.value,
        "risk_level": port_entry.classification.misuse_potential.value,
        "is_web_service": port_entry.is_web_service(),
        "description": port_entry.description,
        "alternative_services": port_entry.alternative_services
    }


def get_scoring_stats() -> dict:
    """
    Get statistics about the scoring system configuration.
    
    Returns:
        Dict with scoring system statistics
    """
    from .mappings import EXACT_MATCH_RULES, TECH_CATEGORY_RULES, PORT_CATEGORY_RULES, WORDLIST_ALTERNATIVES
    
    # Count exact rules
    exact_count = len(EXACT_MATCH_RULES)
    
    # Count tech categories
    tech_count = len(TECH_CATEGORY_RULES)
    
    # Count port categories
    port_count = len(PORT_CATEGORY_RULES)
    
    # Count total wordlists referenced
    all_wordlists = set()
    
    for wordlist_group in EXACT_MATCH_RULES.values():
        all_wordlists.update(wordlist_group)
    
    for config in TECH_CATEGORY_RULES.values():
        all_wordlists.update(config["wordlists"])
    
    for config in PORT_CATEGORY_RULES.values():
        all_wordlists.update(config["wordlists"])
    
    stats = {
        "exact_rules": exact_count,
        "tech_categories": tech_count,
        "port_categories": port_count,
        "total_wordlists": len(all_wordlists),
        "generic_fallbacks": len(GENERIC_FALLBACK),
        "wordlist_alternatives": len(WORDLIST_ALTERNATIVES),
        "catalog_available": WORDLIST_RESOLVER_AVAILABLE and wordlist_resolver.is_available() if wordlist_resolver else False,
        "port_database_available": PORT_DATABASE_AVAILABLE
    }
    
    # Add catalog stats if available
    if WORDLIST_RESOLVER_AVAILABLE and wordlist_resolver and wordlist_resolver.is_available():
        catalog_stats = wordlist_resolver.get_catalog_stats()
        stats["catalog_stats"] = catalog_stats
    
    # Add entropy analysis stats
    try:
        from .entropy import analyzer
        entropy_metrics = analyzer.analyze_recent_selections(days_back=30)
        stats["entropy_stats"] = {
            "recent_entropy_score": entropy_metrics.entropy_score,
            "recommendation_quality": entropy_metrics.recommendation_quality,
            "clustering_percentage": entropy_metrics.clustering_percentage
        }
    except Exception as e:
        logger.debug(f"Could not get entropy stats: {e}")
        stats["entropy_stats"] = {"available": False}
    
    return stats