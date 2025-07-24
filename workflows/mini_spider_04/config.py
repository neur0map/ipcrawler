"""Configuration management for Mini Spider workflow"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from utils.debug import debug_print


@dataclass
class HakrawlerConfig:
    """Configuration for hakrawler tool"""
    timeout: int = 30
    depth: int = 3
    max_pages: int = 100
    include_subdomains: bool = True
    include_urls: bool = True
    include_forms: bool = True
    include_wayback: bool = False  # Disabled by default to prevent infinite loops
    include_commonspeak: bool = False  # Disabled by default
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    delay: int = 1  # Delay between requests in seconds
    threads: int = 5  # Number of concurrent threads


@dataclass
class CustomCrawlerConfig:
    """Configuration for custom path sniffer"""
    max_concurrent: int = 10
    request_timeout: int = 15
    max_redirects: int = 3
    user_agents: List[str] = None
    custom_headers: Dict[str, str] = None
    follow_redirects: bool = True
    verify_ssl: bool = False
    max_content_length: int = 10485760  # 10MB limit
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            ]
        
        if self.custom_headers is None:
            self.custom_headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }


@dataclass
class SpiderConfig:
    """Main configuration for Mini Spider workflow"""
    # Global limits
    max_total_urls: int = 1000
    max_crawl_time: int = 300  # 5 minutes total
    max_concurrent_crawls: int = 5
    
    # URL filtering
    exclude_extensions: List[str] = None
    exclude_patterns: List[str] = None
    include_patterns: List[str] = None
    
    # Discovery settings
    enable_custom_crawler: bool = True
    enable_hakrawler: bool = True
    prefer_parallel_execution: bool = True
    
    # Result processing
    categorize_results: bool = True
    extract_interesting_paths: bool = True
    save_to_workspace: bool = True
    
    # Tool configurations
    hakrawler: HakrawlerConfig = None
    custom_crawler: CustomCrawlerConfig = None
    
    def __post_init__(self):
        if self.exclude_extensions is None:
            self.exclude_extensions = [
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
                '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.zip', '.rar', '.tar', '.gz', '.7z',
                '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv'
            ]
        
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                r'logout', r'signout', r'sign-out', r'exit',
                r'delete', r'remove', r'drop',
                r'\.jpg$', r'\.png$', r'\.gif$', r'\.css$', r'\.js$',
                r'javascript:', r'mailto:', r'tel:', r'ftp:'
            ]
        
        if self.include_patterns is None:
            self.include_patterns = [
                r'/admin', r'/api', r'/v\d+/', r'/app',
                r'/dashboard', r'/portal', r'/console',
                r'/config', r'/settings', r'/manage',
                r'\.php$', r'\.asp$', r'\.aspx$', r'\.jsp$'
            ]
        
        if self.hakrawler is None:
            self.hakrawler = HakrawlerConfig()
        
        if self.custom_crawler is None:
            self.custom_crawler = CustomCrawlerConfig()


class SpiderConfigManager:
    """Manager for loading and validating spider configuration"""
    
    def __init__(self):
        self.config_cache = {}
        self.tools_available = self._check_tool_availability()
    
    def _check_tool_availability(self) -> Dict[str, Any]:
        """Check availability of required tools and store their paths"""
        tools = {}
        
        # Check hakrawler with comprehensive search
        hakrawler_path = self._find_hakrawler_path()
        tools['hakrawler'] = hakrawler_path
        if not hakrawler_path:
            debug_print("hakrawler not found in common locations", level="WARNING")
        else:
            debug_print(f"Found hakrawler at: {hakrawler_path}")
        
        # Check curl (fallback for custom crawler) 
        tools['curl'] = shutil.which('curl')
        
        # Check python dependencies
        try:
            import httpx
            tools['httpx'] = True
        except ImportError:
            tools['httpx'] = False
            debug_print("httpx not available for custom crawler", level="WARNING")
        
        return tools
    
    def _find_hakrawler_path(self) -> Optional[str]:
        """Find hakrawler in multiple common locations"""
        
        # 1. Check PATH first (fastest)
        path = shutil.which('hakrawler')
        if path and self._test_hakrawler_execution(path):
            return path
        
        # 2. Check common Go paths
        go_paths = [
            os.path.expanduser('~/go/bin/hakrawler'),
            '/usr/local/go/bin/hakrawler',
        ]
        
        # Add GOPATH and GOROOT if they exist
        if 'GOPATH' in os.environ:
            go_paths.append(os.path.join(os.environ['GOPATH'], 'bin', 'hakrawler'))
        if 'GOROOT' in os.environ:
            go_paths.append(os.path.join(os.environ['GOROOT'], 'bin', 'hakrawler'))
        
        # 3. Check HTB/Kali common locations
        htb_paths = [
            '/opt/hakrawler/hakrawler',
            '/usr/local/bin/hakrawler',
            '/opt/go/bin/hakrawler',
            '/snap/bin/hakrawler',  # Snap packages
        ]
        
        # 4. Check user tool directories
        user_paths = [
            os.path.expanduser('~/.local/bin/hakrawler'),
            os.path.expanduser('~/tools/hakrawler'),
            os.path.expanduser('~/bin/hakrawler'),
            os.path.expanduser('~/.cargo/bin/hakrawler'),  # Rust installations
        ]
        
        # Test all paths
        for path in go_paths + htb_paths + user_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                if self._test_hakrawler_execution(path):
                    return path
        
        return None
    
    def _test_hakrawler_execution(self, path: str) -> bool:
        """Test if hakrawler path actually works"""
        try:
            result = subprocess.run([path, '-h'], 
                                  capture_output=True, 
                                  timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            return False
    
    def get_config(self, **overrides) -> SpiderConfig:
        """Get spider configuration with optional overrides"""
        # Start with default config
        config = SpiderConfig()
        
        # Load from environment variables
        env_config = self._load_from_environment()
        self._apply_config_overrides(config, env_config)
        
        # Apply user overrides
        self._apply_config_overrides(config, overrides)
        
        # Validate and adjust based on tool availability
        self._validate_and_adjust_config(config)
        
        return config
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}
        
        # Global settings
        if 'SPIDER_MAX_URLS' in os.environ:
            env_config['max_total_urls'] = int(os.environ['SPIDER_MAX_URLS'])
        
        if 'SPIDER_MAX_TIME' in os.environ:
            env_config['max_crawl_time'] = int(os.environ['SPIDER_MAX_TIME'])
        
        if 'SPIDER_CONCURRENT' in os.environ:
            env_config['max_concurrent_crawls'] = int(os.environ['SPIDER_CONCURRENT'])
        
        # Tool toggles
        if 'SPIDER_ENABLE_HAKRAWLER' in os.environ:
            env_config['enable_hakrawler'] = os.environ['SPIDER_ENABLE_HAKRAWLER'].lower() == 'true'
        
        if 'SPIDER_ENABLE_CUSTOM' in os.environ:
            env_config['enable_custom_crawler'] = os.environ['SPIDER_ENABLE_CUSTOM'].lower() == 'true'
        
        # Hakrawler specific
        hakrawler_config = {}
        if 'HAKRAWLER_TIMEOUT' in os.environ:
            hakrawler_config['timeout'] = int(os.environ['HAKRAWLER_TIMEOUT'])
        
        if 'HAKRAWLER_DEPTH' in os.environ:
            hakrawler_config['depth'] = int(os.environ['HAKRAWLER_DEPTH'])
        
        if 'HAKRAWLER_THREADS' in os.environ:
            hakrawler_config['threads'] = int(os.environ['HAKRAWLER_THREADS'])
        
        if hakrawler_config:
            env_config['hakrawler'] = hakrawler_config
        
        return env_config
    
    def _apply_config_overrides(self, config: SpiderConfig, overrides: Dict[str, Any]):
        """Apply configuration overrides"""
        for key, value in overrides.items():
            if hasattr(config, key):
                if key == 'hakrawler' and isinstance(value, dict):
                    # Apply hakrawler sub-config
                    for hk_key, hk_value in value.items():
                        if hasattr(config.hakrawler, hk_key):
                            setattr(config.hakrawler, hk_key, hk_value)
                elif key == 'custom_crawler' and isinstance(value, dict):
                    # Apply custom crawler sub-config
                    for cc_key, cc_value in value.items():
                        if hasattr(config.custom_crawler, cc_key):
                            setattr(config.custom_crawler, cc_key, cc_value)
                else:
                    setattr(config, key, value)
    
    def _validate_and_adjust_config(self, config: SpiderConfig):
        """Validate configuration and adjust based on tool availability"""
        # Disable tools that aren't available
        if not self.tools_available.get('hakrawler'):
            config.enable_hakrawler = False
            debug_print("Hakrawler disabled - tool not available")
        
        if not self.tools_available.get('httpx', False):
            config.enable_custom_crawler = False
            debug_print("Custom crawler disabled - httpx not available")
        
        # Ensure at least one crawler is enabled
        if not config.enable_hakrawler and not config.enable_custom_crawler:
            debug_print("No crawlers available - enabling basic fallback", level="WARNING")
            # Force enable custom crawler with curl fallback
            config.enable_custom_crawler = True
        
        # Validate numeric limits
        config.max_total_urls = max(10, min(10000, config.max_total_urls))
        config.max_crawl_time = max(30, min(3600, config.max_crawl_time))
        config.max_concurrent_crawls = max(1, min(20, config.max_concurrent_crawls))
        
        # Validate hakrawler config
        config.hakrawler.timeout = max(10, min(300, config.hakrawler.timeout))
        config.hakrawler.depth = max(1, min(10, config.hakrawler.depth))
        config.hakrawler.max_pages = max(10, min(1000, config.hakrawler.max_pages))
        config.hakrawler.threads = max(1, min(20, config.hakrawler.threads))
        
        # Validate custom crawler config
        config.custom_crawler.max_concurrent = max(1, min(50, config.custom_crawler.max_concurrent))
        config.custom_crawler.request_timeout = max(5, min(60, config.custom_crawler.request_timeout))
    
    def get_hakrawler_command_args(self, config: SpiderConfig, target_url: str) -> List[str]:
        """Generate hakrawler command arguments"""
        hakrawler_path = self.tools_available.get('hakrawler')
        if not hakrawler_path:
            raise RuntimeError("hakrawler not available")
        
        args = [hakrawler_path]
        
        # Basic options
        args.extend(['-timeout', str(config.hakrawler.timeout)])
        args.extend(['-depth', str(config.hakrawler.depth)])
        args.extend(['-h', config.hakrawler.user_agent])
        args.extend(['-t', str(config.hakrawler.threads)])
        
        # Feature flags
        if config.hakrawler.include_subdomains:
            args.append('-subs')
        
        if config.hakrawler.include_urls:
            args.append('-u')
        
        if config.hakrawler.include_forms:
            args.append('-forms')
        
        if config.hakrawler.include_wayback:
            args.append('-wayback')
        
        if config.hakrawler.include_commonspeak:
            args.append('-commonspeak')
        
        # Rate limiting
        if config.hakrawler.delay > 0:
            args.extend(['-d', str(config.hakrawler.delay)])
        
        return args
    
    def validate_hakrawler_installation(self) -> bool:
        """Validate hakrawler installation and get version"""
        hakrawler_path = self.tools_available.get('hakrawler')
        if not hakrawler_path:
            return False
        
        try:
            result = subprocess.run(
                [hakrawler_path, '-h'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                debug_print("hakrawler validation successful")
                return True
            else:
                debug_print(f"hakrawler validation failed: {result.stderr}", level="ERROR")
                return False
                
        except Exception as e:
            debug_print(f"hakrawler validation error: {e}", level="ERROR")
            return False


# Global config manager instance
_config_manager = None


def get_spider_config(**overrides) -> SpiderConfig:
    """Get spider configuration (singleton pattern)"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SpiderConfigManager()
    return _config_manager.get_config(**overrides)


def get_config_manager() -> SpiderConfigManager:
    """Get config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SpiderConfigManager()
    return _config_manager


def validate_tools() -> Dict[str, bool]:
    """Validate all required tools"""
    manager = get_config_manager()
    return manager.tools_available.copy()