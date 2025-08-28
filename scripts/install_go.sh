#!/usr/bin/env bash
# Go Installation and Update Script
# Handles different environments including Hack The Box VMs
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
info() { printf "${BLUE}ℹ${NC} %s\n" "$1"; }
success() { printf "${GREEN}✓${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
error() { printf "${RED}✗${NC} %s\n" "$1"; }

# Configuration
MIN_GO_VERSION="1.19"
RECOMMENDED_GO_VERSION="1.23"
GO_DOWNLOAD_BASE="https://golang.org/dl"

echo "🔧 Go Installation and Update Manager for IPCrawler"
echo "=================================================="
echo

# Detect environment type
detect_environment() {
    local env_type="standard"
    
    # Check for Hack The Box indicators
    if [[ -f "/etc/os-release" ]]; then
        local os_info=$(cat /etc/os-release)
        if [[ "$os_info" == *"Kali"* ]] || [[ "$os_info" == *"Parrot"* ]]; then
            # Check for HTB-specific indicators
            if [[ -d "/home/htb" ]] || [[ -d "/root/Desktop/HTB" ]] || [[ -f "/root/.htb_vm" ]] || pgrep -f "openvpn.*htb" >/dev/null 2>&1; then
                env_type="htb"
            elif [[ -d "/opt/parrot-tools" ]] || [[ -f "/etc/parrot-version" ]]; then
                env_type="parrot"
            else
                env_type="kali"
            fi
        elif [[ "$os_info" == *"Ubuntu"* ]]; then
            if [[ -d "/home/htb" ]] || [[ -f "/root/.htb_vm" ]]; then
                env_type="htb_ubuntu"
            else
                env_type="ubuntu"
            fi
        elif [[ "$os_info" == *"Debian"* ]]; then
            env_type="debian"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        env_type="macos"
    fi
    
    echo "$env_type"
}

# Check current Go installation
check_current_go() {
    local go_path=""
    local go_version=""
    local go_location=""
    
    if command -v go >/dev/null 2>&1; then
        go_path=$(command -v go)
        go_version=$(go version 2>/dev/null | grep -o 'go[0-9.][0-9.]*' | head -n1 | sed 's/go//')
        go_location=$(dirname "$(dirname "$go_path")")
        
        info "Current Go installation found:"
        echo "  Version: $go_version"
        echo "  Location: $go_location"
        echo "  Binary: $go_path"
        echo "  GOPATH: ${GOPATH:-<not set>}"
        echo "  GOROOT: ${GOROOT:-<not set>}"
        
        # Check if version meets minimum requirements
        if version_compare "$go_version" "$MIN_GO_VERSION"; then
            success "Go version $go_version meets minimum requirements ($MIN_GO_VERSION)"
            return 0
        else
            warn "Go version $go_version is below minimum requirements ($MIN_GO_VERSION)"
            return 1
        fi
    else
        warn "Go is not installed or not in PATH"
        return 2
    fi
}

# Compare version numbers
version_compare() {
    local version1=$1
    local version2=$2
    
    # Convert versions to comparable integers
    local v1=$(echo "$version1" | awk -F. '{printf "%d%03d%03d", $1, $2, $3}')
    local v2=$(echo "$version2" | awk -F. '{printf "%d%03d%03d", $1, $2, $3}')
    
    [[ $v1 -ge $v2 ]]
}

# Get system architecture
get_architecture() {
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64) echo "amd64" ;;
        arm64|aarch64) echo "arm64" ;;
        armv7l) echo "armv6l" ;;
        i386|i686) echo "386" ;;
        *) error "Unsupported architecture: $arch"; exit 1 ;;
    esac
}

# Get system OS
get_os() {
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')
    case "$os" in
        linux) echo "linux" ;;
        darwin) echo "darwin" ;;
        *) error "Unsupported OS: $os"; exit 1 ;;
    esac
}

