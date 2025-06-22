<div align="center">

# 🕷️ ipcrawler

**Smart Network Reconnaissance Made Simple**

[![Version](https://img.shields.io/badge/version-0.1.0--alpha-blue.svg)](https://github.com/neur0map/ipcrawler)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)

*"It's like bowling with bumpers."* - [@ippsec](https://twitter.com/ippsec)

### 🤖 Get AI-Powered Repository Summary

<div align="center">

Get a quick, easy-to-read overview of this project from top AI providers:

<a href="https://chatgpt.com/?q=Analyze%20this%20GitHub%20repo%20%28https%3A%2F%2Fgithub.com%2Fneur0map%2Fipcrawler%29%20and%20give%20me%20a%20SHORT%2C%20clear%20summary%3A%0A%0A%E2%80%A2%20What%20it%20does%20%28main%20purpose%29%0A%E2%80%A2%20Key%20features%20%26%20why%20it%27s%20useful%0A%E2%80%A2%20How%20to%20install%20%28quick%20steps%29%0A%E2%80%A2%20Who%20should%20use%20it%20%26%20when%0A%E2%80%A2%20System%20requirements%0A%0AKeep%20it%20concise%20but%20include%20the%20important%20stuff.%20Make%20it%20beginner-friendly.">
  <img src="https://img.shields.io/badge/ChatGPT-74aa9c?style=for-the-badge&logo=openai&logoColor=white" alt="ChatGPT"/>
</a>

<a href="https://grok.com/?q=Analyze%20this%20GitHub%20repo%20%28https%3A%2F%2Fgithub.com%2Fneur0map%2Fipcrawler%29%20and%20give%20me%20a%20SHORT%2C%20clear%20summary%3A%0A%0A%E2%80%A2%20What%20it%20does%20%28main%20purpose%29%0A%E2%80%A2%20Key%20features%20%26%20why%20it%27s%20useful%0A%E2%80%A2%20How%20to%20install%20%28quick%20steps%29%0A%E2%80%A2%20Who%20should%20use%20it%20%26%20when%0A%E2%80%A2%20System%20requirements%0A%0AKeep%20it%20concise%20but%20include%20the%20important%20stuff.%20Make%20it%20beginner-friendly.">
  <img src="https://img.shields.io/badge/Grok-000000?style=for-the-badge&logo=x&logoColor=white" alt="Grok"/>
</a>

*Get a quick AI explanation of this network reconnaissance tool - just click a button above!*

</div>

</div>

---

## What is ipcrawler?

ipcrawler is an **intelligent multi-threaded network reconnaissance tool** that automates the tedious parts of penetration testing. Instead of manually running dozens of enumeration commands, ipcrawler discovers services and automatically launches the right tools for comprehensive reconnaissance.

## This beginner friendly fork of AutoRecon.
Core functionality stayed the same, this fork has an advanced and extremely easy way to install the needed tools, seclists and overall it's extremely easy to use and to understand the results of your scans.

**Perfect for:** OSCP exam prep, CTFs, penetration testing, and security research.

---

## 🎬 See ipcrawler in Action

<div align="center">

### 🕷️ **Live Reconnaissance Demo**

*Watch ipcrawler automatically discover and enumerate services with beautiful, real-time output*

<img src="media/ipcrawler-demo-small.gif" alt="ipcrawler Live Demo - Smart Network Reconnaissance" width="100%" style="border-radius: 10px; border: 2px solid #00ff41; box-shadow: 0 4px 20px rgba(0, 255, 65, 0.3);">

**🎯 What you're seeing:**
- **Port Discovery** → Intelligent service detection  
- **Smart Enumeration** → Automatic tool selection based on findings
- **Beautiful Output** → Rich, colorful terminal interface with real-time progress
- **Organized Results** → Structured file output for easy analysis

*Demo target: Personal domain scan showcasing web service enumeration;*
*Note: --ignore-plugins-checks flag was issue because test was done in MacOS and tools are not natively available*

</div>

---

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

### Automated Installation (System-wide)

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make install          # Installs tools system-wide
ipcrawler --version   # Test installation
```

### Manual Setup (No System Changes)

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
pip install -r requirements.txt
python3 ipcrawler.py --version  # Test setup
```

### Basic Usage

```bash
# With automated installation
ipcrawler 192.168.1.100
ipcrawler 192.168.1.0/24
ipcrawler -vv target.com

# With manual setup  
python3 ipcrawler.py 192.168.1.100
python3 ipcrawler.py 192.168.1.0/24
python3 ipcrawler.py -vv target.com
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

### 🚨 Installation Options

<details>
<summary><b>⚡ Automated Installation (Recommended)</b></summary>

The `make install` command automatically handles ALL dependencies and system setup:

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make install
```

**What `make install` does:**
- Installs Python dependencies via pipx (isolated environment)
- Downloads and installs penetration testing tools
- Clones SecLists wordlists to `/usr/share/seclists` (or `~/tools/SecLists`)
- Adds tool binaries to system PATH
- Creates configuration directories

**⚠️ System Modifications Warning:**
This command modifies your system by installing packages and tools to:
- `/usr/local/bin/` - Tool binaries (gobuster, feroxbuster, etc.)
- `/usr/share/seclists/` - SecLists wordlist repository
- `/opt/` - Additional tools and resources
- System package manager (apt, brew, pacman)

**🔐 Sudo Privileges Warning:**
The `make install` command automatically configures the `ipcrawler` command to run with sudo privileges. This means:
- **All scans run as root** - No password prompts, but full system access
- **UDP scans work automatically** - No "requires root privileges" errors
- **Automatic /etc/hosts modification** - Discovered hostnames added automatically on Kali/HTB systems
- **Security implications** - The tool has complete system access when running

This design choice eliminates the need to type `sudo ipcrawler` for every scan, but users should be aware that all enumeration runs with elevated privileges.

**Make Commands Available:**
- `make install` - Full installation with tools and dependencies
- `make clean` - Remove ipcrawler only (keeps tools and results)
- `make clean-all` - Remove everything including installed tools
- `make debug` - Show system diagnostics and tool availability
- `make help` - Show all available commands

</details>

<details>
<summary><b>🛡️ Manual Setup (No System Modifications)</b></summary>

If you prefer not to modify system files or are using a restricted environment:

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
pip install -r requirements.txt
python3 ipcrawler.py --version
```

**Run scans directly:**
```bash
python3 ipcrawler.py 192.168.1.100
python3 ipcrawler.py -vv target.com
```

**Required Tools for Manual Setup:**

<details>
<summary>Essential Tools (Core functionality)</summary>

- **nmap** - Port scanning and service detection
- **curl** - HTTP requests and web testing
- **python3** - Runtime environment
- **git** - Repository management

**Installation:**
```bash
# Ubuntu/Debian
sudo apt install nmap curl python3 git

# macOS
brew install nmap curl python3 git

# Arch Linux
sudo pacman -S nmap curl python3 git
```

</details>

<details>
<summary>Web Enumeration Tools (Recommended)</summary>

- **feroxbuster** - Fast directory/file discovery
- **gobuster** - Directory/DNS enumeration  
- **nikto** - Web vulnerability scanner
- **whatweb** - Web technology identification

**Installation:**
```bash
# Ubuntu/Debian
sudo apt install feroxbuster gobuster nikto

# Install from GitHub if not available:
# Feroxbuster: https://github.com/epi052/feroxbuster/releases
# Gobuster: https://github.com/OJ/gobuster/releases
```

</details>

<details>
<summary>Network Enumeration Tools (Optional)</summary>

- **dnsrecon** - DNS enumeration
- **enum4linux** - SMB/NetBIOS enumeration
- **smbclient** - SMB client testing
- **nbtscan** - NetBIOS name scanning
- **onesixtyone** - SNMP scanning

**Installation:**
```bash
# Ubuntu/Debian
sudo apt install dnsrecon enum4linux smbclient nbtscan onesixtyone

# Alternative enum4linux-ng:
git clone https://github.com/cddmp/enum4linux-ng.git
```

</details>

<details>
<summary>Database Tools (Optional)</summary>

- **mysql-client** - MySQL enumeration
- **redis-tools** - Redis enumeration
- **impacket-scripts** - Windows/AD tools

**Installation:**
```bash
# Ubuntu/Debian
sudo apt install mysql-client redis-tools impacket-scripts

# Or via pip:
pip3 install impacket
```

</details>

**SecLists Wordlists (Required for many plugins):**

```bash
# Clone to home directory
git clone https://github.com/danielmiessler/SecLists.git ~/tools/SecLists

# Or system-wide (requires sudo)
sudo git clone https://github.com/danielmiessler/SecLists.git /usr/share/seclists
```

**Verify Manual Setup:**
```bash
python3 ipcrawler.py --version
python3 ipcrawler.py -l  # List available plugins
```

</details>

### Platform Support
- **Full Support:** Kali Linux, Ubuntu, Debian
- **Partial Support:** macOS (limited tool availability)
- **Basic Support:** Arch Linux, RedHat/CentOS

> **💡 Pro Tip:** For VM environments or when you want to avoid system modifications, use the manual setup with `python3 ipcrawler.py`

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
# ~/.config/ipcrawler/config.toml (Linux)
# ~/Library/Application Support/IPCrawler/config.toml (macOS)
verbose = 1
max-scans = 50
heartbeat = 30

[dirbuster]
tool = "feroxbuster"
threads = 20
wordlist = ["/usr/share/wordlists/dirb/common.txt"]
```

### 📚 Wordlist Configuration

ipcrawler automatically detects and configures wordlists from SecLists. The wordlist configuration is managed through a dedicated file:

**Configuration File Locations:**
- **Linux:** `~/.config/ipcrawler/wordlists.toml`
- **macOS:** `~/Library/Application Support/IPCrawler/wordlists.toml`
- **Shortcut:** `ipcrawler/wordlists/wordlists.toml` (symlink for easy access)

```toml
# Auto-generated wordlist configuration
[mode]
type = "auto"              # Use auto-detected SecLists paths
auto_update = true         # Update paths on each run

[custom_paths]
# Add your custom wordlist paths here
usernames = "/path/to/custom/usernames.txt"
passwords = "/path/to/custom/passwords.txt"
web_directories = "/path/to/custom/web-dirs.txt"
```

**Available wordlist categories:**
- `usernames` - User enumeration wordlists
- `passwords` - Password lists for brute force
- `web_directories` - Directory/file discovery
- `web_files` - Common web files
- `subdomains` - Subdomain enumeration
- `snmp_communities` - SNMP community strings
- `dns_servers` - DNS server lists
- `vhosts` - Virtual host discovery

**Override wordlists via command line:**
```bash
ipcrawler --wordlist-usernames /custom/users.txt target.com
ipcrawler --wordlist-web-directories /custom/dirs.txt target.com
```

---

## 🔧 Troubleshooting

### Common Issues

**Missing Tools Error:**
```bash
[!] The following plugins failed checks that prevent ipcrawler from running: dirbuster
```

**Solutions:**
1. **Automated installation:** `make install` (installs all tools)
2. **Manual installation:** Install specific tools as shown in manual setup section
3. **Bypass checks:** `ipcrawler --ignore-plugin-checks target.com`

**SecLists Not Detected:**
```bash
[-] No SecLists installation detected. Using built-in wordlists where available.
```

**Solutions:**
1. **With make install:** Automatically clones SecLists to `/usr/share/seclists`
2. **Manual clone:** `git clone https://github.com/danielmiessler/SecLists.git ~/tools/SecLists`
3. **Package install:** `sudo apt install seclists` (may have different structure)

**Permission Issues:**
For UDP scanning and system-wide tool installation:
```bash
# For scanning
sudo ipcrawler target.com
# OR manual setup
sudo python3 ipcrawler.py target.com

# For make install (requires sudo for system modifications)
make install
```

**Restricted Environments:**
If you cannot install tools system-wide, use manual setup:
```bash
pip install -r requirements.txt
python3 ipcrawler.py target.com  # Runs with available tools only
```

**Tool Detection Failures:**
Check what tools are available:
```bash
make debug  # Shows comprehensive tool status
# OR manually
python3 ipcrawler.py -l  # List plugins (shows which need tools)
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

## 💬 Join Our Community

<div align="center">

### 🎮 **Connect with Fellow Security Enthusiasts**

<a href="https://discord.gg/D77fqNHHzc">
  <img src="https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord"/>
</a>

**Join our Discord community to:**
- 🤝 **Get Help** - Ask questions and get support from experienced users
- 💡 **Share Knowledge** - Exchange tips, techniques, and discoveries  
- 🔧 **Plugin Development** - Collaborate on new plugins and features
- 🎯 **CTF & Lab Discussion** - Share findings from Hack The Box, OSCP labs, and CTFs
- 🚀 **Feature Requests** - Suggest improvements and vote on new features
- 📢 **Updates & Announcements** - Be the first to know about new releases

*Connect with pentesting enthusiasts, share your reconnaissance discoveries, and learn from the community!*

</div>

---

<details>
<summary><h2>⚠️ SECURITY WARNING & LEGAL DISCLAIMER - READ BEFORE USE</h2></summary>

### 🚨 **CRITICAL SECURITY NOTICE FOR USERS**

**ipcrawler is a powerful penetration testing tool that carries significant security and legal risks. By downloading and using this software, you acknowledge and accept full responsibility for your actions.**

#### **This Tool is Like a Firearm - Use with Extreme Caution**
Just as a gun manufacturer is not responsible for how their product is used, **the developers of ipcrawler are NOT responsible for any illegal activities, damages, or consequences resulting from your use of this tool.** You are solely liable for your actions.

### **CRITICAL RISKS - What You're Exposing Yourself To**

#### **1. Legal Liability Exposure**
- **THE RISK**: This tool can easily violate computer crime laws
- **WHAT YOU'RE DOING**: 
  - Port scanning (illegal in many jurisdictions without permission)
  - Brute force attacks (definitely illegal against systems you don't own)
  - Service enumeration (can violate terms of service)
  - Vulnerability scanning (often considered hostile reconnaissance)

#### **2. You're Running Untrusted Code with Root Privileges**
- **THE RISK**: This tool requires `sudo` and root access to function
- **WHAT THIS MEANS**: The entire codebase can do ANYTHING to your system
- **EVIDENCE**: 
  - Documentation requires root for SYN scanning
  - `make install` modifies system directories (`/usr/local/bin/`, `/opt/`, `/usr/share/`)
  - Installs tools and dependencies system-wide

#### **3. Your Network Activity Will Be Highly Suspicious**
- **THE RISK**: Running this tool makes you look like an attacker
- **WHAT HAPPENS**:
  - Your IP will trigger intrusion detection systems
  - Network admins will flag your traffic as malicious
  - Your ISP may investigate or terminate service
  - Law enforcement could investigate your activities

#### **4. Credential and Forensic Evidence Creation**
- **THE RISK**: This tool creates forensic evidence that could be used against you
- **WHAT GETS STORED**:
  - All scan results in `results/` directory
  - Command history with targets in `_commands.log`
  - Discovered credentials in plaintext files
  - Network reconnaissance data that prosecutors could use

### **🎯 INTENDED USE CASE - Isolated Lab Environments**

**This tool was designed and intended to be used ONLY in:**

#### **✅ Recommended Environments:**
- **Hack The Box machines** - Legal, isolated targets designed for security testing
- **OSCP exam labs** - Tool is OSCP compliant and safe for certification testing
- **Kali Linux virtual machines** - Isolated from your main system
- **Personal lab environments** - Networks you own completely
- **TryHackMe platforms** - Legal practice environments
- **Authorized penetration testing** - With explicit written permission

#### **✅ Optimal Security & Performance Setup:**
```bash
# Run in Kali Linux VM for maximum isolation
# Install in Kali for optimal tool compatibility
sudo apt update && sudo apt install -y git make
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make install  # All tools pre-installed in Kali
```

### **❌ DO NOT USE AGAINST:**
- **Any system you don't own**
- **Corporate networks without authorization**
- **Cloud services or hosting providers**
- **Internet-facing systems without permission**
- **Your employer's network (unless explicitly authorized)**
- **Educational institution networks**
- **Government systems**

### **Bottom Line for Users**

**This tool is designed for professional penetration testers and security researchers who:**
- ✅ Have explicit written authorization to test targets
- ✅ Understand the legal implications
- ✅ Run it in isolated lab environments
- ✅ Have proper operational security practices

**As a user downloading this from GitHub, you are:**
- ❌ Running untrusted code with root privileges
- ❌ Creating evidence of potentially illegal activities  
- ❌ Exposing yourself to detection and investigation
- ❌ Installing a toolkit primarily used by attackers
- ❌ Taking on significant legal and technical risks

### **⚖️ LEGAL DISCLAIMER**

**BY USING THIS SOFTWARE, YOU AGREE THAT:**

1. **You have explicit authorization** to test all target systems
2. **You understand your local computer crime laws** and will comply with them
3. **You accept full legal responsibility** for your actions
4. **The developers are not liable** for any damages, legal issues, or consequences
5. **You will only use this tool** in legal, authorized scenarios
6. **You understand the security risks** of running this software

### **🛡️ SECURITY RECOMMENDATIONS**

If you choose to use this tool despite the risks:

1. **Only scan systems you own or have explicit permission to test**
2. **Run in isolated virtual machines** to limit exposure to your main system
3. **Use VPN or proxy chains** to protect your identity (but this doesn't make illegal activity legal)
4. **Regularly review and securely delete scan results**
5. **Understand that detection is likely** and plan accordingly
6. **Consult with legal counsel** if you're unsure about authorization

### **🎓 LEARNING ALTERNATIVES**

If you're learning about security, consider these safer alternatives:
- **Hack The Box** - Legal practice targets
- **OSCP certification labs** - This tool is fully compliant with OSCP exam guidelines
- **TryHackMe** - Guided learning platform
- **VulnHub VMs** - Downloadable vulnerable machines
- **DVWA** - Damn Vulnerable Web Application
- **Security courses** with provided lab environments

---

**Remember: With great power comes great responsibility. Use this tool wisely, legally, and ethically.**

</details>

---

## 📜 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

### Built with ❤️ for the cybersecurity community

[Report Bug](https://github.com/neur0map/ipcrawler/issues) · [Request Feature](https://github.com/neur0map/ipcrawler/issues) · [Learn More](https://hackerhub.me/ipcrawler/overview)

</div>
