#!/usr/bin/env python3
"""
Unit tests for ipcrawler.config module
"""

import unittest
import tempfile
import os
from pathlib import Path
import toml

# Add parent directory to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ipcrawler.config import config, configurable_keys, configurable_boolean_keys


class TestConfigManager(unittest.TestCase):
    """Test configuration management functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.toml"
        
        # Sample config content
        self.sample_config = {
            "general": {
                "verbosity": 1,
                "output_dir": "results",
                "max_concurrent_targets": 5
            },
            "scanning": {
                "default_ports": "80,443,8080,8443",
                "nmap_timing": "T4",
                "min_rate": 1000,
                "max_rate": 5000
            },
            "plugins": {
                "enable_yaml_plugins": True,
                "yaml_plugins_only": True,
                "plugin_timeout": 300
            }
        }
        
        # Write sample config
        with open(self.config_path, 'w') as f:
            toml.dump(self.sample_config, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_keys_exist(self):
        """Test that config keys are properly defined"""
        self.assertIsInstance(configurable_keys, list)
        self.assertIsInstance(configurable_boolean_keys, list)
        self.assertGreater(len(configurable_keys), 0)
        self.assertIn('ports', configurable_keys)
        self.assertIn('enable_yaml_plugins', configurable_keys)
    
    def test_config_global_access(self):
        """Test global config object access"""
        self.assertIsNotNone(config)
        # Config object should be accessible and have attributes
        self.assertTrue(hasattr(config, '__dict__') or hasattr(config, '__getitem__'))
    
    def test_boolean_keys_subset(self):
        """Test that boolean keys are subset of all keys"""
        # Boolean keys should be a subset of all configurable keys
        for bool_key in configurable_boolean_keys:
            self.assertIn(bool_key, configurable_keys)
    
    def test_yaml_plugin_keys_present(self):
        """Test that YAML plugin related keys are present"""
        yaml_keys = [
            'enable_yaml_plugins',
            'yaml_plugins_dir', 
            'debug_yaml_plugins',
            'yaml_plugins_only'
        ]
        
        for key in yaml_keys:
            self.assertIn(key, configurable_keys)


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation logic"""
    
    def test_port_validation_patterns(self):
        """Test port validation patterns"""
        # Valid port patterns
        valid_ports = ["80", "80,443", "1-65535", "80,443,8080-8090"]
        
        # Simple validation - should be strings with numbers and allowed chars
        for port_spec in valid_ports:
            self.assertIsInstance(port_spec, str)
            # Should only contain digits, commas, and hyphens
            import re
            self.assertTrue(re.match(r'^[\d,\-]+$', port_spec))
    
    def test_config_key_consistency(self):
        """Test configuration key consistency"""
        # All boolean keys should be in the main configurable keys
        for bool_key in configurable_boolean_keys:
            self.assertIn(bool_key, configurable_keys)
        
        # Check for common patterns
        self.assertIn('ports', configurable_keys)
        self.assertIn('timeout', configurable_keys)


if __name__ == '__main__':
    unittest.main(verbosity=2)