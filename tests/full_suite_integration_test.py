#!/usr/bin/env python3
"""
Full-Suite Integration Test
Tests ALL existing plugin YAMLs with new load_and_parse_plugin
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, StrictUndefined, UndefinedError, TemplateSyntaxError

# Add ipcrawler to path
sys.path.insert(0, '/Users/carlosm/ipcrawler')

def load_and_parse_plugin_new(plugin_file: Path, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """New parser with Jinja2 template rendering BEFORE YAML parsing"""
    
    try:
        with open(plugin_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # Create Jinja2 environment with StrictUndefined
        env = Environment(
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Render entire YAML through Jinja2 FIRST
        template = env.from_string(raw_content)
        rendered_content = template.render(**context)
        
        # Parse the RENDERED YAML
        plugin_data = yaml.safe_load(rendered_content)
        
        return plugin_data
        
    except UndefinedError as e:
        print(f"   ❌ Missing variable in {plugin_file.name}: {e}")
        return None
        
    except TemplateSyntaxError as e:
        print(f"   ❌ Template syntax error in {plugin_file.name}: {e}")
        return None
        
    except yaml.YAMLError as e:
        print(f"   ❌ YAML syntax error after rendering {plugin_file.name}: {e}")
        return None
        
    except Exception as e:
        print(f"   ❌ Unexpected error in {plugin_file.name}: {e}")
        return None

def find_unrendered_templates(obj: Any, path: str = "root") -> List[str]:
    """Recursively find any remaining {{ or {% patterns"""
    
    unrendered = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            unrendered.extend(find_unrendered_templates(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            unrendered.extend(find_unrendered_templates(item, f"{path}[{i}]"))
    elif isinstance(obj, str):
        if '{{' in obj or '{%' in obj:
            unrendered.append(f"{path}: {repr(obj[:100])}")
    
    return unrendered

def create_comprehensive_context() -> Dict[str, Any]:
    """Create context that should work for most plugins"""
    
    return {
        # Basic target info
        'target': '127.0.0.1',
        'address': '127.0.0.1',
        'ip': '127.0.0.1',
        'port': '80',
        'protocol': 'tcp',
        'service': 'http',
        'service_name': 'http',
        
        # URLs and schemes
        'url': 'http://127.0.0.1',
        'http_scheme': 'http',
        'secure': False,
        
        # Paths and directories
        'scandir': '/tmp/scans',
        'results_base': '/tmp/results',
        'temp_base': '/tmp',
        
        # Nmap and scanning variables
        'min_rate': '1000',
        'max_rate': '5000',
        'top_ports': '1000',
        'ports': '80,443,8080',
        'timing': 'T4',
        
        # Web enumeration
        'wordlist': '/usr/share/wordlists/common.txt',
        'user_agent': 'IPCrawler/1.0',
        'threads': '10',
        
        # Plugin metadata  
        'plugin_slug': 'test-plugin',
        'plugin_name': 'Test Plugin',
        
        # Port lists
        'ports_tcp': ['80', '443', '8080'],
        'ports_udp': ['53', '161'],
        'target_ports_tcp': '80,443,8080',
        'target_ports_udp': '53,161',
        
        # Configuration
        'config': {'proxychains': False},
        'timeout_default': '300',
        
        # Progress tracking
        'live_progress': True,
        'progress_update_interval': '1',
        
        # Common variables that might be missing
        'ipversion': '4',
        'fast_mode': False,
        'verbose': False,
        'stealth': False,
        'domain': 'example.com',
        'hostname': 'example.com',
        'hostname_clean': 'example_com',
        'username': 'admin',
        'password': 'password123',
        'follow_redirects': False,
        'timeout': '30',
        
        # Jinja2 filter helpers
        'default': lambda x, d: d if x is None else x,
    }

def test_all_existing_plugins():
    """Integration test: Load ALL existing plugins and verify compliance"""
    
    print("🧪 FULL-SUITE INTEGRATION TEST")
    print("=" * 50)
    
    # Standard context that should work for most plugins
    context = create_comprehensive_context()
    
    print(f"📋 Context has {len(context)} variables:")
    context_keys = list(context.keys())
    for i in range(0, len(context_keys), 6):
        line_keys = context_keys[i:i+6]
        print(f"   {', '.join(line_keys)}")
    print()
    
    # Find all plugin directories
    plugin_dirs = [
        Path('templates/default-template/01-port-scanning'),
        Path('templates/default-template/02-service-enumeration'),
        Path('templates/default-template/03-bruteforce'),
        Path('templates/default-template/04-reporting'),
        Path('yaml-plugins/01-discovery'),
        Path('yaml-plugins/01-port-scanning'),
        Path('yaml-plugins/02-enumeration'),
        Path('yaml-plugins/02-service-enumeration'),
        Path('yaml-plugins/03-bruteforce'),
    ]
    
    total_plugins = 0
    successful_plugins = 0
    failed_plugins = []
    plugins_with_unrendered = []
    
    print("🔍 Scanning plugin directories...")
    
    for plugin_dir in plugin_dirs:
        if plugin_dir.exists():
            print(f"\n📁 {plugin_dir}")
            
            yaml_files = list(plugin_dir.glob('**/*.yaml'))
            print(f"   Found {len(yaml_files)} YAML files")
            
            for plugin_file in yaml_files:
                total_plugins += 1
                print(f"   🔧 Testing: {plugin_file.name}")
                
                # Test with new parser
                result = load_and_parse_plugin_new(plugin_file, context)
                
                if result:
                    successful_plugins += 1
                    
                    # Check for unrendered templates
                    unrendered = find_unrendered_templates(result)
                    
                    if unrendered:
                        plugins_with_unrendered.append((plugin_file.name, unrendered))
                        print(f"      ⚠️ {len(unrendered)} unrendered templates")
                        for template in unrendered[:2]:  # Show first 2
                            print(f"         {template}")
                    else:
                        print(f"      ✅ No unrendered templates")
                else:
                    failed_plugins.append(plugin_file.name)
        else:
            print(f"📁 {plugin_dir} - Not found")
    
    print(f"\n📊 INTEGRATION TEST RESULTS")
    print("=" * 40)
    print(f"Total plugins tested: {total_plugins}")
    print(f"Successfully parsed: {successful_plugins}")
    print(f"Failed to parse: {len(failed_plugins)}")
    print(f"With unrendered templates: {len(plugins_with_unrendered)}")
    
    if total_plugins > 0:
        success_rate = successful_plugins / total_plugins
        template_success_rate = (successful_plugins - len(plugins_with_unrendered)) / total_plugins
        
        print(f"\n📈 Success Rate: {success_rate:.1%}")
        print(f"📈 Template Success Rate: {template_success_rate:.1%}")
        
        # Exit criteria check
        if template_success_rate >= 0.9:
            print("✅ PASS: Template success rate >= 90%")
        else:
            print("❌ FAIL: Template success rate < 90%")
    
    if failed_plugins:
        print(f"\n❌ FAILED PLUGINS ({len(failed_plugins)}):")
        for plugin in failed_plugins:
            print(f"   • {plugin}")
    
    if plugins_with_unrendered:
        print(f"\n⚠️ PLUGINS WITH UNRENDERED TEMPLATES ({len(plugins_with_unrendered)}):")
        for plugin, templates in plugins_with_unrendered:
            print(f"   • {plugin}: {len(templates)} unrendered")
            for template in templates[:1]:  # Show first template
                print(f"     {template}")
    
    if not failed_plugins and not plugins_with_unrendered:
        print("\n🎉 ALL TESTS PASSED!")
        print("   • All plugins parsed successfully")
        print("   • No unrendered templates found")
        print("   • Ready for production deployment")

def test_specific_known_plugins():
    """Test specific plugins we know exist"""
    
    print("\n🎯 TESTING SPECIFIC KNOWN PLUGINS")
    print("=" * 40)
    
    known_plugins = [
        'templates/default-template/01-port-scanning/portscan-top-tcp-ports.yaml',
        'yaml-plugins/01-port-scanning/nmap-top-ports.yaml',
        'yaml-plugins/02-service-enumeration/web-services/whatweb.yaml',
    ]
    
    context = create_comprehensive_context()
    
    for plugin_path_str in known_plugins:
        plugin_path = Path(plugin_path_str)
        
        if plugin_path.exists():
            print(f"\n🔧 Testing: {plugin_path}")
            
            result = load_and_parse_plugin_new(plugin_path, context)
            
            if result:
                print("   ✅ Parsed successfully")
                
                # Check command templates specifically
                if 'execution' in result:
                    commands = result['execution'].get('commands', [])
                    for i, cmd in enumerate(commands):
                        if 'command' in cmd:
                            command_str = cmd['command']
                            if '{{' in command_str or '{%' in command_str:
                                print(f"   ❌ Command {i} has unrendered templates: {repr(command_str[:100])}")
                            else:
                                print(f"   ✅ Command {i} fully rendered")
                
                # Check for any unrendered templates
                unrendered = find_unrendered_templates(result)
                if unrendered:
                    print(f"   ❌ {len(unrendered)} unrendered templates found")
                    for template in unrendered[:3]:
                        print(f"      {template}")
                else:
                    print("   ✅ No unrendered templates anywhere")
            else:
                print("   ❌ Failed to parse")
        else:
            print(f"\n❌ Plugin not found: {plugin_path}")

if __name__ == "__main__":
    test_all_existing_plugins()
    test_specific_known_plugins()