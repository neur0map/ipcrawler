#!/usr/bin/env bash
# Don't fail on missing optional tools
set -eo pipefail

echo "🔧 Checking required tools..."

# Install and check Go tools
install_go_tool() {
    local tool=$1
    local repo=$2
    local description=$3
    
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool is already installed"
        return 0
    else
        echo "⚠ $tool not found - installing $description"
        if command -v go >/dev/null 2>&1; then
            echo "  Installing: go install -v $repo@latest"
            if go install -v "$repo@latest"; then
                echo "✓ $tool installed successfully"
                return 0
            else
                echo "✗ Failed to install $tool"
                echo "  Try manually: go install -v $repo@latest"
                return 1
            fi
        else
            echo "✗ Go not found - cannot install $tool"
            echo "  Install Go first: https://golang.org/dl/"
            return 1
        fi
    fi
}

# Install and check system tools
install_system_tool() {
    local tool=$1
    local macos_package=$2
    local linux_package=$3
    local description=$4
    
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool is already installed"
        return 0
    else
        echo "⚠ $tool not found - installing $description"
        
        # Detect platform and install accordingly
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS - use Homebrew
            if command -v brew >/dev/null 2>&1; then
                echo "  Installing: brew install $macos_package"
                if brew install "$macos_package" 2>/dev/null; then
                    echo "✓ $tool installed successfully"
                    return 0
                else
                    echo "✗ Failed to install $tool via Homebrew"
                    echo "  Try manually: brew install $macos_package"
                    return 1
                fi
            else
                echo "✗ Homebrew not found - cannot install $tool"
                echo "  Install Homebrew first: https://brew.sh/"
                return 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux - use apt if available
            if command -v apt-get >/dev/null 2>&1; then
                echo "  Installing: sudo apt-get update && sudo apt-get install -y $linux_package"
                if sudo apt-get update && sudo apt-get install -y "$linux_package"; then
                    echo "✓ $tool installed successfully"
                    return 0
                else
                    echo "✗ Failed to install $tool via apt"
                    echo "  Try manually: sudo apt-get install $linux_package"
                    return 1
                fi
            else
                echo "✗ apt-get not found - manual installation required"
                echo "  Install manually: $linux_package"
                return 1
            fi
        else
            echo "✗ Unsupported platform: $OSTYPE"
            echo "  Manual installation required for $tool"
            return 1
        fi
    fi
}

# Check system tools (without auto-install for critical tools)
check_system_tool() {
    local tool=$1
    local install_hint=$2
    
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool is available"
        return 0
    else
        echo "⚠ $tool not found"
        echo "  Install with: $install_hint"
        return 1
    fi
}

# Install and check Rust-based tools
install_rust_tool() {
    local tool=$1
    local crate=$2
    local description=$3
    
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool is already installed"
        return 0
    else
        echo "⚠ $tool not found - installing $description"
        if command -v cargo >/dev/null 2>&1; then
            echo "  Installing: cargo install $crate"
            if cargo install "$crate" --quiet; then
                echo "✓ $tool installed successfully"
                return 0
            else
                echo "✗ Failed to install $tool"
                echo "  Try manually: cargo install $crate"
                return 1
            fi
        else
            echo "✗ cargo not found - cannot install $tool"
            echo "  Install Rust first: https://rustup.rs/"
            return 1
        fi
    fi
}

echo ""
echo "System DNS tools:"
check_system_tool "nslookup" "Usually pre-installed with system"
install_system_tool "dig" "bind" "dnsutils" "DNS lookup tool" || true

echo ""
echo "Go-based reconnaissance tools (for hosts discovery plugin):"
install_go_tool "dnsx" "github.com/projectdiscovery/dnsx/cmd/dnsx" "DNS toolkit" || true
install_go_tool "httpx" "github.com/projectdiscovery/httpx/cmd/httpx" "HTTP toolkit" || true

echo ""
echo "Port scanning tools (for port scanner plugin):"
install_system_tool "nmap" "nmap" "nmap" "network mapper" || true
install_rust_tool "rustscan" "rustscan" "fast port scanner" || true

echo ""
echo "Web application scanning tools (for looter plugin):"
install_go_tool "katana" "github.com/projectdiscovery/katana/cmd/katana" "web crawler" || true
install_go_tool "hakrawler" "github.com/hakluke/hakrawler" "web crawler" || true
install_rust_tool "feroxbuster" "feroxbuster" "directory brute-forcer" || true
install_go_tool "ffuf" "github.com/ffuf/ffuf" "directory fuzzer" || true
install_system_tool "gobuster" "gobuster" "gobuster" "directory brute-forcer" || true
install_rust_tool "xh" "xh" "HTTP client" || true

echo ""
echo "Content analysis tools (for looter plugin):"
install_system_tool "cewl" "cewl" "cewl" "wordlist generator" || true

echo ""
echo "SecLists wordlists (recommended for looter plugin):"
check_seclists_install() {
    local seclists_path="$HOME/.local/share/seclists"
    if [ -d "$seclists_path" ]; then
        echo "✓ SecLists already installed at $seclists_path"
        return 0
    else
        echo "⚠ SecLists not found - installing wordlists"
        echo "  This may take a few minutes..."
        mkdir -p "$(dirname "$seclists_path")"
        if git clone --depth 1 https://github.com/danielmiessler/SecLists.git "$seclists_path" 2>/dev/null; then
            echo "✓ SecLists installed successfully"
            return 0
        else
            echo "✗ Failed to clone SecLists"
            echo "  Try manually: git clone https://github.com/danielmiessler/SecLists.git $seclists_path"
            return 1
        fi
    fi
}
check_seclists_install || true

echo ""
echo "📋 Installation Summary:"
echo "  • All missing tools are automatically installed during 'make build'"
echo "  • DNS tools: nslookup (system), dig (auto-installed via brew/apt)"
echo "  • Go tools: dnsx, httpx, katana, hakrawler, ffuf (auto-installed via 'go install')"
echo "  • Rust tools: rustscan, feroxbuster, xh (auto-installed via cargo)"
echo "  • System tools: nmap, gobuster, cewl (auto-installed via brew/apt)"
echo "  • SecLists wordlists (auto-downloaded from GitHub)"
echo "  • If auto-installation fails, corresponding plugins will be skipped gracefully"
echo ""
echo "💡 Prerequisites for auto-installation:"
echo "  • Homebrew (macOS) or apt (Linux) for system packages"
echo "  • Go compiler for Go-based tools (dnsx, httpx, katana, hakrawler, ffuf)"
echo "  • Rust/Cargo for Rust-based tools (rustscan, feroxbuster, xh)"
echo "  • git for SecLists wordlist download"
echo ""
echo "🔧 Manual installation (if auto-install fails):"
echo "  Go tools:   go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
echo "             go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest"
echo "             go install -v github.com/projectdiscovery/katana/cmd/katana@latest"
echo "             go install -v github.com/hakluke/hakrawler@latest"
echo "             go install -v github.com/ffuf/ffuf@latest"
echo "  Rust tools: cargo install rustscan feroxbuster xh"
echo "  System:     brew install nmap bind gobuster cewl (macOS)"
echo "             sudo apt install nmap dnsutils gobuster cewl (Linux)"
echo "  SecLists:   git clone https://github.com/danielmiessler/SecLists.git ~/.local/share/seclists"