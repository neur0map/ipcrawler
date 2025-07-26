#!/usr/bin/env python3
"""
SecLists Catalog Generator

This script generates a comprehensive catalog of SecLists wordlists with metadata
for intelligent wordlist recommendations in IPCrawler.
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any
from datetime import datetime

# Add project root to path for imports
current_file = Path(__file__).resolve()
# Find project root by looking for the directory containing 'database' folder
project_root = current_file.parent
while project_root.parent != project_root:  # Not at filesystem root
    if (project_root / 'database').exists():
        break
    project_root = project_root.parent
else:
    # Fallback to 4 levels up
    project_root = current_file.parent.parent.parent.parent

sys.path.insert(0, str(project_root))

from src.core.tools.catalog.models import WordlistCatalog, WordlistCategory, WordlistQuality, WordlistSubcategory, WordlistEntry


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
            '21': 'ftp',
            '22': 'ssh', 
            '23': 'telnet',
            '25': 'smtp',
            '53': 'dns',
            '80': 'http',
            '110': 'pop3',
            '143': 'imap',
            '443': 'https',
            '993': 'imaps',
            '995': 'pop3s'
        }
    
    def parse_directory(self) -> WordlistCatalog:
        """Parse entire SecLists directory and generate catalog."""
        
        print(f"Scanning {self.seclists_path} for wordlists...")
        
        # Find all .txt files
        txt_files = list(self.seclists_path.rglob("*.txt"))
        
        # Separate files by size
        regular_files = []
        large_files = []
        
        for txt_file in txt_files:
            try:
                file_size = txt_file.stat().st_size
                if file_size > 50 * 1024 * 1024:  # 50MB threshold
                    large_files.append(txt_file)
                else:
                    regular_files.append(txt_file)
            except OSError:
                continue
        
        print(f"Found {len(regular_files)} regular files and {len(large_files)} large files")
        
        # Process regular files first
        processed = 0
        for txt_file in regular_files:
            try:
                wordlist = self._parse_wordlist_file(txt_file)
                if wordlist:
                    self.catalog.add_wordlist(wordlist)
                    processed += 1
                    
                    if processed % 100 == 0:
                        print(f"Processed {processed} files...")
                        
            except Exception as e:
                print(f"Error processing {txt_file}: {e}")
                continue
        
        # Process large files
        processed = 0
        for txt_file in large_files:
            try:
                wordlist = self._parse_large_wordlist_file(txt_file)
                if wordlist:
                    self.catalog.add_wordlist(wordlist)
                    processed += 1
                    
                    if processed % 100 == 0:
                        print(f"Processed {processed} files...")
                        
            except Exception as e:
                print(f"Error processing {txt_file}: {e}")
                continue
        
        return self.catalog
    
    def _parse_wordlist_file(self, file_path: Path) -> Any | None:
        """Parse individual wordlist file and extract metadata."""
        # Basic file info
        stat = file_path.stat()
        relative_path = file_path.relative_to(self.seclists_path)
        
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
    
    def _count_lines(self, file_path: Path) -> int:
        """Efficiently count lines in file."""
        count = sum(1 for _ in f)
        return count
    
    def _count_lines_buffered(self, file_path: Path, buffer_size: int = 1024 * 1024) -> int:
        """Count lines in large files using buffered reading."""
        count = 0
        with open(file_path, 'rb') as f:
            while True:
                buffer = f.read(buffer_size)
                if not buffer:
                    break
                count += buffer.count(b'\n')
        # Fallback: estimate based on file size (avg 10 chars per line)
        return int(file_path.stat().st_size / 10)
    
    def _get_sample_entries_large(self, file_path: Path, max_samples: int = 3) -> List[str]:
        """Get sample entries from large files without loading entire file."""
        samples = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_samples:
                    break
                line = line.strip()
                if line:
                    samples.append(line)
        return samples
    
    def _get_sample_entries(self, file_path: Path, max_samples: int = 5) -> List[str]:
        """Get sample entries from wordlist for preview."""
        samples = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_samples:
                    break
                line = line.strip()
                if line:
                    samples.append(line)
        return samples
    
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
        
        for pattern, category in category_mappings.items():
            if re.search(pattern, path_str):
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
            name = f"{name} ({context})"
        
        return name
    
    def _extract_tags(self, filename: str, relative_path: Path) -> Set[str]:
        """Extract relevant tags from filename and path."""
        tags = set()
        
        # Extract from filename
        filename_lower = filename.lower()
        
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
        
        for pattern, tag in tag_patterns.items():
            if re.search(tag, filename_lower):
                tags.add(pattern)
        
        # Add size-based tags
        if relative_path.parent.name == 'fuzzing':
            tags.add('fuzzing')
        elif relative_path.parent.name == 'misconfiguration':
            tags.add('misconfiguration')
        elif relative_path.parent.name == 'discovery/infrastructure':
            tags.add('network')
        elif relative_path.parent.name == 'protocol':
            tags.add('protocol')
        elif relative_path.parent.name == 'vulnerability':
            tags.add('vulnerability')
        elif relative_path.parent.name == 'web-shells':
            tags.add('web-shells')
        elif relative_path.parent.name == 'cms':
            tags.add('cms')
        elif relative_path.parent.name == 'database':
            tags.add('database')
        elif relative_path.parent.name == 'api':
            tags.add('api')
        elif relative_path.parent.name == 'admin':
            tags.add('admin')
        elif relative_path.parent.name == 'authentication':
            tags.add('authentication')
        elif relative_path.parent.name == 'backup':
            tags.add('backup')
        elif relative_path.parent.name == 'config':
            tags.add('config')
        elif relative_path.parent.name == 'development':
            tags.add('development')
        elif relative_path.parent.name == 'mail':
            tags.add('mail')
        elif relative_path.parent.name == 'file':
            tags.add('file')
        elif relative_path.parent.name == 'framework':
            tags.add('framework')
        
        return tags
    
    def _extract_tech_compatibility(self, filename: str, relative_path: Path) -> Set[str]:
        """Extract technology compatibility from filename and path."""
        techs = set()
        
        combined_text = f"{filename} {relative_path}".lower()
        
        for pattern, tech in self.tech_patterns.items():
            if re.search(tech, combined_text):
                techs.add(pattern)
        
        return techs
    
    def _extract_port_compatibility(self, filename: str, relative_path: Path) -> Set[str]:
        """Extract port associations from filename and path."""
        ports = set()
        
        combined_text = f"{filename} {relative_path}".lower()
        
        for port, service in self.port_patterns.items():
            if re.search(port, combined_text):
                ports.add(service)
        
        return ports
    
    def _determine_quality(self, line_count: int, sample_entries: List[str]) -> WordlistQuality:
        """Determine wordlist quality based on size and content."""
        if line_count >= 50000:
            return WordlistQuality.EXCELLENT
        elif line_count >= 10000:
            return WordlistQuality.GOOD
        elif line_count >= 1000:
            return WordlistQuality.AVERAGE
        else:
            return WordlistQuality.SPECIALIZED
    
    def _calculate_scorer_weight(self, category: WordlistCategory, line_count: int, tech_compatibility: Set[str]) -> float:
        """Calculate base scorer weight."""
        # Base weight by category
        category_weights = {
            WordlistCategory.WEB_CONTENT: 1.0,
            WordlistCategory.SUBDOMAIN: 0.8,
            WordlistCategory.USERNAMES: 0.7,
            WordlistCategory.PASSWORDS: 0.7,
            WordlistCategory.FUZZING: 0.9,
            WordlistCategory.MISCONFIGURATION: 0.6,
            WordlistCategory.NETWORK: 0.9,
            WordlistCategory.PROTOCOLS: 0.8,
            WordlistCategory.VULNERABILITY: 1.0,
            WordlistCategory.CMS: 0.9,
            WordlistCategory.DATABASE: 0.8,
            WordlistCategory.API: 0.9,
            WordlistCategory.ADMIN_PANEL: 0.9,
            WordlistCategory.AUTHENTICATION: 0.8,
            WordlistCategory.BACKUP: 0.7,
            WordlistCategory.CONFIG: 0.6,
            WordlistCategory.DEVELOPMENT: 0.7,
            WordlistCategory.MAIL: 0.6,
            WordlistCategory.FILE_TRANSFER: 0.7,
            WordlistCategory.FRAMEWORK: 0.8,
            WordlistCategory.OTHER: 0.5
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
        return final_weight
    
    def _get_subcategory(self, relative_path: Path) -> WordlistSubcategory:
        """Get subcategory from path structure."""
        parts = relative_path.parts
        if len(parts) >= 2:
            return WordlistSubcategory.from_path(relative_path)
        return WordlistSubcategory.OTHER
    
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
        
        for pattern, use_case in use_case_patterns.items():
            if re.search(use_case, combined):
                use_cases.append(pattern)
        
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
        
        description += f". Contains {line_count:,} entries"
        
        # Add quality indicator
        if line_count >= 50000:
            description += " (comprehensive list)"
        elif line_count >= 10000:
            description += " (extensive list)"
        elif line_count >= 1000:
            description += " (standard list)"
        else:
            description += " (specialized list)"
        
        return description
    
    def _get_recommended_ports(self, relative_path: Path, filename: str) -> Set[str]:
        """Get specifically recommended ports for this wordlist."""
        # This is more specific than general port compatibility
        combined = f"{relative_path} {filename}".lower()
        
        specific_recommendations = set()
        
        for port, service in self.port_patterns.items():
            if re.search(port, combined):
                specific_recommendations.add(service)
        
        return specific_recommendations
    
    def _parse_large_wordlist_file(self, file_path: Path) -> Any | None:
        """Parse large wordlist file with memory-efficient methods."""
        # Basic file info
        stat = file_path.stat()
        relative_path = file_path.relative_to(self.seclists_path)
        
        # Count lines using memory-efficient method with buffer
        line_count = self._count_lines_buffered(file_path)
        
        # Determine category from path
        category = self._determine_category(relative_path)
        
        # Extract metadata from path and filename
        display_name = self._generate_display_name(file_path.name, relative_path)
        tags = self._extract_tags(file_path.name, relative_path)
        tech_compatibility = self._extract_tech_compatibility(file_path.name, relative_path)
        port_compatibility = self._extract_port_compatibility(file_path.name, relative_path)
        
        # Get limited sample entries for large files
        sample_entries = self._get_sample_entries_large(file_path, max_samples=3)
        
        # Add 'large' tag
        tags.add('large')
        
        # Determine quality based on size
        quality = WordlistQuality.EXCELLENT  # Large files are typically comprehensive
        
        # Calculate scorer weight
        scorer_weight = self._calculate_scorer_weight(category, line_count, tech_compatibility)
        
        description = self._generate_description(file_path.name, relative_path, line_count)
        description += " (Large file - may require special handling)"
        
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
    
    def _generate_catalog_metadata(self) -> Dict[str, Any]:
        """Generate catalog metadata and statistics."""
        metadata = {
            "seclists_path": str(self.seclists_path),
            "total_wordlists": len(self.catalog.wordlists),
            "total_size_bytes": sum(w.size_bytes for w in self.catalog.wordlists),
            "total_size_lines": sum(w.size_lines for w in self.catalog.wordlists),
            "seclists_version": self.catalog.seclists_version,
            "last_updated": datetime.now().isoformat()
        }
        return metadata


def main():
    """Main function to generate SecLists catalog."""
    # Determine SecLists path
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
        except Exception as e:
            print(f"Error reading .seclists_path file: {e}")
    
    # Fallback to command line argument or common locations
    if not seclists_path:
        if len(sys.argv) > 1:
            seclists_path = sys.argv[1]
        else:
            # Try common locations
            common_paths = [
                "/opt/SecLists",
                "/usr/share/SecLists",
                "/usr/share/seclists"
            ]
            for path in common_paths:
                if Path(path).exists():
                    seclists_path = path
                    break
    
    if not seclists_path:
        print("Error: SecLists directory not found. Please specify the path or ensure it's in common locations.")
        sys.exit(1)
    
    print(f"Using SecLists path: {seclists_path}")
    
    # Generate catalog
    parser = SecListsParser(seclists_path)
    catalog = parser.parse_directory()
    
    # Save catalog
    output_path = project_root / "database" / "wordlists" / "seclists_catalog.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog.model_dump(), f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n✓ Catalog generated: {output_path}")
    
    # Print summary
    stats = catalog.get_stats()
    print(f"Total wordlists: {stats.get('total_wordlists', 0)}")
    print(f"Total size: {stats.get('total_size_mb', 0):.1f}MB")
    print(f"Categories: {len(stats.get('categories', {}))}")


if __name__ == "__main__":
    main()
