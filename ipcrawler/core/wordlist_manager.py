"""
WordList Manager for IPCrawler
Parses SecLists and other CTF wordlists into structured JSON for easy discovery
"""

import json
import os
import toml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re
import logging


class WordlistManager:
    """Manages wordlist discovery, parsing, and metadata generation"""
    
    def __init__(self, config_path: str = "config.toml"):
        """Initialize WordlistManager with configuration"""
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        configured_path = self.config.get("wordlists", {}).get("seclists_path", "auto")
        self.seclists_path = self._auto_detect_seclists_path(configured_path)
        self.wordlists_dir = Path("wordlists")
        self.wordlists_dir.mkdir(exist_ok=True)
        self._catalog_cache = None
        self._cache_timestamp = None
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from TOML file"""
        try:
            with open(config_path, 'r') as f:
                return toml.load(f)
        except FileNotFoundError:
            return {}
    
    def _auto_detect_seclists_path(self, configured_path: str) -> str:
        """Auto-detect SecLists installation path."""
        if configured_path != "auto" and configured_path:
            # Use configured path if not set to auto
            if Path(configured_path).exists():
                return configured_path
            else:
                self.logger.warning(f"Configured SecLists path does not exist: {configured_path}")
        
        # Common SecLists installation locations
        common_paths = [
            # User home directory locations
            Path.home() / ".local" / "share" / "seclists",
            Path.home() / "seclists",
            Path.home() / ".seclists",
            Path.home() / "tools" / "seclists",
            Path.home() / "tools" / "SecLists",
            
            # System-wide locations
            Path("/usr/share/seclists"),
            Path("/usr/share/SecLists"),
            Path("/opt/seclists"),
            Path("/opt/SecLists"),
            
            # Common tool directories
            Path("/tools/seclists"),
            Path("/tools/SecLists"),
            
            # Relative to current directory
            Path("seclists"),
            Path("SecLists"),
            Path("../seclists"),
            Path("../SecLists"),
        ]
        
        for path in common_paths:
            if path.exists() and path.is_dir():
                # Verify it's actually SecLists by checking for characteristic directories
                if self._is_seclists_directory(path):
                    self.logger.info(f"Auto-detected SecLists at: {path}")
                    return str(path)
        
        self.logger.warning("SecLists not found in common locations. Auto-wordlist will use fallback.")
        return ""
    
    def _is_seclists_directory(self, path: Path) -> bool:
        """Verify that a directory is actually SecLists."""
        # Check for characteristic SecLists directories
        required_dirs = ["Discovery", "Passwords", "Usernames"]
        return all((path / dir_name).exists() for dir_name in required_dirs)
    
    def _get_file_stats(self, filepath: Path) -> Dict[str, Any]:
        """Get file statistics (size, line count, etc.)"""
        try:
            stat = filepath.stat()
            size = stat.st_size
            
            # Count lines in file
            with open(filepath, 'rb') as f:
                lines = sum(1 for _ in f)
            
            return {
                "size": size,
                "lines": lines,
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "readable": size > 0 and lines > 0
            }
        except Exception:
            return {"size": 0, "lines": 0, "last_modified": "", "readable": False}
    
    def _categorize_wordlist(self, filepath: Path, relative_path: str) -> Dict[str, Any]:
        """Categorize wordlist based on path and filename"""
        path_parts = relative_path.lower().split('/')
        filename = filepath.name.lower()
        
        # Technology mapping
        technology = []
        purpose = ""
        ctf_optimized = False
        quality_score = 5  # Default middle score
        
        # Directory-based categorization
        if "web-content" in path_parts or "webcontent" in path_parts:
            technology.extend(["web", "directory", "http"])
            purpose = "Web directory and file enumeration"
            if "common" in filename:
                quality_score = 9
                ctf_optimized = True
        elif "dns" in path_parts:
            technology.extend(["dns", "subdomain"])
            purpose = "DNS and subdomain enumeration"
            if "subdomains" in filename:
                quality_score = 8
                ctf_optimized = True
        elif "passwords" in path_parts:
            technology.extend(["password", "auth"])
            purpose = "Password and credential attacks"
            if "common" in filename or "rockyou" in filename:
                quality_score = 9
        elif "usernames" in path_parts:
            technology.extend(["username", "auth"])
            purpose = "Username enumeration"
            if "names" in filename:
                quality_score = 7
        elif "fuzzing" in path_parts:
            technology.extend(["fuzzing", "injection"])
            purpose = "Fuzzing and injection testing"
            if "xss" in filename or "sql" in filename:
                quality_score = 8
        elif "api" in path_parts:
            technology.extend(["api", "web"])
            purpose = "API endpoint discovery"
            quality_score = 7
        
        # Add tech tags from filename
        if "admin" in filename:
            technology.append("admin")
            purpose += " - Admin panels"
        elif "backup" in filename:
            technology.append("backup")
            purpose += " - Backup files"
        elif "php" in filename:
            technology.append("php")
        elif "asp" in filename:
            technology.append("asp")
        elif "jsp" in filename:
            technology.append("jsp")
        
        # Check if CTF-optimized
        if any(term in filename for term in ["small", "short", "quick", "common", "top"]):
            ctf_optimized = True
            quality_score += 1
        
        return {
            "technology": list(set(technology)),
            "purpose": purpose.strip(),
            "ctf_optimized": ctf_optimized,
            "quality_score": min(quality_score, 10)
        }
    
    def _parse_seclists_directory(self, directory: Path, category: str) -> List[Dict[str, Any]]:
        """Parse a SecLists directory and return wordlist metadata"""
        wordlists = []
        
        if not directory.exists():
            return wordlists
        
        for filepath in directory.rglob("*.txt"):
            if filepath.is_file():
                relative_path = str(filepath.relative_to(Path(self.seclists_path)))
                stats = self._get_file_stats(filepath)
                
                if not stats["readable"]:
                    continue
                
                categorization = self._categorize_wordlist(filepath, relative_path)
                
                wordlist_info = {
                    "name": filepath.name,
                    "path": relative_path,
                    "absolute_path": str(filepath),
                    "category": category,
                    "size": stats["size"],
                    "lines": stats["lines"],
                    "purpose": categorization["purpose"],
                    "technology": categorization["technology"],
                    "ctf_optimized": categorization["ctf_optimized"],
                    "quality_score": categorization["quality_score"],
                    "last_modified": stats["last_modified"]
                }
                
                wordlists.append(wordlist_info)
        
        return sorted(wordlists, key=lambda x: x["quality_score"], reverse=True)
    
    def _get_seclists_categories(self) -> Dict[str, str]:
        """Get SecLists category mapping"""
        if not self.seclists_path or not Path(self.seclists_path).exists():
            return {}
        
        categories = {}
        seclists_root = Path(self.seclists_path)
        
        # Major categories
        category_mapping = {
            "Discovery": "discovery",
            "Passwords": "passwords", 
            "Usernames": "usernames",
            "Fuzzing": "fuzzing",
            "Miscellaneous": "miscellaneous",
            "Payloads": "payloads"
        }
        
        for dir_name, category_key in category_mapping.items():
            category_path = seclists_root / dir_name
            if category_path.exists():
                categories[category_key] = {
                    "directory": dir_name,
                    "path": str(category_path),
                    "description": self._get_category_description(category_key)
                }
        
        return categories
    
    def _get_category_description(self, category: str) -> str:
        """Get description for category"""
        descriptions = {
            "discovery": "Network and service discovery wordlists",
            "passwords": "Password lists and common credentials",
            "usernames": "Username lists and account enumeration",
            "fuzzing": "Fuzzing payloads and injection testing",
            "miscellaneous": "Various specialized wordlists",
            "payloads": "Attack payloads and exploit strings"
        }
        return descriptions.get(category, "")
    
    def generate_wordlist_catalog(self, output_format: str = "json") -> Dict[str, Any]:
        """Generate wordlist catalog"""
        catalog = {
            "metadata": {
                "generated": datetime.now().isoformat(),
                "version": "1.0.0",
                "sources": []
            },
            "wordlists": {}
        }
        
        # Process SecLists if available
        if self.seclists_path and Path(self.seclists_path).exists():
            seclists_info = self._process_seclists()
            catalog["wordlists"]["seclists"] = seclists_info
            catalog["metadata"]["sources"].append("seclists")
        
        # Process local wordlists
        local_info = self._process_local_wordlists()
        if local_info["files"]:
            catalog["wordlists"]["local"] = local_info
            catalog["metadata"]["sources"].append("local")
        
        return catalog
    
    def _process_seclists(self) -> Dict[str, Any]:
        """Process SecLists directory structure"""
        seclists_root = Path(self.seclists_path)
        
        # Get version info
        version_info = self._get_seclists_version()
        
        seclists_data = {
            "path": self.seclists_path,
            "version": version_info.get("version", "unknown"),
            "last_updated": version_info.get("last_updated", ""),
            "categories": {},
            "total_wordlists": 0
        }
        
        categories = self._get_seclists_categories()
        
        for category_key, category_info in categories.items():
            category_path = Path(category_info["path"])
            wordlists = self._parse_seclists_directory(category_path, category_key)
            
            seclists_data["categories"][category_key] = {
                "directory": category_info["directory"],
                "description": category_info["description"],
                "wordlist_count": len(wordlists),
                "files": wordlists
            }
            
            seclists_data["total_wordlists"] += len(wordlists)
        
        return seclists_data
    
    def _get_seclists_version(self) -> Dict[str, str]:
        """Get SecLists version information"""
        try:
            git_dir = Path(self.seclists_path) / ".git"
            if git_dir.exists():
                # Try to get git info
                import subprocess
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%H|%ci"],
                    cwd=self.seclists_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    commit, date = result.stdout.strip().split('|')
                    return {
                        "version": commit[:8],
                        "last_updated": date
                    }
        except Exception:
            pass
        
        return {"version": "unknown", "last_updated": ""}
    
    def _process_local_wordlists(self) -> Dict[str, Any]:
        """Process local wordlists in wordlists/ directory"""
        local_data = {
            "path": str(self.wordlists_dir),
            "files": []
        }
        
        for filepath in self.wordlists_dir.glob("*.txt"):
            if filepath.is_file():
                stats = self._get_file_stats(filepath)
                if stats["readable"]:
                    local_data["files"].append({
                        "name": filepath.name,
                        "path": str(filepath),
                        "size": stats["size"],
                        "lines": stats["lines"],
                        "last_modified": stats["last_modified"]
                    })
        
        return local_data
    
    def save_catalog(self, catalog: Dict[str, Any], output_path: str = "wordlists/catalog.json"):
        """Save catalog to JSON file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(catalog, f, indent=2)
        
        return output_file
    
    def generate_markdown_report(self, catalog: Dict[str, Any], output_path: str = "wordlists/README.md"):
        """Generate human-readable markdown report"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        md_content = self._build_markdown_content(catalog)
        
        with open(output_file, 'w') as f:
            f.write(md_content)
        
        return output_file
    
    def _build_markdown_content(self, catalog: Dict[str, Any]) -> str:
        """Build markdown content from catalog"""
        lines = [
            "# IPCrawler Wordlist Catalog",
            "",
            f"Generated: {catalog['metadata']['generated']}",
            f"Sources: {', '.join(catalog['metadata']['sources'])}",
            "",
            "## Available Wordlists",
            ""
        ]
        
        for source_name, source_data in catalog["wordlists"].items():
            lines.extend([
                f"### {source_name.upper()}",
                f"- Path: `{source_data['path']}`",
                ""
            ])
            
            if source_name == "seclists":
                lines.append(f"- Total wordlists: {source_data['total_wordlists']}")
                lines.append("")
                
                for category, cat_data in source_data["categories"].items():
                    lines.extend([
                        f"#### {category.replace('_', ' ').title()} ({cat_data['wordlist_count']} files)",
                        f"{cat_data['description']}",
                        ""
                    ])
                    
                    # Show top 5 quality wordlists
                    top_wordlists = sorted(cat_data["files"], key=lambda x: x["quality_score"], reverse=True)[:5]
                    if top_wordlists:
                        lines.extend([
                            "| Name | Lines | Purpose | CTF Optimized | Quality |",
                            "|------|-------|---------|---------------|---------|"
                        ])
                        
                        for wl in top_wordlists:
                            ctf_mark = "✅" if wl["ctf_optimized"] else "❌"
                            lines.append(f"| {wl['name']} | {wl['lines']:,} | {wl['purpose'][:50]}... | {ctf_mark} | {wl['quality_score']}/10 |")
                        
                        lines.append("")
        
        return "\n".join(lines)
    
    def load_catalog(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load wordlist catalog with caching support."""
        catalog_path = self.wordlists_dir / "catalog.json"
        
        # Check if we need to refresh cache
        if force_refresh or self._catalog_cache is None:
            if catalog_path.exists():
                try:
                    with open(catalog_path, 'r') as f:
                        self._catalog_cache = json.load(f)
                        self._cache_timestamp = datetime.now()
                        self.logger.debug(f"Loaded wordlist catalog from {catalog_path}")
                except Exception as e:
                    self.logger.error(f"Error loading catalog: {e}")
                    return {}
            else:
                self.logger.warning(f"Catalog not found at {catalog_path}")
                return {}
        
        return self._catalog_cache or {}
    
    def get_wordlists_by_technology(self, technologies: List[str], 
                                  max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Get wordlists filtered by technology tags.
        
        Args:
            technologies: List of technology tags to match
            max_results: Maximum number of results to return
            
        Returns:
            List of wordlist metadata dictionaries
        """
        catalog = self.load_catalog()
        wordlists = []
        
        # Flatten all wordlists from all sources
        for source_name, source_data in catalog.get("wordlists", {}).items():
            if source_name == "seclists":
                # Process SecLists structure
                for category_name, category_data in source_data.get("categories", {}).items():
                    for wordlist in category_data.get("files", []):
                        wordlist["source"] = "seclists"
                        wordlist["category"] = category_name
                        wordlists.append(wordlist)
            elif "files" in source_data:
                # Process local wordlists
                for wordlist in source_data["files"]:
                    wordlist["source"] = source_name
                    wordlist["category"] = "local"
                    wordlists.append(wordlist)
        
        # Filter by technologies
        if technologies:
            tech_set = set(tech.lower() for tech in technologies if tech)
            filtered_wordlists = []
            
            for wordlist in wordlists:
                wordlist_techs = set(tech.lower() for tech in wordlist.get("technology", []) if tech)
                # Check for intersection
                if tech_set.intersection(wordlist_techs):
                    filtered_wordlists.append(wordlist)
            
            wordlists = filtered_wordlists
        
        # Sort by quality score (descending)
        wordlists.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        
        return wordlists[:max_results]
    
    def score_wordlist(self, wordlist: Dict[str, Any], context: Dict[str, Any],
                      scoring_config: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        """
        Score a wordlist based on context and configuration.
        
        Args:
            wordlist: Wordlist metadata dictionary
            context: Context from target analysis (technologies, hints, etc.)
            scoring_config: Scoring weights configuration
            
        Returns:
            Tuple of (total_score, score_breakdown)
        """
        scores = {
            'technology_score': 0.0,
            'context_score': 0.0,
            'quality_score': 0.0,
            'performance_score': 0.0
        }
        
        # Technology matching score (0-40 points)
        tech_weight = scoring_config.get('technology_weight', 0.4)
        scores['technology_score'] = self._score_technology_match(
            wordlist, context
        ) * tech_weight * 100
        
        # Context relevance score (0-30 points) 
        context_weight = scoring_config.get('context_weight', 0.3)
        scores['context_score'] = self._score_context_match(
            wordlist, context
        ) * context_weight * 100
        
        # Quality metrics score (0-30 points)
        quality_weight = scoring_config.get('quality_weight', 0.3)
        scores['quality_score'] = self._score_quality_metrics(
            wordlist, context
        ) * quality_weight * 100
        
        # Performance score (reserved for future use)
        performance_weight = scoring_config.get('performance_weight', 0.0)
        scores['performance_score'] = 0.0  # Not implemented yet
        
        total_score = sum(scores.values())
        return total_score, scores
    
    def _score_technology_match(self, wordlist: Dict[str, Any], 
                               context: Dict[str, Any]) -> float:
        """Score technology matching (0.0 to 1.0)."""
        wordlist_techs = set(tech.lower() for tech in wordlist.get("technology", []) if tech)
        context_techs = set(tech.lower() for tech in context.get("technologies", []) if tech)
        
        if not context_techs:
            return 0.1  # Default score for generic wordlists
        
        # Exact primary technology match gets highest score
        primary_tech = (context.get("primary_technology") or "").lower()
        if primary_tech and primary_tech in wordlist_techs:
            return 1.0
        
        # Specific technology matches (PHP, JSP, etc.) get high scores
        specific_techs = {"php", "jsp", "asp", "python", "nodejs", "ruby", "java"}
        specific_intersection = wordlist_techs.intersection(context_techs).intersection(specific_techs)
        if specific_intersection:
            # High score for specific technology matches
            return 0.9
        
        # CMS/Framework specific matches
        cms_techs = {"wordpress", "drupal", "joomla", "django", "laravel", "spring"}
        cms_intersection = wordlist_techs.intersection(context_techs).intersection(cms_techs)
        if cms_intersection:
            return 0.8
        
        # General technology intersection
        intersection = wordlist_techs.intersection(context_techs)
        if intersection:
            # Score based on percentage of overlap, but boost for more specific matches
            overlap_ratio = len(intersection) / len(context_techs)
            return min(1.0, overlap_ratio * 0.7)  # Cap at 0.7 for general matches
        
        # Web technology fallback (lowest score for generic web wordlists)
        if "web" in wordlist_techs and any(tech in ["web", "http", "directory"] 
                                          for tech in context_techs):
            return 0.3  # Reduced from 0.5 to prioritize specific wordlists
        
        return 0.0
    
    def _score_context_match(self, wordlist: Dict[str, Any], 
                            context: Dict[str, Any]) -> float:
        """Score context/hint matching (0.0 to 1.0)."""
        wordlist_purpose = (wordlist.get("purpose") or "").lower()
        wordlist_techs = set(tech.lower() for tech in wordlist.get("technology", []) if tech)
        context_hints = set(hint.lower() for hint in context.get("context_hints", []) if hint)
        
        # Check for explicit hint priority (vhost, admin, api, etc.)
        explicit_hint = context.get("explicit_hint", "").lower()
        if explicit_hint:
            # High priority for exact explicit hint matches
            if explicit_hint in wordlist_purpose or explicit_hint in wordlist_techs:
                return 1.0
            # Medium priority for related hint matches
            if explicit_hint == "vhost" and any(term in wordlist_purpose for term in ["subdomain", "dns", "vhost"]):
                return 0.95
            if explicit_hint == "directory" and any(term in wordlist_purpose for term in ["directory", "web", "content"]):
                return 0.95
        
        if not context_hints:
            return 0.3  # Default score when no hints
        
        # Direct purpose matching
        purpose_matches = 0
        for hint in context_hints:
            if hint in wordlist_purpose:
                purpose_matches += 1
        
        # Technology tag matching
        tech_matches = len(wordlist_techs.intersection(context_hints))
        
        # Calculate score based on matches
        total_matches = purpose_matches + tech_matches
        max_possible_matches = len(context_hints)
        
        if total_matches > 0:
            return min(1.0, total_matches / max_possible_matches)
        
        return 0.1
    
    def _score_quality_metrics(self, wordlist: Dict[str, Any], 
                              context: Dict[str, Any]) -> float:
        """Score quality metrics (0.0 to 1.0)."""
        score = 0.0
        
        # Base quality score (0.5 weight)
        quality = wordlist.get("quality_score", 5)
        score += (quality / 10.0) * 0.5
        
        # CTF bonus: +0.3
        if wordlist.get("ctf_optimized", False):
            score += 0.3
        
        # Size bonus: +0.2
        lines = wordlist.get("lines", 0)
        if 1000 <= lines <= 50000:  # Optimal size range
            score += 0.2
        elif lines <= 1000:  # Too small
            score += 0.1
        # Large wordlists get no bonus
        
        return min(1.0, score)
    
    def get_scored_wordlists(self, context: Dict[str, Any], 
                           scoring_config: Dict[str, float],
                           max_results: int = 10) -> List[Tuple[Dict[str, Any], float, Dict[str, float]]]:
        """
        Get wordlists scored and ranked for given context.
        
        Args:
            context: Context dictionary from target analysis
            scoring_config: Scoring configuration with weights
            max_results: Maximum number of results to return
            
        Returns:
            List of tuples (wordlist, total_score, score_breakdown)
        """
        # Get candidate wordlists (ensure sufficient candidates for proper scoring)
        technologies = context.get("technologies", [])
        min_candidates = max(50, max_results * 5)  # Ensure at least 50 candidates
        candidates = self.get_wordlists_by_technology(technologies, min_candidates)
        
        # Score all candidates
        scored_wordlists = []
        for wordlist in candidates:
            total_score, score_breakdown = self.score_wordlist(
                wordlist, context, scoring_config
            )
            scored_wordlists.append((wordlist, total_score, score_breakdown))
        
        # Sort by total score (descending), then by technology relevance, then by quality
        scored_wordlists.sort(key=lambda x: (
            x[1],  # Total score
            len(set(x[0].get("technology", [])).intersection(context.get("technologies", []))),  # Technology overlap
            x[0].get("quality_score", 0),  # Quality score
            -x[0].get("lines", float('inf'))  # Prefer smaller wordlists for speed (negative for ascending)
        ), reverse=True)
        
        return scored_wordlists[:max_results]
    
    def find_best_wordlist(self, context: Dict[str, Any], 
                          scoring_config: Dict[str, float],
                          fallback_path: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Find the best wordlist for given context.
        
        Args:
            context: Context dictionary from target analysis
            scoring_config: Scoring configuration with weights
            fallback_path: Fallback wordlist path if no good match
            
        Returns:
            Tuple of (wordlist_path, score, wordlist_metadata)
        """
        try:
            scored_wordlists = self.get_scored_wordlists(context, scoring_config, max_results=1)
            
            if scored_wordlists:
                wordlist, score, score_breakdown = scored_wordlists[0]
                wordlist_path = wordlist.get("absolute_path", fallback_path)
                
                self.logger.debug(f"Selected wordlist: {wordlist['name']} (score: {score:.1f})")
                self.logger.debug(f"Score breakdown: {score_breakdown}")
                
                return wordlist_path, score, wordlist
            else:
                self.logger.warning("No wordlists found, using fallback")
                return fallback_path, 0.0, {}
                
        except Exception as e:
            self.logger.error(f"Error finding best wordlist: {e}")
            return fallback_path, 0.0, {}


def main():
    """Main entry point for wordlist management"""
    manager = WordlistManager()
    
    # Generate catalog
    print("🔍 Scanning wordlists...")
    catalog = manager.generate_wordlist_catalog()
    
    # Save JSON catalog
    json_file = manager.save_catalog(catalog)
    print(f"✅ JSON catalog saved: {json_file}")
    
    # Generate markdown report
    md_file = manager.generate_markdown_report(catalog)
    print(f"✅ Markdown report saved: {md_file}")
    
    # Print summary
    total_wordlists = 0
    for source_data in catalog["wordlists"].values():
        if "total_wordlists" in source_data:
            total_wordlists += source_data["total_wordlists"]
        elif "files" in source_data:
            total_wordlists += len(source_data["files"])
    
    print(f"📊 Total wordlists cataloged: {total_wordlists}")
    print(f"📦 Sources: {', '.join(catalog['metadata']['sources'])}")


if __name__ == "__main__":
    main()