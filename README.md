# 🕷️ IPCrawler

**Automated network reconnaissance tool for penetration testing and CTFs**

⚡ Originally based on [AutoRecon](https://github.com/Tib3rius/AutoRecon) by [Tib3rius](https://github.com/Tib3rius).  
IPCrawler has since evolved into a standalone tool with simplified setup and enhanced output.

### Changes from AutoRecon
   see changes here (Migrated since Version 2.1.0 --> [ipcrawler-legacy](https://github.com/neur0map/ipcrawler-legacy)

![Version](https://img.shields.io/badge/Version-v2.1.0-brightgreen) ![Status](https://img.shields.io/badge/Status-Stable-brightgreen)

### 🛠️ Available Commands 

If you have `make` installed, you can use the following commands:

```bash
make setup                  # If make not installed: ./bootstrap.sh first
make setup-docker           # If docker not installed: https://docs.docker.com/get-docker/
make clean                  # Removes everything except scan results
make reset                  # Clear all Python/ipcrawler cache and rebuild application
make help                   # Show all commands
make update                 # Update ipcrawler to latest version
```
## 🚀 Quick Start

### 🐧 Linux/macOS (Recommended)
```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make setup                  # If make not installed: ./bootstrap.sh first
ipcrawler 10.10.10.1
```

### 🪟 Windows
```cmd
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
windows-scripts\ipcrawler-windows.bat
```

> 📁 **Windows users**: See `windows-scripts/README.md` for detailed setup instructions and troubleshooting.

### 🐳 Docker (All Platforms)
```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler

# Linux/macOS with make
make setup-docker

# Universal commands (all platforms)
docker build -t ipcrawler .
docker run -it --rm -v "$(pwd)/results:/scans" -w /scans ipcrawler    # Linux/macOS
docker run -it --rm -v "%cd%\results:/scans" -w /scans ipcrawler      # Windows CMD
docker run -it --rm -v "${PWD}\results:/scans" -w /scans ipcrawler    # Windows PowerShell
```


### 🎥 Video Tutorials

<div align="center">

| **🐧 HTB Local Setup** | **🍎 Docker on macOS** |
|:--:|:--:|
| <a href="https://youtu.be/lBXAzpUrtlw" target="_blank"><img src="https://img.youtube.com/vi/lBXAzpUrtlw/maxresdefault.jpg" alt="HTB Setup" width="400"></a> | <a href="https://youtu.be/i6Y5Rn0--kA" target="_blank"><img src="https://img.youtube.com/vi/i6Y5Rn0--kA/maxresdefault.jpg" alt="macOS Setup" width="400"></a> |
| **Complete setup on HTB machines** | **Docker installation & usage on macOS** |

</div>

## ✨ What It Does

- **🎯 Smart Enumeration**: Automatically runs appropriate tools based on discovered services
- **⚡ Multi-threaded**: Scans multiple targets concurrently  
- **📁 Organized Output**: Clean directory structure with HTML reports
- **🔧 Configurable**: Extensive plugin system with TOML config files

## 📊 Example Usage

```bash
# Basic scan with default plugins (excludes slow 'long' plugins)
ipcrawler 10.10.10.10

# Include long-running scans (directory busting, subdomain enum)
ipcrawler --tags 'default' 10.10.10.10

# Quick scan - only fast, safe tools
ipcrawler --tags 'default+safe+quick' 10.10.10.10

# Scan with custom timeout (prevent hanging)
ipcrawler --timeout 60 10.10.10.10

# Verbose output with progress
ipcrawler -v 10.10.10.1

# Fast scan (top 1000 ports)
ipcrawler -p 1-1000 10.10.10.1

# Multiple targets
ipcrawler 10.10.10.1 10.10.10.2

# Custom timing
ipcrawler --nmap-append '-T3' 10.10.10.1

# Docker usage (replace with platform-specific volume syntax from above)
docker run -it --rm -v "$(pwd)/results:/scans" -w /scans ipcrawler 10.10.10.1
```

## 📁 Output Structure

```
results/10.10.10.1/
├── report/
│   ├── Full_Report.html     # 🌟 Main HTML summary
│   └── screenshots/
├── scans/
│   ├── tcp80/              # HTTP enumeration
│   ├── tcp22/              # SSH enumeration
│   ├── _commands.log       # All commands run
│   └── _manual_commands.txt # Suggested next steps
└── exploit/                # Payloads & exploits
```

## ⚙️ Configuration

**💡 See all available plugins and tags:**
```bash
ipcrawler --list
```

**Config files** (auto-created after first run):
- `~/.config/ipcrawler/config.toml` - Main settings
- `~/.config/ipcrawler/global.toml` - Global options & patterns

**Common config tweaks:**
```toml
# config.toml
verbose = 1                 # Default verbosity
max-scans = 20             # Concurrent scans
nmap-append = '-T3'        # Conservative timing
tags = 'default+safe'      # Only safe tools
exclude-tags = 'long'      # Exclude slow tools like nikto, dirbuster
```

### 🔧 Long Scan Timeout Management

**New in v2.1.2**: Fixed hanging issues at 98% completion with comprehensive timeout management.

**Quick fixes for hanging scans:**
```bash
# Exclude long-running tools (recommended for most scans)
ipcrawler --exclude-tags long target.com

# Set global timeout (60 minutes total)
ipcrawler --timeout 60 target.com

# Set per-target timeout (30 minutes per target)
ipcrawler --target-timeout 30 target.com

# Enable parallel port scanning if TCP scan hangs
ipcrawler --top-tcp-ports.parallel-scan target.com

# Enable parallel wordlists if directory busting hangs  
ipcrawler --dirbuster.parallel-wordlists target.com

# Combine both for maximum reliability
ipcrawler --top-tcp-ports.parallel-scan --dirbuster.parallel-wordlists target.com
```

**Plugin-specific timeouts** in `~/.config/ipcrawler/config.toml`:
```toml
# Uncomment and customize these timeout settings:
[dirbuster]
timeout = 1800      # 30 minutes max for directory busting
max_depth = 4       # Prevent infinite recursion

[nikto]
timeout = 1800      # 30 minutes max for web vulnerability scanning

[subdomain-enum]
timeout = 1800      # 30 minutes max for subdomain enumeration
```

> 📖 **Detailed guide**: See `LONG_SCAN_FIXES.md` for complete timeout configuration and troubleshooting.

## 🔍 Verbosity Levels

| Flag | Output |
|------|--------|
| (none) | Minimal |
| `-v` | 🔍 Visual progress with icons |
| `-vv` | ✅ Completion status & timing |
| `-vvv` | Live command output |

## 🎓 Perfect for OSCP & CTFs

- **OSCP Exam**: Run on all targets while focusing on one
- **HTB/VulnHub**: Quick initial enumeration
- **CTF Events**: Rapid service discovery

## 🛠️ Setup Details

### Prerequisites
- **Python 3.8+** (Linux/macOS native install)
- **Docker** (Windows or cross-platform)
- **make** (usually pre-installed on Linux/macOS)

### What `make setup` does:
1. Creates Python virtual environment
2. Installs dependencies (Rich, colorama, etc.)
3. Downloads security tools (nmap, nikto, gobuster, etc.)
4. Creates global `ipcrawler` command
5. Sets up config files

### Cleanup
```bash
make clean  # Removes everything except scan results
```

## 🙏 Credits

Core reconnaissance concepts and plugin architecture inspired by [AutoRecon](https://github.com/Tib3rius/AutoRecon) by [Tib3rius](https://github.com/Tib3rius).

## ⚠️ Legal Notice

For authorized testing only. No automated exploitation by default (OSCP compliant).

---

**⭐ Star this repo if ipcrawler helps with your security testing!**

## 🎯 Wordlist Configuration

**Global wordlists take priority** over plugin defaults and can significantly speed up scans:

```bash
# Edit global wordlists (recommended for faster scans)
nano ipcrawler/global.toml
```

**Default global wordlists** (smaller, faster):
- **Directory busting**: `/usr/share/seclists/Discovery/Web-Content/common.txt` (~4.6K entries)
- **Subdomain enum**: `/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt` (~5K entries)  
- **Virtual hosts**: `/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt` (~5K entries)

**Plugin defaults** (larger, slower):
- **Directory busting**: `directory-list-2.3-medium.txt` (~220K entries)
- **Subdomain enum**: `subdomains-top1million-110000.txt` (~110K entries)

💡 **Tip**: The global wordlists prevent long scans from hanging and provide faster results for most scenarios.
