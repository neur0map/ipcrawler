# Security Documentation

## Script Security Features

IPCrawler implements multiple security layers for custom shell scripts to prevent malicious code execution.

### Automatic Security Validation

All shell scripts are automatically scanned before execution for dangerous patterns.

#### Dangerous Commands (Blocked)

Scripts containing these commands will be rejected:

**Disk Operations:**
- `rm -rf /` - Recursive deletion
- `mkfs` - Filesystem formatting
- `dd if=` - Direct disk write
- `format` - Disk formatting
- `/dev/sda`, `/dev/nvme` - Direct disk access

**System Control:**
- `shutdown` - System shutdown
- `reboot` - System reboot
- `init 0`, `init 6` - Runlevel changes
- `systemctl poweroff`, `systemctl reboot`

**User Management:**
- `userdel` - Delete users
- `passwd` - Change passwords
- `chown root` - Change ownership to root

**Privilege Escalation:**
- `su -` - Switch user
- `sudo su` - Escalate to root
- `eval` - Arbitrary code execution
- `exec` - Execute arbitrary commands

**Dangerous Permissions:**
- `chmod 777` - Overly permissive

**Fork Bombs:**
- `:(){ :|:& };:` - Fork bomb pattern

#### Suspicious Patterns (Warned)

Scripts containing these patterns will generate warnings but are allowed:

**Obfuscation:**
- `base64 -d` - Decode base64 (often used to hide commands)
- `xxd -r` - Reverse hex dump

**Network Connections:**
- `/dev/tcp/`, `/dev/udp/` - Raw network access
- `nc -l`, `ncat -l` - Netcat listener
- `socat` - Socket operations

**Code Execution:**
- `python -c` - Execute Python code
- `perl -e` - Execute Perl code
- `ruby -e` - Execute Ruby code
- `php -r` - Execute PHP code
- `bash -c`, `sh -c` - Execute shell code

#### Allowed Commands

Security-relevant tools are whitelisted:

**Network Tools:**
- `nmap`, `masscan` - Port scanning
- `nc`, `ncat` - Network connections
- `ping`, `traceroute` - Connectivity testing
- `dig`, `host`, `nslookup` - DNS queries
- `whois` - Registration lookup

**Analysis Tools:**
- `curl`, `wget` - HTTP requests (restricted)
- `openssl` - SSL/TLS operations
- `grep`, `sed`, `awk` - Text processing

**System Utilities:**
- `echo`, `printf` - Output
- `cat`, `head`, `tail` - File reading
- `date`, `sleep` - Time operations
- `timeout` - Command timeout

### Script Restrictions

- **Maximum file size:** 1MB
- **Required shebang:** `#!/bin/bash` or `#!/bin/sh`
- **Automatic permissions:** Scripts are made executable automatically
- **No sudo in scripts:** Use tool's `sudo_command` field instead

## Sudo Usage

IPCrawler intelligently selects commands based on privilege level.

### Without Sudo (Normal Mode)

**Nmap:**
- TCP Connect scan (`-sT`)
- Service version detection (`-sV`)
- Default scripts (`-sC`)

**Traceroute:**
- UDP-based traceroute

**Other Tools:**
- Standard tool operations
- No privileged features

### With Sudo (Privileged Mode)

**Nmap:**
- SYN scan (`-sS`) - Faster, more stealthy
- OS detection (`-O`) - Operating system fingerprinting
- Full TCP/IP stack access

**Traceroute:**
- ICMP-based traceroute (`-I`)
- More reliable results

**Masscan:**
- Requires sudo for all operations
- Raw socket access

### Running with Sudo

```bash
# Basic scan
ipcrawler -t 192.168.1.1 -p 80

# Advanced scan with sudo
sudo ipcrawler -t 192.168.1.1 -p 80
```

IPCrawler will automatically:
1. Detect sudo privileges at startup
2. Display privilege status
3. Select appropriate commands for each tool
4. Use enhanced features when available

## Tool Privilege Requirements

| Tool | Requires Sudo | Reason | Enhanced Features |
|------|---------------|--------|-------------------|
| nmap | Optional | Raw socket access | SYN scan, OS detection |
| masscan | Required | Raw socket access | All operations |
| traceroute | Optional | ICMP packets | ICMP mode |
| ping | No | ICMP echo allowed | N/A |
| nikto | No | HTTP-based | N/A |
| gobuster | No | HTTP-based | N/A |
| sqlmap | No | HTTP-based | N/A |
| sslscan | No | SSL/TLS connections | N/A |
| whatweb | No | HTTP-based | N/A |
| dnsenum | No | DNS queries | N/A |

## Best Practices

### For Script Authors

1. **Use whitelisted commands only**
   - Stick to approved security tools
   - Avoid obfuscation techniques
   - No dynamic code execution

2. **Handle errors gracefully**
   - Check command exit codes
   - Provide meaningful error messages
   - Redirect errors to output file

3. **Validate inputs**
   - Don't trust user input
   - Sanitize variables
   - Use timeout for external commands

4. **Keep scripts simple**
   - One clear purpose per script
   - Under 1MB in size
   - Well-commented code

### For Users

1. **Review scripts before use**
   - Read custom scripts carefully
   - Understand what they do
   - Check for suspicious patterns

2. **Use sudo judiciously**
   - Only when needed
   - Understand what changes with sudo
   - Review tool requirements

3. **Monitor execution**
   - Watch real-time output
   - Review logs after completion
   - Check for unexpected behavior

4. **Keep tools updated**
   - Update security tools regularly
   - Check for tool CVEs
   - Use latest IPCrawler version

## Security Considerations

### Network Security

- Tools make active connections to targets
- May trigger IDS/IPS alerts
- Ensure you have authorization to scan targets
- Use VPN or isolated networks when appropriate

### Data Privacy

- Scan results may contain sensitive information
- Store output securely
- Review before sharing
- Consider encryption for sensitive scans

### Legal Compliance

- Only scan systems you own or have permission to test
- Respect rate limits and terms of service
- Follow responsible disclosure practices
- Comply with local laws and regulations

### Authorization

IPCrawler is designed for:
- Authorized penetration testing
- Security research
- Defensive security operations
- CTF competitions
- Educational purposes

**NOT** for:
- Unauthorized scanning
- Malicious activities
- DoS attacks
- Supply chain compromise
- Detection evasion for malicious purposes
