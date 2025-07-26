#!/usr/bin/env python3
"""

"""


# Add project root to path for imports
current_file = Path(__file__).resolve()
# Find project root by looking for the directory containing 'database' folder
project_root = current_file.parent
while project_root.parent != project_root:  # Not at filesystem root
    project_root = project_root.parent
    # Fallback to 4 levels up
    project_root = current_file.parent.parent.parent.parent


)


    """Parser for SecLists directory structure."""
    
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
        }
    
        """Parse entire SecLists directory and generate catalog."""
        
        
        # Find all .txt files
        txt_files = list(self.seclists_path.rglob("*.txt"))
        
        # Separate files by size
        regular_files = []
        large_files = []
        
                file_size = txt_file.stat().st_size
        
        
        processed = 0
                wordlist = self._parse_wordlist_file(txt_file)
                    processed += 1
                    
                    if processed % 100 == 0:
                        
        
        
                    wordlist = self._parse_large_wordlist_file(txt_file)
                        processed += 1
        
        
        
    
        """Parse individual wordlist file and extract metadata."""
            # Basic file info
            stat = file_path.stat()
            relative_path = file_path.relative_to(self.seclists_path)
            
            # Large files are handled separately now
            
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
            
            
    
        """Efficiently count lines in file."""
                count = sum(1 for _ in f)
    
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
            
            
    
    def _count_lines_buffered(self, file_path: Path, buffer_size: int = 1024 * 1024) -> int:
        """Count lines in large files using buffered reading."""
            count = 0
                buffer = f.read(buffer_size)
                    count += buffer.count(b'\n')
                    buffer = f.read(buffer_size)
            # Fallback: estimate based on file size (avg 10 chars per line)
    
    def _get_sample_entries_large(self, file_path: Path, max_samples: int = 3) -> List[str]:
        """Get sample entries from large files without loading entire file."""
        samples = []
        
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    if i >= max_samples:
                    
                    line = line.strip()
            
        
    
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
        
        
        # Add size-based tags
        
    
        """Extract technology compatibility from filename and path."""
        techs = set()
        
        combined_text = f"{filename} {relative_path}".lower()
        
        
    
        """Extract port associations from filename and path."""
        ports = set()
        
        combined_text = f"{filename} {relative_path}".lower()
        
        
    
    def _get_sample_entries(self, file_path: Path, max_samples: int = 5) -> List[str]:
        """Get sample entries from wordlist for preview."""
        samples = []
        
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    if i >= max_samples:
                    
                    line = line.strip()
            
        
    
        """Determine wordlist quality based on size and content."""
        if line_count >= 50000:
        elif line_count >= 10000:
        elif line_count >= 1000:
    
        """Calculate base scorer weight."""
        # Base weight by category
        category_weights = {
        }
        
        base_weight = category_weights.get(category, 0.5)
        
        # Adjust for size (quality)
        if line_count >= 10000:
            size_multiplier = 1.2
        elif line_count >= 1000:
            size_multiplier = 1.1
        elif line_count >= 100:
            size_multiplier = 1.0
            size_multiplier = 0.8
        
        # Adjust for specificity (fewer techs = more specific = higher weight)
        if len(tech_compatibility) == 1:
            specificity_multiplier = 1.2
        elif len(tech_compatibility) <= 3:
            specificity_multiplier = 1.1
            specificity_multiplier = 1.0
        
        final_weight = base_weight * size_multiplier * specificity_multiplier
    
        """Get subcategory from path structure."""
        parts = relative_path.parts
        if len(parts) >= 2:
    
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
        
        
    
        """Generate description for the wordlist."""
        # Extract meaningful parts
        name_clean = filename.replace('.txt', '').replace('-', ' ').replace('_', ' ')
        
        # Get category context
        path_parts = [part.replace('-', ' ') for part in relative_path.parts[:-1]]
        context = ' / '.join(path_parts).title()
        
        # Build description
        description = f"Wordlist for {name_clean}"
        
            description += f" in {context}"
        
            description += f". Contains {line_count:,} entries"
        
        # Add quality indicator
        if line_count >= 50000:
            description += " (comprehensive list)"
        elif line_count >= 10000:
            description += " (extensive list)"
        elif line_count >= 1000:
            description += " (standard list)"
            description += " (specialized list)"
        
    
        """Get specifically recommended ports for this wordlist."""
        # This is more specific than general port compatibility
        combined = f"{relative_path} {filename}".lower()
        
        specific_recommendations = {
        }
        
        ports = set()
        
    
        """Generate catalog metadata and statistics."""
        # Try to get SecLists version
            git_path = self.seclists_path / ".git"
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.seclists_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.catalog.seclists_version = result.stdout.strip()[:8]
        
        # Rebuild indexes
        


    """Main function to generate SecLists catalog."""
    # Get SecLists path
    seclists_path = None
    
    # Try to read from .seclists_path file
    seclists_path_file = project_root / ".seclists_path"
                content = f.read().strip()
                # Extract path from SECLISTS_PATH="path" format
                match = re.search(r'SECLISTS_PATH="([^"]*)"', content)
                    seclists_path = match.group(1)
    
    # Fallback to command line argument or common locations
        seclists_path = sys.argv[1]
    
        # Try common locations
        common_paths = [
            "/opt/SecLists",
            "/usr/share/SecLists",
        ]
        
                seclists_path = path
    
    
        parser = SecListsParser(seclists_path)
        catalog = parser.parse_seclists()
        
        output_path = project_root / "database" / "wordlists" / "seclists_catalog.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(catalog.model_dump(), f, indent=2, default=str, ensure_ascii=False)
        
        # Print summary
        stats = catalog.get_stats()
        
        


if __name__ == "__main__":
