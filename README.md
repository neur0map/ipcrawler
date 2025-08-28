# 🕷️ IPCrawler

> *A reconnaissance automation tool built for CTF and penetration testing by a cybersecurity engineer learning Rust, powered entirely by AI pair programming*

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Language](https://img.shields.io/badge/language-Rust-orange.svg)
![Status](https://img.shields.io/badge/status-Active%20Development-green.svg)

**🚀 Real-time TUI • 🔍 Reconnaissance automation • ⚡ Concurrent scanning**

[Discord Server](https://discord.gg/ipcrawler) • [Reddit Community](https://reddit.com/r/ipcrawler) • [Report Issues](https://github.com/ipcrawler/ipcrawler/issues)

</div>

---

## 📖 About This Project

Hi! I'm Carlos, a cybersecurity and networking engineer. While I'm not a programmer by trade, I built this tool entirely with [**Claude Code**](https://claude.ai/code) - an AI pair programming assistant. As someone who spends time on Hack The Box and CTF challenges, I was frustrated with complex tools like [AutoRecon](https://github.com/Tib3rius/AutoRecon) that are hard to set up and customize.

Since the security industry seems to be moving from C to Rust, I decided this would be a perfect opportunity to learn Rust while building something actually useful for my workflow. Every line of code, every feature, and every bug fix has been implemented through careful collaboration with AI - and honestly, I've learned a ton about programming in the process!

**⚠️ Full transparency:** As I'm not an experienced programmer, there might be bugs or issues. I welcome anyone to try the tool and submit issues - I'll review them and work on improvements with my AI coding partner.

---

## ✨ What IPCrawler Does

IPCrawler is a **comprehensive reconnaissance automation tool** designed for cybersecurity professionals and enthusiasts. It combines DNS enumeration, host discovery, port scanning, and web application analysis into a unified workflow with real-time visual feedback.

### 🎯 Built For
- **Penetration testing** engagements and security assessments
- **Hack The Box** challenges and OSCP lab practice
- **CTF competitions** requiring rapid reconnaissance
- **Bug bounty hunting** and responsible disclosure programs
- **Network security audits** with immediate results

### 🛠️ Core Capabilities
- **Multi-phase reconnaissance**: DNS → Host Discovery → Port Scanning → Service Analysis
- **Real-time TUI**: Live progress tracking with colored results and system monitoring
- **Parallel processing**: Concurrent execution across all reconnaissance phases
- **Web application analysis**: Directory enumeration and file discovery on HTTP/HTTPS services
- **Smart target handling**: IPv4/IPv6 addresses, domains, and CIDR ranges
- **Performance optimized**: 2-minute time budgets per service for rapid CTF/lab workflows
- **Comprehensive coverage**: DNS records, host enumeration, port discovery, and web content analysis
- **Professional artifacts**: Timestamped results with multiple output formats (TXT/MD/JSON)

---

## 🚀 Quick Start

### Installation
```bash
# Clone and build
git clone https://github.com/ipcrawler/ipcrawler.git
cd ipcrawler
make build

# The build process will:
# ✅ Compile the binary
# ✅ Create ~/.local/bin/ipcrawler symlink  
# ✅ Install global.toml config
```

### Basic Usage
```bash
# Scan a domain
ipcrawler -t google.com

# Scan with verbose logging  
ipcrawler -t 8.8.8.8 --verbose

# Get help
ipcrawler --help
```

### Requirements
- **DNS Tools**: `nslookup` and `dig` in PATH (core reconnaissance)
- **Port Scanner**: `rustscan` and `nmap` (optional, for comprehensive coverage)
- **Host Discovery**: `dnsx` and `httpx` (optional, for subdomain enumeration)
- **Web Analysis**: `feroxbuster`, `katana`, `cewl` (optional, for HTTP/HTTPS services)
- **Terminal**: Minimum 70x20 characters for TUI
- **File descriptors**: ≥2048 (`ulimit -n 2048`) for concurrent operations

---

## 🎮 Interface Preview

```
┌─ IPCrawler ──────────────────────────────────────────────────────────────┐
│ Target: example.com | Status: Running | Elapsed: 00:02.8s               │
└──────────────────────────────────────────────────────────────────────────┘
┌─ System ─────────────────────────────────────────────────────────────────┐
│ CPU: 18.7% | RAM: 12.4GB/16.0GB | FDs: 127/2048                         │
└──────────────────────────────────────────────────────────────────────────┘
┌─ Scan Progress ──────────────┬─ Active Tasks ─────────────────────────────┐
│ Phase 3: Service Probing     │ ✓ nslookup: Found 8 DNS records           │
│ ████████████████████░░░░ 85% │ ✓ dig: Found 12 DNS records               │
│                              │ ✓ hosts_discovery: Found 3 subdomains     │
│ 17/20 tasks completed        │ ◯ looter [89s]: Analyzing web services    │
└──────────────────────────────┴─────────────────────────────────────────────┘
┌─ Tabs (←→ to switch) ────────────────────────────────────────────────────┐
│ [Overview] [Ports] [Services] [Logs] [Help]                             │
└──────────────────────────────────────────────────────────────────────────┘
┌─ Discovered Services ────────┬─ Live Logs ─────────────────────────────────┐
│ 80/tcp  http   example.com   │ 14:23:15 INF ✓ port_scanner: Found 6 ports │
│ 443/tcp https  example.com   │ 14:23:16 INF ✓ looter: Phase B - Baseline  │
│ 53/tcp  domain example.com   │ 14:23:18 INF ✓ looter: Found /admin.php    │
│ 22/tcp  ssh    example.com   │ 14:23:19 INF ✓ looter: Found /config.bak   │
└──────────────────────────────┴─────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

IPCrawler uses **smart defaults** - everything works out of the box, but cybersecurity professionals can customize for their specific use cases:

```toml
# ~/.config/ipcrawler/global.toml
# Uncomment sections to override defaults

[concurrency]
max_total_scans = 50          # Total concurrent operations 
max_port_scans = 10          # Port scanning pool size
max_service_scans = 20       # Service analysis parallelism

# [tools.port_scanner.ports]
# scan_strategy = "top-1000"   # Port selection strategy
# # Options: "top-100", "top-1000", "top-10000", "full", "custom"

# [tools.port_scanner.rustscan]
# timeout_ms = 1500           # Fast port discovery
# batch_size = 2000           # Ports per batch

# [tools.port_scanner.nmap]  
# version_intensity = 4       # Service detection depth (0-9)
# total_timeout_ms = 90000    # 90 seconds for service analysis

# [tools.hosts_discovery]
# target_ip = "127.0.0.1"     # Map discovered domains to this IP
# auto_write = true           # Update /etc/hosts if sudo available
```

**Performance Note**: The looter plugin uses internal time budgets (2 minutes per service) optimized for CTF and lab environments. All reconnaissance phases run in parallel for maximum efficiency.

---

## 📁 Output Structure

Professional artifacts for documentation and analysis:

```
artifacts/runs/run_example.com_20250828_142015/
├── scans/
│   ├── nslookup_results.txt      # DNS enumeration results
│   ├── dig_results.txt           # DNS query outputs  
│   ├── port_scanner_results.txt  # Port discovery and service detection
│   ├── hosts_discovery_results.txt # Subdomain and virtual host enumeration
│   └── looter_results.txt        # Web application analysis findings
├── reports/
│   ├── summary.txt               # Executive summary for reports
│   ├── summary.md                # Technical documentation
│   └── summary.json              # Machine-readable data for tooling
└── artifacts/
    ├── discovered_files/         # Retrieved web content and configs
    ├── wordlists/               # Generated target-specific wordlists  
    └── screenshots/             # Visual evidence (future feature)
```

---

## 🗺️ Roadmap & Current Status

### ✅ **Current Capabilities** (v0.1.0-alpha)
- ✅ **DNS enumeration** with nslookup and dig integration
- ✅ **Host discovery** using dnsx and httpx for subdomain/vhost enumeration
- ✅ **Port scanning** with RustScan + Nmap two-phase discovery
- ✅ **Web application analysis** with directory enumeration and file discovery
- ✅ **Parallel processing** across all reconnaissance phases
- ✅ **Real-time TUI** with live progress and system monitoring

### 🚧 **In Development**
- 🔒 **SSL/TLS certificate analysis** and vulnerability assessment
- 📷 **Screenshot capture** for HTTP/HTTPS services  
- 🧬 **Advanced payload generation** and mutation strategies
- 🎯 **Target scope management** for large engagements

### 📋 **Planned Features**
- 🌐 **API endpoint discovery** and analysis
- 🗃️ **Database service probing** (MySQL, PostgreSQL, MongoDB)
- 📧 **Email enumeration** and OSINT integration
- 🔧 **Custom plugin development** framework
- 📊 **Advanced reporting** with executive summaries

*Contributing to penetration testing automation - one plugin at a time!*

---

## 🤝 Community & Support

### Get Help
- 💬 **[Discord Server](https://discord.gg/ipcrawler)** - Chat with users and get help
- 📖 **[Reddit Community](https://reddit.com/r/ipcrawler)** - Discussions and tips
- 🐛 **[GitHub Issues](https://github.com/ipcrawler/ipcrawler/issues)** - Bug reports and feature requests

### Contributing
While I'm still learning programming, I'm happy to review:
- 🐛 Bug reports with detailed reproduction steps
- 💡 Feature suggestions and use cases
- 📝 Documentation improvements
- 🧪 Testing on different systems

---

## 🔧 Troubleshooting

### File Descriptor Limit
```bash
# Quick fix (current session)
ulimit -n 2048

# Permanent fix - add to ~/.zshrc or ~/.bashrc  
echo "ulimit -n 2048" >> ~/.zshrc
```

### Terminal Size Issues
Ensure your terminal is at least **70x20 characters**. The TUI will warn you if it's too small.

### Tool Installation
```bash
# Core DNS tools (required)
which nslookup dig

# macOS (via Homebrew)
brew install bind

# Ubuntu/Debian  
sudo apt install dnsutils

# Optional reconnaissance tools (for full functionality)
# Port scanning
cargo install rustscan
sudo apt install nmap

# Host discovery  
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Web analysis
cargo install feroxbuster
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
apt install cewl
```

---

## 📄 License

MIT License - feel free to use, modify, and learn from this code.

---

## 🙏 Acknowledgments

- **[Claude Code](https://claude.ai/code)** - The AI pair programming assistant that made this possible
- **[AutoRecon](https://github.com/Tib3rius/AutoRecon)** - Inspiration for building a better alternative
- **The Rust Community** - For creating such an amazing language and ecosystem
- **CTF/HTB Community** - For providing the challenges that drive tool development

---

<div align="center">
<i>Built with ❤️ and lots of AI assistance by a cybersecurity engineer learning to code</i>
</div>