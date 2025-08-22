# Rust Reconnaissance Tool - Complete Workflow Guide

## Overview

The Rust Reconnaissance Tool is a powerful, async reconnaissance automation platform that executes security tools in parallel and chains them together based on results. It supports YAML-based configuration, real-time output capture, and intelligent tool chaining.

## Project Structure

```
ipcrawler-rust/
├── Cargo.toml                 # Dependencies and project metadata
├── src/
│   ├── main.rs               # Main entry point and CLI handling
│   ├── cli.rs                # Command-line argument parsing
│   ├── config.rs             # YAML configuration parsing and validation
│   ├── executor.rs           # Async tool execution engine
│   ├── pipeline.rs           # Tool chaining and dependency resolution
│   └── output.rs             # Output management (placeholder)
├── config/
│   ├── default.yaml          # Default reconnaissance profile
│   ├── fast_chain.yaml       # Fast chaining test configuration
│   ├── test.yaml             # Safe test commands
│   └── chain_test.yaml       # Advanced chaining example
└── results/                  # Generated at runtime
    └── {target}_{timestamp}/
        ├── logs/
        │   └── execution.log # Complete execution timeline
        ├── raw/              # Raw tool outputs
        │   ├── tool1.out
        │   ├── tool2.xml
        │   └── ...
        └── errors/           # Tool error outputs
            ├── tool1.err
            └── ...
```

## CLI Usage

### Basic Commands

```bash
# Validate configuration
cargo run -- --validate

# Simple target scan with default config
cargo run -- --target example.com

# Scan with custom config and verbose output
cargo run -- --target example.com --config config/fast_chain.yaml --verbose

# Debug mode with detailed information
cargo run -- --target 192.168.1.1 --debug

# Custom output directory
cargo run -- --target example.com --output /tmp/scan_results/
```

### CLI Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--target` | `-t` | IP address or hostname to scan | Required* |
| `--config` | `-c` | YAML config file path | `config/default.yaml` |
| `--output` | `-o` | Output directory | `results/` |
| `--debug` | `-d` | Enable debug mode | `false` |
| `--verbose` | `-v` | Verbose output | `false` |
| `--validate` | | Validate config and exit | `false` |
| `--help` | `-h` | Show help message | |

*Required unless using `--validate`

## YAML Configuration Structure

### Complete Configuration Schema

```yaml
metadata:
  name: "Profile Name"                    # Human-readable profile name
  description: "Profile description"     # What this profile does
  version: "1.0"                        # Profile version

tools:
  - name: "tool_name"                    # Unique tool identifier
    command: "command {target} {output}" # Command with template variables
    timeout: 60                         # Timeout in seconds
    output_file: "filename.txt"         # Expected output filename
    enabled: true                       # Whether to execute this tool

chains:
  - name: "chain_name"                   # Chain identifier
    from: "source_tool"                 # Source tool name
    to: "target_tool"                   # Target tool name  
    condition: "has_output"             # Chain condition

globals:
  max_concurrent: 3                     # Maximum concurrent tools
  retry_count: 2                       # Retry attempts for failed tools
  log_level: "info"                    # Log level (trace|debug|info|warn|error)
```

### Template Variables

Variables automatically replaced during execution:

- `{target}` → Actual target (IP/hostname)
- `{output}` → Full path to output directory
- `{discovered_ports}` → Comma-separated ports from chained tools

### Chain Conditions

Supported conditions for tool chaining:

- `has_output` → Previous tool produced output
- `exit_success` → Previous tool exited with code 0
- `file_size` → Output file has non-zero size
- `contains` → Output contains specific text (future)

## Execution Modes

### 1. Simple Execution (No Chains)

When `chains: []` is empty, tools run in parallel:

```yaml
tools:
  - name: "nmap"
    command: "nmap -sV {target}"
    timeout: 300
    enabled: true
  - name: "nikto"  
    command: "nikto -h {target}"
    timeout: 180
    enabled: true

chains: []  # Empty = parallel execution
```

**Behavior**: Both tools run simultaneously up to `max_concurrent` limit.

### 2. Chained Execution

When chains are defined, tools run sequentially based on dependencies:

```yaml
tools:
  - name: "naabu"
    command: "naabu -host {target} -o {output}/raw/ports.txt"
    timeout: 60
    enabled: true
    
  - name: "nmap"
    command: "nmap -sV {target} -p {discovered_ports}"
    timeout: 300
    enabled: true

chains:
  - name: "port_discovery"
    from: "naabu" 
    to: "nmap"
    condition: "has_output"
```

**Behavior**: 
1. naabu runs first
2. If naabu produces output, nmap runs with discovered ports
3. If naabu fails/no output, nmap is skipped

## Configuration Examples

### Example 1: Fast Port Discovery Chain

