#!/usr/bin/env python3
"""
Catalog validation and update utility.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.wordlists.models import WordlistCatalog
from database.wordlists.resolver import resolver


def validate_catalog(catalog_path: Path) -> Dict[str, any]:
    """
    Validate catalog file and check wordlist paths.
    
    Args:
        catalog_path: Path to catalog JSON file
        
    Returns:
        Validation results dictionary
    """
    results = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "stats": {}
    }
    
    try:
        # Load and validate catalog structure
        with open(catalog_path, 'r') as f:
            catalog_data = json.load(f)
        
        catalog = WordlistCatalog(**catalog_data)
        results["valid"] = True
        
        # Check file paths
        missing_files = []
        invalid_files = []
        total_size = 0
        
        for entry in catalog.wordlists.values():
            file_path = Path(entry.full_path)
            
            if not file_path.exists():
                missing_files.append(entry.name)
            elif not file_path.is_file():
                invalid_files.append(entry.name)
            else:
                total_size += file_path.stat().st_size
        
        # Generate stats
        results["stats"] = {
            "total_wordlists": len(catalog.wordlists),
            "missing_files": len(missing_files),
            "invalid_files": len(invalid_files),
            "available_files": len(catalog.wordlists) - len(missing_files) - len(invalid_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "catalog_generated": catalog.generated_at.isoformat() if catalog.generated_at else None,
            "seclists_path": catalog.seclists_path
        }
        
        # Add warnings for missing files
        if missing_files:
            results["warnings"].append(f"{len(missing_files)} wordlist files are missing")
            if len(missing_files) <= 10:
                results["warnings"].extend([f"Missing: {f}" for f in missing_files[:10]])
            else:
                results["warnings"].append(f"First 10 missing files: {missing_files[:10]}")
        
        if invalid_files:
            results["warnings"].append(f"{len(invalid_files)} wordlist paths are invalid")
        
    except FileNotFoundError:
        results["errors"].append("Catalog file not found")
    except json.JSONDecodeError as e:
        results["errors"].append(f"Invalid JSON: {e}")
    except Exception as e:
        results["errors"].append(f"Validation error: {e}")
    
    return results


def update_catalog_metadata(catalog_path: Path) -> bool:
    """
    Update catalog metadata without regenerating entire catalog.
    
    Args:
        catalog_path: Path to catalog JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(catalog_path, 'r') as f:
            catalog_data = json.load(f)
        
        catalog = WordlistCatalog(**catalog_data)
        
        # Update metadata
        catalog.generated_at = datetime.utcnow()
        
        # Rebuild indexes
        catalog.rebuild_indexes()
        
        # Update stats
        catalog.get_stats()
        
        # Save updated catalog
        with open(catalog_path, 'w') as f:
            json.dump(catalog.dict(), f, indent=2, default=str)
        
        return True
        
    except Exception as e:
        print(f"Error updating catalog: {e}")
        return False


def main():
    """Main validation function."""
    catalog_path = Path(__file__).parent / "seclists_catalog.json"
    
    print("SecLists Catalog Validation")
    print("=" * 40)
    
    if not catalog_path.exists():
        print(f"❌ Catalog not found: {catalog_path}")
        print("\nTo generate catalog:")
        print("1. Run 'make install' to install SecLists")
        print("2. Or run 'python database/wordlists/generate_catalog.py'")
        return 1
    
    print(f"Validating catalog: {catalog_path}")
    
    # Validate catalog
    results = validate_catalog(catalog_path)
    
    if results["valid"]:
        print("✅ Catalog structure is valid")
    else:
        print("❌ Catalog validation failed")
        for error in results["errors"]:
            print(f"  Error: {error}")
        return 1
    
    # Display stats
    stats = results["stats"]
    print(f"\n📊 Catalog Statistics:")
    print(f"  Total wordlists: {stats['total_wordlists']}")
    print(f"  Available files: {stats['available_files']}")
    print(f"  Missing files: {stats['missing_files']}")
    print(f"  Total size: {stats['total_size_mb']} MB")
    print(f"  Generated: {stats['catalog_generated']}")
    print(f"  SecLists path: {stats['seclists_path']}")
    
    # Display warnings
    if results["warnings"]:
        print(f"\n⚠️  Warnings:")
        for warning in results["warnings"]:
            print(f"  {warning}")
    
    # Test resolver
    print(f"\n🔧 Testing resolver...")
    if resolver.is_available():
        resolver_stats = resolver.get_catalog_stats()
        print(f"  Resolver loaded: ✅")
        print(f"  Catalog wordlists: {resolver_stats.get('total_wordlists', 0)}")
    else:
        print(f"  Resolver loaded: ❌")
    
    # Summary
    if stats['missing_files'] == 0 and stats['invalid_files'] == 0:
        print(f"\n✅ Catalog validation successful!")
        return 0
    else:
        print(f"\n⚠️  Catalog has issues but is usable")
        if stats['missing_files'] > 0:
            print(f"  Consider reinstalling SecLists to fix missing files")
        return 0


if __name__ == "__main__":
    sys.exit(main())