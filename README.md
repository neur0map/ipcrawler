<div align="center">

# 🕷️ ipcrawler

**Smart Network Reconnaissance Made Simple**

[![Version](https://img.shields.io/badge/version-0.1.0--alpha-blue.svg)](https://github.com/neur0map/ipcrawler)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)

*"It's like bowling with bumpers."* - [@ippsec](https://twitter.com/ippsec)

</div>

---

## What is ipcrawler?

ipcrawler is an **intelligent multi-threaded network reconnaissance tool** that automates the tedious parts of penetration testing. Instead of manually running dozens of enumeration commands, ipcrawler discovers services and automatically launches the right tools for comprehensive reconnaissance.

**Perfect for:** OSCP exam prep, CTFs, penetration testing, and security research.

### 🎯 How it Works

```mermaid
graph LR
    A[Target Input] --> B[Port Discovery]
    B --> C[Service Detection]
    C --> D[Smart Enumeration]
    D --> E[Organized Results]
```

1. **Discover** - Scans ports and identifies running services
2. **Enumerate** - Automatically runs appropriate tools for each service found
3. **Organize** - Creates structured output directories with all results
4. **Suggest** - Provides manual commands for advanced testing

---

## ⚡ Quick Start

### Installation

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make install
```

### Basic Usage

```bash
# Scan a single target
ipcrawler 192.168.1.100

# Scan multiple targets
ipcrawler 192.168.1.0/24

# Scan with custom verbosity
ipcrawler -vv target.com
```

### Example Output Structure
```
results/192.168.1.100/
├── scans/           # All enumeration results
│   ├── tcp80/       # HTTP enumeration
│   ├── tcp22/       # SSH enumeration
│   └── tcp445/      # SMB enumeration
├── report/          # Clean reports and screenshots
├── loot/           # Extracted credentials/data
└── exploit/        # Exploit development workspace
```

---

## 🚀 Key Features

<table>
<tr>
<td width="50%">

### 🎯 **Smart Automation**
- **70+ specialized plugins** organized by reconnaissance phases
- **Automatic tool selection** based on discovered services
- **Multi-threaded execution** for faster results
- **Real-time progress** monitoring and control

</td>
<td width="50%">

### 🛠️ **Flexible & Extensible**
- **Plugin-based architecture** for easy customization
- **TOML configuration** for personal preferences
- **Manual command suggestions** for advanced techniques
- **IPv6 support** and **proxychains compatibility**

</td>
</tr>
</table>

### Supported Services & Tools

| Category | Tools & Techniques |
|----------|-------------------|
| **Web Services** | feroxbuster, gobuster, nikto, whatweb, wpscan |
| **Network Services** | nmap scripts, SSL analysis, DNS enumeration |
| **Database Services** | MySQL, MSSQL, Oracle, MongoDB, Redis enumeration |
| **File Services** | SMB, NFS, FTP enumeration and vulnerability checks |
| **Authentication** | LDAP, Kerberos, Active Directory reconnaissance |

---

## 📋 Requirements & Installation

### System Requirements
- **Python 3.8+**
- **Linux/macOS** (Windows via WSL--NOT FULLY TESTED)
- **Root privileges** (for SYN scanning and UDP)

### Dependencies
The installation automatically handles tool dependencies:

**Essential Tools:** nmap, curl, feroxbuster, gobuster, nikto  
**Database Tools:** MySQL, MSSQL, Oracle clients  
**Network Tools:** dnsrecon, enum4linux, smbclient  
**Platform Support:** Full on Kali/Ubuntu, Limited on macOS

---

## 🎮 Usage Examples

### Target Specification
```bash
# Single IP
ipcrawler 10.10.10.1

# CIDR range
ipcrawler 10.10.10.0/24

# Multiple targets
ipcrawler 10.10.10.1 10.10.10.2 target.com

# From file
ipcrawler -t targets.txt
```

### Advanced Options
```bash
# Custom port range
ipcrawler -p 1-1000,8080,8443 target.com

# Specific plugins only
ipcrawler --service-scans dirbuster,nikto target.com

# Custom output directory
ipcrawler -o /tmp/scan-results target.com
```

### Plugin Management
```bash
# List available plugins
ipcrawler -l

# Show port scan plugins
ipcrawler -l port

# Show service enumeration plugins  
ipcrawler -l service
```

---

## 🔧 Configuration

ipcrawler uses TOML configuration files for customization:

```toml
# ~/.config/ipcrawler/config.toml
verbose = 1
max-scans = 50
heartbeat = 30

[dirbuster]
tool = "feroxbuster"
threads = 20
wordlist = ["/usr/share/wordlists/dirb/common.txt"]
```

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### 🐛 **Report Issues**
Found a bug or have a feature request? [Open an issue](https://github.com/neur0map/ipcrawler/issues)

### 🔧 **Develop Plugins**
Create new enumeration plugins:
```python
from ipcrawler.plugins import ServiceScan

class MyCustomScan(ServiceScan):
    def __init__(self):
        super().__init__()
        self.name = "My Custom Scanner"
        self.tags = ['custom', 'safe']
    
    def configure(self):
        self.match_service_name('myservice')
    
    async def run(self, service):
        await service.execute('my-tool {address}:{port}')
```

### 📝 **Improve Documentation**
Help improve our docs, examples, or add new use cases.

### 🏗️ **Development Setup**
```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
pip install -r requirements.txt
python3 ipcrawler.py --version
```

---

## ⚖️ Legal & Ethics

- **Educational Purpose**: Designed for authorized security testing only
- **OSCP Compliant**: No automated exploitation in default configuration  
- **Your Responsibility**: Ensure you have permission before scanning any systems
- **Disclaimer**: Authors not responsible for misuse

---

## 📜 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

### Built with ❤️ for the cybersecurity community

[Report Bug](https://github.com/neur0map/ipcrawler/issues) · [Request Feature](https://github.com/neur0map/ipcrawler/issues) · [Documentation](CLAUDE.md)

</div>
