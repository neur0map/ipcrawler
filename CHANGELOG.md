# 📋 Changelog

All notable changes to **ipcrawler** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.1] - 2025-01-XX 🔧

### 🚨 CRITICAL FIX - Long Scan Hanging Issues
**Resolved the major 98% completion hanging issue that prevented long scans from finishing**

### 🔧 Fixed - Core Framework
- **Process Timeout Management**: Added comprehensive timeout system to prevent indefinite hanging
  - **30-minute default timeout** for all processes with configurable overrides
  - **Graceful termination** (SIGTERM → SIGKILL) for stuck processes
  - **Timeout monitoring tasks** running alongside each process
  - **Proper cleanup** of timeout tasks to prevent memory leaks
- **Stream Reader Improvements**: Enhanced process output handling
  - **30-second timeout** for individual readline operations
  - **None stream handling** for failed processes
  - **Better error handling** to prevent hanging on stream errors
  - **Graceful degradation** when streams fail
- **Target Cleanup**: Improved process management during scan completion
  - **Timeout task cleanup** when targets complete
  - **Enhanced process termination** during global timeouts
  - **Better handling** of stale tasks and processes

### 🔧 Fixed - Plugin-Specific Issues
- **Directory Busting** (`dirbuster.py`): Added timeout and recursion controls
  - **Configurable timeout** (default: 30 minutes)
  - **Maximum recursion depth** limits (default: 4 levels) to prevent infinite loops
  - **Tool-specific depth controls**: `--depth N` for feroxbuster, `--max-recursion-depth=N` for dirsearch
  - **`timeout` command wrapper** for all directory busting tools
- **Web Vulnerability Scanning** (`nikto.py`): Added timeout protection
  - **Configurable timeout** (default: 30 minutes)
  - **`timeout` command wrapper** to prevent indefinite scanning
- **DNS Enumeration**: Added timeout controls for subdomain discovery
  - **Subdomain enumeration** (`subdomain-enumeration.py`): 30-minute timeout with `timeout` wrapper
  - **DNS bruteforce** (`dnsrecon-subdomain-bruteforce.py`): Timeout for manual commands

### ✨ Added - User Configuration
- **Quick Hanging Fixes**: Simple command-line options for immediate relief
  ```bash
  ipcrawler --exclude-tags long target.com     # Skip long-running tools
  ipcrawler --timeout 60 target.com           # 60-minute global timeout
  ipcrawler --target-timeout 30 target.com    # 30-minute per-target timeout
  ```
- **Plugin-Specific Timeouts**: Granular control in `~/.config/ipcrawler/global.toml`
  ```toml
  [dirbuster]
  timeout = 1800      # 30 minutes max for directory busting
  max_depth = 4       # Prevent infinite recursion
  
  [nikto]
  timeout = 1800      # 30 minutes max for web vulnerability scanning
  ```
- **Timeout Hierarchy**: Multi-level timeout system
  1. **Global timeout** (`--timeout`): Maximum total scan time
  2. **Target timeout** (`--target-timeout`): Maximum time per target
  3. **Plugin timeout** (configurable): Maximum time per plugin execution
  4. **Stream timeout** (30s): Maximum time for individual read operations

### 📖 Enhanced - Documentation
- **README Updates**: Added timeout management section with quick fixes
- **Configuration Examples**: Complete timeout configuration examples
- **Troubleshooting Guide**: Solutions for hanging scans and timeout tuning

### 🎯 Impact
- **No more 98% hanging**: Processes terminate gracefully after reasonable timeouts
- **Better resource management**: Prevents memory leaks and zombie processes
- **User control**: Configurable timeouts for different use cases
- **Graceful degradation**: Failed processes don't block entire scans
- **Monitoring capabilities**: Real-time status and timeout warnings

### 🚨 Breaking Changes
- **None**: All timeout features are opt-in with sensible defaults

---

## [2.1.0] - 2025-06-13 🌐

### 🚀 SMART VHOST AUTO-DISCOVERY & PROGRESS BAR ENHANCEMENTS
**Major update introducing intelligent virtual host management and enhanced progress tracking for HTB and CTF environments**

