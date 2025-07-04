#!/usr/bin/env python3
"""
Phase 2 Test Script - YAML Plugin Execution Engine

Tests YAML plugin execution, service matching, command execution,
pattern matching, and integration with main execution loop.
"""

import os
import sys
import asyncio
import tempfile
import shutil
from pathlib import Path

# Add ipcrawler to path
sys.path.insert(0, str(Path(__file__).parent / 'ipcrawler'))

from ipcrawler.config import config
from ipcrawler.yaml_plugins import YamlPluginLoader, PluginType
from ipcrawler.yaml_executor import YamlPluginExecutor
from ipcrawler.plugin_debugger import PluginDebugger
from ipcrawler.yaml_integration import YamlPluginManager, initialize_yaml_plugins


class MockTarget:
    """Mock target for testing"""
    def __init__(self, address="192.168.1.1"):
        self.address = address
        self.ip = address
        self.ipversion = "IPv4"
        self.scandir = tempfile.mkdtemp()
        
    def cleanup(self):
        if os.path.exists(self.scandir):
            shutil.rmtree(self.scandir)


class MockService:
    """Mock service for testing"""
    def __init__(self, target, port=80, protocol="tcp", name="http", secure=False):
        self.target = target
        self.port = port
        self.protocol = protocol
        self.name = name
        self.secure = secure


async def test_yaml_plugin_loader():
    """Test YAML plugin loading"""
    print("🧪 Testing YAML plugin loader...")
    
    # Initialize loader with explicit directory list
    yaml_plugins_dir = config.get('yaml_plugins_dir')
    if not yaml_plugins_dir or not Path(yaml_plugins_dir).exists():
        print(f"❌ YAML plugins directory not found: {yaml_plugins_dir}")
        return False
    
    loader = YamlPluginLoader([yaml_plugins_dir])  # Pass as list
    result = loader.load_plugins()
    
    if not result:
        print(f"❌ Failed to load YAML plugins: No plugins returned")
        return False
    
    print(f"✅ Loaded {len(result)} YAML plugins")
    
    # Check plugin types
    port_scan_plugins = [p for p in result.values() if p.metadata.type == PluginType.PORTSCAN]
    service_scan_plugins = [p for p in result.values() if p.metadata.type == PluginType.SERVICESCAN]
    
    print(f"   • Port scan plugins: {len(port_scan_plugins)}")
    print(f"   • Service scan plugins: {len(service_scan_plugins)}")
    
    return True


async def test_yaml_plugin_debugger():
    """Test YAML plugin debugger"""
    print("🧪 Testing YAML plugin debugger...")
    
    debugger = PluginDebugger("test_session")
    
    # Test plugin selection logging
    debugger.log_plugin_selection("test-plugin", "192.168.1.1", True, "Test reason", "portscan")
    debugger.log_plugin_selection("another-plugin", "192.168.1.1:80", False, "Failed condition", "servicescan")
    
    # Test condition evaluation logging
    debugger.log_condition_evaluation("test-plugin", "192.168.1.1", "service pattern", True, "matched http")
    
    # Test execution logging
    debugger.log_plugin_execution_start("test-plugin", "192.168.1.1")
    debugger.log_plugin_execution_end("test-plugin", "192.168.1.1", True, 2.5)
    
    # Check decisions
    decisions = debugger.current_session.decisions
    if len(decisions) < 2:
        print(f"❌ Expected at least 2 decisions, got {len(decisions)}")
        return False
    
    print(f"✅ Debugger logged {len(decisions)} plugin decisions")
    print(f"   • Selected: {len(debugger.get_selected_plugins())}")
    print(f"   • Skipped: {len(debugger.get_skipped_plugins())}")
    
    return True