# Download and verify Go
download_go() {
    local version=$1
    local os=$2
    local arch=$3
    local download_dir="/tmp/go_install_$$"
    local filename="go${version}.${os}-${arch}.tar.gz"
    local download_url="${GO_DOWNLOAD_BASE}/${filename}"
    
    info "Downloading Go $version for $os-$arch..."
    mkdir -p "$download_dir"
    
    if command -v curl >/dev/null 2>&1; then
        curl -L "$download_url" -o "$download_dir/$filename"
    elif command -v wget >/dev/null 2>&1; then
        wget "$download_url" -O "$download_dir/$filename"
    else
        error "Neither curl nor wget found. Cannot download Go."
        return 1
    fi
    
    if [[ ! -f "$download_dir/$filename" ]]; then
        error "Download failed: $filename not found"
        return 1
    fi
    
    success "Downloaded $filename"
    echo "$download_dir/$filename"
}

# Install Go - Standard method
install_go_standard() {
    local version=$1
    local os=$2
    local arch=$3
    local install_location="/usr/local"
    
    info "Installing Go $version using standard method..."
    
    # Download Go
    local tarball
    if ! tarball=$(download_go "$version" "$os" "$arch"); then
        error "Failed to download Go"
        return 1
    fi
    
    # Remove existing installation
    if [[ -d "$install_location/go" ]]; then
        warn "Removing existing Go installation at $install_location/go"
        sudo rm -rf "$install_location/go"
    fi
    
    # Extract new installation
    info "Extracting Go to $install_location..."
    sudo tar -C "$install_location" -xzf "$tarball"
    
    # Cleanup
    rm -rf "$(dirname "$tarball")"
    
    success "Go $version installed to $install_location/go"
    return 0
}

# Install Go - HTB specific method
install_go_htb() {
    local version=$1
    local os=$2
    local arch=$3
    local install_location="/opt/go"
    local user_home="${HOME:-/root}"
    
    warn "HTB environment detected - using alternative installation method"
    info "Installing Go $version for HTB environment..."
    
    # Download Go
    local tarball
    if ! tarball=$(download_go "$version" "$os" "$arch"); then
        error "Failed to download Go"
        return 1
    fi
    
    # Create opt directory structure
    sudo mkdir -p /opt
    
    # Remove existing installation
    if [[ -d "$install_location" ]]; then
        warn "Removing existing Go installation at $install_location"
        sudo rm -rf "$install_location"
    fi
    
    # Extract to /opt instead of /usr/local (HTB VMs often have permission issues)
    info "Extracting Go to $install_location..."
    sudo tar -C /opt -xzf "$tarball"
    sudo mv /opt/go "$install_location"
    
    # Set proper permissions for HTB environment
    sudo chown -R root:root "$install_location"
    sudo chmod -R 755 "$install_location"
    
    # Cleanup
    rm -rf "$(dirname "$tarball")"
    
    success "Go $version installed to $install_location"
    
    # HTB-specific PATH configuration
    setup_htb_environment "$install_location" "$user_home"
    
    return 0
}

# Install Go using package manager
install_go_package_manager() {
    local env_type=$1
    
    info "Installing Go using package manager for $env_type..."
    
    case "$env_type" in
        "ubuntu"|"debian"|"kali"|"parrot")
            # Update package list
            sudo apt update
            
            # Remove old Go installation
            sudo apt remove -y golang-go golang golang-1.* 2>/dev/null || true
            
            # Install latest Go
            if [[ "$env_type" == "kali" ]] || [[ "$env_type" == "parrot" ]]; then
                # Kali/Parrot often have more recent versions
                sudo apt install -y golang-go
            else
                # Ubuntu/Debian might need PPA for recent versions
                sudo apt install -y golang-go
            fi
            
            success "Go installed via package manager"
            ;;
        "macos")
            if command -v brew >/dev/null 2>&1; then
                brew install go
                success "Go installed via Homebrew"
            else
                warn "Homebrew not found. Please install Homebrew first or use manual installation."
                return 1
            fi
            ;;
        *)
            warn "Package manager installation not supported for $env_type"
            return 1
            ;;
    esac
}

