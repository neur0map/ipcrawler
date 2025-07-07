#!/usr/bin/env python3
"""
Unit tests for ipcrawler.yaml_plugins module
"""

import unittest
import tempfile
import os
from pathlib import Path
import yaml
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ipcrawler.yaml_plugins import (
    YAMLPluginLoader,
    YAMLPlugin,
    load_yaml_plugins,
    validate_plugin_schema
)
from ipcrawler.targets import Target, Service


class TestYAMLPluginLoader(unittest.TestCase):
    """Test YAML plugin loader functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_dir = Path(self.temp_dir) / "test-plugins"
        self.plugin_dir.mkdir()
        
        # Create sample plugin
        self.sample_plugin = {
            "metadata": {
                "name": "test-plugin",
                "description": "Test plugin for unit tests",
                "author": "Test Suite",
                "version": "1.0.0",
                "category": "test"
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
                    "curl -s -A '{user_agent}' --max-time {timeout} http://{target}/"
                ]
            },
            "output": {
                "file_patterns": ["*.txt"],
                "extract_patterns": {
                    "status": r"HTTP/1.1 (\d+)"
                }
            }
        }
        
        # Write sample plugin
        plugin_file = self.plugin_dir / "test-plugin.yaml"
        with open(plugin_file, 'w') as f:
            yaml.dump(self.sample_plugin, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_plugin_loader_initialization(self):
        """Test YAMLPluginLoader initialization"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        
        self.assertEqual(loader.plugin_directory, str(self.plugin_dir))
        self.assertIsInstance(loader.plugins, list)
    
    def test_load_plugins_from_directory(self):
        """Test loading plugins from directory"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        self.assertGreater(len(plugins), 0)
        self.assertIsInstance(plugins[0], YAMLPlugin)
        self.assertEqual(plugins[0].name, "test-plugin")
    
    def test_load_invalid_plugin_file(self):
        """Test loading invalid plugin file"""
        # Create invalid YAML file
        invalid_file = self.plugin_dir / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Should skip invalid files and continue
        self.assertIsInstance(plugins, list)
    
    def test_filter_plugins_by_category(self):
        """Test filtering plugins by category"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        test_plugins = loader.filter_by_category("test")
        self.assertGreater(len(test_plugins), 0)
        
        missing_plugins = loader.filter_by_category("nonexistent")
        self.assertEqual(len(missing_plugins), 0)
    
    def test_get_plugins_for_service(self):
        """Test getting plugins for specific service"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Create mock service
        mock_service = Mock()
        mock_service.name = "http"
        mock_service.port = 80
        
        matching_plugins = loader.get_plugins_for_service(mock_service)
        self.assertGreater(len(matching_plugins), 0)


class TestYAMLPlugin(unittest.TestCase):
    """Test YAMLPlugin class functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.plugin_data = {
            "metadata": {
                "name": "test-plugin",
                "description": "Test plugin",
                "version": "1.0.0",
                "category": "test"
            },
            "conditions": {
                "service_names": ["http"],
                "port_numbers": [80]
            },
            "variables": {
                "timeout": 30,
                "max_redirects": 5
            },
            "execution": {
                "commands": [
                    "curl -s --max-time {timeout} http://{target}:{port}/"
                ]
            },
            "output": {
                "file_patterns": ["*.log"],
                "extract_patterns": {
                    "status_code": r"HTTP/1.1 (\d+)"
                }
            }
        }
        
        self.plugin = YAMLPlugin(self.plugin_data)
    
    def test_plugin_initialization(self):
        """Test YAMLPlugin initialization"""
        self.assertEqual(self.plugin.name, "test-plugin")
        self.assertEqual(self.plugin.description, "Test plugin")
        self.assertEqual(self.plugin.version, "1.0.0")
        self.assertEqual(self.plugin.category, "test")
    
    def test_plugin_variables(self):
        """Test plugin variables access"""
        self.assertEqual(self.plugin.variables["timeout"], 30)
        self.assertEqual(self.plugin.variables["max_redirects"], 5)
    
    def test_plugin_commands(self):
        """Test plugin commands access"""
        commands = self.plugin.commands
        self.assertIsInstance(commands, list)
        self.assertGreater(len(commands), 0)
        self.assertIn("curl", commands[0])
    
    def test_matches_service_name(self):
        """Test service name matching"""
        self.assertTrue(self.plugin.matches_service("http"))
        self.assertFalse(self.plugin.matches_service("ssh"))
    
    def test_matches_port_number(self):
        """Test port number matching"""
        self.assertTrue(self.plugin.matches_port(80))
        self.assertFalse(self.plugin.matches_port(22))
    
    def test_matches_service_object(self):
        """Test matching against service object"""
        # Create mock service that should match
        matching_service = Mock()
        matching_service.name = "http"
        matching_service.port = 80
        
        self.assertTrue(self.plugin.matches_service_object(matching_service))
        
        # Create mock service that should not match
        non_matching_service = Mock()
        non_matching_service.name = "ssh"
        non_matching_service.port = 22
        
        self.assertFalse(self.plugin.matches_service_object(non_matching_service))
    
    def test_render_commands(self):
        """Test command rendering with variables"""
        context = {
            "target": "example.com",
            "port": 80,
            "timeout": 30
        }
        
        rendered_commands = self.plugin.render_commands(context)
        self.assertIsInstance(rendered_commands, list)
        self.assertGreater(len(rendered_commands), 0)
        
        # Check that variables are substituted
        self.assertIn("example.com", rendered_commands[0])
        self.assertIn("80", rendered_commands[0])
        self.assertIn("30", rendered_commands[0])
    
    def test_render_commands_missing_variables(self):
        """Test command rendering with missing variables"""
        context = {
            "target": "example.com"
            # Missing 'port' and 'timeout'
        }
        
        # Should handle missing variables gracefully
        rendered_commands = self.plugin.render_commands(context)
        self.assertIsInstance(rendered_commands, list)
    
    def test_validate_plugin_schema(self):
        """Test plugin schema validation"""
        # Valid plugin should pass validation
        self.assertTrue(validate_plugin_schema(self.plugin_data))
        
        # Invalid plugin should fail validation
        invalid_plugin = {
            "metadata": {
                "name": "invalid-plugin"
                # Missing required fields
            }
        }
        
        self.assertFalse(validate_plugin_schema(invalid_plugin))