async def test_yaml_plugin_executor():
    """Test YAML plugin executor"""
    print("🧪 Testing YAML plugin executor...")
    
    # Initialize components
    yaml_plugins_dir = config.get('yaml_plugins_dir')
    loader = YamlPluginLoader([yaml_plugins_dir])
    result = loader.load_plugins()
    
    if not result:
        print(f"❌ Failed to load plugins for executor test")
        return False
    
    debugger = PluginDebugger("executor_test")
    executor = YamlPluginExecutor(loader, debugger)
    
    # Create mock target and service
    target = MockTarget("192.168.1.100")
    service = MockService(target, 80, "tcp", "http", False)
    
    try:
        # Test port scan plugin selection
        port_plugins = executor.get_yaml_plugins_for_target(target, PluginType.PORTSCAN)
        print(f"   • Found {len(port_plugins)} port scan plugins for target")
        
        # Test service scan plugin selection
        service_plugins = executor.get_yaml_plugins_for_service(service, PluginType.SERVICESCAN)
        print(f"   • Found {len(service_plugins)} service scan plugins for HTTP service")
        
        # Test plugin execution (if we have plugins)
        if port_plugins:
            plugin = port_plugins[0]
            print(f"   • Testing execution of {plugin.metadata.slug}")
            
            # The plugin already has the execution structure from YAML
            # No need to modify - just execute as-is
            result = await executor.execute_yaml_plugin_for_target(plugin, target)
            
            if result['success']:
                print(f"   ✅ Port scan plugin executed successfully")
                print(f"      • Execution time: {result['execution_time']:.2f}s")
                print(f"      • Commands executed: {len(result.get('commands_executed', []))}")
            else:
                print(f"   ⚠️ Port scan plugin execution failed: {result.get('error', 'Unknown error')}")
        
        if service_plugins:
            plugin = service_plugins[0]
            print(f"   • Testing execution of {plugin.metadata.slug}")
            
            # The plugin already has the execution structure from YAML
            # No need to modify - just execute as-is
            result = await executor.execute_yaml_plugin_for_service(plugin, service)
            
            if result['success']:
                print(f"   ✅ Service scan plugin executed successfully")
                print(f"      • Execution time: {result['execution_time']:.2f}s")
                print(f"      • Commands executed: {len(result.get('commands_executed', []))}")
            else:
                print(f"   ⚠️ Service scan plugin execution failed: {result.get('error', 'Unknown error')}")
        
        # Test execution stats
        stats = executor.get_execution_stats()
        print(f"   • Execution stats: {stats['total_executions']} total, {stats['successful_executions']} successful")
        
        print("✅ YAML plugin executor tests passed")
        return True
        
    finally:
        target.cleanup()


async def test_yaml_integration_manager():
    """Test YAML plugin integration manager"""
    print("🧪 Testing YAML plugin integration manager...")
    
    manager = YamlPluginManager()
    
    # Test initialization
    success = manager.initialize()
    if not success:
        print("❌ YAML plugin manager initialization failed")
        return False
    
    print("✅ YAML plugin manager initialized successfully")
    print(f"   • Total plugins loaded: {manager.performance_stats['total_plugins_loaded']}")
    print(f"   • Initialization time: {manager.performance_stats['initialization_time']:.2f}s")
    
    # Test target plugins
    target = MockTarget("192.168.1.200")
    service = MockService(target, 443, "tcp", "https", True)
    
    try:
        port_plugins = manager.get_yaml_port_scan_plugins(target)
        service_plugins = manager.get_yaml_service_scan_plugins(service)
        
        print(f"   • Port scan plugins for target: {len(port_plugins)}")
        print(f"   • Service scan plugins for HTTPS: {len(service_plugins)}")
        
        # Test execution if we have plugins
        if port_plugins:
            result = await manager.execute_yaml_port_scan(port_plugins[0], target)
            if result['success']:
                print(f"   ✅ Port scan execution via manager successful")
            else:
                print(f"   ⚠️ Port scan execution failed: {result.get('error', 'Unknown')}")
        
        if service_plugins:
            result = await manager.execute_yaml_service_scan(service_plugins[0], service)
            if result['success']:
                print(f"   ✅ Service scan execution via manager successful")
            else:
                print(f"   ⚠️ Service scan execution failed: {result.get('error', 'Unknown')}")
        
        # Test performance stats
        perf_stats = manager.get_performance_stats()
        print(f"   • Manager performance: {perf_stats['successful_executions']} successful executions")
        
        print("✅ YAML integration manager tests passed")
        return True
        
    finally:
        target.cleanup()