# Setup HTB-specific environment
setup_htb_environment() {
    local go_root=$1
    local user_home=$2
    
    info "Setting up HTB-specific Go environment..."
    
    # Profile files to update
    local profile_files=(
        "$user_home/.bashrc"
        "$user_home/.zshrc"
        "$user_home/.profile"
        "/root/.bashrc"
        "/root/.zshrc" 
        "/root/.profile"
    )
    
    local go_env="
# Go environment for IPCrawler (HTB optimized)
export GOROOT=\"$go_root\"
export GOPATH=\"\$HOME/go\"
export PATH=\"\$GOROOT/bin:\$GOPATH/bin:\$PATH\"
"
    
    for profile in "${profile_files[@]}"; do
        if [[ -f "$profile" ]]; then
            # Remove any existing Go configuration
            sed -i '/# Go environment for IPCrawler/,+3d' "$profile" 2>/dev/null || true
            sed -i '/export.*GOROOT/d' "$profile" 2>/dev/null || true
            sed -i '/export.*GOPATH/d' "$profile" 2>/dev/null || true
            
            # Add new configuration
            echo "$go_env" >> "$profile"
            success "Updated $profile"
        fi
    done
    
    # Create GOPATH directory
    local gopath="$user_home/go"
    mkdir -p "$gopath/bin" "$gopath/src" "$gopath/pkg"
    
    # Set current session environment
    export GOROOT="$go_root"
    export GOPATH="$gopath"
    export PATH="$GOROOT/bin:$GOPATH/bin:$PATH"
    
    success "HTB Go environment configured"
    info "GOROOT: $GOROOT"
    info "GOPATH: $GOPATH"
    warn "Please restart your shell or run: source ~/.bashrc"
}

