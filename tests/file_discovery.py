#!/usr/bin/env python3
"""
File Discovery System - Find unused test files and fix scripts
"""

import ast
import re
import subprocess
from pathlib import Path
from typing import List, Set, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class FileUsageAnalyzer:
    """Analyzes file usage patterns to identify orphan files"""
    
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.python_files = set()
        self.imports = set()
        self.test_executions = set()
        self.doc_references = set()
        
    def find_unused_files(self, root: str) -> List[Path]:
        """
        Find unused test files and fix scripts
        
        Args:
            root: Root directory to scan
            
        Returns:
            List of unused file paths
        """
        root_path = Path(root).resolve()
        
        # Find all target files (test files and fix scripts)
        target_files = self._find_target_files(root_path)
        
        # Analyze usage patterns
        self._analyze_imports(root_path)
        self._analyze_test_executions(root_path)
        self._analyze_documentation_references(root_path)
        self._analyze_git_history(root_path)
        
        # Determine which files are unused
        unused_files = []
        for file_path in target_files:
            if not self._is_file_used(file_path):
                unused_files.append(file_path)
        
        return sorted(unused_files)
    
    def _find_target_files(self, root_path: Path) -> List[Path]:
        """Find all test files and fix scripts"""
        
        target_files = []
        
        # Pattern 1: Test files
        test_patterns = [
            "test_*.py",
            "*_test.py", 
            "tests.py",
            "**/test_*.py",
            "**/tests/*.py"
        ]
        
        # Pattern 2: Fix/patch scripts
        fix_patterns = [
            "*fix*.py",
            "*patch*.py",
            "*repair*.py",
            "*cleanup*.py",
            "*migration*.py"
        ]
        
        all_patterns = test_patterns + fix_patterns
        
        for pattern in all_patterns:
            for file_path in root_path.glob(pattern):
                if file_path.is_file() and file_path.suffix == '.py':
                    target_files.append(file_path)
        
        logger.debug(f"Found {len(target_files)} target files")
        return target_files
    
    def _analyze_imports(self, root_path: Path) -> None:
        """Analyze Python imports to find file dependencies"""
        
        for py_file in root_path.glob("**/*.py"):
            if py_file.is_file():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse AST to find imports
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                self.imports.add(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                self.imports.add(node.module)
                                for alias in node.names:
                                    full_name = f"{node.module}.{alias.name}"
                                    self.imports.add(full_name)
                
                except (SyntaxError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not parse {py_file}: {e}")
    
    def _analyze_test_executions(self, root_path: Path) -> None:
        """Analyze test execution patterns from CI/pytest configs"""
        
        # Check pytest configuration
        pytest_configs = [
            root_path / "pytest.ini",
            root_path / "pyproject.toml",
            root_path / "setup.cfg",
            root_path / "tox.ini"
        ]
        
        for config_file in pytest_configs:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                    
                    # Find test paths in configuration
                    test_paths = re.findall(r'testpaths\s*=\s*(.+)', content)
                    for path_line in test_paths:
                        paths = re.findall(r'\S+', path_line)
                        self.test_executions.update(paths)
                
                except Exception as e:
                    logger.warning(f"Could not read {config_file}: {e}")
        
        # Check GitHub Actions workflows
        workflows_dir = root_path / ".github" / "workflows"
        if workflows_dir.exists():
            for workflow_file in workflows_dir.glob("*.yml"):
                try:
                    with open(workflow_file, 'r') as f:
                        content = f.read()
                    
                    # Find pytest/python test commands
                    test_commands = re.findall(r'pytest\s+([^\s\n]+)', content)
                    self.test_executions.update(test_commands)
                    
                    # Find direct python executions
                    python_commands = re.findall(r'python3?\s+([^\s\n]+\.py)', content)
                    self.test_executions.update(python_commands)
                
                except Exception as e:
                    logger.warning(f"Could not read {workflow_file}: {e}")
    
    def _analyze_documentation_references(self, root_path: Path) -> None:
        """Find file references in documentation"""
        
        doc_patterns = ["*.md", "*.rst", "*.txt", "docs/**/*"]
        
        for pattern in doc_patterns:
            for doc_file in root_path.glob(pattern):
                if doc_file.is_file():
                    try:
                        with open(doc_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Find Python file references
                        py_refs = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*\.py)', content)
                        self.doc_references.update(py_refs)
                        
                        # Find code block references
                        code_refs = re.findall(r'```(?:python|bash)\n.*?python3?\s+([^\s\n]+\.py)', content, re.DOTALL)
                        self.doc_references.update(code_refs)
                    
                    except Exception as e:
                        logger.warning(f"Could not read {doc_file}: {e}")
    
    def _analyze_git_history(self, root_path: Path) -> None:
        """Check if files have recent git activity"""
        
        try:
            # Get recently modified files (last 30 days)
            result = subprocess.run([
                'git', 'log', '--since=30.days.ago', '--name-only', '--pretty=format:'
            ], cwd=root_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                recent_files = set(result.stdout.strip().split('\n'))
                self.test_executions.update(recent_files)
        
        except subprocess.SubprocessError:
            logger.warning("Could not analyze git history")
    
    def _is_file_used(self, file_path: Path) -> bool:
        """Determine if a file is used based on various criteria"""
        
        file_name = file_path.name
        stem = file_path.stem
        relative_path = str(file_path.relative_to(self.root))
        
        # Check 1: Direct import references
        if any(imp in [stem, file_name, relative_path] for imp in self.imports):
            return True
        
        # Check 2: Module path imports (e.g., test.module_name)
        module_parts = file_path.relative_to(self.root).parts[:-1] + (stem,)
        module_path = '.'.join(module_parts)
        if module_path in self.imports:
            return True
        
        # Check 3: Test execution patterns
        if any(exec_path in relative_path for exec_path in self.test_executions):
            return True
        
        # Check 4: Documentation references
        if file_name in self.doc_references:
            return True
        
        # Check 5: Special patterns (always considered used)
        special_patterns = [
            '__init__.py',
            'conftest.py',
            'setup.py',
            'main.py'
        ]
        
        if file_name in special_patterns:
            return True
        
        # Check 6: Files in active test directories
        active_test_dirs = {'tests', 'test', 'testing'}
        if any(part in active_test_dirs for part in file_path.parts):
            # If it's in a test directory, check if the directory is referenced
            test_dir = None
            for part in file_path.parts:
                if part in active_test_dirs:
                    test_dir = part
                    break
            
            if test_dir and any(test_dir in exec_path for exec_path in self.test_executions):
                return True
        
        return False

def find_unused_files(root: str) -> List[Path]:
    """
    Main function to find unused test files and fix scripts
    
    Args:
        root: Root directory to scan
        
    Returns:
        List of unused file paths
    """
    analyzer = FileUsageAnalyzer(root)
    return analyzer.find_unused_files(root)

# Convenience function for CLI usage
def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Find unused test files and fix scripts")
    parser.add_argument('root', help='Root directory to scan')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    unused_files = find_unused_files(args.root)
    
    print(f"Found {len(unused_files)} unused files:")
    for file_path in unused_files:
        print(f"  {file_path}")

if __name__ == "__main__":
    main()