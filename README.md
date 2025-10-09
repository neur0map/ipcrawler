# IPCrawler

Intelligent automated penetration testing scanner with LLM-powered output parsing. Run multiple security tools concurrently, parse outputs with AI, and get structured reports without hardcoded regex patterns.

## Features

- **AI-Powered Parsing** - Converts tool outputs to structured JSON using LLMs (no regex)
- **Concurrent Execution** - Tokio-based async tool execution with automatic sudo detection
- **Multiple Output Formats** - Terminal, HTML, Markdown, and JSON reports
- **4 LLM Providers** - OpenAI, Groq, Anthropic, Ollama support
- **YAML Template System** - Easy tool configuration and extensibility
- **Secure Configuration** - Store API keys with 0600 file permissions

## Installation

### Quick Install (Stable)

```bash
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash
```

### Unstable Build (Latest)

```bash
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash -s -- --unstable
```

### Install Options

```bash
# Install specific version
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash -s -- --version v1.0.0

# Install to custom directory
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash -s -- --dir /usr/local/bin

# Force reinstall
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash -s -- --force
```

### Build from Source

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
cargo build --release
# Binary at target/release/ipcrawler
```

## Quick Start

```bash
# 1. Configure API keys (one-time setup)
ipcrawler setup

# 2. Run a scan
ipcrawler 192.168.1.1 -o ./scan

# 3. View results
# - Terminal output displays immediately
# - Open ./scan/report.html in browser
# - Read ./scan/report.md for documentation
```

## Configuration

### Interactive Setup

```bash
ipcrawler setup
```

The setup wizard configures:
- LLM provider (Groq, OpenAI, Anthropic, Ollama)
- API key (hidden input)
- Default settings (templates directory, verbose mode)

Configuration is stored at `~/.config/ipcrawler/config.toml` with secure permissions (0600).

### View Configuration

```bash
ipcrawler config
```

### Override Configuration

```bash
# Override provider
ipcrawler <target> -o ./scan --llm-provider openai

# Override via environment
export LLM_API_KEY="your-key"
ipcrawler <target> -o ./scan
```

## Usage

```bash
# Basic scan
ipcrawler <target> -o <output_dir>

# Scan with verbose output
ipcrawler <target> -o <output_dir> -v

# Scan specific ports (default: --top-ports 1000 if not specified)
ipcrawler <target> -p 22,80,443
ipcrawler <target> -p 1-1000
ipcrawler <target> -p 22,80,100-200,443,8000-9000
ipcrawler <target>  # Uses nmap's top 1000 most common ports

# Use custom wordlist (default: common if not specified)
ipcrawler <target> -w medium              # Use 'medium' wordlist from config
ipcrawler <target> -w big                 # Use 'big' wordlist
ipcrawler <target> -w /path/to/custom.txt # Use custom file path
ipcrawler <target>                        # Uses 'common' wordlist by default

# Sudo for enhanced scans (uses privileged templates)
sudo ipcrawler <target> -o <output_dir>

# Skip LLM parsing
ipcrawler <target> -o <output_dir> --no-parse

# Increase consistency passes (more reliable, slower)
ipcrawler <target> -o <output_dir> --consistency-passes 5

# Fast single-pass parsing (faster, less reliable)
ipcrawler <target> -o <output_dir> --consistency-passes 1

# List available templates
ipcrawler list

# Show template details
ipcrawler show nmap

