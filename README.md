# ipcrawler

**A modern security tool orchestration framework designed for professionals and CTF participants**

[![Version](https://img.shields.io/badge/version-0.1.0--alpha-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.8+-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-Open%20Source-green.svg)]()

---

## Overview

ipcrawler is a production-ready security tool orchestration framework that revolutionizes how security professionals conduct reconnaissance and vulnerability assessments. Built with a security-first architecture, it provides a powerful preset system, advanced Rich TUI interface, and seamless integration with popular security tools.

### Key Features

- **Revolutionary Preset System** - Reduce template complexity by 60-70% with predefined tool configurations
- **Advanced Rich TUI** - Real-time progress tracking with 6 professional themes
- **Security-First Design** - Safe command execution with comprehensive validation
- **HTB/CTF Optimized** - Specialized presets for Capture The Flag scenarios
- **Multi-Format Results** - Automatic export to Markdown, JSON, and plain text
- **Async Execution** - Concurrent scanning with intelligent resource management

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/ipcrawler.git
cd ipcrawler

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# List available templates
python ipcrawler.py list

# Run HTB-optimized scans
python ipcrawler.py -htb target.com

# Run specific template
python ipcrawler.py run htb/nmap-htb-scan target.com

# View results
python ipcrawler.py results target.com

# Export results to markdown
python ipcrawler.py export target.com --format md --output report.md
```

## Template System

ipcrawler uses a JSON-based template system that leverages powerful presets to simplify security tool configuration.

### Modern Preset-Based Template

```json
{
  "name": "nmap-htb-scan",
  "tool": "nmap",
  "preset": "nmap.htb_scan",
  "args": ["{{target}}"],
  "description": "HTB-optimized nmap scan with service detection",
  "author": "neur0map",
  "version": "1.0.0",
  "tags": ["htb", "nmap", "service-detection"]
}
```

### Available Categories

- **HTB Templates** - Hack The Box optimized scanning tools
- **Reconnaissance** - Network and service discovery
- **Web Analysis** - HTTP/HTTPS security assessment
- **DNS Enumeration** - Domain and subdomain discovery

## Rich TUI Interface

Experience modern terminal interfaces with real-time progress tracking, customizable themes, and intuitive status displays.

### Themes Available

- **Minimal** - Clean, professional design (default)
- **Dark** - Dark theme with subtle colors
- **Matrix** - Green matrix-style interface
- **Cyber** - Cyan/magenta cyberpunk aesthetic
- **Hacker** - Bright green hacker theme
- **Corporate** - Professional blue design

### Configuration

```toml
[ui]
enable_rich_ui = true
theme = "minimal"
fullscreen_mode = false
refresh_rate = 2
```

## Security Architecture

ipcrawler implements comprehensive security measures to ensure safe operation:

- **No Shell Execution** - Direct tool invocation only, never shell commands
- **Input Validation** - Comprehensive sanitization and validation
- **Resource Limits** - Memory, timeout, and output size constraints
- **Command Isolation** - Secure execution environment
- **Template Validation** - JSON schema and security validation

## Results Management

Automatic result organization with multiple output formats:

```
results/target/
├── success/     # Individual successful scan records
├── errors/      # Error tracking and debugging
├── machine/     # Monthly aggregated data (JSONL)
└── readable/    # Human-readable summaries (MD/TXT)
```

## Advanced Features

### Debug Mode with Sentry Integration

Enable comprehensive error tracking for development and troubleshooting:

```bash
# Create .env file
echo "SENTRY_DSN=your-sentry-dsn" > .env

# Run with debug mode
python ipcrawler.py -debug -htb target.com
```

### Preset System

Create powerful, reusable tool configurations:

```toml
[presets.nmap]
htb_scan = ["-sV", "-T4", "--min-rate", "5000", "--max-rate", "10000", "--open"]

[presets.curl]
fast_content = ["-s", "--max-time", "15", "--connect-timeout", "5"]
```

### Template Development

Build new security tool integrations with minimal effort:

1. Define preset in `configs/presets.toml`
2. Create JSON template referencing preset
3. Test with `python ipcrawler.py validate`
4. Deploy immediately - no code changes required

## Community

### Join Our Discord

Connect with security professionals and ipcrawler contributors in our community Discord server:

**[Join the ipcrawler Discord](https://discord.com/invite/ua2hRhWkSq)**

Share templates, get support, discuss security topics, and collaborate on new features with fellow practitioners.

### Contributing

We welcome contributions from the security community:

- **Template Submissions** - Add new security tools and configurations
- **Feature Requests** - Suggest improvements and new capabilities
- **Bug Reports** - Help us improve stability and performance
- **Documentation** - Enhance guides and examples

## Architecture

```
ipcrawler/
├── cli/              # Command-line interface
├── core/             # Core business logic
├── models/           # Data models and validation
├── security/         # Security and validation layer
├── ui/               # Rich TUI components
└── utils/            # Utility functions
```

## Dependencies

- **Python 3.8+** - Modern Python runtime
- **Rich** - Advanced terminal user interfaces
- **Pydantic** - Data validation and settings management
- **asyncio** - Concurrent execution framework

### External Security Tools

ipcrawler orchestrates popular security tools:
- nmap, curl, dig, openssl
- feroxbuster, gobuster, nuclei
- Custom tools via JSON templates

## License

Open Source - Built for the security community

## Support

- **Documentation** - Comprehensive guides in `CLAUDE.md`
- **Discord Community** - Real-time support and discussions
- **GitHub Issues** - Bug reports and feature requests

---

**Built by security professionals, for security professionals**

*ipcrawler combines the power of modern development practices with the practical needs of security testing, delivering a framework that scales from individual assessments to enterprise security operations.*