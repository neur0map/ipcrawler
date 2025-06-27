"""
Centralized Wordlist Management for ipcrawler

This module provides intelligent wordlist path detection and management,
allowing users to use auto-detected SecLists paths or custom wordlists.
"""

import os
import toml
from pathlib import Path
from typing import Dict, List, Optional, Union

class WordlistManager:
    """Centralized wordlist path management with auto-detection and user overrides"""
    
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.wordlists_config_path = os.path.join(config_dir, 'wordlists.toml')
        self._config = None
        self._cli_overrides = {}
        self._wordlist_size = 'default'  # Can be 'fast', 'default', or 'comprehensive'
        
        # Wordlist categories with different sizes for various scan scenarios
        self.categories = {
            'usernames': {
                'fast': 'Usernames/top-usernames-shortlist.txt',
                'default': 'Usernames/top-usernames-shortlist.txt',
                'comprehensive': 'Usernames/Names/names.txt'
            },
            'passwords': {
                'fast': 'Passwords/Common-Credentials/10-million-password-list-top-100.txt',
                'default': 'Passwords/Common-Credentials/darkweb2017_top-100.txt',
                'comprehensive': 'Passwords/Common-Credentials/10-million-password-list-top-1000.txt'
            },
            'web_directories': {
                'fast': 'Discovery/Web-Content/common.txt',
                'default': 'Discovery/Web-Content/common.txt',
                'comprehensive': 'Discovery/Web-Content/directory-list-2.3-small.txt'
            },
            'web_files': {
                'fast': 'Discovery/Web-Content/common.txt',
                'default': 'Discovery/Web-Content/common.txt',
                'comprehensive': 'Discovery/Web-Content/raft-medium-files.txt'
            },
            'subdomains': {
                'fast': 'Discovery/DNS/subdomains-top1million-5000.txt',
                'default': 'Discovery/DNS/subdomains-top1million-20000.txt',
                'comprehensive': 'Discovery/DNS/subdomains-top1million-110000.txt'
            },
            'snmp_communities': {
                'fast': 'Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt',
                'default': 'Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt',
                'comprehensive': 'Discovery/SNMP/common-snmp-community-strings.txt'
            },
            'dns_servers': {
                'fast': 'Discovery/DNS/dns-Jhaddix.txt',
                'default': 'Discovery/DNS/dns-Jhaddix.txt',
                'comprehensive': 'Discovery/DNS/dns-Jhaddix.txt'
            },
            'vhosts': {
                'fast': 'Discovery/DNS/subdomains-top1million-5000.txt',
                'default': 'Discovery/DNS/subdomains-top1million-20000.txt',
                'comprehensive': 'Discovery/DNS/subdomains-top1million-110000.txt'
            }
        }
        
        # Fallback to old format for backward compatibility
        self.categories_legacy = {
            'usernames': 'Usernames/top-usernames-shortlist.txt',
            'passwords': 'Passwords/Common-Credentials/darkweb2017_top-100.txt',
            'web_directories': 'Discovery/Web-Content/directory-list-2.3-medium.txt',
            'web_files': 'Discovery/Web-Content/common.txt',
            'subdomains': 'Discovery/DNS/subdomains-top1million-110000.txt',
            'snmp_communities': 'Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt',
            'dns_servers': 'Discovery/DNS/dns-Jhaddix.txt',
            'vhosts': 'Discovery/DNS/subdomains-top1million-20000.txt'
        }
        
        # Possible SecLists installation paths (ordered by likelihood)
        self.seclists_search_paths = [
            '/usr/share/seclists',
            '/usr/share/SecLists', 
            '/opt/SecLists',
            '/opt/seclists',
            '/usr/share/wordlists/seclists',
            '/home/kali/SecLists',  # Common Kali location
            os.path.expanduser('~/SecLists'),  # User home directory
            os.path.expanduser('~/tools/SecLists')  # Common pentesting setup
        ]
        
        # No built-in fallback wordlists - WordlistManager should fail if no proper wordlists found
        self.builtin_fallbacks = {}
    
    def load_config(self) -> Dict:
        """Load or create wordlists configuration"""
        if self._config is None:
            if os.path.exists(self.wordlists_config_path):
                try:
                    with open(self.wordlists_config_path, 'r') as f:
                        self._config = toml.load(f)
                except Exception as e:
                    print(f"Warning: Could not load wordlists config: {e}")
                    self._config = self._create_default_config()
            else:
                self._config = self._create_default_config()
                self._save_config()
        
        return self._config
    
    def _create_default_config(self) -> Dict:
        """Create default wordlists configuration"""
        return {
            'mode': {
                'type': 'auto',  # 'auto' or 'custom'
                'auto_update': True,  # Update detected paths on each run
                'last_detection': None,
                'size': 'default'  # 'fast', 'default', or 'comprehensive'
            },
            'smart_wordlists': {
                'enabled': True,  # Enable Smart Wordlist Selector by default
                'comment': 'Smart Wordlist Selector uses technology detection to choose optimal wordlists'
            },
            'detected_paths': {
                'seclists_base': None,
                'comment': 'Auto-generated paths - do not edit manually'
            },
            'custom_paths': {
                'comment': 'Add your custom wordlist paths here',
                'examples': {
                    '# usernames': '/path/to/custom/usernames.txt',
                    '# passwords': '/path/to/custom/passwords.txt',
                    '# web_directories': '/path/to/custom/web-dirs.txt'
                }
            },
            # No built-in wordlists - removed to force use of proper SecLists installation
            'sizes': {
                'comment': 'Wordlist size configurations for different scan scenarios',
                'fast': {
                    'description': 'Small wordlists for quick scans (5-15 minutes)',
                    'estimated_time': '5-15 minutes per service'
                },
                'default': {
                    'description': 'Medium wordlists for standard scans (15-45 minutes)',
                    'estimated_time': '15-45 minutes per service'
                },
                'comprehensive': {
                    'description': 'Large wordlists for thorough scans (30-120 minutes)',
                    'estimated_time': '30-120 minutes per service'
                }
            }
        }
    
    def _save_config(self):
        """Save configuration to file"""
        os.makedirs(self.config_dir, exist_ok=True)
        try:
            with open(self.wordlists_config_path, 'w') as f:
                toml.dump(self._config, f)
            
            # Create user shortcut for easy access
            self._create_user_shortcut()
        except Exception as e:
            print(f"Warning: Could not save wordlists config: {e}")
    
    def _create_user_shortcut(self):
        """Create a symlink for easy user access to wordlists configuration"""
        try:
            # Create shortcut in the data directory, not source directory
            from ipcrawler.config import config
            data_wordlists_dir = os.path.join(config['data_dir'], 'wordlists')
            
            # Create wordlists directory if it doesn't exist
            os.makedirs(data_wordlists_dir, exist_ok=True)
            
            shortcut_path = os.path.join(data_wordlists_dir, 'wordlists.toml')
            
            # Only create if it doesn't exist and the source file exists
            if os.path.exists(self.wordlists_config_path) and not os.path.exists(shortcut_path):
                try:
                    # Create cross-platform symlink to the actual config location
                    os.symlink(self.wordlists_config_path, shortcut_path)
                    print(f"📝 Wordlist config shortcut created: {shortcut_path}")
                    print(f"💡 Points to: {self.wordlists_config_path}")
                    print(f"💡 You can access your wordlist configuration at the shortcut location")
                except (OSError, FileExistsError):
                    # Symlink creation can fail on some systems, that's okay
                    pass
        except Exception:
            # Don't let shortcut creation break anything
            pass
    
    def detect_seclists_installation(self) -> Optional[str]:
        """Detect SecLists installation path"""
        for path in self.seclists_search_paths:
            if os.path.isdir(path):
                # Try different SecLists variants (GitHub vs package versions)
                test_scenarios = [
                    # GitHub version structure
                    [
                        'Usernames/top-usernames-shortlist.txt',
                        'Passwords/Common-Credentials/darkweb2017_top-100.txt'
                    ],
                    # Kali package version structure
                    [
                        'Usernames/top-usernames-shortlist.txt',
                        'Passwords/darkweb2017-top100.txt'
                    ],
                    # Alternative structure - just check usernames exists
                    [
                        'Usernames/top-usernames-shortlist.txt'
                    ]
                ]
                
                for test_files in test_scenarios:
                    if all(os.path.exists(os.path.join(path, f)) for f in test_files):
                        return path
        
        return None
    
    def update_detected_paths(self) -> bool:
        """Update detected paths in configuration"""
        config = self.load_config()
        
        # Skip if auto-update is disabled
        if not config.get('mode', {}).get('auto_update', True):
            return False
        
        seclists_path = self.detect_seclists_installation()
        
        if seclists_path:
            config['detected_paths']['seclists_base'] = seclists_path
            config['mode']['last_detection'] = 'success'
            
            # Add individual category paths for all sizes, trying multiple variants
            for category, size_paths in self.categories.items():
                config['detected_paths'][category] = {}
                
                for size, relative_path in size_paths.items():
                    # Try the specified path first
                    full_path = os.path.join(seclists_path, relative_path)
                    if os.path.exists(full_path):
                        config['detected_paths'][category][size] = full_path
                        continue
                    
                    # For passwords, try alternative paths for different package versions
                    if category == 'passwords' and size == 'default':
                        alternative_paths = [
                            'Passwords/darkweb2017-top100.txt',  # Kali package version
                            'Passwords/Common-Credentials/darkweb2017-top100.txt',  # Alternative naming
                            'Passwords/darkweb2017_top-100.txt',  # Another variant
                            'Passwords/Common-Credentials/10k-most-common.txt',  # Fallback
                            'Passwords/Common-Credentials/best110.txt'  # Another fallback
                        ]
                        for alt_path in alternative_paths:
                            alt_full_path = os.path.join(seclists_path, alt_path)
                            if os.path.exists(alt_full_path):
                                config['detected_paths'][category][size] = alt_full_path
                                break
                    
                    # For missing files, try to find fallbacks within the same category
                    if size not in config['detected_paths'][category]:
                        # Try using default size as fallback
                        if size != 'default' and 'default' in size_paths:
                            fallback_path = os.path.join(seclists_path, size_paths['default'])
                            if os.path.exists(fallback_path):
                                config['detected_paths'][category][size] = fallback_path
                        
                        # If still missing, try other sizes as fallbacks
                        if size not in config['detected_paths'][category]:
                            for fallback_size in ['default', 'fast', 'comprehensive']:
                                if fallback_size != size and fallback_size in size_paths:
                                    fallback_path = os.path.join(seclists_path, size_paths[fallback_size])
                                    if os.path.exists(fallback_path):
                                        config['detected_paths'][category][size] = fallback_path
                                        break
            
            self._config = config
            self._save_config()
            return True
        else:
            config['mode']['last_detection'] = 'failed'
            self._config = config
            self._save_config()
            return False
    
    def get_wordlist_path(self, category: str, data_dir: str = None, size: str = None, detected_technologies: set = None) -> Optional[str]:
        """Get wordlist path for a category with fallback hierarchy - Smart Wordlist Selector prioritized"""
        config = self.load_config()
        
        # Determine the wordlist size to use
        if size is None:
            size = self._wordlist_size
        if size is None:
            size = config.get('mode', {}).get('size', 'default')
        
        # 1. CLI override has highest priority
        if category in self._cli_overrides:
            path = self._cli_overrides[category]
            if os.path.exists(path):
                print(f"🎯 Using CLI override wordlist for {category}: {os.path.basename(path)}")
                return path
            else:
                print(f"Warning: CLI override path for {category} does not exist: {path}")
        
        # 2. Custom paths from config file
        custom_paths = config.get('custom_paths', {})
        if category in custom_paths and custom_paths[category]:
            path = custom_paths[category]
            if os.path.exists(path):
                print(f"🎯 Using custom wordlist for {category}: {os.path.basename(path)}")
                return path
            else:
                print(f"Warning: Custom path for {category} does not exist: {path}")
        
        # 3. PRIORITY: Smart wordlist selection (if enabled and technologies detected)
        smart_path = self._get_smart_wordlist_path(category, detected_technologies)
        if smart_path:
            print(f"🤖 Smart Wordlist Selector: Technology-based selection active")
            return smart_path
        
        # Smart wordlist selector enabled but no technologies detected
        if self._is_smart_wordlists_enabled() and detected_technologies is not None:
            if not detected_technologies:
                print(f"🤖 Smart Wordlist Selector: No technologies detected, falling back to standard wordlists")
            else:
                print(f"🤖 Smart Wordlist Selector: No technology-specific wordlists found, falling back to standard wordlists")
        
        # 4. FALLBACK: Auto-detected SecLists paths (standard wordlist selection)
        if config.get('mode', {}).get('type') == 'auto':
            print(f"📁 Fallback: Using standard wordlist selection from SecLists")
            detected_paths = config.get('detected_paths', {})
            if category in detected_paths:
                # Try the requested size first
                if isinstance(detected_paths[category], dict) and size in detected_paths[category]:
                    path = detected_paths[category][size]
                    if os.path.exists(path):
                        return path
                
                # Fallback to default size if requested size not available
                if isinstance(detected_paths[category], dict) and 'default' in detected_paths[category]:
                    path = detected_paths[category]['default']
                    if os.path.exists(path):
                        return path
                
                # Try any available size as fallback
                if isinstance(detected_paths[category], dict):
                    for fallback_size in ['default', 'fast', 'comprehensive']:
                        if fallback_size in detected_paths[category]:
                            path = detected_paths[category][fallback_size]
                            if os.path.exists(path):
                                return path
                
                # Legacy format support (single path instead of size dict)
                elif isinstance(detected_paths[category], str):
                    path = detected_paths[category]
                    if os.path.exists(path):
                        return path
        
        # 5. FINAL FALLBACK: Legacy hardcoded paths (for backward compatibility)
        if category in self.categories_legacy:
            print(f"⚠️  Final fallback: Using legacy hardcoded wordlist paths")
            legacy_path = '/usr/share/seclists/' + self.categories_legacy[category]
            if os.path.exists(legacy_path):
                return legacy_path
        
        # No wordlists found
        print(f"❌ No wordlist found for category '{category}' - ensure SecLists is installed and configured")
        return None
    
    def set_cli_override(self, category: str, path: str):
        """Set CLI override for a wordlist category"""
        self._cli_overrides[category] = path
    
    def set_wordlist_size(self, size: str):
        """Set the global wordlist size preference"""
        if size in ['fast', 'default', 'comprehensive']:
            self._wordlist_size = size
            # Also update the config file
            config = self.load_config()
            config['mode']['size'] = size
            self._config = config
            self._save_config()
        else:
            raise ValueError(f"Invalid wordlist size: {size}. Must be 'fast', 'default', or 'comprehensive'")
    
    def get_wordlist_size(self) -> str:
        """Get the current wordlist size preference"""
        config = self.load_config()
        return self._wordlist_size or config.get('mode', {}).get('size', 'default')
    
    def get_available_categories(self) -> List[str]:
        """Get list of available wordlist categories"""
        return list(self.categories.keys())
    
    def validate_wordlist_path(self, path: str) -> bool:
        """Validate that a wordlist path exists and is readable"""
        if not path:
            return False
        
        if not os.path.exists(path):
            return False
        
        if not os.path.isfile(path):
            return False
        
        try:
            with open(path, 'r') as f:
                f.readline()  # Try to read first line
            return True
        except:
            return False
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status of wordlist configuration"""
        config = self.load_config()
        report = {
            'mode': config.get('mode', {}),
            'seclists_detected': bool(config.get('detected_paths', {}).get('seclists_base')),
            'categories': {}
        }
        
        for category in self.categories:
            path = self.get_wordlist_path(category)
            report['categories'][category] = {
                'path': path,
                'exists': self.validate_wordlist_path(path) if path else False,
                'source': self._get_path_source(category, path)
            }
        
        return report
    
    def _get_path_source(self, category: str, path: Optional[str]) -> str:
        """Determine the source of a wordlist path"""
        if not path:
            return 'missing'
        
        if category in self._cli_overrides:
            return 'cli_override'
        
        config = self.load_config()
        custom_paths = config.get('custom_paths', {})
        if category in custom_paths and custom_paths[category] == path:
            return 'custom_config'
        
        detected_paths = config.get('detected_paths', {})
        if category in detected_paths and detected_paths[category] == path:
            return 'auto_detected'
        
        if 'wordlists' in path:  # Built-in wordlists
            return 'builtin'
        
        return 'legacy'
    
    def _get_smart_wordlist_path(self, category: str, detected_technologies: set = None) -> Optional[str]:
        """Get smart wordlist path based on detected technologies"""
        # Check if smart wordlists are enabled
        if not self._is_smart_wordlists_enabled():
            return None
        
        # Need detected technologies to proceed
        if not detected_technologies:
            return None
        
        # Get SecLists base path
        config = self.load_config()
        seclists_base = config.get('detected_paths', {}).get('seclists_base')
        if not seclists_base:
            print(f"🤖 Smart Wordlist Selector: SecLists base path not configured")
            return None
        
        try:
            # Import here to avoid dependency issues if rapidfuzz not installed
            from .smart_wordlist_selector import SmartWordlistSelector
            
            # Create selector and get smart wordlist
            selector = SmartWordlistSelector(seclists_base)
            smart_path = selector.select_wordlist(category, detected_technologies)
            
            if smart_path and os.path.exists(smart_path):
                # Log the selection for user visibility
                selection_info = selector.get_selection_info(smart_path, list(detected_technologies)[0])
                print(f"🎯 {selection_info}")
                return smart_path
            else:
                print(f"🤖 Smart Wordlist Selector: No technology-specific wordlist found for {category} with technologies: {', '.join(detected_technologies)}")
                
        except ImportError:
            # Smart wordlist selector not available
            print(f"🤖 Smart Wordlist Selector: Module not available (missing rapidfuzz dependency)")
        except Exception as e:
            # Don't let smart wordlist errors break normal operation
            print(f"🤖 Smart Wordlist Selector: Error occurred - {e}")
            if os.environ.get('IPCRAWLER_DEBUG'):
                import traceback
                traceback.print_exc()
        
        return None
    
    def _is_smart_wordlists_enabled(self) -> bool:
        """Check if smart wordlists are enabled via environment variable or config (defaults to enabled)"""
        # Environment variable takes precedence for backwards compatibility
        env_enabled = os.environ.get('IPCRAWLER_SMART_WORDLISTS', '').lower()
        if env_enabled in ['1', 'true', 'yes', 'on']:
            return True
        elif env_enabled in ['0', 'false', 'no', 'off']:
            return False
        
        # Check global config system (integrated with main ipcrawler config)
        try:
            from .config import config as global_config
            # Default to True - Smart wordlist selector should be enabled by default
            return global_config.get('smart_wordlists', True)
        except ImportError:
            # Fallback to legacy config file method
            config = self.load_config()
            # Default to True - Smart wordlist selector should be enabled by default
            return config.get('smart_wordlists', {}).get('enabled', True)
    
    def get_smart_wordlist_path(self, category: str, detected_technologies: set = None, size: str = None) -> Optional[str]:
        """Public method for smart wordlist selection with fallback"""
        # Try smart selection first
        smart_path = self._get_smart_wordlist_path(category, detected_technologies)
        if smart_path:
            return smart_path
        
        # Fallback to standard selection
        return self.get_wordlist_path(category, size=size)

# Global instance - will be initialized by main.py
wordlist_manager: Optional[WordlistManager] = None

def get_wordlist_manager() -> WordlistManager:
    """Get the global wordlist manager instance"""
    if wordlist_manager is None:
        raise RuntimeError("WordlistManager not initialized. Call init_wordlist_manager() first.")
    return wordlist_manager

def init_wordlist_manager(config_dir: str) -> WordlistManager:
    """Initialize the global wordlist manager"""
    global wordlist_manager
    wordlist_manager = WordlistManager(config_dir)
    return wordlist_manager