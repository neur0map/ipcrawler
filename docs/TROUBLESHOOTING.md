# 🔧 Troubleshooting Guide

This guide covers common issues and their solutions when using the Rust Recon Tool.

## 🚨 Common Issues

### 1. Tool Not Found Errors

**Symptoms:**
```
❌ nmap - Not installed
Command not found: No such file or directory (os error 2)
```

**Solution:**
```bash
# Check which tools are missing
rust_recon_tool --doctor

# Install missing tools (examples)
# macOS
brew install nmap

# Ubuntu/Debian
sudo apt update && sudo apt install nmap

# Go-based tools
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
```

### 2. Configuration File Not Found

**Symptoms:**
```
❌ Config profile 'my-config' not found in any location
```

**Solution:**
```bash
# Check available configurations
rust_recon_tool --config nonexistent --validate

# Check directory paths
rust_recon_tool --paths

# Create config in correct location
mkdir -p ~/.config/recon-tool/profiles
cp config/default.yaml ~/.config/recon-tool/profiles/my-config.yaml
```

### 3. Permission Denied

**Symptoms:**
```
Permission denied (os error 13)
```

**Solutions:**

**For nmap requiring root:**
```bash
# Use unprivileged scan types
nmap -sT -sV target  # Instead of -sS

# Or run with sudo (not recommended for the whole tool)
sudo nmap -sS target
```

**For output directory:**
```bash
# Check output directory permissions
ls -la ./recon-results/

# Use custom output directory
rust_recon_tool --target example.com --output ~/my-scans/
```

### 4. Slow Performance

**Symptoms:**
- Tools taking very long to complete
- High resource usage
- Timeouts

**Solutions:**

**Adjust concurrency:**
```yaml
globals:
  max_concurrent: 5  # Reduce from default 10
  retry_count: 1     # Reduce retries
```

**Optimize tool commands:**
```yaml
tools:
  - name: "nmap_fast"
    command: "nmap -T4 --max-retries 1 -p {discovered_ports} {target}"  # Faster settings
    timeout: 300     # Reduce timeout
```

**Use quick scan profile:**
```bash
rust_recon_tool --target example.com --config quick-scan
```

### 5. No Output Generated

**Symptoms:**
- Tools complete successfully but no useful output
- Empty result files

**Debugging:**
```bash
# Run with debug output
rust_recon_tool --target example.com --debug --verbose

# Check dry run
rust_recon_tool --target example.com --dry-run

# Manually test tool commands
naabu -host example.com -top-ports 100 -silent
```

**Common causes:**
- Target is down or filtered
- Tool syntax changed
- Network connectivity issues
- Firewall blocking

### 6. Chain Dependencies Not Working

**Symptoms:**
- Chained tools not executing
- Missing `{discovered_ports}` data

**Solution:**
```bash
# Check chain conditions
rust_recon_tool --config my-config --list-tools

# Verify output files exist and have content
ls -la recon-results/target_timestamp/raw/

# Test individual tools first
rust_recon_tool --target example.com --config simple-port-scan
```

### 7. HTML/JSON Report Issues

**Symptoms:**
- Reports not generated
- Malformed output

**Solution:**
```bash
# Check output directory permissions
ls -la recon-results/target_timestamp/

# Verify scan completed successfully
echo $?  # Should be 0

# Check for execution errors
cat recon-results/target_timestamp/logs/execution.log
```

## 🔍 Debugging Techniques

### 1. Verbose Output
```bash
rust_recon_tool --target example.com --verbose --debug
```

### 2. Dry Run Analysis
```bash
rust_recon_tool --target example.com --dry-run
```

### 3. Tool-by-Tool Testing
```bash
# Test individual tools manually
naabu -host example.com -top-ports 100
nmap -sV example.com
```

### 4. Configuration Validation
```bash
rust_recon_tool --config my-config --validate
```

### 5. System Health Check
```bash
rust_recon_tool --doctor
```

## 🛠️ Platform-Specific Issues

### macOS

**Issue: Gatekeeper blocking unsigned binaries**
```bash
# Allow unsigned binaries (if you compiled from source)
sudo spctl --master-disable
```

**Issue: SIP (System Integrity Protection)**
```bash
# Some tools may need to be installed via Homebrew
brew install nmap masscan
```

### Linux

