"""
WordList Manager for IPCrawler
Parses SecLists and other CTF wordlists into structured JSON for easy discovery
"""

import json
import os
import toml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import re


class WordlistManager:
    """Manages wordlist discovery, parsing, and metadata generation"""
    
    def __init__(self, config_path: str = "config.toml"):
        """Initialize WordlistManager with configuration"""
        self.config = self._load_config(config_path)
        self.seclists_path = self.config.get("wordlists", {}).get("seclists_path", "")
        self.wordlists_dir = Path("wordlists")
        self.wordlists_dir.mkdir(exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from TOML file"""
        try:
            with open(config_path, 'r') as f:
                return toml.load(f)
        except FileNotFoundError:
            return {}
    
    def _get_file_stats(self, filepath: Path) -> Dict[str, Any]:
        """Get file statistics (size, line count, etc.)"""
        try:
            stat = filepath.stat()
            size = stat.st_size
            
            # Count lines efficiently
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
        
        # Filename-based enhancement
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
        
        # CTF optimization detection
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
        """Generate comprehensive wordlist catalog"""
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
                        "path": str(filepath.relative_to(Path.cwd())),
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