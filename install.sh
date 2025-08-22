#!/bin/bash

################################################################################
# ipcrawler Installation Script
# 
# Professional installation script for ipcrawler reconnaissance tool
# Supports: macOS, Linux (Ubuntu/Debian, CentOS/RHEL/Fedora, Arch)
# 
# Usage: curl -sSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash
#        or: ./install.sh
#
# Copyright (c) 2025 ipcrawler.io
################################################################################

# Colors and formatting
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly GRAY='\033[0;90m'
readonly NC='\033[0m' # No Color
readonly BOLD='\033[1m'

# Global variables
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/usr/local/share/ipcrawler"
TEMP_DIR=""
OS_TYPE=""
DISTRO=""
PACKAGE_MANAGER=""
SUDO_CMD=""
RETRY_COUNT=0
MAX_RETRIES=2

# Required tools for ipcrawler default configurations
declare -A TOOLS=(
    ["nmap"]="Network discovery and security auditing"
    ["naabu"]="Fast port discovery"
    ["httpx"]="HTTP toolkit"
    ["subfinder"]="Subdomain discovery"
    ["gobuster"]="Directory/file brute-forcer"
    ["nuclei"]="Vulnerability scanner"
    ["sslscan"]="SSL/TLS scanner"
    ["nikto"]="Web server scanner"
    ["whatweb"]="Web technology identifier"
    ["dnsrecon"]="DNS enumeration"
    ["arp-scan"]="ARP scanner"
    ["testssl.sh"]="SSL/TLS tester"
    ["wpscan"]="WordPress scanner"
    ["ffuf"]="Fast web fuzzer"
    ["aquatone"]="Domain takeover finder"
    ["see"]="Interactive markdown renderer for scan summaries"
    ["dig"]="DNS lookup utility"
    ["cewl"]="Custom wordlist generator"
    ["jq"]="JSON processor"
)

# Package manager configurations
declare -A APT_PACKAGES=(
    ["nmap"]="nmap"
    ["arp-scan"]="arp-scan"
    ["nikto"]="nikto"
    ["sslscan"]="sslscan"
    ["dnsrecon"]="dnsrecon"
    ["dig"]="dnsutils"
    ["cewl"]="cewl"
    ["jq"]="jq"
)

declare -A HOMEBREW_PACKAGES=(
    ["nmap"]="nmap"
    ["nikto"]="nikto"
    ["sslscan"]="sslscan"
    ["dig"]="bind"
    ["cewl"]="cewl"
    ["jq"]="jq"
)

declare -A GO_TOOLS=(
    ["naabu"]="github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
    ["httpx"]="github.com/projectdiscovery/httpx/cmd/httpx@latest"
    ["subfinder"]="github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    ["nuclei"]="github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
)

declare -A GITHUB_RELEASES=(
    ["gobuster"]="OJ/gobuster"
    ["ffuf"]="ffuf/ffuf"
    ["aquatone"]="michenriksen/aquatone"
)

declare -A SPECIAL_INSTALLS=(
    ["testssl.sh"]="https://testssl.sh/testssl.sh"
    ["wpscan"]="gem:wpscan"
    ["see"]="cargo:see-cat"
)

################################################################################
# Utility Functions
################################################################################

# Enable strict mode after variable declarations
set -euo pipefail

log() {
    echo -e "${WHITE}[$(date +'%H:%M:%S')]${NC} $*"
}

