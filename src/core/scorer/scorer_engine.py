"""IPCrawler scoring engine for wordlist recommendations"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScoringContext:
    """Context for scoring wordlists"""
    target: str
    port: int
    service: str
    tech: Optional[str] = None
    os: Optional[str] = None
    version: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    spider_data: Optional[Dict[str, Any]] = None


@dataclass
class ScoreBreakdown:
    """Breakdown of scoring factors"""
    service_match: float = 0.0
    tech_match: float = 0.0
    port_match: float = 0.0
    popularity: float = 0.0
    total: float = 0.0


@dataclass
class WordlistScore:
    """Score for a specific wordlist"""
    wordlist: str
    score: float
    confidence: str
    breakdown: ScoreBreakdown
    reason: str


@dataclass
class ScoringResult:
    """Result of wordlist scoring"""
    context: ScoringContext
    scores: List[WordlistScore]
    total_wordlists: int
    execution_time: float


from enum import Enum
class Confidence(Enum):
    """Confidence levels for scoring results"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ScoreExplanation:
    """Detailed breakdown of scoring components"""
    exact_match: float = 0.0
    tech_category: float = 0.0
    port_context: float = 0.0
    service_keywords: float = 0.0
    generic_fallback: float = 0.0


@dataclass
class SmartListResult:
    """Result structure expected by SmartList workflow"""
    wordlists: List[str]
    score: float
    confidence: Confidence
    matched_rules: List[str]
    fallback_used: bool
    explanation: ScoreExplanation


# Old ScoringResult-based function removed - now using SmartListResult format


