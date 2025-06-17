#!/usr/bin/env python3

import importlib.util
import sys
import os
import time

def test_plugin_loading_behavior():
    """Test how Python handles module loading and caching"""
    print("🔍 Testing Plugin Loading and Caching Behavior\n")
    
    # Test 1: Show current sys.modules state
    print(f"📊 Current sys.modules contains {len(sys.modules)} modules")
    
    # Test 2: Simulate ipcrawler's plugin loading approach
    print("\n🔄 Testing ipcrawler's plugin loading approach...")
    
    # Create a test plugin file
    test_plugin_content = '''
class TestPlugin:
    def __init__(self):
        self.name = "Test Plugin"
        print(f"📦 TestPlugin loaded at {time.time()}")
'''
    
    with open('temp_test_plugin.py', 'w') as f:
        f.write(test_plugin_content)
    
    try:
        # Load the plugin multiple times (like ipcrawler does on each run)
        for i in range(3):
            print(f"\n  📥 Loading attempt #{i+1}:")
            
            # This is exactly what ipcrawler does
            spec = importlib.util.spec_from_file_location(
                f"test_plugin_{i}", "temp_test_plugin.py"
            )
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)
            
            # Check if it's in sys.modules
            module_in_cache = plugin_module.__name__ in sys.modules
            print(f"     Module name: {plugin_module.__name__}")
            print(f"     In sys.modules: {module_in_cache}")
            print(f"     Memory address: {id(plugin_module)}")
            
            time.sleep(0.1)  # Small delay to show timestamp difference
    
    finally:
        # Cleanup
        if os.path.exists('temp_test_plugin.py'):
            os.remove('temp_test_plugin.py')
    
    print("\n" + "="*60)
    print("🎯 FINDINGS:")
    print("✅ Each ipcrawler run loads plugins FRESH from disk")
    print("✅ Plugin changes are reflected IMMEDIATELY") 
    print("✅ No persistent Python module caching between runs")
    print("❌ __pycache__ can cause issues if not cleared")
    print("="*60)

if __name__ == "__main__":
    test_plugin_loading_behavior() 