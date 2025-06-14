#!/usr/bin/env python3
"""
VHost Post-Processor for ipcrawler
Handles discovered VHosts and provides interactive /etc/hosts management
"""

import os
import sys
import subprocess
import shutil
from collections import defaultdict
from datetime import datetime

# Try to import config, fallback to defaults if not available
try:
    from ipcrawler.config import config
except ImportError:
    config = {}

class VHostPostProcessor:
    
    def __init__(self, scan_directories):
        # Handle both single directory (string) and multiple directories (list)
        if isinstance(scan_directories, str):
            self.scan_directories = [scan_directories]
        else:
            self.scan_directories = scan_directories
        self.discovered_vhosts = []
        self.existing_hosts = set()
        
    def discover_vhosts_from_files(self):
        """Parse VHost discovery files and extract hostnames"""
        for scan_dir in self.scan_directories:
            # Extract IP from the parent directory of scan_dir (scan_dir is usually .../IP/scans/)
            # So we need the parent directory name which contains the IP
            parent_dir = os.path.dirname(scan_dir)
            scan_dir_ip = os.path.basename(parent_dir)
            
            for root, dirs, files in os.walk(scan_dir):
                for file in files:
                    if file.startswith('vhost_redirects_') and file.endswith('.txt'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r') as f:
                                content = f.read()
                                
                            # Use the scan directory IP as the target IP
                            ip = scan_dir_ip
                            
                            # Extract hostname from file content
                            for line in content.split('\n'):
                                if line.startswith('Extracted Hostname:'):
                                    hostname = line.split(':', 1)[1].strip()
                                    if hostname and hostname != ip:
                                        self.discovered_vhosts.append({
                                            'hostname': hostname,
                                            'ip': ip,
                                            'file': file_path
                                        })
                        except Exception as e:
                            print(f"❌ Error parsing {file_path}: {e}")
                        
    def read_existing_hosts(self):
        """Read existing /etc/hosts entries"""
        try:
            with open('/etc/hosts', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            for hostname in parts[1:]:
                                self.existing_hosts.add(hostname)
        except Exception as e:
            print(f"❌ Error reading /etc/hosts: {e}")
            
    def backup_hosts_file(self):
        """Create backup of /etc/hosts in scan directory"""
        vhost_config = config.get('vhost_discovery', {})
        if not vhost_config.get('backup_hosts_file', True):
            print("⚠️  Backup disabled in config - proceeding without backup")
            return "/etc/hosts"  # Return original path to continue
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Store backup in the first scan directory (target directory)
        if self.scan_directories:
            # Get the target directory (parent of scan directory)
            target_dir = os.path.dirname(self.scan_directories[0])
            backup_path = os.path.join(target_dir, f"hosts.backup.{timestamp}")
        else:
            # Fallback to /etc/ if no scan directories
            backup_path = f"/etc/hosts.backup.{timestamp}"
            
        try:
            shutil.copy2('/etc/hosts', backup_path)
            print(f"✅ Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return None
            
    def check_sudo_privileges(self):
        """Check if we have sudo privileges"""
        try:
            result = subprocess.run(['sudo', '-n', 'true'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            return result.returncode == 0
        except:
            return False
            
    def add_hosts_entries(self, entries_to_add):
        """Add entries to /etc/hosts"""
        try:
            # Create temporary file with entries
            temp_entries = []
            for entry in entries_to_add:
                temp_entries.append(f"{entry['ip']} {entry['hostname']}")
                
            # Prepare the command
            entries_text = '\n'.join([
                "\n# Added by ipcrawler VHost discovery",
                f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ] + temp_entries + [""])
            
            # Write to /etc/hosts using sudo
            process = subprocess.Popen(['sudo', 'tee', '-a', '/etc/hosts'], 
                                     stdin=subprocess.PIPE, 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     text=True)
            
            stdout, stderr = process.communicate(input=entries_text)
            
            if process.returncode == 0:
                print("✅ Successfully added entries to /etc/hosts")
                return True
            else:
                print(f"❌ Failed to add entries: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding hosts entries: {e}")
            return False
            
    def display_summary_table(self):
        """Display discovered VHosts in a nice table"""
        if not self.discovered_vhosts:
            print("\n📋 No VHosts discovered during scanning")
            return
            
        print("\n" + "="*70)
        print("🌐 DISCOVERED VIRTUAL HOSTS")
        print("="*70)
        
        # Group by IP for cleaner display
        grouped = defaultdict(list)
        for vhost in self.discovered_vhosts:
            grouped[vhost['ip']].append(vhost['hostname'])
            
        for ip, hostnames in grouped.items():
            print(f"\n📍 Target: {ip}")
            for hostname in hostnames:
                status = "✅ NEW" if hostname not in self.existing_hosts else "⚠️  EXISTS"
                print(f"   {hostname} ({status})")
                
        print("\n" + "="*70)
        
    def run_interactive_session(self):
        """Run the interactive VHost management session"""
        # Check if VHost discovery is enabled
        vhost_config = config.get('vhost_discovery', {})
        if not vhost_config.get('enabled', True):
            return
            
        print("\n🚀 VHost Discovery Post-Processing")
        print("=" * 50)
        
        # Discover VHosts from scan files
        self.discover_vhosts_from_files()
        
        if not self.discovered_vhosts:
            print("📋 No VHosts discovered during scanning")
            return
            
        # Read existing hosts
        self.read_existing_hosts()
        
        # Show summary
        self.display_summary_table()
        
        # Filter out existing entries
        new_vhosts = [v for v in self.discovered_vhosts 
                     if v['hostname'] not in self.existing_hosts]
        
        if not new_vhosts:
            print("\n✅ All discovered VHosts already exist in /etc/hosts")
            return
            
        print(f"\n🎯 Found {len(new_vhosts)} new VHost(s) to add")
        
        # Check privileges
        has_sudo = self.check_sudo_privileges()
        
        if not has_sudo:
            print("\n🔐 Sudo privileges required for /etc/hosts modification")
            print("📝 Manual commands saved to _manual_commands.txt files")
            print("\nManual addition commands:")
            for vhost in new_vhosts:
                print(f"echo '{vhost['ip']} {vhost['hostname']}' | sudo tee -a /etc/hosts")
            return
            
        # Check if interactive mode is disabled
        interactive_mode = vhost_config.get('interactive_mode', True)
        
        if not interactive_mode:
            print("\n📝 Interactive mode disabled in config. Manual commands:")
            for vhost in new_vhosts:
                print(f"echo '{vhost['ip']} {vhost['hostname']}' | sudo tee -a /etc/hosts")
            return
        
        # Note: We always show interactive prompts when post-processor is called
        # The main.py logic already handles the auto_add_hosts config check
            
        # Interactive prompt
        print(f"\n🤔 Add {len(new_vhosts)} new VHost(s) to /etc/hosts?")
        
        for vhost in new_vhosts:
            print(f"   {vhost['ip']} {vhost['hostname']}")
            
        # Try multiple input methods for better compatibility
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Flush stdout to ensure prompt is visible
                import sys
                sys.stdout.flush()
                
                # Enhanced input prompt with better visibility
                print(f"\n[Y]es / [N]o / [S]how details: ", end='')
                sys.stdout.flush()
                
                # Try to get input with better terminal handling
                try:
                    import termios
                    import tty
                    
                    # Save current terminal settings
                    old_settings = termios.tcgetattr(sys.stdin)
                    
                    try:
                        # Set terminal to raw mode for better input visibility
                        tty.setraw(sys.stdin.fileno())
                        
                        # Read single character
                        char = sys.stdin.read(1)
                        
                        # Echo the character so user can see what they typed
                        print(char, end='', flush=True)
                        
                        # If it's not a newline, wait for Enter
                        if char != '\n':
                            while True:
                                next_char = sys.stdin.read(1)
                                if next_char == '\n' or next_char == '\r':
                                    print()  # Add newline
                                    break
                        
                        choice = char.lower().strip()
                        
                    finally:
                        # Restore terminal settings
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        
                except (ImportError, OSError):
                    # Fallback to regular input if termios not available
                    choice = input().lower().strip()
                
                if choice in ['y', 'yes', '']:
                    # Create backup
                    backup_path = self.backup_hosts_file()
                    if backup_path is None:
                        print("❌ Failed to create backup. Aborting.")
                        return
                        
                    print(f"✅ Created backup: {backup_path}")
                    
                    # Add entries
                    if self.add_hosts_entries(new_vhosts):
                        print("🎉 VHost entries successfully added!")
                        print(f"💡 Use 'sudo nano /etc/hosts' to edit manually if needed")
                        print(f"🔄 Restore with: sudo cp '{backup_path}' /etc/hosts")
                    break
                    
                elif choice in ['n', 'no']:
                    print("❌ Skipping VHost addition")
                    print("\n📝 Manual addition commands:")
                    for vhost in new_vhosts:
                        print(f"echo '{vhost['ip']} {vhost['hostname']}' | sudo tee -a /etc/hosts")
                    break
                    
                elif choice in ['s', 'show']:
                    print("\n📋 Detailed VHost Information:")
                    for vhost in new_vhosts:
                        print(f"  📁 File: {vhost['file']}")
                        print(f"  🌐 Hostname: {vhost['hostname']}")
                        print(f"  📍 IP: {vhost['ip']}")
                        print()
                    continue  # Ask again
                    
                else:
                    print(f"❌ Invalid choice: '{choice}'. Please enter Y, N, or S.")
                    attempt += 1
                    continue
                    
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Input cancelled by user")
                print("\n📝 Manual addition commands:")
                for vhost in new_vhosts:
                    print(f"echo '{vhost['ip']} {vhost['hostname']}' | sudo tee -a /etc/hosts")
                break
                
            except Exception as e:
                print(f"\n❌ Input error: {e}")
                attempt += 1
                if attempt >= max_attempts:
                    print("❌ Max input attempts reached. Falling back to manual commands:")
                    for vhost in new_vhosts:
                        print(f"echo '{vhost['ip']} {vhost['hostname']}' | sudo tee -a /etc/hosts")
                    break
                else:
                    print(f"🔄 Retrying... (attempt {attempt + 1}/{max_attempts})")
                    continue

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python3 vhost_post_processor.py <scans_directory>")
        sys.exit(1)
        
    scans_dir = sys.argv[1]
    
    if not os.path.exists(scans_dir):
        print(f"❌ Scans directory not found: {scans_dir}")
        sys.exit(1)
        
    processor = VHostPostProcessor(scans_dir)
    processor.run_interactive_session()

if __name__ == "__main__":
    main() 