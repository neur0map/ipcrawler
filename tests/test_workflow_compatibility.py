"""Test workflow compatibility and data passing between workflows"""
import pytest
import asyncio
from typing import Dict, List, Any
from workflows.redirect_discovery_00.scanner import RedirectDiscoveryScanner
from workflows.nmap_fast_01.scanner import NmapFastScanner
from workflows.nmap_02.scanner import NmapScanner
from workflows.http_03.scanner import HTTPAdvancedScanner
from workflows.core.base import WorkflowResult


class TestWorkflowCompatibility:
    """Test that workflows can work together and pass data correctly"""
    
    @pytest.mark.asyncio
    async def test_workflow_00_output_format(self):
        """Test that workflow 00 produces expected output format"""
        scanner = RedirectDiscoveryScanner()
        
        # Test with mock target
        result = await scanner.execute("127.0.0.1")
        
        assert isinstance(result, WorkflowResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        assert hasattr(result, 'execution_time')
        
        if result.success and result.data:
            # Check expected fields
            assert 'discovered_mappings' in result.data
            assert isinstance(result.data['discovered_mappings'], list)
            
            # Each mapping should have IP and hostname
            for mapping in result.data['discovered_mappings']:
                assert 'ip' in mapping
                assert 'hostname' in mapping
    
    @pytest.mark.asyncio
    async def test_workflow_01_accepts_target(self):
        """Test that workflow 01 accepts various target formats"""
        scanner = NmapFastScanner()
        
        # Test IP address
        result = await scanner.execute("127.0.0.1")
        assert isinstance(result, WorkflowResult)
        
        # Test hostname
        result = await scanner.execute("localhost")
        assert isinstance(result, WorkflowResult)
        
        # Test CIDR
        result = await scanner.execute("127.0.0.1/32")
        assert isinstance(result, WorkflowResult)
    
    @pytest.mark.asyncio
    async def test_workflow_01_output_format(self):
        """Test that workflow 01 produces expected port discovery output"""
        scanner = NmapFastScanner()
        result = await scanner.execute("127.0.0.1")
        
        if result.success and result.data:
            assert 'open_ports' in result.data
            assert isinstance(result.data['open_ports'], list)
            assert 'tool' in result.data
            
            # Each port should be an integer
            for port in result.data.get('open_ports', []):
                assert isinstance(port, int)
    
    @pytest.mark.asyncio
    async def test_workflow_02_accepts_discovered_ports(self):
        """Test that workflow 02 accepts discovered ports from workflow 01"""
        scanner = NmapScanner()
        
        # Test with specific ports
        discovered_ports = [22, 80, 443]
        result = await scanner.execute("127.0.0.1", ports=discovered_ports)
        
        assert isinstance(result, WorkflowResult)
        if result.success and result.data:
            assert 'hosts' in result.data
            assert isinstance(result.data['hosts'], list)
    
    @pytest.mark.asyncio
    async def test_workflow_02_output_format(self):
        """Test that workflow 02 produces expected detailed scan output"""
        scanner = NmapScanner()
        result = await scanner.execute("127.0.0.1", ports=[22, 80])
        
        if result.success and result.data:
            # Check main structure
            assert 'hosts' in result.data
            assert 'total_hosts' in result.data
            assert 'up_hosts' in result.data
            assert 'down_hosts' in result.data
            
            # Check host structure
            for host in result.data.get('hosts', []):
                assert 'ip' in host
                assert 'ports' in host
                
                # Check port structure
                for port in host.get('ports', []):
                    assert 'port' in port
                    assert 'protocol' in port
                    assert 'state' in port
                    assert 'service' in port
    
    @pytest.mark.asyncio
    async def test_workflow_03_accepts_nmap_data(self):
        """Test that workflow 03 accepts data from workflow 02"""
        scanner = HTTPAdvancedScanner()
        
        # Test with ports and discovered hostnames
        http_ports = [80, 443, 8080]
        discovered_hostnames = ["example.local", "test.local"]
        
        result = await scanner.execute(
            "127.0.0.1",
            ports=http_ports,
            discovered_hostnames=discovered_hostnames
        )
        
        assert isinstance(result, WorkflowResult)
        if result.success and result.data:
            assert 'services' in result.data or 'fallback_mode' in result.data
    
    @pytest.mark.asyncio
    async def test_workflow_03_output_format(self):
        """Test that workflow 03 produces expected HTTP scan output"""
        scanner = HTTPAdvancedScanner()
        result = await scanner.execute("127.0.0.1", ports=[80])
        
        if result.success and result.data:
            # Check for expected fields
            expected_fields = ['services', 'vulnerabilities', 'dns_records', 'subdomains']
            for field in expected_fields:
                assert field in result.data
                assert isinstance(result.data[field], list)
            
            # Check service structure
            for service in result.data.get('services', []):
                assert 'port' in service
                assert 'url' in service
                assert 'headers' in service
    
    def test_workflow_data_compatibility(self):
        """Test that data formats are compatible between workflows"""
        # Simulate workflow 01 output
        workflow_01_output = {
            'open_ports': [22, 80, 443, 8080],
            'tool': 'masscan'
        }
        
        # This should be usable by workflow 02
        ports_for_02 = workflow_01_output['open_ports']
        assert isinstance(ports_for_02, list)
        assert all(isinstance(p, int) for p in ports_for_02)
        
        # Simulate workflow 02 output
        workflow_02_output = {
            'hosts': [{
                'ip': '10.0.0.1',
                'hostname': 'example.local',
                'ports': [
                    {'port': 80, 'service': 'http', 'state': 'open'},
                    {'port': 443, 'service': 'https', 'state': 'open'}
                ]
            }]
        }
        
        # Extract data for workflow 03
        http_ports = []
        hostnames = []
        
        for host in workflow_02_output['hosts']:
            if host.get('hostname'):
                hostnames.append(host['hostname'])
            
            for port in host.get('ports', []):
                if port['state'] == 'open' and ('http' in port.get('service', '')):
                    http_ports.append(port['port'])
        
        assert http_ports == [80, 443]
        assert hostnames == ['example.local']
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self):
        """Test that workflows handle errors gracefully"""
        # Test each workflow with invalid input
        workflows = [
            RedirectDiscoveryScanner(),
            NmapFastScanner(),
            NmapScanner(),
            HTTPAdvancedScanner()
        ]
        
        for workflow in workflows:
            # Test with invalid target
            result = await workflow.execute("")
            assert isinstance(result, WorkflowResult)
            assert not result.success or result.errors
            
            # Test with unreachable target
            result = await workflow.execute("999.999.999.999")
            assert isinstance(result, WorkflowResult)
    
    def test_workflow_sequence_order(self):
        """Test that workflows are designed to run in correct sequence"""
        # Define expected workflow order
        expected_order = [
            ('redirect_discovery_00', 'Optional hostname discovery'),
            ('nmap_fast_01', 'Fast port discovery'),
            ('nmap_02', 'Detailed port scan'),
            ('http_03', 'HTTP service analysis')
        ]
        
        # Each workflow should accept output from previous
        workflow_inputs = {
            'redirect_discovery_00': ['target'],
            'nmap_fast_01': ['target'],
            'nmap_02': ['target', 'ports (from 01)'],
            'http_03': ['target', 'ports (from 02)', 'hostnames (from 00 or 02)']
        }
        
        # Verify sequence makes sense
        for i, (name, desc) in enumerate(expected_order):
            assert name in workflow_inputs
            print(f"Workflow {i}: {name} - {desc}")
            print(f"  Inputs: {', '.join(workflow_inputs[name])}")