def score_wordlists(context: ScoringContext) -> SmartListResult:
    """Score wordlists based on context - database-driven version (no hardcoded mappings)"""
    
    # Use database-driven scoring
    try:
        from src.core.scorer.database_scorer import score_wordlists_database
        
        # Get wordlists from database
        recommended_wordlists = score_wordlists_database(
            tech=context.tech,
            port=context.port,
            service=context.service
        )
        
        # If we got recommendations, create result
        if recommended_wordlists:
            return SmartListResult(
                wordlists=recommended_wordlists,
                score=1.0,
                confidence="high",
                matched_rules=[f"database:{context.tech}:{context.port}"],
                explanation={
                    "exact_match": 1.0 if context.tech else 0.0,
                    "port_context": 0.8 if context.port else 0.0,
                    "database_driven": 1.0,
                    "generic_fallback": 0.0
                },
                fallback_used=False
            )
    
    except Exception as e:
        logger.warning(f"Database scoring failed: {e}")
    
    # Fallback to catalog if database fails
    catalog_wordlists = []
    try:
        # Check if database is available
        db_stats = get_database_availability()
        
        if db_stats.get('catalog_available', False):
            # Load catalog and select appropriate wordlists
            catalog_path = Path(db_stats['catalog_path'])
            with open(catalog_path, 'r') as f:
                catalog_data = json.load(f)
            
            wordlists_array = catalog_data.get('wordlists', [])
            # Convert array to dict with name as key for compatibility
            wordlists = {wl.get('name', f'wordlist_{i}'): wl for i, wl in enumerate(wordlists_array)}
            
            # Smart wordlist selection based on context
            selected_wordlists = []
            score_boost = 0.0
            matched_rules = []
            
            # Tech-specific wordlists with version awareness
            if context.tech:
                tech_lower = context.tech.lower()
                version_info = getattr(context, 'version', None)
                
                version_matches = []
                tech_matches = []
                
                for name, info in wordlists.items():
                    name_lower = name.lower()
                    display_name_lower = info.get('display_name', '').lower()
                    
                    # Check for version-specific matches first
                    if version_info:
                        version_patterns = [
                            f"{tech_lower}_{version_info}",
                            f"{tech_lower}-{version_info}",
                            f"{tech_lower}.{version_info}",
                            f"{tech_lower} {version_info}"
                        ]
                        
                        for pattern in version_patterns:
                            if pattern in name_lower or pattern in display_name_lower:
                                version_matches.append(name)
                                matched_rules.append(f"version_match:{context.tech}:{version_info}")
                                score_boost += 0.4  # Higher boost for version match
                                break
                    
                    # Check for general tech matches
                    if tech_lower in name_lower or tech_lower in display_name_lower:
                        tech_matches.append(name)
                
                # Add version matches first, then general tech matches
                selected_wordlists.extend(version_matches[:1])  # Top version match
                remaining_slots = max(0, 2 - len(version_matches))
                for tech_match in tech_matches[:remaining_slots]:
                    if tech_match not in selected_wordlists:
                        selected_wordlists.append(tech_match)
                        matched_rules.append(f"tech_match:{context.tech}")
                        score_boost += 0.3
            
            # Port-specific wordlists for web services
            if context.port in [80, 443, 8080, 8443, 3000, 5000, 9000]:
                for name, info in wordlists.items():
                    if any(tag in ['web', 'directories', 'files'] for tag in info.get('tags', [])):
                        if name not in selected_wordlists:
                            selected_wordlists.append(name)
                        score_boost += 0.2
                        matched_rules.append(f"port:{context.port}")
                        if len(selected_wordlists) >= 3:
                            break
            
            # Add high-quality general wordlists from catalog
            if len(selected_wordlists) < 5:
                for name, info in wordlists.items():
                    if info.get('quality_score', 0) >= 7 and name not in selected_wordlists:
                        selected_wordlists.append(name)
                        if len(selected_wordlists) >= 5:
                            break
            
            catalog_wordlists = selected_wordlists
    
    except Exception as e:
        logger.debug(f"Could not load catalog for basic scoring: {e}")
    
    # Calculate scoring based on available wordlists
    if catalog_wordlists:
        # We found catalog wordlists - calculate score
        base_score = 0.4  # Base score when using catalog
        tech_bonus = 0.2 if context.tech and any('tech_match:' in r for r in matched_rules) else 0.0
        port_bonus = 0.1 if context.port in [80, 443, 8080, 8443] else 0.0
        
        final_score = min(base_score + tech_bonus + port_bonus, 1.0)
        confidence = Confidence.MEDIUM if final_score >= 0.5 else Confidence.LOW
        
        return SmartListResult(
            wordlists=catalog_wordlists,
            score=final_score,
            confidence=confidence,
            matched_rules=matched_rules or ["catalog_basic"],
            fallback_used=False,
            explanation=ScoreExplanation(
                exact_match=0.0,
                tech_category=tech_bonus,
                port_context=port_bonus,
                service_keywords=0.0,
                generic_fallback=0.0
            )
        )
    else:
        # No catalog available - return minimal result indicating catalog needed
        return SmartListResult(
            wordlists=[],  # No hardcoded fallbacks - SmartList engine requires catalog
            score=0.1,  # Very low score to indicate incomplete data
            confidence=Confidence.LOW,
            matched_rules=["no_catalog_available"],
            fallback_used=True,
            explanation=ScoreExplanation(
                exact_match=0.0,
                tech_category=0.0,
                port_context=0.0,
                service_keywords=0.0,
                generic_fallback=0.1  # Minimal score indicating fallback state
            )
        )