```yaml
# config/fast_discovery.yaml
metadata:
  name: "Fast Port Discovery"
  description: "Quick port scan followed by detailed service detection"
  version: "1.0"

tools:
  - name: "naabu_fast"
    command: "naabu -host {target} -top-ports 1000 -o {output}/raw/ports.txt"
    timeout: 60
    output_file: "ports.txt"
    enabled: true
    
  - name: "nmap_detailed"
    command: "nmap -sV -sC -T4 {target} -p {discovered_ports} -oX {output}/raw/detailed.xml"
    timeout: 300
    output_file: "detailed.xml"
    enabled: true

chains:
  - name: "discovery_to_detail"
    from: "naabu_fast"
    to: "nmap_detailed" 
    condition: "has_output"

globals:
  max_concurrent: 2
  retry_count: 1
  log_level: "info"
```

### Example 2: Web Application Testing

```yaml
# config/webapp_scan.yaml
metadata:
  name: "Web Application Scan"
  description: "HTTP service discovery and web application testing"
  version: "1.0"

tools:
  - name: "http_discovery"
    command: "httpx -u {target} -o {output}/raw/http_services.txt"
    timeout: 30
    output_file: "http_services.txt"
    enabled: true
    
  - name: "nikto_scan"
    command: "nikto -h {target} -o {output}/raw/nikto_report.txt"
    timeout: 600
    output_file: "nikto_report.txt"
    enabled: true
    
  - name: "gobuster_dirs"
    command: "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -o {output}/raw/directories.txt"
    timeout: 300
    output_file: "directories.txt"
    enabled: true

chains:
  - name: "http_to_nikto"
    from: "http_discovery"
    to: "nikto_scan"
    condition: "has_output"
    
  - name: "http_to_gobuster"
    from: "http_discovery"
    to: "gobuster_dirs"
    condition: "has_output"

globals:
  max_concurrent: 2
  retry_count: 1
  log_level: "info"
```

### Example 3: Safe Testing Configuration

```yaml
# config/test_safe.yaml
metadata:
  name: "Safe Test Commands"
  description: "Non-invasive commands for testing"
  version: "1.0"

tools:
  - name: "ping_test"
    command: "ping -c 4 {target}"
    timeout: 10
    output_file: "ping.txt"
    enabled: true
    
  - name: "dns_lookup"
    command: "nslookup {target}"
    timeout: 5
    output_file: "dns.txt"  
    enabled: true
    
  - name: "whois_lookup"
    command: "whois {target}"
    timeout: 10
    output_file: "whois.txt"
    enabled: true

chains: []  # Run all in parallel

globals:
  max_concurrent: 3
  retry_count: 0
  log_level: "debug"
```

## Workflow Execution Steps

### 1. Configuration Loading
```bash
cargo run -- --target example.com --config config/custom.yaml
```

1. Validates YAML syntax
2. Checks required fields
3. Validates tool references in chains
4. Replaces `{target}` and `{output}` variables

### 2. Execution Decision

**No Chains (Simple Mode)**:
- All enabled tools execute in parallel
- Respects `max_concurrent` limit
- No dependency resolution

**With Chains (Pipeline Mode)**:
- Builds dependency graph
- Executes tools in dependency order
- Evaluates chain conditions
- Updates dependent tool commands with results

### 3. Tool Execution

Each tool execution includes:
- Process spawning with timeout
- Real-time stdout/stderr capture
- Progress bar with live updates
- Structured logging to files
- Exit code and duration tracking

### 4. Output Management

**Directory Structure**:
```
results/{target}_{YYYY-MM-DD_HH-MM-SS}/
├── logs/execution.log        # Complete execution timeline
├── raw/                      # Tool outputs
│   ├── tool1.out            # stdout
│   ├── tool1.xml            # structured output
│   └── ...
└── errors/                   # Error outputs
    ├── tool1.err            # stderr
    └── ...
```

**Log Format**:
```
[2025-08-20 22:58:33] INFO: Starting tool execution
[2025-08-20 22:58:33] Executing: nmap -sV example.com
[2025-08-20 22:59:45] Tool nmap completed in 72.5s with exit code 0
```

## Advanced Features

### Chain Condition Evaluation

```yaml
chains:
  - name: "conditional_scan"
    from: "port_scanner"
    to: "service_scanner"
    condition: "has_output"  # Only run if ports found
```

**Condition Types**:
- `has_output`: File size > 0 bytes
- `exit_success`: Exit code = 0
- `file_size`: Output file exists and has content

### Port Format Conversion

The pipeline automatically converts between tool formats:

**naabu output** (`host:port`):
```
example.com:80
example.com:443
example.com:8080
```

**nmap input** (comma-separated):
```
80,443,8080
```

### Graceful Interruption

- `Ctrl+C` detection and graceful shutdown
- Running tools complete current operations
- Progress saved to logs
- Clean resource cleanup

### Error Handling and Retries

```yaml
globals:
  retry_count: 2  # Retry failed tools up to 2 times
```

**Retry Logic**:
1. Tool fails → Wait 2 seconds
2. Retry with same command
3. If still fails and retry_count > 0, try again
4. After max retries, mark as failed