success() {
    echo -e "${GREEN}✓${NC} $*"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

error() {
    echo -e "${RED}✗${NC} $*" >&2
}

info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

header() {
    echo
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD} $*${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
}

cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

check_sudo() {
    if [[ $EUID -eq 0 ]]; then
        SUDO_CMD=""
    else
        if command -v sudo >/dev/null 2>&1; then
            SUDO_CMD="sudo"
            # Test sudo access
            if ! sudo -n true 2>/dev/null; then
                warning "This script requires sudo privileges for system-wide installation"
                echo "Please enter your password when prompted..."
                sudo true
            fi
        else
            error "This script requires sudo privileges but sudo is not available"
            error "Please run as root or install sudo"
            exit 1
        fi
    fi
}

################################################################################
# System Detection
################################################################################

detect_os() {
    header "System Detection"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
        DISTRO="macOS"
        success "Detected: macOS"
        
        if command -v brew >/dev/null 2>&1; then
            PACKAGE_MANAGER="brew"
            success "Package manager: Homebrew"
        else
            warning "Homebrew not found - will install it"
            PACKAGE_MANAGER="brew-install"
        fi
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS_TYPE="linux"
        
        if [[ -f /etc/os-release ]]; then
            source /etc/os-release
            DISTRO="$NAME"
            
            # Detect package manager
            if command -v apt >/dev/null 2>&1; then
                PACKAGE_MANAGER="apt"
            elif command -v yum >/dev/null 2>&1; then
                PACKAGE_MANAGER="yum"
            elif command -v dnf >/dev/null 2>&1; then
                PACKAGE_MANAGER="dnf"
            elif command -v pacman >/dev/null 2>&1; then
                PACKAGE_MANAGER="pacman"
            else
                error "Unsupported package manager"
                exit 1
            fi
            
            success "Detected: $DISTRO"
            success "Package manager: $PACKAGE_MANAGER"
        else
            error "Cannot detect Linux distribution"
            exit 1
        fi
    else
        error "Unsupported operating system: $OSTYPE"
        error "Supported systems: macOS, Linux"
        exit 1
    fi
}

################################################################################
# Dependency Installation Functions
################################################################################

install_homebrew() {
    if ! command -v brew >/dev/null 2>&1; then
        info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for current session
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -f /usr/local/bin/brew ]]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
        
        if command -v brew >/dev/null 2>&1; then
            success "Homebrew installed successfully"
        else
            error "Failed to install Homebrew"
            return 1
        fi
    fi
}

install_rust() {
    if ! command -v cargo >/dev/null 2>&1; then
        info "Installing Rust toolchain..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
        
        if command -v cargo >/dev/null 2>&1; then
            success "Rust installed successfully"
        else
            error "Failed to install Rust"
            return 1
        fi
    else
        success "Rust is already installed"
    fi
}

install_go() {
    if ! command -v go >/dev/null 2>&1; then
        info "Installing Go..."
        
        case "$OS_TYPE" in
            "macos")
                if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
                    brew install go
                fi
                ;;
            "linux")
                case "$PACKAGE_MANAGER" in
                    "apt")
                        $SUDO_CMD apt update --allow-releaseinfo-change
                        $SUDO_CMD apt install -y golang-go
                        ;;
                    "yum"|"dnf")
                        $SUDO_CMD $PACKAGE_MANAGER install -y golang
                        ;;
                    "pacman")
                        $SUDO_CMD pacman -S --noconfirm go
                        ;;
                esac
                ;;
        esac
        
        if command -v go >/dev/null 2>&1; then
            success "Go installed successfully"
        else
            error "Failed to install Go"
            return 1
        fi
    else
        success "Go is already installed"
    fi
}

install_ruby() {
    if ! command -v gem >/dev/null 2>&1; then
        info "Installing Ruby..."
        
        case "$OS_TYPE" in
            "macos")
                if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
                    brew install ruby
                fi
                ;;
            "linux")
                case "$PACKAGE_MANAGER" in
                    "apt")
                        $SUDO_CMD apt update --allow-releaseinfo-change
                        $SUDO_CMD apt install -y ruby-full ruby-dev
                        ;;
                    "yum"|"dnf")
                        $SUDO_CMD $PACKAGE_MANAGER install -y ruby ruby-devel
                        ;;
                    "pacman")
                        $SUDO_CMD pacman -S --noconfirm ruby
                        ;;
                esac
                ;;
        esac
        
        if command -v gem >/dev/null 2>&1; then
            success "Ruby installed successfully"
        else
            error "Failed to install Ruby"
            return 1
        fi
    else
        success "Ruby is already installed"
    fi
}

