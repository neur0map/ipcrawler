#!/usr/bin/env python3
"""
SecLists Catalog Generator

Parses SecLists directory structure and generates a comprehensive
wordlist catalog with metadata for intelligent selection.
"""

import sys
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
import hashlib

# Add project root and catalog directory to path for imports
project_root = Path(__file__).parent.parent.parent
catalog_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(catalog_dir))

from models import (
    WordlistEntry, WordlistCatalog, WordlistCategory, WordlistQuality
)


class SecListsParser:
    """Parser for SecLists directory structure."""
    
    def __init__(self, seclists_path: str):
        self.seclists_path = Path(seclists_path)
        self.catalog = WordlistCatalog(seclists_path=str(seclists_path))
        
        # Technology patterns for auto-detection
        self.tech_patterns = {
            'wordpress': r'(wordpress|wp-|wpmu)',
            'drupal': r'drupal',
            'joomla': r'joomla',
            'apache': r'(apache|httpd)',
            'nginx': r'nginx',
            'iis': r'iis',
            'tomcat': r'tomcat',
            'php': r'php',
            'asp': r'(asp|aspx)',
            'mysql': r'mysql',
            'postgresql': r'(postgres|psql)',
            'mongodb': r'mongo',
            'redis': r'redis',
            'jenkins': r'jenkins',
            'gitlab': r'gitlab',
            'git': r'git',
            'svn': r'svn',
            'ftp': r'ftp',
            'ssh': r'ssh',
            'telnet': r'telnet',
            'ldap': r'ldap',
            'smb': r'smb',
            'nfs': r'nfs',
            'snmp': r'snmp'
        }
        
        # Port associations
        self.port_patterns = {
            r'(web|http|www)': [80, 443, 8080, 8443],
            r'(admin|panel|control)': [8080, 9090, 10000],
            r'(database|db|sql)': [3306, 5432, 1433, 27017],
            r'(mail|smtp|imap|pop)': [25, 465, 587, 143, 993, 110, 995],
            r'(ftp|file)': [21, 22, 445, 139],
            r'(ssh|telnet)': [22, 23],
            r'(dns)': [53],
            r'(ldap)': [389, 636],
            r'(snmp)': [161, 162]
        }
    
    def parse_seclists(self) -> WordlistCatalog:
        """Parse entire SecLists directory and generate catalog."""
        print(f"Parsing SecLists from: {self.seclists_path}")
        
        if not self.seclists_path.exists():
            raise FileNotFoundError(f"SecLists path not found: {self.seclists_path}")
        
        # Find all .txt files
        txt_files = list(self.seclists_path.rglob("*.txt"))
        print(f"Found {len(txt_files)} wordlist files")
        
        processed = 0
        for txt_file in txt_files:
            try:
                wordlist = self._parse_wordlist_file(txt_file)
                if wordlist:
                    self.catalog.add_wordlist(wordlist)
                    processed += 1
                    
                    if processed % 100 == 0:
                        print(f"Processed {processed}/{len(txt_files)} files...")
                        
            except Exception as e:
                print(f"Warning: Failed to parse {txt_file}: {e}")
                continue
        
        print(f"Successfully processed {processed} wordlist files")
        
        # Generate catalog metadata
        self._generate_metadata()
        
        return self.catalog
    
    def _parse_wordlist_file(self, file_path: Path) -> Optional[WordlistEntry]:
        """Parse individual wordlist file and extract metadata."""
        try:
            # Basic file info
            stat = file_path.stat()
            relative_path = file_path.relative_to(self.seclists_path)
            
            # Skip very large files (>50MB) to avoid memory issues
            if stat.st_size > 50 * 1024 * 1024:
                print(f"Skipping large file: {file_path} ({stat.st_size // (1024*1024)}MB)")
                return None
            
            # Count lines efficiently
            line_count = self._count_lines(file_path)
            
            # Determine category from path
            category = self._determine_category(relative_path)
            
            # Extract metadata from path and filename
            display_name = self._generate_display_name(file_path.name, relative_path)
            tags = self._extract_tags(file_path.name, relative_path)
            tech_compatibility = self._extract_tech_compatibility(file_path.name, relative_path)
            port_compatibility = self._extract_port_compatibility(file_path.name, relative_path)
            
            # Sample some entries for preview
            sample_entries = self._get_sample_entries(file_path)
            
            # Determine quality based on size and content
            quality = self._determine_quality(line_count, sample_entries)
            
            # Calculate scorer weight
            scorer_weight = self._calculate_scorer_weight(category, line_count, tech_compatibility)
            
            # Generate description
            description = self._generate_description(file_path.name, relative_path, line_count)
            
            wordlist = WordlistEntry(
                name=file_path.name,
                display_name=display_name,
                full_path=str(file_path),
                relative_path=str(relative_path),
                category=category,
                subcategory=self._get_subcategory(relative_path),
                tags=tags,
                size_lines=line_count,
                size_bytes=stat.st_size,
                quality=quality,
                tech_compatibility=tech_compatibility,
                port_compatibility=port_compatibility,
                scorer_weight=scorer_weight,
                use_cases=self._determine_use_cases(relative_path, file_path.name),
                description=description,
                sample_entries=sample_entries,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                recommended_for_ports=self._get_recommended_ports(relative_path, file_path.name)
            )
            
            return wordlist
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _count_lines(self, file_path: Path) -> int:
        """Efficiently count lines in file."""
        try:
            with open(file_path, 'rb') as f:
                count = sum(1 for _ in f)
            return count
        except Exception:
            return 0
    
    def _determine_category(self, relative_path: Path) -> WordlistCategory:
        """Determine category based on file path."""
        path_str = str(relative_path).lower()
        
        # Category mapping based on SecLists structure
        category_mappings = {
            'discovery/web-content': WordlistCategory.WEB_CONTENT,
            'discovery/dns': WordlistCategory.SUBDOMAIN,
            'usernames': WordlistCategory.USERNAMES,
            'passwords': WordlistCategory.PASSWORDS,
            'fuzzing': WordlistCategory.FUZZING,
            'misconfiguration': WordlistCategory.MISCONFIGURATION,
            'discovery/infrastructure': WordlistCategory.NETWORK,
            'protocol': WordlistCategory.PROTOCOLS,
            'vulnerability': WordlistCategory.VULNERABILITY,
            'web-shells': WordlistCategory.VULNERABILITY,
            'cms': WordlistCategory.CMS,
            'database': WordlistCategory.DATABASE,
            'api': WordlistCategory.API,
            'admin': WordlistCategory.ADMIN_PANEL,
            'authentication': WordlistCategory.AUTHENTICATION,
            'backup': WordlistCategory.BACKUP,
            'config': WordlistCategory.CONFIG,
            'development': WordlistCategory.DEVELOPMENT,
            'mail': WordlistCategory.MAIL,
            'file': WordlistCategory.FILE_TRANSFER,
            'framework': WordlistCategory.FRAMEWORK
        }
        
        for path_keyword, category in category_mappings.items():
            if path_keyword in path_str:
                return category
        
        return WordlistCategory.OTHER
    
    def _generate_display_name(self, filename: str, relative_path: Path) -> str:
        """Generate human-readable display name."""
        # Remove extension
        name = filename.replace('.txt', '')
        
        # Convert underscores/hyphens to spaces and title case
        name = re.sub(r'[-_]', ' ', name)
        name = ' '.join(word.capitalize() for word in name.split())
        
        # Add context from path if helpful
        path_parts = relative_path.parts[:-1]  # Exclude filename
        if len(path_parts) >= 2:
            context = path_parts[-1].replace('-', ' ').title()
            if context not in name and len(name) < 30:
                name = f"{name} ({context})"
        
        return name
    
    def _extract_tags(self, filename: str, relative_path: Path) -> List[str]:
        """Extract relevant tags from filename and path."""
        tags = set()
        
        # Extract from filename
        filename_lower = filename.lower()
        for tech, pattern in self.tech_patterns.items():
            if re.search(pattern, filename_lower):
                tags.add(tech)
        
        # Extract from path
        path_str = str(relative_path).lower()
        
        # Common tag patterns
        tag_patterns = {
            'directories': r'(dir|directory|directories|folder)',
            'files': r'(file|files|filename)',
            'admin': r'(admin|administrator|management)',
            'api': r'(api|rest|graphql|endpoint)',
            'backup': r'(backup|bak|old|archive)',
            'config': r'(config|configuration|settings)',
            'common': r'(common|default|standard)',
            'small': r'(small|short|mini|quick)',
            'medium': r'(medium|med)',
            'large': r'(large|big|huge|comprehensive)',
            'custom': r'(custom|specific|specialized)',
            'security': r'(security|sec|vuln|exploit)',
            'test': r'(test|testing|debug)',
            'development': r'(dev|development|staging)'
        }
        
        for tag, pattern in tag_patterns.items():
            if re.search(pattern, path_str) or re.search(pattern, filename_lower):
                tags.add(tag)
        
        # Add size-based tags
        if 'small' in filename_lower or 'short' in filename_lower:
            tags.add('small')
        elif 'large' in filename_lower or 'big' in filename_lower:
            tags.add('large')
        elif 'medium' in filename_lower:
            tags.add('medium')
        
        return sorted(list(tags))
    
    def _extract_tech_compatibility(self, filename: str, relative_path: Path) -> List[str]:
        """Extract technology compatibility from filename and path."""
        techs = set()
        
        combined_text = f"{filename} {relative_path}".lower()
        
        for tech, pattern in self.tech_patterns.items():
            if re.search(pattern, combined_text):
                techs.add(tech)
        
        return sorted(list(techs))
    
    def _extract_port_compatibility(self, filename: str, relative_path: Path) -> List[int]:
        """Extract port associations from filename and path."""
        ports = set()
        
        combined_text = f"{filename} {relative_path}".lower()
        
        for pattern, port_list in self.port_patterns.items():
            if re.search(pattern, combined_text):
                ports.update(port_list)
        
        return sorted(list(ports))
    
    def _get_sample_entries(self, file_path: Path, max_samples: int = 5) -> List[str]:
        """Get sample entries from wordlist for preview."""
        samples = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= max_samples:
                        break
                    
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip comments
                        samples.append(line[:50])  # Limit length
            
        except Exception:
            pass
        
        return samples
    
    def _determine_quality(self, line_count: int, sample_entries: List[str]) -> WordlistQuality:
        """Determine wordlist quality based on size and content."""
        if line_count >= 50000:
            return WordlistQuality.EXCELLENT
        elif line_count >= 10000:
            return WordlistQuality.GOOD
        elif line_count >= 1000:
            return WordlistQuality.AVERAGE
        elif line_count > 0:
            return WordlistQuality.BASIC
        else:
            return WordlistQuality.UNKNOWN
    
    def _calculate_scorer_weight(self, category: WordlistCategory, 
                               line_count: int, tech_compatibility: List[str]) -> float:
        """Calculate base scorer weight."""
        # Base weight by category
        category_weights = {
            WordlistCategory.WEB_CONTENT: 0.8,
            WordlistCategory.CMS: 0.9,
            WordlistCategory.DATABASE: 0.8,
            WordlistCategory.API: 0.7,
            WordlistCategory.ADMIN_PANEL: 0.8,
            WordlistCategory.AUTHENTICATION: 0.7,
            WordlistCategory.BACKUP: 0.6,
            WordlistCategory.CONFIG: 0.6,
            WordlistCategory.DEVELOPMENT: 0.5,
            WordlistCategory.SUBDOMAIN: 0.7,
            WordlistCategory.FUZZING: 0.5,
            WordlistCategory.USERNAMES: 0.6,
            WordlistCategory.PASSWORDS: 0.6,
            WordlistCategory.OTHER: 0.4
        }
        
        base_weight = category_weights.get(category, 0.5)
        
        # Adjust for size (quality)
        if line_count >= 10000:
            size_multiplier = 1.2
        elif line_count >= 1000:
            size_multiplier = 1.1
        elif line_count >= 100:
            size_multiplier = 1.0
        else:
            size_multiplier = 0.8
        
        # Adjust for specificity (fewer techs = more specific = higher weight)
        if len(tech_compatibility) == 1:
            specificity_multiplier = 1.2
        elif len(tech_compatibility) <= 3:
            specificity_multiplier = 1.1
        else:
            specificity_multiplier = 1.0
        
        final_weight = base_weight * size_multiplier * specificity_multiplier
        return min(1.0, max(0.1, final_weight))
    
    def _get_subcategory(self, relative_path: Path) -> str:
        """Get subcategory from path structure."""
        parts = relative_path.parts
        if len(parts) >= 2:
            return parts[-2].replace('-', ' ').title()
        return ""
    
    def _determine_use_cases(self, relative_path: Path, filename: str) -> List[str]:
        """Determine use cases for the wordlist."""
        use_cases = []
        
        combined = f"{relative_path} {filename}".lower()
        
        use_case_patterns = {
            'directory_discovery': r'(dir|directory|directories|folder)',
            'file_discovery': r'(file|files|filename)',
            'subdomain_enumeration': r'(subdomain|dns|domain)',
            'api_testing': r'(api|endpoint|rest|graphql)',
            'admin_panel_discovery': r'(admin|panel|control|management)',
            'backup_file_discovery': r'(backup|bak|old|archive)',
            'configuration_discovery': r'(config|configuration|settings)',
            'vulnerability_testing': r'(vuln|exploit|security)',
            'authentication_testing': r'(auth|login|password|username)',
            'cms_testing': r'(cms|wordpress|drupal|joomla)',
            'database_testing': r'(database|db|sql|mysql|postgres)',
            'fuzzing': r'(fuzz|fuzzing|random)',
            'brute_force': r'(brute|force|crack)',
            'enumeration': r'(enum|enumeration|list)'
        }
        
        for use_case, pattern in use_case_patterns.items():
            if re.search(pattern, combined):
                use_cases.append(use_case)
        
        return use_cases
    
    def _generate_description(self, filename: str, relative_path: Path, line_count: int) -> str:
        """Generate description for the wordlist."""
        # Extract meaningful parts
        name_clean = filename.replace('.txt', '').replace('-', ' ').replace('_', ' ')
        
        # Get category context
        path_parts = [part.replace('-', ' ') for part in relative_path.parts[:-1]]
        context = ' / '.join(path_parts).title()
        
        # Build description
        description = f"Wordlist for {name_clean}"
        
        if context:
            description += f" in {context}"
        
        if line_count > 0:
            description += f". Contains {line_count:,} entries"
        
        # Add quality indicator
        if line_count >= 50000:
            description += " (comprehensive list)"
        elif line_count >= 10000:
            description += " (extensive list)"
        elif line_count >= 1000:
            description += " (standard list)"
        elif line_count > 0:
            description += " (specialized list)"
        
        return description + "."
    
    def _get_recommended_ports(self, relative_path: Path, filename: str) -> List[int]:
        """Get specifically recommended ports for this wordlist."""
        # This is more specific than general port compatibility
        combined = f"{relative_path} {filename}".lower()
        
        specific_recommendations = {
            r'(wordpress|wp-)': [80, 443],
            r'(admin|panel)': [8080, 9090, 10000],
            r'(phpmyadmin|mysql)': [80, 443, 3306],
            r'(jenkins)': [8080, 8443],
            r'(gitlab|git)': [80, 443],
            r'(tomcat)': [8080, 8443],
            r'(apache)': [80, 443],
            r'(nginx)': [80, 443],
            r'(iis)': [80, 443],
            r'(ftp)': [21],
            r'(ssh)': [22],
            r'(smtp|mail)': [25, 465, 587],
            r'(dns)': [53],
            r'(ldap)': [389, 636]
        }
        
        ports = set()
        for pattern, port_list in specific_recommendations.items():
            if re.search(pattern, combined):
                ports.update(port_list)
        
        return sorted(list(ports))
    
    def _generate_metadata(self):
        """Generate catalog metadata and statistics."""
        # Try to get SecLists version
        try:
            git_path = self.seclists_path / ".git"
            if git_path.exists():
                import subprocess
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.seclists_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.catalog.seclists_version = result.stdout.strip()[:8]
        except Exception:
            pass
        
        # Rebuild indexes
        self.catalog.rebuild_indexes()
        
        # Generate statistics
        self.catalog.get_stats()


