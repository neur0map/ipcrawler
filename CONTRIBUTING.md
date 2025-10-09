# Contributing to IPCrawler

Thank you for your interest in contributing to IPCrawler! This document provides guidelines and instructions for different types of contributions.

## Table of Contents

- [Contributing Templates](#contributing-templates)
- [Contributing Code](#contributing-code)
- [Reporting Issues](#reporting-issues)
- [Development Setup](#development-setup)

## Contributing Templates

**IPCrawler's template system requires ZERO code changes to add new tools!**

Templates are automatically discovered and loaded from the `templates/` directory.

### Quick Start: Adding a New Template

1. **Create a YAML file** in the `templates/` directory:
   ```bash
   cd templates/
   nano mytool.yaml
   ```

2. **Use this template structure**:
   ```yaml
   name: mytool
   description: Brief description of what this tool does
   enabled: true            # Optional, defaults to true
   pre_scan: false          # Optional, runs before main scan if true
   
   command:
     binary: mytool         # The executable name
     args:
       - "--flag"
       - "{{target}}"
       - "-o"
       - "{{output_dir}}/output.txt"
   
   depends_on: []           # Optional, list of template names this depends on
   
   outputs:                 # Optional, output file patterns
     - pattern: "{{output_dir}}/output.txt"
   
   timeout: 600            # Optional, seconds, defaults to 3600
   
   env: {}                 # Optional, environment variables
   
   requires_sudo: false    # Optional, defaults to false
   ```

3. **Test your template**:
   ```bash
   # List all templates (yours should appear)
   ipcrawler list
   
   # Show template details
   ipcrawler show mytool
   
   # Run it against a test target
   ipcrawler scan example.com --template mytool
   ```

4. **Submit a pull request** (see [Contributing Code](#contributing-code))

### Template Variables

Use these variables in your `args` section:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{target}}` | The scan target | `192.168.1.1`, `example.com`, `https://example.com` |
| `{{output_dir}}` | Output directory for results | `/tmp/ipcrawler_scan_123/mytool` |
| `{{ports}}` | Port specification | `-p 80,443` or `--top-ports 1000` |
| `{{wordlist}}` | Path to wordlist file | `/usr/share/wordlists/dirb/common.txt` |

### Template Best Practices

#### 1. Naming Conventions

- **Regular template**: `toolname.yaml`
- **Privileged variant**: `toolname-sudo.yaml`
- Use lowercase and hyphens
- Keep names descriptive but concise

#### 2. Enable/Disable Strategy

```yaml
# Enable by default for fast, safe scans
enabled: true

# Disable by default for:
# - Slow scans (e.g., full port scans)
# - Noisy scans (e.g., brute-forcing)
# - Specialized scans (e.g., specific vulnerabilities)
enabled: false
```

#### 3. Pre-Scan vs Main Scan

```yaml
# Use pre_scan: true for information gathering
pre_scan: true  # DNS enumeration, hostname discovery

# Use pre_scan: false (default) for main scanning
pre_scan: false  # Port scanning, web scanning
```

#### 4. Sudo Templates

When a tool has both regular and privileged modes:

**templates/nmap.yaml** (regular):
```yaml
name: nmap
description: Fast TCP port scan (non-privileged)
enabled: true

command:
  binary: nmap
  args:
    - "-sT"  # TCP connect scan (no root needed)
    - "{{target}}"
```

**templates/nmap-sudo.yaml** (privileged):
```yaml
name: nmap
description: SYN scan with service detection (requires root)
enabled: true

command:
  binary: nmap
  args:
    - "-sS"  # SYN scan (requires root)
    - "-sV"  # Service detection
    - "{{target}}"

requires_sudo: true
```

IPCrawler automatically:
- Prefers `-sudo` variants when running with elevated privileges
- Falls back to regular templates if no sudo variant exists
- Skips templates with `requires_sudo: true` if not running as root

#### 5. Timeout Settings

```yaml
# Quick scans (< 1 minute)
timeout: 60

# Standard scans (5-10 minutes)
timeout: 600

# Long scans (30-60 minutes)
timeout: 3600

# Very long scans (hours)
# Omit timeout field to use default (3600)
```

#### 6. Output Files

Always save output to `{{output_dir}}`:

```yaml
outputs:
  - pattern: "{{output_dir}}/tool_output.txt"
  - pattern: "{{output_dir}}/tool_output.json"  # Multiple files OK
```

### Example Templates

#### Example 1: Simple HTTP Scanner

**templates/httpx.yaml**:
```yaml
name: httpx
description: Fast HTTP probe with technology detection
enabled: true

command:
  binary: httpx
  args:
    - "-u"
    - "{{target}}"
    - "-tech-detect"
    - "-status-code"
    - "-title"
    - "-o"
    - "{{output_dir}}/httpx_results.txt"

outputs:
  - pattern: "{{output_dir}}/httpx_results.txt"

timeout: 300

requires_sudo: false
```

#### Example 2: Directory Brute-Force (Disabled by Default)

**templates/ffuf.yaml**:
```yaml
name: ffuf
description: Fast web fuzzer for directory discovery
enabled: false  # Disabled by default (noisy)

command:
  binary: ffuf
  args:
    - "-u"
    - "{{target}}/FUZZ"
    - "-w"
    - "{{wordlist}}"
    - "-o"
    - "{{output_dir}}/ffuf_results.json"
    - "-of"
    - "json"
    - "-mc"
    - "200,204,301,302,307,401,403"

outputs:
  - pattern: "{{output_dir}}/ffuf_results.json"

timeout: 1800

requires_sudo: false
```

#### Example 3: Pre-Scan DNS Enumeration

**templates/subfinder.yaml**:
```yaml
name: subfinder
description: Passive subdomain discovery
enabled: true
pre_scan: true  # Runs before main scan

command:
  binary: subfinder
  args:
    - "-d"
    - "{{target}}"
    - "-o"
    - "{{output_dir}}/subdomains.txt"
    - "-silent"

outputs:
  - pattern: "{{output_dir}}/subdomains.txt"

timeout: 300

requires_sudo: false
```

#### Example 4: Shell Script Wrapper

**templates/custom-recon.yaml**:
```yaml
name: custom-recon
description: Custom reconnaissance script
enabled: true

command:
  binary: bash
  args:
    - "templates/custom-recon.sh"
    - "{{target}}"
    - "{{output_dir}}"

outputs:
  - pattern: "{{output_dir}}/recon_results.txt"

timeout: 600

env:
  CUSTOM_VAR: "value"

requires_sudo: false
```

### Submitting Your Template

1. **Test thoroughly**:
   ```bash
   # Test against various targets
   ipcrawler scan 127.0.0.1 --template mytool
   ipcrawler scan example.com --template mytool
   ipcrawler scan https://example.com --template mytool
   ```

2. **Verify output**:
   - Check that output files are created in the correct location
   - Ensure the tool completes within the specified timeout
   - Test both success and failure scenarios

3. **Document requirements**:
   - Add installation instructions in your PR description if the tool isn't commonly available
   - Specify any dependencies or special configuration needed

4. **Submit a pull request**:
   - Fork the repository
   - Add your template to the `templates/` directory
   - Submit a PR with a clear description of what the template does
   - Include example output if possible

## Contributing Code

### Development Setup

1. **Install Rust**:
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/neur0map/ipcrawler.git
   cd ipcrawler
   ```

3. **Build the project**:
   ```bash
   cargo build
   ```

4. **Run tests**:
   ```bash
   cargo test --all-features
   ```

5. **Run linting**:
   ```bash
   cargo clippy --all-features --all-targets -- -D warnings
   cargo fmt --all -- --check
   ```

### Code Guidelines

1. **Follow Rust conventions**:
   - Use `cargo fmt` for formatting
   - Fix all `cargo clippy` warnings
   - Write tests for new functionality

2. **Cross-platform compatibility**:
   - Use `#[cfg(unix)]` for Unix-specific code
   - Use `#[cfg(windows)]` for Windows-specific code
   - Test on multiple platforms when possible

3. **Dependencies**:
   - Prefer pure Rust dependencies (no C bindings if possible)
   - Currently using `rustls` for TLS (not `native-tls`)
   - Avoid adding heavy dependencies

4. **Error handling**:
   - Use `anyhow::Result` for functions that can fail
   - Provide descriptive error messages
   - Use `tracing` for logging (not `println!`)

### Testing

```bash
# Run all tests
cargo test --all-features

# Run specific test
cargo test test_name

# Run with output
cargo test -- --nocapture

# Test on multiple platforms (if available)
cargo test --target x86_64-unknown-linux-musl
```

### Submitting Code Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes**:
   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Test thoroughly**:
   ```bash
   cargo test --all-features
   cargo clippy --all-features --all-targets -- -D warnings
   cargo fmt --all
   ```

4. **Commit with a clear message**:
   ```bash
   git add .
   git commit -m "Add feature: brief description
   
   Detailed description of what changed and why."
   ```

5. **Push and create a pull request**:
   ```bash
   git push origin feature/my-feature
   ```

6. **Submit PR on GitHub**:
   - Provide a clear description of changes
   - Reference any related issues
   - Wait for CI checks to pass

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the bug
2. **Steps to reproduce**: Exact commands that trigger the bug
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Environment**:
   - OS: (e.g., Ubuntu 22.04, macOS 14, Windows 11)
   - IPCrawler version: `ipcrawler --version`
   - Rust version: `rustc --version`
6. **Logs**: Run with `--verbose` and include relevant output

### Feature Requests

When requesting features:

1. **Use case**: Describe the problem you're trying to solve
2. **Proposed solution**: How you envision the feature working
3. **Alternatives**: Any workarounds you've considered
4. **Additional context**: Screenshots, examples, etc.

## Questions?

- **General questions**: Open a GitHub Discussion
- **Security issues**: Email the maintainers privately
- **Template help**: Check `templates/README.md` first

Thank you for contributing to IPCrawler! 🚀
