"""
Auto-Wordlist Resolver for IPCrawler
Intelligent wordlist selection based on target analysis and scoring algorithms.
"""

import logging
import toml
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .target_analyzer import TargetAnalyzer
from .wordlist_manager import WordlistManager


class AutoWordlistResolver:
    """
    Resolves 'auto_wordlist' template fields to optimal wordlist paths
    based on target analysis and configurable scoring rules.
    """
    
    def __init__(self, config):
        """
        Initialize AutoWordlistResolver with configuration.
        
        Args:
            config: Configuration object (Pydantic AppConfig or dict)
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get wordlist config section
        if hasattr(config, 'wordlists'):
            wordlist_config = config.wordlists
            analysis_timeout = getattr(wordlist_config, 'analysis_timeout', 10)
        else:
            # Fallback for dictionary config
            wordlist_config = config.get("wordlists", {}) if hasattr(config, 'get') else {}
            analysis_timeout = wordlist_config.get("analysis_timeout", 10) if hasattr(wordlist_config, 'get') else 10
        
        # Initialize components
        self.target_analyzer = TargetAnalyzer(timeout=analysis_timeout)
        self.wordlist_manager = WordlistManager()
        
        # Load auto-wordlist configuration from templates.toml
        self.auto_config = self._load_auto_wordlist_config()
        self.enabled = self.auto_config.get("enable", True)
        self.cache_selections = self.auto_config.get("cache_selections", True)
        self.debug_logging = self.auto_config.get("debug_logging", False)
        
        # Scoring configuration
        self.scoring_config = self.auto_config.get("scoring", {
            "technology_weight": 0.4,
            "context_weight": 0.3,
            "quality_weight": 0.3,
            "performance_weight": 0.0
        })
        
        # User preferences
        self.preferences = self.auto_config.get("preferences", {})
        
        # Technology and context mappings
        self.tech_mapping = self.auto_config.get("technology_mapping", {})
        self.context_hints = self.auto_config.get("context_hints", {})
        self.tool_preferences = self.auto_config.get("tool_preferences", {})
        self.fallbacks = self.auto_config.get("fallbacks", {})
        
        # Selection cache
        self._selection_cache = {} if self.cache_selections else None
        
        if self.debug_logging:
            logging.getLogger(__name__).setLevel(logging.DEBUG)
    
    def _load_auto_wordlist_config(self) -> Dict[str, Any]:
        """Load auto-wordlist configuration from templates.toml."""
        try:
            templates_config_path = Path("configs/templates.toml")
            if templates_config_path.exists():
                with open(templates_config_path, 'r') as f:
                    templates_config = toml.load(f)
                return templates_config.get("auto_wordlist", {})
        except Exception as e:
            self.logger.warning(f"Could not load auto_wordlist config: {e}")
        
        # Return default configuration
        return {
            "enable": True,
            "cache_selections": True,
            "debug_logging": False,
            "scoring": {
                "technology_weight": 0.4,
                "context_weight": 0.3,
                "quality_weight": 0.3,
                "performance_weight": 0.0
            },
            "preferences": {
                "prefer_ctf_optimized": True,
                "prefer_smaller_lists": True,
                "max_wordlist_lines": 50000,
                "min_quality_score": 5
            },
            "fallbacks": {
                "default": "auto"
            }
        }
    
    def resolve_wordlist(self, target: str, tool: str = None, 
                        hint: str = None, template_context: Dict[str, Any] = None) -> str:
        """
        Resolve auto_wordlist to optimal wordlist path.
        
        Args:
            target: Target URL or IP to analyze
            tool: Tool that will use the wordlist (gobuster, feroxbuster, etc.)
            hint: Optional context hint (admin, api, directory, etc.)
            template_context: Additional template context
            
        Returns:
            Absolute path to selected wordlist
        """
        if not self.enabled:
            return self._get_fallback_wordlist()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(target, tool, hint)
            if self._selection_cache and cache_key in self._selection_cache:
                cached_result = self._selection_cache[cache_key]
                self.logger.debug(f"Using cached wordlist selection: {cached_result}")
                return cached_result
            
            # Analyze target
            target_analysis = self.target_analyzer.analyze_target(target)
            
            # Build context for wordlist selection
            context = self._build_selection_context(
                target_analysis, tool, hint, template_context
            )
            
            # Find best wordlist
            wordlist_path, score, wordlist_metadata = self.wordlist_manager.find_best_wordlist(
                context, self.scoring_config, self._get_fallback_wordlist()
            )
            
            # Apply user preferences and filters
            wordlist_path = self._apply_user_preferences(
                wordlist_path, wordlist_metadata, context
            )
            
            # Log selection decision
            if self.debug_logging:
                self._log_selection_decision(
                    target, tool, hint, context, wordlist_path, score, wordlist_metadata
                )
            
            # Save wordlist history
            self._save_wordlist_history(
                target, tool, hint, context, wordlist_path, score, wordlist_metadata
            )
            
            # Cache result
            if self._selection_cache:
                self._selection_cache[cache_key] = wordlist_path
            
            return wordlist_path
            
        except Exception as e:
            self.logger.error(f"Error resolving auto_wordlist for {target}: {e}")
            return self._get_fallback_wordlist()
    
    def _generate_cache_key(self, target: str, tool: str = None, hint: str = None) -> str:
        """Generate cache key for wordlist selection."""
        return f"{target}:{tool or 'none'}:{hint or 'none'}"
    
    def _build_selection_context(self, target_analysis: Dict[str, Any], 
                               tool: str = None, hint: str = None,
                               template_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Build comprehensive context for wordlist selection.
        
        Args:
            target_analysis: Result from target analyzer
            tool: Tool that will use the wordlist
            hint: Context hint from template
            template_context: Additional template context
            
        Returns:
            Context dictionary for scoring
        """
        # Start with target analysis context
        context = self.target_analyzer.get_wordlist_context(target_analysis)
        
        # Enhance with configured mappings
        enhanced_technologies = set(context.get("technologies", []))
        enhanced_hints = set(context.get("context_hints", []))
        
        # Apply technology mappings
        for tech in list(enhanced_technologies):
            if tech in self.tech_mapping:
                enhanced_technologies.update(self.tech_mapping[tech])
        
        # Apply context hint mappings with priority boost for explicit hints
        if hint and hint in self.context_hints:
            enhanced_hints.update(self.context_hints[hint])
            enhanced_technologies.update(self.context_hints[hint])
            # Mark explicit hint for priority scoring
            context["explicit_hint"] = hint
        
        # Apply tool preferences
        if tool and tool in self.tool_preferences:
            enhanced_hints.update(self.tool_preferences[tool])
        
        # Update context
        context["technologies"] = list(enhanced_technologies)
        context["context_hints"] = list(enhanced_hints)
        context["tool"] = tool
        context["hint"] = hint
        
        # Add template context if provided
        if template_context:
            context.update(template_context)
        
        return context
    
    def _apply_user_preferences(self, wordlist_path: str, 
                               wordlist_metadata: Dict[str, Any],
                               context: Dict[str, Any]) -> str:
        """
        Apply user preferences to wordlist selection.
        
        Args:
            wordlist_path: Initially selected wordlist path
            wordlist_metadata: Metadata of selected wordlist
            context: Selection context
            
        Returns:
            Final wordlist path after applying preferences
        """
        # Check size limits
        max_lines = self.preferences.get("max_wordlist_lines", 50000)
        if wordlist_metadata.get("lines", 0) > max_lines:
            self.logger.warning(
                f"Selected wordlist too large ({wordlist_metadata.get('lines')} lines), "
                f"using fallback"
            )
            return self._get_fallback_wordlist(context.get("hint"))
        
        # Check quality requirements
        min_quality = self.preferences.get("min_quality_score", 5)
        if wordlist_metadata.get("quality_score", 0) < min_quality:
            self.logger.warning(
                f"Selected wordlist quality too low ({wordlist_metadata.get('quality_score')}), "
                f"using fallback"
            )
            return self._get_fallback_wordlist(context.get("hint"))
        
        # Check if file exists
        if not Path(wordlist_path).exists():
            self.logger.warning(f"Selected wordlist not found: {wordlist_path}, using fallback")
            return self._get_fallback_wordlist(context.get("hint"))
        
        return wordlist_path
    
    def _get_fallback_wordlist(self, hint: str = None) -> str:
        """
        Get fallback wordlist based on context.
        
        Args:
            hint: Optional context hint for fallback selection
            
        Returns:
            Path to fallback wordlist
        """
        if hint and hint in self.fallbacks:
            fallback_path = self.fallbacks[hint]
        else:
            fallback_path = self.fallbacks.get("default", "auto")
        
        # Handle auto-detection
        if fallback_path == "auto":
            fallback_path = self._auto_detect_fallback_wordlist()
        
        # Verify fallback exists
        if Path(fallback_path).exists():
            return fallback_path
        
        # Last resort - try common locations
        common_paths = [
            "/usr/share/seclists/Discovery/Web-Content/common.txt",
            "/usr/share/wordlists/dirb/common.txt", 
            "/opt/SecLists/Discovery/Web-Content/common.txt",
            "wordlists/common.txt"
        ]
        
        # Add user-specific paths
        home = Path.home()
        common_paths.extend([
            str(home / ".local/share/seclists/Discovery/Web-Content/common.txt"),
            str(home / "seclists/Discovery/Web-Content/common.txt"),
            str(home / "tools/seclists/Discovery/Web-Content/common.txt"),
            str(home / "tools/SecLists/Discovery/Web-Content/common.txt"),
        ])
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        # If nothing found, return a basic fallback
        return fallback_path
    
    def _auto_detect_fallback_wordlist(self) -> str:
        """Auto-detect a good fallback wordlist."""
        # Try to get SecLists path from wordlist manager
        seclists_path = self.wordlist_manager.seclists_path
        
        if seclists_path:
            # Try common.txt first (best for general use)
            common_path = Path(seclists_path) / "Discovery/Web-Content/common.txt"
            if common_path.exists():
                return str(common_path)
            
            # Try directory-list-2.3-small.txt as second choice
            small_path = Path(seclists_path) / "Discovery/Web-Content/directory-list-2.3-small.txt"
            if small_path.exists():
                return str(small_path)
        
        # Fallback to a reasonable default
        return "/usr/share/seclists/Discovery/Web-Content/common.txt"
    
    def _log_selection_decision(self, target: str, tool: str, hint: str,
                               context: Dict[str, Any], selected_path: str,
                               score: float, metadata: Dict[str, Any]) -> None:
        """Log detailed selection decision for debugging."""
        self.logger.debug("=" * 60)
        self.logger.debug("AUTO-WORDLIST SELECTION DECISION")
        self.logger.debug("=" * 60)
        self.logger.debug(f"Target: {target}")
        self.logger.debug(f"Tool: {tool}")
        self.logger.debug(f"Hint: {hint}")
        self.logger.debug(f"Detected Technologies: {context.get('technologies', [])}")
        self.logger.debug(f"Context Hints: {context.get('context_hints', [])}")
        self.logger.debug(f"Primary Technology: {context.get('primary_technology')}")
        self.logger.debug(f"Confidence: {context.get('confidence')}")
        self.logger.debug("-" * 60)
        self.logger.debug(f"Selected Wordlist: {metadata.get('name', 'unknown')}")
        self.logger.debug(f"Path: {selected_path}")
        self.logger.debug(f"Total Score: {score:.1f}")
        self.logger.debug(f"Lines: {metadata.get('lines', 0):,}")
        self.logger.debug(f"Quality Score: {metadata.get('quality_score', 0)}/10")
        self.logger.debug(f"CTF Optimized: {metadata.get('ctf_optimized', False)}")
        self.logger.debug(f"Technologies: {metadata.get('technology', [])}")
        self.logger.debug("=" * 60)
    
    def _save_wordlist_history(self, target: str, tool: str, hint: str,
                              context: Dict[str, Any], selected_path: str,
                              score: float, metadata: Dict[str, Any]) -> None:
        """Save wordlist selection history for analysis."""
        try:
            import json
            import os
            from datetime import datetime
            from pathlib import Path
            
            # Create wordlist_history directory
            results_dir = Path("results") / target / "wordlist_history"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Create history entry
            history_entry = {
                "timestamp": datetime.now().isoformat(),
                "target": target,
                "tool": tool,
                "hint": hint,
                "context": {
                    "technologies": context.get("technologies", []),
                    "primary_technology": context.get("primary_technology"),
                    "context_hints": context.get("context_hints", []),
                    "confidence": context.get("confidence", 0.0)
                },
                "selection": {
                    "wordlist_path": selected_path,
                    "wordlist_name": metadata.get("name", "unknown"),
                    "total_score": round(score, 2),
                    "quality_score": metadata.get("quality_score", 0),
                    "lines": metadata.get("lines", 0),
                    "ctf_optimized": metadata.get("ctf_optimized", False),
                    "wordlist_technologies": metadata.get("technology", []),
                    "purpose": metadata.get("purpose", "")
                },
                "scoring_config": self.scoring_config.copy()
            }
            
            # Save to timestamped file
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # microseconds to milliseconds
            history_file = results_dir / f"selection_{timestamp_str}.json"
            
            with open(history_file, 'w') as f:
                json.dump(history_entry, f, indent=2)
                
            # Also append to daily summary file
            daily_summary_file = results_dir / f"daily_summary_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(daily_summary_file, 'a') as f:
                json.dump(history_entry, f)
                f.write('\n')
                
            self.logger.debug(f"Saved wordlist history to {history_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save wordlist history: {e}")
    
    def get_selection_info(self, target: str, tool: str = None, 
                          hint: str = None) -> Dict[str, Any]:
        """
        Get detailed information about wordlist selection without caching.
        
        Args:
            target: Target URL or IP
            tool: Tool name  
            hint: Context hint
            
        Returns:
            Dictionary with selection details and scoring breakdown
        """
        try:
            # Analyze target
            target_analysis = self.target_analyzer.analyze_target(target)
            
            # Build context
            context = self._build_selection_context(target_analysis, tool, hint)
            
            # Get scored wordlists (top 5)
            scored_wordlists = self.wordlist_manager.get_scored_wordlists(
                context, self.scoring_config, max_results=5
            )
            
            # Prepare results
            results = {
                "target_analysis": target_analysis,
                "selection_context": context,
                "scored_wordlists": []
            }
            
            for wordlist, score, score_breakdown in scored_wordlists:
                results["scored_wordlists"].append({
                    "wordlist": wordlist,
                    "total_score": score,
                    "score_breakdown": score_breakdown
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting selection info: {e}")
            return {"error": str(e)}
    
    def clear_cache(self) -> None:
        """Clear the selection cache."""
        if self._selection_cache:
            self._selection_cache.clear()
            self.logger.debug("Auto-wordlist selection cache cleared")
    
    def is_enabled(self) -> bool:
        """Check if auto-wordlist selection is enabled."""
        return self.enabled
    
    def get_config(self) -> Dict[str, Any]:
        """Get current auto-wordlist configuration."""
        return self.auto_config.copy()


def resolve_auto_wordlist(target: str, config: Dict[str, Any], 
                         tool: str = None, hint: str = None) -> str:
    """
    Simple function interface for auto-wordlist resolution.
    
    Args:
        target: Target URL or IP
        config: Application configuration
        tool: Tool name
        hint: Context hint
        
    Returns:
        Path to selected wordlist
    """
    resolver = AutoWordlistResolver(config)
    return resolver.resolve_wordlist(target, tool, hint)