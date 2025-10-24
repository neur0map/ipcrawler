# IPCrawler

Professional automated penetration testing framework with AI-powered security analysis, parallel tool execution, and comprehensive reporting.

A [prowl.sh](https://prowl.sh) project - intelligent IP reconnaissance and network scanning platform.

## NOTE: LLM are only used for parsing and creating the end report.md, it does not provide any help further than that.
## Quick Start

```bash
# Basic scan
ipcrawler -t 192.168.1.1 -p 80,443

# AI-powered security analysis
ipcrawler -t 192.168.1.1 -p 80,443 --use-llm

# Network range with LLM analysis
ipcrawler -t 192.168.1.0/24 -p common --use-llm --llm-provider openai

# Fast port scan with local AI (Ollama)
ipcrawler -t 10.0.0.1 -p fast --use-llm --llm-provider ollama

# Advanced scan with sudo and AI
sudo ipcrawler -t 192.168.1.1 -p top-1000 -w big --use-llm --llm-provider claude

# Dry-run to test parsing
ipcrawler -t 192.168.1.1 -p 80 --dry-run
```

## Key Features

### [AI] AI-Powered Analysis
- **LLM Integration** - Support for OpenAI, Claude, and Ollama
- **Security-Focused Prompts** - Specialized analysis for different tool types
- **Universal Output Parser** - Intelligent parsing with context awareness
- **Enhanced Reporting** - AI-generated insights and recommendations

### [⚡] Performance & Architecture
- **YAML-Driven Architecture** - Fully extensible, zero hardcoded tool logic
- **Parallel Execution** - Run up to 5 tools concurrently with intelligent queueing
- **Sudo Detection** - Automatically selects privileged commands when running with sudo
- **Script Security** - Built-in validation and sandboxing for custom shell scripts

### [⚙] Configuration & Modes
- **Wordlist Management** - Centralized configuration with predefined SecLists paths
- **Advanced Port Modes** - Support for nmap scripts (fast, top-1000, top-10000, all)
- **Dry-Run Mode** - Test parsing without executing tools
- **Verbose Mode** - Detailed output with alternative parsing methods

### [✓] User Experience
- **Modern Terminal UI** - Real-time progress tracking with live vulnerability feed
- **Comprehensive Reporting** - Enhanced Markdown and JSON reports with AI insights
- **Smart Folder Naming** - Results organized as `TARGET_HHMM` for easy identification
- **Environment Support** - `.env` file configuration for API keys and settings

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

### Comprehensive Multi-Phase Tools (JSON Output)
- **nmap_comprehensive** - Advanced multi-phase port scanning
  - Phase 1: Fast SYN scan for port discovery
  - Phase 2: Service and version detection
  - Phase 3: OS detection and aggressive scans (sudo)
  - Intelligent severity assignment (HIGH for insecure protocols)

- **httpx_enumeration** - Complete HTTP(S) reconnaissance
  - Technology detection and fingerprinting
  - Security headers analysis (CSP, HSTS, X-Frame-Options)
  - TLS certificate validation with expiry warnings
  - Discovery file detection (robots.txt, sitemap.xml)

- **dig** - Comprehensive DNS reconnaissance
  - 17 DNS record types (A, AAAA, MX, NS, TXT, SOA, CNAME, etc.)
  - Subdomain enumeration (15 common subdomains)
  - Zone transfer attempts with security flagging
  - DNSSEC validation and DNS tracing

### Network Analysis Tools
- **traceroute** - Network path discovery and hop analysis
- **whois** - Domain and IP registration information

### Tool Architecture
All tools automatically discovered from `tools/` directory - **no configuration needed**.
Each tool outputs structured JSON findings + raw output for comprehensive analysis.

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

### Custom Shell Scripts with JSON Output

Create `tools/scripts/custom.sh`:

```bash
#!/bin/bash
TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

# Initialize findings array
findings_json="[]"

# Output raw tool execution to stderr (for logs and LLM)
echo "===START_RAW_OUTPUT===" >&2
echo "Scanning $TARGET:$PORT" >&2

# Run your tool
result=$(nmap -sV "$TARGET" -p "$PORT" 2>&1)
echo "$result" >&2

# Parse findings and build JSON
if echo "$result" | grep -q "open"; then
  finding=$(cat <<EOF
{
  "severity": "info",
  "title": "Open port detected",
  "description": "Port $PORT is open on $TARGET",
  "port": $PORT
}
EOF
)
  findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new')
fi

echo "===END_RAW_OUTPUT===" >&2

# Output JSON findings to stdout
cat <<EOF
{
  "findings": $findings_json,
  "metadata": {
    "scan_type": "custom_scan",
    "target": "$TARGET",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
```

Reference in YAML with JSON output type:

```yaml
name: "custom-script"
command: "custom.sh {{target}} {{port}} {{output_file}}"
timeout: 60
output:
  type: "json"  # Enable JSON parsing
```

**Key Features:**
- JSON findings parsed automatically into structured reports
- Raw output between markers sent to LLM for analysis
- Full output preserved in logs/ directory
- IPCrawler validates and makes scripts executable

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
ipcrawler-results/TARGET_HHMM/
├── report.md                              # Structured Markdown report with findings
│                                          # - Grouped by tool and severity
│                                          # - LLM analysis sections (if enabled)
│                                          # - Host summaries with key findings
│
├── results.json                           # Machine-readable JSON data
│                                          # - All findings with metadata
│                                          # - Task execution status
│
└── logs/                                  # Full tool outputs for each execution
    ├── nmap_comprehensive_target_22,80,443.log
    ├── httpx_enumeration_target_80.log
    ├── dig_target_none.log
    ├── traceroute_target_none.log
    └── whois_target_none.log
```

**Output Features:**
- **Structured findings** - JSON-parsed results in report.md
- **Raw preservation** - Complete tool outputs in logs/
- **LLM analysis** - AI insights when `--use-llm` enabled
- **Deduplication** - Automatic removal of duplicate findings

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

### Custom Script Integration with JSON
```bash
# Create custom banner-grabbing script
cat > tools/scripts/banner-grab.sh << 'EOF'
#!/bin/bash
TARGET="$1"
PORT="$2"

findings_json="[]"

echo "===START_RAW_OUTPUT===" >&2
echo "Grabbing banner from $TARGET:$PORT" >&2

# Grab banner
banner=$(timeout 5 nc -v "$TARGET" "$PORT" 2>&1)
echo "$banner" >&2
echo "===END_RAW_OUTPUT===" >&2

# Parse banner and create finding
if [ -n "$banner" ]; then
  finding=$(cat <<EOFINDING
{
  "severity": "info",
  "title": "Banner grabbed",
  "description": "TCP banner: $banner",
  "port": $PORT
}
EOFINDING
)
  findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new')
fi

# Output JSON
cat <<EOFINAL
{
  "findings": $findings_json,
  "metadata": {
    "scan_type": "banner_grab",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOFINAL
EOF

# Define tool YAML
cat > tools/banner-grab.yaml << 'EOF'
name: "banner-grab"
description: "TCP banner grabbing with JSON output"
command: "banner-grab.sh {{target}} {{port}}"
timeout: 30
output:
  type: "json"
installer:
  apt: "apt install -y netcat jq"
  pacman: "pacman -S --noconfirm gnu-netcat jq"
EOF

chmod +x tools/scripts/banner-grab.sh

# Run scan - automatically includes banner-grab tool
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
