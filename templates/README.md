# IPCrawler Templates

This directory contains YAML templates for various penetration testing tools.

## Template Structure

```yaml
name: tool-name
description: Tool description
enabled: true            # Optional, defaults to true
pre_scan: false          # Optional, runs before main scan

command:
  binary: executable_name
  args:
    - "arg1"
    - "{{target}}"
    - "{{output_dir}}"

depends_on: []           # Optional, list of template names this depends on

outputs:                 # Optional, output file patterns
  - pattern: "{{output_dir}}/file.txt"

timeout: 600            # Optional, seconds, defaults to 3600

env: {}                 # Optional, environment variables

requires_sudo: false    # Optional, defaults to false

parsing:                # Optional, parsing configuration
  method: llm           # llm (default), regex, or none
  regex_patterns: []    # Optional, custom regex patterns
```

## Available Variables

All template arguments can use these variables:

- `{{target}}`: The scan target (IP, domain, or URL)
- `{{output_dir}}`: Output directory for this tool's results
- `{{ports}}`: Port specification (e.g., "-p 80,443" or "--top-ports 1000")
- `{{wordlist}}`: Path to wordlist file (for directory brute-forcing, etc.)

## Output Parsing

IPCrawler can parse tool outputs using three methods:

### 1. LLM Parsing (Default)
**Best for:** Complex outputs, vulnerability scanners, tools with varied formats

```yaml
parsing:
  method: llm
```

- Uses AI to extract structured data from unstructured output
- Supports multi-pass consistency checking
- Extracts IPs, domains, URLs, ports, vulnerabilities, and findings
- Requires LLM API key (Groq, OpenAI, Anthropic, or Ollama)
- **Cost:** API tokens per parse
- **Speed:** Slower (API calls)

### 2. Regex Parsing
**Best for:** High-volume output, directory/file enumeration tools

```yaml
parsing:
  method: regex
```

- Fast, deterministic pattern matching
- No API costs or token usage
- Built-in patterns for: `gobuster`, `ffuf`, `feroxbuster`, `dirb`, `dirsearch`
- Generic URL extraction fallback for other tools
- **Cost:** Free
- **Speed:** Instant

**Custom Regex Patterns:**
```yaml
parsing:
  method: regex
  regex_patterns:
    - pattern: "^(https?://[^\s]+)"
      extract_as: "url"
    - pattern: "Status: (\d+)"
      extract_as: "finding"
    - pattern: "^([0-9.]+)"
      extract_as: "ip"
```

Supported `extract_as` values: `url`, `domain`, `ip`, `finding`

### 3. No Parsing
**Best for:** Tools with outputs you'll review manually

```yaml
parsing:
  method: none
```

- Skips all parsing
- Output saved to raw files only
- Useful for verbose tools or when manual review is preferred

### Choosing a Parsing Method

| Tool Type | Recommended Method | Why |
|-----------|-------------------|-----|
| Directory brute-forcing (gobuster, ffuf, feroxbuster) | `regex` | Massive output, simple patterns |
| Vulnerability scanners (nikto, nuclei) | `llm` | Complex findings, varied formats |
| Port scanners (nmap) | `llm` | Service detection, version info |
| DNS tools (dig) | `llm` | Varied record types |
| Verbose/debugging tools | `none` | Manual review needed |

## Template Execution Order

Templates can be marked as pre-scan or main scan:

- **pre_scan: true** - Runs before main scanning (e.g., DNS enumeration, quick hostname discovery)
- **pre_scan: false** (default) - Runs during main scan phase

Pre-scan templates are useful for gathering information that might be needed by later scans.

## Sudo Templates

Create sudo variants by appending `-sudo` to the template name:
- `nmap.yaml` - Regular scan
- `nmap-sudo.yaml` - Privileged scan

When running with sudo, IPCrawler will:
1. Prefer `-sudo` variants when available
2. Fall back to regular templates if no sudo variant exists
3. Skip templates with `requires_sudo: true` if not running as root

## Available Templates

### Network & Discovery
- **ping.yaml** - Basic connectivity check (LLM parsing)
- **traceroute.yaml** - Network path mapping (LLM parsing, pre-scan)
- **nmap.yaml** - Fast TCP port scan, top 1000 ports (LLM parsing)
- **nmap-sudo.yaml** - Full SYN scan with service/OS detection (LLM parsing, requires sudo)

