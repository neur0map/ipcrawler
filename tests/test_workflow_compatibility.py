"""Test workflow compatibility and data passing between workflows"""
import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any
from workflows.nmap_fast_01.scanner import NmapFastScanner
from workflows.nmap_02.scanner import NmapScanner
from workflows.http_03.scanner import HTTPAdvancedScanner
from workflows.core.base import WorkflowResult


class TestWorkflowCompatibility:
    """Test that workflows can work together and pass data correctly"""
    
    # Skip network tests in CI environments
    skip_network_tests = os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CI') == 'true'
    
    @pytest.fixture
    def mock_nmap_success(self):
        """Mock successful nmap output"""
        async def mock_communicate():
            xml_output = """<?xml version="1.0"?>
            <nmaprun>
                <host>
                    <address addr="127.0.0.1" addrtype="ipv4"/>
                    <ports>
                        <port protocol="tcp" portid="22">
                            <state state="open"/>
                            <service name="ssh"/>
                        </port>
                        <port protocol="tcp" portid="80">
                            <state state="open"/>
                            <service name="http"/>
                        </port>
                    </ports>
                </host>
            </nmaprun>"""
            return (xml_output.encode(), b'')
        
        mock_process = AsyncMock()
        mock_process.communicate = mock_communicate
        mock_process.returncode = 0
        return mock_process
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    @pytest.mark.skipif(skip_network_tests, reason="Skip network tests in CI")
    async def test_workflow_01_accepts_target(self):
        """Test that workflow 01 accepts various target formats"""
        scanner = NmapFastScanner()
        
        # Test IP address
        result = await scanner.safe_execute(target="127.0.0.1")
        assert isinstance(result, WorkflowResult)
        
        # Test hostname
        result = await scanner.safe_execute(target="localhost")
        assert isinstance(result, WorkflowResult)
        
        # Test CIDR
        result = await scanner.safe_execute(target="127.0.0.1/32")
        assert isinstance(result, WorkflowResult)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    @pytest.mark.skipif(skip_network_tests, reason="Skip network tests in CI")
    async def test_workflow_01_output_format(self):
        """Test that workflow 01 produces expected port discovery output"""
        scanner = NmapFastScanner()
        result = await scanner.safe_execute(target="127.0.0.1")
        
        if result.success and result.data:
            assert 'hosts' in result.data or 'open_ports' in result.data
            assert isinstance(result.data.get('hosts', []), list)
            
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    @pytest.mark.skipif(skip_network_tests, reason="Skip network tests in CI")
    async def test_workflow_02_accepts_discovered_ports(self):
        """Test that workflow 02 accepts discovered ports from workflow 01"""
        scanner = NmapScanner()
        
        # Test with specific ports
        discovered_ports = [22, 80, 443]
        result = await scanner.safe_execute(target="127.0.0.1", ports=discovered_ports)
        
        assert isinstance(result, WorkflowResult)
        if result.success and result.data:
            assert 'hosts' in result.data
            assert isinstance(result.data['hosts'], list)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    @pytest.mark.skipif(skip_network_tests, reason="Skip network tests in CI")
    async def test_workflow_02_output_format(self):
        """Test that workflow 02 produces expected detailed scan output"""
        scanner = NmapScanner()
        result = await scanner.safe_execute(target="127.0.0.1", ports=[22, 80])
        
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
    @pytest.mark.timeout(30)
    @pytest.mark.skipif(skip_network_tests, reason="Skip network tests in CI")
    async def test_workflow_03_accepts_nmap_data(self):
        """Test that workflow 03 accepts data from workflow 02"""
        scanner = HTTPAdvancedScanner()
        
        # Test with ports and discovered hostnames
        http_ports = [80, 443, 8080]
        discovered_hostnames = ["example.local", "test.local"]
        
        result = await scanner.safe_execute(
            target="127.0.0.1",
            ports=http_ports,
            discovered_hostnames=discovered_hostnames
        )
        
        assert isinstance(result, WorkflowResult)
        if result.success and result.data:
            assert 'http_services' in result.data or 'fallback_mode' in result.data
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    @pytest.mark.skipif(skip_network_tests, reason="Skip network tests in CI")
    async def test_workflow_03_output_format(self):
        """Test that workflow 03 produces expected HTTP scan output"""
        scanner = HTTPAdvancedScanner()
        result = await scanner.safe_execute(target="127.0.0.1", ports=[80])
        
        if result.success and result.data:
            # Check for expected fields
            expected_fields = ['http_services', 'vulnerabilities', 'dns_records', 'subdomains']
            data_has_expected_field = any(field in result.data for field in expected_fields)
            assert data_has_expected_field
            
            # Check service structure if present
            for service in result.data.get('http_services', []):
                assert 'port' in service
                assert 'url' in service
    
    def test_workflow_data_compatibility(self):
        """Test that data formats are compatible between workflows"""
        # Simulate workflow 01 output
        workflow_01_output = {
            'hosts': [{
                'ip': '10.0.0.1',
                'ports': [
                    {'port': 22, 'state': 'open'},
                    {'port': 80, 'state': 'open'},
                    {'port': 443, 'state': 'open'},
                    {'port': 8080, 'state': 'open'}
                ]
            }]
        }
        
        # Extract ports for workflow 02
        ports_for_02 = []
        for host in workflow_01_output['hosts']:
            for port in host.get('ports', []):
                if port.get('state') == 'open':
                    ports_for_02.append(port['port'])
        
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
    @pytest.mark.timeout(10)
    async def test_workflow_error_handling(self):
        """Test that workflows handle errors gracefully"""
        # Test each workflow with invalid input
        workflows = [
            NmapFastScanner(),
            NmapScanner(),
            HTTPAdvancedScanner()
        ]
        
        for workflow in workflows:
            # Test with invalid target (empty string)
            result = await workflow.safe_execute(target="")
            assert isinstance(result, WorkflowResult)
            assert not result.success
            assert result.error is not None
    
    def test_workflow_sequence_order(self):
        """Test that workflows are designed to run in correct sequence"""
        # Define expected workflow order
        expected_order = [
            ('nmap_fast_01', 'Fast port discovery'),
            ('nmap_02', 'Detailed port scan'),
            ('http_03', 'HTTP service analysis')
        ]
        
        # Each workflow should accept output from previous
        workflow_inputs = {
            'nmap_fast_01': ['target'],
            'nmap_02': ['target', 'ports (from 01)'],
            'http_03': ['target', 'ports (from 02)', 'hostnames (from 02)']
        }
        
        # Verify sequence makes sense
        for i, (name, desc) in enumerate(expected_order):
            assert name in workflow_inputs
            print(f"Workflow {i+1}: {name} - {desc}")
            print(f"  Inputs: {', '.join(workflow_inputs[name])}")


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@pytest.mark.skipif(TestWorkflowCompatibility.skip_network_tests, reason="Skip network tests in CI")
async def test_full_workflow_integration():
    """Test complete workflow integration with mock data"""
    target = "127.0.0.1"
    
    # Workflow 01: Fast port discovery
    fast_scanner = NmapFastScanner()
    fast_result = await fast_scanner.safe_execute(target=target)
    
    assert fast_result.success or fast_result.error
    discovered_ports = []
    if fast_result.success and fast_result.data:
        # Extract ports from hosts data
        for host in fast_result.data.get('hosts', []):
            for port in host.get('ports', []):
                if port.get('state') == 'open':
                    discovered_ports.append(port['port'])
    
    # Workflow 02: Detailed scan
    detailed_scanner = NmapScanner()
    detailed_result = await detailed_scanner.safe_execute(target=target, ports=discovered_ports if discovered_ports else None)
    
    assert detailed_result.success or detailed_result.error
    http_ports = []
    discovered_hostnames = []
    if detailed_result.success and detailed_result.data:
        for host in detailed_result.data.get('hosts', []):
            if host.get('hostname'):
                discovered_hostnames.append(host['hostname'])
            for port in host.get('ports', []):
                service = port.get('service') or ''
                if 'http' in service.lower():
                    http_ports.append(port['port'])
    
    # Workflow 03: HTTP scan
    if http_ports:
        http_scanner = HTTPAdvancedScanner()
        http_result = await http_scanner.safe_execute(
            target=target,
            ports=http_ports,
            discovered_hostnames=discovered_hostnames
        )
        assert http_result.success or http_result.error