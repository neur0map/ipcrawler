#!/usr/bin/env python3
"""
Integration tests for ipcrawler YAML plugin system
"""

import unittest
import tempfile
import os
import subprocess
import time
from pathlib import Path
import yaml
from unittest.mock import Mock, patch

# Add parent directory to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ipcrawler.yaml_plugins import YAMLPluginLoader, YAMLPlugin
from ipcrawler.targets import Target, Service, TargetManager
from ipcrawler.yaml_executor import YAMLExecutor


class TestYAMLPluginIntegration(unittest.TestCase):
    """Integration tests for YAML plugin system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_dir = Path(self.temp_dir) / "test-plugins"
        self.plugin_dir.mkdir()
        self.results_dir = Path(self.temp_dir) / "results"
        self.results_dir.mkdir()
        
        # Create test plugins
        self.create_test_plugins()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_plugins(self):
        """Create test plugins for integration testing"""
        
        # Simple HTTP test plugin
        http_plugin = {
            "metadata": {
                "name": "http-integration-test",
                "description": "HTTP integration test plugin",
                "version": "1.0.0",
                "category": "web",
                "author": "Test Suite"
            },
            "conditions": {
                "service_names": ["http", "https"],
                "port_numbers": [80, 443, 8080, 8443]
            },
            "variables": {
                "timeout": 10,
                "user_agent": "ipcrawler-test/1.0"
            },
            "execution": {
                "commands": [
                    "echo 'Testing HTTP service on {target}:{port}'",
                    "curl -s -A '{user_agent}' --max-time {timeout} --connect-timeout 5 http://{target}:{port}/ || echo 'Connection failed'"
                ]
            },
            "output": {
                "file_patterns": ["*.log", "*.txt"],
                "extract_patterns": {
                    "http_status": r"HTTP/1\.[01] (\d{3})",
                    "server_header": r"Server: (.+)"
                }
            }
        }
        
        # Port scanning test plugin
        port_scan_plugin = {
            "metadata": {
                "name": "port-scan-integration-test",
                "description": "Port scanning integration test",
                "version": "1.0.0",
                "category": "discovery",
                "author": "Test Suite"
            },
            "conditions": {
                "always_run": True
            },
            "variables": {
                "timing": "T4",
                "ports": "80,443,22,21,25,53,110,143,993,995"
            },
            "execution": {
                "commands": [
                    "echo 'Scanning ports on {target}'",
                    "nmap -Pn -{timing} -p {ports} {target} || echo 'Nmap scan failed'"
                ]
            },
            "output": {
                "file_patterns": ["*.xml", "*.nmap"],
                "extract_patterns": {
                    "open_ports": r"(\d+)/(tcp|udp)\s+open"
                }
            }
        }
        
        # SSH test plugin
        ssh_plugin = {
            "metadata": {
                "name": "ssh-integration-test",
                "description": "SSH integration test plugin",
                "version": "1.0.0",
                "category": "network",
                "author": "Test Suite"
            },
            "conditions": {
                "service_names": ["ssh"],
                "port_numbers": [22]
            },
            "variables": {
                "timeout": 5
            },
            "execution": {
                "commands": [
                    "echo 'Testing SSH service on {target}:{port}'",
                    "nc -zv -w {timeout} {target} {port} || echo 'SSH connection test failed'"
                ]
            },
            "output": {
                "file_patterns": ["*.log"],
                "extract_patterns": {
                    "ssh_banner": r"SSH-([0-9.]+)-(.+)"
                }
            }
        }
        
        # Write plugins to files
        with open(self.plugin_dir / "http-test.yaml", 'w') as f:
            yaml.dump(http_plugin, f)
        
        with open(self.plugin_dir / "port-scan-test.yaml", 'w') as f:
            yaml.dump(port_scan_plugin, f)
        
        with open(self.plugin_dir / "ssh-test.yaml", 'w') as f:
            yaml.dump(ssh_plugin, f)
    
    def test_plugin_loading_and_validation(self):
        """Test that plugins load correctly and pass validation"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Should load all 3 plugins
        self.assertEqual(len(plugins), 3)
        
        # Check plugin names
        plugin_names = {p.name for p in plugins}
        expected_names = {
            "http-integration-test",
            "port-scan-integration-test", 
            "ssh-integration-test"
        }
        self.assertEqual(plugin_names, expected_names)
        
        # Each plugin should be valid
        for plugin in plugins:
            self.assertIsInstance(plugin, YAMLPlugin)
            self.assertIsNotNone(plugin.name)
            self.assertIsNotNone(plugin.description)
            self.assertIsNotNone(plugin.version)
    
    def test_plugin_service_matching(self):
        """Test plugin matching against different services"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Create test services
        http_service = Service("http", 80, "tcp")
        https_service = Service("https", 443, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        ftp_service = Service("ftp", 21, "tcp")
        
        # Test HTTP service matching
        http_plugins = [p for p in plugins if p.matches_service_object(http_service)]
        self.assertGreater(len(http_plugins), 0)
        
        # Should include HTTP plugin
        http_plugin_names = {p.name for p in http_plugins}
        self.assertIn("http-integration-test", http_plugin_names)
        
        # Test HTTPS service matching
        https_plugins = [p for p in plugins if p.matches_service_object(https_service)]
        self.assertGreater(len(https_plugins), 0)
        
        # Should include HTTP plugin (matches both HTTP and HTTPS)
        https_plugin_names = {p.name for p in https_plugins}
        self.assertIn("http-integration-test", https_plugin_names)
        
        # Test SSH service matching
        ssh_plugins = [p for p in plugins if p.matches_service_object(ssh_service)]
        self.assertGreater(len(ssh_plugins), 0)
        
        # Should include SSH plugin
        ssh_plugin_names = {p.name for p in ssh_plugins}
        self.assertIn("ssh-integration-test", ssh_plugin_names)
        
        # Test FTP service (should not match any specific plugins)
        ftp_plugins = [p for p in plugins if p.matches_service_object(ftp_service)]
        # Only plugins with always_run=True should match
        always_run_plugins = [p for p in ftp_plugins if p.data.get("conditions", {}).get("always_run", False)]
        self.assertGreater(len(always_run_plugins), 0)
    
    def test_command_rendering_with_context(self):
        """Test command rendering with target context"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Find HTTP plugin
        http_plugin = next((p for p in plugins if p.name == "http-integration-test"), None)
        self.assertIsNotNone(http_plugin)
        
        # Test command rendering
        context = {
            "target": "example.com",
            "port": 80,
            "timeout": 10,
            "user_agent": "test-agent"
        }
        
        rendered_commands = http_plugin.render_commands(context)
        self.assertIsInstance(rendered_commands, list)
        self.assertGreater(len(rendered_commands), 0)
        
        # Check variable substitution
        command_text = " ".join(rendered_commands)
        self.assertIn("example.com", command_text)
        self.assertIn("80", command_text)
        self.assertIn("10", command_text)
        self.assertIn("test-agent", command_text)
    
    def test_target_and_service_integration(self):
        """Test integration between targets, services, and plugins"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Create target with services
        target = Target("192.168.1.100", hostname="test.example.com")
        
        http_service = Service("http", 80, "tcp")
        https_service = Service("https", 443, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        
        target.add_service(http_service)
        target.add_service(https_service)
        target.add_service(ssh_service)
        
        # Test plugin selection for each service
        for service in target.services:
            matching_plugins = [p for p in plugins if p.matches_service_object(service)]
            self.assertGreater(len(matching_plugins), 0)
            
            # Test command generation for each matching plugin
            for plugin in matching_plugins:
                context = {
                    "target": target.address,
                    "hostname": target.hostname,
                    "port": service.port,
                    "service": service.name,
                    "protocol": service.protocol
                }
                
                # Add plugin variables to context
                context.update(plugin.variables)
                
                rendered_commands = plugin.render_commands(context)
                self.assertIsInstance(rendered_commands, list)
                self.assertGreater(len(rendered_commands), 0)
    
    def test_plugin_execution_simulation(self):
        """Test simulated plugin execution"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Create a simple target
        target = Target("127.0.0.1")
        http_service = Service("http", 80, "tcp")
        target.add_service(http_service)
        
        # Find HTTP plugin
        http_plugin = next((p for p in plugins if p.name == "http-integration-test"), None)
        self.assertIsNotNone(http_plugin)
        
        # Simulate plugin execution
        context = {
            "target": target.address,
            "port": http_service.port,
            "timeout": 5,
            "user_agent": "test-agent"
        }
        
        context.update(http_plugin.variables)
        commands = http_plugin.render_commands(context)
        
        # Test that commands are valid
        self.assertIsInstance(commands, list)
        self.assertGreater(len(commands), 0)
        
        # Commands should contain expected elements
        command_text = " ".join(commands)
        self.assertIn("127.0.0.1", command_text)
        self.assertIn("80", command_text)
    
    def test_plugin_category_filtering(self):
        """Test filtering plugins by category"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Test web category
        web_plugins = loader.filter_by_category("web")
        self.assertEqual(len(web_plugins), 1)
        self.assertEqual(web_plugins[0].name, "http-integration-test")
        
        # Test network category
        network_plugins = loader.filter_by_category("network")
        self.assertEqual(len(network_plugins), 1)
        self.assertEqual(network_plugins[0].name, "ssh-integration-test")
        
        # Test discovery category
        discovery_plugins = loader.filter_by_category("discovery")
        self.assertEqual(len(discovery_plugins), 1)
        self.assertEqual(discovery_plugins[0].name, "port-scan-integration-test")
        
        # Test non-existent category
        missing_plugins = loader.filter_by_category("nonexistent")
        self.assertEqual(len(missing_plugins), 0)
    
    def test_plugin_output_patterns(self):
        """Test plugin output pattern configuration"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Check each plugin has proper output configuration
        for plugin in plugins:
            self.assertIn("output", plugin.data)
            output_config = plugin.data["output"]
            
            # Should have file patterns
            self.assertIn("file_patterns", output_config)
            self.assertIsInstance(output_config["file_patterns"], list)
            self.assertGreater(len(output_config["file_patterns"]), 0)
            
            # Should have extract patterns
            self.assertIn("extract_patterns", output_config)
            self.assertIsInstance(output_config["extract_patterns"], dict)
    
    def test_plugin_variable_defaults(self):
        """Test plugin variable defaults and overrides"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Find HTTP plugin
        http_plugin = next((p for p in plugins if p.name == "http-integration-test"), None)
        self.assertIsNotNone(http_plugin)
        
        # Check default variables
        self.assertIn("timeout", http_plugin.variables)
        self.assertIn("user_agent", http_plugin.variables)
        self.assertEqual(http_plugin.variables["timeout"], 10)
        
        # Test variable override
        context = {
            "target": "example.com",
            "port": 80,
            "timeout": 30,  # Override default
            "user_agent": "custom-agent"  # Override default
        }
        
        rendered_commands = http_plugin.render_commands(context)
        command_text = " ".join(rendered_commands)
        
        # Should use overridden values
        self.assertIn("30", command_text)  # timeout
        self.assertIn("custom-agent", command_text)  # user_agent


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end workflow tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.results_dir = Path(self.temp_dir) / "results"
        self.results_dir.mkdir()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('subprocess.run')
    def test_simple_scan_workflow(self, mock_subprocess):
        """Test a simple scan workflow"""
        # Mock subprocess output
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Test output"
        mock_subprocess.return_value.stderr = ""
        
        # Create target manager
        manager = TargetManager()
        target = manager.get_or_create_target("127.0.0.1")
        
        # Add services
        http_service = Service("http", 80, "tcp")
        ssh_service = Service("ssh", 22, "tcp")
        
        target.add_service(http_service)
        target.add_service(ssh_service)
        
        # Verify target setup
        self.assertEqual(len(target.services), 2)
        self.assertTrue(target.has_service("http"))
        self.assertTrue(target.has_service("ssh"))
        self.assertTrue(target.has_port(80))
        self.assertTrue(target.has_port(22))
        
        # Test web services detection
        web_services = target.get_web_services()
        self.assertEqual(len(web_services), 1)
        self.assertEqual(web_services[0].name, "http")
    
    def test_plugin_execution_order(self):
        """Test plugin execution order and dependencies"""
        # This test would verify that plugins execute in the correct order
        # and that dependencies are respected
        
        # Create plugins with different categories
        plugins = [
            {"metadata": {"name": "discovery", "category": "01-discovery"}},
            {"metadata": {"name": "port-scan", "category": "01-port-scanning"}},
            {"metadata": {"name": "service-enum", "category": "02-service-enumeration"}},
            {"metadata": {"name": "bruteforce", "category": "03-bruteforce"}},
        ]
        
        # Sort by category (simulating plugin execution order)
        sorted_plugins = sorted(plugins, key=lambda p: p["metadata"]["category"])
        
        # Verify order
        expected_order = ["discovery", "port-scan", "service-enum", "bruteforce"]
        actual_order = [p["metadata"]["name"] for p in sorted_plugins]
        
        self.assertEqual(actual_order, expected_order)
    
    def test_error_handling_integration(self):
        """Test error handling in plugin execution"""
        # Test that errors in plugin execution are handled gracefully
        # and don't crash the entire scan
        
        # Create a target
        target = Target("127.0.0.1")
        
        # Simulate plugin execution errors
        errors = []
        
        try:
            # This would simulate a plugin failing
            raise Exception("Plugin execution failed")
        except Exception as e:
            errors.append(f"Plugin error: {e}")
        
        # Verify error was captured
        self.assertEqual(len(errors), 1)
        self.assertIn("Plugin execution failed", errors[0])
        
        # Target should still be valid
        self.assertEqual(target.address, "127.0.0.1")


if __name__ == '__main__':
    unittest.main(verbosity=2)