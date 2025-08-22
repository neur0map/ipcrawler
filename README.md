# ipcrawler

A streamlined reconnaissance automation tool built for CTF players and security enthusiasts. Born from the need to simplify repetitive scanning workflows during Hack The Box challenges.

[![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://www.linux.org/)
[![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)](https://www.apple.com/macos/)

## About

As a cybersecurity and network engineering student, I built ipcrawler to solve a personal frustration: running the same reconnaissance commands repeatedly during CTF competitions. Instead of maintaining sprawling cheatsheets and copy-pasting commands, I wanted a single tool that could orchestrate multiple scanners intelligently.

This project is developed with AI assistance as part of my learning journey. It's designed to be more approachable than existing tools like autorecon (Python) or reconnoitre (Go), especially for those just starting with security assessments.

## Why ipcrawler?

- **CTF-Focused**: Built specifically for Hack The Box and CTF scenarios
- **YAML Workflows**: Define reusable scan profiles for different machine types
- **Parallel Execution**: Run multiple tools simultaneously with smart concurrency
- **Tool Chaining**: Automatically pipe outputs between tools (e.g., naabu → nmap)
- **Interactive Summary Viewing**: Beautiful markdown reports with terminal window integration
- **Beginner Friendly**: Clear output, simple configuration, minimal learning curve

## Why Rust?

The journey to Rust wasn't straightforward. This project began in Python, but as it grew in complexity, silent errors became increasingly difficult to track down and debug. The additional configuration overhead required to run on Hack The Box machines (requiring source code cloning instead of simple binary deployment) further complicated the development process.

I then explored Go for its excellent binary compilation features, but encountered the same silent error issues that plagued the Python version. When attempting to build a TUI interface, Go presented inconsistent failures that were difficult to diagnose—especially challenging for someone learning to code with AI assistance.

**Rust solved these core problems:**
- **Compile-time Error Detection**: Rust's compiler catches errors before runtime, eliminating the silent failures that plagued previous versions
- **Memory Safety**: No segfaults or memory leaks to debug in production
- **Excellent Concurrency**: Built-in support for safe parallel and concurrent execution, crucial for running multiple scanning tools simultaneously
- **Single Binary Deployment**: Easy distribution and installation on CTF environments
- **Strong Community**: Large, helpful community with extensive documentation and AI-friendly error messages

While Rust has a steep learning curve and can be challenging for AI-assisted development, the compiler's detailed error messages and the community's focus on helpful tooling made it manageable. The investment in learning Rust paid off with significantly more reliable and maintainable code, especially for the complex concurrent execution patterns required for effective reconnaissance automation.

**A Learning Journey**: My understanding of Rust is still in its baby steps—I'm learning the language as I build this project. However, I'm committed to continuing this learning journey and evolving ipcrawler alongside my growing Rust knowledge. This project represents not just a tool for the cybersecurity community, but also a way to contribute back while learning. Every challenge overcome and feature added helps both my development as a programmer and provides value to fellow CTF players and security enthusiasts.

## Quick Start

### One-Line Installation

```bash
curl -sSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash
```

### Manual Installation

<details>
<summary>Prerequisites</summary>

```bash
# Install Rust (includes cargo)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Install Go (for ProjectDiscovery tools)
# macOS
brew install go

# Linux
sudo apt install golang-go  # Debian/Ubuntu
sudo dnf install golang      # Fedora

# Verify installations
cargo --version
go version
```
</details>

<details>
<summary>Build from Source</summary>

**Step 1: Clone and build ipcrawler** (all platforms)
```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
cargo build --release
cargo install --path .
```

**Step 2: Install reconnaissance tools**

*macOS:*
```bash
# Core Go tools
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# System packages
brew install nmap nikto sslscan

# Optional tools
go install github.com/OJ/gobuster/v3@latest
go install github.com/ffuf/ffuf@latest

# Interactive markdown viewer (optional but recommended)
cargo install see-cat
```

*Linux (Debian/Ubuntu):*
```bash
# Core Go tools
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# System packages
sudo apt install nmap nikto sslscan dnsrecon arp-scan

# Optional tools
go install github.com/OJ/gobuster/v3@latest
go install github.com/ffuf/ffuf@latest

# Interactive markdown viewer (optional but recommended)
cargo install see-cat
```

*Linux (Fedora/RHEL):*
```bash
# Core Go tools (same as above)
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# System packages
sudo dnf install nmap nikto sslscan

# Optional tools
go install github.com/OJ/gobuster/v3@latest
go install github.com/ffuf/ffuf@latest

# Interactive markdown viewer (optional but recommended)
cargo install see-cat
```

**Step 3: Verify installation**
```bash
ipcrawler --doctor  # Check tool availability
```
</details>

### Developer Mode (No Installation)

```bash
# Clone and run directly
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler

# Run without installing
cargo run -- -t example.com -c quick-scan

# Or build and use the binary directly, you still need to install the tools manually
cargo build --release
./target/release/ipcrawler -t example.com -c quick-scan
```

## Usage

### Basic Scanning

```bash
# Quick scan with default profile
ipcrawler -t 10.10.10.1

# Use specific scan profile
ipcrawler -t box.htb -c web-scan

# Multiple profiles in parallel
ipcrawler -t target.htb -c quick-scan,network-scan

# Custom output location
ipcrawler -t target.htb -c quick-scan -o ~/htb/results
```

### Interactive Summary Viewing

After each scan completes, ipcrawler offers an enhanced viewing experience:

```bash
📁 Results Location
Mode: Development Mode  
Path: ./recon-results/target_2024-08-21_15-30-45
Generated Reports:
  • scan_summary.json -> Full structured data with raw outputs
  • scan_summary.html -> Interactive web report
  • scan_summary.md   -> Documentation format
  • scan_summary.txt  -> Terminal-friendly summary

📖 Do you want to view the markdown summary? [y/N]: y
Opening markdown summary in new terminal window...
✅ Markdown summary opened in new terminal window (130x60)
```

**Features:**
- 🪟 **New terminal window** opens automatically (130 columns × 60 rows)
- 🎨 **Syntax highlighting** for code blocks and structured data  
- 📄 **Line numbers** for easy reference
- 🔗 **Clickable links** in supported terminals
- ⏸️ **Stay-open prompt** - window remains until you close it

**Requirements:** Install the optional `see` markdown renderer:
```bash
cargo install see-cat
```

### Available Profiles

| Profile | Purpose | Tools |
|---------|---------|-------|
| `quick-scan` | Fast initial assessment | naabu, nmap, httpx |
| `network-scan` | Network infrastructure | ping sweep, port scan, service detection |
| `web-scan` | Web application focus | subdomain enum, directory fuzzing, nuclei |
| `enterprise-scan` | Comprehensive scanning | All tools, extended timeouts |

### Creating Custom Profiles

```yaml
# ~/.config/ipcrawler/profiles/ctf-web.yaml
metadata:
  name: "CTF Web Box"
  description: "Quick web-focused scan for CTF"

tools:
  - name: "port_scan"
    command: "naabu -host {target} -top-ports 1000 -o {output}/ports.txt"
    timeout: 60

  - name: "service_scan"
    command: "nmap -sV -sC {target} -p {discovered_ports} -oX {output}/nmap.xml"
    timeout: 300

chains:
  - from: "port_scan"
    to: "service_scan"
    condition: "has_output"
```

## ipcrawler Commands

| Flag | Description |
|------|-------------|
| `-t`, `--target <target>` | IP address or hostname to scan |
| `-c`, `--config <profile>` | Configuration profile (comma-separated for multiple) |
| `-o`, `--output <path>` | Output directory for results |
| `-l`, `--list` | List all available configuration profiles |
| `--list-tools` | Show available tools in configuration |
| `--validate` | Validate configuration file and exit |
| `--doctor` | Check system dependencies |
| `--update` | Update to latest version |
| `--dry-run` | Preview execution plan without running |
| `--resume <path>` | Resume interrupted scan from output directory |
| `--paths` | Show directory paths for configs and outputs |
| `-d`, `--debug` | Enable debug mode with verbose logging |
| `-v`, `--verbose` | Enable verbose output |

## Tools Overview

### Currently Active Tools (Default Profile)

The default scan profile (`default.yaml`) currently uses these tools:

| Tool | Purpose | Usage in Profile |
|------|---------|------------------|
| **naabu** | Fast port discovery | Initial port scanning with top 1000 ports |
| **nmap** | Network discovery & service detection | Detailed service scanning on discovered ports |

*Tool chaining*: naabu → nmap (discovered ports are automatically passed to nmap)

### Available Tools (Installed but Not Yet Configured)

The installation script sets up a comprehensive toolkit ready for use in custom profiles:

#### 🔍 **Discovery & Reconnaissance**
| Tool | Purpose | Source |
|------|---------|--------|
| **httpx** | HTTP toolkit for web discovery | Go (ProjectDiscovery) |
| **subfinder** | Subdomain enumeration | Go (ProjectDiscovery) |
| **dnsrecon** | DNS enumeration and reconnaissance | System package |
| **arp-scan** | ARP network discovery | System package |
| **whatweb** | Web technology identification | System package |

#### 🎯 **Vulnerability Scanning**
| Tool | Purpose | Source |
|------|---------|--------|
| **nuclei** | Modern vulnerability scanner | Go (ProjectDiscovery) |
| **nikto** | Web server vulnerability scanner | System package |
| **testssl.sh** | SSL/TLS security testing | Direct download |
| **wpscan** | WordPress security scanner | Ruby gem |

#### 🔨 **Directory & Content Discovery**
| Tool | Purpose | Source |
|------|---------|--------|
| **gobuster** | Directory/file brute-forcer | GitHub release |
| **ffuf** | Fast web fuzzer | GitHub release |

#### 🛡️ **SSL/TLS Analysis**
| Tool | Purpose | Source |
|------|---------|--------|
| **sslscan** | SSL/TLS configuration analyzer | System package |
| **testssl.sh** | Comprehensive SSL/TLS testing | Direct download |

#### 🌐 **Domain & Takeover Detection**
| Tool | Purpose | Source |
|------|---------|--------|
| **aquatone** | Domain takeover detection | GitHub release |

### Enhancement Tools

#### 📖 **Interactive Report Viewing**
| Tool | Purpose | Installation |
|------|---------|-------------|
| **see** | Beautiful markdown rendering in terminal windows | `cargo install see-cat` |

**Features:**
- Opens scan summaries in new terminal windows (130x60)
- Syntax highlighting for structured data
- Line numbers and clickable links
- Stay-open prompt for easy reference

### Creating Custom Profiles

All installed tools are available for use in custom YAML profiles. Example usage patterns:

```yaml
# Web-focused reconnaissance
tools:
  - name: "subdomain_enum"
    command: "subfinder -d {target} -o {output}/subdomains.txt"
  
  - name: "web_probe"
    command: "httpx -l {output}/subdomains.txt -o {output}/live_hosts.txt"
  
  - name: "vulnerability_scan"
    command: "nuclei -l {output}/live_hosts.txt -o {output}/vulnerabilities.txt"

# Directory discovery chain
  - name: "directory_scan"
    command: "gobuster dir -u {target} -w /usr/share/wordlists/common.txt -o {output}/directories.txt"
```

### Installation Status

✅ **Automatically Installed**: All tools listed above are installed during the setup process
⚠️ **Configuration Needed**: Tools require YAML profile configuration to be utilized
📚 **Documentation**: See `docs/` directory for profile creation guides

## Project Structure

```
ipcrawler-rust/
├── config/           # Scan profiles
├── src/              # Rust source
├── docs/             # Documentation
│   └── scripts/      # Utility scripts
└── testing/          # Test configs
```

## Community

Join our growing community of CTF players and security enthusiasts:

- **Discord**: [discord.gg/ipcrawler](https://discord.gg/ipcrawler)
- **Reddit**: [r/ipcrawler](https://reddit.com/r/ipcrawler)
- **Issues**: [GitHub Issues](https://github.com/neur0map/ipcrawler/issues)

## Development

This is an active learning project. Contributions, feedback, and suggestions are welcome. If you're also learning security or want to help make reconnaissance more accessible, feel free to contribute.

## Disclaimer

ipcrawler is intended for authorized security testing only. Users are responsible for complying with all applicable laws and obtaining proper authorization before scanning any systems.

## License

MIT License - See LICENSE file for details

---

*Built with AI assistance and a lot of trial and error by a security student trying to make CTFs a bit easier.*