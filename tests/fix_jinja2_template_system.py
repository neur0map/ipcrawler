#!/usr/bin/env python3
"""
Fix the YAML plugin system to properly handle Jinja2 templates
"""

from pathlib import Path
import re

def fix_yaml_executor_jinja2():
    """Update the YAML executor to use proper Jinja2 template rendering"""
    
    print("🔧 FIXING YAML EXECUTOR FOR JINJA2 TEMPLATES")
    print("=" * 50)
    
    executor_file = Path("ipcrawler/yaml_executor.py")
    content = executor_file.read_text()
    
    # Find the _substitute_variables method and replace it with a Jinja2-aware version
    old_substitute_method = '''    def _substitute_variables(self, command: str, env_vars: Dict[str, str]) -> str:
        """
        Substitute variables in command string with detailed audit logging.
        
        Args:
            command: Command template with variables
            env_vars: Environment variables for substitution
            
        Returns:
            Command with variables substituted
        """
        original_command = command
        audit_logger.debug(f"🔀 STAGE 4 - Variable Substitution:")
        audit_logger.debug(f"   Original command: {repr(original_command[:150])}")
        
        # Replace {variable} patterns
        for var_name, var_value in env_vars.items():
            var_pattern = f'{{{var_name}}}'
            if var_pattern in command:
                audit_logger.debug(f"   🔄 Substituting {var_pattern} → {repr(var_value)}")
                command = command.replace(var_pattern, str(var_value))
        
        audit_logger.debug(f"   Final command: {repr(command[:150])}")
        
        # Check for remaining unsubstituted variables
        import re
        remaining_vars = re.findall(r'\\{([^}]+)\\}', command)
        if remaining_vars:
            audit_logger.debug(f"   ❌ UNSUBSTITUTED variables: {remaining_vars}")
        
        # Check for remaining Jinja2 templates
        if '{%' in command:
            audit_logger.debug(f"   ❌ UNPROCESSED Jinja2 templates still in command")
        
        return command'''
    
    new_substitute_method = '''    def _substitute_variables(self, command: str, env_vars: Dict[str, str]) -> str:
        """
        Substitute variables in command string using Jinja2 templating with detailed audit logging.
        
        Args:
            command: Command template with variables
            env_vars: Environment variables for substitution
            
        Returns:
            Command with variables substituted
        """
        original_command = command
        audit_logger.debug(f"🔀 STAGE 4 - Variable Substitution (Jinja2):")
        audit_logger.debug(f"   Original command: {repr(original_command[:150])}")
        audit_logger.debug(f"   Available variables: {list(env_vars.keys())}")
        
        try:
            from jinja2 import Environment, Template, StrictUndefined
            
            # Create Jinja2 environment
            jinja_env = Environment(undefined=StrictUndefined)
            
            # First, handle simple {variable} substitution for backward compatibility
            for var_name, var_value in env_vars.items():
                var_pattern = f'{{{var_name}}}'
                if var_pattern in command:
                    audit_logger.debug(f"   🔄 Legacy substituting {var_pattern} → {repr(var_value)}")
                    command = command.replace(var_pattern, str(var_value))
            
            # Then, handle Jinja2 {{variable}} templates
            if '{{' in command and '}}' in command:
                audit_logger.debug(f"   🎨 Processing Jinja2 template: {repr(command[:150])}")
                template = jinja_env.from_string(command)
                command = template.render(**env_vars)
                audit_logger.debug(f"   ✅ Jinja2 rendered: {repr(command[:150])}")
            
            # Handle Jinja2 conditionals like {% if %}
            if '{%' in command and '%}' in command:
                audit_logger.debug(f"   🎨 Processing Jinja2 conditionals: {repr(command[:100])}")
                template = jinja_env.from_string(command)
                command = template.render(**env_vars)
                audit_logger.debug(f"   ✅ Jinja2 conditionals rendered: {repr(command[:150])}")
            
        except Exception as e:
            audit_logger.debug(f"   💥 Jinja2 processing failed: {e}")
            # Fall back to simple string substitution
            for var_name, var_value in env_vars.items():
                var_pattern = f'{{{var_name}}}'
                if var_pattern in command:
                    command = command.replace(var_pattern, str(var_value))
        
        audit_logger.debug(f"   Final command: {repr(command[:150])}")
        
        # Check for remaining unsubstituted variables
        import re
        remaining_vars = re.findall(r'\\{\\{([^}]+)\\}\\}', command)
        remaining_legacy = re.findall(r'\\{([^}]+)\\}', command)
        if remaining_vars or remaining_legacy:
            audit_logger.debug(f"   ❌ UNSUBSTITUTED Jinja2 variables: {remaining_vars}")
            audit_logger.debug(f"   ❌ UNSUBSTITUTED legacy variables: {remaining_legacy}")
        
        return command'''
    
    if old_substitute_method in content:
        updated_content = content.replace(old_substitute_method, new_substitute_method)
        executor_file.write_text(updated_content)
        print("✅ Updated _substitute_variables method for Jinja2")
        return True
    else:
        print("❌ Could not find _substitute_variables method to replace")
        return False