def main():
    """Main function to generate SecLists catalog."""
    # Get SecLists path
    seclists_path = None
    
    # Try to read from .seclists_path file
    seclists_path_file = project_root / ".seclists_path"
    if seclists_path_file.exists():
        try:
            with open(seclists_path_file, 'r') as f:
                content = f.read().strip()
                # Extract path from SECLISTS_PATH="path" format
                match = re.search(r'SECLISTS_PATH="([^"]*)"', content)
                if match:
                    seclists_path = match.group(1)
        except Exception:
            pass
    
    # Fallback to command line argument or common locations
    if not seclists_path and len(sys.argv) > 1:
        seclists_path = sys.argv[1]
    
    if not seclists_path:
        # Try common locations
        common_paths = [
            "/opt/SecLists",
            "/usr/share/SecLists",
            os.path.expanduser("~/SecLists")
        ]
        
        for path in common_paths:
            if Path(path).exists():
                seclists_path = path
                break
    
    if not seclists_path:
        print("Error: SecLists path not found!")
        print("Usage: python generate_catalog.py [seclists_path]")
        print("Or ensure SecLists is installed in a common location.")
        return 1
    
    try:
        # Generate catalog
        parser = SecListsParser(seclists_path)
        catalog = parser.parse_seclists()
        
        # Save catalog
        output_path = project_root / "database" / "wordlists" / "seclists_catalog.json"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Saving catalog to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            # Use model_dump() for Pydantic v2 compatibility
            catalog_data = catalog.model_dump() if hasattr(catalog, 'model_dump') else catalog.dict()
            json.dump(catalog_data, f, indent=2, default=str, ensure_ascii=False)
        
        # Print summary
        stats = catalog.get_stats()
        print(f"\n✓ Catalog generated successfully!")
        print(f"  Total wordlists: {stats['total_wordlists']}")
        print(f"  Categories: {stats['categories']}")
        print(f"  Technologies: {stats['technologies']}")
        print(f"  Total entries: {stats['size_stats']['total_entries']:,}")
        
        return 0
        
    except Exception as e:
        print(f"Error generating catalog: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())