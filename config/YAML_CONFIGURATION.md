# ipcrawler YAML Configuration Guide

This document explains how to create custom YAML configuration files for ipcrawler. The tool is designed to be completely flexible - **no tools are hardcoded**. You can add any command-line tool by simply defining it in YAML.

## Configuration Structure

### Complete YAML Template

```yaml
metadata:
  name: "Your Profile Name"
  description: "Description of what this profile does"
  version: "1.0"

tools:
  - name: "tool_identifier"
    command: "actual_command_to_run {target} {output}"
    timeout: 120
    output_file: "filename.txt"
    enabled: true

chains:
  - name: "chain_name"
    from: "first_tool"
    to: "second_tool" 
    condition: "has_output"

globals:
  max_concurrent: 10
  retry_count: 2
  log_level: "info"
```

## Section Breakdown

### 1. Metadata Section (Required)

```yaml
metadata:
  name: "Profile Display Name"          # String: Shows in --list output
  description: "What this profile does"  # String: Detailed description
  version: "1.0"                        # String: Version tracking
```

### 2. Tools Section (Required)

Each tool is defined with these fields:

```yaml
tools:
  - name: "unique_tool_name"           # String: Unique identifier (used in chains)
    command: "tool_command_here"       # String: Actual command to execute
    timeout: 300                       # Number: Seconds before timeout
    output_file: "output_filename"     # String: Where tool saves results
    enabled: true                      # Boolean: Whether to run this tool
```

#### Available Variables

ipcrawler automatically replaces these variables in your commands:

- `{target}` - The target IP/hostname provided with `-t`
- `{output}` - The output directory path
- `{discovered_ports}` - Comma-separated ports from previous tools (for chaining)

#### Tool Examples

```yaml
# Port scanner
- name: "nmap_scan"
  command: "nmap -sS -T4 {target} -oX {output}/nmap.xml"
  timeout: 600
  output_file: "nmap.xml"
  enabled: true

# Web scanner  
- name: "nikto_scan"
  command: "nikto -h {target} -output {output}/nikto.txt"
  timeout: 300
  output_file: "nikto.txt"
  enabled: true

# Directory bruteforce
- name: "gobuster_dirs"
  command: "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -o {output}/gobuster.txt"
  timeout: 900
  output_file: "gobuster.txt"
  enabled: true

# Custom script
- name: "custom_recon"
  command: "/path/to/your/script.sh {target} {output}"
  timeout: 120
  output_file: "custom_results.txt"
  enabled: true
```

### 3. Chains Section (Optional)

Chains allow you to connect tools so one runs after another based on conditions:

```yaml
chains:
  - name: "descriptive_chain_name"
    from: "first_tool_name"      # Tool that runs first
    to: "second_tool_name"       # Tool that runs after
    condition: "trigger_type"    # When to trigger second tool
```

#### Available Conditions

- `"has_output"` - Run if first tool produced any output file
- `"exit_success"` - Run if first tool exited successfully (exit code 0)
- `"contains"` - Run if first tool's output contains specific text
- `"file_size"` - Run if output file is larger than X bytes

#### Chain Examples

```yaml
chains:
  # Run nmap on ports discovered by naabu
  - name: "port_discovery_to_service_scan"
    from: "naabu_scan"
    to: "nmap_service_scan"
    condition: "has_output"
    
  # Run directory scan if web server is detected
  - name: "web_to_dirs"
    from: "nmap_scan"
    to: "gobuster_dirs"
    condition: "exit_success"
```

### 4. Globals Section (Required)

```yaml
globals:
  max_concurrent: 10        # Number: Maximum tools running simultaneously
  retry_count: 2           # Number: How many times to retry failed tools
  log_level: "info"        # String: "trace", "debug", "info", "warn", "error"
```

## Adding Any Tool

ipcrawler can run **ANY** command-line tool. Here's how to add tools:

