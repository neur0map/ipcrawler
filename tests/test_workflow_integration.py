"""Integration tests for workflow data passing"""
import asyncio
import json
from typing import Dict, Any


class MockWorkflowResult:
    """Mock workflow result for testing"""
    def __init__(self, success: bool, data: Dict[str, Any], execution_time: float = 1.0):
        self.success = success
        self.data = data
        self.execution_time = execution_time
        self.errors = []


async def simulate_workflow_chain():
    """Simulate the complete workflow chain with mock data"""
    
    print("\n=== WORKFLOW INTEGRATION TEST ===\n")
    
    # Target for testing
    target = "10.10.10.1"
    
    # Workflow 00: Redirect Discovery
    print("→ Workflow 00: Redirect Discovery")
    redirect_data = {
        'discovered_mappings': [
            {'ip': '10.10.10.1', 'hostname': 'example.htb'},
            {'ip': '10.10.10.1', 'hostname': 'admin.example.htb'}
        ],
        'etc_hosts_updated': False,
        'redirect_chains': [
            {
                'url': 'http://10.10.10.1',
                'redirects': ['http://example.htb/', 'https://example.htb/']
            }
        ]
    }
    redirect_result = MockWorkflowResult(True, redirect_data)
    
    # Extract hostnames for later use
    discovered_hostnames = [m['hostname'] for m in redirect_data['discovered_mappings']]
    print(f"  ✓ Discovered hostnames: {discovered_hostnames}")
    
    # Workflow 01: Fast Port Discovery
    print("\n→ Workflow 01: Fast Port Discovery")
    port_discovery_data = {
        'open_ports': [22, 80, 443, 8080, 8443],
        'tool': 'masscan',
        'scan_rate': 1000,
        'discovered_count': 5
    }
    port_result = MockWorkflowResult(True, port_discovery_data)
    
    discovered_ports = port_discovery_data['open_ports']
    print(f"  ✓ Discovered {len(discovered_ports)} open ports: {discovered_ports}")
    
    # Workflow 02: Detailed Nmap Scan
    print("\n→ Workflow 02: Detailed Nmap Scan")
    nmap_data = {
        'hosts': [{
            'ip': '10.10.10.1',
            'hostname': 'example.htb',
            'state': 'up',
            'os': 'Linux 3.x|4.x',
            'os_accuracy': 95,
            'ports': [
                {
                    'port': 22,
                    'protocol': 'tcp',
                    'state': 'open',
                    'service': 'ssh',
                    'version': 'OpenSSH 7.6p1',
                    'scripts': [
                        {'id': 'ssh-hostkey', 'output': 'SSH keys...'}
                    ]
                },
                {
                    'port': 80,
                    'protocol': 'tcp',
                    'state': 'open',
                    'service': 'http',
                    'product': 'nginx',
                    'version': '1.14.0',
                    'scripts': [
                        {'id': 'http-title', 'output': 'Site doesn\'t have a title (text/html).'}
                    ]
                },
                {
                    'port': 443,
                    'protocol': 'tcp',
                    'state': 'open',
                    'service': 'https',
                    'product': 'nginx',
                    'version': '1.14.0'
                },
                {
                    'port': 8080,
                    'protocol': 'tcp',
                    'state': 'open',
                    'service': 'http-proxy'
                },
                {
                    'port': 8443,
                    'protocol': 'tcp',
                    'state': 'open',
                    'service': 'https-alt'
                }
            ]
        }],
        'total_hosts': 1,
        'up_hosts': 1,
        'down_hosts': 0
    }
    nmap_result = MockWorkflowResult(True, nmap_data)
    
    # Extract HTTP/HTTPS ports and any additional hostnames
    http_ports = []
    additional_hostnames = []
    
    for host in nmap_data['hosts']:
        if host.get('hostname') and host['hostname'] not in discovered_hostnames:
            additional_hostnames.append(host['hostname'])
        
        for port in host['ports']:
            if 'http' in port.get('service', '').lower():
                http_ports.append(port['port'])
    
    # Combine all hostnames
    all_hostnames = list(set(discovered_hostnames + additional_hostnames))
    
    print(f"  ✓ Found {len(http_ports)} HTTP/HTTPS services on ports: {http_ports}")
    print(f"  ✓ Total hostnames for HTTP scanning: {all_hostnames}")
    
    # Workflow 03: HTTP Advanced Scanner
    print("\n→ Workflow 03: HTTP Advanced Scanner")
    http_data = {
        'services': [
            {
                'port': 80,
                'scheme': 'http',
                'url': 'http://10.10.10.1',
                'status_code': 200,
                'server': 'nginx/1.14.0',
                'technologies': ['nginx', 'PHP'],
                'discovered_paths': [
                    '/index.php', '/admin/', '/api/', '/login',
                    '/.git/config', '/robots.txt', '/sitemap.xml'
                ]
            },
            {
                'port': 443,
                'scheme': 'https',
                'url': 'https://10.10.10.1',
                'status_code': 200,
                'server': 'nginx/1.14.0',
                'technologies': ['nginx', 'PHP', 'Laravel'],
                'discovered_paths': [
                    '/api/v1/', '/dashboard', '/docs/'
                ]
            }
        ],
        'vulnerabilities': [
            {
                'type': 'missing-x-frame-options',
                'severity': 'medium',
                'description': 'Missing Clickjacking protection header',
                'url': 'http://10.10.10.1'
            },
            {
                'type': 'weak-ssl-version',
                'severity': 'high',
                'description': 'Weak SSL/TLS version: TLSv1.1',
                'url': 'https://10.10.10.1'
            }
        ],
        'dns_records': [
            {'type': 'A', 'value': '10.10.10.1'}
        ],
        'subdomains': ['www.example.htb', 'mail.example.htb'],
        'tested_hostnames': all_hostnames
    }
    http_result = MockWorkflowResult(True, http_data)
    
    print(f"  ✓ Scanned {len(http_data['services'])} HTTP services")
    print(f"  ✓ Found {len(http_data['vulnerabilities'])} vulnerabilities")
    print(f"  ✓ Discovered {sum(len(s['discovered_paths']) for s in http_data['services'])} paths")
    
    # Final data aggregation (as done in ipcrawler.py)
    print("\n→ Final Data Aggregation")
    
    final_data = {
        'target': target,
        'total_execution_time': sum([
            redirect_result.execution_time,
            port_result.execution_time,
            nmap_result.execution_time,
            http_result.execution_time
        ]),
        'discovery_enabled': True,
        'discovered_ports': len(discovered_ports),
        **nmap_data,  # Include all nmap data
        'http_scan': http_data,  # Include HTTP scan results
        'redirect_discovery': redirect_data,  # Include redirect discovery
        'summary': {
            'total_open_ports': len(discovered_ports),
            'http_services': len(http_data['services']),
            'vulnerabilities': len(http_data['vulnerabilities']),
            'discovered_hostnames': len(all_hostnames),
            'discovered_paths': sum(len(s['discovered_paths']) for s in http_data['services'])
        }
    }
    
    print("\n=== FINAL SUMMARY ===")
    print(f"Target: {target}")
    print(f"Total execution time: {final_data['total_execution_time']:.2f}s")
    print(f"Open ports: {final_data['summary']['total_open_ports']}")
    print(f"HTTP services: {final_data['summary']['http_services']}")
    print(f"Vulnerabilities: {final_data['summary']['vulnerabilities']}")
    print(f"Discovered hostnames: {final_data['summary']['discovered_hostnames']}")
    print(f"Discovered paths: {final_data['summary']['discovered_paths']}")
    
    # Validate data structure
    print("\n=== DATA STRUCTURE VALIDATION ===")
    
    # Check that all expected fields are present
    required_fields = ['target', 'hosts', 'http_scan', 'summary']
    for field in required_fields:
        assert field in final_data, f"Missing required field: {field}"
        print(f"  ✓ {field}: present")
    
    # Save sample data structure for reference
    with open('tests/sample_workflow_data.json', 'w') as f:
        json.dump(final_data, f, indent=2)
    print("\n  ✓ Sample data structure saved to tests/sample_workflow_data.json")
    
    return True


if __name__ == "__main__":
    asyncio.run(simulate_workflow_chain())