#!/usr/bin/env python3
"""
Simulate CI cleanup check - shows what happens when orphan files are detected
"""

import tempfile
import shutil
import subprocess
import sys
from pathlib import Path

def simulate_ci_cleanup_check():
    """Simulate the GitHub Actions cleanup check"""
    
    print("🔬 SIMULATING CI CLEANUP CHECK")
    print("=" * 40)
    
    # Create temporary directory with orphan files
    temp_dir = Path(tempfile.mkdtemp())
    print(f"📁 Test repository: {temp_dir}")
    
    try:
        # Create project structure with orphan files
        print(f"\n📝 Creating test repository with orphan files...")
        
        # Create legitimate project files
        main_file = temp_dir / "main.py"
        main_file.write_text('''
#!/usr/bin/env python3
"""Main application"""

def main():
    print("IPCrawler running...")

if __name__ == "__main__":
    main()
''')
        
        active_test = temp_dir / "test_main.py"
        active_test.write_text('''
import main

def test_main():
    """Test main functionality"""
    main.main()
''')
        
        # Create ORPHAN files (should be detected)
        old_fix = temp_dir / "old_fix.py"
        old_fix.write_text('''
#!/usr/bin/env python3
"""Old fix script that's no longer needed"""

def old_fix():
    print("Running old fix...")

if __name__ == "__main__":
    old_fix()
''')
        
        legacy_test = temp_dir / "legacy_test.py"
        legacy_test.write_text('''
def test_legacy_functionality():
    """This test is for removed functionality"""
    assert True
''')
        
        abandoned_migration = temp_dir / "migration_v1_to_v2.py"
        abandoned_migration.write_text('''
#!/usr/bin/env python3
"""Old migration that was superseded"""

def migrate_v1_to_v2():
    print("Migrating v1 to v2...")
''')
        
        print(f"   ✅ Created main.py (legitimate)")
        print(f"   ✅ Created test_main.py (legitimate)")
        print(f"   ❌ Created old_fix.py (ORPHAN)")
        print(f"   ❌ Created legacy_test.py (ORPHAN)")
        print(f"   ❌ Created migration_v1_to_v2.py (ORPHAN)")
        
        # Simulate CI cleanup check
        print(f"\n🔍 Running CI cleanup check...")
        
        cleanup_script = Path(__file__).parent / "ipcrawler_cleanup.py"
        
        # Run cleanup dry-run (as CI would)
        cmd = [
            sys.executable, str(cleanup_script),
            "--root", str(temp_dir),
            "--dry-run"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        print(f"   Exit code: {result.returncode}")
        
        # Show CI output format
        print(f"\n📋 CI OUTPUT:")
        print("=" * 50)
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Simulate CI logic for detecting orphans
        print(f"\n🤖 CI LOGIC SIMULATION:")
        print("=" * 30)
        
        has_orphans = False
        orphan_count = 0
        
        if "Found" in result.stdout and "unused files" in result.stdout:
            # Extract count
            import re
            match = re.search(r'Found (\d+) unused files', result.stdout)
            if match:
                orphan_count = int(match.group(1))
                has_orphans = True
        
        print(f"has_orphans: {has_orphans}")
        print(f"orphan_count: {orphan_count}")
        
        # Simulate CI decision
        print(f"\n🎭 CI JOB RESULT:")
        print("=" * 20)
        
        if has_orphans:
            print("❌ CLEANUP CHECK FAILED")
            print(f"")
            print(f"Found {orphan_count} orphan files that should be cleaned up.")
            print(f"")
            print(f"To fix this issue:")
            print(f"1. Review the files listed above")
            print(f"2. Remove unused files: python3 ipcrawler_cleanup.py --remove-unused")
            print(f"3. Or exclude them if they should be kept (add to .cleanup_ignore)")
            print(f"")
            print(f"For more details, see the cleanup report artifact.")
            
            # Show what specific files were detected
            print(f"\n📄 ORPHAN FILES DETECTED:")
            lines = result.stdout.split('\n')
            for line in lines:
                if '❌' in line and '.py' in line:
                    print(f"   {line.strip()}")
            
            return 1  # CI would fail
            
        else:
            print("✅ CLEANUP CHECK PASSED")
            print("")
            print("No orphan files detected - repository is clean!")
            print("Good job maintaining file hygiene! 🎉")
            
            return 0  # CI would pass
    
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up test repository")

def show_sample_ci_outputs():
    """Show sample CI outputs for different scenarios"""
    
    print(f"\n📋 SAMPLE CI OUTPUTS")
    print("=" * 25)
    
    print(f"\n✅ PASSING CI OUTPUT:")
    print("-" * 20)
    print("""
🔍 Scanning for unused files...
✅ No unused files found!

✅ FILE HYGIENE CHECK PASSED

No orphan files detected - repository is clean!
Good job maintaining file hygiene! 🎉
""")
    
    print(f"\n❌ FAILING CI OUTPUT:")
    print("-" * 20)
    print("""
🔍 Scanning for unused files...

📊 Found 3 unused files:
   ❌ old_fix.py (245 bytes)
   ❌ legacy_test.py (123 bytes)
   ❌ migration_v1_to_v2.py (156 bytes)

🔍 DRY RUN: Would delete 3 files

❌ ORPHAN FILES DETECTED!

Found 3 orphan files that should be cleaned up.

To fix this issue:
1. Review the files listed above
2. Remove unused files: python3 ipcrawler_cleanup.py --remove-unused
3. Or exclude them if they should be kept (add to .cleanup_ignore)

For more details, see the cleanup report artifact.
""")
    
    print(f"\n📊 PATTERN ANALYSIS OUTPUT:")
    print("-" * 30)
    print("""
📊 CLEANUP PATTERN ANALYSIS
==========================
Analyzing cleanup output...
Test files: 1
Fix scripts: 1
Migration scripts: 1
""")

if __name__ == "__main__":
    exit_code = simulate_ci_cleanup_check()
    show_sample_ci_outputs()
    
    print(f"\n🏁 SIMULATION COMPLETE")
    print(f"Exit code: {exit_code}")
    
    if exit_code == 0:
        print("✅ CI would PASS - no orphan files")
    else:
        print("❌ CI would FAIL - orphan files detected")