#!/usr/bin/env bash

# IPCrawler Installation Script
# A modern, intelligent installer for network reconnaissance

set -e  # Exit on error

# Colors - unique scheme inspired by terminal phosphor
BLOOD='\033[38;5;88m'      # Deep red for errors
NEON='\033[38;5;46m'       # Electric green for success
AMBER='\033[38;5;214m'     # Warm amber for warnings
STEEL='\033[38;5;67m'      # Steel blue for info
SMOKE='\033[38;5;240m'     # Smoky gray for secondary text
VOLT='\033[38;5;226m'      # High voltage yellow for highlights
GHOST='\033[38;5;255m'     # Off-white for main text
NC='\033[0m'               # No Color

# Unicode symbols
CHECK="■"
CROSS="▪"
ARROW="▸"
INFO="◆"

# Installation directory - get parent directory since script is in scripts/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

# Print colored output
print_color() {
    echo -e "${2}${1}${NC}"
}

# Print header
print_header() {
    echo
    print_color "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓" "${SMOKE}"
    print_color "     IPCrawler // Advanced Network Reconnaissance" "${GHOST}"
    print_color "     Scanning the shadows since $(date +%Y)" "${STEEL}"
    print_color "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓" "${SMOKE}"
    echo
}

# Print step
print_step() {
    echo
    print_color "${ARROW} ${1}" "${STEEL}"
}

# Print success
print_success() {
    print_color "${CHECK} ${1}" "${NEON}"
}

# Print error
print_error() {
    print_color "${CROSS} ${1}" "${BLOOD}"
}

# Print info
print_info() {
    print_color "${INFO} ${1}" "${AMBER}"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO=$ID
        elif [ -f /etc/debian_version ]; then
            DISTRO="debian"
        elif [ -f /etc/redhat-release ]; then
            DISTRO="rhel"
        else
            DISTRO="unknown"
        fi
    else
        OS="unknown"
        DISTRO="unknown"
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Homebrew on macOS
install_homebrew() {
    print_step "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for this session
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f "/usr/local/bin/brew" ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    print_success "Homebrew installed successfully"
}

# Install nmap based on OS
install_nmap() {
    print_step "Installing nmap..."
    
    case $OS in
        "macos")
            if ! command_exists brew; then
                install_homebrew
            fi
            brew install nmap
            ;;
        "linux")
            case $DISTRO in
                "ubuntu"|"debian")
                    sudo apt-get update
                    sudo apt-get install -y nmap
                    ;;
                "fedora"|"rhel"|"centos")
                    sudo yum install -y nmap || sudo dnf install -y nmap
                    ;;
                "arch"|"manjaro")
                    sudo pacman -S --noconfirm nmap
                    ;;
                *)
                    print_error "Unsupported Linux distribution: $DISTRO"
                    print_info "Please install nmap manually"
                    exit 1
                    ;;
            esac
            ;;
        *)
            print_error "Unsupported operating system: $OS"
            exit 1
            ;;
    esac
    
    print_success "nmap installed successfully"
}

# Check and install tools
check_tools() {
    print_step "Checking required tools..."
    
    # Check nmap
    if command_exists nmap; then
        NMAP_VERSION=$(nmap --version | head -n1)
        print_success "nmap found: $NMAP_VERSION"
    else
        print_info "nmap not found"
        install_nmap
    fi
}

# Install Python dependencies
install_python_deps() {
    print_step "Installing Python dependencies..."
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version)
    print_color "Runtime: $PYTHON_VERSION" "${SMOKE}"
    
    # Try normal installation first
    print_info "Installing to user environment..."
    if python3 -m pip install --user -r "${INSTALL_DIR}/requirements.txt" 2>/dev/null; then
        print_success "Python dependencies installed to user environment"
    else
        # If normal installation fails, try with break-system-packages flag
        print_info "Retrying with --break-system-packages flag..."
        if python3 -m pip install --user --break-system-packages -r "${INSTALL_DIR}/requirements.txt"; then
            print_success "Python dependencies installed (with break-system-packages)"
        else
            print_error "Failed to install Python dependencies"
            print_info "Try manually: pip install --user -r ${INSTALL_DIR}/requirements.txt"
            exit 1
        fi
    fi
    
    # Explicitly verify HTTP scanner dependencies
    print_info "Verifying HTTP scanner dependencies..."
    if python3 -c "import httpx, dns.resolver" 2>/dev/null; then
        print_success "HTTP scanner dependencies verified (httpx, dnspython)"
    else
        print_info "Installing HTTP scanner dependencies explicitly..."
        if python3 -m pip install --user httpx dnspython 2>/dev/null || \
           python3 -m pip install --user --break-system-packages httpx dnspython 2>/dev/null; then
            print_success "HTTP scanner dependencies installed"
        else
            print_error "Failed to install HTTP scanner dependencies"
            print_info "HTTP scanning will use fallback mode (limited functionality)"
        fi
    fi
}


