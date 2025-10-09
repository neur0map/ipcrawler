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
```

## Available Variables

All template arguments can use these variables:

- `{{target}}`: The scan target (IP, domain, or URL)
- `{{output_dir}}`: Output directory for this tool's results
- `{{ports}}`: Port specification (e.g., "-p 80,443" or "--top-ports 1000")
- `{{wordlist}}`: Path to wordlist file (for directory brute-forcing, etc.)

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

- **ping.yaml** - Basic connectivity check
- **nmap.yaml** - Fast TCP port scan (top 1000 ports)
- **nmap-sudo.yaml** - Full SYN scan with service/OS detection
- **nikto.yaml** - Web server vulnerability scanner
- **whatweb.yaml** - Web technology fingerprinting
- **gobuster.yaml** - Directory brute-forcing (disabled by default)

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

### Example: Creating a Custom Nikto Template

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
```

Save this as `templates/nikto-full.yaml` and it's immediately available!
