#!/usr/bin/env python3
"""
Test script for the enhanced error handling system in IPCrawler.

This script validates the new error hierarchy, collection system, and reporting features.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from workflows.core.exceptions import (
    IPCrawlerError, ToolExecutionError, NetworkError, ValidationError,
    ErrorSeverity, ErrorCategory, ErrorCodes, create_error_context
)
from workflows.core.error_collector import ErrorCollector, collect_error
from workflows.core.base import WorkflowResult
from workflows.core.error_reporter import ErrorReporter


def test_error_hierarchy():
    """Test the error hierarchy and structured errors"""
    print("🧪 Testing Error Hierarchy...")
    
    # Test basic IPCrawlerError
    context = create_error_context("test_workflow", "test_operation", "192.168.1.1")
    basic_error = IPCrawlerError(
        message="Test error message",
        error_code="TEST_ERROR",
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.UNKNOWN,
        context=context
    )
    
    assert basic_error.message == "Test error message"
    assert basic_error.error_code == "TEST_ERROR"
    assert basic_error.severity == ErrorSeverity.ERROR
    assert basic_error.category == ErrorCategory.UNKNOWN
    
    # Test specialized exceptions
    tool_error = ToolExecutionError(
        message="Tool execution failed",
        tool_name="nmap",
        error_code=ErrorCodes.TOOL_EXECUTION_FAILED,
        context=context
    )
    
    assert tool_error.tool_name == "nmap"
    assert tool_error.category == ErrorCategory.TOOL
    
    network_error = NetworkError(
        message="Connection timeout",
        error_code=ErrorCodes.NETWORK_TIMEOUT,
        context=context
    )
    
    assert network_error.category == ErrorCategory.NETWORK
    
    print("✅ Error hierarchy tests passed!")


def test_error_collection():
    """Test the error collection system"""
    print("🧪 Testing Error Collection System...")
    
    # Create temporary workspace for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        collector = ErrorCollector(temp_dir)
        
        # Test error collection
        context = create_error_context("test_workflow", "test_operation", "test.example.com")
        test_error = ToolExecutionError(
            message="Test tool failure",
            tool_name="test_tool",
            error_code="TEST_TOOL_ERROR",
            context=context,
            suggestions=["Check tool installation", "Verify permissions"]
        )
        
        # Collect the error
        occurrence_id = collector.collect_error(test_error)
        assert occurrence_id is not None
        
        # Test error retrieval
        errors = collector.get_errors()
        assert len(errors) == 1
        assert errors[0].error.message == "Test tool failure"
        
        # Test duplicate error handling
        occurrence_id2 = collector.collect_error(test_error)
        assert occurrence_id == occurrence_id2  # Should be same ID for duplicate
        
        errors = collector.get_errors()
        assert len(errors) == 1  # Still only one unique error
        assert errors[0].occurrence_count == 2  # But count increased
        
        # Test stats
        stats = collector.get_stats()
        assert stats.total_errors == 1
        assert stats.total_occurrences == 2
        
        # Test filtering
        tool_errors = collector.get_errors(category=ErrorCategory.TOOL)
        assert len(tool_errors) == 1
        
        network_errors = collector.get_errors(category=ErrorCategory.NETWORK)
        assert len(network_errors) == 0
        
        print("✅ Error collection tests passed!")


def test_workflow_result_integration():
    """Test WorkflowResult integration with error handling"""
    print("🧪 Testing WorkflowResult Integration...")
    
    # Test success result
    success_result = WorkflowResult.success_result(data={"test": "data"}, execution_time=1.5)
    assert success_result.success is True
    assert success_result.data == {"test": "data"}
    assert success_result.execution_time == 1.5
    assert len(success_result.error_details) == 0
    
    # Test error result with string
    error_result = WorkflowResult.error_result(
        error="Simple error message",
        workflow_name="test_workflow",
        operation="test_operation",
        target="test.target.com"
    )
    
    assert error_result.success is False
    assert error_result.error == "Simple error message"
    assert len(error_result.error_details) == 1
    assert error_result.error_details[0].workflow_name == "test_workflow"
    
    # Test error result with IPCrawlerError
    context = create_error_context("test_workflow", "test_operation", "test.target.com")
    structured_error = ValidationError(
        message="Invalid input parameter",
        error_code=ErrorCodes.INVALID_TARGET,
        context=context,
        suggestions=["Check input format", "Verify parameter values"]
    )
    
    structured_result = WorkflowResult.error_result(
        error=structured_error,
        workflow_name="test_workflow",
        operation="test_operation"
    )
    
    assert structured_result.success is False
    assert len(structured_result.error_details) == 1
    detail = structured_result.error_details[0]
    assert detail.error_code == ErrorCodes.INVALID_TARGET
    assert detail.category == ErrorCategory.VALIDATION.value
    assert len(detail.suggestions) == 2
    
    # Test backward compatibility
    legacy_format = structured_result.to_legacy_format()
    assert "success" in legacy_format
    assert "error" in legacy_format
    assert "errors" in legacy_format
    
    print("✅ WorkflowResult integration tests passed!")


def test_error_reporting():
    """Test error reporting and analysis"""
    print("🧪 Testing Error Reporting...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test errors
        collector = ErrorCollector(temp_dir)
        
        # Add various types of errors
        errors_to_add = [
            ToolExecutionError(
                message="Nmap execution failed",
                tool_name="nmap",
                error_code=ErrorCodes.TOOL_EXECUTION_FAILED,
                context=create_error_context("nmap", "scan", "192.168.1.1")
            ),
            NetworkError(
                message="Connection timeout",
                error_code=ErrorCodes.NETWORK_TIMEOUT,
                context=create_error_context("http_scanner", "connect", "example.com")
            ),
            ValidationError(
                message="Invalid target format",
                error_code=ErrorCodes.INVALID_TARGET,
                context=create_error_context("input_validator", "validate", "invalid_target")
            )
        ]
        
        for error in errors_to_add:
            collector.collect_error(error)
            # Add each error multiple times to test frequency
            collector.collect_error(error)
        
        # Test error reporter
        reporter = ErrorReporter(temp_dir)
        summary = reporter.generate_workspace_summary()
        
        # Validate summary structure
        assert "summary" in summary
        assert "severity_breakdown" in summary
        assert "category_analysis" in summary
        assert "workflow_impact" in summary
        assert "recommendations" in summary
        
        # Check that we have the expected errors
        assert summary["summary"]["total_unique_errors"] == 3
        assert summary["summary"]["total_occurrences"] == 6  # Each error added twice
        
        # Test category breakdown
        categories = summary["category_analysis"]["distribution"]
        assert categories[ErrorCategory.TOOL.value] == 2
        assert categories[ErrorCategory.NETWORK.value] == 2
        assert categories[ErrorCategory.VALIDATION.value] == 2
        
        # Test human-readable report generation
        readable_report = reporter.generate_human_readable_report()
        assert "IPCrawler Workspace Error Analysis Report" in readable_report
        assert "Executive Summary" in readable_report
        assert "Recommendations" in readable_report
        
        print("✅ Error reporting tests passed!")


async def test_integration_example():
    """Test a complete integration example"""
    print("🧪 Testing Complete Integration Example...")
    
    # Simulate a workflow that encounters errors
    class TestWorkflow:
        def __init__(self):
            self.name = "test_integration_workflow"
        
        def create_error_result(self, error, operation, target=None, **kwargs):
            return WorkflowResult.error_result(
                error=error,
                workflow_name=self.name,
                operation=operation,
                target=target,
                **kwargs
            )
    
    workflow = TestWorkflow()
    
    # Simulate various error scenarios
    try:
        # Simulate a tool failure
        raise FileNotFoundError("Tool not found: /usr/bin/nmap")
    except FileNotFoundError as e:
        result1 = workflow.create_error_result(
            error=e,
            operation="tool_check",
            target="192.168.1.1"
        )
        
        assert not result1.success
        assert len(result1.error_details) == 1
        assert result1.error_details[0].category == ErrorCategory.FILESYSTEM.value
    
    try:
        # Simulate a network error
        raise ConnectionError("Connection refused")
    except ConnectionError as e:
        result2 = workflow.create_error_result(
            error=e,
            operation="network_scan",
            target="unreachable.host.com"
        )
        
        assert not result2.success
        assert len(result2.error_details) == 1
        assert result2.error_details[0].category == ErrorCategory.NETWORK.value
    
    # Test success case
    success_result = WorkflowResult.success_result(
        data={"hosts": ["192.168.1.1"], "ports": [80, 443]},
        execution_time=2.3
    )
    
    assert success_result.success
    assert success_result.data["hosts"] == ["192.168.1.1"]
    assert len(success_result.error_details) == 0
    
    print("✅ Integration example tests passed!")


def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Error Handling System Tests\n")
    
    try:
        test_error_hierarchy()
        print()
        
        test_error_collection()
        print()
        
        test_workflow_result_integration()
        print()
        
        test_error_reporting()
        print()
        
        asyncio.run(test_integration_example())
        print()
        
        print("🎉 All tests passed! Enhanced error handling system is working correctly.")
        
        # Demonstrate the system with a final example
        print("\n📊 Demo: Generating sample error report...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample errors
            collector = ErrorCollector(temp_dir)
            
            sample_errors = [
                NetworkError(
                    message="DNS resolution failed for target",
                    error_code=ErrorCodes.DNS_RESOLUTION_FAILED,
                    context=create_error_context("dns_resolver", "resolve", "nonexistent.domain.com"),
                    suggestions=["Check DNS configuration", "Verify domain exists"]
                ),
                ToolExecutionError(
                    message="Nmap scan timed out",
                    tool_name="nmap",
                    error_code=ErrorCodes.TOOL_TIMEOUT,
                    context=create_error_context("nmap_scanner", "full_scan", "192.168.1.100"),
                    suggestions=["Reduce scan scope", "Increase timeout values"]
                )
            ]
            
            for error in sample_errors:
                for _ in range(3):  # Simulate multiple occurrences
                    collector.collect_error(error)
            
            # Generate reports
            reporter = ErrorReporter(temp_dir)
            
            # Save JSON report
            json_file = reporter.save_workspace_report()
            if json_file:
                print(f"📄 JSON report saved: {json_file}")
            
            # Save human-readable report
            md_file = reporter.save_human_readable_report()
            if md_file:
                print(f"📋 Readable report saved: {md_file}")
                
                # Show a snippet of the readable report
                with open(md_file, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    print("\n📖 Sample from readable report:")
                    print("=" * 50)
                    for line in lines[:15]:  # Show first 15 lines
                        print(line)
                    print("...")
                    print("=" * 50)
        
        print("\n✨ Enhanced error handling system demonstration complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()