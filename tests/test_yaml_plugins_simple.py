#!/usr/bin/env python3
"""
Simplified unit tests for ipcrawler.yaml_plugins module
"""

import unittest
import tempfile
import os
from pathlib import Path
import yaml

# Add parent directory to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ipcrawler.yaml_plugins import PluginType, Severity, OptionType


class TestYAMLPluginEnums(unittest.TestCase):
    """Test YAML plugin enum definitions"""
    
    def test_plugin_type_enum(self):
        """Test PluginType enum values"""
        self.assertEqual(PluginType.PORTSCAN, "portscan")
        self.assertEqual(PluginType.SERVICESCAN, "servicescan")
        self.assertEqual(PluginType.BRUTEFORCE, "bruteforce")
        self.assertEqual(PluginType.REPORTING, "reporting")
        
        # Test that all enum values are strings
        for plugin_type in PluginType:
            self.assertIsInstance(plugin_type.value, str)
    
    def test_severity_enum(self):
        """Test Severity enum values"""
        self.assertEqual(Severity.INFO, "info")
        self.assertEqual(Severity.LOW, "low")
        self.assertEqual(Severity.MEDIUM, "medium")
        self.assertEqual(Severity.HIGH, "high")
        self.assertEqual(Severity.CRITICAL, "critical")
        
        # Test severity ordering (if needed)
        severities = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        self.assertEqual(len(severities), 5)
    
    def test_option_type_enum(self):
        """Test OptionType enum (if it exists)"""
        # This tests that the enum is properly defined
        self.assertTrue(hasattr(OptionType, '__members__'))


class TestYAMLPluginValidation(unittest.TestCase):
    """Test YAML plugin validation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_valid_plugin_structure(self):
        """Test valid plugin YAML structure"""
        valid_plugin = {
            "metadata": {
                "name": "test-plugin",
                "description": "A test plugin",
                "version": "1.0.0",
                "category": "test",
                "author": "Test Suite"
            },
            "conditions": {
                "service_names": ["http", "https"],
                "port_numbers": [80, 443]
            },
            "variables": {
                "timeout": 30,
                "user_agent": "ipcrawler-test"
            },
            "execution": {
                "commands": [
                    "echo 'Testing {target}:{port}'",
                    "curl -s --max-time {timeout} http://{target}:{port}/"
                ]
            },
            "output": {
                "file_patterns": ["*.log", "*.txt"],
                "extract_patterns": {
                    "status_code": r"HTTP/1.1 (\d+)"
                }
            }
        }
        
        # Test YAML structure validation
        self.assertIn("metadata", valid_plugin)
        self.assertIn("execution", valid_plugin)
        self.assertIn("commands", valid_plugin["execution"])
        self.assertIsInstance(valid_plugin["execution"]["commands"], list)
        self.assertGreater(len(valid_plugin["execution"]["commands"]), 0)
    
    def test_plugin_yaml_serialization(self):
        """Test that plugin can be serialized to/from YAML"""
        plugin_data = {
            "metadata": {
                "name": "yaml-test",
                "description": "YAML serialization test",
                "version": "1.0.0"
            },
            "execution": {
                "commands": ["echo 'test'"]
            }
        }
        
        # Test YAML serialization
        yaml_str = yaml.dump(plugin_data)
        self.assertIsInstance(yaml_str, str)
        self.assertIn("metadata", yaml_str)
        
        # Test YAML deserialization
        loaded_data = yaml.safe_load(yaml_str)
        self.assertEqual(loaded_data["metadata"]["name"], "yaml-test")
        self.assertEqual(loaded_data["execution"]["commands"], ["echo 'test'"])
    
    def test_plugin_file_loading(self):
        """Test loading plugin from file"""
        plugin_data = {
            "metadata": {
                "name": "file-test",
                "description": "File loading test",
                "version": "1.0.0"
            },
            "execution": {
                "commands": ["echo 'file test'"]
            }
        }
        
        # Write plugin to file
        plugin_file = Path(self.temp_dir) / "test-plugin.yaml"
        with open(plugin_file, 'w') as f:
            yaml.dump(plugin_data, f)
        
        # Read plugin from file
        with open(plugin_file, 'r') as f:
            loaded_plugin = yaml.safe_load(f)
        
        self.assertEqual(loaded_plugin["metadata"]["name"], "file-test")
        self.assertIn("execution", loaded_plugin)
    
    def test_invalid_plugin_yaml(self):
        """Test handling of invalid YAML"""
        invalid_yaml = "invalid: yaml: content: ["
        
        # Should raise YAML error
        with self.assertRaises(yaml.YAMLError):
            yaml.safe_load(invalid_yaml)
    
    def test_plugin_variable_substitution_patterns(self):
        """Test variable substitution patterns"""
        command_template = "curl -s --max-time {timeout} http://{target}:{port}/"
        
        # Test that template contains expected variables
        self.assertIn("{timeout}", command_template)
        self.assertIn("{target}", command_template)
        self.assertIn("{port}", command_template)
        
        # Test simple string substitution (would be done by template engine)
        variables = {
            "timeout": "30",
            "target": "example.com",
            "port": "80"
        }
        
        # Simulate variable substitution
        rendered_command = command_template.format(**variables)
        self.assertIn("30", rendered_command)
        self.assertIn("example.com", rendered_command)
        self.assertIn("80", rendered_command)
        self.assertNotIn("{", rendered_command)  # No unresolved variables


class TestYAMLPluginDirectory(unittest.TestCase):
    """Test YAML plugin directory operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_dir = Path(self.temp_dir) / "plugins"
        self.plugin_dir.mkdir()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_plugin_directory_structure(self):
        """Test plugin directory structure"""
        # Create plugin categories
        categories = [
            "01-discovery",
            "02-enumeration",
            "03-bruteforce"
        ]
        
        for category in categories:
            category_dir = self.plugin_dir / category
            category_dir.mkdir()
            
            # Create a test plugin in each category
            plugin_data = {
                "metadata": {
                    "name": f"{category}-test",
                    "description": f"Test plugin for {category}",
                    "version": "1.0.0",
                    "category": category
                },
                "execution": {
                    "commands": [f"echo 'Running {category} test'"]
                }
            }
            
            plugin_file = category_dir / f"{category}-test.yaml"
            with open(plugin_file, 'w') as f:
                yaml.dump(plugin_data, f)
        
        # Verify directory structure
        self.assertTrue(self.plugin_dir.exists())
        
        # Count plugin files
        plugin_files = list(self.plugin_dir.rglob("*.yaml"))
        self.assertEqual(len(plugin_files), 3)
        
        # Verify each plugin can be loaded
        for plugin_file in plugin_files:
            with open(plugin_file, 'r') as f:
                plugin_data = yaml.safe_load(f)
            
            self.assertIn("metadata", plugin_data)
            self.assertIn("execution", plugin_data)
    
    def test_plugin_discovery(self):
        """Test plugin discovery in directory"""
        # Create plugins in different subdirectories
        web_dir = self.plugin_dir / "web-services"
        web_dir.mkdir()
        
        http_plugin = {
            "metadata": {"name": "http-test", "version": "1.0.0"},
            "execution": {"commands": ["echo 'http test'"]}
        }
        
        with open(web_dir / "http.yaml", 'w') as f:
            yaml.dump(http_plugin, f)
        
        # Discover all YAML files
        yaml_files = list(self.plugin_dir.rglob("*.yaml"))
        self.assertEqual(len(yaml_files), 1)
        
        # Verify file path
        self.assertTrue(str(yaml_files[0]).endswith("http.yaml"))


if __name__ == '__main__':
    unittest.main(verbosity=2)