# Create system command
create_command() {
    print_step "Creating ipcrawler command..."
    
    # Use ~/.local/bin (no root needed, follows XDG Base Directory spec)
    LOCAL_BIN="$HOME/.local/bin"
    SYMLINK_PATH="$LOCAL_BIN/ipcrawler"
    LAUNCHER_SCRIPT="${INSTALL_DIR}/ipcrawler"
    
    # Create ~/.local/bin if it doesn't exist
    if [ ! -d "$LOCAL_BIN" ]; then
        print_info "Creating ~/.local/bin directory..."
        mkdir -p "$LOCAL_BIN"
    fi
    
    # Remove old symlink if it exists
    if [ -L "$SYMLINK_PATH" ] || [ -f "$SYMLINK_PATH" ]; then
        print_info "Removing old ipcrawler command..."
        rm -f "$SYMLINK_PATH"
    fi
    
    # Create symlink to the launcher script
    print_info "Installing ipcrawler command..."
    ln -sf "$LAUNCHER_SCRIPT" "$SYMLINK_PATH"
    
    # Verify installation
    if [ -L "$SYMLINK_PATH" ]; then
        print_success "Command installed to ~/.local/bin/ipcrawler"
        
        # Check if ~/.local/bin is in PATH
        if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
            print_info "Note: ~/.local/bin is not in your PATH"
            print_info "Add this to your shell config:"
            print_color "     export PATH=\"\$HOME/.local/bin:\$PATH\"" "${VOLT}"
        else
            print_info "No shell reload needed - updates take effect immediately!"
        fi
    else
        print_error "Failed to create command"
        print_info "You can run directly with: ${INSTALL_DIR}/ipcrawler"
    fi
}

# Clean Python cache
clean_cache() {
    print_step "Cleaning Python cache..."
    
    # Remove __pycache__ directories
    find "$INSTALL_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    # Set environment variable to prevent cache creation
    export PYTHONDONTWRITEBYTECODE=1
    
    print_success "Cache cleaned and disabled"
}

# Final setup
final_setup() {
    print_step "Finalizing installation..."
    
    # Make ipcrawler.py executable
    chmod +x "${INSTALL_DIR}/ipcrawler.py"
    
    print_success "Installation completed"
}

# Main installation
main() {
    print_header
    
    print_color "Initializing..." "${SMOKE}"
    print_color "Target: ${VOLT}$INSTALL_DIR${NC}" "${SMOKE}"
    
    # Detect OS
    detect_os
    print_success "Detected OS: $OS ($DISTRO)"
    
    # Check and install tools
    check_tools
    
    # Install Python dependencies
    install_python_deps
    
    # Clean cache
    clean_cache
    
    # Create system command
    create_command
    
    # Final setup
    final_setup
    
    echo
    print_color "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓" "${SMOKE}"
    echo
    print_color "[${NEON}READY${NC}] Installation complete" "${GHOST}"
    echo
    print_color "Start scanning immediately:" "${STEEL}"
    echo
    print_color "     ${VOLT}ipcrawler <target>${NC}" "${GHOST}"
    echo
    print_color "  Example: ${VOLT}ipcrawler 192.168.1.0/24${NC}" "${SMOKE}"
    print_color "           ${VOLT}ipcrawler example.com${NC}" "${SMOKE}"
    print_color "           ${VOLT}ipcrawler 10.0.0.1${NC}" "${SMOKE}"
    echo
    
    # Ask about system-wide command for sudo usage
    print_color "Enable sudo usage (${VOLT}sudo ipcrawler${NC}) by creating system-wide command?" "${STEEL}"
    printf "${STEEL}Create system-wide command? [Y/n]: ${NC}"
    read -r create_system_cmd
    
    if [[ ! "$create_system_cmd" =~ ^[Nn]$ ]]; then
        echo
        print_step "Creating system-wide command..."
        SYSTEM_BIN="/usr/local/bin"
        
        # Create /usr/local/bin if it doesn't exist
        if [ ! -d "$SYSTEM_BIN" ]; then
            if sudo mkdir -p "$SYSTEM_BIN" 2>/dev/null; then
                print_info "Created $SYSTEM_BIN directory"
            else
                print_error "Failed to create $SYSTEM_BIN directory"
                print_info "Try manually: ${VOLT}sudo mkdir -p $SYSTEM_BIN${NC}"
            fi
        fi
        
        # Create system symlink
        if sudo ln -sf "${INSTALL_DIR}/ipcrawler" "$SYSTEM_BIN/ipcrawler" 2>/dev/null; then
            print_success "System-wide command installed to $SYSTEM_BIN/ipcrawler"
            print_color "You can now use: ${VOLT}sudo ipcrawler <target>${NC}" "${STEEL}"
        else
            print_error "Failed to create system-wide command"
            print_info "Try manually: ${VOLT}sudo ln -sf ${INSTALL_DIR}/ipcrawler /usr/local/bin/ipcrawler${NC}"
        fi
        
        echo
        print_color "Note: For optimal sudo performance, install Python deps system-wide:" "${STEEL}"
        print_color "  ${VOLT}sudo pip3 install -r ${INSTALL_DIR}/requirements.txt${NC}" "${STEEL}"
        print_color "  Or: ${VOLT}sudo python3 -m pip install --break-system-packages -r ${INSTALL_DIR}/requirements.txt${NC}" "${STEEL}"
    else
        echo
        print_color "[${VOLT}SKIPPED${NC}] System-wide command creation" "${GHOST}"
        print_color "For sudo usage: ${VOLT}sudo \$(which python3) ${INSTALL_DIR}/ipcrawler.py <target>${NC}" "${STEEL}"
    fi
    echo
    print_color "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓" "${SMOKE}"
    echo
}

# Run main installation
main