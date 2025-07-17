"""
Core scoring engine for wordlist recommendation.
"""

from typing import List, Set, Optional
import logging
from .models import ScoringContext, ScoringResult, ScoreBreakdown, Confidence
from .rules import rule_engine
from .mappings import GENERIC_FALLBACK
from .cache import cache_selection

# Import wordlist resolver
try:
    from ..wordlists.resolver import resolver as wordlist_resolver
    WORDLIST_RESOLVER_AVAILABLE = True
except ImportError:
    WORDLIST_RESOLVER_AVAILABLE = False
    wordlist_resolver = None

logger = logging.getLogger(__name__)


def score_wordlists(context: ScoringContext) -> ScoringResult:
    """
    Main function to score wordlists based on context.
    
    Args:
        context: ScoringContext with target information
        
    Returns:
        ScoringResult with recommendations and explanations
    """
    logger.debug(f"Scoring wordlists for {context.target}:{context.port}")
    
    # Initialize scoring components
    breakdown = ScoreBreakdown()
    all_wordlists: Set[str] = set()
    matched_rules: List[str] = []
    
    # Level 1: Exact match rules (highest priority)
    exact_wordlists, exact_rules, exact_score = rule_engine.apply_exact_match(context)
    if exact_wordlists:
        breakdown.exact_match = exact_score
        all_wordlists.update(exact_wordlists)
        matched_rules.extend(exact_rules)
        logger.debug(f"Exact match: {exact_rules} -> {exact_wordlists}")
    
    # Level 2: Technology category rules
    tech_wordlists, tech_rules, tech_score = rule_engine.apply_tech_category(context)
    if tech_wordlists:
        breakdown.tech_category = tech_score
        all_wordlists.update(tech_wordlists)
        matched_rules.extend(tech_rules)
        logger.debug(f"Tech category: {tech_rules} -> {tech_wordlists}")
    
    # Level 3: Port category rules (always apply for fallback)
    port_wordlists, port_rules, port_score = rule_engine.apply_port_category(context)
    if port_wordlists:
        breakdown.port_context = port_score
        all_wordlists.update(port_wordlists)
        matched_rules.extend(port_rules)
        logger.debug(f"Port category: {port_rules} -> {port_wordlists}")
    
    # Level 4: Service keyword matching
    keyword_wordlists, keyword_rules, keyword_score = rule_engine.apply_service_keywords(context)
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
    final_wordlists = rule_engine.deduplicate_wordlists(list(all_wordlists))
    
    # Determine confidence level
    confidence = _determine_confidence(final_score, fallback_used, matched_rules)
    
    # Generate cache key
    cache_key = context.get_cache_key()
    
    # Create result
    result = ScoringResult(
        score=final_score,
        explanation=breakdown,
        wordlists=final_wordlists,
        matched_rules=matched_rules,
        fallback_used=fallback_used,
        cache_key=cache_key,
        confidence=confidence
    )
    
    logger.info(
        f"Scored {len(final_wordlists)} wordlists for {context.target}:{context.port} "
        f"(score: {final_score:.3f}, confidence: {confidence})"
    )
    
    # Cache the selection for tracking
    try:
        cache_selection(context, result)
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
    logger.debug(f"Scoring with catalog for {context.target}:{context.port}")
    
    # First get rule-based recommendations
    rule_result = score_wordlists(context)
    
    # Enhance with catalog wordlists
    catalog_wordlists = wordlist_resolver.get_wordlists_for_context(
        tech=context.tech,
        port=context.port,
        max_results=15
    )
    
    # Resolve rule-based wordlists through catalog
    resolved_wordlists = wordlist_resolver.resolve_scorer_recommendations(
        scorer_wordlists=rule_result.wordlists,
        tech=context.tech,
        port=context.port,
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
        relevance_score = entry.get_relevance_score(context.tech, context.port)
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
    
    # Create enhanced result
    enhanced_result = ScoringResult(
        score=enhanced_score,
        explanation=breakdown,
        wordlists=final_wordlists,
        matched_rules=enhanced_rules,
        fallback_used=rule_result.fallback_used,
        cache_key=context.get_cache_key(),
        confidence=_determine_confidence(enhanced_score, rule_result.fallback_used, enhanced_rules)
    )
    
    # Add catalog metadata to result (custom field)
    enhanced_result.catalog_metadata = {
        "wordlist_paths": wordlist_paths,
        "catalog_entries_count": len(all_catalog_entries),
        "avg_relevance_score": sum(score for _, score in scored_entries[:5]) / min(5, len(scored_entries)) if scored_entries else 0.0,
        "catalog_enhanced": True
    }
    
    logger.info(
        f"Enhanced scoring: {len(final_wordlists)} wordlists for {context.target}:{context.port} "
        f"(score: {enhanced_score:.3f}, catalog entries: {len(all_catalog_entries)})"
    )
    
    # Cache the enhanced selection
    try:
        cache_selection(context, enhanced_result)
    except Exception as e:
        logger.warning(f"Failed to cache enhanced selection: {e}")
    
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
        logger.warning("Catalog not available - returning wordlist names as paths")
        return wordlist_names
    
    # Resolve through catalog
    entries = wordlist_resolver.resolve_scorer_recommendations(
        scorer_wordlists=wordlist_names,
        tech=tech,
        port=port,
        max_results=len(wordlist_names)
    )
    
    return [entry.full_path for entry in entries]


def get_scoring_stats() -> dict:
    """
    Get statistics about the scoring system configuration.
    
    Returns:
        Dict with scoring system statistics
    """
    from .mappings import EXACT_MATCH_RULES, TECH_CATEGORY_RULES, PORT_CATEGORY_RULES
    
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
        "catalog_available": WORDLIST_RESOLVER_AVAILABLE and wordlist_resolver.is_available() if wordlist_resolver else False
    }
    
    # Add catalog stats if available
    if WORDLIST_RESOLVER_AVAILABLE and wordlist_resolver and wordlist_resolver.is_available():
        catalog_stats = wordlist_resolver.get_catalog_stats()
        stats["catalog_stats"] = catalog_stats
    
    return stats