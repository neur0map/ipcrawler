#!/usr/bin/env python3
"""
Fix YAML plugin variable substitution issues
"""

import yaml
from pathlib import Path
import re
from jinja2 import Environment, Template, StrictUndefined
import sys

def get_global_variables():
    """Get global variables from global.toml"""
    try:
        import toml
        global_config = toml.load('ipcrawler/global.toml')
        return global_config.get('variables', {})
    except:
        # Fallback common variables
        return {
            'min_rate': 1000,
            'max_rate': 5000,
            'timing_template': 'T4',
            'service_opts': '-sV -sC',
            'timing_opts': '-T4 --min-rate=1000 --max-rate=5000',
            'timeout': 300,
            'http_timeout': 10,
            'aggression': 3,
            'top_ports': 1000
        }

def test_template_rendering():
    """Test actual template rendering like the system does"""
    
    print("🔧 TESTING ACTUAL TEMPLATE RENDERING")
    print("=" * 50)
    
    template_dir = Path("templates/default-template")
    global_vars = get_global_variables()
    
    # Sample context for testing
    test_context = {
        'address': '192.168.1.100',
        'hostname': 'test.example.com',
        'port': 80,
        'http_scheme': 'http',
        'scandir': '/tmp/scans',
        'domain': 'example.com',
        'all_hostnames': ['test.example.com', '192.168.1.100'],
        'target_ports_tcp': '80,443,8080',
        'target_ports_udp': '53,161,123',
        'addressv6': '[::1]',
        'wordlist': 'common.txt',
        'timeout': 300,
        'http_timeout': 10,
        'timing': 'T4',
        'follow_flag': '-L',
        'path': '/',
        'target_type': 'ip',
        **global_vars
    }
    
    # Find plugins with issues
    problematic_plugins = []
    
    for category_dir in template_dir.iterdir():
        if not category_dir.is_dir():
            continue
            
        for yaml_file in category_dir.rglob("*.yaml"):
            if yaml_file.name.endswith('.disabled'):
                continue
                
            relative_path = yaml_file.relative_to(template_dir)
            
            try:
                # Read and parse YAML
                content = yaml_file.read_text()
                plugin_data = yaml.safe_load(content)
                
                if not plugin_data or 'execution' not in plugin_data:
                    continue
                
                # Check commands for rendering issues
                commands = plugin_data['execution'].get('commands', [])
                
                for i, command in enumerate(commands):
                    if not isinstance(command, str):
                        continue
                    
                    try:
                        # Try to render the command with Jinja2
                        template = Template(command)
                        rendered = template.render(**test_context)
                        
                        # Check if there are still unresolved variables
                        unresolved = re.findall(r'\{([^}]+)\}', rendered)
                        if unresolved:
                            problematic_plugins.append({
                                'file': relative_path,
                                'command_index': i,
                                'original': command,
                                'rendered': rendered,
                                'unresolved': unresolved
                            })
                            print(f"❌ {relative_path} (cmd {i}): {unresolved}")
                            print(f"   Original: {command[:100]}...")
                            print(f"   Rendered: {rendered[:100]}...")
                    
                    except Exception as e:
                        print(f"💥 {relative_path} (cmd {i}): Template error - {e}")
                        problematic_plugins.append({
                            'file': relative_path,
                            'command_index': i,
                            'error': str(e)
                        })
            
            except Exception as e:
                print(f"💥 {relative_path}: YAML error - {e}")
    
    return problematic_plugins

def fix_plugins(problematic_plugins):
    """Fix the problematic plugins"""
    
    print(f"\n🔧 FIXING {len(problematic_plugins)} PLUGIN ISSUES")
    print("=" * 40)
    
    # Group by file
    files_to_fix = {}
    for issue in problematic_plugins:
        file_path = issue['file']
        if file_path not in files_to_fix:
            files_to_fix[file_path] = []
        files_to_fix[file_path].append(issue)
    
    template_dir = Path("templates/default-template")
    
    for file_path, issues in files_to_fix.items():
        full_path = template_dir / file_path
        print(f"\n🔧 Fixing: {file_path}")
        
        try:
            # Read current content
            content = full_path.read_text()
            plugin_data = yaml.safe_load(content)
            
            # Add variables section if missing
            if 'variables' not in plugin_data:
                plugin_data['variables'] = {}
            
            # Add common variables that are missing
            common_vars = {
                'min_rate': 1000,
                'max_rate': 5000,
                'timing_template': 'T4',
                'timeout': 300,
                'http_timeout': 10,
                'aggression': 3
            }
            
            for var, value in common_vars.items():
                if var not in plugin_data['variables']:
                    plugin_data['variables'][var] = value
                    print(f"   ✅ Added variable: {var} = {value}")
            
            # Fix commands with unresolved variables
            for issue in issues:
                if 'unresolved' in issue:
                    cmd_index = issue['command_index']
                    unresolved = issue['unresolved']
                    
                    # Replace common unresolved variables
                    commands = plugin_data['execution']['commands']
                    original_cmd = commands[cmd_index]
                    fixed_cmd = original_cmd
                    
                    # Common substitutions
                    substitutions = {
                        '{min_rate}': '{{min_rate}}',
                        '{max_rate}': '{{max_rate}}', 
                        '{timing_template}': '{{timing_template}}',
                        '{service_opts}': '-sV -sC',
                        '{timing_opts}': '-{{timing_template}} --min-rate={{min_rate}} --max-rate={{max_rate}}'
                    }
                    
                    for old, new in substitutions.items():
                        if old in fixed_cmd:
                            fixed_cmd = fixed_cmd.replace(old, new)
                            print(f"   🔧 Fixed: {old} → {new}")
                    
                    commands[cmd_index] = fixed_cmd
            
            # Write back to file
            with open(full_path, 'w') as f:
                yaml.dump(plugin_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            print(f"   ✅ Fixed and saved: {file_path}")
            
        except Exception as e:
            print(f"   💥 Error fixing {file_path}: {e}")

if __name__ == "__main__":
    # Test rendering to find issues
    problematic = test_template_rendering()
    
    if problematic:
        print(f"\n📊 Found {len(problematic)} issues to fix")
        
        # Ask user if they want to fix
        response = input("\n🤔 Do you want to automatically fix these issues? [y/N]: ")
        if response.lower() == 'y':
            fix_plugins(problematic)
            print(f"\n✅ Plugin fixes completed!")
        else:
            print(f"\n❌ No fixes applied")
    else:
        print(f"\n✅ No rendering issues found!")
    
    sys.exit(0)