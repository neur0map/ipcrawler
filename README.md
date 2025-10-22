# IPCrawler

Professional automated penetration testing framework for parallel security tool execution with intelligent privilege management and comprehensive reporting.

A [prowl.sh](https://prowl.sh) project - comprehensive IP reconnaissance and network scanning tool.

## Quick Start

```bash
# Basic scan
ipcrawler -t 192.168.1.1 -p 80,443

# Network range with common ports
ipcrawler -t 192.168.1.0/24 -p common

# Fast port scan (top 100 ports)
ipcrawler -t 10.0.0.1 -p fast

# Advanced scan with sudo
sudo ipcrawler -t 192.168.1.1 -p top-1000 -w big
```

## Key Features

- **YAML-Driven Architecture** - Fully extensible, zero hardcoded tool logic
- **Parallel Execution** - Run up to 5 tools concurrently with intelligent queueing
- **Sudo Detection** - Automatically selects privileged commands when running with sudo
- **Script Security** - Built-in validation and sandboxing for custom shell scripts
- **Wordlist Management** - Centralized configuration with predefined SecLists paths
- **Advanced Port Modes** - Support for nmap scripts (fast, top-1000, top-10000, all)
- **Modern Terminal UI** - Real-time progress tracking with live vulnerability feed
- **Comprehensive Reporting** - Markdown and JSON reports with individual tool logs

## Installation

### Prerequisites

- Rust 1.70+ ([install from rustup.rs](https://rustup.rs))
- Package manager: apt, yum, dnf, brew, pacman, or zypper
- SecLists wordlists (recommended): `/usr/share/seclists`

### Build from Source

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make build
```

Binary location: `target/release/ipcrawler`

### Install Security Tools

IPCrawler can auto-install missing tools, or install manually:

```bash
# Arch Linux
sudo pacman -S nmap nikto gobuster sqlmap sslscan masscan whatweb dnsenum

# Debian/Ubuntu
sudo apt install nmap nikto gobuster sqlmap sslscan masscan whatweb dnsenum

# macOS
brew install nmap nikto gobuster sqlmap sslscan masscan whatweb dnsenum
```

## Usage

### Command Line

```
ipcrawler -t <TARGET> -p <PORTS> [OPTIONS]

Required:
  -t, --target <TARGET>        IP, CIDR, or file path
  -p, --ports <PORTS>          Port list, range, or mode

Options:
  -w, --wordlist <NAME/PATH>   Wordlist name or custom path (default: common)
  -o, --output <DIR>           Output directory
  --install                    Auto-install missing tools
  --tools-dir <PATH>           Tools directory (default: tools)
```

### Port Modes

| Mode | Description |
|------|-------------|
| `fast` | Top 100 ports (nmap -F) |
| `common` | 15 most common ports |
| `top-1000` | Top 1000 ports |
| `top-10000` | Top 10000 ports |
| `all` | All 65535 ports |
| `1-1000` | Port range |
| `22,80,443` | Port list |

### Target Formats

```bash
# Single IP
ipcrawler -t 192.168.1.1 -p 80

# CIDR range
ipcrawler -t 192.168.1.0/24 -p common

# File-based targets
echo "192.168.1.1" > targets.txt
echo "10.0.0.0/24" >> targets.txt
ipcrawler -t targets.txt -p fast
```

### Wordlist Options

```bash
# Predefined wordlists
ipcrawler -t 192.168.1.1 -p 80 -w common
ipcrawler -t 192.168.1.1 -p 80 -w big

# Custom wordlist
ipcrawler -t 192.168.1.1 -p 80 -w /path/to/wordlist.txt
```

Available: `common`, `big`, `medium`, `small`, `subdomains`, `api`, `backups`

## Supported Tools

### Network Reconnaissance
- **nmap** - Port scanner and service detection
- **masscan** - Ultra-fast TCP port scanner (requires sudo)
- **ping** - ICMP connectivity testing
- **traceroute** - Network path discovery

### DNS Enumeration
- **dig** - DNS query and lookup
- **host** - Simple DNS lookup
- **whois** - Domain/IP registration
- **dnsenum** - DNS enumeration and subdomain discovery

### Web Application Testing
- **nikto** - Web server vulnerability scanner
- **gobuster** - Directory and file bruteforcer
- **whatweb** - Web technology fingerprinting
- **sqlmap** - SQL injection testing
- **sslscan** - SSL/TLS configuration scanner

See [Tool Documentation](docs/TOOLS.md) for detailed information.

## Configuration

### Adding Custom Tools

Create `tools/custom.yaml`:

```yaml
name: "custom-scanner"
description: "My custom scanner"
command: "scanner {{target}} -p {{port}} -o {{output_file}}"
sudo_command: "scanner {{target}} -p {{port}} --privileged -o {{output_file}}"
installer:
  apt: "apt install -y scanner"
  pacman: "pacman -S --noconfirm scanner"
timeout: 300
output:
  type: "json"
  patterns:
    - name: "finding"
      regex: "VULN: (.+)"
      severity: "high"
```

### Custom Shell Scripts

Create `tools/scripts/custom.sh`:

```bash
#!/bin/bash
TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

echo "Scanning $TARGET:$PORT" > "$OUTPUT_FILE"
nmap -sV "$TARGET" -p "$PORT" >> "$OUTPUT_FILE"
```

Reference in YAML:

```yaml
name: "custom-script"
command: "custom.sh {{target}} {{port}} {{output_file}}"
```

IPCrawler automatically validates and makes scripts executable.

See [Configuration Guide](docs/CONFIGURATION.md) for details.

## Security

IPCrawler implements comprehensive security for custom scripts:

- **Dangerous Commands Blocked** - Prevents disk wipes, system shutdowns, privilege escalation
- **Suspicious Patterns Warned** - Detects obfuscation, network backdoors, code execution
- **Script Size Limits** - Maximum 1MB per script
- **Automatic Validation** - All scripts scanned before execution
- **Privilege Management** - Explicit sudo detection, no automatic escalation

See [Security Documentation](docs/SECURITY.md) for complete details.

## Output Structure

```
ipcrawler-results/YYYYMMDD_HHMMSS/
├── report.md           # Markdown summary
├── results.json        # Machine-readable results
└── logs/              # Individual tool outputs
```

## Documentation

- [Configuration Guide](docs/CONFIGURATION.md) - Custom tools, scripts, wordlists
- [Security Guide](docs/SECURITY.md) - Security features, sudo usage, validation
- [Tool Reference](docs/TOOLS.md) - Complete tool list and specifications
- [Architecture](docs/ARCHITECTURE.md) - System design and implementation
- [Development](docs/DEVELOPMENT.md) - Contributing, building, testing
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## Example Workflows

### Basic Web Application Scan
```bash
ipcrawler -t webapp.example.com -p 80,443 -w big
```

### Full Network Discovery
```bash
sudo ipcrawler -t 192.168.1.0/24 -p top-1000
```

### Targeted Vulnerability Assessment
```bash
ipcrawler -t targets.txt -p common -w medium
```

### Custom Script Integration
```bash
# Create custom script
cat > tools/scripts/banner-grab.sh << 'EOF'
#!/bin/bash
timeout 5 nc -v "$1" "$2" 2>&1 > "$3"
EOF

# Define tool YAML
cat > tools/banner-grab.yaml << 'EOF'
name: "banner-grab"
description: "TCP banner grabbing"
command: "banner-grab.sh {{target}} {{port}} {{output_file}}"
timeout: 30
output:
  type: "regex"
  patterns:
    - name: "banner"
      regex: "(.+)"
      severity: "info"
EOF

# Run scan
ipcrawler -t 192.168.1.1 -p 22,80,443
```

## Development

```bash
# Build
cargo build

# Test
cargo test

# Lint
cargo clippy

# Format
cargo fmt

# Run
cargo run -- -t 192.168.1.1 -p 80
```

See [Development Guide](docs/DEVELOPMENT.md) for details.

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Priority areas:
- Additional tool definitions
- Enhanced output parsers
- UI improvements
- Security enhancements
- Documentation updates

## Legal Notice

IPCrawler is designed for authorized security testing only:
- Penetration testing engagements
- Security research
- CTF competitions
- Educational purposes
- Defensive security operations

**Do not use for unauthorized scanning or malicious activities.**

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) file for details.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Acknowledgments

Built with Rust for performance and safety. Integrates industry-standard security tools. Inspired by professional penetration testing workflows.

---

**IPCrawler** is part of the [prowl.sh](https://prowl.sh) ecosystem of professional security tools.

Maintained by [neur0map](mailto:neur0map@prowl.sh)
