#!/usr/bin/env python3
"""
Unit tests for ipcrawler.targets module
"""

import unittest
from unittest.mock import Mock, patch

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ipcrawler.targets import Target


class TestService(unittest.TestCase):
    """Test Service class functionality"""
    
    def test_service_initialization(self):
        """Test Service object initialization"""
        service = Service("http", 80, "tcp")
        
        self.assertEqual(service.name, "http")
        self.assertEqual(service.port, 80)
        self.assertEqual(service.protocol, "tcp")
        self.assertEqual(service.state, "open")
        self.assertEqual(service.version, "")
        self.assertEqual(service.product, "")
    
    def test_service_with_details(self):
        """Test Service initialization with detailed information"""
        service = Service(
            name="http",
            port=80,
            protocol="tcp",
            state="open",
            version="1.1",
            product="Apache httpd",
            extra_info="Ubuntu"
        )
        
        self.assertEqual(service.name, "http")
        self.assertEqual(service.port, 80)
        self.assertEqual(service.protocol, "tcp")
        self.assertEqual(service.state, "open")
        self.assertEqual(service.version, "1.1")
        self.assertEqual(service.product, "Apache httpd")
        self.assertEqual(service.extra_info, "Ubuntu")
    
    def test_service_string_representation(self):
        """Test Service string representation"""
        service = Service("http", 80, "tcp")
        service_str = str(service)
        
        self.assertIn("http", service_str)
        self.assertIn("80", service_str)
        self.assertIn("tcp", service_str)
    
    def test_service_equality(self):
        """Test Service equality comparison"""
        service1 = Service("http", 80, "tcp")
        service2 = Service("http", 80, "tcp")
        service3 = Service("https", 443, "tcp")
        
        self.assertEqual(service1, service2)
        self.assertNotEqual(service1, service3)
    
    def test_service_hash(self):
        """Test Service hash functionality"""
        service1 = Service("http", 80, "tcp")
        service2 = Service("http", 80, "tcp")
        service3 = Service("https", 443, "tcp")
        
        # Same services should have same hash
        self.assertEqual(hash(service1), hash(service2))
        
        # Different services should have different hash
        self.assertNotEqual(hash(service1), hash(service3))
    
    def test_service_is_web_service(self):
        """Test web service detection"""
        http_service = Service("http", 80, "tcp")
        https_service = Service("https", 443, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        
        self.assertTrue(http_service.is_web_service())
        self.assertTrue(https_service.is_web_service())
        self.assertFalse(ssh_service.is_web_service())
    
    def test_service_get_url(self):
        """Test URL generation for web services"""
        http_service = Service("http", 80, "tcp")
        https_service = Service("https", 443, "tcp")
        custom_http = Service("http", 8080, "tcp")
        
        self.assertEqual(http_service.get_url("example.com"), "http://example.com/")
        self.assertEqual(https_service.get_url("example.com"), "https://example.com/")
        self.assertEqual(custom_http.get_url("example.com"), "http://example.com:8080/")


class TestTarget(unittest.TestCase):
    """Test Target class functionality"""
    
    def test_target_initialization(self):
        """Test Target object initialization"""
        target = Target("192.168.1.1")
        
        self.assertEqual(target.address, "192.168.1.1")
        self.assertEqual(target.hostname, "")
        self.assertIsInstance(target.services, list)
        self.assertEqual(len(target.services), 0)
        self.assertIsInstance(target.ports, list)
        self.assertEqual(len(target.ports), 0)
    
    def test_target_with_hostname(self):
        """Test Target initialization with hostname"""
        target = Target("192.168.1.1", hostname="example.com")
        
        self.assertEqual(target.address, "192.168.1.1")
        self.assertEqual(target.hostname, "example.com")
    
    def test_target_add_service(self):
        """Test adding services to target"""
        target = Target("192.168.1.1")
        service = Service("http", 80, "tcp")
        
        target.add_service(service)
        
        self.assertEqual(len(target.services), 1)
        self.assertEqual(target.services[0], service)
        self.assertIn(80, target.ports)
    
    def test_target_add_multiple_services(self):
        """Test adding multiple services to target"""
        target = Target("192.168.1.1")
        
        http_service = Service("http", 80, "tcp")
        https_service = Service("https", 443, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        
        target.add_service(http_service)
        target.add_service(https_service)
        target.add_service(ssh_service)
        
        self.assertEqual(len(target.services), 3)
        self.assertEqual(set(target.ports), {80, 443, 22})
    
    def test_target_get_services_by_name(self):
        """Test getting services by name"""
        target = Target("192.168.1.1")
        
        http_service = Service("http", 80, "tcp")
        https_service = Service("https", 443, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        
        target.add_service(http_service)
        target.add_service(https_service)
        target.add_service(ssh_service)
        
        # Test getting HTTP services
        http_services = target.get_services_by_name("http")
        self.assertEqual(len(http_services), 1)
        self.assertEqual(http_services[0].name, "http")
        
        # Test getting non-existent service
        ftp_services = target.get_services_by_name("ftp")
        self.assertEqual(len(ftp_services), 0)
    
    def test_target_get_services_by_port(self):
        """Test getting services by port"""
        target = Target("192.168.1.1")
        
        http_service = Service("http", 80, "tcp")
        https_service = Service("https", 443, "tcp")
        
        target.add_service(http_service)
        target.add_service(https_service)
        
        # Test getting service on port 80
        port_80_services = target.get_services_by_port(80)
        self.assertEqual(len(port_80_services), 1)
        self.assertEqual(port_80_services[0].port, 80)
        
        # Test getting service on non-existent port
        port_22_services = target.get_services_by_port(22)
        self.assertEqual(len(port_22_services), 0)
    
    def test_target_get_web_services(self):
        """Test getting web services"""
        target = Target("192.168.1.1")
        
        http_service = Service("http", 80, "tcp")
        https_service = Service("https", 443, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        
        target.add_service(http_service)
        target.add_service(https_service)
        target.add_service(ssh_service)
        
        web_services = target.get_web_services()
        self.assertEqual(len(web_services), 2)
        
        web_service_names = {s.name for s in web_services}
        self.assertEqual(web_service_names, {"http", "https"})
    
    def test_target_has_service(self):
        """Test checking if target has specific service"""
        target = Target("192.168.1.1")
        
        http_service = Service("http", 80, "tcp")
        target.add_service(http_service)
        
        self.assertTrue(target.has_service("http"))
        self.assertFalse(target.has_service("ssh"))
    
    def test_target_has_port(self):
        """Test checking if target has specific port open"""
        target = Target("192.168.1.1")
        
        http_service = Service("http", 80, "tcp")
        target.add_service(http_service)
        
        self.assertTrue(target.has_port(80))
        self.assertFalse(target.has_port(22))
    
    def test_target_string_representation(self):
        """Test Target string representation"""
        target = Target("192.168.1.1", hostname="example.com")
        target_str = str(target)
        
        self.assertIn("192.168.1.1", target_str)
        self.assertIn("example.com", target_str)
    
    def test_target_equality(self):
        """Test Target equality comparison"""
        target1 = Target("192.168.1.1")
        target2 = Target("192.168.1.1")
        target3 = Target("192.168.1.2")
        
        self.assertEqual(target1, target2)
        self.assertNotEqual(target1, target3)


class TestTargetManager(unittest.TestCase):
    """Test TargetManager class functionality"""
    
    def test_target_manager_initialization(self):
        """Test TargetManager initialization"""
        manager = TargetManager()
        
        self.assertIsInstance(manager.targets, dict)
        self.assertEqual(len(manager.targets), 0)
    
    def test_add_target(self):
        """Test adding targets to manager"""
        manager = TargetManager()
        target = Target("192.168.1.1")
        
        manager.add_target(target)
        
        self.assertEqual(len(manager.targets), 1)
        self.assertIn("192.168.1.1", manager.targets)
        self.assertEqual(manager.targets["192.168.1.1"], target)
    
    def test_get_target(self):
        """Test getting target from manager"""
        manager = TargetManager()
        target = Target("192.168.1.1")
        
        manager.add_target(target)
        
        retrieved_target = manager.get_target("192.168.1.1")
        self.assertEqual(retrieved_target, target)
        
        # Test getting non-existent target
        non_existent = manager.get_target("192.168.1.2")
        self.assertIsNone(non_existent)
    
    def test_get_or_create_target(self):
        """Test getting or creating target"""
        manager = TargetManager()
        
        # Create new target
        target1 = manager.get_or_create_target("192.168.1.1")
        self.assertIsInstance(target1, Target)
        self.assertEqual(target1.address, "192.168.1.1")
        
        # Get existing target
        target2 = manager.get_or_create_target("192.168.1.1")
        self.assertEqual(target1, target2)
        
        # Verify only one target exists
        self.assertEqual(len(manager.targets), 1)
    
    def test_get_all_targets(self):
        """Test getting all targets"""
        manager = TargetManager()
        
        target1 = Target("192.168.1.1")
        target2 = Target("192.168.1.2")
        
        manager.add_target(target1)
        manager.add_target(target2)
        
        all_targets = manager.get_all_targets()
        self.assertEqual(len(all_targets), 2)
        self.assertIn(target1, all_targets)
        self.assertIn(target2, all_targets)
    
    def test_get_targets_with_service(self):
        """Test getting targets with specific service"""
        manager = TargetManager()
        
        target1 = Target("192.168.1.1")
        target2 = Target("192.168.1.2")
        
        http_service = Service("http", 80, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        
        target1.add_service(http_service)
        target1.add_service(ssh_service)
        target2.add_service(ssh_service)
        
        manager.add_target(target1)
        manager.add_target(target2)
        
        # Test getting targets with HTTP service
        http_targets = manager.get_targets_with_service("http")
        self.assertEqual(len(http_targets), 1)
        self.assertEqual(http_targets[0], target1)
        
        # Test getting targets with SSH service
        ssh_targets = manager.get_targets_with_service("ssh")
        self.assertEqual(len(ssh_targets), 2)
        self.assertIn(target1, ssh_targets)
        self.assertIn(target2, ssh_targets)
    
    def test_get_targets_with_port(self):
        """Test getting targets with specific port"""
        manager = TargetManager()
        
        target1 = Target("192.168.1.1")
        target2 = Target("192.168.1.2")
        
        http_service = Service("http", 80, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        
        target1.add_service(http_service)
        target2.add_service(ssh_service)
        
        manager.add_target(target1)
        manager.add_target(target2)
        
        # Test getting targets with port 80
        port_80_targets = manager.get_targets_with_port(80)
        self.assertEqual(len(port_80_targets), 1)
        self.assertEqual(port_80_targets[0], target1)
        
        # Test getting targets with port 22
        port_22_targets = manager.get_targets_with_port(22)
        self.assertEqual(len(port_22_targets), 1)
        self.assertEqual(port_22_targets[0], target2)
    
    def test_target_count(self):
        """Test target count functionality"""
        manager = TargetManager()
        
        self.assertEqual(manager.target_count(), 0)
        
        target1 = Target("192.168.1.1")
        target2 = Target("192.168.1.2")
        
        manager.add_target(target1)
        self.assertEqual(manager.target_count(), 1)
        
        manager.add_target(target2)
        self.assertEqual(manager.target_count(), 2)
    
    def test_clear_targets(self):
        """Test clearing all targets"""
        manager = TargetManager()
        
        target1 = Target("192.168.1.1")
        target2 = Target("192.168.1.2")
        
        manager.add_target(target1)
        manager.add_target(target2)
        
        self.assertEqual(manager.target_count(), 2)
        
        manager.clear_targets()
        self.assertEqual(manager.target_count(), 0)
        self.assertEqual(len(manager.targets), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)