### DNS & Hostname Discovery
- **dig.yaml** - Comprehensive DNS reconnaissance (LLM parsing, pre-scan)
- **hostname-discovery.yaml** - SSL certificate hostname extraction (LLM parsing, pre-scan)
- **reverse-dns.yaml** - PTR record lookups (LLM parsing, pre-scan)

### Web Application Scanning
- **nikto.yaml** - Web server vulnerability scanner (LLM parsing)
- **whatweb.yaml** - Web technology fingerprinting (LLM parsing)
- **nuclei.yaml** - Modern vulnerability scanner with templates (LLM parsing)
- **nuclei-cve.yaml** - CVE-focused scanning (LLM parsing, disabled)
- **nuclei-tech.yaml** - Technology detection (LLM parsing, disabled)

### Directory & File Enumeration
- **gobuster.yaml** - Directory brute-forcing (Regex parsing)
- **ffuf-directory.yaml** - Fast fuzzing with recursion (Regex parsing)
- **ffuf-vhost.yaml** - Virtual host discovery (Regex parsing, disabled)
- **ffuf-subdomain.yaml** - Subdomain enumeration (Regex parsing, disabled)
- **ffuf-parameters.yaml** - GET parameter fuzzing (Regex parsing, disabled)

### SMB & Windows Enumeration
- **enum4linux-ng.yaml** - SMB/Samba enumeration (LLM parsing)
- **smbmap.yaml** - SMB share enumeration with file listing (LLM parsing)

### Service-Specific
- **snmpwalk.yaml** - SNMP enumeration with community strings (LLM parsing)
- **snmp-check.yaml** - Alternative SNMP enumeration (LLM parsing, disabled)
- **ssh-audit.yaml** - SSH security audit (LLM parsing)

## Creating Custom Templates

**IPCrawler automatically discovers and loads all `.yaml` files in this directory.**

No code changes are required - just add your template file!

### Steps:

1. **Create a new `.yaml` file** in the `templates/` directory
   - Name it descriptively: `mytool.yaml`
   - For sudo variant: `mytool-sudo.yaml`

2. **Follow the template structure** (see above)
   - All fields except `name`, `description`, and `command` are optional
   - Use template variables in your arguments

3. **Set enabled status** (optional)
   - `enabled: true` - Template will run automatically
   - `enabled: false` - Template available but won't run by default

4. **Test your template**
   ```bash
   # Show template details
   ipcrawler show mytool
   
   # Run specific template
   ipcrawler scan <target> --template mytool
   ```

5. **Verify it works**
   ```bash
   # List all available templates
   ipcrawler list
   ```

### Example 1: Custom Nikto Template with LLM Parsing

```yaml
name: nikto-full
description: Comprehensive web vulnerability scan with all tests
enabled: false

command:
  binary: nikto
  args:
    - "-h"
    - "{{target}}"
    - "-o"
    - "{{output_dir}}/nikto_full.txt"
    - "-Tuning"
    - "x"
    - "-Display"
    - "V"

outputs:
  - pattern: "{{output_dir}}/nikto_full.txt"

timeout: 3600

requires_sudo: false

parsing:
  method: llm  # Complex vulnerability output, best for LLM
```

### Example 2: Custom Dirsearch Template with Regex Parsing

```yaml
name: dirsearch
description: Fast directory brute-forcing with dirsearch
enabled: true

command:
  binary: dirsearch
  args:
    - "-u"
    - "{{target}}"
    - "-w"
    - "{{wordlist}}"
    - "-o"
    - "{{output_dir}}/dirsearch_results.txt"

outputs:
  - pattern: "{{output_dir}}/dirsearch_results.txt"

timeout: 1800

requires_sudo: false

parsing:
  method: regex  # High-volume output, regex is faster and cheaper
```

### Example 3: Custom Template with Custom Regex Patterns

```yaml
name: custom-scanner
description: Custom scanner with specific output format
enabled: true

command:
  binary: my-scanner
  args:
    - "--target"
    - "{{target}}"

timeout: 600

parsing:
  method: regex
  regex_patterns:
    - pattern: "Found URL: (https?://[^\s]+)"
      extract_as: "url"
    - pattern: "IP Address: ([0-9.]+)"
      extract_as: "ip"
    - pattern: "Domain: ([a-zA-Z0-9.-]+)"
      extract_as: "domain"
    - pattern: "FINDING: (.+)"
      extract_as: "finding"
```

Save these as `.yaml` files in `templates/` and they're immediately available!