def add_missing_variables_to_plugins():
    """Add proper variables sections to plugins that need them"""
    
    print("\n🔧 ADDING VARIABLES SECTIONS TO PLUGINS")
    print("=" * 40)
    
    template_dir = Path("templates/default-template")
    
    # Define common variables that should be available
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
                import yaml
                content = yaml_file.read_text()
                plugin_data = yaml.safe_load(content)
                
                if not plugin_data:
                    continue
                
                # Check what variables are used in the commands
                commands_text = ""
                if 'execution' in plugin_data and 'commands' in plugin_data['execution']:
                    for cmd in plugin_data['execution']['commands']:
                        if isinstance(cmd, dict) and 'command' in cmd:
                            commands_text += cmd['command'] + " "
                        elif isinstance(cmd, str):
                            commands_text += cmd + " "
                
                # Find which variables are needed
                needed_vars = {}
                for var_name, default_value in common_variables.items():
                    if f'{{{{{var_name}}}}}' in commands_text or f'{{{var_name}}}' in commands_text:
                        needed_vars[var_name] = default_value
                
                # Add variables section if we have options but no variables
                has_variables = 'variables' in plugin_data and plugin_data['variables']
                has_options = 'options' in plugin_data and plugin_data['options']
                
                if needed_vars and has_options and not has_variables:
                    print(f"   📝 Adding variables to {relative_path}: {list(needed_vars.keys())}")
                    plugin_data['variables'] = needed_vars
                    
                    # Write back the file
                    with open(yaml_file, 'w') as f:
                        yaml.dump(plugin_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                    
                    plugins_updated += 1
                    print(f"   ✅ Updated: {relative_path}")
                
            except Exception as e:
                print(f"   💥 Error processing {relative_path}: {e}")
    
    print(f"\n📊 Updated {plugins_updated} plugins with variables sections")
    return plugins_updated > 0

def test_jinja2_system():
    """Test the Jinja2 template system"""
    
    print("\n🧪 TESTING JINJA2 TEMPLATE SYSTEM")
    print("=" * 35)
    
    try:
        from jinja2 import Environment, Template
        
        # Test basic Jinja2 functionality
        env = Environment()
        
        # Test 1: Simple variable substitution
        template1 = env.from_string("nmap -{{timing_template}} --min-rate={{min_rate}} {{address}}")
        vars1 = {'timing_template': 'T4', 'min_rate': 1000, 'address': '192.168.1.1'}
        result1 = template1.render(**vars1)
        expected1 = "nmap -T4 --min-rate=1000 192.168.1.1"
        
        if result1 == expected1:
            print("✅ Test 1: Basic variable substitution works")
        else:
            print(f"❌ Test 1 failed: {result1} != {expected1}")
            return False
        
        # Test 2: Conditional templates
        template2 = env.from_string("nmap {% if not config.proxychains %}-sV -sC{% endif %} {{address}}")
        vars2 = {'config': {'proxychains': False}, 'address': '192.168.1.1'}
        result2 = template2.render(**vars2)
        expected2 = "nmap -sV -sC 192.168.1.1"
        
        if result2 == expected2:
            print("✅ Test 2: Conditional templates work")
        else:
            print(f"❌ Test 2 failed: {result2} != {expected2}")
        
        # Test 3: Mixed legacy and Jinja2
        test_command = "nmap -{timing_template} --min-rate={{min_rate}} {address}"
        vars3 = {'timing_template': 'T4', 'min_rate': 1000, 'address': '192.168.1.1'}
        
        # Simulate what our new method should do
        # First legacy substitution
        for var_name, var_value in vars3.items():
            var_pattern = f'{{{var_name}}}'
            if var_pattern in test_command:
                test_command = test_command.replace(var_pattern, str(var_value))
        
        # Then Jinja2
        if '{{' in test_command:
            template3 = env.from_string(test_command)
            result3 = template3.render(**vars3)
        else:
            result3 = test_command
        
        expected3 = "nmap -T4 --min-rate=1000 192.168.1.1"
        
        if result3 == expected3:
            print("✅ Test 3: Mixed legacy/Jinja2 substitution works")
        else:
            print(f"❌ Test 3 failed: {result3} != {expected3}")
            return False
        
        print("✅ All Jinja2 tests passed!")
        return True
        
    except Exception as e:
        print(f"💥 Jinja2 test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 FIXING JINJA2 TEMPLATE SYSTEM")
    print("=" * 35)
    
    success_count = 0
    
    # 1. Fix YAML executor for Jinja2
    if fix_yaml_executor_jinja2():
        success_count += 1
    
    # 2. Add missing variables to plugins
    if add_missing_variables_to_plugins():
        success_count += 1
    
    # 3. Test the Jinja2 system
    if test_jinja2_system():
        success_count += 1
    
    print(f"\n📊 SUMMARY: {success_count}/3 fixes completed")
    
    if success_count >= 2:
        print("✅ JINJA2 SYSTEM READY!")
        print("\nTest with: python3 ipcrawler.py --fast 127.0.0.1")
    else:
        print("❌ Some fixes failed")
    
    exit(0 if success_count >= 2 else 1)