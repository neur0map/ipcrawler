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
            os.path.join(os.path.dirname(__file__), 'data', 'seclists_catalog.yaml'),
            os.path.join(os.path.dirname(__file__), '..', 'data', 'seclists_catalog.yaml'),
            'seclists_catalog.yaml'  # Current directory
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
        print("⚠️  No SecLists catalog found for smart wordlist selection.")
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
            category: Wordlist category (e.g., 'web_directories', 'web_files')
            detected_technologies: Set of detected technology strings
            
        Returns:
            Full path to selected wordlist, or None if no good match found
        """
        if not detected_technologies or not self.catalog.get('wordlists'):
            return None
        
        # Find best technology match using alias mapping
        best_tech = self._find_best_technology_match(detected_technologies)
        if not best_tech:
            return None
        
        # Get candidate wordlists for this technology
        candidates = self._get_candidate_wordlists(best_tech, category)
        if not candidates:
            return None
        
        # Score and select best candidate
        best_wordlist = self._score_and_select_candidates(candidates, best_tech)
        if not best_wordlist:
            return None
        
        # Return full path
        full_path = os.path.join(self.seclists_base_path, best_wordlist)
        return full_path if os.path.exists(full_path) else None
    
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
        
        # Only return if we have a reasonable confidence
        return best_tech if best_info['score'] > 0.6 else None
    
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
        """Get candidate wordlists for technology and category"""
        candidates = []
        
        # Get wordlists that contain the technology name in their path/filename
        if not self.catalog or 'wordlists' not in self.catalog:
            return candidates
        
        for wordlist_path, wordlist_info in sorted(self.catalog['wordlists'].items()):
            path_lower = wordlist_path.lower()
            
            # Check if wordlist is relevant to this technology
            if technology in path_lower or any(tag == technology for tag in wordlist_info.get('tags', [])):
                # Check if wordlist is appropriate for the category
                if self._is_appropriate_category(wordlist_info, category):
                    candidates.append((wordlist_path, wordlist_info))
        
        return candidates
    
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
        
        if scored_candidates and scored_candidates[0][0] > 0.3:  # Minimum score threshold
            return scored_candidates[0][1]
        
        return None
    
    def _calculate_size_score(self, wordlist_path: str, lines: int) -> float:
        """Calculate size score - prefer comprehensive wordlists for directory enumeration"""
        path_lower = wordlist_path.lower()
        
        # For directory/web enumeration, we want comprehensive but reasonable wordlists
        if any(term in path_lower for term in ['web-content', 'discovery', 'directory', 'file']):
            # Penalize tiny wordlists heavily for directory enumeration
            if lines < 100:
                return -0.5  # Heavy penalty for tiny lists like joomla-themes.fuzz.txt (30 lines)
            elif lines < 1000:
                return 0.0   # Neutral for small lists
            elif lines < 10000:
                return 0.3   # Good for medium lists
            elif lines < 20000:
                return 0.5   # Best for comprehensive lists (sweet spot)
            else:
                return -0.3  # Penalty for massive wordlists (>20K lines) - too slow
        
        # For other categories (usernames, passwords), prefer smaller targeted lists
        else:
            if lines > 50000:
                return -0.2  # Penalty for huge lists
            elif lines > 10000:
                return 0.0   # Neutral for large lists
            elif lines > 1000:
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
        
        return f"Using {technology} wordlist: {filename} ({lines} lines, {size_kb}KB)"
    
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
                        
                        # Count lines efficiently (limit to avoid hanging on huge files)
                        line_count = 0
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, _ in enumerate(f):
                                if i > 500000:  # Cap at 500k lines for performance
                                    line_count = f">{i}"
                                    break
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
        
        catalog['metadata']['total_wordlists'] = wordlist_count
        print(f"✅ Cataloged {wordlist_count} wordlists")
        
        # Save catalog to first available location
        catalog_paths = [
            os.path.join(os.path.dirname(__file__), 'data', 'seclists_catalog.yaml'),
            os.path.join(os.path.dirname(__file__), '..', 'data', 'seclists_catalog.yaml'),
            'seclists_catalog.yaml'  # Current directory
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
        
        if 'web' in path_lower or 'http' in path_lower or 'directory' in path_lower or 'file' in path_lower:
            return 'web'
        elif 'username' in path_lower or 'user' in path_lower:
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