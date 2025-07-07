#!/usr/bin/env python3
"""
End-to-end test for ipcrawler-cleanup command
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
import sys
import os

def test_cleanup_end_to_end():
    """End-to-end test of the cleanup command"""
    
    print("🧪 END-TO-END CLEANUP TEST")
    print("=" * 40)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"📁 Test directory: {temp_dir}")
    
    try:
        # Step 1: Create test structure
        print("\n📝 Step 1: Creating test files...")
        
        # Create unused test file (should be deleted)
        unused_test = temp_dir / "unused_test.py"
        unused_test.write_text('''
def test_unused_functionality():
    """This test is no longer used anywhere"""
    assert True

def another_unused_test():
    """Another unused test function"""
    pass
''')
        
        # Create used test file (should NOT be deleted)
        used_test = temp_dir / "test_active.py"
        used_test.write_text('''
def test_active_functionality():
    """This test is actively used"""
    assert True
''')
        
        # Create main module that imports the used test
        main_file = temp_dir / "main.py"
        main_file.write_text('''
import test_active
from test_active import test_active_functionality

def main():
    test_active_functionality()
    print("Application running")

if __name__ == "__main__":
    main()
''')
        
        # Create unused fix script (should be deleted)
        unused_fix = temp_dir / "old_fix_migration.py"
        unused_fix.write_text('''
#!/usr/bin/env python3
"""Old migration script that's no longer needed"""

def old_migration():
    print("Running old migration...")

if __name__ == "__main__":
    old_migration()
