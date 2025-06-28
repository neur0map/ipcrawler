"""
Smart Wordlist Selector for ipcrawler

Provides intelligent wordlist selection based on detected technologies
using pre-generated SecLists catalog and technology alias mapping.
"""

import os
import yaml
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

# Module-level cache for performance
_catalog_cache: Optional[Dict] = None
_aliases_cache: Optional[Dict] = None


class SmartWordlistSelector:
    """Intelligent wordlist selection based on technology detection"""
    
    def __init__(self, seclists_base_path: str):
        self.seclists_base_path = seclists_base_path
        self._last_selected_technology = None  # Track the last selected technology
        self._load_catalog()
        self._load_aliases()
    
    def _load_catalog(self):
        """Load SecLists catalog from cache or file"""
        global _catalog_cache
        
        if _catalog_cache is not None:
            self.catalog = _catalog_cache
            return
        
        # Look for catalog in multiple locations
        catalog_paths = [
            os.path.join(os.path.dirname(__file__), 'data', 'unified_wordlists_catalog.yaml'),
            os.path.join(os.path.dirname(__file__), '..', 'data', 'unified_wordlists_catalog.yaml'),
            'unified_wordlists_catalog.yaml'  # Current directory
        ]
        
        for catalog_path in catalog_paths:
            if os.path.exists(catalog_path):
                try:
                    with open(catalog_path, 'r') as f:
                        _catalog_cache = yaml.safe_load(f)
                    self.catalog = _catalog_cache
                    return
                except Exception as e:
                    print(f"Warning: Could not load catalog from {catalog_path}: {e}")
        
        # No catalog found - try to auto-generate it
        print("⚠️  No unified wordlists catalog found for smart wordlist selection.")
        if self.seclists_base_path and os.path.exists(self.seclists_base_path):
            print(f"🤖 Auto-generating catalog for {self.seclists_base_path}...")
            try:
                catalog = self._generate_catalog_on_demand()
                if catalog:
                    _catalog_cache = catalog
                    self.catalog = _catalog_cache
                    print("✅ Catalog generated successfully!")
                    return
            except Exception as e:
                print(f"❌ Auto-generation failed: {e}")
        
        print("   Falling back to standard wordlist selection.")
        _catalog_cache = {'wordlists': {}}
        self.catalog = _catalog_cache
    
    def _load_aliases(self):
        """Load technology aliases from cache or file"""
        global _aliases_cache
        
        if _aliases_cache is not None:
            self.aliases = _aliases_cache
            return
        
        aliases_path = os.path.join(os.path.dirname(__file__), 'data', 'technology_aliases.yaml')
        
        try:
            with open(aliases_path, 'r') as f:
                _aliases_cache = yaml.safe_load(f)
            self.aliases = _aliases_cache
        except Exception as e:
            print(f"Warning: Could not load aliases from {aliases_path}: {e}")
            # Minimal fallback aliases
            _aliases_cache = {
                'technology_aliases': {
                    'wordpress': {'aliases': ['wordpress', 'wp'], 'priority': 'high'},
                    'php': {'aliases': ['php'], 'priority': 'medium'}
                },
                'scoring': {'alias_match_weight': 0.7, 'size_penalty_weight': 0.3, 'max_lines_threshold': 100000}
            }
            self.aliases = _aliases_cache
    
    def select_wordlist(self, category: str, detected_technologies: Set[str]) -> Optional[str]:
        """
        Select best wordlist for category based on detected technologies

        Args:
            category: Wordlist category (e.g., 'web_directories', 'web_files', 'vhosts', 'subdomains')
            detected_technologies: Set of detected technology strings

        Returns:
            Full path to selected wordlist, or None if no good match found
        """
        if not detected_technologies or not self.catalog.get('wordlists'):
            return None

        # Map web enumeration categories to standard categories
        category_mapping = {
            'vhosts': 'web_directories',
            'subdomains': 'web_directories', 
            'directories': 'web_directories',
            'files': 'web_files',
            'hostnames': 'web_directories',
            'virtual_hosts': 'web_directories'
        }
        
        # Use mapped category if available
        mapped_category = category_mapping.get(category, category)

        # Find best technology match using alias mapping
        best_tech = self._find_best_technology_match(detected_technologies)
        if not best_tech:
            return None

        # Store the selected technology for later use
        self._last_selected_technology = best_tech
        self._last_fallback_level = None

        # Get candidate wordlists for this technology
        candidates = self._get_candidate_wordlists(best_tech, mapped_category)
        fallback_level = "technology-specific"

        # If no technology-specific wordlists found, try generic ones
        if not candidates:
            candidates = self._get_generic_candidate_wordlists(mapped_category)
            fallback_level = "generic"

        # If still no candidates, try the most generic fallback
        if not candidates:
            candidates = self._get_fallback_candidate_wordlists(mapped_category)
            fallback_level = "fallback"

        # If STILL no candidates, try an extremely broad search
        if not candidates:
            candidates = self._get_desperate_fallback_wordlists(mapped_category)
            fallback_level = "desperate"

        # Store fallback level for reporting
        self._last_fallback_level = fallback_level

        # Score and select best candidate
        best_wordlist = self._score_and_select_candidates(candidates, best_tech)
        if not best_wordlist:
            return None

        # Return full path with proper resolution for premium wordlists
        full_path = self._resolve_wordlist_path(best_wordlist)
        return full_path if os.path.exists(full_path) else None
    
    def _resolve_wordlist_path(self, relative_path: str) -> str:
        """Resolve relative wordlist path to absolute path"""
        # Check if it's a premium wordlist that needs special path resolution
        if 'jhaddix' in relative_path.lower():
            # Jhaddix wordlists are in ~/tools/wordlists/jhaddix/
            jhaddix_paths = [
                os.path.expanduser("~/tools/wordlists/jhaddix/jhaddix-all.txt"),
                "/usr/share/wordlists/jhaddix/jhaddix-all.txt"
            ]
            for path in jhaddix_paths:
                if os.path.exists(path):
                    return path
        
        elif 'onelistforall' in relative_path.lower():
            # OneListForAll wordlists are in ~/tools/wordlists/onelistforall/
            base_dirs = [
                os.path.expanduser("~/tools/wordlists/onelistforall"),
                "/usr/share/wordlists/onelistforall"
            ]
            
            # Extract the actual filename from the relative path
            filename = relative_path.split('/')[-1]
            
            for base_dir in base_dirs:
                if os.path.exists(base_dir):
                    # Try the file directly in the base directory
                    full_path = os.path.join(base_dir, filename)
                    if os.path.exists(full_path):
                        return full_path
                    
                    # Try in subdirectories
                    for root, dirs, files in os.walk(base_dir):
                        if filename in files:
                            return os.path.join(root, filename)
        
        # Default: assume it's a SecLists wordlist
        return os.path.join(self.seclists_base_path, relative_path)

    def get_selected_technology(self) -> Optional[str]:
        """Get the last selected technology from wordlist selection"""
        return self._last_selected_technology

    def _get_security_tiers(self) -> Dict[str, Set[str]]:
        """Get security tiers for technology prioritization"""
        return {
            'critical': {  # Admin interfaces, high-value targets
                'wordpress', 'drupal', 'joomla', 'magento', 'phpmyadmin', 'cpanel', 'plesk',
                'jenkins', 'gitlab', 'grafana', 'splunk', 'sharepoint', 'confluence', 'jira',
                'tomcat', 'weblogic', 'pfsense', 'vmware', 'citrix', 'salesforce', 'sap',
                'directadmin', 'webmin', 'cyberpanel', 'paloalto', 'cisco', 'exchange',
                'oracle', 'adminer', 'dotnetnuke', 'sitecore', 'episerver', 'nextcloud',
                'mysql', 'postgresql', 'mongodb', 'shopify', 'scada', 'wonderware',
                'rockwell', 'schneider', 'keycloak', 'okta', 'auth0', 'activedirectory',
                'saml', 'cas', 'servicenow', 'jira_service', 'crowdstrike', 'sentinelone',
                'carbon_black', 'qualys', 'rapid7', 'github_enterprise', 'gitlab_enterprise',
                'azure_devops', 'microsoft_365', 'google_workspace', 'workday', 'netsuite',
                'oracle_erp', 'microsoft_dynamics', 'aws_api_gateway', 'azure_api', 'google_api'
            },
            'high': {  # CMS, databases, enterprise apps
                'prestashop', 'opencart', 'concrete5', 'typo3', 'ghost', 'umbraco',
                'liferay', 'plone', 'phpbb', 'vbulletin', 'invision', 'discourse',
                'flarum', 'notion', 'bookstack', 'outline', 'mediawiki', 'dokuwiki',
                'mssql', 'cassandra', 'couchdb', 'neo4j', 'influxdb', 'clickhouse',
                'roundcube', 'squirrelmail', 'zimbra', 'moodle', 'chamilo', 'canvas',
                'blackboard', 'schoology', 'claroline', 'sakai', 'brightspace',
                'zabbix', 'nagios', 'cacti', 'prtg', 'prometheus', 'kibana',
                'sonarqube', 'artifactory', 'nexus', 'bamboo', 'teamcity', 'bitbucket',
                'juniper', 'fortinet', 'sonicwall', 'checkpoint', 'aws', 'azure', 'gcp',
                'totara', 'absorb', 'cornerstone', 'docebo', 'talentlms', 'litmos',
                'google_classroom', 'microsoft_teams_edu', 'hubspot_crm', 'zoho_crm',
                'freshsales', 'insightly', 'vtiger', 'suitecrm', 'civicrm', 'mulesoft',
                'azure_api', 'aws_api_gateway', 'google_api', 'confluence_server',
                'freshdesk_pro', 'jira_service', 'kayako', 'spiceworks', 'rdp'
            },
            'medium': {  # Frameworks, development tools, platforms
                'php', 'asp', 'java', 'python', 'ruby', 'nodejs', 'nextjs', 'golang',
                'rust', 'scala', 'kotlin', 'coldfusion', 'react', 'vue', 'angular',
                'svelte', 'django', 'flask', 'fastapi', 'rails', 'laravel', 'symfony',
                'codeigniter', 'cakephp', 'yii', 'zend', 'spring', 'struts',
                'nginx', 'apache', 'iis', 'websphere', 'jboss', 'glassfish', 'resin',
                'payara', 'liberty', 'undertow', 'sqlite', 'docker', 'kubernetes',
                'openshift', 'rancher', 'nomad', 'harbor', 'istio', 'linkerd', 'consul',
                'synology', 'qnap', 'freenas', 'proxmox', 'ansible', 'puppet', 'chef',
                'saltstack', 'terraform', 'vercel', 'netlify', 'heroku', 'gatsby',
                'hugo', 'jekyll', 'nuxt', 'tableau', 'powerbi', 'qlik', 'slack',
                'teams', 'zoom', 'webex', 'alfresco', 'selenium', 'sentry', 'bugsnag',
                'rollbar', 'rabbitmq', 'kafka', 'elasticsearch', 'solr', 'redis',
                'haproxy', 'traefik', 'temenos', 'finastra', 'corebanking', 'pos',
                'micros', 'hubspot', 'marketo', 'jamf', 'intune', 'airwatch',
                'raspberry', 'openwrt', 'ddwrt', 'unifi', 'bitwarden', 'pritunl',
                'sugarcrm', 'odoo', 'osticket', 'digitalocean', 'linode', 'vultr',
                'hetzner', 'ovh', 'scaleway', 'contabo', 'hostinger', 'bluehost',
                'godaddy', 'namecheap', 'hostgator', 'dreamhost', 'siteground',
                'ispconfig', 'cloudways', 'wpengine', 'kinsta', 'pantheon',
                'oracle_cloud', 'ibm_cloud', 'alibaba_cloud', 'cloudflare', 'akamai',
                'fastly', 'bunnycdn', 'keycdn', 'office365', 'tiddlywiki',
                'wagtail', 'apostrophe', 'keystone', 'strapi', 'contentful', 'sanity',
                'forestry', 'netlify_cms', 'ghost_pro', 'webflow', 'squarespace', 'wix',
                'weebly', 'edmodo', 'pipedrive', 'rapidapi', 'postman_api', 'insomnia_api',
                'hostgator', 'bluehost', 'godaddy', 'namecheap', 'dreamhost', 'siteground',
                'a2hosting', 'inmotion', 'etsy', 'amazon_seller', 'ebay_seller', 'alibaba',
                'drupal_commerce', 'joomla_virtuemart', 'typo3_shop', 'roam', 'obsidian',
                'dropbox_business', 'box', 'mongodb_compass', 'redis_insight', 'pgadmin',
                'mysql_workbench', 'google_ads', 'facebook_ads', 'linkedin_ads', 'mailchimp_pro',
                'constant_contact', 'discord', 'telegram', 'whatsapp_business', 'cloudfront',
                'fastly', 'maxcdn', 'datadog', 'new_relic', 'dynatrace', 'pingdom',
                'browserstack', 'sauce_labs', 'lambdatest', 'adobe_creative', 'invision',
                'quickbooks', 'xero', 'freshbooks', 'bamboohr', 'adp', 'docusign', 'adobe_sign',
                'teamviewer', 'anydesk', 'vnc', 'acronis', 'commvault', 'netbackup',
                'symantec', 'mcafee', 'kaspersky', 'trend_micro', 'hootsuite', 'buffer', 'sprout_social'
            },
            'low': {  # Languages, basic tools, legacy, social platforms
                'perl', 'vbscript', 'blogger', 'tumblr', 'arduino', 'access', 'foxpro', 'dbase', 'cics',
                'ims', 'cobol', 'fortran', 'documentum', 'matlab', 'autocad', 'vimeo', 'youtube',
                'homeassistant', 'openhab', 'mqtt', 'memcached', 'facebook', 'twitter', 'linkedin',
                'steam', 'unity', 'arcgis', 'qgis', 'jupyter', 'rstudio', 'xibo',
                'lowendbox', 'buyvm', 'ramnode', 'wholesaleinternet', 'upcloud',
                'kamatera', 'time4vps', 'ventraip', 'x10hosting', '000webhost',
                'freehostia', 'testng', 'hyper-v', 'canva', 'figma', 'sketch',
                'smartthings', 'philips_hue', 'steam_community', 'epic_games',
                'minecraft', 'steam', 'bitcoin', 'ethereum', 'metamask', 'plex', 'emby', 'jellyfin',
                'tiddlywiki', 'webpack', 'babel', 'typescript', 'ionic', 'xamarin',
                'selenium', 'cypress', 'gitbook', 'mkdocs', 'sphinx', 'google_analytics',
                'matomo', 'bugsnag', 'stripe', 'paypal', 'square', 'mailchimp', 'sendgrid',
                'mailgun', 'netlify', 'vercel', 'github_pages', 'aws_lambda', 'azure_functions',
                'google_functions', 'thingsboard', 'ntopng', 'wireshark', 'graylog', 'fluentd',
                'logstash', 'insomnia', 'zapier', 'ifttt', 'dam', 'typeform', 'surveymonkey',
                'zendesk', 'freshdesk', 'intercom', 'toggl', 'harvest', 'lastpass', 'onepassword',
                'keepass', 'burpsuite', 'owasp_zap', 'nessus', 'openvas', 'metasploit', 'sqlite'
            }
        }

    def _find_best_technology_match(self, detected_technologies: Set[str]) -> Optional[str]:
        """Find best technology match using security-priority system + fuzzy matching"""
        if not self.aliases:
            return None

        try:
            from rapidfuzz import process, fuzz
        except ImportError:
            print("🔧 RapidFuzz not available - install with: pip install rapidfuzz")
            print("   ↳ Falling back to simple string matching (still functional)")
            return self._simple_technology_match(detected_technologies)

        tech_aliases = self.aliases.get('technology_aliases', {})
        if not tech_aliases:
            return None

        # Get security tiers
        security_tiers = self._get_security_tiers()
        
        # Find all matching technologies with their tiers
        technology_matches = {}
        
        for tech_key, tech_config in sorted(tech_aliases.items()):
            aliases = tech_config.get('aliases', [])
            
            # Determine security tier for this technology
            security_tier = 'unknown'
            tier_priority = 0
            for tier, tech_set in sorted(security_tiers.items()):
                if tech_key in tech_set:
                    security_tier = tier
                    tier_priority = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'unknown': 0}[tier]
                    break
            
            # Check each detected technology against this tech's aliases
            for detected in sorted(detected_technologies):
                alias_match = process.extractOne(
                    detected.lower(),
                    [alias.lower() for alias in aliases],
                    scorer=fuzz.partial_ratio,
                    score_cutoff=70
                )
                
                if alias_match:
                    match_score = alias_match[1] / 100.0  # Convert to 0-1 range
                    
                    # Apply standard priority bonus
                    priority = tech_config.get('priority', 'medium')
                    scoring_config = self.aliases.get('scoring', {})
                    priority_bonus = scoring_config.get('priority_bonus', {}).get(priority, 0)
                    
                    # Calculate final score with security tier weighting
                    base_score = match_score + priority_bonus
                    security_weighted_score = base_score + (tier_priority * 0.5)  # +2.0 for critical, +1.5 for high, etc.
                    
                    technology_matches[tech_key] = {
                        'score': security_weighted_score,
                        'tier': security_tier,
                        'tier_priority': tier_priority,
                        'base_score': base_score,
                        'detected_string': detected
                    }
        
        if not technology_matches:
            return None
        
        # Sort by security tier first, then by score within tier, then by technology name for deterministic tie-breaking
        sorted_matches = sorted(
            technology_matches.items(),
            key=lambda x: (x[1]['tier_priority'], x[1]['score'], x[0]),  # x[0] is tech_key for deterministic tie-breaking
            reverse=True
        )
        
        best_tech, best_info = sorted_matches[0]
        
        # Debug logging for transparency
        if len(technology_matches) > 1:
            print(f"🔍 Multiple technologies detected:")
            for tech, info in sorted_matches[:3]:  # Show top 3
                print(f"   • {tech} (tier: {info['tier']}, score: {info['score']:.2f}) from '{info['detected_string']}'")
            print(f"✅ Selected: {best_tech} (tier: {best_info['tier']}) - highest security priority")
        
        # Only return if we have a reasonable confidence (lowered threshold for better coverage)
        return best_tech if best_info['score'] > 0.4 else None
    
    def _simple_technology_match(self, detected_technologies: Set[str]) -> Optional[str]:
        """Fallback simple string matching with security priority when RapidFuzz unavailable"""
        if not self.aliases:
            return None

        tech_aliases = self.aliases.get('technology_aliases', {})
        if not tech_aliases:
            return None

        # Use centralized security tiers
        security_tiers = self._get_security_tiers()
        
        # Find matches organized by security tier
        tier_matches = {'critical': [], 'high': [], 'medium': [], 'low': [], 'unknown': []}
        
        for tech_key, tech_config in sorted(tech_aliases.items()):
            aliases = tech_config.get('aliases', [])
            
            # Determine security tier
            security_tier = 'unknown'
            for tier, tech_set in sorted(security_tiers.items()):
                if tech_key in tech_set:
                    security_tier = tier
                    break
            
            # Check for string matches
            for detected in sorted(detected_technologies):
                for alias in aliases:
                    if alias.lower() in detected.lower() or detected.lower() in alias.lower():
                        tier_matches[security_tier].append((tech_key, detected))
                        break  # Found a match for this tech, move to next
                else:
                    continue  # No match found for this detected tech
                break  # Found a match, move to next tech_key
        
        # Return highest priority match with deterministic tie-breaking
        for tier in ['critical', 'high', 'medium', 'low', 'unknown']:
            if tier_matches[tier]:
                # Sort matches within tier by technology name for deterministic selection
                sorted_tier_matches = sorted(tier_matches[tier], key=lambda x: x[0])  # Sort by tech_key
                best_tech, detected_string = sorted_tier_matches[0]  # Best match in highest available tier
                if len(sum(tier_matches.values(), [])) > 1:  # Multiple matches found
                    print(f"🔍 Multiple technologies detected (simple matching)")
                    print(f"✅ Selected: {best_tech} (tier: {tier}) - highest security priority")
                return best_tech
        
        return None
    
    def _get_candidate_wordlists(self, technology: str, category: str) -> List[Tuple[str, Dict]]:
        """Get candidate wordlists for technology and category with premium priority"""
        candidates = []
        
        if not self.catalog or 'wordlists' not in self.catalog:
            return candidates
        
        # Priority 1: Look for technology-specific wordlists first
        tech_specific_candidates = []
        for wordlist_path, wordlist_info in self.catalog['wordlists'].items():
            # Use enhanced technology matching
            if self._is_technology_relevant(technology, wordlist_path, wordlist_info):
                if self._is_appropriate_category(wordlist_info, category):
                    tech_specific_candidates.append((wordlist_path, wordlist_info))
        
        # If we found good technology-specific wordlists, use them
        if tech_specific_candidates:
            candidates.extend(tech_specific_candidates)
            print(f"🎯 Found {len(tech_specific_candidates)} technology-specific wordlists for {technology}")
            return candidates
        
        # Priority 2: Premium comprehensive wordlists as fallback
        if category in ['web_directories', 'web_files']:
            premium_candidates = self._get_premium_wordlists(category)
            candidates.extend(premium_candidates)
            if premium_candidates:
                print(f"🏆 Using premium wordlists for {category} (no tech-specific found)")
                return candidates
        
        # Priority 2: Technology-specific wordlists
        for wordlist_path, wordlist_info in self.catalog['wordlists'].items():
            path_lower = wordlist_path.lower()
            
            # Skip if already added as premium
            if any(wordlist_path == p for p, _ in candidates):
                continue
            
            # Use RapidFuzz for better technology matching
            if self._is_technology_relevant(technology, wordlist_path, wordlist_info):
                if self._is_appropriate_category(wordlist_info, category):
                    candidates.append((wordlist_path, wordlist_info))
        
        return candidates
    
    def _get_premium_wordlists(self, category: str) -> List[Tuple[str, Dict]]:
        """Get premium wordlists with highest priority"""
        premium_candidates = []
        
        # Premium wordlist priorities (highest to lowest)
        premium_priorities = [
            # Jhaddix wordlists - highest priority
            ('jhaddix', ['jhaddix', 'Discovery/Web-Content/jhaddix']),
            # OneListForAll comprehensive lists
            ('onelistforall', ['onelistforallshort.txt', 'onelistforallmicro.txt']),
            # Large SecLists comprehensive wordlists
            ('seclists_large', ['directory-list-2.3-big.txt', 'directory-list-2.3-medium.txt'])
        ]
        
        for priority_name, patterns in premium_priorities:
            for wordlist_path, wordlist_info in self.catalog['wordlists'].items():
                path_lower = wordlist_path.lower()
                
                # Check if this wordlist matches the premium pattern
                if any(pattern.lower() in path_lower for pattern in patterns):
                    if self._is_appropriate_category(wordlist_info, category):
                        lines = wordlist_info.get('lines', 0)
                        print(f"   🎯 Premium: {wordlist_path} ({lines:,} lines)")
                        premium_candidates.append((wordlist_path, wordlist_info))
                        
                        # For web discovery, one good premium wordlist is often enough
                        if category in ['web_directories', 'web_files'] and lines > 10000:
                            return premium_candidates
        
        return premium_candidates
    
    def _is_technology_relevant(self, technology: str, wordlist_path: str, wordlist_info: Dict) -> bool:
        """Check if wordlist is relevant to technology using enhanced path matching"""
        try:
            from rapidfuzz import fuzz
            
            path_lower = wordlist_path.lower()
            filename = os.path.basename(path_lower)
            
            # 1. Direct technology name match in path
            if technology.lower() in path_lower:
                return True
            
            # 2. Check existing tags (if any)
            tags = wordlist_info.get('tags', [])
            if tags and any(tag.lower() == technology.lower() for tag in tags):
                return True
            
            # 3. Enhanced path-based matching for wordlists without tags
            # Auto-generate implicit tags from path structure
            implicit_tags = self._extract_implicit_tags(wordlist_path)
            if any(tag.lower() == technology.lower() for tag in implicit_tags):
                return True
            
            # 4. Technology aliases matching
            tech_aliases = self.aliases.get('technology_aliases', {}).get(technology, {}).get('aliases', [])
            for alias in tech_aliases:
                # Check path and implicit tags
                if alias.lower() in path_lower:
                    return True
                if any(alias.lower() in tag.lower() for tag in implicit_tags):
                    return True
                # Fuzzy match on filename
                if fuzz.partial_ratio(alias.lower(), filename) > 75:  # Lowered threshold
                    return True
            
            # 5. Direct fuzzy matching on filename
            similarity = fuzz.partial_ratio(technology.lower(), filename)
            if similarity > 75:  # Lowered threshold for better coverage
                return True
            
            return False
            
        except ImportError:
            # Enhanced fallback without RapidFuzz
            path_lower = wordlist_path.lower()
            
            # Direct match
            if technology.lower() in path_lower:
                return True
            
            # Check tags
            tags = wordlist_info.get('tags', [])
            if tags and any(tag.lower() == technology.lower() for tag in tags):
                return True
            
            # Check implicit tags from path
            implicit_tags = self._extract_implicit_tags(wordlist_path)
            if any(tag.lower() == technology.lower() for tag in implicit_tags):
                return True
            
            # Check aliases
            tech_aliases = self.aliases.get('technology_aliases', {}).get(technology, {}).get('aliases', [])
            for alias in tech_aliases:
                if alias.lower() in path_lower:
                    return True
            
            return False
    
    def _extract_implicit_tags(self, wordlist_path: str) -> List[str]:
        """Extract implicit technology tags from wordlist path structure"""
        implicit_tags = []
        path_lower = wordlist_path.lower()
        
        # Split path into components for analysis
        path_parts = wordlist_path.lower().replace('\\\\', '/').split('/')
        filename = os.path.basename(path_lower)
        
        # Technology patterns in path/filename
        tech_patterns = {
            'wordpress': ['wordpress', 'wp-', 'wp_', 'wpadmin'],
            'drupal': ['drupal'],
            'joomla': ['joomla'],
            'apache': ['apache', 'httpd'],
            'nginx': ['nginx'],
            'iis': ['iis', 'microsoft'],
            'tomcat': ['tomcat'],
            'php': ['php', '.php'],
            'asp': ['asp', '.asp', '.aspx'],
            'coldfusion': ['coldfusion', 'cfm'],
            'django': ['django'],
            'rails': ['rails', 'ruby'],
            'nodejs': ['node', 'express'],
            'sharepoint': ['sharepoint'],
            'jenkins': ['jenkins'],
            'gitlab': ['gitlab'],
            'mysql': ['mysql'],
            'mssql': ['mssql', 'sqlserver'],
            'oracle': ['oracle'],
            'mongodb': ['mongo'],
            'elasticsearch': ['elastic'],
            'redis': ['redis'],
            'ftp': ['ftp'],
            'ssh': ['ssh'],
            'telnet': ['telnet'],
            'smtp': ['smtp'],
            'snmp': ['snmp'],
            'ldap': ['ldap'],
            'smb': ['smb', 'samba'],
            'nfs': ['nfs']
        }
        
        # Check each pattern
        for tech, patterns in tech_patterns.items():
            for pattern in patterns:
                if pattern in path_lower:
                    implicit_tags.append(tech)
                    break
        
        # CMS-specific detection
        if 'cms' in path_lower:
            for part in path_parts:
                if part and len(part) > 2:  # Avoid short meaningless parts
                    # Check if this part matches a known CMS
                    cms_names = ['wordpress', 'drupal', 'joomla', 'magento', 'prestashop', 'opencart']
                    for cms in cms_names:
                        if cms in part:
                            implicit_tags.append(cms)
        
        # Framework detection
        if 'framework' in path_lower or 'language' in path_lower:
            framework_names = ['django', 'rails', 'laravel', 'symfony', 'codeigniter', 'yii', 'zend']
            for framework in framework_names:
                if framework in path_lower:
                    implicit_tags.append(framework)
        
        # Remove duplicates and return
        return list(set(implicit_tags))
    
    def _get_generic_candidate_wordlists(self, category: str) -> List[Tuple[str, Dict]]:
        """Get generic wordlists when technology-specific ones aren't available"""
        candidates = []
        
        if not self.catalog or 'wordlists' not in self.catalog:
            return candidates
        
        # Enhanced generic patterns for web enumeration
        generic_patterns = {
            'web_directories': [
                'directory', 'web-content', 'common', 'big.txt', 'medium.txt', 'small.txt',
                'discovery', 'subdomain', 'vhost', 'dns', 'top1million', 'directory-list'
            ],
            'web_files': [
                'file', 'extension', 'web-content', 'common', 'backup', 'config',
                'discovery', 'directory-list'
            ],
            'usernames': ['username', 'user', 'names', 'admin'],
            'passwords': ['password', 'pass', 'common', 'rockyou']
        }
        
        relevant_patterns = generic_patterns.get(category, [])
        if not relevant_patterns:
            # Fallback to web directory patterns for unknown categories
            relevant_patterns = generic_patterns['web_directories']
        
        print(f"🔍 Searching for generic wordlists with patterns: {relevant_patterns[:3]}...")
        
        for wordlist_path, wordlist_info in sorted(self.catalog['wordlists'].items()):
            path_lower = wordlist_path.lower()
            
            # Check if wordlist matches any of the generic patterns
            if any(pattern in path_lower for pattern in relevant_patterns):
                # Check if wordlist is appropriate for the category
                if self._is_appropriate_category_generic(wordlist_info, category, path_lower):
                    candidates.append((wordlist_path, wordlist_info))
        
        if candidates:
            print(f"🎯 Found {len(candidates)} generic wordlists for {category}")
        
        return candidates
    
    def _get_fallback_candidate_wordlists(self, category: str) -> List[Tuple[str, Dict]]:
        """Get most generic fallback wordlists as last resort"""
        candidates = []
        
        if not self.catalog or 'wordlists' not in self.catalog:
            return candidates
        
        # Extremely broad fallback patterns - accept any web-related wordlist
        fallback_patterns = {
            'web_directories': ['web', 'dir', 'common', 'big.txt', 'medium.txt'],
            'web_files': ['web', 'file', 'common', 'big.txt', 'medium.txt']
        }
        
        relevant_patterns = fallback_patterns.get(category, [])
        
        for wordlist_path, wordlist_info in sorted(self.catalog['wordlists'].items()):
            path_lower = wordlist_path.lower()
            wordlist_category = wordlist_info.get('category', 'other')

            # First check if it's categorized as 'web' (most reliable)
            if category in ['web_directories', 'web_files'] and wordlist_category == 'web':
                candidates.append((wordlist_path, wordlist_info))
                continue

            # Very permissive matching for fallback
            if any(pattern in path_lower for pattern in relevant_patterns):
                # Accept almost anything for fallback
                if ('discovery' in path_lower or
                    'fuzzing' in path_lower or
                    'dirbuster' in path_lower or
                    'common' in path_lower):
                    candidates.append((wordlist_path, wordlist_info))
        
        return candidates
    
    def _get_desperate_fallback_wordlists(self, category: str) -> List[Tuple[str, Dict]]:
        """Extremely broad fallback - find ANY potential wordlist"""
        candidates = []
        
        if not self.catalog or 'wordlists' not in self.catalog:
            return candidates
        
        # Accept almost anything that looks like it could be a wordlist
        for wordlist_path, wordlist_info in sorted(self.catalog['wordlists'].items()):
            path_lower = wordlist_path.lower()
            filename = os.path.basename(path_lower)
            wordlist_category = wordlist_info.get('category', 'other')

            # First check if it's categorized as 'web' (most reliable)
            if category in ['web_directories', 'web_files'] and wordlist_category == 'web':
                candidates.append((wordlist_path, wordlist_info))
                continue

            # Very broad acceptance criteria
            if (category == 'web_directories' and
                (any(word in path_lower for word in ['discovery', 'web', 'dir', 'content', 'common', 'list']) or
                 any(word in filename for word in ['dir', 'common', 'list', 'medium', 'big', 'small']) or
                 filename.endswith('.txt'))):
                candidates.append((wordlist_path, wordlist_info))
        
        return candidates
    
    def _is_appropriate_category_generic(self, wordlist_info: Dict, category: str, path_lower: str) -> bool:
        """Check if a generic wordlist is appropriate for the requested category"""
        # For generic wordlists, we're more permissive with categories
        # since they're meant to be broadly applicable

        if category in ['web_directories', 'web_files']:
            # First check if it's categorized as 'web' (most reliable)
            wordlist_category = wordlist_info.get('category', 'other')
            if wordlist_category == 'web':
                return True

            # Also accept if it's in web-content discovery or contains directory/file keywords
            return ('web-content' in path_lower or
                   'discovery' in path_lower or
                   'directory' in path_lower or
                   'dirbuster' in path_lower or
                   'raft' in path_lower or
                   'common' in path_lower or
                   'web' in path_lower)

        # For other categories, use the stricter check
        return self._is_appropriate_category(wordlist_info, category)
    
    def _is_appropriate_category(self, wordlist_info: Dict, category: str) -> bool:
        """Check if wordlist is appropriate for the requested category"""
        wordlist_category = wordlist_info.get('category', 'other')
        
        # Category mapping
        category_mapping = {
            'web_directories': ['web'],
            'web_files': ['web'],
            'usernames': ['usernames'],
            'passwords': ['passwords'],
            'subdomains': ['dns'],
            'vhosts': ['dns'],
            'snmp_communities': ['snmp']
        }
        
        appropriate_categories = category_mapping.get(category, ['other'])
        return wordlist_category in appropriate_categories
    
    def _score_and_select_candidates(self, candidates: List[Tuple[str, Dict]], technology: str) -> Optional[str]:
        """Score candidates and select the best one"""
        if not candidates:
            return None
        
        scoring_config = self.aliases.get('scoring', {})
        alias_weight = scoring_config.get('alias_match_weight', 0.7)
        size_weight = scoring_config.get('size_penalty_weight', 0.3)
        max_lines = scoring_config.get('max_lines_threshold', 100000)
        
        scored_candidates = []
        
        for wordlist_path, wordlist_info in candidates:
            # Alias match score (how well the filename matches the technology)
            alias_score = self._calculate_alias_score(wordlist_path, technology)
            
            # Smart size handling - avoid tiny wordlists for directory enumeration
            lines = wordlist_info.get('lines', 0)
            size_score = self._calculate_size_score(wordlist_path, lines)
            
            # Final score
            final_score = (alias_score * alias_weight) + (size_score * size_weight)
            
            scored_candidates.append((final_score, wordlist_path, wordlist_info))
        
        # Sort by score (descending), then by wordlist path for deterministic tie-breaking
        scored_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

        # Use adaptive threshold - more lenient for better coverage
        min_threshold = 0.2  # Lowered from 0.3
        if scored_candidates:
            best_score = scored_candidates[0][0]
            # If we have candidates but none score above 0.2, use an even lower threshold
            # This handles cases where we're using generic wordlists that don't match the technology name
            if best_score <= 0.2 and best_score > -0.3:  # Accept reasonable generic wordlists
                min_threshold = -0.3  # More lenient

        if scored_candidates and scored_candidates[0][0] > min_threshold:
            return scored_candidates[0][1]

        return None
    
    def _calculate_size_score(self, wordlist_path: str, lines: int) -> float:
        """Calculate size score - prefer comprehensive wordlists for directory enumeration"""
        path_lower = wordlist_path.lower()
        
        # Ensure lines is an integer (handle string values from catalog)
        try:
            if isinstance(lines, str) and lines.startswith('>'):
                # Handle legacy string format like ">500000"
                lines_int = int(lines[1:])  # Remove '>' and convert to int
            else:
                lines_int = int(lines) if lines is not None else 0
        except (ValueError, TypeError):
            lines_int = 0  # Default to 0 if conversion fails
        
        # For directory/web enumeration, we want comprehensive but reasonable wordlists
        if any(term in path_lower for term in ['web-content', 'discovery', 'directory', 'file']):
            # Penalize tiny wordlists heavily for directory enumeration
            if lines_int < 100:
                return -0.5  # Heavy penalty for tiny lists like joomla-themes.fuzz.txt (30 lines)
            elif lines_int < 1000:
                return 0.0   # Neutral for small lists
            elif lines_int < 10000:
                return 0.3   # Good for medium lists
            elif lines_int < 20000:
                return 0.5   # Best for comprehensive lists (sweet spot)
            else:
                return -0.3  # Penalty for massive wordlists (>20K lines) - too slow
        
        # For other categories (usernames, passwords), prefer smaller targeted lists
        else:
            if lines_int > 50000:
                return -0.2  # Penalty for huge lists
            elif lines_int > 10000:
                return 0.0   # Neutral for large lists
            elif lines_int > 1000:
                return 0.3   # Good for medium lists
            else:
                return 0.5   # Best for small targeted lists
    
    def _calculate_alias_score(self, wordlist_path: str, technology: str) -> float:
        """Calculate how well wordlist path matches technology"""
        path_lower = wordlist_path.lower()
        tech_lower = technology.lower()
        filename = os.path.basename(path_lower)
        
        # Penalize overly specific wordlists for general directory enumeration
        if any(term in filename for term in ['themes', 'plugins', 'extensions', 'modules']):
            # These are too specific for general directory busting
            if any(term in path_lower for term in ['web-content', 'discovery']):
                return 0.2  # Low score for overly specific lists
        
        # Exact match in filename
        if tech_lower in filename:
            # Prefer general wordlists over specific ones
            if any(term in filename for term in ['all-levels', 'comprehensive', 'full']):
                return 1.0  # Best for comprehensive lists
            elif not any(term in filename for term in ['theme', 'plugin', 'extension']):
                return 0.9  # Good for general technology lists
            else:
                return 0.3  # Lower for specific component lists
        
        # Match in directory path
        if tech_lower in path_lower:
            return 0.8
        
        # Partial matches
        tech_aliases = self.aliases.get('technology_aliases', {}).get(technology, {}).get('aliases', [])
        for alias in tech_aliases:
            if alias.lower() in path_lower:
                return 0.7
        
        return 0.0
    
    def get_selection_info(self, wordlist_path: str, technology: str) -> str:
        """Get human-readable info about wordlist selection"""
        if not wordlist_path:
            return "No technology-specific wordlist found"

        filename = os.path.basename(wordlist_path)
        wordlist_info = self.catalog['wordlists'].get(
            os.path.relpath(wordlist_path, self.seclists_base_path), {}
        )

        lines = wordlist_info.get('lines', 'unknown')
        size_kb = wordlist_info.get('size_kb', 'unknown')

        # Include fallback level information for transparency
        fallback_level = getattr(self, '_last_fallback_level', 'unknown')
        if fallback_level == 'technology-specific':
            return f"Using {technology} wordlist: {filename} ({lines} lines, {size_kb}KB)"
        else:
            return f"Using {fallback_level} wordlist for {technology}: {filename} ({lines} lines, {size_kb}KB)"
    
    def _generate_catalog_on_demand(self) -> Optional[Dict]:
        """Generate catalog on-demand when not found"""
        from datetime import datetime
        
        catalog = {
            'metadata': {
                'generator_version': '1.0',
                'seclists_path': self.seclists_base_path,
                'generated_at': datetime.now().isoformat(),
                'total_wordlists': 0
            },
            'wordlists': {}
        }
        
        print(f"🔍 Scanning SecLists directory: {self.seclists_base_path}")
        
        # Walk through all .txt files in SecLists
        wordlist_count = 0
        for root, dirs, files in os.walk(self.seclists_base_path):
            for file in sorted(files):
                if file.endswith('.txt') or file.endswith('.fuzz.txt'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.seclists_base_path)
                    
                    # Get file statistics
                    try:
                        stat = os.stat(full_path)
                        size_kb = stat.st_size // 1024
                        
                        # Count lines efficiently (no artificial cap - count real lines)
                        line_count = 0
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, _ in enumerate(f):
                                line_count = i + 1
                        
                        # Categorize wordlist based on path
                        category = self._categorize_wordlist(relative_path)
                        
                        # Extract tags from path/filename
                        tags = self._extract_tags(relative_path.lower())
                        
                        catalog['wordlists'][relative_path] = {
                            'size_kb': size_kb,
                            'lines': line_count,
                            'category': category,
                            'tags': tags
                        }
                        
                        wordlist_count += 1
                        if wordlist_count % 100 == 0:
                            print(f"  📊 Processed {wordlist_count} wordlists...")
                            
                    except Exception as e:
                        print(f"  ⚠️  Skipping {relative_path}: {e}")
                        continue
        
        # Add Jhaddix All.txt if available
        jhaddix_paths = [
            "/usr/share/wordlists/jhaddix/jhaddix-all.txt",  # Linux
            os.path.expanduser("~/tools/wordlists/jhaddix/jhaddix-all.txt")  # macOS
        ]
        
        jhaddix_path = None
        for path in jhaddix_paths:
            if os.path.exists(path):
                jhaddix_path = path
                break
        if jhaddix_path and os.path.exists(jhaddix_path):
            print(f"🏆 Adding Jhaddix All.txt to catalog...")
            try:
                stat = os.stat(jhaddix_path)
                size_kb = stat.st_size // 1024
                
                # Count lines for Jhaddix
                line_count = 0
                with open(jhaddix_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, _ in enumerate(f):
                        line_count = i + 1
                
                # Add to catalog with web category
                catalog['wordlists']['Discovery/Web-Content/jhaddix-all.txt'] = {
                    'size_kb': size_kb,
                    'lines': line_count,
                    'category': 'web',
                    'tags': ['comprehensive', 'discovery', 'jhaddix']
                }
                wordlist_count += 1
                print(f"  ✅ Added Jhaddix All.txt ({line_count:,} lines)")
                
            except Exception as e:
                print(f"  ⚠️  Could not process Jhaddix All.txt: {e}")
        
        # Add OneListForAll wordlists if available
        onelistforall_dirs = [
            "/usr/share/wordlists/onelistforall",  # Linux
            os.path.expanduser("~/tools/wordlists/onelistforall")  # macOS
        ]
        
        onelistforall_dir = None
        for dir_path in onelistforall_dirs:
            if os.path.exists(dir_path):
                onelistforall_dir = dir_path
                break
        if onelistforall_dir and os.path.exists(onelistforall_dir):
            print(f"📚 Adding OneListForAll wordlists to catalog...")
            onelistforall_count = 0
            
            for root, dirs, files in os.walk(onelistforall_dir):
                for file in sorted(files):
                    if file.endswith('.txt') and not file.startswith('.') and 'readme' not in file.lower():
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, onelistforall_dir)
                        
                        try:
                            stat = os.stat(full_path)
                            size_kb = stat.st_size // 1024
                            
                            # Count lines
                            line_count = 0
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                for i, _ in enumerate(f):
                                    line_count = i + 1
                            
                            # Add to catalog with OneListForAll prefix
                            catalog_key = f"OneListForAll/{relative_path}"
                            catalog['wordlists'][catalog_key] = {
                                'size_kb': size_kb,
                                'lines': line_count,
                                'category': 'web',
                                'tags': ['onelistforall', 'fuzzing']
                            }
                            onelistforall_count += 1
                            wordlist_count += 1
                            
                        except Exception as e:
                            print(f"    ⚠️  Skipping {relative_path}: {e}")
                            continue
            
            if onelistforall_count > 0:
                print(f"  ✅ Added {onelistforall_count} OneListForAll wordlists")
        
        catalog['metadata']['total_wordlists'] = wordlist_count
        print(f"✅ Cataloged {wordlist_count} total wordlists")
        
        # Save catalog to first available location
        catalog_paths = [
            os.path.join(os.path.dirname(__file__), 'data', 'unified_wordlists_catalog.yaml'),
            os.path.join(os.path.dirname(__file__), '..', 'data', 'unified_wordlists_catalog.yaml'),
            'unified_wordlists_catalog.yaml'  # Current directory
        ]
        
        for catalog_path in catalog_paths:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(catalog_path), exist_ok=True)
                
                with open(catalog_path, 'w') as f:
                    yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True)
                print(f"💾 Catalog saved to: {catalog_path}")
                break
            except Exception as e:
                print(f"  ⚠️  Could not save to {catalog_path}: {e}")
                continue
        
        return catalog
    
    def _categorize_wordlist(self, path: str) -> str:
        """Categorize wordlist based on its path"""
        path_lower = path.lower()
        
        # Web-related (check first, before username to avoid User-Agent misclassification)
        if ('web' in path_lower or 'http' in path_lower or 'directory' in path_lower or 
            'file' in path_lower or 'user-agent' in path_lower or 'useragent' in path_lower or
            'fuzzing' in path_lower or 'content' in path_lower or 'discovery' in path_lower):
            return 'web'
        # Username/User wordlists (but exclude User-Agent files)
        elif ('username' in path_lower or 
              ('user' in path_lower and 'user-agent' not in path_lower and 'useragent' not in path_lower)):
            return 'usernames'
        elif 'password' in path_lower or 'pass' in path_lower:
            return 'passwords'
        elif 'subdomain' in path_lower or 'dns' in path_lower:
            return 'dns'
        elif 'snmp' in path_lower:
            return 'snmp'
        else:
            return 'other'
    
    def _extract_tags(self, path: str) -> List[str]:
        """Extract technology tags from wordlist path"""
        tags = []
        
        # Common technologies to look for
        tech_keywords = [
            'wordpress', 'wp', 'drupal', 'joomla', 'php', 'asp', 'aspx', 
            'jsp', 'coldfusion', 'perl', 'python', 'rails', 'django',
            'apache', 'nginx', 'iis', 'tomcat', 'jenkins', 'sharepoint'
        ]
        
        for keyword in tech_keywords:
            if keyword in path:
                tags.append(keyword)
        
        return tags
    
    def select_multi_technology_wordlist(self, category: str, detected_technologies: Set[str]) -> List[str]:
        """
        Select multiple wordlists when multiple high-value technologies are detected
        
        Returns:
            List of wordlist paths, prioritized by security importance
        """
        if not detected_technologies or not self.catalog.get('wordlists'):
            return []
        
        # Get all technology matches with security tiers
        tech_matches = self._get_all_technology_matches(detected_technologies)
        
        selected_wordlists = []
        
        # For critical and high-tier technologies, include multiple wordlists
        for tier in ['critical', 'high']:
            tier_techs = [tech for tech, info in sorted(tech_matches.items()) if info['tier'] == tier]
            
            for tech in tier_techs[:2]:  # Max 2 technologies per tier to avoid too many wordlists
                candidates = self._get_candidate_wordlists(tech, category)
                best_wordlist = self._score_and_select_candidates(candidates, tech)
                
                if best_wordlist:
                    full_path = os.path.join(self.seclists_base_path, best_wordlist)
                    if os.path.exists(full_path) and full_path not in selected_wordlists:
                        selected_wordlists.append(full_path)
        
        # If no high-value technologies found, fall back to single best match
        if not selected_wordlists:
            single_wordlist = self.select_wordlist(category, detected_technologies)
            if single_wordlist:
                selected_wordlists.append(single_wordlist)
        
        return selected_wordlists
    
    def _get_all_technology_matches(self, detected_technologies: Set[str]) -> Dict[str, Dict]:
        """Get all matching technologies with their security tier information"""
        if not self.aliases:
            return {}

        tech_aliases = self.aliases.get('technology_aliases', {})
        if not tech_aliases:
            return {}

        # Use centralized security tiers
        security_tiers = self._get_security_tiers()
        
        technology_matches = {}
        
        for tech_key, tech_config in sorted(tech_aliases.items()):
            aliases = tech_config.get('aliases', [])
            
            # Determine security tier
            security_tier = 'unknown'
            for tier, tech_set in sorted(security_tiers.items()):
                if tech_key in tech_set:
                    security_tier = tier
                    break
            
            # Simple string matching for all technologies
            for detected in sorted(detected_technologies):
                for alias in aliases:
                    if alias.lower() in detected.lower() or detected.lower() in alias.lower():
                        technology_matches[tech_key] = {
                            'tier': security_tier,
                            'detected_string': detected,
                            'aliases': aliases
                        }
                        break
                else:
                    continue
                break
        
        return technology_matches
    
    def get_security_analysis(self, detected_technologies: Set[str]) -> Dict[str, any]:
        """
        Provide detailed security analysis of detected technologies
        
        Returns:
            Analysis with security implications and recommendations
        """
        tech_matches = self._get_all_technology_matches(detected_technologies)
        
        analysis = {
            'total_technologies': len(tech_matches),
            'security_tiers': {'critical': [], 'high': [], 'medium': [], 'low': [], 'unknown': []},
            'recommendations': [],
            'risk_level': 'low'
        }
        
        # Categorize technologies by security tier
        for tech, info in sorted(tech_matches.items()):
            tier = info['tier']
            analysis['security_tiers'][tier].append({
                'technology': tech,
                'detected_from': info['detected_string']
            })
        
        # Generate risk assessment and recommendations
        critical_count = len(analysis['security_tiers']['critical'])
        high_count = len(analysis['security_tiers']['high'])
        
        if critical_count > 0:
            analysis['risk_level'] = 'critical'
            analysis['recommendations'].append("🔴 Critical technologies detected - prioritize admin interface testing")
            analysis['recommendations'].append("🔐 Focus on authentication bypass and privilege escalation")
        elif high_count > 0:
            analysis['risk_level'] = 'high'
            analysis['recommendations'].append("🟡 High-value technologies detected - comprehensive enumeration recommended")
            analysis['recommendations'].append("💡 Check for default credentials and misconfigurations")
        elif len(analysis['security_tiers']['medium']) > 0:
            analysis['risk_level'] = 'medium'
            analysis['recommendations'].append("🔵 Development tools detected - look for exposed interfaces")
        else:
            analysis['recommendations'].append("ℹ️ Basic technologies detected - standard enumeration sufficient")
        
        return analysis


# Convenience function for easy integration
def select_smart_wordlist(category: str, detected_technologies: Set[str], seclists_path: str) -> Optional[str]:
    """
    Convenient function for smart wordlist selection
    
    Args:
        category: Wordlist category
        detected_technologies: Set of detected technology strings  
        seclists_path: Path to SecLists installation
        
    Returns:
        Full path to selected wordlist or None
    """
    if not detected_technologies or not seclists_path:
        return None
    
    selector = SmartWordlistSelector(seclists_path)
    return selector.select_wordlist(category, detected_technologies)