#!/usr/bin/env python3
"""
Script to populate tech_compatibility and port_compatibility in seclists_catalog.json
Based on the wordlist_mappings.json database
"""

import json
import sys
from pathlib import Path

def populate_catalog_mappings():
    """Populate compatibility fields in wordlist catalog"""
    
    # Get database paths
    db_path = Path(__file__).parent.parent / "database"
    catalog_path = db_path / "wordlists" / "seclists_catalog.json"
    mappings_path = db_path / "scorer" / "wordlist_mappings.json"
    
    # Load existing data
    try:
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
        
        with open(mappings_path, 'r') as f:
            mappings = json.load(f)
    except Exception as e:
        print(f"Error loading files: {e}")
        return False
    
    # Create reverse mapping: wordlist -> [technologies, ports]
    wordlist_to_tech = {}
    wordlist_to_ports = {}
    
    # Process technology mappings
    for tech, config in mappings.get('technology_mappings', {}).items():
        for wl in config.get('primary_wordlists', []) + config.get('secondary_wordlists', []):
            if wl not in wordlist_to_tech:
                wordlist_to_tech[wl] = []
            wordlist_to_tech[wl].append(tech)
    
    # Process port mappings
    for port, config in mappings.get('port_mappings', {}).items():
        for wl in config.get('primary_wordlists', []) + config.get('secondary_wordlists', []):
            if wl not in wordlist_to_ports:
                wordlist_to_ports[wl] = []
            wordlist_to_ports[wl].append(int(port))
    
    # Update catalog entries
    updated_count = 0
    for wordlist in catalog.get('wordlists', []):
        wl_name = wordlist['name']
        
        # Update tech_compatibility
        if wl_name in wordlist_to_tech:
            wordlist['tech_compatibility'] = wordlist_to_tech[wl_name]
            updated_count += 1
        
        # Update port_compatibility  
        if wl_name in wordlist_to_ports:
            wordlist['port_compatibility'] = wordlist_to_ports[wl_name]
            wordlist['recommended_for_ports'] = wordlist_to_ports[wl_name]
            updated_count += 1
    
    # Save updated catalog
    try:
        with open(catalog_path, 'w') as f:
            json.dump(catalog, f, indent=2)
        print(f"Successfully updated {updated_count} wordlist entries")
        return True
    except Exception as e:
        print(f"Error saving catalog: {e}")
        return False

if __name__ == "__main__":
    success = populate_catalog_mappings()
    sys.exit(0 if success else 1)