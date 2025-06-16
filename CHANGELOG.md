# Changelog

All notable changes to **ipcrawler** will be documented in this file.

---

## [2.2.0] - 2025-01-17

### Added
- **LFI Testing Plugin**: Smart Local File Inclusion vulnerability scanner (`curl-lfi-test.py`)
- Smart endpoint discovery from directory busting results (feroxbuster, gobuster, dirsearch, dirb, ffuf)
- Parameter extraction from HTML forms, JavaScript, and URLs
- Intelligent ffuf fallback scanning with two-phase approach
- LFI-specific wordlist configuration in `global.toml`

### Enhanced
- Rich Summary reporting with LFI vulnerability patterns and evidence detection
- HTB-optimized performance (2-6 minute scan times on low-resource machines)
- Configurable resource limits and threading controls

---

## [2.1.3] - 2025-01-16

### Added
- **MegaLinter Integration**: Automated code quality analysis with 65+ language support
- **Enhanced Discord Notifications**: Code quality status included in commit reports  
- **Dependabot Configuration**: Automated dependency updates (weekly)

### Fixed
- Discord notification reliability (missing authors, hardcoded file lists)
- GitHub Actions workflow improvements
- jq syntax errors in notification scripts

### Changed
- Intelligence Report now includes real-time code quality analysis
- Discord notifications wait for MegaLinter completion before posting
- Enhanced error handling throughout CI/CD pipeline

---

## [2.1.2] - 2025-01-XX

### Fixed
- **Critical**: Global wordlist priority system prevents long scan hanging
- Plugins now check `global.toml` wordlist settings before using massive defaults
- Reduced default wordlist sizes: 220K → 4.6K entries (95% reduction)

### Added
- Global wordlist configuration in `global.toml`
- Fallback protection for wordlist configurations
- Performance improvements for directory/subdomain enumeration

---

## [2.1.1] - 2025-01-XX

### Fixed
- **Critical**: Long scan hanging issues at 98% completion
- Process timeout management (30-minute default timeout)
- Stream reader improvements with graceful error handling
- Directory busting recursion controls and timeout protection

### Added
- Quick hanging fixes via command-line options (`--exclude-tags long`, `--timeout`)
- Plugin-specific timeout configurations
- Multi-level timeout hierarchy (global → target → plugin → stream)

---

## [2.1.0] - 2025-06-13

### Added
- **VHost Auto-Discovery**: Intelligent virtual host detection and `/etc/hosts` management
- **HTB Environment Detection**: Auto-enables vhost management for HackTheBox machines
- **Enhanced Progress Bars**: Realistic duration estimates and asymptotic progress curves
- **Live VHost Notifications**: Real-time console output for discovered hosts

### Fixed
- Progress bar "stuck at 90%" issue
- VHost pattern detection in HTTP responses
- Duplicate prevention in hosts file management

---

## [2.0.2] - 2025-06-13

### Fixed
- **Critical**: Development workflow issues preventing git updates
- Entry point confusion between cached and source code versions
- Cache override problems in Application Support directory
- Plugin path quoting issues with spaces in directory names

### Enhanced
- Smart cache management in `make update`
- Tag filtering system and plugin count display
- Cross-platform compatibility for development workflow

---

## [2.0.1] - 2025-06-13

### Fixed
- **Critical**: Missing `return True` statements in plugin check methods
- Progress bar IndexError during task removal
- Directory buster auto-detection across different tools

### Improved
- Plugin resilience and error reporting
- System compatibility and tool detection

---

## [2.0.0] - 2025-06-13

### Added
- **Major UI Overhaul**: Feroxbuster-inspired interface with Rich library
- ASCII art startup banner with configuration display
- Live progress bars with animated spinners
- Enhanced discovery output formatting
- Rich plugin listing with organized tables

### Changed
- Complete visual transformation while maintaining backwards compatibility
- Professional terminal output with consistent styling
- Interactive elements and progress tracking

---

## [1.1.4] - 2025-01-12

### Fixed
- Plugin loading "datetime not a subclass" error
- VHost backup location moved to target scan directory
- Plugin validation for imported dependencies

---

## [1.1.3] - 2025-01-12

### Fixed
- **Critical**: IP extraction logic for VHost post-processor
- Directory structure handling in results extraction

---

## [1.1.2] - 2025-01-12

### Fixed
- **Critical**: Incorrect IP address extraction in VHost post-processor
- Invisible input during VHost interactive prompts
- Enhanced terminal handling and input system

---

## [1.1.1] - 2025-06-12

### Fixed
- VHost Discovery priority execution order
- Post-processing path resolution for target directories
- File detection logic for vhost redirect files

---

## [1.1.0] - 2025-06-12

### Added
- **VHost Discovery System**: Automatic hostname discovery via HTTP redirect analysis
- Interactive `/etc/hosts` management with safety features
- Configuration-driven VHost settings
- Integration with HTML reporting system

---

## [1.0.0] - 2025-06-10

### Added
- Initial stable release
- Enhanced user experience with Rich-formatted CLI
- Streamlined setup process with `make setup`
- Cross-platform support (Linux/macOS/Windows via Docker)
- Comprehensive build system and automation
- Enhanced HTML reporting with interactive features
- 80+ reconnaissance plugins inherited from AutoRecon

### Changed
- Simplified installation process
- Modern TOML-based configuration
- Enhanced error handling and dependency checking

---

## Future Roadmap

### [1.2.0] - YOLO Mode & Enhanced Automation
- Auto-execute recommended commands from manual output
- Smart command prioritization and parallel execution
- CTF-focused templates and environment detection
- Extended tool integration and custom wordlists

---

## Versioning
- **Major** (x.0.0): Breaking changes, major features
- **Minor** (1.x.0): New features, backward compatible  
- **Patch** (1.0.x): Bug fixes, security updates

## Support
- [GitHub Issues](https://github.com/neur0map/ipcrawler/issues)
- [Documentation](https://github.com/neur0map/ipcrawler/wiki) 