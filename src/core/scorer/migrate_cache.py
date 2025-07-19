#!/usr/bin/env python3
"""
Migrate existing cache files to privacy-safe format by removing sensitive information.

Usage:
    python migrate_cache.py [--dry-run] [--backup]
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .models import CacheEntry, AnonymizedCacheEntry


class CacheMigrator:
    """Migrates cache files to privacy-safe format."""
    
    def __init__(self, cache_dir: Path, dry_run: bool = False, backup: bool = True):
        self.cache_dir = cache_dir
        self.selections_dir = cache_dir / "selections"
        self.dry_run = dry_run
        self.backup = backup
        self.stats = {
            "total_files": 0,
            "migrated": 0,
            "already_anonymized": 0,
            "errors": 0,
            "sensitive_data_removed": 0
        }
    
    def run(self):
        """Run the migration process."""
        print("🔒 SmartList Cache Privacy Migration")
        print("=" * 50)
        
        if self.dry_run:
            print("🔍 DRY RUN MODE - No files will be modified")
        
        # Create backup if requested
        if self.backup and not self.dry_run:
            self._create_backup()
        
        # Process all cache files
        cache_files = list(self.selections_dir.rglob("*.json"))
        self.stats["total_files"] = len(cache_files)
        
        print(f"\n📁 Found {len(cache_files)} cache files to process")
        
        for file_path in cache_files:
            self._migrate_file(file_path)
        
        # Print summary
        self._print_summary()
    
    def _create_backup(self):
        """Create backup of cache directory."""
        backup_dir = self.cache_dir.parent / f"contributions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n💾 Creating backup at: {backup_dir}")
        shutil.copytree(self.cache_dir, backup_dir)
        print("✅ Backup complete")
    
    def _migrate_file(self, file_path: Path):
        """Migrate a single cache file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check if already anonymized
            if 'context' in data and 'target' not in data['context']:
                self.stats["already_anonymized"] += 1
                return
            
            # Check for sensitive data
            context = data.get('context', {})
            has_sensitive = False
            
            if 'target' in context:
                target = context['target']
                if self._is_sensitive(target):
                    has_sensitive = True
                    self.stats["sensitive_data_removed"] += 1
            
            # Convert to anonymized format
            if not self.dry_run:
                # Load as old format
                old_entry = CacheEntry(**data)
                
                # Convert to anonymized
                anon_entry = AnonymizedCacheEntry.from_cache_entry(old_entry)
                
                # Save back
                with open(file_path, 'w') as f:
                    json.dump(anon_entry.model_dump(), f, indent=2, default=str)
            
            self.stats["migrated"] += 1
            
            if has_sensitive:
                print(f"🔒 Removed sensitive data from: {file_path.name}")
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"❌ Error processing {file_path.name}: {e}")
    
    def _is_sensitive(self, target: str) -> bool:
        """Check if target contains sensitive information."""
        # Check for IPs
        import re
        ip_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        if ip_pattern.match(target):
            return True
        
        # Check for domains
        if '.' in target and not target.startswith('localhost'):
            return True
        
        return False
    
    def _print_summary(self):
        """Print migration summary."""
        print("\n📊 Migration Summary")
        print("-" * 50)
        print(f"Total files: {self.stats['total_files']}")
        print(f"Migrated: {self.stats['migrated']}")
        print(f"Already anonymized: {self.stats['already_anonymized']}")
        print(f"Sensitive data removed: {self.stats['sensitive_data_removed']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.dry_run:
            print("\n🔍 DRY RUN COMPLETE - No files were modified")
            print("Run without --dry-run to perform actual migration")
        else:
            print("\n✅ Migration complete!")
            print("All cache files are now privacy-safe")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate cache to privacy-safe format")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without making changes")
    parser.add_argument("--no-backup", action="store_true",
                       help="Skip creating backup (not recommended)")
    
    args = parser.parse_args()
    
    # Find cache directory
    project_root = Path(__file__).parent.parent.parent.parent
    cache_dir = project_root / "database" / "scorer" / "contributions"
    
    if not cache_dir.exists():
        print(f"❌ Cache directory not found: {cache_dir}")
        sys.exit(1)
    
    # Run migration
    migrator = CacheMigrator(
        cache_dir=cache_dir,
        dry_run=args.dry_run,
        backup=not args.no_backup
    )
    
    try:
        migrator.run()
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()