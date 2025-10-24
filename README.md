<div align="center">

# IPCrawler

**Automated reconnaissance framework for penetration testing**

*Parallel tool execution • JSON output • Extensible architecture*

[![prowl.sh](https://img.shields.io/badge/prowl-sh-blue)](https://prowl.sh)

</div>

---

## Quick Start

```bash
# Basic scan
ipcrawler -t 192.168.1.1 -p 80,443

# Network range scan
sudo ipcrawler -t 192.168.1.0/24 -p common

# Comprehensive scan with wordlist
sudo ipcrawler -t target.com -p top-1000 -w big

# Optional: Enhanced reports with LLM analysis
ipcrawler -t 192.168.1.1 -p 80,443 --use-llm --llm-provider ollama
```

## Core Features

**🔍 Reconnaissance Tools**
- Multi-phase port scanning (nmap)
- HTTP(S) enumeration and security analysis
- DNS reconnaissance with zone transfer detection
- Network path discovery and whois lookups

**⚡ Performance**
- Parallel execution (up to 5 tools concurrently)
- Automatic tool discovery from YAML configs
- Privilege escalation detection (sudo/root)
- Smart timeout and retry handling

**📊 Output**
- Structured JSON findings
- Markdown reports with severity grouping
- Complete raw logs preserved
- Optional LLM-enhanced analysis for reports

**🔧 Extensibility**
- YAML-driven tool configuration
- Custom shell script support
- Zero hardcoded tool logic
- Built-in script security validation

## Installation

### Build from Source

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make build
cargo install --path .
```

**Requirements:**
- Rust 1.70+ ([rustup.rs](https://rustup.rs))
- Tools auto-installed on first run (or manual install)

## Included Tools

**Network Scanning:**
- `nmap_comprehensive` - Multi-phase port scanning with service detection
- `traceroute` - Network path analysis

**HTTP Analysis:**
- `httpx_enumeration` - Security headers, TLS certs, technology detection

**DNS Reconnaissance:**
- `dig` - 17 DNS record types, subdomain enum, zone transfers

**Information Gathering:**
- `whois` - Domain registration and ownership

See [Tool Documentation](docs/TOOLS.md) for complete details.

## Usage

### Basic Scans

```bash
# Single target
ipcrawler -t 192.168.1.1 -p 80,443

# CIDR range
ipcrawler -t 192.168.1.0/24 -p common

# Multiple targets from file
ipcrawler -t targets.txt -p fast
```

### Port Modes

| Mode | Description |
|------|-------------|
| `common` | 15 most common ports |
| `fast` | Top 100 ports (nmap -F) |
| `top-1000` | Top 1000 ports |
| `all` | All 65535 ports |
| `22,80,443` | Custom port list |
| `1-1000` | Port range |

### Advanced Options

```bash
# With custom wordlist
ipcrawler -t example.com -p 80 -w /path/to/wordlist.txt

# Output directory
ipcrawler -t target.com -p common -o /tmp/scan-results

# Tools directory (custom tools)
ipcrawler -t target.com -p 80 --tools-dir ./custom-tools
```

## Output Structure

```
ipcrawler-results/TARGET_HHMM/
├── report.md           # Structured findings by tool and severity
├── results.json        # Machine-readable JSON output
└── logs/               # Full raw output from each tool
    ├── nmap_comprehensive_target_ports.log
    ├── httpx_enumeration_target_port.log
    └── dig_target_none.log
```

## Adding Custom Tools

Create `tools/custom.yaml`:

```yaml
name: "banner-grab"
description: "TCP banner grabbing"
command: "banner-grab.sh {{target}} {{port}}"
timeout: 60
installer:
  apt: "apt install -y netcat jq"
output:
  type: "json"
```

Create `tools/scripts/banner-grab.sh`:

```bash
#!/bin/bash
TARGET="$1"
PORT="$2"

findings_json="[]"

echo "===START_RAW_OUTPUT===" >&2
banner=$(timeout 5 nc -v "$TARGET" "$PORT" 2>&1)
echo "$banner" >&2
echo "===END_RAW_OUTPUT===" >&2

if [ -n "$banner" ]; then
  finding=$(cat <<EOF
{"severity": "info", "title": "Banner grabbed", "description": "Banner: $banner", "port": $PORT}
EOF
)
  findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new')
fi

cat <<EOF
{"findings": $findings_json}
EOF
```

**Tool auto-discovered on next run.**

See [Configuration Guide](docs/CONFIGURATION.md) for complete examples.

## Optional: LLM Enhancement

LLM integration is **optional** and only enhances report generation with AI analysis of raw tool output.

```bash
# Setup (one-time)
echo 'OPENAI_API_KEY=your_key' > .env

# Run with LLM report enhancement
ipcrawler -t target.com -p 80 --use-llm --llm-provider openai

# Use local LLM (Ollama)
ipcrawler -t target.com -p 80 --use-llm --llm-provider ollama
```

**Supported providers:** OpenAI, Claude, Ollama (local)

LLM analyzes raw output and adds insights to `report.md`. Core scanning functionality works identically with or without LLM.

## Documentation

- **[Configuration Guide](docs/CONFIGURATION.md)** - Custom tools, JSON format, wordlists
- **[Tool Reference](docs/TOOLS.md)** - Complete tool specifications
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow
- **[Security](docs/SECURITY.md)** - Script validation and sudo usage
- **[Development](docs/DEVELOPMENT.md)** - Contributing and building

## Development

```bash
# Build
cargo build

# Test
cargo test

# Quality checks
make check

# Format
make fmt
```

## Legal Notice

**For authorized security testing only:**
- Penetration testing with permission
- Security research and CTF competitions
- Defensive security operations
- Educational purposes

**Do not use for unauthorized scanning.**

## License

Apache License 2.0 - See [LICENSE](LICENSE) file.

---

<div align="center">

**IPCrawler** is part of the [prowl.sh](https://prowl.sh) security tools ecosystem

Maintained by [neur0map](mailto:neur0map@prowl.sh)

</div>
