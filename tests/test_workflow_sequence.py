"""Test workflow startup sequence and dependencies"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflows.redirect_discovery_00.scanner import RedirectDiscoveryScanner
from workflows.nmap_fast_01.scanner import NmapFastScanner
from workflows.nmap_02.scanner import NmapScanner
from workflows.http_03.scanner import HTTPAdvancedScanner


def test_workflow_order():
    """Validate that workflows are numbered correctly and follow logical sequence"""
    
    # Define workflow sequence with dependencies
    workflow_sequence = [
        {
            'number': '00',
            'name': 'redirect_discovery',
            'class': RedirectDiscoveryScanner,
            'purpose': 'Discover hostnames via HTTP redirects',
            'inputs': ['target'],
            'outputs': ['discovered_mappings', 'etc_hosts_updated'],
            'required': False  # Optional workflow
        },
        {
            'number': '01',
            'name': 'nmap_fast',
            'class': NmapFastScanner,
            'purpose': 'Fast port discovery',
            'inputs': ['target'],
            'outputs': ['open_ports', 'tool'],
            'required': True
        },
        {
            'number': '02',
            'name': 'nmap',
            'class': NmapScanner,
            'purpose': 'Detailed port and service scan',
            'inputs': ['target', 'ports (optional from 01)'],
            'outputs': ['hosts', 'ports', 'services', 'scripts'],
            'required': True
        },
        {
            'number': '03',
            'name': 'http',
            'class': HTTPAdvancedScanner,
            'purpose': 'Advanced HTTP service analysis',
            'inputs': ['target', 'ports (from 02)', 'discovered_hostnames (from 00 or 02)'],
            'outputs': ['services', 'vulnerabilities', 'dns_records', 'technologies'],
            'required': False  # Only if HTTP services found
        }
    ]
    
    print("\n=== WORKFLOW STARTUP SEQUENCE ===\n")
    
    # Validate sequence
    for i, workflow in enumerate(workflow_sequence):
        print(f"Workflow {workflow['number']}: {workflow['name']}")
        print(f"  Purpose: {workflow['purpose']}")
        print(f"  Required: {'Yes' if workflow['required'] else 'No (conditional)'}")
        print(f"  Inputs: {', '.join(workflow['inputs'])}")
        print(f"  Outputs: {', '.join(workflow['outputs'])}")
        
        # Check class exists
        assert workflow['class'] is not None, f"Workflow {workflow['number']} class not found"
        
        # Check workflow has proper name attribute
        instance = workflow['class']()
        assert hasattr(instance, 'name'), f"Workflow {workflow['number']} missing name attribute"
        assert workflow['name'] in instance.name, f"Workflow name mismatch: {instance.name} vs {workflow['name']}"
        
        print(f"  ✓ Class verified: {workflow['class'].__name__}")
        print()
    
    # Validate data flow
    print("=== DATA FLOW VALIDATION ===\n")
    
    # Check that each workflow's inputs are satisfied by previous workflows
    available_outputs = {'target'}  # Initial input
    
    for workflow in workflow_sequence:
        print(f"Checking {workflow['name']}...")
        
        # Parse inputs
        for input_item in workflow['inputs']:
            if '(' in input_item:
                # Extract base input name
                base_input = input_item.split('(')[0].strip()
            else:
                base_input = input_item
            
            # Special handling for known inputs
            if base_input == 'target':
                assert 'target' in available_outputs
            elif base_input == 'ports':
                assert 'open_ports' in available_outputs or 'ports' in available_outputs
            elif base_input == 'discovered_hostnames':
                # This can come from multiple sources
                assert any(out in available_outputs for out in ['discovered_mappings', 'hostname', 'hostnames'])
        
        # Add outputs to available data
        for output in workflow['outputs']:
            available_outputs.add(output)
        
        print(f"  ✓ All inputs satisfied")
        print(f"  Available data after: {sorted(available_outputs)}")
        print()
    
    print("=== WORKFLOW SEQUENCE VALIDATED ===")
    return True


def test_workflow_dependencies():
    """Test that workflow dependencies are properly defined"""
    
    # Map of workflow dependencies
    dependencies = {
        'redirect_discovery_00': {
            'requires': [],
            'optional': True,
            'enhances': ['nmap_02', 'http_03']  # Provides hostnames
        },
        'nmap_fast_01': {
            'requires': [],
            'optional': False,
            'provides_to': ['nmap_02']  # Provides port list
        },
        'nmap_02': {
            'requires': [],  # Can run standalone or with ports from 01
            'optional': False,
            'enhanced_by': ['nmap_fast_01', 'redirect_discovery_00'],
            'provides_to': ['http_03']
        },
        'http_03': {
            'requires': ['nmap_02'],  # Needs to know which ports have HTTP
            'optional': True,  # Only runs if HTTP services found
            'enhanced_by': ['redirect_discovery_00', 'nmap_02']
        }
    }
    
    print("\n=== WORKFLOW DEPENDENCIES ===\n")
    
    for workflow, deps in dependencies.items():
        print(f"{workflow}:")
        print(f"  Optional: {deps['optional']}")
        print(f"  Requires: {deps['requires'] or 'None'}")
        
        if 'enhanced_by' in deps:
            print(f"  Enhanced by: {deps['enhanced_by']}")
        if 'provides_to' in deps:
            print(f"  Provides data to: {deps['provides_to']}")
        if 'enhances' in deps:
            print(f"  Enhances: {deps['enhances']}")
        print()
    
    return True


if __name__ == "__main__":
    test_workflow_order()
    test_workflow_dependencies()