def score_wordlists_with_catalog(context: ScoringContext) -> SmartListResult:
    """Score wordlists using catalog data - enhanced version with database integration"""
    try:
        # Check if database is available
        db_stats = get_database_availability()
        
        if db_stats.get('catalog_available', False):
            # Load catalog and select appropriate wordlists
            catalog_path = Path(db_stats['catalog_path'])
            with open(catalog_path, 'r') as f:
                catalog_data = json.load(f)
            
            wordlists_array = catalog_data.get('wordlists', [])
            # Convert array to dict with name as key for compatibility
            wordlists = {wl.get('name', f'wordlist_{i}'): wl for i, wl in enumerate(wordlists_array)}
            
            # Smart wordlist selection based on context
            selected_wordlists = []
            score_boost = 0.0
            matched_rules = []
            
            # Enhanced tech-specific wordlists with version awareness
            if context.tech:
                tech_lower = context.tech.lower()
                version_info = getattr(context, 'version', None)
                
                # First, look for version-specific wordlists
                version_matches = []
                tech_matches = []
                
                for name, info in wordlists.items():
                    name_lower = name.lower()
                    display_name_lower = info.get('display_name', '').lower()
                    
                    # Check for version-specific matches first (highest priority)
                    if version_info:
                        version_patterns = [
                            f"{tech_lower}_{version_info}",
                            f"{tech_lower}-{version_info}",
                            f"{tech_lower}.{version_info}",
                            f"{tech_lower} {version_info}"
                        ]
                        
                        for pattern in version_patterns:
                            if pattern in name_lower or pattern in display_name_lower:
                                version_matches.append({
                                    'name': name,
                                    'score_boost': 0.5,  # Highest boost for version match
                                    'rule': f"version_exact:{context.tech}:{version_info}:{context.port}"
                                })
                                break
                    
                    # Check for general tech matches
                    if tech_lower in name_lower or tech_lower in display_name_lower:
                        # Check tech compatibility if available
                        tech_compatibility = info.get('tech_compatibility', [])
                        compatibility_boost = 0.0
                        
                        if tech_compatibility:
                            for tech_compat in tech_compatibility:
                                if tech_lower in tech_compat.lower():
                                    compatibility_boost = 0.1
                                    break
                        
                        tech_matches.append({
                            'name': name,
                            'score_boost': 0.3 + compatibility_boost,
                            'rule': f"tech_match:{context.tech}:{context.port}"
                        })
                
                # Add version-specific matches first (highest priority)
                for match in version_matches[:2]:  # Limit to top 2 version matches
                    selected_wordlists.append(match['name'])
                    score_boost += match['score_boost']
                    matched_rules.append(match['rule'])
                
                # Add general tech matches if we don't have enough version-specific ones
                remaining_slots = max(0, 3 - len(version_matches))
                for match in tech_matches[:remaining_slots]:
                    if match['name'] not in selected_wordlists:
                        selected_wordlists.append(match['name'])
                        score_boost += match['score_boost']
                        matched_rules.append(match['rule'])
            
            # Port-specific wordlists for web services
            if context.port in [80, 443, 8080, 8443, 3000, 5000, 9000]:
                for name, info in wordlists.items():
                    if any(tag in ['web', 'directories', 'files'] for tag in info.get('tags', [])):
                        if name not in selected_wordlists:
                            selected_wordlists.append(name)
                        score_boost += 0.2
                        matched_rules.append(f"port:{context.port}")
                        if len(selected_wordlists) >= 3:
                            break
            
            # Add high-quality general-purpose wordlists from catalog (no hardcoding)
            if len(selected_wordlists) < 5:
                # Get wordlists with high quality scores or common tags
                for name, info in wordlists.items():
                    if name not in selected_wordlists:
                        # Prioritize by quality score or common usage tags
                        if (info.get('quality_score', 0) >= 8 or 
                            any(tag in ['common', 'general', 'basic'] for tag in info.get('tags', []))):
                            selected_wordlists.append(name)
                            if len(selected_wordlists) >= 5:
                                break
            
            # If we found catalog-specific wordlists, return enhanced result
            if selected_wordlists:
                final_score = min(0.6 + score_boost, 1.0)
                confidence = Confidence.HIGH if final_score > 0.8 else Confidence.MEDIUM
                
                return SmartListResult(
                    wordlists=selected_wordlists,
                    score=final_score,
                    confidence=confidence,
                    matched_rules=matched_rules or ["catalog_fallback"],
                    fallback_used=False,
                    explanation=ScoreExplanation(
                        exact_match=0.3 if context.tech and any('exact:' in r for r in matched_rules) else 0.0,
                        tech_category=0.2 if context.tech else 0.0,
                        port_context=0.2 if any('port:' in r for r in matched_rules) else 0.0,
                        service_keywords=0.1,
                        generic_fallback=0.0
                    )
                )
        
        # Fallback to basic scoring if catalog not available
        logger.debug("Catalog not available, using basic scoring")
        
    except Exception as e:
        logger.warning(f"Error in catalog scoring: {e}")
    
    # Fallback to basic scoring
    return score_wordlists(context)


