#!/usr/bin/env python3
"""
Test all YAML plugins for variable substitution issues
"""

import yaml
from pathlib import Path
import re
from jinja2 import Environment, StrictUndefined, meta
import sys

def test_plugin_variables():
    """Test all YAML plugins for unresolved variables"""
    
    print("🧪 TESTING ALL YAML PLUGINS FOR VARIABLE ISSUES")
    print("=" * 60)
    
    template_dir = Path("templates/default-template")
    if not template_dir.exists():
        print(f"❌ Template directory not found: {template_dir}")
        return False
    
    # Collect all YAML plugin files
    plugin_files = []
    for category_dir in template_dir.iterdir():
        if category_dir.is_dir():
            for yaml_file in category_dir.rglob("*.yaml"):
                if not yaml_file.name.endswith('.disabled'):
                    plugin_files.append(yaml_file)
    
    print(f"📊 Found {len(plugin_files)} YAML plugins to test")
    
    # Test variables
    issues_found = []
    jinja_env = Environment(undefined=StrictUndefined)
    
    for plugin_file in plugin_files:
        relative_path = plugin_file.relative_to(template_dir)
        print(f"\n🔍 Testing: {relative_path}")
        
        try:
            # Read raw content
            content = plugin_file.read_text()
            
            # Parse YAML
            plugin_data = yaml.safe_load(content)
            
            if not plugin_data or 'execution' not in plugin_data:
                print(f"   ⚠️ No execution section found")
                continue
            
            # Check each command for unresolved variables
            commands = plugin_data['execution'].get('commands', [])
            for i, command in enumerate(commands):
                if isinstance(command, str):
                    # Look for unresolved variables like {min_rate}, {max_rate}
                    unresolved = re.findall(r'\{([^}]+)\}', command)
                    if unresolved:
                        # Filter out Jinja2 variables (which are OK)
                        jinja_vars = set()
                        try:
                            ast = jinja_env.parse(command)
                            jinja_vars = meta.find_undeclared_variables(ast)
                        except:
                            pass
                        
                        problematic = []
                        for var in unresolved:
                            # These are common problematic variables
                            if var in ['min_rate', 'max_rate', 'timing_template', 'service_opts', 'timing_opts']:
                                problematic.append(var)
                        
                        if problematic:
                            issue = {
                                'file': relative_path,
                                'command_index': i,
                                'command': command,
                                'unresolved_vars': problematic
                            }
                            issues_found.append(issue)
                            print(f"   ❌ Command {i}: {problematic}")
            
            # Check if plugin defines variables section
            variables_section = plugin_data.get('variables', {})
            if variables_section:
                print(f"   ✅ Has variables section: {list(variables_section.keys())}")
            else:
                print(f"   ⚠️ No variables section defined")
        
        except Exception as e:
            print(f"   💥 Error parsing: {e}")
            issues_found.append({
                'file': relative_path,
                'error': str(e)
            })
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("=" * 20)
    print(f"Total plugins tested: {len(plugin_files)}")
    print(f"Plugins with issues: {len(issues_found)}")
    
    if issues_found:
        print(f"\n❌ ISSUES FOUND:")
        for issue in issues_found:
            if 'error' in issue:
                print(f"   💥 {issue['file']}: {issue['error']}")
            else:
                print(f"   🔧 {issue['file']} (cmd {issue['command_index']}): {issue['unresolved_vars']}")
        
        return False
    else:
        print(f"\n✅ ALL PLUGINS PASSED!")
        return True

def get_common_variables():
    """Get common variables that should be defined"""
    return {
        'min_rate': '1000',
        'max_rate': '5000', 
        'timing_template': 'T4',
        'service_opts': '-sV -sC',
        'timing_opts': '-T4 --min-rate=1000 --max-rate=5000'
    }

if __name__ == "__main__":
    success = test_plugin_variables()
    
    if not success:
        print(f"\n🔧 RECOMMENDED FIXES:")
        print("1. Add variables section to plugins missing common variables")
        print("2. Remove hardcoded timing parameters from commands")
        print("3. Use Jinja2 templating for conditional logic")
        
        common_vars = get_common_variables()
        print(f"\n📝 Common variables to add:")
        for var, value in common_vars.items():
            print(f"   {var}: '{value}'")
    
    sys.exit(0 if success else 1)