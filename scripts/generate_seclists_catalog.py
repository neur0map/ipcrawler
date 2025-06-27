#!/usr/bin/env python3
"""
SecLists Catalog Generator

Generates a comprehensive catalog of all wordlists in a SecLists installation
for use with ipcrawler intelligent wordlist selection.

Usage: python3 generate_seclists_catalog.py /path/to/SecLists
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
import argparse


def generate_seclists_catalog(seclists_path: str) -> dict:
    """Generate catalog of all wordlists in SecLists directory"""
    catalog = {
        'metadata': {
            'generator_version': '1.0',
            'seclists_path': seclists_path,
            'generated_at': datetime.now().isoformat(),
            'total_wordlists': 0
        },
        'wordlists': {}
    }
    
    print(f"🔍 Scanning SecLists directory: {seclists_path}")
    
    # Walk through all .txt files in SecLists
    wordlist_count = 0
    for root, dirs, files in os.walk(seclists_path):
        for file in files:
            if file.endswith('.txt') or file.endswith('.fuzz.txt'):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, seclists_path)
                
                # Get file statistics
                try:
                    stat = os.stat(full_path)
                    size_kb = stat.st_size // 1024
                    
                    # Count lines efficiently
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        line_count = sum(1 for _ in f)
                    
                    catalog['wordlists'][relative_path] = {
                        'size_kb': max(1, size_kb),  # Minimum 1KB
                        'lines': line_count,
                        'category': _categorize_wordlist(relative_path),
                        'tags': _extract_tags(relative_path, file)
                    }
                    
                    wordlist_count += 1
                    if wordlist_count % 100 == 0:
                        print(f"  📄 Processed {wordlist_count} wordlists...")
                    
                except Exception as e:
                    print(f"⚠️  Warning: Could not process {relative_path}: {e}")
    
    catalog['metadata']['total_wordlists'] = wordlist_count
    print(f"✅ Cataloged {wordlist_count} wordlists")
    
    return catalog


def _categorize_wordlist(path: str) -> str:
    """Categorize wordlist based on path"""
    path_lower = path.lower()
    
    if 'web-content' in path_lower:
        return 'web'
    elif 'usernames' in path_lower:
        return 'usernames'  
    elif 'passwords' in path_lower:
        return 'passwords'
    elif 'dns' in path_lower:
        return 'dns'
    elif 'snmp' in path_lower:
        return 'snmp'
    elif 'fuzzing' in path_lower:
        return 'fuzzing'
    else:
        return 'other'


def _extract_tags(path: str, filename: str) -> list:
    """Extract technology tags from path and filename"""
    tags = []
    
    # Technology detection from path/filename
    tech_indicators = {
        'wordpress': ['wordpress', 'wp-'],
        'drupal': ['drupal'],
        'php': ['php'],
        'asp': ['asp', 'iis'],
        'cms': ['cms'],
        'apache': ['apache'],
        'nginx': ['nginx'],
        'tomcat': ['tomcat'],
        'joomla': ['joomla'],
        'sharepoint': ['sharepoint'],
        'coldfusion': ['coldfusion'],
        'spring': ['spring'],
        'java': ['java'],
        'dotnet': ['.net', 'dotnet'],
        'python': ['python', 'django', 'flask'],
        'nodejs': ['node', 'express'],
        'ruby': ['ruby', 'rails']
    }
    
    path_filename = f"{path} {filename}".lower()
    
    for tech, indicators in tech_indicators.items():
        if any(indicator in path_filename for indicator in indicators):
            tags.append(tech)
    
    # Size-based tags for quick filtering
    if 'small' in path_filename or 'short' in path_filename or 'top' in path_filename:
        tags.append('small')
    elif 'big' in path_filename or 'large' in path_filename or 'huge' in path_filename:
        tags.append('large')
    
    return tags


def main():
    parser = argparse.ArgumentParser(description='Generate SecLists catalog for ipcrawler')
    parser.add_argument('seclists_path', help='Path to SecLists directory')
    parser.add_argument('-o', '--output', default='seclists_catalog.yaml', 
                        help='Output catalog file (default: seclists_catalog.yaml)')
    parser.add_argument('--validate', action='store_true',
                        help='Validate SecLists installation before cataloging')
    
    args = parser.parse_args()
    
    # Validate SecLists path
    if not os.path.exists(args.seclists_path):
        print(f"❌ Error: SecLists path does not exist: {args.seclists_path}")
        sys.exit(1)
    
    # Basic validation - check for common directories
    if args.validate:
        print("🔍 Validating SecLists installation...")
        required_dirs = ['Discovery', 'Usernames', 'Passwords']
        for req_dir in required_dirs:
            full_dir = os.path.join(args.seclists_path, req_dir)
            if not os.path.exists(full_dir):
                print(f"⚠️  Warning: Expected directory not found: {req_dir}")
            else:
                print(f"✅ Found: {req_dir}")
    
    print(f"🚀 Starting catalog generation...")
    catalog = generate_seclists_catalog(args.seclists_path)
    
    # Write catalog
    print(f"💾 Writing catalog to: {args.output}")
    try:
        with open(args.output, 'w') as f:
            yaml.dump(catalog, f, default_flow_style=False, sort_keys=True)
        
        print(f"✅ Catalog successfully generated!")
        print(f"   📊 Total wordlists: {catalog['metadata']['total_wordlists']}")
        print(f"   📁 Catalog file: {args.output}")
        print(f"   💡 Place this file in ipcrawler/data/ for intelligent wordlist selection")
        
    except Exception as e:
        print(f"❌ Error writing catalog: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()