def get_wordlist_paths(wordlist_names: List[str], tech: str = None, port: int = None) -> List[Optional[str]]:
    """Get full paths for wordlist names using catalog if available"""
    paths = []
    
    try:
        # Get database availability
        db_stats = get_database_availability()
        if not db_stats.get('catalog_available', False):
            logger.debug("Wordlist catalog not available - SmartList engine requires catalog")
            # No hardcoded fallbacks - SmartList engine requires catalog
            return [None] * len(wordlist_names)
        
        # Load wordlist catalog
        catalog_path = Path(db_stats['catalog_path'])
        with open(catalog_path, 'r') as f:
            catalog_data = json.load(f)
        
        wordlists_array = catalog_data.get('wordlists', [])
        # Convert array to dict with name as key for compatibility
        wordlists = {wl.get('name', f'wordlist_{i}'): wl for i, wl in enumerate(wordlists_array)}
        
        for name in wordlist_names:
            path = None
            
            # Try exact match first
            if name in wordlists:
                path = wordlists[name].get('full_path')
            else:
                # Try fuzzy matching (remove extensions, case insensitive)
                name_base = name.lower().replace('.txt', '').replace('.list', '')
                for catalog_name, info in wordlists.items():
                    catalog_base = catalog_name.lower().replace('.txt', '').replace('.list', '')
                    if name_base in catalog_base or catalog_base in name_base:
                        path = info.get('full_path')
                        logger.debug(f"Fuzzy matched '{name}' to '{catalog_name}'")
                        break
            
            if path and Path(path).exists():
                paths.append(path)
                logger.debug(f"Resolved '{name}' to: {path}")
            else:
                # Fallback to default path
                fallback_path = f"/usr/share/seclists/Discovery/Web-Content/{name}"
                if Path(fallback_path).exists():
                    paths.append(fallback_path)
                    logger.debug(f"Using fallback path for '{name}': {fallback_path}")
                else:
                    paths.append(None)
                    logger.warning(f"Could not resolve path for wordlist: {name}")
        
    except Exception as e:
        logger.warning(f"Error resolving wordlist paths: {e}")
        # Return fallback paths
        return [f"/usr/share/seclists/Discovery/Web-Content/{name}" for name in wordlist_names]
    
    return paths


def get_port_context(port: int, service: str = None) -> Dict[str, Any]:
    """Get context information for a port from database"""
    # Default response
    context = {
        "port": port,
        "service": service or "unknown",
        "common_services": [],
        "technology_stack": [],
        "category": "unknown",
        "risk_level": "unknown",
        "is_web_service": False,
        "technologies": []
    }
    
    try:
        # Get database availability
        db_stats = get_database_availability()
        if not db_stats.get('port_database_available', False):
            logger.debug(f"Port database not available, returning default context for port {port}")
            return context
        
        # Load port database
        port_db_path = Path(db_stats['port_db_path'])
        with open(port_db_path, 'r') as f:
            port_data = json.load(f)
        
        # Look up port information
        port_str = str(port)
        if port_str in port_data:
            port_info = port_data[port_str]
            
            # Update context with database information
            context.update({
                "service": port_info.get('default_service', service or "unknown"),
                "common_services": port_info.get('alternative_services', []),
                "technology_stack": port_info.get('tech_stack', {}),
                "category": port_info.get('classification', {}).get('category', 'unknown'),
                "risk_level": port_info.get('classification', {}).get('risk_level', 'unknown'),
                "is_web_service": port_info.get('classification', {}).get('category') in ['web-service', 'web'],
                "technologies": port_info.get('indicators', {}).get('tech_indicators', []),
                "description": port_info.get('description', ''),
                "banners": port_info.get('indicators', {}).get('banners', [])
            })
            
            logger.debug(f"Loaded port context for {port}: {context['service']} ({context['category']})")
        else:
            logger.debug(f"Port {port} not found in database, using defaults")
            
    except Exception as e:
        logger.warning(f"Error loading port context for {port}: {e}")
    
    return context


