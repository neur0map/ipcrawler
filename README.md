# 🕷️ IPCrawler

> *A modern DNS reconnaissance tool built by a cybersecurity engineer who's learning Rust, powered entirely by AI pair programming*

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Language](https://img.shields.io/badge/language-Rust-orange.svg)
![Status](https://img.shields.io/badge/status-Active%20Development-green.svg)

**🚀 Real-time TUI • 🔍 Multi-tool DNS enumeration • ⚡ Concurrent scanning**

[Discord Server](https://discord.gg/ipcrawler) • [Reddit Community](https://reddit.com/r/ipcrawler) • [Report Issues](https://github.com/ipcrawler/ipcrawler/issues)

</div>

---

## 📖 About This Project

Hi! I'm Carlos, a cybersecurity and networking engineer. While I'm not a programmer by trade, I built this tool entirely with [**Claude Code**](https://claude.ai/code) - an AI pair programming assistant. As someone who spends time on Hack The Box and CTF challenges, I was frustrated with complex tools like [AutoRecon](https://github.com/Tib3rius/AutoRecon) that are hard to set up and customize.

Since the security industry seems to be moving from C to Rust, I decided this would be a perfect opportunity to learn Rust while building something actually useful for my workflow. Every line of code, every feature, and every bug fix has been implemented through careful collaboration with AI - and honestly, I've learned a ton about programming in the process!

**⚠️ Full transparency:** As I'm not an experienced programmer, there might be bugs or issues. I welcome anyone to try the tool and submit issues - I'll review them and work on improvements with my AI coding partner.

---

## ✨ What IPCrawler Does

IPCrawler is a **concurrent DNS reconnaissance tool** that uses both `nslookup` and `dig` simultaneously to perform comprehensive DNS enumeration. It features a real-time terminal interface that shows live results as they come in.

### 🎯 Built For
- **Hack The Box** challenges and labs
- **CTF competitions** and practice
- **Network reconnaissance** during security assessments  
- **DNS enumeration** with immediate visual feedback

### 🛠️ Key Features
- **Real-time TUI**: Live updates with colored results and progress tracking
- **Concurrent scanning**: Both tools run simultaneously for faster results
- **Smart target handling**: Supports domains, IPv4, and IPv6 addresses
- **Comprehensive DNS records**: A, AAAA, MX, NS, TXT, CNAME, SOA, PTR
- **Configurable behavior**: Override tool settings via `global.toml`
- **Detailed artifacts**: All scan results saved with timestamps

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
- **Tools**: `nslookup` and `dig` in PATH
- **Terminal**: Minimum 70x20 characters
- **File descriptors**: ≥1024 (`ulimit -n 2048`)

---

## 🎮 Interface Preview

```
┌─ IPCrawler ──────────────────────────────────────────────────────────────┐
│ Target: google.com | Status: Running | Elapsed: 00:03.2s                │
└──────────────────────────────────────────────────────────────────────────┘
┌─ System ─────────────────────────────────────────────────────────────────┐
│ CPU: 12.3% | RAM: 8.2GB/16.0GB | FDs: 45/2048                           │
└──────────────────────────────────────────────────────────────────────────┘
┌─ Scan Progress ──────────────┬─ Active Tasks ─────────────────────────────┐
│ DNS Reconnaissance           │ • dig queries: Running                     │
│ ████████████████░░░░ 82%     │ • nslookup queries: Running                │
└──────────────────────────────┴─────────────────────────────────────────────┘
┌─ Tabs (←→ to switch) ────────────────────────────────────────────────────┐
│ [Overview] [Ports] [Services] [Logs] [Help]                             │
└──────────────────────────────────────────────────────────────────────────┘
┌─ Results ────────────────────┬─ Live Logs ─────────────────────────────────┐
│ dig A - A: 142.250.80.78     │ 12:34:56 INF Starting dig DNS queries      │
│ dig AAAA - AAAA: 2607:f8b0   │ 12:34:56 INF dig A query completed         │  
│ nslookup MX - MX: smtp.goog  │ 12:34:57 INF nslookup MX query completed   │
│ dig NS - NS: ns1.google.com  │ 12:34:57 INF Found 15 DNS records total    │
└──────────────────────────────┴─────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

IPCrawler uses **optional overrides** - everything works out of the box, but you can customize:

```toml
# ~/.config/ipcrawler/global.toml
# Uncomment sections to override defaults

# [tools.dig]
# command = "/usr/local/bin/dig"
# base_args = ["+short", "+time=2"]
# 
# [tools.dig.options]  
# record_types = ["A", "MX", "NS"]  # Only query these types
# delay_between_queries_ms = 100    # Faster queries
#
# [tools.dig.limits]
# timeout_ms = 5000                 # 5 second timeout
```

**No rebuild required** - configuration changes apply immediately on next scan.

---

## 📁 Output Structure

All scan results are preserved:

```
artifacts/runs/run_google.com_20250825_143022/
├── scans/
│   ├── dig_results.txt           # Raw dig output
│   ├── nslookup_results.txt      # Raw nslookup output
│   └── scan_summary.txt          # Combined results  
└── reports/
    ├── summary.txt               # Human-readable summary
    ├── summary.md                # Markdown report
    └── summary.json              # Machine-readable data
```

---

## 🗺️ Roadmap

This is just the beginning! More plugins are planned:

- 🔍 **Port scanning** (nmap integration)
- 🌐 **HTTP enumeration** (directory bruteforcing) 
- 🔒 **SSL/TLS analysis**
- 📡 **Subdomain discovery**
- 🗂️ **Custom plugin system**

*Want a specific feature? Join our Discord and let me know!*

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

### Tool Not Found
```bash
# Verify required tools
which nslookup dig

# macOS (via Homebrew)
brew install bind

# Ubuntu/Debian  
sudo apt install dnsutils
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