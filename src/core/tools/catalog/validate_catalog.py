#!/usr/bin/env python3
"""
"""


# Add project root to path



    """
    
        
    """
    results = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "stats": {}
    }
    
            catalog_data = json.load(f)
        
        catalog = WordlistCatalog(**catalog_data)
        results["valid"] = True
        
        # Check file paths
        missing_files = []
        invalid_files = []
        total_size = 0
        
            file_path = Path(entry.full_path)
            
                total_size += file_path.stat().st_size
        
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
            if len(missing_files) <= 10:
        
        
    


    """
    
        
    """
            catalog_data = json.load(f)
        
        catalog = WordlistCatalog(**catalog_data)
        
        catalog.generated_at = datetime.utcnow()
        
        # Rebuild indexes
        
        
            json.dump(catalog.dict(), f, indent=2, default=str)
        
        


    """Main validation function."""
    project_root = Path(__file__).parent.parent.parent
    catalog_path = project_root / "database" / "wordlists" / "seclists_catalog.json"
    
    print("=" * 40)
    
    
    
    # Validate catalog
    results = validate_catalog(catalog_path)
    
    
    # Display stats
    stats = results["stats"]
    
    # Display warnings
    
    # Test resolver
        resolver_stats = resolver.get_catalog_stats()
    
    # Summary
    if stats['missing_files'] == 0 and stats['invalid_files'] == 0:


if __name__ == "__main__":
