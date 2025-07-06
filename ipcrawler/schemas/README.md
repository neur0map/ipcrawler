# IPCrawler YAML Plugin Schema Documentation

This directory contains the schema and documentation for creating YAML-based plugins in IPCrawler's template system.

## Table of Contents

- [Quick Start](#quick-start)
- [Plugin Structure](#plugin-structure)
- [Template Variables](#template-variables)
- [Pattern Matching](#pattern-matching)
- [Service Detection](#service-detection)
- [Command Examples](#command-examples)
- [Plugin Types](#plugin-types)
- [Complete Examples](#complete-examples)
- [AI Development Guidelines](#ai-development-guidelines)

---

## File Organization & Workflow

### Plugin File Structure
```
templates/
├── your-template-name/
│   ├── 01-port-scanning/           # ORGANIZATIONAL: Port scan plugins
│   │   ├── nmap-basic.yaml         # priority: 1 (runs first)
│   │   └── custom-portscan.yaml    # priority: 5 (runs after nmap-basic)
│   ├── 02-service-enumeration/     # ORGANIZATIONAL: Service scan plugins  
│   │   ├── web-services/
│   │   │   ├── directory-scan.yaml # priority: 15 (runs after port scans)
│   │   │   └── web-enum.yaml       # priority: 20
│   │   └── ssh-services/
│   │       └── ssh-enum.yaml       # priority: 25
│   ├── 03-bruteforce/              # ORGANIZATIONAL: Brute force plugins
│   │   └── ssh-bruteforce.yaml     # priority: 50 (runs after service scans)
│   └── 04-reporting/               # ORGANIZATIONAL: Report plugins  
│       └── markdown-report.yaml   # priority: 90 (runs last)
```

**IMPORTANT**: Directory names (01-, 02-, etc.) are for **human organization only**. 
The actual execution order is determined by the `priority` field in each plugin's metadata.

### Execution Workflow
IPCrawler executes plugins based on **PRIORITY ONLY**:

**Execution Order:**
1. **Port Scan Plugins** (`type: "portscan"`): Execute by priority (1-10), discover open ports
2. **Service Scan Plugins** (`type: "servicescan"`): Execute by priority (10-40), analyze discovered services  
3. **Brute Force Plugins** (`type: "bruteforce"`): Execute by priority (40-60), attempt authentication
4. **Report Plugins** (`type: "reporting"`): Execute by priority (60-100), generate final reports

**CRITICAL: Priority-Based Execution Rules:**
- **Directory structure is ORGANIZATIONAL ONLY** (01-, 02-, 03-, 04- folders are for human organization)
- **Execution order is determined by plugin `priority` field** (lower numbers run first)
- **Plugin type determines when they run** (portscan → servicescan → bruteforce → reporting)
- **Service plugins only run if their `conditions` match discovered services**
- **Results from earlier plugins are available to later plugins**

### Template Selection
```bash
# Use existing template
ipcrawler --template default-template target.com

# Create custom template
mkdir -p templates/my-template/01-port-scanning
cp templates/default-template/01-port-scanning/nmap-basic.yaml templates/my-template/01-port-scanning/
# Edit and customize...
```

---

## Quick Start

Create a new YAML plugin in your template directory:

```yaml
metadata:
  name: "My Custom Plugin"
  description: "What this plugin does"
  type: "servicescan"  # or "portscan", "bruteforce", "reporting"
  priority: 10  # Lower numbers run first

conditions:
  services:
    include: ["^http", "^https", "ssl/http"]  # Service name patterns

options:
  - name: "wordlist"
    type: "string"
    default: "auto"
    help: "Wordlist to use"

execution:
  commands:
    - name: "scan_command"
      command: "your_tool -target {address}:{port}"
      timeout: 300

output:
  patterns:
    - pattern: "Found: (.+)"
      description: "Discovery: {match1}"
      severity: "info"

requirements:
  tools:
    - name: "your_tool"
      check_command: "your_tool --version"
```

---

## Step-by-Step Tutorial: Creating Your First Plugin

### 1. Choose Your Plugin Type and Location
```bash
# Create directory structure for your template
mkdir -p templates/my-custom-template/02-service-enumeration/web-services

# Navigate to the plugin directory
cd templates/my-custom-template/02-service-enumeration/web-services
```

### 2. Create Basic Plugin Structure
Create `custom-web-enum.yaml`:
```yaml
metadata:
  name: "My Custom Web Scanner"
  description: "Custom web enumeration plugin"
  type: "servicescan"
  priority: 15

conditions:
  services:
    include: ["^http", "^https", "ssl/http"]

execution:
  commands:
    - name: "web_scan"
      command: "curl -I {url}"
      timeout: 30

output:
  patterns:
    - pattern: "Server: (.+)"
      description: "Web server: {match1}"
      severity: "info"

requirements:
  tools:
    - name: "curl"
      check_command: "curl --version"
```

### 3. Test Your Plugin
```bash
# Test with a single target
ipcrawler --template my-custom-template --target example.com

# Check results
ls results/example.com/
```

### 4. Common Validation Errors and Fixes

**Error**: `Tool 'mytool' not found`
**Fix**: Add tool to requirements section with check_command

**Error**: `No services match conditions`
**Fix**: Check service patterns in conditions.services.include

**Error**: `Command timeout`
**Fix**: Increase timeout value or optimize command

### 5. Plugin Development Checklist
- [ ] Metadata section complete with name, description, type, priority
- [ ] Conditions properly filter target services/ports
- [ ] Commands have appropriate timeouts
- [ ] Output patterns extract useful information
- [ ] Required tools are specified with check commands
- [ ] Plugin tested against target environment

---

## Plugin Structure

### Metadata (Required)
```yaml
metadata:
  name: "Human-readable plugin name"
  description: "What this plugin does"
  type: "portscan|servicescan|bruteforce|reporting"
  priority: 1-100  # Lower = higher priority
  version: "1.0"
  author: "Your Name"
  tags: ["web", "enumeration", "safe"]
```

### Conditions (Required)
```yaml
conditions:
  services:
    include: ["^http", "ssl/http", "^https"]  # Regex patterns
    exclude: ["^nacn_http$"]  # Exclude false positives
  
  ports:
    include: [80, 443, 8080]  # Specific ports
    exclude: [8443]  # Ports to avoid
    ranges: ["8000-8999"]  # Port ranges
  
  protocols:
    include: ["tcp"]  # tcp, udp
    exclude: ["udp"]
  
  when:
    ssl_required: true  # Only HTTPS services
    has_hostname: true  # Only when hostname available
```

---

## Template Variables

IPCrawler provides these variables for command substitution:

### Target Variables
- `{address}` - Target IP address or hostname
- `{target}` - Same as address
- `{ip}` - IP address (resolved if hostname)
- `{scandir}` - Results directory for this target

### Service Variables (for servicescan plugins)
- `{port}` - Port number (e.g., "80")
- `{protocol}` - Protocol (e.g., "tcp", "udp")
- `{service}` - Service name (e.g., "http", "ssl/http")
- `{service_name}` - Same as service
- `{secure}` - "true" if HTTPS/secure, "false" otherwise
- `{http_scheme}` - "https" or "http" based on service
- `{url}` - Full URL (e.g., "https://target.com:443")

### Wordlist Variables
- `{wordlist}` - Resolved wordlist path
- `{resolved_wordlist}` - Same as wordlist (explicit)

### Configuration Variables
- `{nmap_extra}` - Global nmap options
- `{ports_tcp}` - TCP ports to scan
- `{ports_udp}` - UDP ports to scan

---

## Pattern Matching

### Basic Pattern Syntax
```yaml
output:
  patterns:
    - pattern: "Found: (.+)"
      description: "Discovery: {match1}"
      severity: "info"
      category: "discovery"
```

### Regex Pattern Examples

**Port Detection (for portscan plugins):**
```yaml
# Standard nmap port format
pattern: "(\\d+)/(tcp|udp)\\s+open\\s+(\\S+)"
description: "Open Port: {match1}/{match2} - {match3}"

# Detailed port with service info
pattern: "(?i)(\\d+)/(tcp|udp)\\s+open\\s+(\\S+)\\s+(.+)"
description: "Open Port: {match1}/{match2} - {match3} ({match4})"
```

**Web Discovery:**
```yaml
# Directory/file found
pattern: "200\\s+\\d+l\\s+\\d+w\\s+\\d+c\\s+(.*)"
description: "Found directory: {match1}"

# Technology detection
pattern: "(?i)powered.by[:\\s]*([^\\n\\r]+)"
description: "Technology: Powered by {match1}"

# Login page detection
pattern: "(?i)<title>([^<]*(?:login|sign.?in)[^<]*)</title>"
description: "Login page found: {match1}"
```

**Credential Discovery:**
```yaml
# Successful authentication
pattern: "\\[22\\]\\[ssh\\].*login:\\s*(.+).*password:\\s*(.+)"
description: "SSH Login Found: {match1}:{match2}"
severity: "critical"

# Database connection string
pattern: "(?i)(mysql|postgres|mongodb)://([^\\s\"']+)"
description: "Database connection: {match1} - {match2}"
severity: "high"
```

### Pattern Severity Levels
- `info` - Informational findings
- `low` - Minor security issues
- `medium` - Moderate security concerns
- `high` - Significant security issues
- `critical` - Critical security vulnerabilities

---

## Service Detection

For port scan plugins, detect new services:

```yaml
output:
  service_detection:
    - pattern: "^(\\d+)/(tcp|udp)\\s+open\\s+(\\S+)"
      service_name: "{match3}"
    
    # Special handling for specific services
    - pattern: "5985/tcp\\s+open\\s+wsman"
      service_name: "winrm"
      port_override: 5985
    
    # HTTPS detection
    - pattern: "443/tcp\\s+open\\s+ssl/http"
      service_name: "https"
```

---

## Command Examples

### Basic Commands
```yaml
execution:
  commands:
    - name: "simple_scan"
      command: "nmap -sV -p {port} {address}"
      timeout: 300
      description: "Service version scan"
```

### Web Enumeration
```yaml
execution:
  commands:
    - name: "directory_bust"
      command: "feroxbuster -u {url} -w {resolved_wordlist} -t 10"
      timeout: 3600
      description: "Directory enumeration"
    
    - name: "robots_check"
      command: "curl -s {url}/robots.txt"
      timeout: 30
      description: "Check robots.txt"
```

### Conditional Commands
```yaml
execution:
  commands:
    - name: "https_only"
      command: "sslscan {address}:{port}"
      condition: "secure == 'true'"
      timeout: 120
    
    - name: "custom_headers"
      command: "curl -I {url}"
      timeout: 30
      output_file: "{protocol}_{port}_headers.txt"
```

### Multi-step Commands
```yaml
execution:
  commands:
    - name: "complex_scan"
      command: |
        echo "Starting scan of {url}" &&
        curl -s -I {url} > headers.tmp &&
        if grep -q "WordPress" headers.tmp; then
          echo "WordPress detected, using WP wordlist"
          wordlist="/path/to/wordpress.txt"
        else
          wordlist="{resolved_wordlist}"
        fi &&
        feroxbuster -u {url} -w $wordlist
      timeout: 1800
```

---

## Plugin Types

### Port Scan Plugins
```yaml
metadata:
  type: "portscan"
  priority: 1  # Run early

conditions:
  # Usually no service filters for port scans
  services:
    include: []

execution:
  commands:
    - name: "port_scan"
      command: "nmap -sS -T4 --top-ports 1000 {address}"
```

### Service Scan Plugins
```yaml
metadata:
  type: "servicescan"
  priority: 10

conditions:
  services:
    include: ["^http", "^https"]  # Only HTTP services

execution:
  commands:
    - name: "http_enum"
      command: "nikto -h {url}"
```

### Brute Force Plugins
```yaml
metadata:
  type: "bruteforce"
  priority: 50  # Run later

conditions:
  services:
    include: ["^ssh", "^ftp"]

execution:
  commands:
    - name: "credential_attack"
      command: "hydra -L {wordlist_users} -P {wordlist_passwords} {service}://{address}:{port}"
```

---

## Complete Examples

### Web Directory Scanner
```yaml
metadata:
  name: "Advanced Directory Scanner"
  description: "Intelligent directory enumeration with auto wordlists"
  type: "servicescan"
  priority: 5
  tags: ["web", "enumeration", "directories"]

conditions:
  services:
    include: ["^http", "ssl/http", "^https"]
    exclude: ["^nacn_http$"]

options:
  - name: "wordlist"
    type: "string"
    default: "auto"
    help: "Wordlist for directory enumeration"
  - name: "threads"
    type: "integer"
    default: 10
    help: "Number of concurrent threads"
  - name: "extensions"
    type: "string"
    default: "php,html,txt,js"
    help: "File extensions to check"

execution:
  commands:
    - name: "directory_enum"
      command: "feroxbuster -u {url} -w {resolved_wordlist} -t {threads} -x {extensions} -s 200,301,302,403"
      timeout: 3600
      output_file: "{protocol}_{port}_directories.txt"
    
    - name: "robots_txt"
      command: "curl -s {url}/robots.txt"
      timeout: 30
      output_file: "{protocol}_{port}_robots.txt"

output:
  patterns:
    - pattern: "200\\s+\\d+l\\s+\\d+w\\s+\\d+c\\s+(\\S+)"
      description: "Directory found: {match1}"
      severity: "info"
      category: "directory_enumeration"
    
    - pattern: "403\\s+\\d+l\\s+\\d+w\\s+\\d+c\\s+(\\S+)"
      description: "Forbidden directory: {match1}"
      severity: "low"
      category: "directory_enumeration"
    
    - pattern: "(?i)admin|login|dashboard"
      description: "Admin interface detected"
      severity: "medium"
      category: "admin_detection"

requirements:
  tools:
    - name: "feroxbuster"
      check_command: "feroxbuster --version"
      install_hint: "cargo install feroxbuster"
    - name: "curl"
      check_command: "curl --version"
      install_hint: "apt-get install curl"
```

### SSH Service Scanner
```yaml
metadata:
  name: "SSH Service Enumeration"
  description: "SSH service analysis and enumeration"
  type: "servicescan"
  priority: 15

conditions:
  services:
    include: ["^ssh"]
  ports:
    include: [22, 2222]

execution:
  commands:
    - name: "ssh_enum"
      command: "nmap -sV -p {port} --script ssh2-enum-algos,ssh-hostkey,ssh-auth-methods {address}"
      timeout: 300
      output_file: "{protocol}_{port}_ssh_enum.txt"
    
    - name: "ssh_banner"
      command: "nc -nv {address} {port} < /dev/null"
      timeout: 10
      output_file: "{protocol}_{port}_ssh_banner.txt"

output:
  patterns:
    - pattern: "SSH-([0-9\\.]+)-(.+)"
      description: "SSH version: {match1} - {match2}"
      severity: "info"
      category: "version_detection"
    
    - pattern: "(?i)(openssh[^\\s]*)"
      description: "OpenSSH detected: {match1}"
      severity: "info"
      category: "service_identification"

requirements:
  tools:
    - name: "nmap"
      check_command: "nmap --version"
      install_hint: "apt-get install nmap"
    - name: "nc"
      check_command: "nc -h"
      install_hint: "apt-get install netcat"
```

---

## Best Practices

1. **Use descriptive names**: Make plugin names and descriptions clear
2. **Set appropriate priorities**: Port scans (1-10), Service scans (10-40), Brute force (40-60), Reports (60-100)
3. **Include proper conditions**: Use specific service patterns to avoid false triggers
4. **Add timeouts**: Always specify command timeouts to prevent hanging
5. **Validate tools**: Include tool requirements with install hints
6. **Use wordlist option**: Always include wordlist option for plugins that need word lists
7. **Pattern matching**: Use specific regex patterns to extract useful information
8. **Output organization**: Use meaningful output file names and categories

---

## Template Variables Reference

### Available Variables by Plugin Type

**All Plugins:**
- `{address}`, `{target}`, `{ip}`, `{scandir}`

**Service Scan Plugins:**
- All target variables plus: `{port}`, `{protocol}`, `{service}`, `{secure}`, `{http_scheme}`, `{url}`

**Wordlist-enabled Plugins:**
- `{wordlist}`, `{resolved_wordlist}` (auto-resolved or custom path)

### Wordlist Resolution

```yaml
options:
  - name: "wordlist"
    type: "string"
    default: "auto"  # Uses SmartWordlistSelector
    # OR
    default: "data/wordlists/custom.txt"  # Custom path
```

- `auto` - Intelligent wordlist selection based on detected technologies
- `path` - Custom wordlist file path (relative to ipcrawler directory)
- Missing custom wordlists cause immediate failure (fail-fast behavior)

---

## AI Development Guidelines

### Plugin Generation Patterns

**For AI systems creating plugins**, follow these patterns:

1. **Always include all required sections**:
   ```yaml
   metadata:      # REQUIRED
   conditions:    # REQUIRED
   execution:     # REQUIRED
   output:        # REQUIRED (for meaningful plugins)
   requirements:  # REQUIRED if using external tools
   ```

2. **Service condition patterns**:
   ```yaml
   # HTTP services
   conditions:
     services:
       include: ["^http", "^https", "ssl/http"]
   
   # SSH services
   conditions:
     services:
       include: ["^ssh"]
   
   # Database services
   conditions:
     services:
       include: ["^mysql", "^postgresql", "^mongodb"]
   ```

3. **Priority allocation**:
   - Port scanning: 1-10
   - Service enumeration: 10-40
   - Brute force: 40-60
   - Reporting: 60-100

### Validation Rules

**Critical validation checks for AI-generated plugins**:

1. **Schema compliance**: All plugins must validate against `plugin_schema.yaml`
2. **Command syntax**: Use proper variable substitution `{variable}` not `$variable`
3. **Timeout values**: Always specify realistic timeouts (30-3600 seconds)
4. **Tool requirements**: Include check_command for all external tools
5. **Pattern syntax**: Use properly escaped regex patterns

### Common AI Generation Mistakes

❌ **Incorrect variable syntax**:
```yaml
command: "nmap $target"  # Wrong
```
✅ **Correct variable syntax**:
```yaml
command: "nmap {target}"  # Correct
```

❌ **Missing tool requirements**:
```yaml
execution:
  commands:
    - command: "nikto -h {url}"  # Missing requirements
```
✅ **Complete tool requirements**:
```yaml
execution:
  commands:
    - command: "nikto -h {url}"
requirements:
  tools:
    - name: "nikto"
      check_command: "nikto -Version"
```

❌ **Unsafe regex patterns**:
```yaml
pattern: "(.*)"  # Too greedy
```
✅ **Specific regex patterns**:
```yaml
pattern: "Server: ([^\\r\\n]+)"  # Specific match
```

### Template Generation Guidelines

When creating complete templates:

1. **Create phase directories**: `01-port-scanning`, `02-service-enumeration`, etc.
2. **Include basic plugins**: At minimum, include port scanning and service enumeration
3. **Maintain consistency**: Use consistent naming conventions across plugins
4. **Test compatibility**: Ensure plugins work together in the execution pipeline

---

For more examples, see the templates in `/templates/` directory and the plugin schema in `plugin_schema.yaml`.