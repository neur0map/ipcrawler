#!/bin/bash

# ipcrawler Bootstrap Script
# Ensures 'make' is installed on all supported operating systems

set -e

echo "🚀 ipcrawler Bootstrap Script"
echo "============================="
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/os-release ]]; then
        OS_ID=$(grep '^ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
        echo "$OS_ID"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to install make
install_make() {
    local os=$1
    echo "📦 Installing make for $os..."
    
    case $os in
        "macos")
            if command_exists brew; then
                echo "🍺 Installing make via Homebrew..."
                brew install make
            else
                echo "🔧 Installing Xcode Command Line Tools (includes make)..."
                xcode-select --install
                echo "⚠️  Please run this script again after Xcode tools installation completes"
                echo "ℹ️  Or install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        "kali"|"ubuntu"|"debian"|"parrot")
            echo "📦 Installing make via apt..."
            sudo apt update -qq
            sudo apt install -y make build-essential
            ;;
        "arch"|"manjaro")
            echo "📦 Installing make via pacman..."
            sudo pacman -Sy --noconfirm make base-devel
            ;;
        "centos"|"rhel"|"fedora")
            if command_exists dnf; then
                echo "📦 Installing make via dnf..."
                sudo dnf install -y make gcc gcc-c++ kernel-devel
            elif command_exists yum; then
                echo "📦 Installing make via yum..."
                sudo yum groupinstall -y "Development Tools"
                sudo yum install -y make gcc gcc-c++ kernel-devel
            fi
            ;;
        "opensuse"|"suse")
            echo "📦 Installing make via zypper..."
            sudo zypper install -y make gcc gcc-c++
            ;;
        "alpine")
            echo "📦 Installing make via apk..."
            sudo apk add make build-base
            ;;
        "windows")
            echo "🪟 Windows detected. Please install make using one of these options:"
            echo ""
            echo "🎯 Recommended: Install WSL (Windows Subsystem for Linux)"
            echo "   wsl --install"
            echo "   # Then run this script inside WSL"
            echo ""
            echo "🔧 Alternative: Install make via package managers"
            echo "   # Via Chocolatey:"
            echo "   choco install make"
            echo ""
            echo "   # Via Scoop:"
            echo "   scoop install make"
            echo ""
            echo "   # Manual download:"
            echo "   # http://gnuwin32.sourceforge.net/packages/make.htm"
            echo ""
            echo "🐳 Or use Docker (recommended for Windows):"
            echo "   # Install Docker Desktop, then:"
            echo "   # docker run -it --rm -v \$(pwd):/workspace ubuntu bash"
            echo "   # apt update && apt install -y make git"
            exit 1
            ;;
        *)
            echo "❌ Unsupported OS: $os"
            echo "ℹ️  Please install make manually for your system:"
            echo "   - Debian/Ubuntu: sudo apt install make build-essential"
            echo "   - RHEL/CentOS: sudo yum groupinstall 'Development Tools'"
            echo "   - Arch Linux: sudo pacman -S make base-devel"
            echo "   - macOS: xcode-select --install"
            exit 1
            ;;
    esac
}

# Main execution
echo "🔍 Checking for make..."

if command_exists make; then
    echo "✅ make is already installed"
    MAKE_VERSION=$(make --version 2>/dev/null | head -1 || echo "Unknown version")
    echo "   Version: $MAKE_VERSION"
else
    echo "❌ make is not installed"
    echo ""
    
    OS=$(detect_os)
    echo "🔍 Detected OS: $OS"
    echo ""
    
    echo "🚀 Installing make automatically..."
    if install_make "$OS"; then
        echo ""
        echo "✅ make installed successfully!"
        
        # Verify installation
        if command_exists make; then
            MAKE_VERSION=$(make --version 2>/dev/null | head -1 || echo "Unknown version")
            echo "   Version: $MAKE_VERSION"
        else
            echo "⚠️  make installation may require a new shell session"
            echo "ℹ️  Please close and reopen your terminal, then try: make help"
            exit 1
        fi
    else
        echo "❌ Failed to install make automatically"
        echo "ℹ️  Please install make manually and run this script again"
        exit 1
    fi
fi

echo ""
echo "🎯 Now you can use ipcrawler make commands:"
echo "   make help           # Show all available commands"
echo "   make setup          # Set up local environment with security tools"
echo "   make setup-docker   # Set up Docker environment"
echo "   make update         # Update repository, tools, and Docker image"
echo "   make clean          # Clean up installation"
echo ""
echo "🎉 Bootstrap complete!"
echo "📖 Next steps: make help" 