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
- `json` - Structured JSON output with findings array (recommended for shell scripts)
- `regex` - Plain text with regex patterns (for traditional CLI tools)
- `xml` - XML output (legacy support)

**Severity Levels:**
- `critical`, `high`, `medium`, `low`, `info`

### JSON Output Format (Recommended)

For modern tools and shell scripts, use JSON output for structured findings:

```yaml
output:
  type: "json"  # Enables JSON parsing
```

**JSON Schema** your script should output:

```json
{
  "findings": [
    {
      "severity": "info|low|medium|high|critical",
      "title": "Short finding title",
      "description": "Detailed description of the finding",
      "port": 80  // Optional - port number if applicable
    }
  ],
  "metadata": {  // Optional - not parsed but preserved in logs
    "scan_type": "custom",
    "timestamp": "2025-01-23T12:00:00Z"
  }
}
```

**Marker-Based Output** for LLM analysis and logs:

```bash
#!/bin/bash
# Output markers separate raw tool output from JSON findings

echo "===START_RAW_OUTPUT===" >&2
echo "Running nmap scan..." >&2
nmap -sV "$TARGET" -p "$PORT" 2>&1 >&2  # Raw output to stderr
echo "===END_RAW_OUTPUT===" >&2

# JSON findings to stdout
cat <<EOF
{
  "findings": [
    {"severity": "info", "title": "Scan complete", "description": "Found 3 open ports"}
  ]
}
EOF
```

**How it works:**
1. **JSON findings** (stdout) → Parsed into structured report.md
2. **Marked raw output** (stderr) → Sent to LLM for analysis (if `--use-llm` enabled)
3. **Complete output** → Saved to logs/ directory

## Custom Shell Scripts

IPCrawler supports custom shell scripts with built-in security validation.

### Creating Custom Scripts

1. Create script in `tools/scripts/` directory with JSON output:

```bash
#!/bin/bash
# custom-scan.sh
TARGET="$1"
PORT="$2"

# Initialize findings
findings_json="[]"

# Raw output to stderr with markers
echo "===START_RAW_OUTPUT===" >&2
echo "Scanning $TARGET:$PORT" >&2
result=$(nmap -sV "$TARGET" -p "$PORT" 2>&1)
echo "$result" >&2
echo "===END_RAW_OUTPUT===" >&2

# Parse results into JSON
if echo "$result" | grep -q "open"; then
  finding=$(cat <<EOF
{
  "severity": "info",
  "title": "Port scan complete",
  "description": "Found open port on $TARGET:$PORT",
  "port": $PORT
}
EOF
)
  findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new')
fi

# Output JSON to stdout
cat <<EOF
{
  "findings": $findings_json,
  "metadata": {
    "scan_type": "custom_scan",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
```

2. Reference in tool YAML:

```yaml
name: "custom-scan"
description: "Custom scanning script with JSON output"
command: "custom-scan.sh {{target}} {{port}}"
timeout: 300
installer:
  apt: "apt install -y nmap jq"
  pacman: "pacman -S --noconfirm nmap jq"
output:
  type: "json"  # Enable JSON parsing
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

## Port Configuration

IPCrawler uses a centralized port configuration in `config/ports.yaml`, similar to wordlists.

### Using Predefined Port Ranges

```bash
ipcrawler -t 192.168.1.1 -p fast
ipcrawler -t 192.168.1.1 -p web
ipcrawler -t 192.168.1.1 -p database
```

### Available Port Range Names

- `fast` - Top 100 most common ports
- `common` - 15 most common ports for quick recon
- `top-1000` - Nmap built-in top 1000 ports selection
- `top-10000` - Nmap built-in top 10000 ports selection
- `all` - All 65535 TCP ports
- `web` - Common web server ports (80,443,8000,8080,8443,etc)
- `database` - Database server ports (1433,3306,5432,etc)
- `remote` - Remote access ports (22,3389,5900,etc)
- `mail` - Email server ports (25,110,143,465,587,993,995)
- `ftp` - FTP and related ports (20,21,989,990)

### Custom Port Specifications

```bash
# Single port
ipcrawler -t 192.168.1.1 -p 80

# Port list
ipcrawler -t 192.168.1.1 -p 22,80,443

# Port range
ipcrawler -t 192.168.1.1 -p 1-1000
```

### Customizing Port Ranges

Edit `config/ports.yaml`:

```yaml
port_ranges:
  fast: "21,22,23,25,53,80,110,111,135,139,143,443,993,995,1723,3306,3389,5432,5900,8080,8443,9100,10000"
  custom: "80,443,8080,8443,9000"
  corporate: "22,53,80,88,135,139,389,443,445,636,993,995,1433,3306,3389,5432"
