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
        
        # Wordlist categories and their SecLists relative paths
        self.categories = {
            'usernames': 'Usernames/top-usernames-shortlist.txt',
            'passwords': 'Passwords/darkweb2017-top100.txt',
            'web_directories': 'Discovery/Web-Content/directory-list-2.3-medium.txt',
            'web_files': 'Discovery/Web-Content/common.txt',
            'subdomains': 'Discovery/DNS/subdomains-top1million-110000.txt',
            'snmp_communities': 'Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt',
            'dns_servers': 'Discovery/DNS/dns-Jhaddix.txt',
            'vhosts': 'Discovery/Web-Content/virtual-host-scanning.txt'
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
        
        # Built-in fallback wordlists (relative to ipcrawler data directory)
        self.builtin_fallbacks = {
            'web_directories': 'wordlists/dirbuster.txt',
            'web_files': 'wordlists/dirbuster.txt'
        }
    
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
                'last_detection': None
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
            'builtin_paths': {
                'comment': 'Built-in wordlists shipped with ipcrawler',
                'data_dir': None  # Will be populated at runtime
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
            # Find the wordlists directory relative to this file
            import inspect
            current_file = inspect.getfile(inspect.currentframe())
            ipcrawler_dir = os.path.dirname(current_file)
            wordlists_dir = os.path.join(ipcrawler_dir, 'wordlists')
            
            # Create wordlists directory if it doesn't exist
            os.makedirs(wordlists_dir, exist_ok=True)
            
            shortcut_path = os.path.join(wordlists_dir, 'wordlists.toml')
            
            # Only create if it doesn't exist and the source file exists
            if os.path.exists(self.wordlists_config_path) and not os.path.exists(shortcut_path):
                try:
                    # Create cross-platform symlink to the actual config location
                    os.symlink(self.wordlists_config_path, shortcut_path)
                    print(f"📝 Wordlist config shortcut created: {shortcut_path}")
                    print(f"💡 Points to: {self.wordlists_config_path}")
                    print(f"💡 You can now easily access your wordlist configuration by navigating to the ipcrawler/wordlists/ directory")
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
                # Verify it's actually SecLists by checking for key files
                test_files = [
                    'Usernames/top-usernames-shortlist.txt',
                    'Passwords/darkweb2017-top100.txt'
                ]
                
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
            
            # Add individual category paths
            for category, relative_path in self.categories.items():
                full_path = os.path.join(seclists_path, relative_path)
                if os.path.exists(full_path):
                    config['detected_paths'][category] = full_path
            
            self._config = config
            self._save_config()
            return True
        else:
            config['mode']['last_detection'] = 'failed'
            self._config = config
            self._save_config()
            return False
    
    def get_wordlist_path(self, category: str, data_dir: str = None) -> Optional[str]:
        """Get wordlist path for a category with fallback hierarchy"""
        config = self.load_config()
        
        # 1. CLI override has highest priority
        if category in self._cli_overrides:
            path = self._cli_overrides[category]
            if os.path.exists(path):
                return path
            else:
                print(f"Warning: CLI override path for {category} does not exist: {path}")
        
        # 2. Custom paths from config file
        custom_paths = config.get('custom_paths', {})
        if category in custom_paths and custom_paths[category]:
            path = custom_paths[category]
            if os.path.exists(path):
                return path
            else:
                print(f"Warning: Custom path for {category} does not exist: {path}")
        
        # 3. Auto-detected SecLists paths
        if config.get('mode', {}).get('type') == 'auto':
            detected_paths = config.get('detected_paths', {})
            if category in detected_paths and detected_paths[category]:
                path = detected_paths[category]
                if os.path.exists(path):
                    return path
        
        # 4. Built-in fallbacks
        if category in self.builtin_fallbacks and data_dir:
            path = os.path.join(data_dir, self.builtin_fallbacks[category])
            if os.path.exists(path):
                return path
        
        # 5. Legacy hardcoded paths (for backward compatibility)
        legacy_paths = {
            'usernames': '/usr/share/seclists/Usernames/top-usernames-shortlist.txt',
            'passwords': '/usr/share/seclists/Passwords/darkweb2017-top100.txt',
            'subdomains': '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
            'snmp_communities': '/usr/share/seclists/Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt'
        }
        
        if category in legacy_paths and os.path.exists(legacy_paths[category]):
            return legacy_paths[category]
        
        return None
    
    def set_cli_override(self, category: str, path: str):
        """Set CLI override for a wordlist category"""
        self._cli_overrides[category] = path
    
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