### ✨ Added - VHost Auto-Discovery System
- **🌐 Intelligent VHost Detection**: Detects virtual hosts from HTTP redirects, error pages, and response content
- **🏠 Smart /etc/hosts Management**: Automatically adds discovered vhosts to `/etc/hosts` during scanning
- **🎯 HTB Environment Detection**: Auto-enables vhost management when HTB indicators detected
- **🔐 Permission Management**: Smart sudo detection and privilege escalation for hosts file modification
- **📋 Automatic Backup**: Creates timestamped backups of `/etc/hosts` before modifications
- **🔄 Real-Time Addition**: Adds vhosts immediately upon discovery (eliminates 400 errors!)
- **🛡️ Duplicate Prevention**: Prevents duplicate entries and checks existing hostnames
- **💡 Manual Fallback**: Provides copy-paste commands when auto-add unavailable

### 🔧 Enhanced - Discovery Methods
- **VHost Redirect Hunter**: Enhanced to auto-add discovered redirects to `/etc/hosts`
- **HTTP Response Analysis**: New curl plugin enhancement parsing responses for hostname patterns
- **Pattern Detection**: Advanced regex patterns for detecting vhosts in:
  - HTTP redirects and Location headers
  - HTML titles and content (especially `.htb` domains)
  - Server error messages and configuration pages
  - Link href attributes and form actions

### 📊 Enhanced - Progress Bar System
- **⏱️ Realistic Duration Estimates**: Updated with actual scan times:
  - Port scans: 15s → 60s (4x more realistic)
  - Nikto/Gobuster: 8s → 300s (5 minutes for web scans)
  - Nmap services: 8s → 120s (2 minutes)
  - Other services: 8s → 60s (1 minute)
- **📈 Asymptotic Progress Curve**: Continues advancing smoothly past estimated duration
  - Eliminated "stuck at 90%" issue using exponential decay to approach 98%
  - Provides realistic progress indication for long-running scans
- **🎯 Deduplication System**: Prevents multiple progress bars for same scan types
- **✨ Rich Visual Feedback**: Enhanced display with modern spinners and formatting

### 🎨 Enhanced - User Experience  
- **🌐 Live VHost Notifications**: Real-time Rich console output when vhosts discovered and added
- **📋 HTB Optimization**: Perfect integration for HackTheBox machines with `.htb` domains
- **⚡ Zero Interruption**: Scanning continues seamlessly after vhost discovery
- **🔍 Debug Information**: Enhanced verbosity levels for troubleshooting

### 🛠️ Technical Improvements
- **🧮 Mathematical Progress**: Exponential decay formula: `progress = 90% + 8% × (1 - e^(-overtime/60s))`
- **🔄 Concurrent Processing**: VHost detection runs parallel without performance impact
- **🛡️ Error Handling**: Robust handling for permission issues and network failures
- **📁 Code Organization**: New `VHostManager` class with clean separation of concerns

### 🎯 Use Cases
- **HTB Machines**: Auto-resolves virtual hosts like `furni.htb`, `faculty.htb`, etc.
- **CTF Challenges**: Handles web applications with hostname-based routing
- **Enterprise Testing**: Manages complex virtual host configurations
- **OSCP Preparation**: Streamlined workflow for exam environments

### 💡 Configuration Options
```toml
[vhost_discovery]
enabled = true                    # Enable/disable vhost auto-discovery
backup_hosts_file = true         # Create backups before modification  
request_timeout = 10             # HTTP request timeout for discovery
user_agent = "ipcrawler-vhost-hunter/1.0"  # User agent for requests
```

### 🚨 Breaking Changes
- **None**: All changes are backwards compatible and opt-in based on environment detection

---

## [2.0.2] - 2025-06-13 🔄

### 🚀 DEVELOPMENT WORKFLOW OVERHAUL
**Fixed critical development workflow issues preventing proper git updates and code propagation**

### 🔧 Fixed - Development Infrastructure
- **Entry Point Confusion**: Fixed `make setup` to use correct development entry point
  - **Issue**: `ipcrawler-cmd` was calling `ipcrawler.py` instead of `ipcrawler/main.py` with proper `PYTHONPATH`
  - **Result**: Commands now properly execute development code instead of cached versions
- **Cache Override Problem**: Fixed Application Support cache overriding source code changes
  - **Issue**: `make setup` created cached files that ignored git updates
  - **Solution**: Enhanced `make update` to clean cached files and recreate symlinks to source
