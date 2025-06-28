"""
Technology Detection Helper for ipcrawler

Extracts technology information from scan results for intelligent wordlist selection.
Hooks into existing WhatWeb, Nmap, and other scan outputs.
"""

import os
import re
import glob
from typing import Set, Optional, Dict, List

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class TechnologyDetector:
    """Extract technology information from scan results"""
    
    def __init__(self, target_scan_dir: str):
        """
        Initialize detector for a target's scan directory
        
        Args:
            target_scan_dir: Path to target's scan results directory
        """
        self.scan_dir = target_scan_dir
        self.detected_technologies = set()
        self.technology_patterns = self._load_technology_patterns()
    
    def _load_technology_patterns(self) -> Dict[str, List[str]]:
        """
        Load technology detection patterns from technology_aliases.yaml
        
        Returns:
            Dictionary mapping technology names to their detection patterns
        """
        aliases_path = os.path.join(os.path.dirname(__file__), 'data', 'technology_aliases.yaml')
        
        try:
            if not YAML_AVAILABLE:
                raise ImportError("PyYAML not available")
            
            with open(aliases_path, 'r') as f:
                aliases_data = yaml.safe_load(f)
            
            technology_aliases = aliases_data.get('technology_aliases', {})
            patterns = {}
            
            # Convert aliases to regex patterns for detection
            for tech, tech_data in technology_aliases.items():
                if isinstance(tech_data, dict) and 'aliases' in tech_data:
                    # Convert aliases to regex patterns
                    tech_patterns = []
                    for alias in tech_data['aliases']:
                        # Escape regex special characters but preserve intentional regex patterns
                        if any(char in alias for char in ['.', '?', '*', '+', '[', ']', '(', ')', '{', '}', '|', '^', '$']):
                            # This looks like a regex pattern, use as-is
                            tech_patterns.append(alias)
                        else:
                            # This is a plain string, escape it for regex
                            tech_patterns.append(re.escape(alias))
                    patterns[tech] = tech_patterns
            
            return patterns
            
        except Exception as e:
            if os.environ.get('IPCRAWLER_DEBUG'):
                print(f"Warning: Could not load technology patterns from {aliases_path}: {e}")
            
            # Minimal fallback patterns
            return {
                'wordpress': [r'wp-content', r'wp-admin', r'WordPress'],
                'php': [r'\.php', r'PHP/', r'PHPSESSID'],
                'apache': [r'Server:.*Apache', r'Apache/'],
                'nginx': [r'Server:.*nginx', r'nginx/']
            }
    
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
            files = sorted(glob.glob(os.path.join(self.scan_dir, '**', pattern), recursive=True))
            
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
            
            # Apply technology detection patterns with confidence scoring
            for tech, patterns in sorted(self.technology_patterns.items()):
                confidence_score = 0
                matches_found = 0
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        matches_found += len(matches)
                        confidence_score += len(matches)
                
                # Require stronger evidence for detection (reduce false positives)
                # Higher threshold for generic technologies, lower for specific ones
                min_confidence = 2 if tech in ['apache', 'nginx', 'php', 'java'] else 1
                
                if confidence_score >= min_confidence:
                    detected.add(tech)
                        
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