## Troubleshooting

### Common Issues

**1. Tool Not Found**
```
Error: No such file or directory (os error 2)
```
**Solution**: Install the required tool or update the command path.

**2. Permission Denied**
```
Error: Permission denied (os error 13)
```
**Solution**: Run with appropriate permissions or modify tool commands.

**3. Configuration Validation Errors**
```
Error: Tool 'nmap_scan' command cannot be empty
```
**Solution**: Check YAML syntax and ensure all required fields are present.

**4. Chain Dependencies**
```
[PIPELINE] ⚠ No tools ready to execute - checking for circular dependencies
```
**Solution**: Verify chain dependencies don't create loops.

### Debug Mode

Use `--debug` for detailed information:
```bash
cargo run -- --target example.com --debug
```

**Debug Output Includes**:
- Target and configuration details
- Tool execution counts
- Total execution duration
- File paths and settings

### Validation Mode

Test configurations without execution:
```bash
cargo run -- --validate --config config/custom.yaml
```

**Validation Checks**:
- YAML syntax
- Required fields
- Tool command validity
- Chain reference integrity
- Timeout and concurrency limits

## Performance Tuning

### Concurrent Execution
```yaml
globals:
  max_concurrent: 5  # Run up to 5 tools simultaneously
```

**Recommendations**:
- CPU-bound tools: `max_concurrent = CPU cores`
- Network tools: `max_concurrent = 2-4x CPU cores`
- Mixed workloads: Start with `max_concurrent = 3`

### Timeout Settings
```yaml
tools:
  - name: "fast_scan"
    timeout: 30      # Quick scans
  - name: "deep_scan"  
    timeout: 1800    # Thorough scans (30 minutes)
```

### Memory Considerations

Large output files are streamed to disk in real-time to minimize memory usage. The tool can handle multi-gigabyte outputs without memory issues.

## Integration Examples

### CI/CD Pipeline
```yaml
# .github/workflows/security-scan.yml
- name: Run Security Scan
  run: |
    cargo run -- --target ${{ env.TARGET_HOST }} --config config/ci_scan.yaml
    # Upload results artifacts
```

### Automated Monitoring
```bash
#!/bin/bash
# scheduled_scan.sh
TARGETS=("host1.com" "host2.com" "host3.com")
for target in "${TARGETS[@]}"; do
  cargo run -- --target "$target" --config config/monitoring.yaml
done
```

### Custom Tool Integration
```yaml
tools:
  - name: "custom_scanner"
    command: "/path/to/custom/tool --target {target} --output {output}/raw/custom.json"
    timeout: 300
    output_file: "custom.json"
    enabled: true
```

## Interactive Summary Viewing

After scan completion, ipcrawler provides an enhanced interactive experience for viewing results:

### Enhanced Output Features

```bash
📁 Results Location
Mode: Development Mode
Path: ./recon-results/target_2024-08-21_15-30-45
Generated Reports:
  • scan_summary.json -> Structured data with raw outputs
  • scan_summary.html -> Interactive web report  
  • scan_summary.md   -> Documentation format
  • scan_summary.txt  -> Terminal-friendly summary

📖 Do you want to view the markdown summary? [y/N]: y
Opening markdown summary in new terminal window...
✅ Markdown summary opened in new terminal window (130x60)
```

### See Integration Features

**Installation**: 
```bash
cargo install see-cat
```

**Capabilities**:
- **New Terminal Window**: Automatically opens in 130×60 character window
- **Syntax Highlighting**: Code blocks and structured data are highlighted
- **Line Numbers**: Easy reference with numbered lines
- **Cross-Platform**: Works on macOS (Terminal.app), Linux (gnome-terminal, xterm)
- **Stay-Open Prompt**: Window remains open until manually closed

### Platform-Specific Behavior

**macOS**: Uses AppleScript to open new Terminal.app window with precise sizing
```bash
# Behind the scenes command:
osascript -e "tell application \"Terminal\" to do script \"see --show-line-numbers=true '/path/to/scan_summary.md'; read -p 'Press Enter to close...'\"" -e "tell application \"Terminal\" to set bounds of front window to {100, 100, 1400, 800}"
```

**Linux**: Detects and uses available terminal emulators
```bash
# gnome-terminal example:
gnome-terminal --geometry=130x60 -- bash -c "see --show-line-numbers=true '/path/to/scan_summary.md'; read -p 'Press Enter to close...'"
```

**Fallback**: If terminal window creation fails or `see` isn't installed, gracefully falls back to current terminal viewing.

### Usage in Workflows

```bash
# Standard scan with interactive viewing
cargo run -- --target example.com --verbose

# Batch processing (auto-declines interactive prompts)
echo "n" | cargo run -- --target example.com
```

This workflow guide provides complete documentation for using the Rust Reconnaissance Tool effectively in various scenarios, from simple scans to complex chained reconnaissance workflows with modern interactive result viewing.