install_system_packages() {
    local packages_to_install=()
    
    info "Checking system packages..."
    
    case "$OS_TYPE" in
        "macos")
            if [[ "$PACKAGE_MANAGER" == "brew-install" ]]; then
                install_homebrew
                PACKAGE_MANAGER="brew"
            fi
            
            for tool in "${!HOMEBREW_PACKAGES[@]}"; do
                if ! command -v "$tool" >/dev/null 2>&1; then
                    packages_to_install+=("${HOMEBREW_PACKAGES[$tool]}")
                fi
            done
            
            if [[ ${#packages_to_install[@]} -gt 0 ]]; then
                info "Installing: ${packages_to_install[*]}"
                brew install "${packages_to_install[@]}"
            fi
            ;;
            
        "linux")
            case "$PACKAGE_MANAGER" in
                "apt")
                    $SUDO_CMD apt update --allow-releaseinfo-change
                    
                    for tool in "${!APT_PACKAGES[@]}"; do
                        if ! command -v "$tool" >/dev/null 2>&1; then
                            packages_to_install+=("${APT_PACKAGES[$tool]}")
                        fi
                    done
                    
                    if [[ ${#packages_to_install[@]} -gt 0 ]]; then
                        info "Installing: ${packages_to_install[*]}"
                        $SUDO_CMD apt install -y "${packages_to_install[@]}"
                    fi
                    ;;
                    
                "yum"|"dnf")
                    for tool in "${!APT_PACKAGES[@]}"; do
                        if ! command -v "$tool" >/dev/null 2>&1; then
                            # Convert package names if needed
                            local pkg="${APT_PACKAGES[$tool]}"
                            info "Installing: $pkg"
                            $SUDO_CMD $PACKAGE_MANAGER install -y "$pkg"
                        fi
                    done
                    ;;
                    
                "pacman")
                    for tool in "${!APT_PACKAGES[@]}"; do
                        if ! command -v "$tool" >/dev/null 2>&1; then
                            local pkg="${APT_PACKAGES[$tool]}"
                            info "Installing: $pkg"
                            $SUDO_CMD pacman -S --noconfirm "$pkg"
                        fi
                    done
                    ;;
            esac
            ;;
    esac
}

install_go_tools() {
    info "Installing Go-based tools..."
    
    for tool in "${!GO_TOOLS[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            info "Installing $tool..."
            go install "${GO_TOOLS[$tool]}"
        else
            success "$tool is already installed"
        fi
    done
    
    # Ensure Go bin is in PATH
    if [[ ":$PATH:" != *":$HOME/go/bin:"* ]]; then
        export PATH="$PATH:$HOME/go/bin"
        
        # Add to shell profile
        local shell_profile=""
        if [[ -n "${BASH_VERSION:-}" ]]; then
            shell_profile="$HOME/.bashrc"
        elif [[ -n "${ZSH_VERSION:-}" ]]; then
            shell_profile="$HOME/.zshrc"
        fi
        
        if [[ -n "$shell_profile" && -f "$shell_profile" ]]; then
            if ! grep -q "export PATH.*go/bin" "$shell_profile"; then
                echo 'export PATH="$PATH:$HOME/go/bin"' >> "$shell_profile"
                info "Added Go bin directory to $shell_profile"
            fi
        fi
    fi
}

install_github_releases() {
    info "Installing tools from GitHub releases..."
    
    for tool in "${!GITHUB_RELEASES[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            info "Installing $tool..."
            install_github_tool "$tool" "${GITHUB_RELEASES[$tool]}"
        else
            success "$tool is already installed"
        fi
    done
}

install_github_tool() {
    local tool_name="$1"
    local repo="$2"
    local temp_dir=$(mktemp -d)
    
    # Get latest release URL
    local latest_url="https://api.github.com/repos/$repo/releases/latest"
    local download_url=""
    
    case "$OS_TYPE" in
        "macos")
            download_url=$(curl -s "$latest_url" | grep "browser_download_url.*darwin.*amd64\|browser_download_url.*darwin.*arm64" | head -1 | cut -d '"' -f 4)
            ;;
        "linux")
            download_url=$(curl -s "$latest_url" | grep "browser_download_url.*linux.*amd64" | head -1 | cut -d '"' -f 4)
            ;;
    esac
    
    if [[ -n "$download_url" ]]; then
        cd "$temp_dir"
        curl -L -o archive "$download_url"
        
        # Extract based on file type
        if [[ "$download_url" == *.tar.gz ]]; then
            tar -xzf archive
        elif [[ "$download_url" == *.zip ]]; then
            unzip -q archive
        fi
        
        # Find and install binary
        local binary=$(find . -name "$tool_name" -type f -executable | head -1)
        if [[ -n "$binary" ]]; then
            $SUDO_CMD cp "$binary" "$INSTALL_DIR/"
            $SUDO_CMD chmod +x "$INSTALL_DIR/$tool_name"
            success "$tool_name installed successfully"
        else
            error "Could not find $tool_name binary in release"
        fi
    else
        error "Could not find download URL for $tool_name"
    fi
    
    rm -rf "$temp_dir"
}

