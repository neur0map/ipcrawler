#!/usr/bin/env python3
"""
Fix YAML variable system - handle both options and variables sections
"""

import yaml
from pathlib import Path
import re
import sys

def fix_yaml_executor():
    """Fix the YAML executor to handle options as variables"""
    
    print("🔧 FIXING YAML EXECUTOR TO HANDLE OPTIONS AS VARIABLES")
    print("=" * 60)
    
    executor_file = Path("ipcrawler/yaml_executor.py")
    
    if not executor_file.exists():
        print(f"❌ File not found: {executor_file}")
        return False
    
    content = executor_file.read_text()
    
    # Find the section where plugin variables are processed
    # We need to add options handling after variables handling
    
    insertion_point = """        # Plugin-specific variables override global ones
        if plugin.variables:
            # Process any Jinja2 templates in plugin variables
            processed_plugin_vars = {}
            for var_name, var_value in plugin.variables.items():
                if isinstance(var_value, str) and '{%' in var_value and '%}' in var_value:
                    processed_value = self._process_jinja2_template(var_value, env_vars)
                    processed_plugin_vars[var_name] = processed_value
                else:
                    processed_plugin_vars[var_name] = str(var_value)
            
            env_vars.update(processed_plugin_vars)"""
    
    new_section = """        # Plugin-specific variables override global ones
        if plugin.variables:
            # Process any Jinja2 templates in plugin variables
            processed_plugin_vars = {}
            for var_name, var_value in plugin.variables.items():
                if isinstance(var_value, str) and '{%' in var_value and '%}' in var_value:
                    processed_value = self._process_jinja2_template(var_value, env_vars)
                    processed_plugin_vars[var_name] = processed_value
                else:
                    processed_plugin_vars[var_name] = str(var_value)
            
            env_vars.update(processed_plugin_vars)
        
        # Also process plugin options as variables (for backward compatibility)
        if hasattr(plugin, 'options') and plugin.options:
            for option in plugin.options:
                if hasattr(option, 'name') and hasattr(option, 'default'):
                    var_name = option.name
                    var_value = option.default
                    # Only add if not already set by variables section
                    if var_name not in env_vars:
                        env_vars[var_name] = str(var_value)"""
    
    if insertion_point in content:
        updated_content = content.replace(insertion_point, new_section)
        
        # Write back to file
        executor_file.write_text(updated_content)
        print("✅ Updated yaml_executor.py to handle options as variables")
        return True
    else:
        print("❌ Could not find insertion point in yaml_executor.py")
        return False

def fix_plugin_commands():
    """Fix plugin commands to use proper Jinja2 syntax"""
    
    print("\n🔧 FIXING PLUGIN COMMANDS TO USE JINJA2 SYNTAX")
    print("=" * 50)
    
    template_dir = Path("templates/default-template")
    
    if not template_dir.exists():
        print(f"❌ Template directory not found: {template_dir}")
        return False
    
    fixes_applied = 0
    
    # Variable replacements
    replacements = {
        '{min_rate}': '{{min_rate}}',
        '{max_rate}': '{{max_rate}}',
        '{timing_template}': '{{timing_template}}',
        '{service_opts}': '{{service_opts}}',
        '{timing_opts}': '{{timing_opts}}',
        '{aggression}': '{{aggression}}',
        '{timeout}': '{{timeout}}',
        '{http_timeout}': '{{http_timeout}}'
    }
    
    for category_dir in template_dir.iterdir():
        if not category_dir.is_dir():
            continue
            
        for yaml_file in category_dir.rglob("*.yaml"):
            if yaml_file.name.endswith('.disabled'):
                continue
            
            relative_path = yaml_file.relative_to(template_dir)
            
            try:
                content = yaml_file.read_text()
                original_content = content
                
                # Apply replacements
                for old, new in replacements.items():
                    if old in content:
                        content = content.replace(old, new)
                        print(f"   🔧 {relative_path}: {old} → {new}")
                        fixes_applied += 1
                
                # Write back if changed
                if content != original_content:
                    yaml_file.write_text(content)
                    print(f"   ✅ Updated: {relative_path}")
                
            except Exception as e:
                print(f"   💥 Error processing {relative_path}: {e}")
    
    print(f"\n📊 Applied {fixes_applied} command syntax fixes")
    return fixes_applied > 0