# Setup standard environment
setup_standard_environment() {
    local go_root=$1
    local user_home="${HOME:-/root}"
    
    info "Setting up standard Go environment..."
    
    # Profile files to update
    local profile_files=()
    if [[ -f "$user_home/.bashrc" ]]; then
        profile_files+=("$user_home/.bashrc")
    fi
    if [[ -f "$user_home/.zshrc" ]]; then
        profile_files+=("$user_home/.zshrc")
    fi
    if [[ -f "$user_home/.profile" ]]; then
        profile_files+=("$user_home/.profile")
    fi
    
    # If no profile files exist, create .bashrc
    if [[ ${#profile_files[@]} -eq 0 ]]; then
        touch "$user_home/.bashrc"
        profile_files+=("$user_home/.bashrc")
    fi
    
    local go_env="
# Go environment for IPCrawler
export GOPATH=\"\$HOME/go\"
export PATH=\"$go_root/bin:\$GOPATH/bin:\$PATH\"
"
    
    for profile in "${profile_files[@]}"; do
        # Remove any existing Go PATH configuration
        sed -i '/# Go environment for IPCrawler/,+2d' "$profile" 2>/dev/null || true
        
        # Add new configuration
        echo "$go_env" >> "$profile"
        success "Updated $profile"
    done
    
    # Create GOPATH directory
    local gopath="$user_home/go"
    mkdir -p "$gopath/bin" "$gopath/src" "$gopath/pkg"
    
    # Set current session environment
    export GOPATH="$gopath"
    export PATH="$go_root/bin:$GOPATH/bin:$PATH"
    
    success "Standard Go environment configured"
    info "GOPATH: $GOPATH"
    warn "Please restart your shell or run: source ~/.bashrc"
}

# Verify installation
verify_installation() {
    info "Verifying Go installation..."
    
    # Source profile to get new PATH
    if [[ -f "$HOME/.bashrc" ]]; then
        set +u  # Disable undefined variable errors temporarily
        source "$HOME/.bashrc" 2>/dev/null || true
        set -u
    fi
    
    if command -v go >/dev/null 2>&1; then
        local version=$(go version | grep -o 'go[0-9.][0-9.]*' | head -n1 | sed 's/go//')
        success "Go $version is now available"
        
        # Test Go functionality
        info "Testing Go functionality..."
        if go env GOPATH >/dev/null 2>&1; then
            success "Go environment is properly configured"
            echo "  GOPATH: $(go env GOPATH)"
            echo "  GOROOT: $(go env GOROOT)"
            echo "  GOOS: $(go env GOOS)"
            echo "  GOARCH: $(go env GOARCH)"
            return 0
        else
            error "Go environment configuration failed"
            return 1
        fi
    else
        error "Go installation verification failed"
        return 1
    fi
}

# Main installation function
install_or_update_go() {
    local env_type=$1
    local os=$(get_os)
    local arch=$(get_architecture)
    local target_version="$RECOMMENDED_GO_VERSION"
    
    info "Target Go version: $target_version"
    info "Environment: $env_type"
    info "Platform: $os-$arch"
    echo
    
    case "$env_type" in
        "htb"|"htb_ubuntu")
            if ! install_go_htb "$target_version" "$os" "$arch"; then
                error "HTB-specific Go installation failed"
                return 1
            fi
            ;;
        "macos")
            # macOS: Try Homebrew first, then manual
            if command -v brew >/dev/null 2>&1; then
                if ! install_go_package_manager "$env_type"; then
                    warn "Homebrew installation failed, trying manual installation..."
                    install_go_standard "$target_version" "$os" "$arch" || return 1
                    setup_standard_environment "/usr/local/go"
                fi
            else
                install_go_standard "$target_version" "$os" "$arch" || return 1
                setup_standard_environment "/usr/local/go"
            fi
            ;;
        "kali"|"parrot"|"ubuntu"|"debian")
            # Linux: Try package manager first for convenience, then manual for latest version
            if install_go_package_manager "$env_type"; then
                success "Go installed via package manager"
            else
                warn "Package manager installation failed or unavailable, using manual installation..."
                install_go_standard "$target_version" "$os" "$arch" || return 1
                setup_standard_environment "/usr/local/go"
            fi
            ;;
        *)
            # Standard installation for unknown environments
            install_go_standard "$target_version" "$os" "$arch" || return 1
            setup_standard_environment "/usr/local/go"
            ;;
    esac
    
    return 0
}

# Main execution
main() {
    echo
    info "Step 1: Detecting environment..."
    local env_type=$(detect_environment)
    success "Environment detected: $env_type"
    echo
    
    info "Step 2: Checking current Go installation..."
    local go_status=0
    check_current_go || go_status=$?
    echo
    
    case $go_status in
        0)
            success "Go is properly installed and meets requirements"
            info "If you want to update to the latest version, run with --force flag"
            ;;
        1)
            warn "Go version is outdated, updating..."
            install_or_update_go "$env_type" || exit 1
            verify_installation || exit 1
            ;;
        2)
            info "Go is not installed, installing..."
            install_or_update_go "$env_type" || exit 1
            verify_installation || exit 1
            ;;
    esac
    
    echo
    success "Go installation/update completed successfully!"
    echo
    info "Next steps:"
    echo "  • Restart your terminal or run: source ~/.bashrc"
    echo "  • Run 'go version' to verify the installation"
    echo "  • Run 'make install-tools' to install Go-based reconnaissance tools"
    echo
}

# Handle command line arguments
if [[ $# -gt 0 ]] && [[ "$1" == "--force" ]]; then
    info "Force mode enabled - will reinstall Go regardless of current version"
    env_type=$(detect_environment)
    install_or_update_go "$env_type" || exit 1
    verify_installation || exit 1
else
    main "$@"
fi