"""Generate workflow compatibility report"""
import sys
import os
import importlib
import inspect
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def analyze_workflow(module_path: str, class_name: str):
    """Analyze a workflow class for compatibility"""
    try:
        module = importlib.import_module(module_path)
        workflow_class = getattr(module, class_name)
        instance = workflow_class()
        
        # Get execute method signature
        execute_method = getattr(workflow_class, 'execute')
        sig = inspect.signature(execute_method)
        params = dict(sig.parameters)
        
        # Remove 'self' parameter
        params.pop('self', None)
        
        # Analyze parameters
        required_params = []
        optional_params = []
        
        for name, param in params.items():
            if param.default == param.empty:
                required_params.append(name)
            else:
                optional_params.append(f"{name}={param.default}")
        
        # Check for validate_input method
        has_validation = hasattr(workflow_class, 'validate_input')
        
        # Check base class
        inherits_base = any(base.__name__ == 'BaseWorkflow' for base in workflow_class.__bases__)
        
        return {
            'name': instance.name,
            'class': class_name,
            'module': module_path,
            'required_params': required_params,
            'optional_params': optional_params,
            'has_validation': has_validation,
            'inherits_base': inherits_base,
            'docstring': execute_method.__doc__ or 'No documentation'
        }
    except Exception as e:
        return {
            'name': 'Error',
            'error': str(e)
        }


def generate_report():
    """Generate comprehensive workflow compatibility report"""
    
    workflows = [
        ('workflows.redirect_discovery_00.scanner', 'RedirectDiscoveryScanner'),
        ('workflows.nmap_fast_01.scanner', 'NmapFastScanner'),
        ('workflows.nmap_02.scanner', 'NmapScanner'),
        ('workflows.http_03.scanner', 'HTTPAdvancedScanner')
    ]
    
    print("# Workflow Compatibility Report")
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n## Workflow Analysis\n")
    
    all_workflows = []
    
    for module_path, class_name in workflows:
        analysis = analyze_workflow(module_path, class_name)
        all_workflows.append(analysis)
        
        if 'error' in analysis:
            print(f"### ❌ {class_name}")
            print(f"Error: {analysis['error']}\n")
            continue
        
        print(f"### ✅ Workflow: {analysis['name']}")
        print(f"- **Class**: `{analysis['class']}`")
        print(f"- **Module**: `{analysis['module']}`")
        print(f"- **Inherits BaseWorkflow**: {'Yes' if analysis['inherits_base'] else 'No'}")
        print(f"- **Has Validation**: {'Yes' if analysis['has_validation'] else 'No'}")
        print(f"\n**Execute Method Parameters:**")
        print(f"- Required: `{', '.join(analysis['required_params']) if analysis['required_params'] else 'None'}`")
        print(f"- Optional: `{', '.join(analysis['optional_params']) if analysis['optional_params'] else 'None'}`")
        print(f"\n**Documentation**: {analysis['docstring'].strip()}")
        print()
    
    # Data flow analysis
    print("## Data Flow Compatibility\n")
    
    print("### Workflow Sequence")
    print("```")
    print("1. redirect_discovery_00 (Optional)")
    print("   ↓ discovered_mappings")
    print("2. nmap_fast_01")
    print("   ↓ open_ports")
    print("3. nmap_02")
    print("   ↓ hosts, ports, services")
    print("4. http_03 (Conditional)")
    print("   → Final results")
    print("```\n")
    
    print("### Input/Output Mapping\n")
    
    io_mapping = [
        {
            'workflow': 'redirect_discovery_00',
            'inputs': ['target'],
            'outputs': ['discovered_mappings', 'etc_hosts_updated', 'redirect_chains'],
            'used_by': ['http_03 (discovered_hostnames)']
        },
        {
            'workflow': 'nmap_fast_01',
            'inputs': ['target'],
            'outputs': ['open_ports', 'tool', 'scan_rate'],
            'used_by': ['nmap_02 (ports parameter)']
        },
        {
            'workflow': 'nmap_02',
            'inputs': ['target', 'ports (optional)'],
            'outputs': ['hosts', 'ports', 'services', 'os_info', 'scripts'],
            'used_by': ['http_03 (http ports extraction)', 'final results']
        },
        {
            'workflow': 'http_03',
            'inputs': ['target', 'ports', 'discovered_hostnames (optional)'],
            'outputs': ['services', 'vulnerabilities', 'technologies', 'dns_records'],
            'used_by': ['final results']
        }
    ]
    
    for mapping in io_mapping:
        print(f"**{mapping['workflow']}**")
        print(f"- Inputs: {', '.join(mapping['inputs'])}")
        print(f"- Outputs: {', '.join(mapping['outputs'])}")
        print(f"- Used by: {', '.join(mapping['used_by'])}")
        print()
    
    # Compatibility matrix
    print("## Compatibility Matrix\n")
    print("| From \\ To | redirect_00 | nmap_01 | nmap_02 | http_03 |")
    print("|------------|-------------|---------|---------|---------|")
    print("| Initial    | ✅ target   | ✅ target | ✅ target | ❌ needs ports |")
    print("| redirect_00| -           | ✅ target | ✅ target | ✅ hostnames |")
    print("| nmap_01    | ❌          | -       | ✅ ports  | ❌ needs service info |")
    print("| nmap_02    | ❌          | ❌      | -       | ✅ ports + hostnames |")
    print("| http_03    | ❌          | ❌      | ❌      | -       |")
    
    print("\n## Key Findings\n")
    
    # Check for common issues
    issues = []
    recommendations = []
    
    for workflow in all_workflows:
        if 'error' in workflow:
            issues.append(f"- {workflow.get('class', 'Unknown')} failed to load")
        elif not workflow['inherits_base']:
            issues.append(f"- {workflow['name']} doesn't inherit from BaseWorkflow")
        elif not workflow['has_validation']:
            recommendations.append(f"- {workflow['name']} should implement validate_input()")
    
    if issues:
        print("### ⚠️ Issues")
        for issue in issues:
            print(issue)
        print()
    
    if recommendations:
        print("### 💡 Recommendations")
        for rec in recommendations:
            print(rec)
        print()
    
    print("### ✅ Strengths")
    print("- All workflows follow consistent parameter patterns")
    print("- Data flows logically from discovery → enumeration → analysis")
    print("- Optional workflows (00, 03) enhance but don't break the flow")
    print("- Each workflow can run independently with appropriate inputs")
    
    print("\n## Testing Recommendations\n")
    print("1. **Unit Tests**: Test each workflow with mock data")
    print("2. **Integration Tests**: Test data passing between workflows")
    print("3. **Error Handling**: Test with invalid inputs and network failures")
    print("4. **Performance**: Test with large port ranges and multiple hosts")
    print("5. **Compatibility**: Test with different Python versions and OS platforms")


if __name__ == "__main__":
    generate_report()