- **Git Update Propagation**: Fixed disconnect between `git pull` and running code
  - **Issue**: Users could run `git pull` but changes wouldn't take effect due to cached installations
  - **Solution**: `make update` now ensures all git changes become active immediately

### ✨ Enhanced - Update System
- **Smart Cache Management**: `make update` now automatically:
  - Stashes uncommitted changes before git pull
  - Cleans Application Support cached plugins
  - Recreates symlinks from cache to source code
  - Regenerates command scripts with latest code
  - Updates Python packages and system tools
  - Restores stashed changes after update
- **Config Migration**: Enhanced config handling to preserve user settings while updating
- **Backup Protection**: Automatically backs up user configs before cleaning cache

### 🎯 Enhanced - Tag Filtering System
- **Fixed `--list` Command**: Now properly applies tag filtering when showing available plugins
- **Tag Processing Logic**: Improved subset matching for complex tag combinations like `default+safe+quick`
- **Plugin Count Display**: Accurate active/excluded plugin counts in `--list` output
- **Performance Optimization**: Faster plugin filtering with proper tag subset logic

### 🛠️ Fixed - Plugin Infrastructure  
- **Path Quoting Issues**: Fixed wordlist paths with spaces in directory busting tools
  - **Affected**: feroxbuster, gobuster, dirsearch, ffuf, dirb commands
  - **Issue**: Paths like `/Users/.../Application Support/ipcrawler/wordlists/` failed due to unescaped spaces
  - **Solution**: Proper path quoting in all plugin command generation
- **Duplicate Plugin Prevention**: Disabled conflicting `all-tcp-ports` scanner to prevent duplicate scans
- **Plugin Symlink Management**: Fixed plugin loading to use source code instead of cached copies

### 📋 Enhanced - User Workflow
- **Clear Update Process**: Users can now safely use standard git workflow:
  ```bash
  git pull           # Gets latest source code  
  make update        # Cleans cache, updates everything, activates changes
  ```
- **Development Mode**: Enhanced developer experience with proper source code execution
- **Tool Installation**: Improved missing tool detection and installation suggestions

### 🔍 Technical Improvements
- **Entry Point Standardization**: All execution paths now use proper development entry points
- **Configuration Consistency**: Unified config loading between development and installed versions
- **Error Handling**: Better error messages for setup and update operations
- **Cross-Platform Compatibility**: Enhanced macOS and Linux support for development workflow

---

## [2.0.1] - 2025-06-13 🐛

### 🐛 CRITICAL BUG FIXES
**Fixed major plugin check issues that were preventing plugins from running with default tags**

### 🔧 Fixed
- **Plugin Check Logic**: Fixed missing `return True` statements in multiple plugin `check()` methods
  - Fixed: `dnsrecon`, `redis-cli`, `dnsrecon-subdomain-bruteforce`, `enum4linux`, `oracle-scanner`, `oracle-tnscmd`
  - **Impact**: Plugins with available tools were incorrectly failing checks and not running
  - **Result**: Plugins now properly pass checks when their required tools are installed
- **Progress Bar Exception**: Fixed `IndexError` in ProgressManager when tasks were removed during updates
  - Added proper error handling and task existence checks in `_progress_updater()`
  - **Impact**: Eliminated random crashes during progress bar updates
  - **Result**: Smooth progress bar operation without exceptions
- **Directory Buster Auto-Detection**: Enhanced dirbuster plugin to automatically detect available tools
  - Auto-switches from `feroxbuster` → `ffuf` → `dirsearch` → `gobuster` → `dirb`
  - **Impact**: Directory busting now works with `--tags default` when any compatible tool is available
  - **Result**: Improved plugin compatibility across different systems

### 📈 Improvements
- **Plugin Resilience**: All plugins now handle tool availability checks correctly
- **Better Error Messages**: Enhanced plugin error reporting with installation suggestions
- **System Compatibility**: Improved cross-platform tool detection and usage

---

## [2.0.0] - 2025-06-13 🎨

### 🎨 MAJOR UI OVERHAUL - Feroxbuster-Inspired Interface
**ipcrawler** v2.0.0 introduces a complete visual transformation inspired by feroxbuster's clean, professional interface while maintaining all core functionality and backwards compatibility.

