# ipcrawler Templates

This directory contains YAML templates for various reconnaissance tools.

## Template Structure

Each template is a YAML file that defines:
- Tool name and description
- Command to execute with arguments
- Dependencies on other templates
- Output file patterns
- Timeout and environment variables

## Variables

Templates support variable substitution:
- `{{target}}` - Target IP or hostname from CLI
- `{{output_dir}}` - Output directory from CLI
- `{{template_name}}` - Name of the current template

## Example Template

```yaml
name: nmap
description: Network port scanner
enabled: true

command:
  binary: nmap
  args:
    - "-sV"
    - "-p-"
    - "-oA"
    - "{{output_dir}}/nmap/{{target}}"
    - "{{target}}"

depends_on: []

outputs:
  - pattern: "{{output_dir}}/nmap/*.xml"

timeout: 3600

env: {}
```

## Available Templates

- **nmap.yaml** - Full port scan with service detection
- **nmap-quick.yaml** - Quick scan of top 1000 ports
- **ping.yaml** - Basic connectivity test
- **naabu.yaml** - Fast Go-based port scanner (disabled by default)
- **gobuster.yaml** - Web directory brute-forcer (disabled by default)
- **nikto.yaml** - Web vulnerability scanner (disabled by default)
- **whatweb.yaml** - Web technology identifier (disabled by default)

## Creating Custom Templates

1. Create a new YAML file in this directory
2. Follow the structure above
3. Set `enabled: true` to activate
4. Use `depends_on` to specify execution order

## Enabling/Disabling Templates

Set `enabled: false` to disable a template without deleting it.

## Dependencies

Use `depends_on` to create execution chains:

```yaml
name: gobuster
depends_on: [nmap]  # Runs after nmap completes
```
