# IPCrawler Tools Configuration Guide

This guide provides comprehensive documentation for creating tool configurations (YAML files) and shell scripts for the IPCrawler reconnaissance framework.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [YAML Tool Configuration](#yaml-tool-configuration)
- [Shell Script Integration](#shell-script-integration)
- [Command Execution Model](#command-execution-model)
- [Output Processing](#output-processing)
- [Pattern Matching](#pattern-matching)
- [Template Variables](#template-variables)
- [Best Practices](#best-practices)
- [Complete Examples](#complete-examples)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### How IPCrawler Processes Tools

```
┌─────────────────┐
│   YAML Files    │ → Loaded by ToolRegistry
│  (tools/*.yaml) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Tool Schema    │ → Validated and parsed
│   (Tool struct) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Task Queue    │ → Commands rendered with context
│   (with target) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TaskRunner     │ → Executes commands directly (NOT through shell)
│   (async exec)  │ → Captures stdout/stderr automatically
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OutputParser    │ → Applies regex patterns to stdout
│  (regex/json)   │ → Creates Finding objects
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Reports      │ → report.md, results.json, logs/*.log
└─────────────────┘
```

### Key Concepts

1. **Direct Execution**: Commands are executed directly via `tokio::process::Command`, NOT through a shell
2. **stdout Capture**: All stdout is captured automatically - no need for redirections
3. **Pattern Matching**: Regex patterns extract findings from stdout
4. **Automatic Handling**: Scripts are automatically made executable, validated for security

---

## YAML Tool Configuration

### Complete Schema

```yaml
name: "tool-name"                    # REQUIRED: Unique identifier
description: "Tool description"      # REQUIRED: What the tool does
command: "command {{target}}"        # REQUIRED: Command template (no shell redirections!)
sudo_command: "sudo command"         # OPTIONAL: Alternative command for root/sudo
script_path: "path/to/script.sh"     # OPTIONAL: Reference to shell script
installer:                           # REQUIRED: Installation commands per package manager
  apt: "apt install -y package"
  yum: "yum install -y package"
  dnf: "dnf install -y package"
  brew: "brew install package"
  pacman: "pacman -S --noconfirm package"
  zypper: "zypper install -y package"
  yay: "yay -S --noconfirm package"       # AUR helpers (Arch)
  paru: "paru -S --noconfirm package"
  pikaur: "pikaur -S --noconfirm package"
  trizen: "trizen -S --noconfirm package"
timeout: 60                          # REQUIRED: Timeout in seconds (default: 300)
output:                              # REQUIRED: Output processing configuration
  type: "regex"                      # "regex", "json", or "xml"
  json_flag: "-o json"               # OPTIONAL: Flag for JSON output
  patterns:                          # List of regex patterns
    - name: "pattern_name"           # Pattern identifier
      regex: 'regex_pattern'         # Regular expression
      severity: "info"               # "info", "low", "medium", "high", "critical"
```

### Field Details

#### `name` (REQUIRED)
- **Type**: String
- **Purpose**: Unique identifier for the tool
- **Rules**:
  - Must be unique across all tools
  - Used for logging, task tracking, and output files
  - Lowercase with hyphens recommended
- **Example**: `"nmap"`, `"nikto"`, `"whatweb"`

#### `description` (REQUIRED)
- **Type**: String
- **Purpose**: Human-readable description of the tool's function
- **Displayed**: In tool selection, help messages, reports
- **Example**: `"Comprehensive port scanner and service detection"`

#### `command` (REQUIRED)
- **Type**: String (template)
- **Purpose**: The command to execute
- **CRITICAL RULES**:
  - [-] **DO NOT** use shell redirections (`>`, `>>`, `|`, `&`)
  - [-] **DO NOT** use shell features (backticks, `$()`, globs)
  - [+] **DO** use template variables (`{{target}}`, `{{port}}`, etc.)
  - [+] stdout is captured automatically
- **Example**:
  ```yaml
  # CORRECT
  command: "nmap -sV {{target}} -p {{ports}}"

  # WRONG - stdout redirection doesn't work!
  command: "nmap -sV {{target}} > {{output_file}}"
  ```

#### `sudo_command` (OPTIONAL)
- **Type**: String (template)
- **Purpose**: Alternative command when running with sudo/root privileges
- **Automatically selected** when IPCrawler detects root privileges
- **Use case**: Enable privileged scan modes (SYN scan, OS detection, etc.)
- **Example**:
  ```yaml
  command: "nmap -sV {{target}}"
  sudo_command: "nmap -sS -O -A {{target}}"
  ```

#### `installer` (REQUIRED)
- **Type**: Object mapping package managers to install commands
- **Purpose**: Automatic tool installation
- **Supported package managers**:
  - `apt` (Debian/Ubuntu)
  - `yum` (RHEL/CentOS 7)
  - `dnf` (Fedora/RHEL 8+)
  - `brew` (macOS)
  - `pacman` (Arch Linux - official repos)
  - `zypper` (openSUSE)
  - `yay`, `paru`, `pikaur`, `trizen` (Arch AUR helpers)
- **Fallback behavior**: AUR helpers fall back to `pacman` if not specified
- **Example**:
  ```yaml
  installer:
    apt: "apt install -y nmap"
    pacman: "pacman -S --noconfirm nmap"
    yay: "yay -S --noconfirm nmap"  # Same package, AUR helper for other tools
  ```

#### `timeout` (OPTIONAL)
- **Type**: Integer (seconds)
- **Default**: 300 seconds (5 minutes)
- **Purpose**: Maximum execution time before task is killed
- **Recommendations**:
  - Quick checks (ping, whois): 30-60 seconds
  - Scans (nmap, nikto): 600-1800 seconds
  - Heavy scans (comprehensive): 3600+ seconds

#### `output` (REQUIRED)
- **Type**: Object
- **Purpose**: Defines how to parse tool output
- **Fields**:
  - `type`: Output format (`"regex"`, `"json"`, `"xml"`)
  - `json_flag`: Optional flag to enable JSON output
  - `patterns`: List of regex patterns to extract findings

---

## Output Processing

### Output Types

#### 1. `regex` (Most Common)
- **Use**: For text-based output
- **Behavior**: Applies regex patterns line-by-line to stdout
- **Best for**: Most CLI tools (nmap, dig, gobuster, etc.)

```yaml
output:
  type: "regex"
  patterns:
    - name: "open_port"
      regex: 'Port (\d+) is (open|closed)'
      severity: "info"
```

#### 2. `json`
- **Use**: For tools that output JSON
- **Behavior**: Validates JSON, then applies regex patterns
- **Fallback**: If JSON invalid, treats as regex
- **Best for**: Modern tools with `--json` flag

```yaml
output:
  type: "json"
  json_flag: "-o json"  # Flag to enable JSON output
  patterns:
    - name: "vulnerability"
      regex: '"severity":"(high|critical)"'
      severity: "high"
```

#### 3. `xml`
- **Use**: For XML output (like nmap `-oX`)
- **Behavior**: Applies regex patterns to XML structure
- **Best for**: Tools with XML output modes

```yaml
output:
  type: "xml"
  patterns:
    - name: "service"
      regex: '<service name="([^"]+)"'
      severity: "info"
```

### Pattern Matching

#### Pattern Structure

```yaml
patterns:
  - name: "pattern_identifier"        # What you're looking for
    regex: 'regex_with_capture_groups'
    severity: "info"                  # Finding severity
```

#### Severity Levels

| Level      | Use Case                          | Color (TUI) |
|------------|-----------------------------------|-------------|
| `info`     | Informational findings            | Blue        |
| `low`      | Minor issues, low-priority        | Green       |
| `medium`   | Moderate issues, attention needed | Yellow      |
| `high`     | Serious issues, important         | Orange      |
| `critical` | Critical vulnerabilities          | Red         |

#### Regex Capture Groups

The parser uses capture groups to extract data:

- **Group 0**: Full match (always captured)
- **Group 1+**: Extracted data (displayed in findings)

**Example**:
```yaml
- name: "a_record"
  regex: '([^\s]+)\s+\d+\s+IN\s+A\s+([0-9.]+)'
  # Group 1: Domain name
  # Group 2: IP address
  severity: "info"
```

**Result** in findings:
```
Title: a_record
Description: example.com | 93.184.216.34
```

#### What Happens if Patterns Don't Match?

**Don't worry - nothing is lost!** IPCrawler has multiple safety nets:

1. **Automatic Fallback**: If no patterns match but there's stdout, IPCrawler creates a generic "Tool output" finding containing the complete raw output
2. **Raw Log Files**: Every tool execution saves complete stdout/stderr to `logs/{tool}_{target}_{port}.log`
3. **You can review and improve**: Check the logs, identify missed patterns, update YAML, re-run

**Example**:
```yaml
# Even with no patterns at all, output is preserved
output:
  type: "regex"
  patterns: []  # Empty patterns
  # Result: Generic finding with full stdout + saved to logs/
```

#### Pattern Best Practices

1. **Use capture groups** to extract meaningful data
2. **Make patterns specific** to avoid false positives
3. **Test patterns** with sample output
4. **Use non-greedy matching** (`.*?`) when appropriate
5. **Escape special regex characters** (`\.`, `\[`, `\(`, etc.)
6. **Add catch-all patterns** at the end for anything missed
7. **Review logs/** after first run to identify missed patterns

**Example patterns**:

```yaml
# Good - Specific, captures useful data
- name: "ssh_version"
  regex: 'SSH-([0-9.]+)-OpenSSH_([0-9.]+)'
  severity: "info"

# Bad - Too generic, captures useless data
- name: "anything"
  regex: '.*'
  severity: "info"
```

---

## Template Variables

### Available Variables

| Variable        | Type   | Description                        | Example             |
|-----------------|--------|------------------------------------|---------------------|
| `{{target}}`    | String | Target IP/domain                   | `192.168.1.1`       |
| `{{port}}`      | Int    | Single port (per-port scanning)    | `80`                |
| `{{ports}}`     | String | Comma-separated ports (batch scan) | `80,443,8080`       |
| `{{output_file}}`| String| Path for output file (legacy)      | `/tmp/scan.json`    |
| `{{wordlist}}`  | String | Path to wordlist file              | `/usr/share/...`    |

### Variable Usage Rules

#### `{{target}}` (Always Available)
- **Required**: Yes, for all tools
- **Format**: Depends on user input
  - Domain: `example.com`
  - IPv4: `192.168.1.1`
  - IPv6: `2001:db8::1`
  - CIDR: `192.168.1.0/24`

#### `{{port}}` vs `{{ports}}`

**Use `{{port}}`** when:
- Tool scans ONE port at a time
- Examples: `nikto`, `whatweb`, `gobuster`, `sslscan`
- Task behavior: One task created per port
- Command: `nikto -h {{target}}:{{port}}`

**Use `{{ports}}`** when:
- Tool scans MULTIPLE ports efficiently
- Examples: `nmap`, `masscan`
- Task behavior: One task for ALL ports
- Command: `nmap -p {{ports}} {{target}}`

**Use neither** when:
- Tool doesn't use ports
- Examples: `ping`, `whois`, `traceroute`, `dig`
- Task behavior: One task per target

#### `{{output_file}}` (Legacy - Not Recommended)

- **Status**: Deprecated but still available
- **Reason**: stdout capture is automatic
- **Current behavior**: File path is generated but often unused
- **Use case**: Only if tool REQUIRES a `-o` flag and doesn't support stdout

**Why not to use it**:
```yaml
# WRONG - Redirection doesn't work
command: "tool {{target}} > {{output_file}}"

# WRONG - Unnecessary, stdout is captured anyway
command: "tool {{target}} -o {{output_file}}"

# CORRECT - Just output to stdout
command: "tool {{target}}"
```

#### `{{wordlist}}` (Optional)

- **Use**: For tools that need wordlists (directory busters, brute forcers)
- **Configuration**: User specifies wordlist via CLI
- **Default resolution**: Uses wordlist config or direct path
- **Example**:
  ```yaml
  command: "gobuster dir -u http://{{target}} -w {{wordlist}}"
  ```

---

## Command Execution Model

### Direct Execution (No Shell)

**How IPCrawler executes commands**:

```rust
Command::new("nmap")           // Program name
    .args(["-sV", target])     // Arguments as array
    .stdout(Stdio::piped())    // Capture stdout
    .stderr(Stdio::piped())    // Capture stderr
    .output()                  // Execute and wait
```

### Critical Implications

#### [-] Shell Features Don't Work

```yaml
# THESE WILL FAIL:

# Redirections
command: "nmap {{target}} > output.txt"    # '>' treated as argument

# Pipes
command: "cat file | grep pattern"         # '|' treated as argument

# Globbing
command: "cat /etc/*.conf"                 # '*' treated as literal

# Command substitution
command: "echo $(whoami)"                  # '$()' treated as literal

# Environment variables
command: "echo $HOME"                      # '$HOME' treated as literal
```

#### [+] What Works

```yaml
# Direct commands with arguments
command: "nmap -sV -p 80,443 {{target}}"

# Template variables
command: "dig {{target}} A +short"

# Flags and options
command: "nikto -h {{target}} -Tuning 1,2,3"
```

### For Shell Features: Use Shell Scripts

If you need shell features, create a `.sh` script:

```yaml
# YAML file
name: "complex-scan"
command: "tools/complex-scan.sh {{target}} {{port}} {{output_file}}"
```

```bash
#!/bin/bash
# complex-scan.sh
TARGET="$1"
PORT="$2"

# Now you can use shell features
for i in {1..5}; do
    echo "Attempt $i"
    timeout 5 nc -zv "$TARGET" "$PORT" 2>&1 | grep -i "open"
done

# Pipes, redirections, etc. work here
```

---

## Shell Script Integration

### When to Use Shell Scripts

Use shell scripts (.sh) when you need:

1. **Multiple commands** in sequence
2. **Shell features** (loops, pipes, redirections)
3. **Conditional logic** (if/else)
4. **Complex processing** (grep, awk, sed)
5. **Error handling** (retry logic)
6. **Multiple tool orchestration**

### Shell Script Rules

**IMPORTANT**: Shell scripts must be placed in `tools/scripts/` directory and should NOT be made executable manually. IPCrawler will scan and make them executable at runtime.

#### 1. Directory Structure

```
tools/
├── tool.yaml          # YAML configurations
├── README.md          # This file
└── scripts/
    └── tool.sh        # Shell scripts (not executable)
```

#### 2. Shebang is Required

```bash
#!/bin/bash
# Must be first line
```

#### 3. Accept Standard Parameters

For TUI compatibility, accept these parameters:

```bash
TARGET="$1"      # Always provided
PORT="$2"        # Provided if tool uses {{port}}
OUTPUT_FILE="$3" # Provided but optional to use
```

#### 4. Output to stdout

**Critical**: All output you want parsed must go to stdout

```bash
# CORRECT - Output to stdout (captured by TUI)
echo "=== RESULTS ==="
dig "$TARGET" A

# WRONG - File output (not captured)
dig "$TARGET" A > results.txt

# OPTIONAL - Can use files internally, but echo important stuff
dig "$TARGET" A > /tmp/temp.txt
echo "Found IPs:"
grep "IN A" /tmp/temp.txt
```

#### 5. Handle Errors Gracefully

```bash
# Check if command exists
if ! command -v nmap &> /dev/null; then
    echo "ERROR: nmap not found"
    exit 1
fi

# Timeout long operations
timeout 30 nmap "$TARGET" || echo "Scan timed out"

# Suppress stderr if not useful
dig "$TARGET" 2>/dev/null || echo "DNS query failed"
```

#### 6. Security Considerations

Scripts are automatically validated for security by IPCrawler:

**Blocked patterns**:
- `rm -rf /`, `rm -rf /*`
- `dd if=/dev/zero`
- `:(){:|:&};:` (fork bombs)
- `mkfs`, `format`

**Warnings**:
- `sudo`, `su`
- `chmod`, `chown`
- `curl`, `wget` without domain restrictions

**Best practices**:
- Validate input
- Use quotes around variables
- Avoid destructive operations
- Comment dangerous sections

#### 7. Script is Made Executable Automatically

**You don't need to run** `chmod +x script.sh`

Scripts in `tools/scripts/` are automatically scanned and made executable by IPCrawler at runtime via `ScriptSecurity::make_executable()`.

**DO NOT** manually set execute permissions - leave scripts as `-rw-r--r--` (644).

### Shell Script Template

```bash
#!/bin/bash
# Tool Name - Description
# Usage: script.sh <target> <port> <output_file>

set -euo pipefail  # Exit on error, undefined vars, pipe failures

TARGET="${1:-}"
PORT="${2:-}"
OUTPUT_FILE="${3:-}"

# Validate input
if [ -z "$TARGET" ]; then
    echo "ERROR: Target is required"
    exit 1
fi

# Header (for readability in logs)
echo "=== TOOL SCAN FOR $TARGET ==="
echo "Started at: $(date)"
echo ""

# Main logic - output to stdout
echo "=== PHASE 1: Basic Checks ==="
timeout 10 command1 "$TARGET" || echo "Command 1 failed"
echo ""

echo "=== PHASE 2: Deep Scan ==="
timeout 30 command2 "$TARGET" "$PORT" || echo "Command 2 failed"
echo ""

# Footer
echo "=== SCAN COMPLETED ==="
echo "Finished at: $(date)"

exit 0
```

---

## Complete Examples

### Example 1: Simple Regex Tool (ping)

```yaml
name: "ping"
description: "ICMP connectivity test"
command: "ping -c 4 -W 2 {{target}}"
installer:
  apt: "apt install -y iputils-ping"
  pacman: "pacman -S --noconfirm iputils"
timeout: 30
output:
  type: "regex"
  patterns:
    - name: "packets_received"
      regex: '(\d+) packets transmitted, (\d+) received'
      severity: "info"
    - name: "rtt_times"
      regex: 'rtt min/avg/max/mdev = ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)'
      severity: "info"
    - name: "packet_loss"
      regex: '(\d+)% packet loss'
      severity: "medium"
```

### Example 2: Port-Specific Tool (nikto)

```yaml
name: "nikto"
description: "Web server vulnerability scanner"
command: "nikto -h {{target}}:{{port}} -Format json -Tuning 1,2,3,4,5"
sudo_command: "nikto -h {{target}}:{{port}} -Format json -Tuning 1,2,3,4,5,6,7,8,9,a,b,c -evasion 1,2,3"
installer:
  apt: "apt install -y nikto"
  pacman: "pacman -S --noconfirm nikto"
timeout: 1800
output:
  type: "json"
  json_flag: "-Format json"
  patterns:
    - name: "vulnerability_found"
      regex: '"msg":"([^"]+)".*"OSVDB-(\d+)"'
      severity: "medium"
    - name: "critical_vuln"
      regex: '"msg":"([^"]+)".*"critical"'
      severity: "critical"
    - name: "server_info"
      regex: '"msg":"Server: ([^"]+)"'
      severity: "info"
```

### Example 3: Batch Port Scanner (nmap)

```yaml
name: "nmap"
description: "Comprehensive port scanner"
command: "nmap -sV -sC {{target}} -p {{ports}}"
sudo_command: "nmap -sS -sV -sC -O -A {{target}} -p {{ports}}"
installer:
  apt: "apt install -y nmap"
  pacman: "pacman -S --noconfirm nmap"
timeout: 1800
output:
  type: "regex"
  patterns:
    - name: "open_port"
      regex: '(\d+)/(tcp|udp)\s+(open|filtered)'
      severity: "info"
    - name: "service_detected"
      regex: '(\d+)/(tcp|udp)\s+open\s+([^\s]+)\s+([^\n]+)'
      severity: "info"
    - name: "os_detection"
      regex: 'OS: ([^\n]+)'
      severity: "medium"
```

### Example 4: No-Port Tool (whois)

```yaml
name: "whois"
description: "Domain registration information"
command: "whois {{target}}"
installer:
  apt: "apt install -y whois"
  pacman: "pacman -S --noconfirm whois"
timeout: 60
output:
  type: "regex"
  patterns:
    - name: "registrar"
      regex: 'Registrar: ([^\n]+)'
      severity: "info"
    - name: "creation_date"
      regex: 'Creation Date: ([^\n]+)'
      severity: "info"
    - name: "expiration_date"
      regex: 'Expir[ay].*Date: ([^\n]+)'
      severity: "info"
    - name: "nameservers"
      regex: 'Name Server: ([^\s]+)'
      severity: "info"
```

### Example 5: Tool with Wordlist (gobuster)

```yaml
name: "gobuster"
description: "Directory and file bruteforcer"
command: "gobuster dir -u http://{{target}}:{{port}} -w {{wordlist}} -q -t 50 -e -x php,html,txt"
sudo_command: "gobuster dir -u http://{{target}}:{{port}} -w {{wordlist}} -q -t 100 -e -x php,asp,aspx,jsp,html,txt,conf,bak"
installer:
  apt: "apt install -y gobuster"
  pacman: "pacman -S --noconfirm gobuster"
timeout: 1200
output:
  type: "regex"
  patterns:
    - name: "found_path"
      regex: '(http[s]?://[^\s]+)\s+\(Status: (200|201|301|302)\)'
      severity: "low"
    - name: "sensitive_path"
      regex: '(http[s]?://[^\s]+(?:admin|config|backup|login)[^\s]*)\s+\(Status:'
      severity: "medium"
    - name: "error_page"
      regex: '(http[s]?://[^\s]+)\s+\(Status: (401|403|500)\)'
      severity: "info"
```

### Example 6: Shell Script-Based Tool (comprehensive-scan)

**comprehensive-scan.yaml**:
```yaml
name: "comprehensive-scan"
description: "Multi-tool comprehensive reconnaissance"
command: "comprehensive-scan.sh {{target}} {{port}} {{output_file}}"
installer:
  apt: "echo 'Built-in script, no installation needed'"
  pacman: "echo 'Built-in script, no installation needed'"
timeout: 3600
output:
  type: "regex"
  patterns:
    - name: "service_banner"
      regex: 'Banner: ([^\n]+)'
      severity: "info"
    - name: "ssl_cert"
      regex: 'SSL Certificate: ([^\n]+)'
      severity: "info"
    - name: "interesting_path"
      regex: 'Interesting path found: ([^\n]+)'
      severity: "medium"
```

**tools/scripts/comprehensive-scan.sh** (not executable):
```bash
#!/bin/bash
TARGET="$1"
PORT="$2"

echo "=== COMPREHENSIVE SCAN FOR $TARGET:$PORT ==="

# Basic connectivity
echo "=== CONNECTIVITY CHECK ==="
timeout 5 nc -zv "$TARGET" "$PORT" 2>&1
echo ""

# Banner grab
echo "=== BANNER GRAB ==="
echo "" | timeout 5 nc "$TARGET" "$PORT" 2>/dev/null | head -5
echo ""

# SSL check if port 443
if [ "$PORT" = "443" ]; then
    echo "=== SSL CERTIFICATE ==="
    timeout 10 openssl s_client -connect "$TARGET:$PORT" -servername "$TARGET" \
        2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null
    echo ""
fi

echo "=== SCAN COMPLETE ==="
```

---

## Best Practices

### 1. Command Design

[+] **DO**:
- Use direct commands that output to stdout
- Include appropriate timeout values
- Test commands manually before adding to YAML
- Use specific flags for cleaner output
- Consider both standard and sudo variants

[-] **DON'T**:
- Use shell redirections (`>`, `>>`, `|`)
- Rely on shell variables (`$VAR`, `$()`)
- Use interactive commands
- Forget to handle errors in scripts
- Make commands that require user input

### 2. Output Patterns

[+] **DO**:
- Create specific patterns for important findings
- Use capture groups to extract useful data
- Test regex patterns with real output
- Include patterns for error conditions
- Use appropriate severity levels

[-] **DON'T**:
- Make overly broad patterns (`.*`)
- Forget to escape special regex characters
- Use patterns that match noise
- Mix multiple finding types in one pattern

### 3. Script Writing

[+] **DO**:
- Output important results to stdout
- Include section headers for readability
- Handle missing commands gracefully
- Use timeouts for network operations
- Validate input parameters
- Add comments explaining complex logic

[-] **DON'T**:
- Only write to files (stdout is captured)
- Assume commands exist without checking
- Run destructive operations
- Ignore errors silently
- Use unbounded loops or operations

### 4. Testing

**Always test your tools**:

```bash
# 1. Test command manually
dig example.com ANY +noall +answer

# 2. Test with template substitution
dig 8.8.8.8 ANY +noall +answer

# 3. Verify output matches patterns
dig example.com ANY +noall +answer | grep -E 'IN\s+A\s+'

# 4. Test in IPCrawler
./ipcrawler -t example.com -p 80 -d tools/
```

### 5. Documentation

Add comments to complex tools:

```yaml
name: "complex-tool"
description: "Does complex things with multiple phases"  # Be specific
command: "tool {{target}} -v -x advanced"  # Explain non-obvious flags
installer:
  # Some systems need additional dependencies
  apt: "apt install -y tool libspecial-dev"
timeout: 300  # Increased timeout due to comprehensive scanning
output:
  type: "regex"
  patterns:
    # Pattern explanation: matches IPv4 addresses in output
    - name: "ipv4_address"
      regex: '(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
      severity: "info"
```

---

## Troubleshooting

### Common Issues

#### Issue: Tool not finding output / Missing findings

**Symptoms**: Tool completes but no findings, or important data seems missing

**Causes**:
1. Command uses shell redirection
2. Output not on stdout
3. Regex patterns don't match output format

**Important**: Even if patterns don't match, output is NOT lost!

**Where to find the output**:
```bash
# Check the raw logs directory
cat ipcrawler-results/{timestamp}/logs/{tool}_{target}_{port}.log

# Look for generic "Tool output" finding in report.md
# This contains full stdout when no patterns match
```

**Solutions**:
```yaml
# Check 1: Remove redirections
# WRONG
command: "tool {{target}} > file"
# RIGHT
command: "tool {{target}}"

# Check 2: Force stdout output
command: "tool {{target}} -o -"  # Many tools use '-' for stdout

# Check 3: Test patterns
# Run manually and check output format:
$ tool target
```

#### Issue: Command times out

**Symptoms**: Task shows "Timed Out" status

**Solutions**:
```yaml
# Increase timeout for slow operations
timeout: 3600  # 1 hour for heavy scans

# Add timeout to command if it supports it
command: "tool {{target}} --timeout 60"

# For scripts, use timeout internally
# In script:
timeout 60 long-running-command
```

#### Issue: Template variables not substituted

**Symptoms**: Command shows literal `{{target}}`

**Causes**:
1. Typo in variable name
2. Variable not available for tool type

**Solutions**:
```yaml
# Check spelling (case-sensitive)
{{target}}    # Correct
{{Target}}    # Wrong
{{taget}}     # Wrong

# Check if variable makes sense
# Port-specific tool needs {{port}}
command: "tool {{target}}:{{port}}"

# Port-batch tool needs {{ports}}
command: "tool {{target}} -p {{ports}}"
```

#### Issue: Script not executing

**Symptoms**: "Script not found" or "Permission denied"

**Causes**:
1. Script path incorrect
2. Script not in `tools/scripts/` directory
3. Missing shebang
4. Manually set executable permission (incorrect workflow)

**Solutions**:
```yaml
# CORRECT: Use just the script filename
command: "script.sh {{target}}"
# IPCrawler will look in tools/scripts/ automatically

# WRONG: Using full path
command: "tools/scripts/script.sh {{target}}"  # Incorrect

# Script structure:
tools/
└── scripts/
    └── script.sh  # Should be -rw-r--r-- (644), NOT executable

# Ensure shebang is first line
#!/bin/bash
# Must be line 1, no spaces before

# DON'T manually chmod +x - IPCrawler does this at runtime
# Script permissions should be -rw-r--r-- (644)
```

#### Issue: Pattern matches but wrong data

**Symptoms**: Findings show unexpected text

**Cause**: Regex capture groups not correct

**Solution**:
```yaml
# Test regex with sample output
# Output: "Server: nginx/1.18.0"

# Bad - captures full line
regex: '.*nginx.*'

# Good - captures version
regex: 'Server: nginx/([0-9.]+)'
# Result: Description shows "1.18.0"

# Test with:
$ echo "Server: nginx/1.18.0" | grep -oP 'nginx/\K[0-9.]+'
```

### Debugging Tips

1. **Check raw output**:
   ```bash
   # Look in logs directory after scan
   cat ipcrawler-results/*/logs/tool_target_port.log
   ```

2. **Test regex patterns online**:
   - Use https://regex101.com/
   - Paste sample output
   - Test your patterns

3. **Run tool manually**:
   ```bash
   # Test exact command IPCrawler would run
   tool target -p 80
   ```

4. **Enable verbose logging**:
   ```bash
   # Check for error messages during execution
   RUST_LOG=debug ./ipcrawler -t target -p 80
   ```

5. **Validate YAML syntax**:
   ```bash
   # Use yamllint or online validators
   yamllint tools/tool.yaml
   ```

---

## Quick Reference

### Minimal Working Example

```yaml
name: "example"
description: "Example tool"
command: "example {{target}}"
installer:
  apt: "apt install -y example"
  pacman: "pacman -S --noconfirm example"
timeout: 60
output:
  type: "regex"
  patterns:
    - name: "result"
      regex: 'Result: (.+)'
      severity: "info"
```

### Template Variables Cheat Sheet

| Use Case | Variables | Task Creation |
|----------|-----------|---------------|
| No ports | `{{target}}` | 1 task per target |
| Per-port | `{{target}}` `{{port}}` | 1 task per port per target |
| Port batch | `{{target}}` `{{ports}}` | 1 task per target (all ports) |
| Wordlist | `{{wordlist}}` | Add to any above |

### Severity Guidelines

- **Critical**: RCE, auth bypass, critical vulns
- **High**: Serious security issues, sensitive data exposure
- **Medium**: Misconfigurations, deprecated software, moderate issues
- **Low**: Minor issues, recommendations
- **Info**: Informational findings, version detection, open ports

---

## Iterative Pattern Improvement Workflow

### Step 1: Run with Basic Patterns
```yaml
output:
  type: "regex"
  patterns:
    - name: "basic_match"
      regex: '\d+/tcp'
      severity: "info"
```

### Step 2: Check Raw Logs
```bash
# After scan completes
cat ipcrawler-results/20250122_120000/logs/nmap_192.168.1.1_80.log
```

### Step 3: Identify Missed Patterns
```
# Example log content:
22/tcp open  ssh     OpenSSH 8.2p1 Ubuntu
| ssh-hostkey:
|   2048 aa:bb:cc:dd:ee:ff (RSA)
80/tcp open  http    nginx 1.18.0
|_http-title: Welcome to nginx!
```

### Step 4: Add New Patterns
```yaml
patterns:
  # Original
  - name: "basic_match"
    regex: '\d+/tcp'
    severity: "info"

  # New patterns for missed data
  - name: "ssh_version"
    regex: 'ssh\s+OpenSSH ([^\s]+)'
    severity: "info"

  - name: "http_title"
    regex: '\|_http-title: (.+)'
    severity: "info"

  - name: "ssh_key_type"
    regex: '\|\s+(\d+)\s+[\w:]+\s+\((\w+)\)'
    severity: "low"
```

### Step 5: Verify Improvement
```bash
# Re-run scan
./ipcrawler -t 192.168.1.1 -p 22,80

# Check report for new findings
cat ipcrawler-results/*/report.md
```

## Additional Resources

- **IPCrawler Repository**: https://github.com/neur0map/prowl/ipcrawler
- **Regex Testing**: https://regex101.com/
- **YAML Validation**: https://www.yamllint.com/
- **Tool Documentation**: Check each tool's `--help` output

---

**Last Updated**: 2025-01-22
**Version**: 1.0.0