install_special_tools() {
    info "Installing special tools..."
    
    for tool in "${!SPECIAL_INSTALLS[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            info "Installing $tool..."
            local install_method="${SPECIAL_INSTALLS[$tool]}"
            
            case "$install_method" in
                https://*)
                    # Direct download
                    $SUDO_CMD curl -L "$install_method" -o "$INSTALL_DIR/$tool"
                    $SUDO_CMD chmod +x "$INSTALL_DIR/$tool"
                    ;;
                gem:*)
                    # Ruby gem
                    local gem_name="${install_method#gem:}"
                    gem install "$gem_name"
                    ;;
                cargo:*)
                    # Rust cargo crate
                    local crate_name="${install_method#cargo:}"
                    cargo install "$crate_name"
                    ;;
            esac
        else
            success "$tool is already installed"
        fi
    done
}

################################################################################
# ipcrawler Installation
################################################################################

install_ipcrawler() {
    header "Installing ipcrawler"
    
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    info "Downloading ipcrawler source..."
    git clone https://github.com/neur0map/ipcrawler.git .
    
    info "Building ipcrawler..."
    cargo build --release
    
    info "Installing ipcrawler binary..."
    $SUDO_CMD cp target/release/ipcrawler "$INSTALL_DIR/"
    $SUDO_CMD chmod +x "$INSTALL_DIR/ipcrawler"
    
    info "Installing configuration files..."
    $SUDO_CMD mkdir -p "$CONFIG_DIR"
    $SUDO_CMD cp -r config/* "$CONFIG_DIR/"
    
    success "ipcrawler installed successfully"
}

################################################################################
# Verification Functions
################################################################################

verify_installation() {
    header "Verification"
    
    local failed_tools=()
    local total_tools=${#TOOLS[@]}
    local installed_tools=0
    
    info "Verifying tool installations..."
    echo
    
    for tool in "${!TOOLS[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            success "$tool - ${TOOLS[$tool]}"
            ((installed_tools++))
        else
            error "$tool - Missing"
            failed_tools+=("$tool")
        fi
    done
    
    echo
    
    # Verify ipcrawler
    if command -v ipcrawler >/dev/null 2>&1; then
        success "ipcrawler - Core reconnaissance tool"
        ((installed_tools++))
        ((total_tools++))
        
        # Test ipcrawler functionality
        info "Testing ipcrawler functionality..."
        if ipcrawler --version >/dev/null 2>&1; then
            success "ipcrawler is working correctly"
        else
            warning "ipcrawler installed but not functioning properly"
        fi
    else
        error "ipcrawler - Core reconnaissance tool"
        failed_tools+=("ipcrawler")
        ((total_tools++))
    fi
    
    echo
    echo -e "${BOLD}Installation Summary:${NC}"
    echo -e "  Installed: ${GREEN}$installed_tools${NC}/$total_tools tools"
    
    if [[ ${#failed_tools[@]} -gt 0 ]]; then
        echo -e "  Failed: ${RED}${#failed_tools[@]}${NC} tools"
        echo
        warning "The following tools failed to install:"
        for tool in "${failed_tools[@]}"; do
            echo -e "    ${RED}✗${NC} $tool"
        done
        return 1
    else
        echo -e "  Status: ${GREEN}All tools installed successfully${NC}"
        return 0
    fi
}

retry_failed_installations() {
    header "Retry Failed Installations"
    
    ((RETRY_COUNT++))
    warning "Attempt $RETRY_COUNT of $MAX_RETRIES"
    
    info "Retrying installation of missing dependencies..."
    install_system_packages
    install_go_tools
    install_github_releases
    install_special_tools
    
    # Don't retry ipcrawler installation as it's less likely to fail on retry
    # and more likely to be a source/build issue
}

################################################################################
# Update Functions
################################################################################

update_ipcrawler() {
    header "Updating ipcrawler"
    
    info "Checking current installation..."
    
    if command -v ipcrawler >/dev/null 2>&1; then
        local current_version=$(ipcrawler --version 2>/dev/null | head -1)
        info "Current version: $current_version"
    else
        error "ipcrawler is not installed"
        info "Run the installer instead: ./install.sh"
        exit 1
    fi
    
    # Create temp directory for update
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    info "Downloading latest ipcrawler source..."
    git clone https://github.com/neur0map/ipcrawler.git . >/dev/null 2>&1
    
    if [[ ! -f "Cargo.toml" ]]; then
        error "Failed to download source"
        exit 1
    fi
    
    # Get new version
    local new_version=$(grep "^version" Cargo.toml | cut -d'"' -f2)
    info "Latest version: $new_version"
    
    info "Building latest version..."
    cargo build --release >/dev/null 2>&1
    
    if [[ ! -f "target/release/ipcrawler" ]]; then
        error "Build failed"
        exit 1
    fi
    
    # Backup current binary
    if [[ -f "$INSTALL_DIR/ipcrawler" ]]; then
        $SUDO_CMD cp "$INSTALL_DIR/ipcrawler" "$INSTALL_DIR/ipcrawler.backup"
        info "Current binary backed up to $INSTALL_DIR/ipcrawler.backup"
    fi
    
    # Install new binary
    info "Installing new version..."
    $SUDO_CMD cp target/release/ipcrawler "$INSTALL_DIR/"
    $SUDO_CMD chmod +x "$INSTALL_DIR/ipcrawler"
    
    # Update configuration files if needed
    if [[ -d "config" ]]; then
        info "Updating configuration files..."
        $SUDO_CMD mkdir -p "$CONFIG_DIR"
        $SUDO_CMD cp -r config/* "$CONFIG_DIR/"
    fi
    
    # Verify update
    if ipcrawler --version >/dev/null 2>&1; then
        success "ipcrawler updated successfully!"
        
        # Clean up backup
        $SUDO_CMD rm -f "$INSTALL_DIR/ipcrawler.backup"
    else
        error "Update verification failed"
        warning "Restoring previous version..."
        $SUDO_CMD mv "$INSTALL_DIR/ipcrawler.backup" "$INSTALL_DIR/ipcrawler"
        exit 1
    fi
    
    # Clean up temp directory
    cd /
    rm -rf "$TEMP_DIR"
    
    echo
    success "Update complete!"
    info "Run 'ipcrawler --version' to verify"
}

################################################################################
# Main Installation Flow
################################################################################

show_banner() {
    echo
    echo -e "${CYAN}${BOLD}"
    cat << 'EOF'
    ██╗██████╗  ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗ 
    ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗
    ██║██████╔╝██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝
    ██║██╔═══╝ ██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗
    ██║██║     ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║
    ╚═╝╚═╝      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝
EOF
    echo -e "${NC}"
    echo -e "${WHITE}${BOLD}                Modern IP Reconnaissance Automation Tool${NC}"
    echo -e "${GRAY}                         Professional Installation${NC}"
    echo
}

show_completion() {
    header "Installation Complete"
    
    success "ipcrawler has been successfully installed!"
    echo
    info "Quick start commands:"
    echo -e "  ${CYAN}ipcrawler --help${NC}                    # Show help"
    echo -e "  ${CYAN}ipcrawler --paths${NC}                   # Show configuration paths"
    echo -e "  ${CYAN}ipcrawler -t example.com -c quick-scan${NC} # Run quick scan"
    echo
    info "Configuration files installed to: $CONFIG_DIR"
    info "Binary installed to: $INSTALL_DIR/ipcrawler"
    echo
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${WHITE}${BOLD}  Thank you for using ipcrawler!${NC}"
    echo
    echo -e "  ${CYAN}Website:${NC}    https://ipcrawler.io"
    echo -e "  ${CYAN}Documentation:${NC} https://docs.ipcrawler.io"
    echo -e "  ${YELLOW}Support:${NC}    https://patreon.com/ipcrawler"
    echo
    echo -e "  ${GRAY}Help support development and get priority support on Patreon${NC}"
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
}

main() {
    # Check if running in update mode
    if [[ "${1:-}" == "--update" || "${1:-}" == "-u" ]]; then
        show_banner
        detect_os
        check_sudo
        update_ipcrawler
        exit 0
    fi
    
    show_banner
    
    # System checks
    detect_os
    check_sudo
    
    # Install core dependencies
    header "Installing Core Dependencies"
    install_rust
    install_go
    install_ruby
    
    # Install tools
    header "Installing Reconnaissance Tools"
    install_system_packages
    install_go_tools
    install_github_releases
    install_special_tools
    
    # Install ipcrawler
    install_ipcrawler
    
    # Verification loop
    while [[ $RETRY_COUNT -le $MAX_RETRIES ]]; do
        if verify_installation; then
            show_completion
            exit 0
        elif [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; then
            retry_failed_installations
        else
            break
        fi
    done
    
    # If we reach here, installation failed after retries
    echo
    error "Installation completed with errors after $MAX_RETRIES attempts"
    error "Some tools may not be available. Please check the output above."
    echo
    warning "You can:"
    echo "  1. Install missing tools manually"
    echo "  2. Run this script again"
    echo "  3. Contact support at https://ipcrawler.io/support"
    
    exit 1
}

# Run main function
main "$@"