# List available wordlists
ipcrawler wordlists
```

## LLM Configuration

The LLM is used solely for parsing tool outputs into structured JSON. Configure via `ipcrawler setup`:

- **Groq** - Fast, free tier (recommended) - https://console.groq.com
- **OpenAI** - Reliable - https://platform.openai.com
- **Anthropic** - High quality - https://console.anthropic.com  
- **Ollama** - Local, free - https://ollama.ai

## Output Structure

```
scan_output/
├── raw/            # Raw tool outputs (nmap/, nikto/, etc.)
├── entities.json   # Extracted data (JSON)
├── report.json     # Full report (JSON)
├── report.html     # HTML report (open in browser)
└── report.md       # Markdown report (for docs)
```

Output formats: Terminal (immediate), HTML (web report), Markdown (docs), JSON (automation)

## Template System

YAML-based templates define tool execution, arguments, timeouts, and dependencies. Customize tool behavior without code changes.

### Pre-Scan Phase

IPCrawler automatically runs a **pre-scan phase** before the main scan to discover hostnames associated with the target IP. This ensures tools like `gobuster` and `feroxbuster` get better results by using hostnames instead of IPs.

**How it works:**
1. Pre-scan templates (marked with `pre_scan: true`) run first
2. Hostnames are extracted from SSL certificates, HTTP headers, and reverse DNS
3. Discovered hostnames are added to `/etc/hosts` (requires sudo)
4. Main scan templates automatically benefit from hostname discovery

**Included Pre-Scan Templates:**
- `dig` - Comprehensive DNS reconnaissance with advanced techniques:
  - All record types (A, AAAA, MX, TXT, NS, SOA, CAA, DNSSEC, SRV)
  - Zone transfer attempts (AXFR)
  - Subdomain enumeration (40+ common subdomains)
  - Service discovery (SRV records for LDAP, Kerberos, XMPP, SIP, etc.)
  - Wildcard detection
  - Email security records (SPF, DMARC, DKIM)
  - Internal IP leakage detection (RFC1918 addresses)
  - Queries authoritative nameservers directly
- `hostname-discovery` - Uses nmap scripts to extract hostnames from SSL certs and HTTP headers
- `reverse-dns` - Quick reverse DNS lookup (PTR records)

Example template:

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

**Template Variables:**
- `{{target}}` - Scan target (IP, domain, or URL)
- `{{output_dir}}` - Output directory for this tool
- `{{ports}}` - Port specification: `--top-ports 1000` (default) or `-p <custom>` from flag
- `{{wordlist}}` - Wordlist path: resolved from `-w` flag or default `common` wordlist

**Port Behavior:**
- No `-p` flag: Uses `--top-ports 1000` (nmap's 1000 most common ports)
- With `-p`: Uses custom specification like `-p 22,80,443` or `-p 1-1000`
- Generic: Works with any port scanner (nmap, naabu, rustscan) via `{{ports}}` variable

**Wordlist Behavior:**
- No `-w` flag: Uses `common` wordlist (configured in `templates/wordlists.toml`)
- With `-w <name>`: Uses named wordlist from configuration (e.g., `medium`, `big`, `raft-small`)
- With `-w /path`: Uses direct file path
- Generic: Works with any brute-forcing tool (gobuster, ffuf, wfuzz) via `{{wordlist}}` variable
- Run `ipcrawler wordlists` to see available wordlists and their status

**Sudo Detection:** Create two variants (`tool.yaml` and `tool-sudo.yaml`). IPCrawler auto-selects based on privileges.

**Included Templates:** 
- Pre-scan: dig, hostname-discovery, reverse-dns
- Main scan: ping, nmap, nmap-sudo, nikto, whatweb, gobuster

**Pre-Scan Templates:** Set `pre_scan: true` to run a template before the main scan phase. Useful for hostname discovery, port discovery, or any reconnaissance that benefits subsequent tools.

**Example Usage:**
```bash
# Run with sudo to automatically update /etc/hosts with discovered hostnames
sudo ipcrawler <target-ip> -o <output>

# Without sudo - hostnames will be discovered but not added to /etc/hosts
ipcrawler <target-ip> -o <output>
```

When hostnames are discovered and added to `/etc/hosts`, subsequent tools (like gobuster, feroxbuster, nikto) will automatically use the hostname, resulting in better scan results.

See [templates/README.md](templates/README.md) for complete documentation.

## How AI Parsing Works

**Data Flow:** Tools execute → Raw text → LLM parses (multiple passes) → Validated JSON → Reports

The LLM performs only text-to-JSON conversion. It does NOT analyze vulnerabilities, make security decisions, or provide recommendations. Just data extraction.

Example:
```
Input:  "22/tcp open ssh OpenSSH 8.2"
Output: {"ports": [{"port": 22, "service": "ssh", "version": "OpenSSH 8.2"}]}
```

### Consistency Pipeline

Since LLMs are non-deterministic, IPCrawler runs multiple parsing passes (default: 3) to ensure consistent results:

1. **Multi-pass parsing** - Parse each tool output multiple times
2. **Union merge strategy** - Include findings from ANY pass (safer for security)
3. **Consistency scoring** - Calculate similarity between passes
4. **Validation** - Schema validation on all outputs
5. **Warnings** - Alert on low consistency or variations

**Why this matters:**
- Prevents missing critical vulnerabilities
- Detects when LLM is being inconsistent
- No tool-specific hardcoded logic needed
- Configurable via `--consistency-passes` (1-5)

**Benefits:**
- Adapts to any tool's output format
- No regex patterns to maintain
- Works with tools you haven't configured yet
- Consistent, reliable results across runs

## Security

- Config stored with 0600 permissions at `~/.config/ipcrawler/config.toml`
- API keys masked when viewing config
- Hidden password-style input during setup

## Architecture

```
src/
├── main.rs       # Entry point
├── cli.rs        # CLI parsing
├── config/       # Configuration (loading, setup wizard)
├── display/      # Output formatting (terminal, HTML, markdown)
├── parser/       # AI integration (LLM API, entity extraction)
├── templates/    # YAML system (loader, sudo detection, executor)
└── storage/      # Output management (file ops, reports)
```

## Development

```bash
cargo build
cargo run -- <target> -o ./scan -v  # Debug logging
```

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

## Troubleshooting

**TTY warning during setup:** Build the release binary first and run directly instead of through `cargo run`:

```bash
cargo build --release
./target/release/ipcrawler setup
```

**Auto-generated output directories:** If no `-o` flag is provided, output is saved to `./ipcrawler_<target>_<timestamp>`.

## License

MIT