class TestYAMLPluginIntegration(unittest.TestCase):
    """Test integration between plugins and targets/services"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_dir = Path(self.temp_dir) / "plugins"
        self.plugin_dir.mkdir()
        
        # Create HTTP plugin
        http_plugin = {
            "metadata": {
                "name": "http-test",
                "description": "HTTP testing plugin",
                "version": "1.0.0",
                "category": "web"
            },
            "conditions": {
                "service_names": ["http", "https"],
                "port_numbers": [80, 443, 8080]
            },
            "variables": {
                "timeout": 30
            },
            "execution": {
                "commands": [
                    "curl -s --max-time {timeout} http://{target}:{port}/"
                ]
            }
        }
        
        with open(self.plugin_dir / "http-test.yaml", 'w') as f:
            yaml.dump(http_plugin, f)
        
        # Create SSH plugin
        ssh_plugin = {
            "metadata": {
                "name": "ssh-test",
                "description": "SSH testing plugin",
                "version": "1.0.0",
                "category": "network"
            },
            "conditions": {
                "service_names": ["ssh"],
                "port_numbers": [22]
            },
            "variables": {
                "timeout": 10
            },
            "execution": {
                "commands": [
                    "nmap -p {port} -sV {target}"
                ]
            }
        }
        
        with open(self.plugin_dir / "ssh-test.yaml", 'w') as f:
            yaml.dump(ssh_plugin, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_plugin_service_matching(self):
        """Test plugin matching against services"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Create mock HTTP service
        http_service = Mock()
        http_service.name = "http"
        http_service.port = 80
        
        # Create mock SSH service
        ssh_service = Mock()
        ssh_service.name = "ssh"
        ssh_service.port = 22
        
        # Test HTTP plugin matching
        http_plugins = [p for p in plugins if p.matches_service_object(http_service)]
        self.assertEqual(len(http_plugins), 1)
        self.assertEqual(http_plugins[0].name, "http-test")
        
        # Test SSH plugin matching
        ssh_plugins = [p for p in plugins if p.matches_service_object(ssh_service)]
        self.assertEqual(len(ssh_plugins), 1)
        self.assertEqual(ssh_plugins[0].name, "ssh-test")
    
    def test_plugin_command_generation(self):
        """Test plugin command generation for services"""
        loader = YAMLPluginLoader(str(self.plugin_dir))
        plugins = loader.load_plugins()
        
        # Find HTTP plugin
        http_plugin = next((p for p in plugins if p.name == "http-test"), None)
        self.assertIsNotNone(http_plugin)
        
        # Generate commands for specific target
        context = {
            "target": "example.com",
            "port": 80,
            "timeout": 30
        }
        
        commands = http_plugin.render_commands(context)
        self.assertIsInstance(commands, list)
        self.assertGreater(len(commands), 0)
        
        # Verify variable substitution
        self.assertIn("example.com", commands[0])
        self.assertIn("80", commands[0])
        self.assertIn("30", commands[0])
    
    @patch('ipcrawler.yaml_plugins.YAMLPluginLoader.load_plugins')
    def test_load_yaml_plugins_function(self, mock_load):
        """Test load_yaml_plugins convenience function"""
        mock_plugin = Mock()
        mock_plugin.name = "test-plugin"
        mock_load.return_value = [mock_plugin]
        
        plugins = load_yaml_plugins(str(self.plugin_dir))
        
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].name, "test-plugin")
        mock_load.assert_called_once()


