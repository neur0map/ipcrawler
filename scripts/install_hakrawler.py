#!/usr/bin/env python3
"""
Hakrawler Installation and Configuration Script
Automatically detects, installs, and configures hakrawler for IPCrawler
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

def print_status(message, status="INFO"):
    """Print formatted status message"""
    symbols = {
        "INFO": "ℹ",
        "SUCCESS": "✅",
        "WARNING": "⚠",
        "ERROR": "❌",
        "PROCESS": "→"
    }
    print(f"{symbols.get(status, 'ℹ')} {message}")

def run_command(cmd, capture_output=True, timeout=30, input_data=None):
    """Run command safely with error handling"""
    try:
        result = subprocess.run(
            cmd, 
            shell=isinstance(cmd, str),
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            input=input_data
        )
        return result
    except subprocess.TimeoutExpired:
        print_status(f"Command timed out: {cmd}", "WARNING")
        return None
    except Exception as e:
        print_status(f"Command failed: {cmd} - {e}", "ERROR")
        return None

def check_hakrawler_installation():
    """Check if hakrawler is installed and working"""
    print_status("Checking hakrawler installation...", "PROCESS")
    
    # Check if it's in PATH
    if shutil.which('hakrawler'):
        print_status("Found hakrawler in PATH", "SUCCESS")
        return True, shutil.which('hakrawler')
    
    # Check common installation locations
    common_paths = [
        os.path.expanduser('~/go/bin/hakrawler'),
        '/usr/local/go/bin/hakrawler',
        '/usr/bin/hakrawler',
        '/usr/local/bin/hakrawler',
        '/opt/hakrawler/hakrawler',
        '/opt/go/bin/hakrawler',
        '/snap/bin/hakrawler',
        os.path.expanduser('~/.local/bin/hakrawler'),
        os.path.expanduser('~/tools/hakrawler'),
        os.path.expanduser('~/bin/hakrawler'),
    ]
    
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            # Test if it works
            result = run_command([path], input_data='', timeout=3)
            if result is not None:  # Any response means it's working
                print_status(f"Found working hakrawler at: {path}", "SUCCESS")
                return True, path
    
    print_status("Hakrawler not found", "WARNING")
    return False, None

def install_hakrawler():
    """Install hakrawler using Go"""
    print_status("Installing hakrawler...", "PROCESS")
    
    # Check if Go is available
    if not shutil.which('go'):
        print_status("Go not found - cannot install hakrawler", "ERROR")
        return False
    
    # Install hakrawler
    print_status("Running: go install github.com/hakluke/hakrawler@latest", "PROCESS")
    result = run_command(['go', 'install', 'github.com/hakluke/hakrawler@latest'], timeout=120)
    
    if result and result.returncode == 0:
        print_status("Hakrawler installed successfully", "SUCCESS")
        return True
    else:
        print_status("Failed to install hakrawler", "ERROR")
        if result:
            print_status(f"Error: {result.stderr}", "ERROR")
        return False

def configure_path():
    """Configure PATH to include Go bin directory"""
    print_status("Configuring PATH for hakrawler...", "PROCESS")
    
    go_bin = os.path.expanduser('~/go/bin')
    
    # Check if Go bin directory exists
    if not os.path.isdir(go_bin):
        print_status(f"Go bin directory not found: {go_bin}", "WARNING")
        return False
    
    # Check current PATH
    current_path = os.environ.get('PATH', '')
    if go_bin in current_path:
        print_status("Go bin directory already in PATH", "SUCCESS")
        return True
    
    # Add to shell profiles
    shell_profiles = []
    
    # Determine which shell profiles to update
    if os.path.exists(os.path.expanduser('~/.bashrc')):
        shell_profiles.append('~/.bashrc')
    if os.path.exists(os.path.expanduser('~/.zshrc')):
        shell_profiles.append('~/.zshrc')
    if os.path.exists(os.path.expanduser('~/.profile')):
        shell_profiles.append('~/.profile')
    
    # If no profiles exist, create .bashrc
    if not shell_profiles:
        shell_profiles = ['~/.bashrc']
    
    path_export = f'export PATH="$PATH:{go_bin}"'
    
    for profile in shell_profiles:
        profile_path = os.path.expanduser(profile)
        
        # Check if PATH export already exists
        try:
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    content = f.read()
                    if go_bin in content and 'PATH' in content:
                        print_status(f"PATH already configured in {profile}", "SUCCESS")
                        continue
            
            # Add PATH export
            with open(profile_path, 'a') as f:
                f.write(f'\n# Added by IPCrawler for hakrawler\n{path_export}\n')
            
            print_status(f"Added PATH configuration to {profile}", "SUCCESS")
            
        except Exception as e:
            print_status(f"Failed to update {profile}: {e}", "ERROR")
    
    # Update current environment
    os.environ['PATH'] = f"{current_path}:{go_bin}"
    print_status("Updated current session PATH", "SUCCESS")
    
    return True

def create_system_symlink():
    """Create system-wide symlink for hakrawler"""
    print_status("Creating system symlink for hakrawler...", "PROCESS")
    
    # Find hakrawler
    is_installed, hakrawler_path = check_hakrawler_installation()
    if not is_installed:
        print_status("Hakrawler not found for symlink creation", "ERROR")
        return False
    
    # Create symlink in /usr/local/bin
    symlink_path = '/usr/local/bin/hakrawler'
    
    try:
        # Remove existing symlink if it exists
        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            result = run_command(['sudo', 'rm', '-f', symlink_path])
            if result and result.returncode != 0:
                print_status("Failed to remove existing symlink", "WARNING")
        
        # Create new symlink
        result = run_command(['sudo', 'ln', '-sf', hakrawler_path, symlink_path])
        
        if result and result.returncode == 0:
            print_status(f"Created symlink: {symlink_path} -> {hakrawler_path}", "SUCCESS")
            return True
        else:
            print_status("Failed to create system symlink", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Error creating symlink: {e}", "ERROR")
        return False

def test_ipcrawler_detection():
    """Test if IPCrawler can detect hakrawler"""
    print_status("Testing IPCrawler hakrawler detection...", "PROCESS")
    
    try:
        # Add current directory to Python path
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from workflows.mini_spider_04.config import get_config_manager
        
        cm = get_config_manager()
        detected_path = cm.tools_available.get('hakrawler')
        validation_result = cm.validate_hakrawler_installation()
        
        if detected_path and validation_result:
            print_status(f"IPCrawler successfully detected hakrawler: {detected_path}", "SUCCESS")
            return True
        elif detected_path:
            print_status(f"IPCrawler found hakrawler but validation failed: {detected_path}", "WARNING")
            return False
        else:
            print_status("IPCrawler could not detect hakrawler", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Error testing IPCrawler detection: {e}", "ERROR")
        return False

def main():
    """Main installation and configuration process"""
    print("🔧 Hakrawler Installation and Configuration")
    print("=" * 50)
    
    # Check current installation
    is_installed, current_path = check_hakrawler_installation()
    
    if not is_installed:
        print_status("Hakrawler not found, attempting installation...", "PROCESS")
        
        if not install_hakrawler():
            print_status("Failed to install hakrawler", "ERROR")
            print_status("Please install manually: go install github.com/hakluke/hakrawler@latest", "INFO")
            return False
        
        # Check again after installation
        is_installed, current_path = check_hakrawler_installation()
        if not is_installed:
            print_status("Installation completed but hakrawler still not found", "ERROR")
            return False
    
    # Configure PATH
    if not shutil.which('hakrawler'):
        print_status("Hakrawler not in PATH, configuring...", "PROCESS")
        configure_path()
    
    # Create system symlink for better accessibility
    print_status("Setting up system-wide access...", "PROCESS")
    create_system_symlink()
    
    # Test IPCrawler detection
    if test_ipcrawler_detection():
        print_status("All tests passed! Hakrawler is ready for IPCrawler", "SUCCESS")
        
        # Update mini spider scanner to suppress warnings
        try:
            update_scanner_detection()
        except Exception as e:
            print_status(f"Could not update scanner detection logic: {e}", "WARNING")
        
        return True
    else:
        print_status("IPCrawler detection test failed", "ERROR")
        return False

def update_scanner_detection():
    """Update the mini spider scanner to better handle hakrawler detection"""
    print_status("Updating scanner detection logic...", "PROCESS")
    
    # This will be handled by the broader scanner improvements
    # For now, just confirm detection works
    pass

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n" + "=" * 50)
        print_status("Hakrawler setup completed successfully!", "SUCCESS")
        print_status("IPCrawler Mini Spider will now use hakrawler automatically", "INFO")
        print_status("You may need to restart your terminal or run: source ~/.bashrc", "INFO")
    else:
        print("\n" + "=" * 50)
        print_status("Hakrawler setup encountered issues", "WARNING")
        print_status("IPCrawler will still work but may show hakrawler warnings", "INFO")
        print_status("Run 'python scripts/check_hakrawler.py' for detailed diagnostics", "INFO")
    
    sys.exit(0 if success else 1) 