def explain_scoring(result: ScoringResult) -> str:
    """Explain how scoring was calculated"""
    explanation = f"Scored {result.total_wordlists} wordlists for {result.context.service} on port {result.context.port}\n"
    explanation += f"Top results:\n"
    
    for score in result.scores[:3]:
        explanation += f"- {score.wordlist}: {score.score:.2f} ({score.confidence}) - {score.reason}\n"
    
    return explanation


def get_database_availability() -> Dict[str, Any]:
    """Check availability of database files"""
    try:
        # Find project root - go up from scorer directory
        current_path = Path(__file__).parent
        project_root = None
        
        # Look for database directory in parent directories
        for parent in [current_path] + list(current_path.parents):
            database_path = parent / "database"
            if database_path.exists():
                project_root = parent
                break
        
        if not project_root:
            logger.warning("Could not find database directory")
            return {
                "port_database_available": False,
                "catalog_available": False,
                "error": "Database directory not found"
            }
        
        database_path = project_root / "database"
        port_db_path = database_path / "ports" / "port_db.json"
        catalog_path = database_path / "wordlists" / "seclists_catalog.json"
        
        # Check port database
        port_db_available = False
        port_db_error = None
        try:
            if port_db_path.exists():
                with open(port_db_path, 'r') as f:
                    port_data = json.load(f)
                    # Verify it has expected structure
                    if isinstance(port_data, dict) and len(port_data) > 0:
                        port_db_available = True
                        logger.debug(f"Port database loaded: {len(port_data)} ports")
                    else:
                        port_db_error = "Port database is empty or invalid format"
            else:
                port_db_error = f"Port database not found at {port_db_path}"
        except Exception as e:
            port_db_error = f"Error loading port database: {e}"
            logger.warning(port_db_error)
        
        # Check wordlist catalog
        catalog_available = False
        catalog_error = None
        try:
            if catalog_path.exists():
                with open(catalog_path, 'r') as f:
                    catalog_data = json.load(f)
                    # Verify it has expected structure
                    if isinstance(catalog_data, dict) and 'wordlists' in catalog_data:
                        wordlists = catalog_data['wordlists']
                        # Handle both array and dict formats
                        if isinstance(wordlists, list) and len(wordlists) > 0:
                            catalog_available = True
                            logger.debug(f"Wordlist catalog loaded: {len(wordlists)} wordlists")
                        elif isinstance(wordlists, dict) and len(wordlists) > 0:
                            catalog_available = True
                            logger.debug(f"Wordlist catalog loaded: {len(wordlists)} wordlists")
                        else:
                            catalog_error = "Wordlist catalog has no wordlists"
                    else:
                        catalog_error = "Wordlist catalog is invalid format"
            else:
                catalog_error = f"Wordlist catalog not found at {catalog_path}"
        except Exception as e:
            catalog_error = f"Error loading wordlist catalog: {e}"
            logger.warning(catalog_error)
        
        result = {
            "port_database_available": port_db_available,
            "catalog_available": catalog_available,
            "database_path": str(database_path),
            "port_db_path": str(port_db_path),
            "port_database_path": str(port_db_path),  # For compatibility with SmartList scanner
            "catalog_path": str(catalog_path)
        }
        
        # Add error details if any
        if port_db_error:
            result["port_db_error"] = port_db_error
        if catalog_error:
            result["catalog_error"] = catalog_error
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking database availability: {e}")
        return {
            "port_database_available": False,
            "catalog_available": False,
            "error": str(e)
        }


def get_scoring_stats(result: ScoringResult = None) -> Dict[str, Any]:
    """Get statistics about scoring results and database availability
    
    Args:
        result: Optional ScoringResult to analyze. If None, returns only database stats.
    """
    # Always include database availability
    stats = get_database_availability()
    
    # Add scoring statistics if result provided
    if result:
        stats.update({
            "total_wordlists": result.total_wordlists,
            "high_confidence": len([s for s in result.scores if s.confidence == "HIGH"]),
            "medium_confidence": len([s for s in result.scores if s.confidence == "MEDIUM"]),
            "low_confidence": len([s for s in result.scores if s.confidence == "LOW"]),
            "average_score": sum(s.score for s in result.scores) / len(result.scores) if result.scores else 0,
            "execution_time": result.execution_time
        })
    
    return stats