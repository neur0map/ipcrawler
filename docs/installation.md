# ipcrawler Installation Guide

This guide covers the installation of ipcrawler and all its required dependencies across supported platforms.

## Quick Installation

### One-Line Installation (Recommended)

```bash
curl -sSL https://install.ipcrawler.io | bash
```

### Manual Installation

```bash
# Download the installer
curl -L -o install.sh https://raw.githubusercontent.com/your-username/ipcrawler-rust/main/install.sh
chmod +x install.sh

# Run the installer
./install.sh
```

## Supported Platforms

### macOS
- **Versions:** macOS 10.15+ (Catalina and newer)
- **Architectures:** Intel (x86_64) and Apple Silicon (arm64)
- **Package Manager:** Homebrew (will be installed if missing)

### Linux Distributions
- **Ubuntu/Debian:** 18.04+ / Debian 10+
- **CentOS/RHEL/Rocky Linux:** 7+ / 8+
- **Fedora:** 30+
- **Arch Linux:** Current

## What Gets Installed

### Core Dependencies
- **Rust Toolchain** - For building ipcrawler
- **Go** - For Go-based security tools
- **Ruby** - For Ruby-based tools (wpscan)

### Reconnaissance Tools

#### Network Discovery
- **nmap** - Network discovery and security auditing
- **naabu** - Fast port discovery tool
- **arp-scan** - ARP network scanner

#### Web Application Testing
- **httpx** - Fast and multi-purpose HTTP toolkit
- **subfinder** - Subdomain discovery tool
- **gobuster** - Directory/file enumeration tool
- **nuclei** - Fast vulnerability scanner
- **ffuf** - Fast web fuzzer
- **aquatone** - Domain takeover finder

#### SSL/TLS Testing
- **sslscan** - SSL/TLS cipher suite scanner
- **testssl.sh** - SSL/TLS configuration checker

#### Web Server Analysis
- **nikto** - Web server scanner
- **whatweb** - Web technology identifier
- **wpscan** - WordPress security scanner

#### DNS Tools
- **dnsrecon** - DNS enumeration tool

### ipcrawler Core
- **ipcrawler binary** - Main reconnaissance automation tool
- **Configuration files** - Default scan profiles

### Optional Enhancement Tools
- **see** - Interactive markdown renderer for beautiful terminal output
  - Enables new terminal window viewing (130x60)
  - Syntax highlighting and line numbers
  - Install with: `cargo install see-cat`

## Installation Process

The installer performs the following steps:

1. **System Detection**
   - Identifies operating system and distribution
   - Detects available package managers
   - Checks for sudo privileges

2. **Core Dependencies**
   - Installs Rust toolchain
   - Installs Go programming language
   - Installs Ruby (for gem-based tools)

3. **System Packages**
   - Installs tools available through system package managers
   - Updates package repositories as needed

4. **Go Tools**
   - Installs ProjectDiscovery tools (naabu, httpx, subfinder, nuclei)
   - Adds Go bin directory to PATH

5. **GitHub Releases**
   - Downloads and installs tools from GitHub releases
   - Selects appropriate architecture binaries

6. **Special Tools**
   - Downloads testssl.sh script
   - Installs Ruby gems (wpscan)
   - Installs Rust cargo crates (see-cat for markdown rendering)

7. **ipcrawler Installation**
   - Clones ipcrawler source code
   - Builds release binary
   - Installs to /usr/local/bin
   - Installs configuration files to /usr/local/share/ipcrawler

8. **Verification**
   - Tests all tool installations
   - Verifies ipcrawler functionality
   - Retries failed installations (up to 2 attempts)

## Installation Locations

### macOS
```
Binary:         /usr/local/bin/ipcrawler
Configurations: /usr/local/share/ipcrawler/
User Data:      ~/Library/Application Support/io.recon-tool.recon-tool/
```

### Linux
```
Binary:         /usr/local/bin/ipcrawler
Configurations: /usr/local/share/ipcrawler/
User Data:      ~/.local/share/ipcrawler/
```

## Manual Installation Steps

If the automated installer fails or you prefer manual installation:

### 1. Install Dependencies

#### macOS
```bash
# Install Homebrew (if not present)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install core tools
brew install nmap nikto sslscan go rust

# Install Go tools
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Install Ruby tools
gem install wpscan
```

#### Ubuntu/Debian
```bash
# Update packages
sudo apt update

# Install system packages
sudo apt install -y nmap nikto sslscan dnsrecon arp-scan golang-go ruby-full ruby-dev

# Install Go tools
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Install Ruby tools
gem install wpscan

# Install special tools
sudo curl -L https://testssl.sh/testssl.sh -o /usr/local/bin/testssl.sh
sudo chmod +x /usr/local/bin/testssl.sh
```

### 2. Install ipcrawler

```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Clone and build ipcrawler
git clone https://github.com/your-username/ipcrawler-rust.git
cd ipcrawler-rust
cargo build --release

# Install binary and configs
sudo cp target/release/ipcrawler /usr/local/bin/
sudo chmod +x /usr/local/bin/ipcrawler
sudo mkdir -p /usr/local/share/ipcrawler
sudo cp -r config/* /usr/local/share/ipcrawler/
```