### 1. Network Tools
```yaml
# Masscan - Fast port scanner
- name: "masscan"
  command: "masscan {target} -p1-65535 --rate=1000 -oX {output}/masscan.xml"
  timeout: 300
  output_file: "masscan.xml"
  enabled: true

# Zmap - Internet-wide scanner
- name: "zmap"
  command: "zmap -p 80 {target}/24 -o {output}/zmap.txt"
  timeout: 600
  output_file: "zmap.txt"
  enabled: true
```

### 2. Web Tools
```yaml
# Whatweb - Web technology detection
- name: "whatweb"
  command: "whatweb {target} -a 3 --log-brief={output}/whatweb.txt"
  timeout: 120
  output_file: "whatweb.txt"
  enabled: true

# Ffuf - Web fuzzer
- name: "ffuf"
  command: "ffuf -w /usr/share/wordlists/dirb/common.txt -u http://{target}/FUZZ -o {output}/ffuf.json"
  timeout: 300
  output_file: "ffuf.json"
  enabled: true
```

### 3. Custom Scripts
```yaml
# Python script
- name: "custom_python"
  command: "python3 /path/to/script.py --target {target} --output {output}/custom.json"
  timeout: 180
  output_file: "custom.json"
  enabled: true

# Bash script
- name: "custom_bash"
  command: "/home/user/scripts/recon.sh {target} > {output}/custom_recon.txt"
  timeout: 240
  output_file: "custom_recon.txt"
  enabled: true
```

## File Locations

Configuration files can be placed in:

1. **Project configs**: `./config/your_profile.yaml`
2. **User profiles**: `~/.config/ipcrawler/profiles/your_profile.yaml`
3. **System templates**: `/usr/local/share/ipcrawler/your_profile.yaml`

## Usage Examples

```bash
# Use your custom profile
ipcrawler -t target.com -c your_profile

# Multiple profiles
ipcrawler -t target.com -c quick_scan,web_scan,custom_profile

# Validate before running
ipcrawler --validate -c your_profile
```

## Best Practices

1. **Tool Names**: Use descriptive, unique names without spaces
2. **Timeouts**: Set realistic timeouts based on tool complexity
3. **Output Files**: Use descriptive filenames with proper extensions
4. **Commands**: Always test commands manually first
5. **Chaining**: Chain related tools for efficient workflows
6. **Error Handling**: Enable `retry_count` for network-dependent tools

## Validation

Always validate your YAML before running:

```bash
# Validate syntax and tool availability
ipcrawler --validate -c your_profile

# Check which tools are available on your system
ipcrawler --doctor
```

## Example: Complete Custom Profile

```yaml
metadata:
  name: "CTF Web Box"
  description: "Comprehensive scan for web-focused CTF machines"
  version: "1.0"

tools:
  - name: "port_discovery"
    command: "nmap -sS --top-ports 1000 {target} -oX {output}/nmap_ports.xml"
    timeout: 300
    output_file: "nmap_ports.xml"
    enabled: true
    
  - name: "service_detection"
    command: "nmap -sV -sC {target} -p {discovered_ports} -oX {output}/nmap_services.xml"
    timeout: 600
    output_file: "nmap_services.xml"
    enabled: true
    
  - name: "web_tech"
    command: "whatweb {target} -a 3 --log-brief={output}/whatweb.txt"
    timeout: 120
    output_file: "whatweb.txt"
    enabled: true
    
  - name: "dir_brute"
    command: "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/big.txt -x php,html,txt -o {output}/gobuster.txt"
    timeout: 900
    output_file: "gobuster.txt"
    enabled: true

chains:
  - name: "ports_to_services"
    from: "port_discovery"
    to: "service_detection"
    condition: "has_output"
    
  - name: "services_to_web"
    from: "service_detection"
    to: "web_tech"
    condition: "exit_success"
    
  - name: "web_to_dirs"
    from: "web_tech"
    to: "dir_brute"
    condition: "has_output"

globals:
  max_concurrent: 5
  retry_count: 1
  log_level: "info"
```

This configuration would:
1. Discover open ports with nmap
2. Get detailed service info on discovered ports
3. Identify web technologies if services are found
4. Brute force directories if web server is detected

**Remember**: ipcrawler is tool-agnostic. You can add any command-line tool simply by defining it in YAML!