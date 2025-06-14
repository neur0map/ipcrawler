# 🕷️ IPCrawler

**Automated network reconnaissance tool for penetration testing and CTFs**

⚡ Originally based on [AutoRecon](https://github.com/Tib3rius/AutoRecon) by [Tib3rius](https://github.com/Tib3rius).  
IPCrawler has since evolved into a standalone tool with simplified setup and enhanced output.
### Changes from AutoRecon
 see changes here --> [ipcrawler-legacy](https://github.com/neur0map/ipcrawler-legacy)

![Version](https://img.shields.io/badge/Version-v2.1.0-brightgreen) ![Status](https://img.shields.io/badge/Status-Stable-brightgreen)




### 🎥 Video Tutorials

<div align="center">

| **🐧 HTB Local Setup** | **🍎 Docker on macOS** |
|:--:|:--:|
| <a href="https://youtu.be/lBXAzpUrtlw" target="_blank"><img src="https://img.youtube.com/vi/lBXAzpUrtlw/maxresdefault.jpg" alt="HTB Setup" width="400"></a> | <a href="https://youtu.be/i6Y5Rn0--kA" target="_blank"><img src="https://img.youtube.com/vi/i6Y5Rn0--kA/maxresdefault.jpg" alt="macOS Setup" width="400"></a> |
| **Complete setup on HTB machines** | **Docker installation & usage on macOS** |

</div>

### 🐧 Linux/macOS (Recommended)
```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make setup                  # If make not installed: ./bootstrap.sh first
ipcrawler 10.10.10.1
```

### 🪟 Windows (Docker)
```cmd
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
ipcrawler-windows.bat
```

### 🐳 Docker (All Platforms)
```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make setup-docker
```

## ✨ What It Does

- **🎯 Smart Enumeration**: Automatically runs appropriate tools based on discovered services
- **⚡ Multi-threaded**: Scans multiple targets concurrently  
- **📁 Organized Output**: Clean directory structure with HTML reports
- **🔧 Configurable**: Extensive plugin system with TOML config files

## 📊 Example Usage

```bash
# Basic scan
ipcrawler 10.10.10.1

# Verbose output with progress
ipcrawler -v 10.10.10.1

# Fast scan (top 1000 ports)
ipcrawler -p 1-1000 10.10.10.1

# Multiple targets
ipcrawler 10.10.10.1 10.10.10.2

# Custom timing
ipcrawler --nmap-append '-T3' 10.10.10.1
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
tags = 'default+safe'      # Only safe, fast tools
```

## 🎓 Perfect for OSCP & CTFs

- **OSCP Exam**: Run on all targets while focusing on one
- **HTB/VulnHub**: Quick initial enumeration
- **CTF Events**: Rapid service discovery

## 🛠️ Setup Details

### Prerequisites
- **Python 3.8+** (Linux/macOS)
- **Docker** (Windows/optional for others)
- **make** (usually pre-installed)

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

## 🔍 Verbosity Levels

| Flag | Output |
|------|--------|
| (none) | Minimal |
| `-v` | 🔍 Visual progress with icons |
| `-vv` | ✅ Completion status & timing |
| `-vvv` | Live command output |

## 🙏 Credits

⚡ Originally based on [AutoRecon](https://github.com/Tib3rius/AutoRecon) by [Tib3rius](https://github.com/Tib3rius).  
IPCrawler has since evolved into a standalone tool with simplified setup and enhanced output.

Core reconnaissance concepts and plugin architecture inspired by the excellent foundation provided by AutoRecon.

## ⚠️ Legal Notice

For authorized testing only. No automated exploitation by default (OSCP compliant).

---

**⭐ Star this repo if ipcrawler helps with your security testing!**
