# Troubleshooting Guide

## Common Issues

### Tool Not Found

**Symptom:**
```
Tool 'nmap' not found. Install using: apt install -y nmap? [y/N]
```

**Solutions:**

1. Check if tool is installed:
```bash
which nmap
```

2. Use auto-install flag:
```bash
ipcrawler -t 192.168.1.1 -p 80 --install
```

3. Manual installation:
```bash
# Arch Linux
sudo pacman -S nmap

# Debian/Ubuntu
sudo apt install nmap

# macOS
brew install nmap
```

4. Verify PATH:
```bash
echo $PATH
# Ensure /usr/bin or tool location is in PATH
```

### Permission Errors

**Symptom:**
```
Error: Permission denied
Failed to execute: nmap -sS
```

**Solutions:**

1. Use sudo for privileged operations:
```bash
sudo ipcrawler -t 192.168.1.1 -p 80
```

2. Check tool requirements:
- masscan always requires sudo
- nmap SYN scan requires sudo
- traceroute ICMP mode requires sudo

3. Verify user permissions:
```bash
# Check if sudo is available
which sudo

# Test sudo access
sudo -v
```

### Wordlist Not Found

**Symptom:**
```
Warning: Wordlist 'common' not found
```

**Solutions:**

1. Check if config exists:
```bash
ls config/wordlists.yaml
```

2. Install SecLists:
```bash
# Arch Linux
sudo pacman -S seclists

# Debian/Ubuntu
sudo apt install seclists

# Manual
git clone https://github.com/danielmiessler/SecLists.git /usr/share/seclists
```

3. Use direct path:
```bash
ipcrawler -t 192.168.1.1 -p 80 -w /path/to/wordlist.txt
```

4. Verify wordlist paths in config:
```bash
cat config/wordlists.yaml
```

### Script Validation Fails

**Symptom:**
```
SECURITY WARNING: Script contains dangerous commands!
  - rm -rf /
```

**Solutions:**

1. Review script content:
```bash
cat tools/scripts/yourscript.sh
```

2. Remove dangerous commands:
- Replace `rm -rf /` with safe alternatives
- Remove system shutdown commands
- Avoid privilege escalation

3. Check allowed commands list:
See [Security Documentation](SECURITY.md) for whitelisted commands

4. Use tool YAML instead:
Instead of shell script, define tool in YAML with simple commands

### No Output from Tool

**Symptom:**
Tool runs but produces no findings

**Solutions:**

1. Check tool output directly:
```bash
# Run tool manually
nmap -sV 192.168.1.1 -p 80

# Check IPCrawler logs
cat ipcrawler-results/*/logs/nmap_*.json
```

2. Verify output patterns:
```bash
# Check tool YAML
cat tools/nmap.yaml

# Ensure regex patterns match actual output
```

3. Check tool timeout:
```yaml
# In tool YAML
timeout: 600  # Increase if needed
```

4. Verify target is reachable:
```bash
ping 192.168.1.1
```

### Build Errors

**Symptom:**
```
error: could not compile `ipcrawler`
```

**Solutions:**

1. Update Rust:
```bash
rustup update
```

2. Clean and rebuild:
```bash
cargo clean
cargo build
```

3. Check dependencies:
```bash
cargo check
```

4. Update dependencies:
```bash
cargo update
```

5. Verify Rust version:
```bash
rustc --version
# Should be 1.70 or later
```

### Timeout Errors

**Symptom:**
```
Task timed out after 300s
```

**Solutions:**

1. Increase timeout in tool YAML:
```yaml
timeout: 900  # Increase from 300
```

2. Reduce scan scope:
```bash
# Scan fewer ports
ipcrawler -t 192.168.1.1 -p 80,443

# Scan smaller range
ipcrawler -t 192.168.1.1/30 -p common
```

3. Use faster tools:
```bash
# Use masscan instead of nmap for large ranges
sudo ipcrawler -t 192.168.1.0/24 -p fast
```

### Memory Issues

**Symptom:**
```
Out of memory
Cannot allocate memory
```

**Solutions:**

1. Reduce concurrent tasks:
Edit `src/executor/runner.rs`:
```rust
pub fn new(max_concurrent: usize) -> Self {
    Self {
        max_concurrent: 3,  // Reduce from 5
```

2. Scan smaller ranges:
```bash
# Split large ranges
ipcrawler -t 192.168.1.0/25 -p 80
ipcrawler -t 192.168.128.0/25 -p 80
```

3. Use lighter wordlists:
```bash
ipcrawler -t 192.168.1.1 -p 80 -w small
```

### Network Connectivity Issues

**Symptom:**
```
Connection refused
No route to host
```

**Solutions:**

1. Verify network connectivity:
```bash
ping 192.168.1.1
traceroute 192.168.1.1
```

2. Check firewall rules:
```bash
# Check local firewall
sudo iptables -L

# Check target firewall
nmap -Pn 192.168.1.1
```

3. Verify target is correct:
```bash
# Check DNS resolution
dig example.com
host example.com
```

4. Use VPN if required:
```bash
# Connect to VPN first
vpn connect
ipcrawler -t 10.0.0.1 -p 80
```