def add_missing_variables():
    """Add missing variables sections to plugins that need them"""
    
    print("\n🔧 ADDING MISSING VARIABLES SECTIONS")
    print("=" * 40)
    
    template_dir = Path("templates/default-template")
    
    # Common variables that plugins might need
    common_variables = {
        'min_rate': 1000,
        'max_rate': 5000,
        'timing_template': 'T4',
        'timeout': 300,
        'http_timeout': 10,
        'aggression': 3,
        'service_opts': '-sV -sC',
        'timing_opts': '-T4 --min-rate=1000 --max-rate=5000'
    }
    
    plugins_updated = 0
    
    for category_dir in template_dir.iterdir():
        if not category_dir.is_dir():
            continue
            
        for yaml_file in category_dir.rglob("*.yaml"):
            if yaml_file.name.endswith('.disabled'):
                continue
            
            relative_path = yaml_file.relative_to(template_dir)
            
            try:
                content = yaml_file.read_text()
                plugin_data = yaml.safe_load(content)
                
                if not plugin_data:
                    continue
                
                # Check if plugin has variables section
                has_variables = 'variables' in plugin_data
                has_options = 'options' in plugin_data
                
                # Check which variables are used in commands
                commands = []
                if 'execution' in plugin_data and 'commands' in plugin_data['execution']:
                    for cmd in plugin_data['execution']['commands']:
                        if isinstance(cmd, dict) and 'command' in cmd:
                            commands.append(cmd['command'])
                        elif isinstance(cmd, str):
                            commands.append(cmd)
                
                command_text = ' '.join(commands)
                
                # Determine which variables are needed
                needed_vars = {}
                for var, default in common_variables.items():
                    if f'{{{{{var}}}}}' in command_text or f'{{{var}}}' in command_text:
                        needed_vars[var] = default
                
                # Add variables section if needed and not present
                if needed_vars and not has_variables and not has_options:
                    print(f"   📝 Adding variables to {relative_path}: {list(needed_vars.keys())}")
                    plugin_data['variables'] = needed_vars
                    
                    # Write back to file
                    with open(yaml_file, 'w') as f:
                        yaml.dump(plugin_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                    
                    plugins_updated += 1
                    print(f"   ✅ Updated: {relative_path}")
                
            except Exception as e:
                print(f"   💥 Error processing {relative_path}: {e}")
    
    print(f"\n📊 Updated {plugins_updated} plugins with variables sections")
    return plugins_updated > 0

def test_fixed_system():
    """Test that the fixes work"""
    
    print("\n🧪 TESTING FIXED SYSTEM")
    print("=" * 25)
    
    # Try to import and test the fixed executor
    try:
        import sys
        sys.path.insert(0, str(Path.cwd()))
        
        from ipcrawler.yaml_plugins import YamlPluginLoader
        from ipcrawler.yaml_executor import YamlPluginExecutor
        
        # Load plugins
        template_dir = Path("templates/default-template")
        loader = YamlPluginLoader(str(template_dir))
        loader.load_all_plugins()
        
        # Create executor
        executor = YamlPluginExecutor(loader)
        
        # Test variable loading for a few plugins
        test_plugins = ['nmap-ssh', 'portscan-top-tcp-ports', 'nmap-http']
        
        for plugin_name in test_plugins:
            if plugin_name in loader.plugins:
                plugin = loader.plugins[plugin_name]
                
                # Create a dummy target for testing
                class DummyTarget:
                    def __init__(self):
                        self.address = "192.168.1.100"
                        self.scandir = "/tmp/scans"
                
                env_vars = executor._load_environment_variables(plugin, DummyTarget())
                
                # Check for critical variables
                critical_vars = ['min_rate', 'max_rate', 'timing_template']
                missing = [var for var in critical_vars if var not in env_vars]
                
                if missing:
                    print(f"   ❌ {plugin_name}: Missing variables {missing}")
                else:
                    print(f"   ✅ {plugin_name}: All critical variables present")
        
        print("✅ System test completed")
        return True
        
    except Exception as e:
        print(f"💥 System test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 STARTING YAML VARIABLE SYSTEM FIX")
    print("=" * 40)
    
    success_count = 0
    
    # 1. Fix YAML executor
    if fix_yaml_executor():
        success_count += 1
    
    # 2. Fix plugin command syntax
    if fix_plugin_commands():
        success_count += 1
    
    # 3. Add missing variables
    if add_missing_variables():
        success_count += 1
    
    # 4. Test the system
    if test_fixed_system():
        success_count += 1
    
    print(f"\n📊 SUMMARY: {success_count}/4 fixes completed")
    
    if success_count == 4:
        print("✅ ALL FIXES APPLIED SUCCESSFULLY!")
        print("\nYou can now run: python3 ipcrawler.py --fast 127.0.0.1")
    else:
        print("❌ Some fixes failed - check the output above")
    
    sys.exit(0 if success_count == 4 else 1)