### ✨ Added
- **🕷️ Creepy ASCII Art**: Spider-themed startup banner with version info and professional branding
- **📊 Configuration Display**: Beautiful Rich-formatted configuration table showing all TOML settings at startup
- **📈 Live Progress Bars**: Real-time progress tracking with animated spinners for port and service scans
- **🎯 Enhanced Discovery Output**: Feroxbuster-style `GET 200 tcp/22 ssh 154.53.32.192` formatting for all discoveries
- **📋 Rich Plugin Listing**: Completely redesigned `--list` command with organized tables, icons, and usage examples
- **🎪 Status Icons**: Emoji-based status indicators (🔍 PortScan, 🔧 ServiceScan, 📊 Report, 🚨 ERROR, ⚠️ WARNING)

### 🔧 Enhanced
- **Terminal Output**: All verbosity levels now use Rich formatting with consistent color schemes and styling
- **Progress Tracking**: ProgressManager class with concurrent progress bars, percentage completion, and elapsed time
- **Error Messages**: Professional error formatting with clean color code removal and enhanced readability
- **Scan Summaries**: Beautiful completion statistics with total scans, elapsed time, and discovery counts
- **Configuration Integration**: Seamless integration with existing TOML configuration system

### 🎨 Visual Improvements
- **Startup Banner**: Professional separator lines and clean layout matching feroxbuster aesthetic
- **Message Formatting**: `Text.assemble()` for consistent styling across all output types
- **Color Management**: Proper cleanup of legacy color codes (`{bright}`, `{rst}`, `{byellow}`, etc.)
- **Interactive Elements**: Enhanced progress bars that disappear when complete for clean terminal output
- **Plugin Organization**: Alphabetically sorted plugin lists with type-specific icons and descriptions

### 🔄 Technical Changes
- **Rich Library Integration**: Full utilization of Rich's Table, Panel, Progress, and Text components
- **Backwards Compatibility**: All existing TOML configurations and plugin systems remain unchanged
- **Performance Optimization**: Parallel progress tracking without impacting scan performance
- **Code Organization**: Enhanced `io.py` with modular functions for different UI components

### 📦 Dependencies
- **Rich Library**: Enhanced terminal output with professional formatting capabilities
- **Progress Tracking**: Real-time updates with animated spinners and completion percentages
- **Configuration Display**: Dynamic TOML value rendering in startup configuration table

### 🐛 Fixed
- **Message Processing**: Improved handling of all message types including basic `[*]` info messages
- **Color Code Cleanup**: Proper removal of legacy formatting codes for clean Rich rendering
- **Progress Bar Lifecycle**: Automatic cleanup of completed progress bars for tidy terminal output

---

## [1.1.4] - 2025-01-12 🛠️

### 🛠️ Plugin & Backup Improvements
- **Fixed Plugin Loading**: Resolved "datetime not a subclass" error by filtering out imported classes from plugin validation
- **Enhanced Backup Location**: VHost /etc/hosts backups now stored in target scan directory instead of /etc/ (survives terminal closure)
- **Improved Plugin Validation**: Plugin loader now only validates classes defined in plugin files, not imported dependencies
- **Better Backup Persistence**: Backup files stored in `results/IP/hosts.backup.timestamp` for easy access and restoration

---

## [1.1.3] - 2025-01-12 🔥

### 🔥 HOTFIX - Critical IP Extraction Bug
- **CRITICAL**: Fixed IP extraction logic to use parent directory instead of scan directory name
- **Root Cause**: VHost post-processor was extracting IP from "scans" directory instead of parent target directory
- **Impact**: Now correctly adds `10.10.11.68 planning.htb` instead of `scans planning.htb` to /etc/hosts
- **Directory Structure**: Properly handles ipcrawler's structure: `results/IP/scans/` → extracts IP from parent directory

---

## [1.1.2] - 2025-01-12 🚨

### 🚨 Critical Bug Fixes
- **CRITICAL**: Fixed incorrect IP address extraction in VHost post-processor (was using directory name "scans" instead of target IP)
- **CRITICAL**: Fixed invisible input during VHost interactive prompts with enhanced terminal handling
- **Enhanced Input System**: Added character echoing and proper terminal mode management for better user experience
- **Improved Error Handling**: Better fallback options for input failures with multiple retry attempts
- **Visual Feedback**: Enhanced interactive VHost management sessions with clearer prompts and status messages

