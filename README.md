# IPCrawler

**Modern penetration testing scanner with AI-powered output parsing**

IPCrawler runs multiple security tools concurrently and uses LLMs to parse outputs into structured data—no regex patterns, no hardcoded parsers. Add new tools through YAML templates without touching code.

```bash
# One command to scan, parse, and report
ipcrawler 192.168.1.1 -o ./scan
```

---

## Key Features

**AI-Powered Parsing**  
Convert any tool output to structured JSON using OpenAI, Groq, Anthropic, or Ollama

**Concurrent Execution**  
Tokio-based async architecture with automatic pre-scan phase and sudo detection

**Template System**  
YAML-based tool configuration—add tools without code changes

**Multiple Output Formats**  
Terminal, HTML, Markdown, and JSON reports

**Smart Consistency**  
Multi-pass parsing with union merge strategy ensures no findings are missed

---

## Installation

### Quick Install

```bash
# Stable release
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash

# Latest unstable build
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash -s -- --unstable
```

### Build from Source

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
cargo build --release
sudo mv target/release/ipcrawler /usr/local/bin/
```

---

## Quick Start

```bash
# 1. Configure LLM provider (one-time)
ipcrawler setup

# 2. Run scan
ipcrawler example.com -o ./scan

# 3. View results
open ./scan/report.html
```

---

## Usage

### Basic Commands

```bash
# Basic scan
ipcrawler <target> -o <output_dir>

# Scan with verbose logging
ipcrawler <target> -o <output_dir> -v

# Enhanced scan with sudo (uses privileged templates)
sudo ipcrawler <target> -o <output_dir>

# Skip LLM parsing (raw outputs only)
ipcrawler <target> -o <output_dir> --no-parse
```

### Port Scanning

```bash
# Default: nmap's top 1000 ports
ipcrawler <target> -o <output>

# Specific ports
ipcrawler <target> -p 22,80,443 -o <output>

# Port ranges
ipcrawler <target> -p 1-1000 -o <output>

# Mixed syntax
ipcrawler <target> -p 22,80,100-200,443,8000-9000 -o <output>
```

### Wordlists

```bash
# Default: 'common' wordlist (SecLists)
ipcrawler <target> -o <output>

# Named wordlist
ipcrawler <target> -w medium -o <output>
ipcrawler <target> -w big -o <output>
ipcrawler <target> -w raft-small -o <output>

# Custom file
ipcrawler <target> -w /path/to/wordlist.txt -o <output>

# List available wordlists
ipcrawler wordlists
```

### Templates

```bash
# List all templates
ipcrawler list

# Show template details
ipcrawler show nmap
```

### Configuration

```bash
# Interactive setup wizard
ipcrawler setup

# View current config
ipcrawler config

# Override provider for single scan
ipcrawler <target> -o <output> --llm-provider openai
```

---

## Configuration

### LLM Providers

Get API keys from:
- **Groq** (recommended, fast, free tier): https://console.groq.com
- **OpenAI**: https://platform.openai.com
- **Anthropic**: https://console.anthropic.com
- **Ollama** (local, free): https://ollama.ai

Configure via `ipcrawler setup` or set environment variables:

```bash
export LLM_PROVIDER="groq"
export LLM_API_KEY="your-key-here"
```

### File Locations

```
~/.config/ipcrawler/config.toml    # Configuration (0600 permissions)
./templates/                       # YAML tool templates
./templates/wordlists.toml         # Wordlist definitions
```

---

## Output Structure

```
scan_output/
├── raw/              # Raw tool outputs (nmap/, nikto/, etc.)
├── entities.json     # Extracted entities (IPs, ports, URLs, etc.)
├── report.json       # Full structured report
├── report.html       # Interactive HTML report
└── report.md         # Markdown documentation
```

---

## How It Works

### Execution Flow

```
1. Pre-Scan Phase
   └─ Templates with pre_scan: true run first
   └─ Discovers hostnames, DNS records, open ports
   └─ Updates /etc/hosts (if sudo)

2. Main Scan Phase
   └─ All enabled templates run concurrently
   └─ Raw outputs saved to ./raw/

