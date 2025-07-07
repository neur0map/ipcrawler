#!/usr/bin/env python3
"""
Manual test for file discovery (without pytest)
"""

import tempfile
import shutil
from pathlib import Path
from file_discovery import find_unused_files

def test_finds_unused_files():
    """Manual test that demonstrates unused file detection"""
    
    print("🧪 TESTING FILE DISCOVERY SYSTEM")
    print("=" * 40)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"📁 Test directory: {temp_dir}")
    
    try:
        # Create unused test file (should be detected)
        old_test = temp_dir / "old_test.py"
        old_test.write_text('''
def test_old_functionality():
    """This test is no longer used"""
    assert True

def another_old_test():
    pass
''')
        
        # Create used test file (should NOT be detected)
        current_test = temp_dir / "test_current.py"
        current_test.write_text('''
def test_current_functionality():
    """This test is actively used"""
    assert True
''')
        
        # Create main module that imports the used test
        main_file = temp_dir / "main.py"
        main_file.write_text('''
import test_current
from test_current import test_current_functionality

def main():
    test_current_functionality()
    print("Running main")

if __name__ == "__main__":
    main()
''')
        
        # Create unused fix script (should be detected)
        old_fix = temp_dir / "legacy_fix_database.py"
        old_fix.write_text('''
#!/usr/bin/env python3
"""Legacy database fix that's no longer needed"""

def fix_old_database():
    print("Fixing old database structure...")

if __name__ == "__main__":
    fix_old_database()
''')
        
        # Create used fix script (referenced in docs)
        current_fix = temp_dir / "current_migration.py"
        current_fix.write_text('''
#!/usr/bin/env python3
"""Current migration script"""

def run_migration():
    print("Running current migration...")
''')
        
        # Create documentation that references used fix
        readme = temp_dir / "README.md"
        readme.write_text('''
# Project Documentation

## Running Migrations

To run the current migration, execute:

```bash
python3 current_migration.py
```

This will update the database schema.
''')
        
        # Create pytest configuration
        pytest_ini = temp_dir / "pytest.ini"
        pytest_ini.write_text('''
[tool:pytest]
testpaths = tests/
python_files = test_*.py
''')
        
        # Create test in configured directory (should NOT be detected)
        tests_dir = temp_dir / "tests"
        tests_dir.mkdir()
        configured_test = tests_dir / "test_configured.py"
        configured_test.write_text('''
def test_in_configured_directory():
    """Test in pytest testpaths"""
    assert True
''')
        
        print("\n📄 Created test files:")
        print(f"   ❌ {old_test.name} - unused test")
        print(f"   ✅ {current_test.name} - used test (imported)")
        print(f"   ✅ {main_file.name} - main module")
        print(f"   ❌ {old_fix.name} - unused fix script")
        print(f"   ✅ {current_fix.name} - used fix (documented)")
        print(f"   ✅ {readme.name} - documentation")
        print(f"   ✅ {configured_test} - test in pytest testpaths")
        
        # Run file discovery
        print(f"\n🔍 Running file discovery...")
        unused_files = find_unused_files(str(temp_dir))
        
        print(f"\n📊 RESULTS:")
        print(f"   Found {len(unused_files)} unused files")
        
        unused_names = [f.name for f in unused_files]
        
        for unused_file in unused_files:
            print(f"   ❌ UNUSED: {unused_file.name}")
        
        # Verify expected results
        print(f"\n✅ VERIFICATION:")
        
        expected_unused = ["old_test.py", "legacy_fix_database.py"]
        expected_used = ["test_current.py", "main.py", "current_migration.py", "test_configured.py"]
        
        success = True
        
        for expected in expected_unused:
            if expected in unused_names:
                print(f"   ✅ Correctly identified unused: {expected}")
            else:
                print(f"   ❌ Failed to identify unused: {expected}")
                success = False
        
        for expected in expected_used:
            if expected not in unused_names:
                print(f"   ✅ Correctly identified used: {expected}")
            else:
                print(f"   ❌ Incorrectly marked as unused: {expected}")
                success = False
        
        if success:
            print(f"\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n💥 SOME TESTS FAILED!")
        
        return success
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up test directory")

if __name__ == "__main__":
    test_finds_unused_files()