## Verification

After installation, verify everything is working:

```bash
# Check ipcrawler version
ipcrawler --version

# List available configurations
ipcrawler --list-tools

# Check system paths
ipcrawler --paths

# Run dependency check
ipcrawler --doctor

# Test with dry run
ipcrawler -t example.com -c quick-scan --dry-run
```

## Troubleshooting

### Common Issues

#### Permission Denied
```bash
# Ensure sudo access
sudo -v

# Re-run installer with explicit sudo
sudo ./install.sh
```

#### Missing Package Managers
```bash
# macOS: Install Homebrew manually
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Linux: Install using your distribution's method
# Ubuntu/Debian: apt is pre-installed
# CentOS: yum/dnf is pre-installed
# Arch: pacman is pre-installed
```

#### Go Tools Not Found
```bash
# Add Go bin to PATH
export PATH="$PATH:$HOME/go/bin"

# Make permanent
echo 'export PATH="$PATH:$HOME/go/bin"' >> ~/.bashrc
source ~/.bashrc
```

#### Ruby Gem Installation Fails
```bash
# Install Ruby development headers
# Ubuntu/Debian
sudo apt install ruby-dev

# CentOS/RHEL
sudo yum install ruby-devel

# Then retry gem installation
gem install wpscan
```

### Log Files

The installer creates logs in `/tmp/ipcrawler-install-*.log` for debugging failed installations.

### Getting Help

1. **Check the logs** - Look for specific error messages
2. **Run doctor** - `ipcrawler --doctor` shows missing dependencies
3. **Manual installation** - Install missing tools individually
4. **Support** - Visit https://ipcrawler.io/support for help

## Updating ipcrawler

### Automatic Update

ipcrawler includes a built-in update command:

```bash
# Update to latest version
ipcrawler --update
```

This will:
- Detect your installation type (cargo, system, or development)
- Download and install the latest version
- Preserve your configurations
- Verify the update was successful

### Manual Update Methods

#### Via Install Script
```bash
# Update using the installer
curl -sSL https://install.ipcrawler.io/update.sh | bash

# Or with the main installer
./install.sh --update

# Or run the update script directly from the repository
./docs/scripts/update.sh
```

#### Via Cargo
```bash
# If installed via cargo
cargo install --force ipcrawler

# From source
cargo install --force --git https://github.com/your-username/ipcrawler-rust.git
```

#### Development Version
```bash
# Pull latest changes
git pull origin main

# Rebuild
cargo build --release

# Install system-wide (optional)
cargo install --path .
```

### Update Verification

After updating, verify the new version:

```bash
# Check version
ipcrawler --version

# Test functionality
ipcrawler --doctor
```

### Rollback

If an update causes issues:

1. **System Installation**: The update script creates a backup at `/usr/local/bin/ipcrawler.backup`
   ```bash
   sudo mv /usr/local/bin/ipcrawler.backup /usr/local/bin/ipcrawler
   ```

2. **Cargo Installation**: Reinstall a specific version
   ```bash
   cargo install --force --version 0.1.0 ipcrawler
   ```

3. **Development**: Git checkout to previous version
   ```bash
   git checkout <previous-commit>
   cargo build --release
   ```

## Uninstallation

To remove ipcrawler:

```bash
# Remove binary
sudo rm /usr/local/bin/ipcrawler

# Remove configurations
sudo rm -rf /usr/local/share/ipcrawler

# Remove user data (optional)
rm -rf ~/.local/share/ipcrawler  # Linux
rm -rf ~/Library/Application\ Support/io.recon-tool.recon-tool  # macOS

# Remove individual tools (optional)
# Use your package manager or remove from Go bin directory
```

## Advanced Configuration

### Custom Installation Directory

```bash
# Install to custom location
INSTALL_DIR="/opt/ipcrawler/bin" ./install.sh

# Add to PATH
export PATH="$PATH:/opt/ipcrawler/bin"
```

### Offline Installation

1. Download all required packages on a connected machine
2. Transfer to target machine
3. Install packages manually
4. Build ipcrawler from source

### Container Installation

```dockerfile
FROM ubuntu:20.04
RUN apt update && apt install -y curl
RUN curl -sSL https://install.ipcrawler.io | bash
```

## Security Considerations

- The installer requires sudo privileges for system-wide installation
- All tools are installed from official sources (GitHub releases, package managers)
- ipcrawler source code is built locally from source
- No binaries are downloaded directly for ipcrawler itself

## Next Steps

After successful installation:

1. **Read the documentation** - https://docs.ipcrawler.io
2. **Try example scans** - Start with `quick-scan` profile
3. **Create custom configs** - Build your own scan profiles
4. **Join the community** - https://ipcrawler.io/community

---

For the latest installation instructions and troubleshooting, visit: https://docs.ipcrawler.io/installation