---

## [1.1.1] - 2025-06-12 🔧

### 🐛 Fixed
- **VHost Discovery Priority**: VHost Redirect Hunter now runs before Virtual Host Enumeration (priority 10 vs 5)
- **Post-Processing Path Resolution**: Fixed post-processor to correctly scan all target directories instead of single 'scans' directory
- **File Detection Logic**: Enhanced VHost file discovery to properly locate `vhost_redirects_*.txt` files in target subdirectories
- **Plugin Execution Order**: Ensured VHost Redirect Hunter takes priority over other VHost enumeration methods

### 🔧 Enhanced
- **Error Handling**: Improved error messages and debugging information for VHost discovery issues
- **Directory Scanning**: More robust directory traversal for multi-target scenarios

---

## [1.1.0] - 2025-06-12 🌐

### 🚀 VHost Discovery Release
**ipcrawler** v1.1.0 introduces comprehensive virtual host discovery capabilities with interactive `/etc/hosts` management, making it even easier to handle complex web applications during penetration testing.

### ✨ Added
- **🌐 VHost Discovery System**
  - **VHost Redirect Hunter Plugin**: Automatic discovery of hostnames via HTTP redirect analysis
  - **Interactive Post-Processing**: Smart `/etc/hosts` management with Y/N/S options for user control
  - **Safety Features**: Automatic backup of `/etc/hosts` before modifications with timestamped files
  - **Configuration-Driven**: Full control via `[vhost_discovery]` section in config.toml
  - **Intelligent Detection**: Duplicate prevention and existing entry detection
  - **Manual Fallback**: Copy-paste commands generated when sudo privileges unavailable
  - **Beautiful Output**: Emoji-rich progress indicators and summary tables
  - **Integration**: Seamless integration with existing HTML reporting system

### 🔧 Enhanced
- **Post-Scan Processing**: Automatic VHost management runs after all scans complete
- **Configuration System**: New VHost-specific settings (timeout, user-agent, auto-add behavior)
- **Error Handling**: Graceful fallbacks and comprehensive error management
- **Reporting Integration**: VHost discoveries automatically included in Rich HTML reports

---

## [1.0.0] - 2025-06-10 🎉

### 🚀 Initial Release
**ipcrawler** v1.0.0 marks the first stable release of our simplified AutoRecon fork, designed to make network reconnaissance accessible for CTFs, OSCP, and penetration testing.

### ✨ Added
- **🎨 Enhanced User Experience**
  - Beautiful Rich-formatted `--help` with organized sections, examples, and pro tips
  - Rich-colored output for verbosity levels (`-v`, `-vv`, `-vvv`) with visual progress indicators
  - Professional command-line interface with improved readability
  
- **🔧 Streamlined Setup Process**
  - One-command setup with `make setup` for local installation
  - Docker support with `make setup-docker` for cross-platform compatibility
  - Automatic Docker detection and smart installation workflow
  - `bootstrap.sh` script for OS-specific dependency management
  - Windows `.bat` file for seamless Docker integration

- **📦 Platform Support**
  - Native Linux/macOS support with local installation
  - Full Windows compatibility via Docker
  - HTB machine compatibility with optimized tool paths
  - Cross-platform wordlist and dependency management

- **🛠️ Build System & Automation**
  - Comprehensive Makefile with setup, docker, update, and cleanup commands
  - Automated virtual environment creation and management
  - Docker image building with security tools pre-installed
  - Global command wrapper installation (`ipcrawler-cmd`)

- **📚 Documentation & User Guides**
  - Step-by-step setup instructions for all platforms
  - Video tutorial integration for HTB and macOS setups
  - Comprehensive README with troubleshooting guides
  - Configuration file documentation with TOML examples

- **📊 Enhanced Reporting System**
  - Rich HTML Summary Reports with interactive collapsible sections
  - Key findings extraction and executive summary generation
  - Beautiful CSS styling with responsive design and dark code themes
  - Combined multi-target reporting capabilities
  - Automatic discovery and presentation of URLs, domains, vulnerabilities
  - Technology stack detection and credential extraction

