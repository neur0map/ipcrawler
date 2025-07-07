#!/usr/bin/env python3
"""
Tests for file discovery system
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from file_discovery import find_unused_files, FileUsageAnalyzer

class TestFileDiscovery:
    """Test suite for file discovery functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, path: str, content: str = "") -> Path:
        """Helper to create test files"""
        file_path = self.temp_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path
    
    def test_finds_unused_test_file(self):
        """Test that unused test files are detected"""
        
        # Create an unused test file
        unused_test = self.create_test_file(
            "old_test.py", 
            '''
def test_old_functionality():
    """This test is no longer used"""
    assert True
'''
        )
        
        # Create a used test file (imported by main module)
        used_test = self.create_test_file(
            "test_current.py",
            '''
def test_current_functionality():
    """This test is actively used"""
    assert True
'''
        )
        
        # Create main module that imports the used test
        self.create_test_file(
            "main.py",
            '''
import test_current
from test_current import test_current_functionality

def main():
    test_current_functionality()
'''
        )
        
        # Run discovery
        unused_files = find_unused_files(str(self.temp_dir))
        
        # Verify results
        unused_names = [f.name for f in unused_files]
        assert "old_test.py" in unused_names
        assert "test_current.py" not in unused_names
    
    def test_finds_unused_fix_script(self):
        """Test that unused fix scripts are detected"""
        
        # Create unused fix script
        unused_fix = self.create_test_file(
            "old_fix_database.py",
            '''
#!/usr/bin/env python3
"""Old database fix that's no longer needed"""

def fix_database():
    print("Fixing database...")

if __name__ == "__main__":
    fix_database()
'''
        )
        
        # Create used fix script (referenced in docs)
        used_fix = self.create_test_file(
            "current_fix.py",
            '''
#!/usr/bin/env python3
"""Current fix script"""

def current_fix():
    print("Running current fix...")
'''
        )
        
        # Create documentation that references used fix
        self.create_test_file(
            "README.md",
            '''
# Project Documentation

To run the current fix, execute:

```bash
python3 current_fix.py
```

This will resolve the issue.
'''
        )
        
        # Run discovery
        unused_files = find_unused_files(str(self.temp_dir))
        
        # Verify results
        unused_names = [f.name for f in unused_files]
        assert "old_fix_database.py" in unused_names
        assert "current_fix.py" not in unused_names
    
    def test_respects_pytest_configuration(self):
        """Test that files in pytest testpaths are considered used"""
        
        # Create test file in configured test directory
        test_in_config = self.create_test_file(
            "tests/test_configured.py",
            '''
def test_in_configured_directory():
    assert True
'''
        )
        
        # Create test file outside configured directory
        test_outside_config = self.create_test_file(
            "old_test_outside.py",
            '''
def test_outside_configured_directory():
    assert True
'''
        )
        
        # Create pytest configuration
        self.create_test_file(
            "pytest.ini",
            '''
[tool:pytest]
testpaths = tests/
python_files = test_*.py
'''
        )
        
        # Run discovery
        unused_files = find_unused_files(str(self.temp_dir))
        
        # Verify results
        unused_names = [f.name for f in unused_files]
        assert "test_configured.py" not in unused_names  # In testpaths
        assert "old_test_outside.py" in unused_names     # Outside testpaths
    
    def test_respects_github_actions_workflow(self):
        """Test that files referenced in GitHub Actions are considered used"""
        
        # Create test file referenced in workflow
        workflow_test = self.create_test_file(
            "integration_test.py",
            '''
def test_integration():
    print("Running integration test")
'''
        )
        
        # Create test file not referenced in workflow
        unused_test = self.create_test_file(
            "unused_integration_test.py",
            '''
def test_unused_integration():
    print("This test is unused")
'''
        )
        
        # Create GitHub Actions workflow
        workflow_dir = self.temp_dir / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)
        
        workflow_file = workflow_dir / "ci.yml"
        workflow_file.write_text('''
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run integration tests
      run: |
        python3 integration_test.py
    - name: Run pytest
      run: |
        pytest tests/
''')
        
        # Run discovery
        unused_files = find_unused_files(str(self.temp_dir))
        
        # Verify results
        unused_names = [f.name for f in unused_files]
        assert "integration_test.py" not in unused_names      # Referenced in workflow
        assert "unused_integration_test.py" in unused_names   # Not referenced
    
    def test_finds_multiple_unused_files(self):
        """Test detection of multiple unused files"""
        
        # Create multiple unused files
        unused_files_data = [
            ("old_test_1.py", "def test_old_1(): pass"),
            ("old_test_2.py", "def test_old_2(): pass"),
            ("legacy_fix.py", "def legacy_fix(): pass"),
            ("deprecated_patch.py", "def patch(): pass"),
        ]
        
        for filename, content in unused_files_data:
            self.create_test_file(filename, content)
        
        # Create one used file
        self.create_test_file("test_active.py", "def test_active(): pass")
        self.create_test_file("main.py", "import test_active")
        
        # Run discovery
        unused_files = find_unused_files(str(self.temp_dir))
        
        # Verify all unused files are detected
        unused_names = set(f.name for f in unused_files)
        expected_unused = {"old_test_1.py", "old_test_2.py", "legacy_fix.py", "deprecated_patch.py"}
        
        assert expected_unused.issubset(unused_names)
        assert "test_active.py" not in unused_names
    
    def test_excludes_special_files(self):
        """Test that special files are never considered unused"""
        
        special_files = [
            "__init__.py",
            "conftest.py", 
            "setup.py",
            "main.py"
        ]
        
        for filename in special_files:
            self.create_test_file(filename, "# Special file")
        
        # Run discovery
        unused_files = find_unused_files(str(self.temp_dir))
        
        # Verify special files are not marked as unused
        unused_names = [f.name for f in unused_files]
        for special_file in special_files:
            assert special_file not in unused_names
    
    def test_handles_import_variations(self):
        """Test detection of various import patterns"""
        
        # Create test files with different import patterns
        self.create_test_file(
            "utils_test.py",
            "def test_utils(): pass"
        )
        
        self.create_test_file(
            "helper_test.py", 
            "def test_helper(): pass"
        )
        
        self.create_test_file(
            "unused_test.py",
            "def test_unused(): pass"
        )
        
        # Create file with various import patterns
        self.create_test_file(
            "main.py",
            '''
import utils_test
from helper_test import test_helper

def main():
    utils_test.test_utils()
    test_helper()
'''
        )
        
        # Run discovery
        unused_files = find_unused_files(str(self.temp_dir))
        
        # Verify import detection
        unused_names = [f.name for f in unused_files]
        assert "utils_test.py" not in unused_names    # Direct import
        assert "helper_test.py" not in unused_names   # From import
        assert "unused_test.py" in unused_names       # No import
    
    def test_analyzer_initialization(self):
        """Test FileUsageAnalyzer initialization"""
        
        analyzer = FileUsageAnalyzer(str(self.temp_dir))
        
        assert analyzer.root == self.temp_dir.resolve()
        assert isinstance(analyzer.imports, set)
        assert isinstance(analyzer.test_executions, set)
        assert isinstance(analyzer.doc_references, set)

def test_cli_integration(tmp_path):
    """Test CLI integration"""
    
    # Create test structure
    test_file = tmp_path / "old_test.py"
    test_file.write_text("def test_old(): pass")
    
    used_file = tmp_path / "current.py"
    used_file.write_text("def current(): pass")
    
    main_file = tmp_path / "main.py"
    main_file.write_text("import current")
    
    # Test find_unused_files function directly
    unused_files = find_unused_files(str(tmp_path))
    
    unused_names = [f.name for f in unused_files]
    assert "old_test.py" in unused_names
    assert "current.py" not in unused_names

if __name__ == "__main__":
    pytest.main([__file__, "-v"])