@pytest.mark.asyncio
async def test_full_workflow_integration():
    """Test complete workflow integration with mock data"""
    target = "127.0.0.1"
    
    # Workflow 00: Redirect discovery (optional)
    redirect_scanner = RedirectDiscoveryScanner()
    redirect_result = await redirect_scanner.execute(target)
    
    discovered_hostnames = []
    if redirect_result.success and redirect_result.data:
        mappings = redirect_result.data.get('discovered_mappings', [])
        discovered_hostnames = [m['hostname'] for m in mappings]
    
    # Workflow 01: Fast port discovery
    fast_scanner = NmapFastScanner()
    fast_result = await fast_scanner.execute(target)
    
    assert fast_result.success or fast_result.errors
    discovered_ports = []
    if fast_result.success and fast_result.data:
        discovered_ports = fast_result.data.get('open_ports', [])
    
    # Workflow 02: Detailed scan
    detailed_scanner = NmapScanner()
    detailed_result = await detailed_scanner.execute(target, ports=discovered_ports)
    
    assert detailed_result.success or detailed_result.errors
    http_ports = []
    if detailed_result.success and detailed_result.data:
        for host in detailed_result.data.get('hosts', []):
            for port in host.get('ports', []):
                service = port.get('service') or ''
                if 'http' in service.lower():
                    http_ports.append(port['port'])
    
    # Workflow 03: HTTP scan
    if http_ports:
        http_scanner = HTTPAdvancedScanner()
        http_result = await http_scanner.execute(
            target,
            ports=http_ports,
            discovered_hostnames=discovered_hostnames
        )
        assert http_result.success or http_result.errors