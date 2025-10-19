#!/bin/bash

# IPCrawler Dependencies Installer
# Installs system dependencies based on detected OS

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        elif [ -f /etc/arch-release ]; then
            echo "arch"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

install_package() {
    local package="$1"
    local os=$(detect_os)
    
    print_info "Installing $package..."
    
    case $os in
        "debian")
            if command -v apt >/dev/null 2>&1; then
                sudo apt update
                sudo apt install -y "$package"
            else
                print_error "apt not found. Cannot install $package"
                return 1
            fi
            ;;
        "redhat")
            if command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y "$package"
            elif command -v yum >/dev/null 2>&1; then
                sudo yum install -y "$package"
            else
                print_error "Neither dnf nor yum found. Cannot install $package"
                return 1
            fi
            ;;
        "arch")
            if command -v pacman >/dev/null 2>&1; then
                sudo pacman -S --noconfirm "$package"
            else
                print_error "pacman not found. Cannot install $package"
                return 1
            fi
            ;;
        "macos")
            if command -v brew >/dev/null 2>&1; then
                brew install "$package"
            else
                print_error "Homebrew not found. Please install Homebrew first: https://brew.sh"
                return 1
            fi
            ;;
        "windows")
            print_error "Automatic installation not supported on Windows"
            return 1
            ;;
        *)
            print_error "Unsupported OS for automatic installation"
            return 1
            ;;
    esac
    
    if command -v "$package" >/dev/null 2>&1; then
        print_success "$package installed successfully"
        return 0
    else
        print_error "Failed to install $package"
        return 1
    fi
}

main() {
    print_info "Detecting operating system..."
    local os=$(detect_os)
    print_success "Detected OS: $os"
    
    # Essential reconnaissance tools
    local tools=(
        "nmap"
        "dnsutils"  # Contains dig on Debian/Ubuntu
        "ping"
        "traceroute"
        "whois"
        "curl"
        "openssl"
    )
    
    # OS-specific package mappings
    case $os in
        "debian")
            tools[1]="dnsutils"  # dig is in dnsutils package
            ;;
        "redhat")
            tools[1]="bind-utils"  # dig is in bind-utils package
            ;;
        "arch")
            tools[1]="bind-tools"  # dig is in bind-tools package
            ;;
        "macos")
            # Most tools come with macOS or are available via brew
            tools=(
                "nmap"
                "bind"  # dig is in bind package
                "ping"  # Usually pre-installed
                "traceroute"  # Usually pre-installed
                "whois"
                "curl"  # Usually pre-installed
                "openssl"  # Usually pre-installed
            )
            ;;
    esac
    
    print_info "Installing essential reconnaissance tools..."
    
    local failed_installs=()
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            print_success "$tool is already installed"
        else
            if install_package "$tool"; then
                print_success "$tool installed successfully"
            else
                print_warning "Failed to install $tool"
                failed_installs+=("$tool")
            fi
        fi
    done
    
    # Additional useful tools
    echo ""
    print_info "Installing additional useful tools..."
    
    local additional_tools=(
        "jq"  # JSON processor
        "wget"
        "git"
    )
    
    for tool in "${additional_tools[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            print_success "$tool is already installed"
        else
            if install_package "$tool"; then
                print_success "$tool installed successfully"
            else
                print_warning "Failed to install $tool"
                failed_installs+=("$tool")
            fi
        fi
    done
    
    # Summary
    echo ""
    print_info "Installation summary:"
    if [ ${#failed_installs[@]} -eq 0 ]; then
        print_success "All tools installed successfully!"
    else
        print_warning "Some tools failed to install:"
        for tool in "${failed_installs[@]}"; do
            echo "  ✗ $tool"
        done
        echo ""
        print_info "You may need to install these manually or check your package manager."
    fi
    
    echo ""
    print_success "Dependency installation complete!"
}

main "$@"