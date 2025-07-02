#!/usr/bin/env python3

import os
import re
import random
import string
import requests
import platform
import socket
import tempfile
from ipcrawler.plugins import ServiceScan
from ipcrawler.wordlists import get_wordlist_manager
from ipcrawler.config import config

class EnhancedVhostDiscovery(ServiceScan):
    """
    Enhanced Virtual Host Discovery Plugin
    
    This plugin performs comprehensive vhost/subdomain discovery using multiple techniques:
    1. Standard ffuf-based vhost enumeration
    2. Common subdomain patterns (www, mail, ftp, admin, api, etc.)
    3. Technology-specific subdomains (lms, cms, blog, shop, etc.)
    4. Wildcard detection and filtering
    5. Response analysis for hidden vhosts
    """

    def __init__(self):
        super().__init__()
        self.name = 'Enhanced Virtual Host Discovery'
        self.slug = 'enhanced-vhost-discovery'
        self.tags = ['default', 'safe', 'http', 'long']

    def configure(self):
        self.add_option('hostname', help='The hostname to use as the base host (e.g. example.com) for virtual host enumeration. Default: %(default)s')
        self.add_list_option('wordlist', default=['auto'], help='The wordlist(s) to use when enumerating virtual hosts. Use "auto" for automatic SecLists detection, or specify custom paths. Default: %(default)s')
        self.add_option('threads', default=20, help='The number of threads to use when enumerating virtual hosts. Default: %(default)s')
        self.add_option('timeout', default=10, help='Request timeout in seconds. Default: %(default)s')
        self.add_option('common-only', default=False, help='Only test common subdomains (faster). Default: %(default)s')
        self.match_service_name('^http')
        self.match_service_name('ssl/http')
        self.match_service_name('^https')
        self.match_service_name('^nacn_http$', negative_match=True)

    async def run(self, service):
        hostnames = []
        if self.get_option('hostname'):
            hostnames.append(self.get_option('hostname'))
        if service.target.type == 'hostname' and service.target.address not in hostnames:
            hostnames.append(service.target.address)
        if self.get_global('domain') and self.get_global('domain') not in hostnames:
            hostnames.append(self.get_global('domain'))
        
        # Add already discovered hostnames as base domains for further vhost discovery
        discovered_hostnames = service.target.discovered_hostnames
        for discovered in discovered_hostnames:
            if discovered not in hostnames:
                hostnames.append(discovered)
                service.info(f"🔄 Using previously discovered hostname as base: {discovered}")

        # If no hostnames found but we have an IP target, try to discover hostnames first
        if len(hostnames) == 0 and service.target.type == 'ip':
            # Try reverse DNS lookup for the IP
            try:
                reverse_dns = socket.gethostbyaddr(service.target.address)[0]
                if reverse_dns and reverse_dns != service.target.address:
                    hostnames.append(reverse_dns)
                    service.info(f"🔍 Discovered hostname via reverse DNS: {reverse_dns}")
            except:
                pass

        if len(hostnames) > 0:
            # Get detected technologies for smart subdomain selection
            detected_technologies = set()
            try:
                from ipcrawler.technology_detector import TechnologyDetector
                detector = TechnologyDetector(service.target.scandir)
                detected_technologies = detector.detect_from_scan_results()
                if detected_technologies:
                    service.info(f"🤖 Detected technologies: {', '.join(sorted(detected_technologies))}")
                else:
                    service.info("🤖 No specific technologies detected")
            except Exception as e:
                service.warn(f"Technology detection failed: {e}")

            # Resolve wordlists at runtime
            wordlists = self.get_option('wordlist')
            resolved_wordlists = []
            
            for wordlist in wordlists:
                if wordlist == 'auto':
                    # Auto-detect best available wordlist using Smart Wordlist Selector FIRST
                    try:
                        # PRIORITY 1: Try Smart Wordlist Selector first
                        smart_wordlist_path = None
                        if detected_technologies:
                            try:
                                from ipcrawler.smart_wordlist_selector import SmartWordlistSelector
                                
                                # Get SecLists path from WordlistManager
                                wordlist_manager = get_wordlist_manager()
                                config_data = wordlist_manager.load_config()
                                seclists_path = config_data.get('detected_paths', {}).get('seclists_base')
                                
                                if seclists_path and os.path.exists(seclists_path):
                                    service.info(f"🤖 Using Smart Wordlist Selector with SecLists at: {seclists_path}")
                                    selector = SmartWordlistSelector(seclists_path)
                                    smart_wordlist_path = selector.select_wordlist('vhosts', detected_technologies)
                                    
                                    if smart_wordlist_path and os.path.exists(smart_wordlist_path):
                                        resolved_wordlists.append(smart_wordlist_path)
                                        # Use the actually selected technology, not the first detected one
                                        selected_tech = selector.get_selected_technology() or list(detected_technologies)[0]
                                        selection_info = selector.get_selection_info(smart_wordlist_path, selected_tech)
                                        service.info(f"✅ Smart selection: {selection_info}")
                                        service.info(f"✅ Using technology-specific wordlist: {smart_wordlist_path}")
                                    else:
                                        service.info("🤖 Smart Wordlist Selector found no technology-specific wordlists")
                                        service.info(f"🤖 Technologies detected: {', '.join(detected_technologies)}")
                                        service.info(f"🤖 Catalog available: {bool(selector.catalog)}")
                                        if selector.catalog:
                                            service.info(f"🤖 Catalog wordlists: {len(selector.catalog.get('wordlists', {}))}")
                                else:
                                    service.info("🤖 Smart Wordlist Selector: SecLists path not available")
                            except Exception as e:
                                service.info(f"🤖 Smart Wordlist Selector unavailable: {e}")
                        
                        # PRIORITY 2: Fallback to WordlistManager if Smart Selector didn't find anything
                        if not smart_wordlist_path:
                            service.info("📚 Falling back to WordlistManager (wordlists.toml)")
                            
                            wordlist_manager = get_wordlist_manager()
                            current_size = wordlist_manager.get_wordlist_size()
                            service.info(f"🔍 WordlistManager size: {current_size}")
                            
                            vhost_path = wordlist_manager.get_wordlist_path('vhosts', config.get('data_dir'), current_size, detected_technologies)
                            service.info(f"🔍 WordlistManager resolved path: {vhost_path}")
                            
                            if vhost_path and os.path.exists(vhost_path):
                                resolved_wordlists.append(vhost_path)
                                service.info(f"✅ Using WordlistManager wordlist: {vhost_path}")
                            else:
                                service.error(f'❌ WordlistManager found no wordlist for size "{current_size}". Path attempted: {vhost_path}')
                                
                        # PRIORITY 3: Hard-coded fallbacks if both Smart Selector and WordlistManager failed
                        if not resolved_wordlists:
                            service.info("📦 Trying hard-coded fallback wordlists")
                            if platform.system() == "Darwin":  # macOS
                                service.info(f"💡 Install SecLists: brew install seclists")
                            else:
                                service.info(f"💡 Install SecLists: sudo apt install seclists")
                            service.info(f"💡 Or specify custom: --enhanced-vhost-discovery.wordlist /path/to/wordlist.txt")
                            
                            fallback_paths = [
                                '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
                                '/usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt',
                                '/usr/share/wordlists/dirb/common.txt'
                            ]
                            found_fallback = False
                            for fallback_path in fallback_paths:
                                if os.path.exists(fallback_path):
                                    service.info(f"🔄 Using fallback wordlist: {fallback_path}")
                                    resolved_wordlists.append(fallback_path)
                                    found_fallback = True
                                    break
                            if not found_fallback:
                                service.warn('WordlistManager not available and no SecLists found. Skipping auto wordlist.')
                                continue
                    except Exception as e:
                        service.error(f'❌ WordlistManager error: {e}')
                        service.info("📦 Trying hard-coded fallback wordlists")
                        if platform.system() == "Darwin":  # macOS
                            service.info(f"💡 Install SecLists: brew install seclists")
                        else:
                            service.info(f"💡 Install SecLists: sudo apt install seclists")
                        service.info(f"💡 Or specify custom: --enhanced-vhost-discovery.wordlist /path/to/wordlist.txt")
                        
                        fallback_paths = [
                            '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
                            '/usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt',
                            '/usr/share/wordlists/dirb/common.txt'
                        ]
                        found_fallback = False
                        for fallback_path in fallback_paths:
                            if os.path.exists(fallback_path):
                                service.info(f"🔄 Using fallback wordlist: {fallback_path}")
                                resolved_wordlists.append(fallback_path)
                                found_fallback = True
                                break
                        if not found_fallback:
                            service.warn('WordlistManager not available and no SecLists found. Skipping auto wordlist.')
                            continue
                else:
                    if os.path.exists(wordlist):
                        resolved_wordlists.append(wordlist)
                    else:
                        service.warn(f'Wordlist not found: {wordlist}')

            # Add technology-specific common subdomains
            tech_subdomains = self._get_technology_subdomains(detected_technologies)
            if tech_subdomains:
                # Create a temporary wordlist with technology-specific subdomains
                tech_wordlist = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                for subdomain in tech_subdomains:
                    tech_wordlist.write(f"{subdomain}\n")
                tech_wordlist.close()
                resolved_wordlists.insert(0, tech_wordlist.name)  # Prioritize tech-specific subdomains
                service.info(f"🎯 Added {len(tech_subdomains)} technology-specific subdomains")

            # Always add common subdomains wordlist
            common_subdomains = self._get_common_subdomains()
            common_wordlist = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            for subdomain in common_subdomains:
                common_wordlist.write(f"{subdomain}\n")
            common_wordlist.close()
            resolved_wordlists.insert(0, common_wordlist.name)  # Prioritize common subdomains
            service.info(f"🎯 Added {len(common_subdomains)} common subdomains")

            for wordlist in resolved_wordlists:
                name = os.path.splitext(os.path.basename(wordlist))[0]
                for hostname in hostnames:
                    try:
                        # Wildcard detection
                        wildcard = requests.get(
                            ('https' if service.secure else 'http') + '://' + service.target.address + ':' + str(service.port) + '/',
                            headers={'Host': ''.join(random.choice(string.ascii_letters) for _ in range(20)) + '.' + hostname},
                            verify=False,
                            allow_redirects=False,
                            timeout=self.get_option('timeout')
                        )
                        wildcard_size = str(len(wildcard.content))
                        wildcard_status = str(wildcard.status_code)
                    except requests.exceptions.RequestException as e:
                        service.error(f"Wildcard request failed for {hostname}: {e}", verbosity=1)
                        continue

                    # Build ffuf command with enhanced options
                    verbose_level = self.get_global('verbose', 0)
                    if verbose_level is None:
                        verbose_level = 0
                    ffuf_cmd = ('ffuf -u {http_scheme}://' + hostname + ':{port}/ -t ' + str(self.get_option('threads')) +
                        ' -w ' + wordlist + ' -H "Host: FUZZ.' + hostname + '" -mc all -fs ' + wildcard_size +
                        ' -fc ' + wildcard_status + ' -r -noninteractive')
                    
                    # Add verbosity options
                    if verbose_level == 0:
                        ffuf_cmd += ' -s'  # Silent mode
                    elif verbose_level >= 2:
                        ffuf_cmd += ' -v'  # Verbose mode
                    
                    # Add timeout
                    ffuf_cmd += f' -timeout {self.get_option("timeout")}'
                    
                    ffuf_cmd += (' -o "{scandir}/{protocol}_{port}_{http_scheme}_' + hostname + '_enhanced_vhosts_' + name + '.txt" -of csv')
                    
                    # Show progress info
                    with open(wordlist, 'r') as f:
                        total_lines = sum(1 for _ in f)
                    service.info(f"🔍 Enhanced vhost enumeration: {total_lines} entries on {hostname}...")
                    
                    # Enhanced pattern matching for virtual host discoveries
                    self.add_pattern(r'(\S+\.' + hostname.replace('.', r'\.') + r')', description='Enhanced Virtual Host: {match1} - potential service/subdomain')
                    
                    await service.execute(ffuf_cmd, outfile='{protocol}_{port}_{http_scheme}_' + hostname + '_enhanced_vhosts_' + name + '.txt')
                    
                    # Cleanup temporary wordlists
                    if 'temp' in wordlist and os.path.exists(wordlist):
                        try:
                            os.unlink(wordlist)
                        except:
                            pass
        else:
            service.info('No hostname available for enhanced vhost enumeration. Use --enhanced-vhost-discovery.hostname=example.com')

    def _get_common_subdomains(self):
        """Get list of common subdomains to test"""
        return [
            'www', 'mail', 'ftp', 'admin', 'api', 'blog', 'shop', 'store',
            'dev', 'test', 'staging', 'demo', 'beta', 'alpha', 'preview',
            'cms', 'lms', 'portal', 'dashboard', 'panel', 'control',
            'secure', 'ssl', 'vpn', 'remote', 'access', 'login',
            'support', 'help', 'docs', 'wiki', 'forum', 'community',
            'news', 'media', 'images', 'static', 'cdn', 'assets',
            'mobile', 'm', 'app', 'apps', 'service', 'services',
            'old', 'new', 'v1', 'v2', 'backup', 'archive'
        ]

    def _get_technology_subdomains(self, detected_technologies):
        """Get technology-specific subdomains based on detected technologies"""
        tech_subdomains = set()
        
        # LMS-specific subdomains
        if any(lms in detected_technologies for lms in ['moodle', 'chamilo', 'canvas', 'blackboard']):
            tech_subdomains.update([
                'lms', 'learning', 'courses', 'education', 'elearning',
                'student', 'teacher', 'instructor', 'class', 'classroom',
                'training', 'academy', 'school', 'university', 'college'
            ])
        
        # CMS-specific subdomains
        if any(cms in detected_technologies for cms in ['wordpress', 'drupal', 'joomla']):
            tech_subdomains.update([
                'cms', 'content', 'blog', 'news', 'articles', 'posts',
                'wp', 'wordpress', 'drupal', 'joomla'
            ])
        
        # E-commerce subdomains
        if any(shop in detected_technologies for shop in ['magento', 'shopify', 'woocommerce']):
            tech_subdomains.update([
                'shop', 'store', 'cart', 'checkout', 'payment', 'orders',
                'products', 'catalog', 'inventory', 'ecommerce'
            ])
        
        # Development/Admin subdomains
        if any(dev in detected_technologies for dev in ['jenkins', 'gitlab', 'github']):
            tech_subdomains.update([
                'git', 'gitlab', 'github', 'jenkins', 'ci', 'cd',
                'build', 'deploy', 'repo', 'repository', 'code'
            ])
        
        return list(tech_subdomains)
