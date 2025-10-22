# Configuration Guide

## Wordlist Management

IPCrawler uses a centralized wordlist configuration in `config/wordlists.yaml`.

### Using Predefined Wordlists

```bash
ipcrawler -t 192.168.1.1 -p 80 -w common
ipcrawler -t 192.168.1.1 -p 80 -w big
ipcrawler -t 192.168.1.1 -p 80 -w medium
```

### Using Custom Wordlist Path

```bash
ipcrawler -t 192.168.1.1 -p 80 -w /path/to/custom/wordlist.txt
```

### Available Wordlist Names

- `common` - Common web content (default)
- `big` - Larger web content list
- `medium` - Medium directory list
- `small` - Small directory list
- `subdomains` - Top 5000 subdomains
- `subdomains-20k` - Top 20000 subdomains
- `api` - API endpoints
- `backups` - Backup files

### Customizing Wordlists

Edit `config/wordlists.yaml`:

```yaml
wordlists:
  common: /usr/share/seclists/Discovery/Web-Content/common.txt
  custom: /path/to/your/wordlist.txt
  api: /path/to/api-wordlist.txt
```

## Adding Custom Tools

Create a YAML file in the `tools/` directory:

```yaml
name: "custom-scanner"
description: "My custom vulnerability scanner"
command: "custom-scanner -h {{target}} -p {{port}} -o {{output_file}}"
sudo_command: "custom-scanner -h {{target}} -p {{port}} --aggressive -o {{output_file}}"
installer:
  apt: "apt install -y custom-scanner"
  brew: "brew install custom-scanner"
  pacman: "pacman -S --noconfirm custom-scanner"
timeout: 300
output:
  type: "json"
  patterns:
    - name: "vulnerability_found"
      regex: "VULN: (.+)"
      severity: "high"
```

### YAML Schema Reference

**Required Fields:**
- `name` - Tool name
- `description` - Short description
- `command` - Command template for normal execution
- `installer` - Installation commands per package manager
- `output` - Output parsing configuration

**Optional Fields:**
- `sudo_command` - Command template when running with sudo
- `script_path` - Path to custom shell script

**Template Placeholders:**
- `{{target}}` - Target IP address
- `{{port}}` - Port number (for port-specific tools)
- `{{output_file}}` - Output file path
- `{{wordlist}}` - Resolved wordlist path

**Output Types:**
- `json` - Native JSON output
- `xml` - XML output
- `regex` - Plain text with regex patterns

**Severity Levels:**
- `critical`, `high`, `medium`, `low`, `info`

## Custom Shell Scripts

IPCrawler supports custom shell scripts with built-in security validation.

### Creating Custom Scripts

1. Create script in `tools/scripts/` directory:

```bash
#!/bin/bash
# custom-scan.sh
TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

echo "Scanning $TARGET:$PORT" > "$OUTPUT_FILE"
nmap -sV "$TARGET" -p "$PORT" >> "$OUTPUT_FILE"
```

2. Reference in tool YAML:

```yaml
name: "custom-scan"
description: "Custom scanning script"
command: "custom-scan.sh {{target}} {{port}} {{output_file}}"
timeout: 300
output:
  type: "regex"
  patterns:
    - name: "scan_result"
      regex: "open"
      severity: "info"
```

3. Run normally:

```bash
ipcrawler -t 192.168.1.1 -p 80
```

IPCrawler will:
- Automatically detect the .sh file
- Validate script for dangerous commands
- Make it executable (no chmod needed)
- Execute with security restrictions

### Script Best Practices

- Always include shebang (`#!/bin/bash`)
- Use variables for passed arguments
- Redirect output to `$OUTPUT_FILE`
- Keep scripts under 1MB
- Avoid dangerous commands (see [Security Documentation](SECURITY.md))
- Test scripts individually before integration

## Port Scanning Modes

| Mode | Description | Example |
|------|-------------|---------|
| `fast` | Nmap fast scan (top 100 ports) | `-p fast` |
| `common` | 15 most common ports | `-p common` |
| `top-1000` | Top 1000 most used ports | `-p top-1000` |
| `top-10000` | Top 10000 most used ports | `-p top-10000` |
| `all` | All 65535 ports | `-p all` |
| List | Comma-separated ports | `-p 22,80,443,8080` |
| Range | Port range | `-p 1-1000` |

## Output Structure

### Directory Layout

```
ipcrawler-results/YYYYMMDD_HHMMSS/
├── report.md           # Markdown summary report
├── results.json        # JSON formatted results
└── logs/              # Individual tool outputs
    ├── nmap_192_168_1_1_80.json
    ├── nikto_192_168_1_1_80.json
    └── gobuster_192_168_1_1_80.json
```

### Report Contents

**report.md includes:**
- Scan metadata (targets, ports, timestamp)
- Summary counts by severity
- Open ports and services
- Vulnerability tables organized by severity
- Tool execution log with status and duration

**results.json includes:**
- Structured findings data
- Tool execution results
- Timestamps and metadata
- Machine-readable format for integration
