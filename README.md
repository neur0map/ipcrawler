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
# Clone and build with automatic tool installation
git clone https://github.com/ipcrawler/ipcrawler.git
cd ipcrawler
make build

# The build process will:
# ✅ Install ALL reconnaissance tools automatically
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

# Install Go compiler (includes HTB VM support)
make install-go

# Install/update tools only (without rebuilding)
make install-tools

# Check which tools are available
make check-tools
```

### System Requirements
- **Prerequisites**: Homebrew (macOS) or apt (Linux), Rust/Cargo
- **Auto-installed**: Go compiler and all reconnaissance tools are installed automatically
- **Terminal**: Minimum 70x20 characters for TUI
- **File descriptors**: ≥2048 (`ulimit -n 2048`) for concurrent operations

**Tools Installed Automatically:**
- **Go Compiler**: Latest Go (with HTB VM compatibility via `make install-go`)
- **DNS**: `dig` (via system package manager)
- **Go tools**: `dnsx`, `httpx`, `katana`, `hakrawler`, `ffuf` (via `go install`)
- **Rust tools**: `rustscan`, `feroxbuster`, `xh` (via `cargo install`)
- **System tools**: `nmap`, `gobuster`, `cewl` (via system package manager)
- **Wordlists**: SecLists collection (via `git clone`)

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

---

## 🔌 Plugin Ecosystem & Roadmap
# The following list may change as the project evolves and I will be using more external tools instead of reinventing the wheel, but for now this is the plan.
IPCrawler follows a **reconnaissance-only** philosophy - we enumerate and discover, not exploit. All plugins are designed for OSCP exam compliance and responsible security testing.

### ✅ **Currently Implemented Plugins**

| Plugin | Description | Key Features |
|--------|-------------|--------------|
| **nslookup** | DNS record enumeration | A, AAAA, MX, NS, TXT, SOA records |
| **dig** | Advanced DNS queries | AXFR attempts, DNSSEC validation |
| **hosts_discovery** | Subdomain & vhost enumeration | dnsx/httpx integration, automatic /etc/hosts updates |
| **port_scanner** | Two-phase port discovery | RustScan speed + Nmap accuracy, service detection |
| **looter** | Web application analysis | Directory brute-force, sensitive file discovery, auto-analysis of looted files |

### 🚀 **Web Application Security Plugins** (v0.2.0 - Coming Soon)

| Plugin | Description | Scope Limitation |
|--------|-------------|-----------------|
| **Website Code Keywords Analyzer** | Parse HTML/JS for tech hints and sensitive keywords (e.g., password, apiKey, config) | Lightweight parsing only - not reinventing linkfinder/jsfinder |
| **CMS Detector + SQLi Probes** | Identify common CMS (WordPress, Joomla, Drupal) and test basic SQLi payloads | Limited to lightweight probes - not a sqlmap replacement |
| **LFI/Path Traversal Prober** | Classic payload set for ../../etc/passwd, Windows paths, log file inclusions | Curated SecLists payloads only - no aggressive spraying |
| **Cookie & Session Inspector** | Detect base64/JWT cookies, flag missing security flags (HttpOnly, Secure) | Analysis only - no session hijacking capabilities |
| **Form Field Enumerator** | Detect login/register/reset forms, extract parameter names for tool integration | Prepares data for Hydra - doesn't perform authentication attacks |

### 🔧 **Network Service Plugins** (v0.3.0 - Mid-term)

| Plugin | Description | OSCP Relevance |
|--------|-------------|----------------|
| **SMB Enumerator** | Test for null sessions, enumerate users, check SMB signing status | Classic OSCP enumeration technique |
| **SNMP Walker Lite** | Quick snmpwalk with default communities (public, private), extract system info | Essential for OSCP lab environments |
| **Auth & Login Hunter** | Detect login panels across services, enumerate authentication parameters | Preparation for credential testing only |
| **FTP Prober** | Anonymous login checks, banner grabbing, directory listing | Common CTF/OSCP service |
| **SSH Enumerator** | Version detection, weak algorithm detection, user enumeration timing attacks | Information gathering only |

### 🔬 **Advanced Analysis Plugins** (v0.4.0 - Long-term)

| Plugin | Description | Integration Notes |
|--------|-------------|-------------------|
| **Tech Fingerprinting Add-On** | Headers + favicon hash + TLS fingerprinting to identify tech stack | Leverages existing Wappalyzer signatures |
| **File Decryptor Integration** | When encrypted files are found, pass to John the Ripper or Hashcat | Lightweight wrapper - requires external tools |
| **Hydra Integration Lite** | Controlled credential testing with generated wordlists | Rate-limited, single-threaded to avoid account lockouts |
| **API Endpoint Mapper** | Discover and document REST/GraphQL endpoints | Focus on enumeration, not fuzzing |
| **Certificate Analyzer** | SSL/TLS certificate chain analysis, expiry warnings, weak ciphers | Security assessment only |

### ⚠️ **Important Scope Notes**

- **Enumeration Only**: IPCrawler is a reconnaissance tool, not an exploitation framework
- **OSCP Compliant**: All plugins follow OSCP exam restrictions (no automatic exploitation)
- **Lightweight Probes**: We prioritize speed and stealth over comprehensive coverage
- **Responsible Use**: Designed for authorized security testing and CTF competitions only
- **Time-Bounded**: Each plugin respects time budgets to prevent hanging on slow targets
- **No Brute Force**: Authentication testing is limited to common defaults, not dictionary attacks

### 🎯 **Design Philosophy**

Each plugin follows these principles:
1. **Fast**: Complete within 2-minute time budgets
2. **Focused**: Do one thing well, not everything poorly
3. **Safe**: No destructive operations or DoS conditions
4. **Informative**: Provide actionable intelligence for manual testing
5. **Integrated**: Work seamlessly with other plugins and external tools

*Want to contribute a plugin? Check our [Plugin Development Guide](docs/PLUGIN_DEVELOPMENT.md) for the implementation spec!*

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

### Go Compiler Issues (HTB VMs)
```bash
# HTB VM / KALI SPECIFIC (automatic detection and handling)
make install-go       # Installs Go with HTB VM compatibility

# The script automatically detects HTB environments and:
# • Uses /opt/go instead of /usr/local/go for better permissions
# • Updates multiple shell profiles (.bashrc, .zshrc, .profile)
# • Sets proper GOPATH and GOROOT environment variables
# • Works around HTB VM permission restrictions

# Force reinstall Go (if current installation is broken)
bash scripts/install_go.sh --force
```

### Tool Installation Issues  
```bash
# AUTOMATIC INSTALLATION (recommended)
make install-tools    # Install all tools automatically
make check-tools      # Verify installation status

# MANUAL INSTALLATION (if automatic fails)
# Prerequisites
# macOS: brew install go rust
# Linux: sudo apt install golang rustc cargo

# Go tools
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/hakluke/hakrawler@latest
go install -v github.com/ffuf/ffuf@latest

# Rust tools
cargo install rustscan feroxbuster xh

# System tools
# macOS: brew install nmap bind gobuster cewl
# Linux: sudo apt install nmap dnsutils gobuster cewl

# Wordlists
git clone https://github.com/danielmiessler/SecLists.git ~/.local/share/seclists
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