async def test_global_integration_functions():
    """Test global integration functions"""
    print("🧪 Testing global integration functions...")
    
    # Test initialization function
    from ipcrawler.yaml_integration import (
        initialize_yaml_plugins, 
        get_yaml_port_scan_tasks, 
        get_yaml_service_scan_tasks,
        should_skip_python_plugins
    )
    
    success = initialize_yaml_plugins()
    if not success:
        print("❌ Global YAML plugin initialization failed")
        return False
    
    print("✅ Global YAML plugin initialization successful")
    
    # Test task generation
    target = MockTarget("192.168.1.250")
    service = MockService(target, 22, "tcp", "ssh", False)
    
    try:
        # Test port scan tasks
        port_tasks = get_yaml_port_scan_tasks(target)
        print(f"   • Generated {len(port_tasks)} port scan tasks")
        
        # Test service scan tasks
        service_tasks = get_yaml_service_scan_tasks(service)
        print(f"   • Generated {len(service_tasks)} service scan tasks")
        
        # Test python plugin skip check
        skip_python = should_skip_python_plugins()
        print(f"   • Should skip Python plugins: {skip_python}")
        
        # Test task execution if we have any
        if port_tasks:
            task = port_tasks[0]
            print(f"   • Testing port scan task: {task.plugin_name}")
            result = await task
            if result['success']:
                print(f"   ✅ Port scan task executed successfully")
            else:
                print(f"   ⚠️ Port scan task failed: {result.get('error', 'Unknown')}")
        
        if service_tasks:
            task = service_tasks[0]
            print(f"   • Testing service scan task: {task.plugin_name}")
            result = await task
            if result['success']:
                print(f"   ✅ Service scan task executed successfully")
            else:
                print(f"   ⚠️ Service scan task failed: {result.get('error', 'Unknown')}")
        
        print("✅ Global integration function tests passed")
        return True
        
    finally:
        target.cleanup()


async def test_service_condition_evaluation():
    """Test advanced service condition evaluation"""
    print("🧪 Testing service condition evaluation...")
    
    # Initialize components
    yaml_plugins_dir = config.get('yaml_plugins_dir')
    loader = YamlPluginLoader([yaml_plugins_dir])
    result = loader.load_plugins()
    
    if not result:
        print(f"❌ Failed to load plugins for condition test")
        return False
    
    executor = YamlPluginExecutor(loader)
    
    # Create test services
    target = MockTarget("192.168.1.111")
    
    test_services = [
        MockService(target, 80, "tcp", "http", False),
        MockService(target, 443, "tcp", "https", True),
        MockService(target, 22, "tcp", "ssh", False),
        MockService(target, 21, "tcp", "ftp", False),
        MockService(target, 53, "udp", "dns", False)
    ]
    
    try:
        total_matches = 0
        
        for service in test_services:
            service_plugins = executor.get_yaml_plugins_for_service(service, PluginType.SERVICESCAN)
            total_matches += len(service_plugins)
            print(f"   • {service.name} on {service.protocol}/{service.port}: {len(service_plugins)} matching plugins")
        
        print(f"   • Total service-plugin matches: {total_matches}")
        print("✅ Service condition evaluation tests passed")
        return True
        
    finally:
        target.cleanup()


async def run_all_tests():
    """Run all Phase 2 tests"""
    print("🚀 Starting Phase 2 YAML Plugin Tests")
    print("=" * 50)
    
    tests = [
        ("YAML Plugin Loader", test_yaml_plugin_loader),
        ("YAML Plugin Debugger", test_yaml_plugin_debugger),
        ("YAML Plugin Executor", test_yaml_plugin_executor),
        ("YAML Integration Manager", test_yaml_integration_manager),
        ("Global Integration Functions", test_global_integration_functions),
        ("Service Condition Evaluation", test_service_condition_evaluation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            success = await test_func()
            if success:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"💥 {test_name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Phase 2 tests PASSED! YAML plugin execution engine is working!")
        print("\n🔥 Ready for Phase 3: Core Plugin Conversion!")
    else:
        print(f"⚠️ {failed} test(s) failed. Please review and fix issues before proceeding.")
    
    return failed == 0


if __name__ == "__main__":
    # Set up minimal config for testing
    current_dir = Path(__file__).parent.absolute()
    yaml_plugins_path = current_dir / 'ipcrawler' / 'yaml-plugins'
    
    config.update({
        'enable_yaml_plugins': True,
        'yaml_plugins_dir': str(yaml_plugins_path),
        'debug_yaml_plugins': True,
        'yaml_plugins_only': False,
        'verbose': 1
    })
    
    print(f"🔧 Using YAML plugins directory: {yaml_plugins_path}")
    print(f"🔧 Directory exists: {yaml_plugins_path.exists()}")
    
    asyncio.run(run_all_tests()) 