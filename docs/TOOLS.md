# Supported Tools

IPCrawler includes pre-configured YAML definitions for 13 security tools across multiple categories.

## Network Reconnaissance

### nmap
**Description:** Port scanner and service detection

**Features:**
- Service version detection
- OS fingerprinting (with sudo)
- Default script scanning
- XML output parsing

**Sudo Benefits:**
- SYN stealth scan (`-sS`)
- OS detection (`-O`)
- Faster scanning

**Example:**
```bash
ipcrawler -t 192.168.1.1 -p 80,443
sudo ipcrawler -t 192.168.1.1 -p top-1000  # With OS detection
```

### masscan
**Description:** Ultra-fast TCP port scanner

**Features:**
- Asynchronous transmission
- High-speed scanning
- JSON output
- Rate limiting

**Requirements:**
- Requires sudo for all operations
- Raw socket access

**Example:**
```bash
sudo ipcrawler -t 192.168.1.0/24 -p 1-1000
```

### ping
**Description:** ICMP echo request for host connectivity

**Features:**
- Host reachability testing
- RTT measurement
- Packet loss detection

**Example:**
```bash
ipcrawler -t 192.168.1.1 -p common
```

### traceroute
**Description:** Network path discovery and hop analysis

**Features:**
- Route visualization
- Hop detection
- Latency per hop

**Sudo Benefits:**
- ICMP mode (`-I`)
- More reliable results

**Example:**
```bash
ipcrawler -t 8.8.8.8 -p 80
sudo ipcrawler -t 8.8.8.8 -p 80  # ICMP mode
```

## DNS Enumeration

### dig
**Description:** DNS query and lookup tool

**Features:**
- A, MX, NS, TXT record queries
- ANY record type support
- Detailed DNS responses

**Example:**
```bash
ipcrawler -t example.com -p 53
```

### host
**Description:** Simple DNS lookup utility

**Features:**
- Quick DNS resolution
- IP address lookup
- Mail server detection

**Example:**
```bash
ipcrawler -t example.com -p common
```

### whois
**Description:** Domain/IP registration and ownership lookup

**Features:**
- Registrar information
- Registration dates
- Nameserver details
- Contact information

**Example:**
```bash
ipcrawler -t example.com -p 80
```

### dnsenum
**Description:** DNS enumeration and subdomain discovery

**Features:**
- Subdomain brute-forcing
- Zone transfer attempts
- NS server enumeration
- MX record discovery

**Example:**
```bash
ipcrawler -t example.com -p 53
```

## Web Application Testing

### nikto
**Description:** Web server vulnerability scanner

**Features:**
- Server misconfiguration detection
- Outdated software identification
- Dangerous files and CGIs
- JSON output

**Example:**
```bash
ipcrawler -t 192.168.1.1 -p 80,443
```

### gobuster
**Description:** Directory and file brute-forcer

**Features:**
- Directory enumeration
- File discovery
- Custom wordlist support
- Status code filtering

**Wordlist Support:**
- Uses configured wordlist from `-w` flag
- Default: common wordlist

**Example:**
```bash
ipcrawler -t 192.168.1.1 -p 80 -w big
ipcrawler -t 192.168.1.1 -p 80 -w /path/to/custom.txt
```

### whatweb
**Description:** Web technology fingerprinting

**Features:**
- CMS detection
- Technology stack identification
- Plugin/theme enumeration
- JSON output

**Example:**
```bash
ipcrawler -t 192.168.1.1 -p 80,8080
```

### sqlmap
**Description:** SQL injection testing

**Features:**
- Automatic SQL injection detection
- Database fingerprinting
- Data extraction
- Multiple injection techniques

**Example:**
```bash
ipcrawler -t 192.168.1.1 -p 80
```

### sslscan
**Description:** SSL/TLS configuration scanner

**Features:**
- Cipher suite enumeration
- Protocol version detection
- Certificate analysis
- Weak configuration detection

**Example:**
```bash
ipcrawler -t 192.168.1.1 -p 443
```

## Tool Installation

### Automatic Installation

IPCrawler can automatically detect and install missing tools:

```bash
# Auto-install without prompting
ipcrawler -t 192.168.1.1 -p 80 --install

# Prompt for each missing tool
ipcrawler -t 192.168.1.1 -p 80
```

### Manual Installation

#### Arch Linux
```bash
sudo pacman -S nmap nikto gobuster sqlmap sslscan masscan whatweb dnsenum bind-tools traceroute iputils whois
```

#### Debian/Ubuntu
```bash
sudo apt install nmap nikto gobuster sqlmap sslscan masscan whatweb dnsenum dnsutils traceroute iputils-ping whois
```

#### macOS
```bash
brew install nmap nikto gobuster sqlmap sslscan masscan whatweb dnsenum bind traceroute
```

#### Fedora/RHEL
```bash
sudo dnf install nmap nikto gobuster sqlmap sslscan masscan whatweb dnsenum bind-utils traceroute iputils whois
```

## Tool Output Formats

| Tool | Output Type | Parser |
|------|-------------|--------|
| nmap | XML | Native XML parser |
| masscan | JSON | Native JSON parser |
| nikto | JSON | Native JSON parser |
| whatweb | JSON | Native JSON parser |
| gobuster | Text | Regex patterns |
| sqlmap | Text | Regex patterns |
| sslscan | Text | Regex patterns |
| ping | Text | Regex patterns |
| traceroute | Text | Regex patterns |
| dig | Text | Regex patterns |
| host | Text | Regex patterns |
| whois | Text | Regex patterns |
| dnsenum | Text | Regex patterns |

## Performance Characteristics

| Tool | Speed | Resource Usage | Recommended Timeout |
|------|-------|----------------|---------------------|
| nmap | Medium | Medium | 600s |
| masscan | Very Fast | High | 300s |
| nikto | Slow | Low | 900s |
| gobuster | Medium | Medium | 600s |
| sqlmap | Slow | Medium | 1800s |
| sslscan | Fast | Low | 120s |
| whatweb | Fast | Low | 120s |
| ping | Very Fast | Very Low | 30s |
| traceroute | Medium | Low | 120s |
| dig | Fast | Very Low | 30s |
| host | Fast | Very Low | 30s |
| whois | Fast | Very Low | 60s |
| dnsenum | Slow | Medium | 600s |

## Tool Compatibility

All tools are compatible with:
- Linux (all distributions)
- macOS
- BSD variants

Some tools have enhanced features on specific platforms. Refer to individual tool documentation for details.
