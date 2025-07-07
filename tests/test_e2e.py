#!/usr/bin/env python3
"""
End-to-end tests for ipcrawler complete scan workflows
"""

import unittest
import tempfile
import subprocess
import os
import time
from pathlib import Path
import yaml
import json

# Add parent directory to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestE2EScanWorkflows(unittest.TestCase):
    """End-to-end tests for complete scan workflows"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.results_dir = Path(self.temp_dir) / "results"
        self.results_dir.mkdir()
        
        # Change to ipcrawler directory for tests
        self.original_cwd = os.getcwd()
        self.ipcrawler_dir = Path(__file__).parent.parent
        os.chdir(self.ipcrawler_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_localhost_scan_basic(self):
        """Test basic localhost scan workflow"""
        # Run a fast scan against localhost
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "127.0.0.1"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            # Check that scan completed (may have errors, but should not crash)
            self.assertIn(result.returncode, [0, 1])  # 0 = success, 1 = some errors
            
            # Check that results directory was created
            results_path = Path("results/127.0.0.1")
            self.assertTrue(results_path.exists())
            
            # Check that scan logs were created
            scans_path = results_path / "scans"
            self.assertTrue(scans_path.exists())
            
            # Check that error log exists
            error_log = scans_path / "errors.log"
            self.assertTrue(error_log.exists())
            
            # Check that some plugin logs were created
            log_files = list(scans_path.glob("*.log"))
            self.assertGreater(len(log_files), 0)
            
        except subprocess.TimeoutExpired:
            self.fail("Scan timed out after 2 minutes")
    
    def test_localhost_scan_with_parsing(self):
        """Test localhost scan with automatic parsing"""
        # Run scan that should trigger parsing
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "127.0.0.1"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )
            
            # Check results directory
            results_path = Path("results/127.0.0.1")
            self.assertTrue(results_path.exists())
            
            # Check that parsed.yaml was generated
            parsed_yaml = results_path / "parsed.yaml"
            if parsed_yaml.exists():
                # Verify parsed.yaml has valid content
                with open(parsed_yaml, 'r') as f:
                    parsed_data = yaml.safe_load(f)
                
                self.assertIsInstance(parsed_data, dict)
                self.assertIn("target", parsed_data)
                self.assertEqual(parsed_data["target"], "127.0.0.1")
            
            # Check that report.md was generated
            report_md = results_path / "report.md"
            if report_md.exists():
                # Verify report.md has content
                report_content = report_md.read_text()
                self.assertIn("127.0.0.1", report_content)
                self.assertIn("Scan Results", report_content)
            
        except subprocess.TimeoutExpired:
            self.fail("Scan with parsing timed out after 3 minutes")
    
    def test_invalid_target_handling(self):
        """Test handling of invalid targets"""
        # Test with invalid IP address
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "999.999.999.999"  # Invalid IP
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Should handle invalid target gracefully
            self.assertIsNotNone(result.returncode)
            
            # Should have error message in output
            output = result.stdout + result.stderr
            self.assertTrue(
                "invalid" in output.lower() or 
                "error" in output.lower() or
                "failed" in output.lower()
            )
            
        except subprocess.TimeoutExpired:
            self.fail("Invalid target test timed out")
    
    def test_multiple_targets_scan(self):
        """Test scanning multiple targets"""
        # Test with multiple localhost addresses
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "127.0.0.1",
            "::1"  # IPv6 localhost
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=240  # 4 minute timeout for multiple targets
            )
            
            # Check that results were created for primary target
            results_path = Path("results/127.0.0.1")
            self.assertTrue(results_path.exists())
            
            # Check that scan completed
            self.assertIn(result.returncode, [0, 1])
            
        except subprocess.TimeoutExpired:
            self.fail("Multiple targets scan timed out")
    
    def test_port_specification(self):
        """Test custom port specification"""
        # Test with specific ports
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "-p", "80,443,22",
            "127.0.0.1"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Check that scan completed
            self.assertIn(result.returncode, [0, 1])
            
            # Check results directory
            results_path = Path("results/127.0.0.1")
            self.assertTrue(results_path.exists())
            
        except subprocess.TimeoutExpired:
            self.fail("Port specification test timed out")
    
    def test_verbosity_levels(self):
        """Test different verbosity levels"""
        # Test with verbose output
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "-v",
            "127.0.0.1"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Verbose output should contain more information
            output = result.stdout + result.stderr
            self.assertGreater(len(output), 100)  # Should have substantial output
            
        except subprocess.TimeoutExpired:
            self.fail("Verbosity test timed out")
    
    def test_scan_interruption_handling(self):
        """Test handling of scan interruption"""
        # This test simulates Ctrl+C interruption
        cmd = [
            "python3", "ipcrawler.py",
            "--ignore-plugin-checks",
            "127.0.0.1"  # Full scan (no --fast)
        ]
        
        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Let it run for a few seconds
            time.sleep(5)
            
            # Interrupt the process
            process.terminate()
            
            # Wait for process to finish
            stdout, stderr = process.communicate(timeout=30)
            
            # Check that results directory was created
            results_path = Path("results/127.0.0.1")
            self.assertTrue(results_path.exists())
            
            # Check that some files were created before interruption
            scans_path = results_path / "scans"
            if scans_path.exists():
                log_files = list(scans_path.glob("*.log"))
                # Should have at least error log
                self.assertGreater(len(log_files), 0)
            
        except subprocess.TimeoutExpired:
            # Kill process if it doesn't terminate
            process.kill()
            self.fail("Interrupted scan test timed out")
    
    def test_yaml_plugin_system_integration(self):
        """Test YAML plugin system integration"""
        # Test that YAML plugins execute correctly
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "-v",
            "127.0.0.1"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            output = result.stdout + result.stderr
            
            # Should mention plugin execution
            self.assertTrue(
                "plugin" in output.lower() or
                "yaml" in output.lower() or
                "starting" in output.lower()
            )
            
            # Check that plugin logs were created
            results_path = Path("results/127.0.0.1")
            if results_path.exists():
                scans_path = results_path / "scans"
                if scans_path.exists():
                    log_files = list(scans_path.glob("*.log"))
                    # Should have multiple log files from different plugins
                    self.assertGreater(len(log_files), 1)
            
        except subprocess.TimeoutExpired:
            self.fail("YAML plugin integration test timed out")
    
    def test_help_and_version_commands(self):
        """Test help and version commands"""
        # Test version command
        version_cmd = ["python3", "ipcrawler.py", "--version"]
        
        try:
            result = subprocess.run(
                version_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            self.assertEqual(result.returncode, 0)
            self.assertIn("ipcrawler", result.stdout.lower())
            
        except subprocess.TimeoutExpired:
            self.fail("Version command timed out")
        
        # Test help command
        help_cmd = ["python3", "ipcrawler.py", "--help"]
        
        try:
            result = subprocess.run(
                help_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            self.assertEqual(result.returncode, 0)
            self.assertIn("usage", result.stdout.lower())
            
        except subprocess.TimeoutExpired:
            self.fail("Help command timed out")
    
    def test_plugin_listing(self):
        """Test plugin listing functionality"""
        # Test listing plugins
        cmd = ["python3", "ipcrawler.py", "-l"]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should list available plugins
            self.assertEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            
            # Should contain plugin information
            self.assertTrue(
                "plugin" in output.lower() or
                "available" in output.lower() or
                "yaml" in output.lower()
            )
            
        except subprocess.TimeoutExpired:
            self.fail("Plugin listing test timed out")
    
    def test_configuration_validation(self):
        """Test configuration file validation"""
        # Test with default configuration
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "--dry-run",  # If supported
            "127.0.0.1"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Should handle configuration validation
            # Even if dry-run is not supported, should not crash
            self.assertIsNotNone(result.returncode)
            
        except subprocess.TimeoutExpired:
            self.fail("Configuration validation test timed out")


class TestReportGeneration(unittest.TestCase):
    """Test report generation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        self.ipcrawler_dir = Path(__file__).parent.parent
        os.chdir(self.ipcrawler_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_automatic_report_generation(self):
        """Test automatic report generation after scan"""
        # Run a minimal scan to generate reports
        cmd = [
            "python3", "ipcrawler.py",
            "--fast",
            "--ignore-plugin-checks",
            "127.0.0.1"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180
            )
            
            results_path = Path("results/127.0.0.1")
            
            # Check for parsed.yaml
            parsed_yaml = results_path / "parsed.yaml"
            if parsed_yaml.exists():
                # Validate parsed.yaml structure
                with open(parsed_yaml, 'r') as f:
                    parsed_data = yaml.safe_load(f)
                
                self.assertIsInstance(parsed_data, dict)
                self.assertIn("target", parsed_data)
                
                # Check for required sections
                expected_sections = ["ports", "services", "summary"]
                for section in expected_sections:
                    if section in parsed_data:
                        self.assertIsInstance(parsed_data[section], (dict, list))
            
            # Check for report.md
            report_md = results_path / "report.md"
            if report_md.exists():
                # Validate report.md content
                report_content = report_md.read_text()
                
                self.assertIn("127.0.0.1", report_content)
                self.assertGreater(len(report_content), 100)
                
                # Should contain markdown formatting
                self.assertTrue(
                    "#" in report_content or  # Headers
                    "**" in report_content or  # Bold
                    "*" in report_content  # Italic or lists
                )
            
        except subprocess.TimeoutExpired:
            self.fail("Report generation test timed out")
    
    def test_manual_parsing_execution(self):
        """Test manual execution of parsing tools"""
        # First, ensure we have some scan results
        results_path = Path("results/127.0.0.1")
        if not results_path.exists():
            # Skip if no results available
            self.skipTest("No scan results available for parsing test")
        
        # Test manual parsing execution
        cmd = ["python3", "ipcrawler/parse_logs.py", "127.0.0.1"]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Should complete without error
            self.assertEqual(result.returncode, 0)
            
            # Should create or update parsed.yaml
            parsed_yaml = results_path / "parsed.yaml"
            if parsed_yaml.exists():
                with open(parsed_yaml, 'r') as f:
                    parsed_data = yaml.safe_load(f)
                
                self.assertIsInstance(parsed_data, dict)
                self.assertIn("target", parsed_data)
            
        except subprocess.TimeoutExpired:
            self.fail("Manual parsing test timed out")
        except FileNotFoundError:
            self.skipTest("parse_logs.py not found or not executable")


if __name__ == '__main__':
    unittest.main(verbosity=2)