```

## LLM Configuration

IPCrawler supports multiple LLM providers for enhanced output analysis and security insights.

### Environment Configuration

Create a `.env` file in the project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com

# Claude Configuration  
ANTHROPIC_API_KEY=your_claude_api_key
CLAUDE_MODEL=claude-3-sonnet-20240229
CLAUDE_BASE_URL=https://api.anthropic.com

# Ollama Configuration
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434

# Generic LLM Configuration
LLM_API_KEY=your_generic_api_key
```

### CLI LLM Options

```bash
# Enable LLM analysis
ipcrawler -t 192.168.1.1 -p 80 --use-llm

# Specify LLM provider
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-provider openai
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-provider claude
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-provider ollama

# Custom model and endpoint
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-model gpt-4-turbo
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-base-url http://localhost:8080

# API key via CLI (not recommended for production)
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-api-key your_key
```

### LLM Features

- **Security Analysis**: Specialized prompts for security tool output
- **Context Awareness**: Maintains conversation context for better analysis
- **Template System**: Customizable prompt templates for different tools
- **Multiple Providers**: Support for OpenAI, Claude, and Ollama
- **Fallback Handling**: Graceful degradation when LLM is unavailable

## Output Structure

### Directory Layout

```
ipcrawler-results/TARGET_HHMM/
├── report.md           # Enhanced Markdown summary with LLM insights
├── results.json        # JSON formatted results with LLM analysis
└── logs/              # Individual tool outputs
    ├── nmap_192_168_1_1_80.json
    ├── nikto_192_168_1_1_80.json
    └── gobuster_192_168_1_1_80.json
```

**Folder Naming:**
- **Single target**: `{IP}_HHMM` (e.g., `192.168.1.1_1532`)
- **Multiple targets**: `multiple_HHMM` (e.g., `multiple_1532`)

### Report Contents

**report.md includes:**
- Scan metadata (targets, ports, timestamp)
- Discovery narratives with LLM-generated insights
- Enhanced services analysis sections
- Vulnerability tables organized by severity with LLM context
- Tool execution log with status, duration, and LLM analysis
- Open ports extraction with service identification
- LLM-powered security assessments and recommendations

**results.json includes:**
- Structured findings data with LLM analysis
- Enhanced tool execution results
- Timestamps and metadata
- LLM context and conversation history
- Machine-readable format for integration
- Severity assessments with LLM confidence scores

## Universal Output Parser

IPCrawler features a Universal Output Parser with optional LLM intelligence for advanced analysis.

### Parsing Methods

#### Standard Parsing (`parse`)
- Original pattern-based parsing (regex, JSON, XML)
- Optional LLM enhancement when enabled
- Best for general use cases

#### Synchronous Parsing (`parse_sync`)
- Synchronous parsing for testing and dry-run modes
- No async overhead
- Used in `--dry-run` mode

#### LLM-Enhanced Parsing (`parse_with_llm`)
- Full LLM-powered analysis
- Context-aware processing
- Enhanced finding extraction and severity assessment

### Content Analysis Features

The `ContentAnalyzer` provides specialized analysis methods:

- **Network Scan Analysis**: Open ports, services, versions
- **DNS Reconnaissance**: Subdomains, records, misconfigurations
- **Vulnerability Assessment**: CVE identification, risk scoring
- **Web Application Analysis**: Technologies, vulnerabilities, headers
- **Service Enumeration**: Banner grabbing, fingerprinting

### Usage Examples

```bash
# Standard parsing with optional LLM
ipcrawler -t 192.168.1.1 -p 80 --use-llm

# Verbose mode uses original parsing method
ipcrawler -t 192.168.1.1 -p 80 --verbose --use-llm

# Dry-run mode uses synchronous parsing
ipcrawler -t 192.168.1.1 -p 80 --dry-run

# Normal mode uses enhanced LLM parsing
ipcrawler -t 192.168.1.1 -p 80 --use-llm
```

### Advanced Configuration

The Universal Output Parser can be configured through:

1. **CLI Options**: Enable/disable LLM, choose parsing mode
2. **Environment Variables**: LLM provider settings
3. **Tool YAML**: Output patterns and parsing rules
4. **Prompt Templates**: Custom analysis prompts

This creates a flexible system that can work with any security tool output while providing intelligent analysis when LLM is available.
