# IPCrawler Templates

This directory contains YAML templates for various penetration testing tools.

## Template Structure

```yaml
name: tool-name
description: Tool description
enabled: true|false

command:
  binary: executable_name
  args:
    - "arg1"
    - "{{target}}"
    - "{{output_dir}}"

depends_on: []

outputs:
  - pattern: "{{output_dir}}/file.txt"

timeout: 600

env: {}

requires_sudo: false
```

## Variables

- `{{target}}`: The scan target (IP, domain, or URL)
- `{{output_dir}}`: Output directory for this tool

## Sudo Templates

Create sudo variants by appending `-sudo` to the template name:
- `nmap.yaml` - Regular scan
- `nmap-sudo.yaml` - Privileged scan

When running with sudo, IPCrawler will:
1. Prefer `-sudo` variants when available
2. Fall back to regular templates if no sudo variant exists
3. Skip templates with `requires_sudo: true` if not running as root

## Available Templates

- **ping.yaml** - Basic connectivity check
- **nmap.yaml** - Fast TCP port scan (top 1000 ports)
- **nmap-sudo.yaml** - Full SYN scan with service/OS detection
- **nikto.yaml** - Web server vulnerability scanner
- **whatweb.yaml** - Web technology fingerprinting
- **gobuster.yaml** - Directory brute-forcing (disabled by default)

## Creating Custom Templates

1. Create a new `.yaml` file in this directory
2. Follow the structure above
3. Set `enabled: true` to activate
4. Test with: `ipcrawler show template-name`