**Issue: Missing dependencies**
```bash
# Install build dependencies
sudo apt install build-essential pkg-config libssl-dev

# Install Go for ProjectDiscovery tools
sudo apt install golang-go
```

**Issue: Firewall blocking**
```bash
# Check iptables rules
sudo iptables -L

# Allow outbound connections (if needed)
sudo ufw allow out 53,80,443
```

### Windows

**Issue: Windows Defender flagging tools**
- Add exclusions for reconnaissance tools
- Use Windows Security exclusions

**Issue: Path problems**
```cmd
# Add tools to PATH
setx PATH "%PATH%;C:\path\to\tools"
```

## 📊 Performance Tuning

### Network Scanning

**For local networks:**
```yaml
globals:
  max_concurrent: 15
tools:
  - name: "nmap_fast"
    command: "nmap -T5 --min-rate 1000 {target} -p {discovered_ports}"
```

**For remote targets:**
```yaml
globals:
  max_concurrent: 5
tools:
  - name: "nmap_careful"
    command: "nmap -T3 --max-retries 2 {target} -p {discovered_ports}"
```

### Resource Management

**Memory usage:**
```yaml
# Avoid full port scans on large networks
tools:
  - name: "selective_scan"
    command: "nmap -p 22,80,443,8080 {target}"  # Specific ports only
```

**CPU usage:**
```yaml
globals:
  max_concurrent: 4  # Limit based on CPU cores
```

## 📝 Configuration Best Practices

### 1. Start Simple
```yaml
# Begin with basic tools
tools:
  - name: "basic_nmap"
    command: "nmap -sV -T4 {target}"
    timeout: 300
    enabled: true
```

### 2. Add Tools Gradually
```yaml
# Add one tool at a time and test
tools:
  - name: "new_tool"
    enabled: false  # Start disabled
```

### 3. Use Appropriate Timeouts
```yaml
tools:
  - name: "quick_scan"
    timeout: 60     # Short for fast tools
  - name: "deep_scan"
    timeout: 1800   # Longer for comprehensive scans
```

### 4. Test Chain Dependencies
```yaml
chains:
  - name: "test_chain"
    from: "port_scan"
    to: "service_scan"
    condition: "has_output"  # Start with simple conditions
```

## 🚨 Security Considerations

### 1. Target Authorization
- Only scan targets you own or have explicit permission to test
- Be aware of terms of service for cloud providers

### 2. Network Impact
- Use appropriate timing templates (-T1 to -T5)
- Respect rate limits and avoid DoS conditions

### 3. Tool Selection
- Disable aggressive tools by default
- Use passive reconnaissance when possible

### 8. Interactive Summary Viewing Issues

**Symptoms:**
```
💡 Tip: Install 'see' for interactive markdown viewing:
  cargo install see-cat
```

**Or:**
```
Failed to open new terminal window, falling back...
❌ Failed to launch 'see': No such file or directory
```

**Solutions:**

**Missing see tool:**
```bash
# Install see for markdown rendering
cargo install see-cat

# Verify installation
see --version
```

**Terminal window not opening (macOS):**
```bash
# Check if Terminal.app is accessible
osascript -e 'tell application "Terminal" to get version'

# Manual command to test:
osascript -e 'tell application "Terminal" to do script "echo test"'
```

**Terminal window not opening (Linux):**
```bash
# Check available terminal emulators
which gnome-terminal
which xterm

# Test terminal opening manually
gnome-terminal --geometry=130x60 -- bash -c "echo test; read"
```

**Fallback behavior:**
- ipcrawler automatically falls back to current terminal viewing
- No functionality is lost if `see` is not installed
- You can always manually view: `see --show-line-numbers=true /path/to/scan_summary.md`

## 📞 Getting Help

### 1. Check Documentation
```bash
rust_recon_tool --help
```

### 2. Validate Configuration
```bash
rust_recon_tool --config my-config --validate --verbose
```

### 3. System Diagnostics
```bash
rust_recon_tool --doctor
rust_recon_tool --paths
```

### 4. Debug Information
```bash
rust_recon_tool --target example.com --debug > debug.log 2>&1
```

### 5. Report Issues
When reporting issues, include:
- Operating system and version
- Rust and tool versions
- Configuration file (sanitized)
- Error messages and logs
- Steps to reproduce

---

**Remember**: This tool is for authorized security testing only. Always ensure you have proper permission before scanning any target.