''')
        
        print(f"   ✅ Created {unused_test.name} (unused)")
        print(f"   ✅ Created {used_test.name} (used)")
        print(f"   ✅ Created {main_file.name} (imports used test)")
        print(f"   ✅ Created {unused_fix.name} (unused)")
        
        # Step 2: Run dry-run to verify detection
        print(f"\n🔍 Step 2: Running dry-run...")
        
        cleanup_script = Path(__file__).parent / "ipcrawler_cleanup.py"
        
        dry_run_cmd = [
            sys.executable, str(cleanup_script),
            "--root", str(temp_dir),
            "--dry-run"
        ]
        
        dry_run_result = subprocess.run(
            dry_run_cmd,
            capture_output=True,
            text=True
        )
        
        print(f"   Exit code: {dry_run_result.returncode}")
        print(f"   Output: {dry_run_result.stdout}")
        
        if dry_run_result.stderr:
            print(f"   Stderr: {dry_run_result.stderr}")
        
        # Verify dry-run detected unused files
        assert "unused_test.py" in dry_run_result.stdout
        assert "old_fix_migration.py" in dry_run_result.stdout
        assert "test_active.py" not in dry_run_result.stdout
        assert "main.py" not in dry_run_result.stdout
        
        print("   ✅ Dry-run correctly identified unused files")
        
        # Step 3: Run actual cleanup with force flag
        print(f"\n🗑️ Step 3: Running cleanup with --force...")
        
        cleanup_cmd = [
            sys.executable, str(cleanup_script),
            "--root", str(temp_dir),
            "--remove-unused",
            "--force"
        ]
        
        cleanup_result = subprocess.run(
            cleanup_cmd,
            capture_output=True,
            text=True
        )
        
        print(f"   Exit code: {cleanup_result.returncode}")
        print(f"   Output: {cleanup_result.stdout}")
        
        if cleanup_result.stderr:
            print(f"   Stderr: {cleanup_result.stderr}")
        
        # Step 4: Verify files were deleted
        print(f"\n✅ Step 4: Verifying deletion results...")
        
        # Check that unused files no longer exist
        assert not unused_test.exists(), f"{unused_test.name} should have been deleted"
        assert not unused_fix.exists(), f"{unused_fix.name} should have been deleted"
        
        # Check that used files still exist
        assert used_test.exists(), f"{used_test.name} should still exist"
        assert main_file.exists(), f"{main_file.name} should still exist"
        
        print(f"   ✅ {unused_test.name} correctly deleted")
        print(f"   ✅ {unused_fix.name} correctly deleted")
        print(f"   ✅ {used_test.name} preserved")
        print(f"   ✅ {main_file.name} preserved")
        
        # Step 5: Verify backups were created
        print(f"\n💾 Step 5: Verifying backups...")
        
        backup_dir = temp_dir / "cleanup_backups"
        assert backup_dir.exists(), "Backup directory should exist"
        
        backup_subdirs = list(backup_dir.iterdir())
        assert len(backup_subdirs) > 0, "Should have at least one backup subdirectory"
        
        # Check that backed up files exist
        backup_files = []
        for backup_subdir in backup_subdirs:
            backup_files.extend(list(backup_subdir.glob("**/*.py")))
        
        backup_names = [f.name for f in backup_files]
        assert "unused_test.py" in backup_names, "unused_test.py should be backed up"
        assert "old_fix_migration.py" in backup_names, "old_fix_migration.py should be backed up"
        
        print(f"   ✅ Backup directory created: {backup_dir}")
        print(f"   ✅ {len(backup_files)} files backed up")
        
        # Step 6: Test restore functionality
        print(f"\n🔄 Step 6: Testing restore functionality...")
        
        restore_cmd = [
            sys.executable, str(cleanup_script),
            "--root", str(temp_dir),
            "--restore", "unused_test.py"
        ]
        
        # Use echo to provide 'y' for overwrite confirmation
        restore_result = subprocess.run(
            restore_cmd,
            input="y\n",
            capture_output=True,
            text=True
        )
        
        print(f"   Restore exit code: {restore_result.returncode}")
        print(f"   Restore output: {restore_result.stdout}")
        
        # Verify file was restored
        assert unused_test.exists(), "unused_test.py should be restored"
        
        # Verify content is correct
        restored_content = unused_test.read_text()
        assert "test_unused_functionality" in restored_content
        
        print(f"   ✅ {unused_test.name} successfully restored")
        
        # Step 7: Test list-backups functionality
        print(f"\n📋 Step 7: Testing list-backups...")
        
        list_cmd = [
            sys.executable, str(cleanup_script),
            "--root", str(temp_dir),
            "--list-backups"
        ]
        
        list_result = subprocess.run(
            list_cmd,
            capture_output=True,
            text=True
        )
        
        print(f"   List exit code: {list_result.returncode}")
        print(f"   List output: {list_result.stdout}")
        
        assert "cleanup_backups" in list_result.stdout
        assert "files" in list_result.stdout
        
        print(f"   ✅ List backups working correctly")
        
        print(f"\n🎉 ALL END-TO-END TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n💥 TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up test directory")

def test_cleanup_interactive_mode():
    """Test interactive confirmation mode"""
    
    print(f"\n🧪 TESTING INTERACTIVE MODE")
    print("=" * 30)
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create test files
        unused1 = temp_dir / "unused1.py"
        unused1.write_text("def test1(): pass")
        
        unused2 = temp_dir / "unused2.py"
        unused2.write_text("def test2(): pass")
        
        cleanup_script = Path(__file__).parent / "ipcrawler_cleanup.py"
        
        # Test cancellation (respond with 'n' to all)
        cmd = [
            sys.executable, str(cleanup_script),
            "--root", str(temp_dir),
            "--remove-unused"
        ]
        
        # Simulate user responding 'n' (no to all)
        result = subprocess.run(
            cmd,
            input="n\n",
            capture_output=True,
            text=True
        )
        
        # Files should still exist (cancelled)
        assert unused1.exists()
        assert unused2.exists()
        
        print("   ✅ Interactive cancellation works")
        
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    success = test_cleanup_end_to_end()
    test_cleanup_interactive_mode()
    
    if success:
        print(f"\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print(f"\n💥 SOME TESTS FAILED!")
        sys.exit(1)