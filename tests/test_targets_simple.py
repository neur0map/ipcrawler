#!/usr/bin/env python3
"""
Simplified unit tests for ipcrawler.targets module
"""

import unittest
from unittest.mock import Mock

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ipcrawler.targets import Target


class TestTarget(unittest.TestCase):
    """Test Target class functionality"""
    
    def test_target_initialization(self):
        """Test Target object initialization"""
        # Create a mock ipcrawler object
        mock_ipcrawler = Mock()
        
        target = Target("192.168.1.1", "192.168.1.1", 4, "ip", mock_ipcrawler)
        
        self.assertEqual(target.address, "192.168.1.1")
        self.assertEqual(target.ip, "192.168.1.1")
        self.assertEqual(target.ipversion, 4)
        self.assertEqual(target.type, "ip")
        self.assertEqual(target.ipcrawler, mock_ipcrawler)
        self.assertIsInstance(target.services, list)
        self.assertIsInstance(target.pending_services, list)
    
    def test_target_string_representation(self):
        """Test Target string representation"""
        mock_ipcrawler = Mock()
        target = Target("example.com", "192.168.1.1", 4, "hostname", mock_ipcrawler)
        
        target_str = str(target)
        self.assertIsInstance(target_str, str)
        # Just check that string representation works
        self.assertGreater(len(target_str), 0)
    
    def test_target_hostname_validation(self):
        """Test hostname validation"""
        mock_ipcrawler = Mock()
        target = Target("192.168.1.1", "192.168.1.1", 4, "ip", mock_ipcrawler)
        
        # Test valid hostname
        valid_hostname = target._validate_hostname("example.com")
        self.assertEqual(valid_hostname, "example.com")
        
        # Test invalid hostname (ends with .html)
        invalid_hostname = target._validate_hostname("test.html")
        self.assertIsNone(invalid_hostname)
        
        # Test empty hostname
        empty_hostname = target._validate_hostname("")
        self.assertIsNone(empty_hostname)
    
    async def test_target_discovered_hostnames_async(self):
        """Test discovered hostnames functionality"""
        mock_ipcrawler = Mock()
        target = Target("192.168.1.1", "192.168.1.1", 4, "ip", mock_ipcrawler)
        
        # Test adding valid hostname (async method)
        await target.add_discovered_hostname("api.example.com")
        self.assertIn("api.example.com", target.discovered_hostnames)
        
        # Test adding invalid hostname (should be filtered out)
        await target.add_discovered_hostname("test.html")
        self.assertNotIn("test.html", target.discovered_hostnames)
        
        # Test deduplication
        await target.add_discovered_hostname("api.example.com")  # Add same hostname again
        self.assertEqual(target.discovered_hostnames.count("api.example.com"), 1)
    
    def test_target_scans_structure(self):
        """Test target scans data structure"""
        mock_ipcrawler = Mock()
        target = Target("192.168.1.1", "192.168.1.1", 4, "ip", mock_ipcrawler)
        
        self.assertIn('ports', target.scans)
        self.assertIn('services', target.scans)
        self.assertIsInstance(target.scans['ports'], dict)
        self.assertIsInstance(target.scans['services'], dict)
    
    def test_target_lock_initialization(self):
        """Test that target has proper async lock"""
        import asyncio
        mock_ipcrawler = Mock()
        target = Target("192.168.1.1", "192.168.1.1", 4, "ip", mock_ipcrawler)
        
        self.assertIsInstance(target.lock, asyncio.Lock)
    
    async def test_add_service_async(self):
        """Test async service addition"""
        mock_ipcrawler = Mock()
        target = Target("192.168.1.1", "192.168.1.1", 4, "ip", mock_ipcrawler)
        
        # Create a mock service
        mock_service = Mock()
        mock_service.name = "http"
        mock_service.port = 80
        
        # Add service asynchronously
        await target.add_service(mock_service)
        
        # Check that service was added to pending services
        self.assertIn(mock_service, target.pending_services)


class TestTargetHelperMethods(unittest.TestCase):
    """Test Target helper methods"""
    
    def test_hostname_validation_patterns(self):
        """Test hostname validation patterns"""
        mock_ipcrawler = Mock()
        target = Target("192.168.1.1", "192.168.1.1", 4, "ip", mock_ipcrawler)
        
        # Test various invalid patterns
        invalid_hostnames = [
            "test.html",
            "page.php", 
            "script.js",
            "style.css",
            "adminhome",
            "indexlogin",
            "",
            "   ",  # Whitespace only
            None
        ]
        
        for hostname in invalid_hostnames:
            result = target._validate_hostname(hostname)
            self.assertIsNone(result, f"Hostname '{hostname}' should be invalid")
        
        # Test valid hostnames
        valid_hostnames = [
            "example.com",
            "api.example.com",
            "test-server.local",
            "server1.domain.org"
        ]
        
        for hostname in valid_hostnames:
            result = target._validate_hostname(hostname)
            self.assertEqual(result, hostname, f"Hostname '{hostname}' should be valid")
    
    def test_directory_setup(self):
        """Test target directory setup"""
        mock_ipcrawler = Mock()
        target = Target("192.168.1.1", "192.168.1.1", 4, "ip", mock_ipcrawler)
        
        # Test that directory attributes exist
        self.assertEqual(target.basedir, '')
        self.assertEqual(target.reportdir, '')
        self.assertEqual(target.scandir, '')
        
        # These would be set by the main application
        target.basedir = "/tmp/results/192.168.1.1"
        target.scandir = "/tmp/results/192.168.1.1/scans"
        target.reportdir = "/tmp/results/192.168.1.1/report"
        
        self.assertIsInstance(target.basedir, str)
        self.assertIsInstance(target.scandir, str)
        self.assertIsInstance(target.reportdir, str)


if __name__ == '__main__':
    # Run tests with asyncio support
    import asyncio
    
    # Create a simple async test runner
    class AsyncTestRunner:
        def run_async_tests(self):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the async tests
                target_test = TestTarget()
                target_test.setUp = lambda: None
                target_test.tearDown = lambda: None
                
                loop.run_until_complete(target_test.test_add_service_async())
                loop.run_until_complete(target_test.test_target_discovered_hostnames_async())
                print("✅ Async tests passed")
                
            except Exception as e:
                print(f"❌ Async test failed: {e}")
            finally:
                loop.close()
    
    # Run async tests first
    async_runner = AsyncTestRunner()
    async_runner.run_async_tests()
    
    # Run regular unittest tests (skip async ones)
    unittest.main(verbosity=2, argv=['test_targets_simple.py'])