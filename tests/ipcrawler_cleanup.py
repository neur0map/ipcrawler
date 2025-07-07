#!/usr/bin/env python3
"""
IPCrawler Cleanup Tool - Safely remove unused test files and fix scripts
"""

import argparse
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

from file_discovery import find_unused_files

logger = logging.getLogger(__name__)

class IPCrawlerCleanup:
    """Main cleanup tool for removing unused files"""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.backup_dir = self.root_dir / "cleanup_backups"
        self.trash_dir = self.root_dir / "trash"
        
    def run_cleanup(self, dry_run: bool = False, force: bool = False, 
                   backup: bool = True, restore_file: Optional[str] = None) -> int:
        """
        Run the cleanup process
        
        Args:
            dry_run: Only show what would be deleted
            force: Delete without confirmation
            backup: Create backups before deletion
            restore_file: Restore a specific file from backup
            
        Returns:
            Exit code (0 = success, 1 = error)
        """
        
        if restore_file:
            return self._restore_file(restore_file)
        
        # Find unused files
        print("🔍 Scanning for unused files...")
        unused_files = find_unused_files(str(self.root_dir))
        
        if not unused_files:
            print("✅ No unused files found!")
            return 0
        
        print(f"\n📊 Found {len(unused_files)} unused files:")
        for file_path in unused_files:
            relative_path = file_path.relative_to(self.root_dir)
            file_size = file_path.stat().st_size
            print(f"   ❌ {relative_path} ({file_size} bytes)")
        
        if dry_run:
            print(f"\n🔍 DRY RUN: Would delete {len(unused_files)} files")
            return 0
        
        # Confirm deletion
        if not force:
            if not self._confirm_deletion(unused_files):
                print("❌ Cleanup cancelled by user")
                return 1
        
        # Create backup if requested
        if backup:
            backup_path = self._create_backup_directory()
            print(f"💾 Creating backups in: {backup_path}")
        
        # Delete files
        deleted_count = 0
        for file_path in unused_files:
            try:
                if backup:
                    self._backup_file(file_path, backup_path)
                
                self._delete_file(file_path)
                deleted_count += 1
                
                relative_path = file_path.relative_to(self.root_dir)
                print(f"   ✅ Deleted: {relative_path}")
                
            except Exception as e:
                relative_path = file_path.relative_to(self.root_dir)
                print(f"   ❌ Failed to delete {relative_path}: {e}")
        
        print(f"\n🎉 Cleanup complete: {deleted_count}/{len(unused_files)} files deleted")
        
        if backup and deleted_count > 0:
            print(f"💾 Backups saved to: {backup_path}")
            print(f"🔄 To restore a file: ipcrawler-cleanup --restore <filename>")
        
        return 0
    
    def _confirm_deletion(self, unused_files: List[Path]) -> bool:
        """Prompt user for confirmation on each file or all files"""
        
        print(f"\n❓ Confirm deletion of {len(unused_files)} files:")
        print("   [y]es to all, [n]o to all, [i]nteractive mode")
        
        choice = input("Choose [y/n/i]: ").strip().lower()
        
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        elif choice == 'i':
            return self._interactive_confirmation(unused_files)
        else:
            print("❌ Invalid choice")
            return self._confirm_deletion(unused_files)
    
    def _interactive_confirmation(self, unused_files: List[Path]) -> bool:
        """Interactive confirmation for each file"""
        
        confirmed_files = []
        
        for file_path in unused_files:
            relative_path = file_path.relative_to(self.root_dir)
            
            # Show file content preview
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    preview = '\n'.join(lines[:5])  # First 5 lines
                
                print(f"\n📄 {relative_path}:")
                print(f"   Preview (first 5 lines):")
                for i, line in enumerate(preview.split('\n')[:5], 1):
                    print(f"   {i:2}: {line[:80]}")
                
                if len(lines) > 5:
                    print(f"   ... and {len(lines) - 5} more lines")
                    
            except Exception:
                print(f"\n📄 {relative_path}: (could not preview)")
            
            while True:
                choice = input(f"Delete {relative_path}? [y/n/q]: ").strip().lower()
                
                if choice == 'y':
                    confirmed_files.append(file_path)
                    break
                elif choice == 'n':
                    break
                elif choice == 'q':
                    print("❌ Cleanup cancelled")
                    return False
                else:
                    print("Please enter y, n, or q")
        
        # Update the list to only include confirmed files
        unused_files[:] = confirmed_files
        return len(confirmed_files) > 0
    
    def _create_backup_directory(self) -> Path:
        """Create timestamped backup directory"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / timestamp
        backup_path.mkdir(parents=True, exist_ok=True)
        
        return backup_path
    
    def _backup_file(self, file_path: Path, backup_dir: Path) -> None:
        """Backup a file before deletion"""
        
        relative_path = file_path.relative_to(self.root_dir)
        backup_file = backup_dir / relative_path
        
        # Create backup directory structure
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file to backup
        shutil.copy2(file_path, backup_file)
    
    def _delete_file(self, file_path: Path) -> None:
        """Delete a file (move to trash first for safety)"""
        
        # Create trash directory if it doesn't exist
        self.trash_dir.mkdir(exist_ok=True)
        
        # Move to trash first
        relative_path = file_path.relative_to(self.root_dir)
        trash_file = self.trash_dir / relative_path.name
        
        # Handle filename conflicts in trash
        counter = 1
        while trash_file.exists():
            stem = relative_path.stem
            suffix = relative_path.suffix
            trash_file = self.trash_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Move to trash
        shutil.move(str(file_path), str(trash_file))
    
    def _restore_file(self, filename: str) -> int:
        """Restore a file from backup"""
        
        print(f"🔍 Searching for backup of: {filename}")
        
        # Find all backup directories
        if not self.backup_dir.exists():
            print("❌ No backup directory found")
            return 1
        
        backup_dirs = sorted([d for d in self.backup_dir.iterdir() if d.is_dir()], reverse=True)
        
        if not backup_dirs:
            print("❌ No backups found")
            return 1
        
        # Search for the file in backups (most recent first)
        for backup_dir in backup_dirs:
            for backup_file in backup_dir.glob(f"**/{filename}"):
                return self._restore_file_from_backup(backup_file, filename)
        
        print(f"❌ File '{filename}' not found in any backup")
        return 1
    
    def _restore_file_from_backup(self, backup_file: Path, filename: str) -> int:
        """Restore a specific file from backup"""
        
        try:
            # Determine original location
            # backup_file is in backup_dir/timestamp/original/path
            # We need to reconstruct the original path
            backup_dir_parts = backup_file.parts
            timestamp_index = None
            
            for i, part in enumerate(backup_dir_parts):
                if part == "cleanup_backups":
                    timestamp_index = i + 1
                    break
            
            if timestamp_index is None or timestamp_index + 1 >= len(backup_dir_parts):
                print("❌ Could not determine original file location")
                return 1
            
            # Original path is everything after timestamp directory
            original_relative_parts = backup_dir_parts[timestamp_index + 1:]
            original_path = self.root_dir
            for part in original_relative_parts:
                original_path = original_path / part
            
            # Check if file already exists
            if original_path.exists():
                choice = input(f"File {original_path.relative_to(self.root_dir)} already exists. Overwrite? [y/N]: ")
                if choice.lower() != 'y':
                    print("❌ Restore cancelled")
                    return 1
            
            # Create directory structure
            original_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file back
            shutil.copy2(backup_file, original_path)
            
            backup_timestamp = backup_file.parts[timestamp_index]
            print(f"✅ Restored {filename} from backup {backup_timestamp}")
            print(f"   Location: {original_path.relative_to(self.root_dir)}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to restore {filename}: {e}")
            return 1
    
    def list_backups(self) -> int:
        """List available backups"""
        
        if not self.backup_dir.exists():
            print("❌ No backup directory found")
            return 1
        
        backup_dirs = sorted([d for d in self.backup_dir.iterdir() if d.is_dir()], reverse=True)
        
        if not backup_dirs:
            print("❌ No backups found")
            return 1
        
        print(f"📁 Available backups in {self.backup_dir}:")
        
        for backup_dir in backup_dirs:
            timestamp = backup_dir.name
            files = list(backup_dir.glob("**/*.py"))
            print(f"   {timestamp}: {len(files)} files")
            
            for file_path in files[:5]:  # Show first 5 files
                relative_path = file_path.relative_to(backup_dir)
                print(f"      • {relative_path}")
            
            if len(files) > 5:
                print(f"      ... and {len(files) - 5} more files")
        
        return 0

def main():
    """CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="IPCrawler cleanup tool for removing unused test files and fix scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ipcrawler-cleanup --dry-run                 # Show what would be deleted
  ipcrawler-cleanup --remove-unused           # Interactive deletion
  ipcrawler-cleanup --remove-unused --force   # Delete all without confirmation
  ipcrawler-cleanup --restore old_test.py     # Restore a deleted file
  ipcrawler-cleanup --list-backups            # Show available backups
        """
    )
    
    parser.add_argument('--root', default='.', help='Root directory to scan (default: current directory)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    parser.add_argument('--remove-unused', action='store_true', help='Remove unused files')
    parser.add_argument('--force', action='store_true', help='Delete without confirmation')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backups')
    parser.add_argument('--restore', metavar='FILENAME', help='Restore a file from backup')
    parser.add_argument('--list-backups', action='store_true', help='List available backups')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Validate arguments
    action_count = sum([args.dry_run, args.remove_unused, bool(args.restore), args.list_backups])
    
    if action_count == 0:
        parser.error("Must specify one action: --dry-run, --remove-unused, --restore, or --list-backups")
    elif action_count > 1:
        parser.error("Can only specify one action at a time")
    
    # Initialize cleanup tool
    cleanup = IPCrawlerCleanup(args.root)
    
    try:
        if args.list_backups:
            return cleanup.list_backups()
        else:
            return cleanup.run_cleanup(
                dry_run=args.dry_run,
                force=args.force,
                backup=not args.no_backup,
                restore_file=args.restore
            )
    
    except KeyboardInterrupt:
        print("\n❌ Cleanup interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())