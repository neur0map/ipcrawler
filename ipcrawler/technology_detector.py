"""
Technology Detection Helper for ipcrawler

Extracts technology information from scan results for intelligent wordlist selection.
Hooks into existing WhatWeb, Nmap, and other scan outputs.
"""

import os
import re
import glob
from typing import Set, Optional
from pathlib import Path


class TechnologyDetector:
    """Extract technology information from scan results"""
    
    # Technology detection patterns from common scan outputs
    TECHNOLOGY_PATTERNS = {
        # Web Technologies
        'wordpress': [
            r'wp-content',
            r'wp-admin', 
            r'wp-json',
            r'wp-includes',
            r'WordPress',
            r'wp_',
            r'/wp/'
        ],
        'drupal': [
            r'drupal',
            r'sites/default',
            r'modules/',
            r'Drupal'
        ],
        'joomla': [
            r'joomla',
            r'index\.php\?option=com_',
            r'Joomla'
        ],
        
        # Programming Languages
        'php': [
            r'X-Powered-By:.*PHP',
            r'PHPSESSID',
            r'\.php',
            r'PHP/'
        ],
        'asp': [
            r'X-AspNet-Version',
            r'ASPSESSIONID',
            r'\.aspx?',
            r'ASP\.NET'
        ],
        'java': [
            r'tomcat',
            r'jetty',
            r'JSESSIONID',
            r'spring',
            r'struts'
        ],
        'python': [
            r'django',
            r'flask',
            r'wsgi',
            r'gunicorn',
            r'Python'
        ],
        'nodejs': [
            r'X-Powered-By:.*Express',
            r'Server:.*Express',
            r'\bexpress\b',  # Word boundary to avoid matching "expression"
            r'node\.js',
            r'nodejs'
        ],
        'nextjs': [
            r'X-Powered-By:.*Next\.js',
            r'Next\.js',
            r'_next/',
            r'__next'
        ],
        
        # Web Servers
        'apache': [
            r'Server:.*Apache',
            r'Apache/',
            r'httpd'
        ],
        'nginx': [
            r'Server:.*nginx',
            r'nginx/'
        ],
        'iis': [
            r'Server:.*Microsoft-IIS',
            r'Microsoft-IIS'
        ],
        
        # Cloud Platforms
        'aws': [
            r'X-Amz-',
            r'amazonaws',
            r'AmazonS3'
        ],
        'azure': [
            r'X-Azure-',
            r'azure'
        ],
        'gcp': [
            r'X-Goog-',
            r'appengine'
        ]
    }
    
    def __init__(self, target_scan_dir: str):
        """
        Initialize detector for a target's scan directory
        
        Args:
            target_scan_dir: Path to target's scan results directory
        """
        self.scan_dir = target_scan_dir
        self.detected_technologies = set()
    
    def detect_from_scan_results(self) -> Set[str]:
        """
        Detect technologies from all scan results in target directory
        
        Returns:
            Set of detected technology strings
        """
        if not os.path.exists(self.scan_dir):
            return set()
        
        detected = set()
        
        # Analyze different types of scan files
        scan_file_patterns = [
            '*whatweb*.txt',      # WhatWeb results
            '*nmap*.txt',         # Nmap results  
            '*http*.txt',         # HTTP scan results
            '*curl*.txt',         # Curl results
            '*nikto*.txt'         # Nikto results
        ]
        
        for pattern in scan_file_patterns:
            files = glob.glob(os.path.join(self.scan_dir, '**', pattern), recursive=True)
            
            for file_path in files:
                file_technologies = self._analyze_scan_file(file_path)
                detected.update(file_technologies)
        
        self.detected_technologies = detected
        return detected
    
    def _analyze_scan_file(self, file_path: str) -> Set[str]:
        """
        Analyze individual scan file for technology indicators
        
        Args:
            file_path: Path to scan result file
            
        Returns:
            Set of detected technologies from this file
        """
        detected = set()
        
        try:
            # Read file with error handling for various encodings
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Only read first 16KB for performance
                content = f.read(16384)
            
            # Apply technology detection patterns
            for tech, patterns in self.TECHNOLOGY_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        detected.add(tech)
                        break  # One match per technology is enough
                        
        except Exception as e:
            # Silent failure - don't break scanning for detection issues
            if os.environ.get('IPCRAWLER_DEBUG'):
                print(f"Technology detection warning: {file_path}: {e}")
        
        return detected
    
    def get_detected_technologies_summary(self) -> str:
        """Get human-readable summary of detected technologies"""
        if not self.detected_technologies:
            return "No technologies detected"
        
        return f"Detected technologies: {', '.join(sorted(self.detected_technologies))}"
    
    @classmethod
    def detect_from_target(cls, target) -> Set[str]:
        """
        Convenience method to detect technologies from a target object
        
        Args:
            target: Target object with scandir attribute
            
        Returns:
            Set of detected technology strings
        """
        if not hasattr(target, 'scandir') or not target.scandir:
            return set()
        
        detector = cls(target.scandir)
        return detector.detect_from_scan_results()


# Convenience function for plugin integration
def get_detected_technologies(target) -> Set[str]:
    """
    Get detected technologies for a target
    
    Args:
        target: Target object or scan directory path
        
    Returns:
        Set of detected technology strings
    """
    if isinstance(target, str):
        # target is a scan directory path
        detector = TechnologyDetector(target)
        return detector.detect_from_scan_results()
    elif hasattr(target, 'scandir'):
        # target is a target object
        return TechnologyDetector.detect_from_target(target)
    else:
        return set()