#!/usr/bin/env python3
"""Test file operations for error handling system"""

import sys
import tempfile
import json
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_file_operations():
    print("🧪 Testing file operations...")
    
    from workflows.core.exceptions import (
        IPCrawlerError, ErrorSeverity, ErrorCategory, create_error_context
    )
    from workflows.core.error_collector import ErrorCollector
    
    # Test with explicit temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp directory: {temp_dir}")
        
        # Create error collector with explicit workspace
        collector = ErrorCollector(temp_dir)
        print("✅ Error collector created")
        
        # Create a simple error
        context = create_error_context("test", "test", "test")
        error = IPCrawlerError(
            message="File test error",
            error_code="FILE_TEST",
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.UNKNOWN,
            context=context
        )
        print("✅ Error created")
        
        # Test collection
        print("Collecting error...")
        occurrence_id = collector.collect_error(error)
        print(f"✅ Error collected with ID: {occurrence_id}")
        
        # Test retrieval
        errors = collector.get_errors()
        print(f"✅ Retrieved {len(errors)} errors")
        
        # Check files were created
        errors_file = Path(temp_dir) / "errors.json"
        summary_file = Path(temp_dir) / "error_summary.json"
        
        if errors_file.exists():
            print("✅ Errors file created")
            with open(errors_file) as f:
                data = json.load(f)
                print(f"✅ Errors file contains {len(data.get('errors', []))} errors")
        
        if summary_file.exists():
            print("✅ Summary file created")
    
    print("🎉 File operations test completed!")

if __name__ == "__main__":
    test_file_operations()