3. AI Parsing Phase
   └─ Multiple consistency passes per tool
   └─ LLM converts text → structured JSON
   └─ Union merge strategy (include all findings)
   └─ Schema validation

4. Report Generation
   └─ Terminal output (immediate)
   └─ HTML report (interactive)
   └─ Markdown report (documentation)
   └─ JSON report (automation)
```

### AI Parsing Details

The LLM performs **only text-to-JSON conversion**—no analysis, no recommendations, just data extraction.

**Multi-Pass Consistency:**
- Default 3 passes per tool output
- Union merge: include findings from ANY pass
- Consistency scoring alerts on variations
- Configurable via `--consistency-passes 1-5`

**Example:**
```
Input:  "22/tcp open ssh OpenSSH 8.2"
Output: {"ports": [{"port": 22, "service": "ssh", "version": "OpenSSH 8.2"}]}
```

---

## Template System

Add new tools through YAML templates—no code changes required.

### Basic Template

```yaml
name: nmap
description: Fast port scan
enabled: true
command:
  binary: nmap
  args: ["-sT", "-T4", "-p", "{{ports}}", "{{target}}"]
timeout: 600
requires_sudo: false
```

### Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{target}}` | Scan target | `192.168.1.1`, `example.com` |
| `{{output_dir}}` | Tool output directory | `./scan/raw/nmap` |
| `{{ports}}` | Port specification | `-p 80,443` or `--top-ports 1000` |
| `{{wordlist}}` | Wordlist file path | `/usr/share/seclists/...` |

### Included Templates

**Pre-Scan:**
- `dig` - Comprehensive DNS reconnaissance
- `hostname-discovery` - Extract hostnames from SSL/HTTP
- `reverse-dns` - PTR record lookups

**Main Scan:**
- `ping` - Connectivity check
- `nmap` / `nmap-sudo` - Port scanning
- `nikto` - Web server scanner
- `whatweb` - Web technology detection
- `gobuster` - Directory/file brute-forcing

For complete template documentation, see [templates/README.md](templates/README.md).

---

## Example Output

```
============================================================
Scan Results for example.com
============================================================

[IP Addresses]
  1. 93.184.216.34

[Open Ports]
  80 (tcp)  http nginx
  443 (tcp)  ssl/http nginx

[URLs]
  http://example.com
  https://example.com

[No vulnerabilities detected]

============================================================
[Scan Summary]
============================================================

  Target: example.com | Duration: 23s | Tools: 4/4

  Discovered: 1 IPs, 2 Domains, 2 URLs, 2 Open Ports, 0 Vulnerabilities

[Scan completed successfully]

Output Files:
  - ./scan/entities.json
  - ./scan/report.json
  - ./scan/report.html
  - ./scan/report.md
  - ./scan/raw/
```

---

## Security

- Config stored with `0600` permissions
- API keys masked in output
- Hidden password-style input during setup
- No credentials in logs or reports

---

## Documentation

- [Template Guide](templates/README.md) - Complete template system documentation
- [Contributing Guide](CONTRIBUTING.md) - Development guidelines and contribution instructions
- [Release Notes](RELEASE.md) - Version history and changelog

---

## Development

```bash
# Build
cargo build --release

# Run with debug logging
cargo run -- <target> -o ./scan -v

# Run tests
cargo test --all-features

# Format and lint
cargo fmt
cargo clippy
```

---

## Troubleshooting

**TTY Warning During Setup**

Build the release binary first:
```bash
cargo build --release
./target/release/ipcrawler setup
```

**Auto-Generated Output Directories**

If no `-o` flag is provided, output is saved to `./ipcrawler_<target>_<timestamp>`.

**Wordlist Not Found**

Install SecLists (recommended for Kali/HTB):
```bash
sudo apt install seclists
```

Or use direct file path:
```bash
ipcrawler <target> -w /path/to/wordlist.txt
```

---

## License

MIT License - see [LICENSE](LICENSE) for details

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick contribution areas:**
- Add new tool templates (no code required)
- Improve HTML report styling
- Add wordlist configurations
- Enhance documentation

---

**Built with Rust and powered by AI**
