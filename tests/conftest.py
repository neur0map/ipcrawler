#!/usr/bin/env python3
"""
Pytest configuration and fixtures for ipcrawler tests
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
import yaml

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_config():
    """Provide sample configuration for tests"""
    return {
        "general": {
            "verbosity": 1,
            "output_dir": "results",
            "max_concurrent_targets": 5
        },
        "scanning": {
            "default_ports": "80,443,22,21",
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


@pytest.fixture
def sample_plugin_data():
    """Provide sample YAML plugin data for tests"""
    return {
        "metadata": {
            "name": "test-plugin",
            "description": "Test plugin for unit tests",
            "author": "Test Suite",
            "version": "1.0.0",
            "category": "test"
        },
        "conditions": {
            "service_names": ["http", "https"],
            "port_numbers": [80, 443, 8080, 8443]
        },
        "variables": {
            "timeout": 30,
            "user_agent": "ipcrawler-test",
            "max_redirects": 5
        },
        "execution": {
            "commands": [
                "echo 'Starting test for {target}:{port}'",
                "curl -s -A '{user_agent}' --max-time {timeout} --max-redirs {max_redirects} http://{target}:{port}/"
            ]
        },
        "output": {
            "file_patterns": ["*.log", "*.txt"],
            "extract_patterns": {
                "http_status": r"HTTP/1\.[01] (\d{3})",
                "server_header": r"Server: (.+)",
                "title": r"<title>(.+?)</title>"
            }
        }
    }


@pytest.fixture
def plugin_directory(temp_dir, sample_plugin_data):
    """Create a temporary plugin directory with test plugins"""
    plugin_dir = Path(temp_dir) / "test-plugins"
    plugin_dir.mkdir()
    
    # Create test plugin categories
    categories = [
        "01-discovery",
        "02-enumeration", 
        "02-service-enumeration/web-services",
        "03-bruteforce"
    ]
    
    for category in categories:
        category_path = plugin_dir / category
        category_path.mkdir(parents=True, exist_ok=True)
    
    # Create sample HTTP plugin
    http_plugin = sample_plugin_data.copy()
    http_plugin["metadata"]["name"] = "http-test"
    http_plugin["metadata"]["category"] = "web"
    
    with open(plugin_dir / "02-service-enumeration/web-services/http-test.yaml", 'w') as f:
        yaml.dump(http_plugin, f)
    
    # Create sample SSH plugin
    ssh_plugin = {
        "metadata": {
            "name": "ssh-test",
            "description": "SSH test plugin",
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
                "echo 'Testing SSH on {target}:{port}'",
                "nc -zv -w {timeout} {target} {port}"
            ]
        },
        "output": {
            "file_patterns": ["*.log"],
            "extract_patterns": {
                "ssh_version": r"SSH-([0-9.]+)"
            }
        }
    }
    
    with open(plugin_dir / "02-enumeration/ssh-test.yaml", 'w') as f:
        yaml.dump(ssh_plugin, f)
    
    # Create discovery plugin
    discovery_plugin = {
        "metadata": {
            "name": "port-discovery",
            "description": "Port discovery plugin",
            "version": "1.0.0",
            "category": "discovery"
        },
        "conditions": {
            "always_run": True
        },
        "variables": {
            "timing": "T4",
            "ports": "80,443,22,21"
        },
        "execution": {
            "commands": [
                "echo 'Scanning {target}'",
                "nmap -Pn -{timing} -p {ports} {target}"
            ]
        },
        "output": {
            "file_patterns": ["*.xml", "*.nmap"],
            "extract_patterns": {
                "open_ports": r"(\d+)/(tcp|udp)\s+open"
            }
        }
    }
    
    with open(plugin_dir / "01-discovery/port-discovery.yaml", 'w') as f:
        yaml.dump(discovery_plugin, f)
    
    return str(plugin_dir)


@pytest.fixture
def sample_target():
    """Provide a sample target for tests"""
    from ipcrawler.targets import Target, Service
    
    target = Target("192.168.1.100", hostname="test.example.com")
    
    # Add sample services
    http_service = Service("http", 80, "tcp", state="open", product="Apache", version="2.4")
    https_service = Service("https", 443, "tcp", state="open", product="Apache", version="2.4")
    ssh_service = Service("ssh", 22, "tcp", state="open", product="OpenSSH", version="8.0")
    
    target.add_service(http_service)
    target.add_service(https_service)
    target.add_service(ssh_service)
    
    return target


@pytest.fixture
def mock_scan_results(temp_dir):
    """Create mock scan results for testing"""
    results_dir = Path(temp_dir) / "results" / "192.168.1.100"
    scans_dir = results_dir / "scans"
    scans_dir.mkdir(parents=True)
    
    # Create mock scan logs
    nmap_log = scans_dir / "nmap.log"
    nmap_log.write_text("""
Starting Nmap 7.80 ( https://nmap.org ) at 2024-01-01 12:00 UTC
Nmap scan report for test.example.com (192.168.1.100)
Host is up (0.0010s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.0 (Ubuntu 20.04.1)
80/tcp open  http    Apache httpd 2.4.41
443/tcp open  https   Apache httpd 2.4.41

Nmap done: 1 IP address (1 host up) scanned in 2.34 seconds
""")
    
    # Create mock HTTP scan log
    http_log = scans_dir / "curl.log"
    http_log.write_text("""
HTTP/1.1 200 OK
Server: Apache/2.4.41 (Ubuntu)
Content-Type: text/html
Content-Length: 1234

<html>
<head><title>Test Site</title></head>
<body><h1>Welcome to Test Site</h1></body>
</html>
""")
    
    # Create mock error log
    error_log = scans_dir / "errors.log"
    error_log.write_text("# No errors recorded\n")
    
    return str(results_dir)


@pytest.fixture(scope="session")
def ipcrawler_root():
    """Provide path to ipcrawler root directory"""
    return Path(__file__).parent.parent


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for component interaction")
    config.addinivalue_line("markers", "e2e: End-to-end tests for complete workflows")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")
    config.addinivalue_line("markers", "network: Tests that require network access")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add markers based on test file names
        if "test_e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
        elif "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Add network marker for tests that use real network
        if "localhost" in item.nodeid.lower() or "127.0.0.1" in item.nodeid.lower():
            item.add_marker(pytest.mark.network)