class TestYAMLPluginValidation(unittest.TestCase):
    """Test YAML plugin validation functionality"""
    
    def test_valid_plugin_schema(self):
        """Test validation of valid plugin schema"""
        valid_plugin = {
            "metadata": {
                "name": "valid-plugin",
                "description": "A valid plugin",
                "version": "1.0.0",
                "category": "test"
            },
            "conditions": {
                "service_names": ["http"],
                "port_numbers": [80]
            },
            "execution": {
                "commands": ["echo 'test'"]
            }
        }
        
        self.assertTrue(validate_plugin_schema(valid_plugin))
    
    def test_invalid_plugin_missing_metadata(self):
        """Test validation with missing metadata"""
        invalid_plugin = {
            "conditions": {
                "service_names": ["http"]
            },
            "execution": {
                "commands": ["echo 'test'"]
            }
        }
        
        self.assertFalse(validate_plugin_schema(invalid_plugin))
    
    def test_invalid_plugin_missing_execution(self):
        """Test validation with missing execution section"""
        invalid_plugin = {
            "metadata": {
                "name": "invalid-plugin",
                "description": "Missing execution",
                "version": "1.0.0"
            },
            "conditions": {
                "service_names": ["http"]
            }
        }
        
        self.assertFalse(validate_plugin_schema(invalid_plugin))
    
    def test_invalid_plugin_empty_commands(self):
        """Test validation with empty commands"""
        invalid_plugin = {
            "metadata": {
                "name": "invalid-plugin",
                "description": "Empty commands",
                "version": "1.0.0"
            },
            "conditions": {
                "service_names": ["http"]
            },
            "execution": {
                "commands": []
            }
        }
        
        self.assertFalse(validate_plugin_schema(invalid_plugin))


if __name__ == '__main__':
    unittest.main(verbosity=2)