### Parsing Errors

**Symptom:**
```
Error parsing output for nmap
```

**Solutions:**

1. Check output format:
```bash
# View raw output
cat ipcrawler-results/*/logs/nmap_*.json
```

2. Verify tool output type matches YAML:
```yaml
output:
  type: "xml"  # Must match actual output
```

3. Test regex patterns:
```bash
# Use online regex tester
# Test against actual tool output
```

4. Update patterns in YAML:
```yaml
patterns:
  - name: "finding"
    regex: 'NEW_PATTERN_HERE'
    severity: "info"
```

### Script Execution Fails

**Symptom:**
```
Script not found: tools/scripts/scan.sh
```

**Solutions:**

1. Verify script location:
```bash
ls tools/scripts/
```

2. Check script path in YAML:
```yaml
command: "scan.sh {{target}}"  # Looks in tools/scripts/
# OR
command: "./tools/scripts/scan.sh {{target}}"  # Relative path
```

3. Verify shebang:
```bash
head -1 tools/scripts/scan.sh
# Should be: #!/bin/bash or #!/bin/sh
```

4. Script is made executable automatically, but verify:
```bash
ls -l tools/scripts/scan.sh
```

### Port Parsing Errors

**Symptom:**
```
Invalid port format: xyz
```

**Solutions:**

1. Use valid port format:
```bash
# Single port
-p 80

# List
-p 80,443,8080

# Range
-p 1-1000

# Mode
-p fast
-p common
-p top-1000
```

2. Check for typos:
```bash
# Incorrect
-p 80-443-8080

# Correct
-p 80,443,8080
```

### Target Parsing Errors

**Symptom:**
```
Invalid target format: xyz
```

**Solutions:**

1. Use valid target format:
```bash
# Single IP
-t 192.168.1.1

# CIDR
-t 192.168.1.0/24

# File
-t targets.txt
```

2. Verify file format:
```bash
# targets.txt should contain:
192.168.1.1
192.168.1.10
10.0.0.0/24
```

3. Check for invalid characters:
```bash
# Remove comments and empty lines
grep -v '^#' targets.txt | grep -v '^$'
```

## Platform-Specific Issues

### Linux

**Issue:** Permission denied for raw sockets
```bash
# Add capabilities to nmap (instead of always using sudo)
sudo setcap cap_net_raw,cap_net_admin,cap_net_bind_service+eip /usr/bin/nmap
```

### macOS

**Issue:** Masscan not working
```bash
# macOS firewall may block masscan
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/masscan
```

### Windows (WSL)

**Issue:** Tools not found in WSL
```bash
# Install tools in WSL environment
sudo apt update
sudo apt install nmap nikto gobuster
```

## Getting Help

### Gather Information

Before asking for help, collect:

1. IPCrawler version:
```bash
ipcrawler --version
```

2. OS and version:
```bash
uname -a
cat /etc/os-release
```

3. Rust version:
```bash
rustc --version
cargo --version
```

4. Error messages:
```bash
# Copy full error output
ipcrawler -t 192.168.1.1 -p 80 2>&1 | tee error.log
```

5. Tool versions:
```bash
nmap --version
nikto -Version
gobuster version
```

### Where to Ask

1. GitHub Issues: Create issue with detailed information
2. Discord/IRC: Real-time help from community
3. Documentation: Check all docs first

### What to Include

- Command you ran
- Full error message
- Steps to reproduce
- Expected vs actual behavior
- System information
- Tool versions

## Performance Optimization

### Slow Scans

**Solutions:**

1. Use faster port modes:
```bash
# Instead of all ports
ipcrawler -t 192.168.1.1 -p all

# Use fast mode
ipcrawler -t 192.168.1.1 -p fast
```

2. Increase concurrency (if resources allow):
Edit `src/executor/runner.rs` to increase from 5 concurrent tasks

3. Use lighter tools:
```bash
# Use masscan for port discovery
sudo ipcrawler -t 192.168.1.0/24 -p top-1000

# Then use nmap for detailed scanning
ipcrawler -t <discovered-hosts> -p <open-ports>
```

4. Reduce wordlist size:
```bash
ipcrawler -t 192.168.1.1 -p 80 -w small
```

### High Resource Usage

**Solutions:**

1. Limit concurrent tasks (edit source)
2. Scan in batches
3. Use specific ports instead of ranges
4. Close other applications

## Debugging Tips

### Enable Verbose Output

```bash
# Rust logging
RUST_LOG=debug cargo run -- -t 192.168.1.1 -p 80

# Check individual tool output
cat ipcrawler-results/*/logs/*.json
```

### Test Individual Components

```bash
# Test target parsing
cargo test test_parse_targets

# Test port parsing
cargo test test_parse_ports

# Test tool discovery
cargo test
```

### Check Tool Output Manually

```bash
# Run tool directly to see output
nmap -sV 192.168.1.1 -p 80 -oX output.xml

# Compare with expected format in YAML
cat tools/nmap.yaml
```

## Still Having Issues?

If problems persist:

1. Check GitHub issues for similar problems
2. Review all documentation thoroughly
3. Test with minimal configuration
4. Create detailed bug report with all information above
