# Usage Guide

Comprehensive usage instructions for IPCrawler.

## Basic Commands

```bash
# Basic scan
ipcrawler <target> -o <output_dir>

# Scan with verbose logging
ipcrawler <target> -o <output_dir> -v

# Enhanced scan with sudo (uses privileged templates)
sudo ipcrawler <target> -o <output_dir>

# Skip LLM parsing (raw outputs only)
ipcrawler <target> -o <output_dir> --no-parse

# Override LLM provider
ipcrawler <target> -o <output> --llm-provider openai
```

## Port Scanning

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

## Wordlists

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

## Templates

```bash
# List all templates
ipcrawler list

# Show template details
ipcrawler show nmap
```

## Output Structure

```
scan_output/
├── raw/              # Raw tool outputs (nmap/, nikto/, etc.)
├── entities.json     # Extracted entities (IPs, ports, URLs, etc.)
├── report.json       # Full structured report
├── report.html       # Interactive HTML report
└── report.md         # Markdown documentation
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

## Troubleshooting

### TTY Warning During Setup

Build the release binary first:
```bash
cargo build --release
./target/release/ipcrawler setup
```

### Auto-Generated Output Directories

If no `-o` flag is provided, output is saved to `./ipcrawler_<target>_<timestamp>`.

### Wordlist Not Found

Install SecLists (recommended for Kali/HTB):
```bash
sudo apt install seclists
```

Or use direct file path:
```bash
ipcrawler <target> -w /path/to/wordlist.txt
```