- **🕷️ VHost Redirect Hunter (NEW)**
  - Automatic discovery of hostnames via HTTP redirect analysis
  - Post-scan interactive prompt to add discovered VHosts to `/etc/hosts`
  - Smart privilege elevation - prompts for `sudo` only when needed
  - Beautiful emoji-rich output with summary tables
  - Automatic backup of `/etc/hosts` before modifications
  - Duplicate detection and manual command generation
  - Configurable timeouts and user agents
  - File-based results organization with intelligent filtering
  - Print-friendly layouts and mobile-responsive design

### 🔄 Changed (from AutoRecon)
- **Simplified Installation**: From complex `pipx` commands to simple `make setup`
- **Enhanced CLI**: Rich formatting replaces basic terminal output
- **Better Error Handling**: Improved error messages and dependency checking
- **Modern Configuration**: TOML-based config files with better organization
- **Streamlined Workflow**: Automated setup replaces manual dependency management

### 🔧 Technical Improvements
- **Dependencies**: Added Rich library for enhanced terminal output
- **Python Requirements**: Maintained Python 3.8+ compatibility
- **Plugin System**: Inherited 80+ reconnaissance plugins from AutoRecon
- **Architecture**: Multi-threaded scanning with concurrent execution
- **Configuration**: Enhanced TOML configuration with user-friendly defaults

### 🗂️ Core Features (Inherited from AutoRecon)
- **Port Scanning**: Comprehensive TCP/UDP port discovery
- **Service Enumeration**: 80+ specialized plugins for service analysis
- **Web Application Testing**: Directory busting, vulnerability scanning
- **SMB Enumeration**: Share discovery, user enumeration, vulnerability checks
- **DNS Reconnaissance**: Zone transfers, subdomain enumeration
- **Database Testing**: MySQL, MSSQL, Oracle, MongoDB scanning
- **Brute Force Testing**: SSH, FTP, RDP, HTTP authentication
- **Reporting**: Multiple output formats (Markdown, CherryTree, Rich HTML)

### 🐛 Fixed
- Platform-specific installation issues resolved via Docker option
- Dependency conflicts addressed through virtual environment isolation
- Path resolution problems fixed for various operating systems
- WordList location issues resolved with automatic detection

---

## 🚀 Future Goal

### 🎯 [1.2.0] - YOLO Mode & Enhanced Automation
**Target Date**: Q1 2025

#### 🚀 Full YOLO Mode
- **Auto-Execute Recommended Commands**: Automatically run all commands from `_manual_commands.txt`
- **Smart Command Prioritization**: Execute high-value commands first (credential dumping, exploit attempts)
- **Interactive Confirmation**: Optional prompts for destructive commands
- **Parallel Execution**: Run multiple manual commands simultaneously where safe

#### 🛠️ Additional Tools & Templates
- **Extended Tool Integration**: Add more reconnaissance tools (subfinder, amass, feroxbuster, etc.)
- **CTF-Focused Templates**: Optimized plugin configurations for common CTF scenarios
- **Custom Wordlists**: Curated wordlists for specific environments (HTB, THM, OSCP)
- **Quick Exploit Modules**: Built-in common exploit execution (EternalBlue, PrintNightmare, etc.)

#### 📋 Smart Templates
- **Environment Detection**: Auto-detect HTB/THM/OSCP environments and adjust scanning approach
- **Target Profiling**: Automatically select optimal plugin sets based on discovered services
- **Time-Bounded Modes**: OSCP exam mode with strict time limits and prioritized scanning
- **Stealth Mode**: Reduced noise scanning for more realistic penetration testing scenarios

---

## 📝 Versioning Scheme

- **Major Version** (x.0.0): Breaking changes, major feature additions
- **Minor Version** (1.x.0): New features, backward compatible
- **Patch Version** (1.0.x): Bug fixes, security updates

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:
- Bug reports and feature requests
- Plugin development
- Documentation improvements
- Code contributions

## 📞 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/neur0map/ipcrawler/issues)
- **Documentation**: [Full documentation](https://github.com/neur0map/ipcrawler/wiki)
- **Community**: [Discord server](https://discord.gg/ipcrawler) for discussions and support

---

*Built with ❤️ for the cybersecurity community* 
