#!/usr/bin/env python3
"""Debug test to find where hang occurs"""

import sys
import tempfile
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

print("Starting debug test...")

try:
    print("1. Importing exceptions...")
    from workflows.core.exceptions import IPCrawlerError, ErrorSeverity, ErrorCategory, create_error_context
    print("   ✅ Exceptions imported")
    
    print("2. Creating error context...")
    context = create_error_context("test", "test", "test")
    print("   ✅ Context created")
    
    print("3. Creating error...")
    error = IPCrawlerError(
        message="Debug test error",
        error_code="DEBUG_TEST",
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.UNKNOWN,
        context=context
    )
    print("   ✅ Error created")
    
    print("4. Importing ErrorCollector...")
    from workflows.core.error_collector import ErrorCollector
    print("   ✅ ErrorCollector imported")
    
    print("5. Creating temp directory...")
    temp_dir = tempfile.mkdtemp()
    print(f"   ✅ Temp dir: {temp_dir}")
    
    print("6. Creating ErrorCollector instance...")
    collector = ErrorCollector(temp_dir)
    print("   ✅ ErrorCollector created")
    
    print("7. About to collect error...")
    sys.stdout.flush()  # Force output
    
except Exception as e:
    print(f"ERROR at step: {e}")
    import traceback
    traceback.print_exc()