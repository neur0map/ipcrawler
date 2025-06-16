#!/bin/bash

# ========================================
# ipcrawler Cache Reset Script
# ========================================
# Clears all Python cache, ipcrawler cache, and rebuilds application
# Usage: make reset

set -e

echo "🔄 ipcrawler Cache Reset - Clearing all static cache and rebuilding..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ========================================
# 1. OS Detection using detect-os.sh
# ========================================
print_status "Detecting operating system..."

# Source the OS detection script
if [ -f "scripts/detect-os.sh" ]; then
    source scripts/detect-os.sh
    # OS_ID is already set by detect-os.sh
    print_success "Detected OS: $OS_ID"
else
    # Fallback OS detection
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS_ID="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            OS_ID=$(grep '^ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
        else
            OS_ID="linux"
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS_ID="windows"
    else
        OS_ID="unknown"
    fi
    print_warning "Using fallback OS detection: $OS_ID"
fi

# Check for WSL
WSL_DETECTED="no"
if [ -n "${WSL_DISTRO_NAME:-}" ] || [ -n "${WSL_INTEROP:-}" ] || grep -qi microsoft /proc/version 2>/dev/null; then
    WSL_DETECTED="yes"
    print_success "WSL environment detected"
fi

echo ""

# ========================================
# 2. Clear Python Bytecode Cache
# ========================================
print_status "Clearing Python bytecode cache..."

# Remove __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
print_success "Removed __pycache__ directories"

# Remove .pyc files
find . -name "*.pyc" -delete 2>/dev/null || true
print_success "Removed .pyc files"

# Remove .pyo files
find . -name "*.pyo" -delete 2>/dev/null || true
print_success "Removed .pyo files"

echo ""

# ========================================
# 3. Clear ipcrawler Application Cache (OS-specific)
# ========================================
print_status "Clearing ipcrawler application cache for $OS_ID..."

case "$OS_ID" in
    "macos")
        # macOS Application Support
        MACOS_CACHE="$HOME/Library/Application Support/ipcrawler"
        if [ -d "$MACOS_CACHE" ]; then
            print_warning "Found macOS Application Support cache - preserving user configs"
            # Remove cache but preserve configs
            find "$MACOS_CACHE" -name "*.cache" -delete 2>/dev/null || true
            find "$MACOS_CACHE" -name "*.tmp" -delete 2>/dev/null || true
            find "$MACOS_CACHE" -name "*.log" -delete 2>/dev/null || true
            print_success "Cleared macOS Application Support cache"
        fi
        
        # Clear pip cache
        if command -v pip &> /dev/null; then
            CACHE_INFO=$(pip cache info 2>/dev/null || echo "No cache info available")
            pip cache purge 2>/dev/null || true
            echo "$CACHE_INFO"
            print_success "Cleared pip cache"
        fi
        ;;
        
    "kali"|"parrot"|"ubuntu"|"debian")
        # Linux XDG cache directories
        XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
        IPCRAWLER_CACHE="$XDG_CACHE_HOME/ipcrawler"
        
        if [ -d "$IPCRAWLER_CACHE" ]; then
            rm -rf "$IPCRAWLER_CACHE"
            print_success "Cleared XDG cache directory"
        fi
        
        # Clear pip cache
        if command -v pip &> /dev/null; then
            pip cache purge 2>/dev/null || true
            print_success "Cleared pip cache"
        fi
        
        # Kali/Parrot specific cache
        if [ "$OS_ID" = "kali" ] || [ "$OS_ID" = "parrot" ]; then
            # Clear any penetration testing tool caches
            rm -rf ~/.msf4/logs/* 2>/dev/null || true
            rm -rf ~/.local/share/nmap/* 2>/dev/null || true
            print_success "Cleared penetration testing tool caches"
        fi
        ;;
        
    "fedora"|"rhel"|"centos"|"arch"|"manjaro")
        # Standard Linux cache
        XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
        IPCRAWLER_CACHE="$XDG_CACHE_HOME/ipcrawler"
        
        if [ -d "$IPCRAWLER_CACHE" ]; then
            rm -rf "$IPCRAWLER_CACHE"
            print_success "Cleared XDG cache directory"
        fi
        
        # Clear pip cache
        if command -v pip &> /dev/null; then
            pip cache purge 2>/dev/null || true
            print_success "Cleared pip cache"
        fi
        ;;
        
    "windows")
        # Windows AppData cache
        if [ -n "${APPDATA:-}" ]; then
            WINDOWS_CACHE="$APPDATA/ipcrawler"
            if [ -d "$WINDOWS_CACHE" ]; then
                rm -rf "$WINDOWS_CACHE"
                print_success "Cleared Windows AppData cache"
            fi
        fi
        
        # Clear pip cache
        if command -v pip &> /dev/null; then
            pip cache purge 2>/dev/null || true
            print_success "Cleared pip cache"
        fi
        ;;
        
    *)
        # Generic cache clearing
        USER_CACHE="$HOME/.cache/ipcrawler"
        if [ -d "$USER_CACHE" ]; then
            rm -rf "$USER_CACHE"
            print_success "Cleared user cache directory"
        fi
        
        # Clear pip cache
        if command -v pip &> /dev/null; then
            pip cache purge 2>/dev/null || true
            print_success "Cleared pip cache"
        fi
        ;;
esac

# WSL-specific cache clearing
if [ "$WSL_DETECTED" = "yes" ]; then
    print_status "WSL detected - clearing additional cache..."
    
    # Clear Windows temp if accessible
    if [ -d "/mnt/c/Users" ]; then
        find /mnt/c/Users/*/AppData/Local/Temp -name "*ipcrawler*" -delete 2>/dev/null || true
        print_success "Cleared Windows temp cache"
    fi
fi

echo ""

# ========================================
# 4. Clear Virtual Environment and Build Cache
# ========================================
print_status "Clearing virtual environment cache..."

# Remove virtual environments
rm -rf venv/ 2>/dev/null || true
rm -rf .venv/ 2>/dev/null || true
print_success "Removed existing virtual environment"

print_status "Clearing build artifacts..."

# Remove build directories
rm -rf build/ 2>/dev/null || true
rm -rf dist/ 2>/dev/null || true
rm -rf *.egg-info/ 2>/dev/null || true
print_success "Removed build artifacts"

# Remove any compiled extensions (OS-specific)
find . -name "*.so" -delete 2>/dev/null || true      # Linux
find . -name "*.dylib" -delete 2>/dev/null || true   # macOS
find . -name "*.dll" -delete 2>/dev/null || true     # Windows
find . -name "*.pyd" -delete 2>/dev/null || true     # Windows Python extensions

echo ""

# ========================================
# 5. Clear Docker Cache (if Docker is available)
# ========================================
if command -v docker &> /dev/null; then
    print_status "Clearing Docker cache..."
    
    # Remove ipcrawler Docker images
    docker rmi ipcrawler 2>/dev/null || true
    docker rmi $(docker images -q --filter "reference=ipcrawler*") 2>/dev/null || true
    
    # Prune Docker build cache
    docker builder prune -f 2>/dev/null || true
    
    print_success "Cleared Docker cache"
else
    print_warning "Docker not available - skipping Docker cache cleanup"
fi

echo ""

# ========================================
# 6. Clear System-specific Package Cache
# ========================================
print_status "Clearing system-specific package cache for $OS_ID..."

case "$OS_ID" in
    "macos")
        # Clear Homebrew cache
        if command -v brew &> /dev/null; then
            brew cleanup 2>/dev/null || true
            print_success "Cleared Homebrew cache"
        fi
        ;;
        
    "kali"|"parrot"|"ubuntu"|"debian")
        # Clear APT cache
        if command -v apt &> /dev/null; then
            sudo apt autoremove -y 2>/dev/null || print_warning "Could not run apt autoremove (may need sudo)"
            sudo apt autoclean 2>/dev/null || print_warning "Could not run apt autoclean (may need sudo)"
            print_success "Cleared APT cache"
        fi
        
        # Clear snap cache if available
        if command -v snap &> /dev/null; then
            sudo snap refresh 2>/dev/null || true
            print_success "Refreshed snap packages"
        fi
        ;;
        
    "fedora"|"rhel"|"centos")
        # Clear YUM/DNF cache
        if command -v dnf &> /dev/null; then
            sudo dnf clean all 2>/dev/null || print_warning "Could not run dnf clean (may need sudo)"
            print_success "Cleared DNF cache"
        elif command -v yum &> /dev/null; then
            sudo yum clean all 2>/dev/null || print_warning "Could not run yum clean (may need sudo)"
            print_success "Cleared YUM cache"
        fi
        ;;
        
    "arch"|"manjaro")
        # Clear Pacman cache
        if command -v pacman &> /dev/null; then
            sudo pacman -Sc --noconfirm 2>/dev/null || print_warning "Could not run pacman -Sc (may need sudo)"
            print_success "Cleared Pacman cache"
        fi
        
        # Clear AUR helper cache if available
        if command -v yay &> /dev/null; then
            yay -Sc --noconfirm 2>/dev/null || true
            print_success "Cleared AUR cache"
        fi
        ;;
        
    *)
        print_warning "Unknown OS - skipping system package cache cleanup"
        ;;
esac

# WSL-specific package management
if [ "$WSL_DETECTED" = "yes" ]; then
    print_status "WSL detected - ensuring Windows integration..."
    # Clear any Windows Python cache if accessible
    if command -v python.exe &> /dev/null; then
        python.exe -m pip cache purge 2>/dev/null || true
        print_success "Cleared Windows Python cache"
    fi
fi

echo ""

# ========================================
# 7. Rebuild Application
# ========================================
print_status "Rebuilding ipcrawler application..."

# Recreate virtual environment
print_status "Creating fresh virtual environment..."
python3 -m venv venv
print_success "Created new virtual environment"

# Activate virtual environment (OS-specific activation)
if [ "$WSL_DETECTED" = "yes" ] || [[ "$OS_ID" == *"windows"* ]]; then
    # WSL or Windows-like environment
    source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null || {
        print_error "Could not activate virtual environment"
        exit 1
    }
else
    # Unix-like systems
    source venv/bin/activate
fi

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip
print_success "Upgraded pip"

# Install requirements
if [ -f "requirements.txt" ]; then
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    print_success "Installed Python dependencies"
fi

# Install ipcrawler in development mode
print_status "Installing ipcrawler in development mode..."
pip install -e .
print_success "Installed ipcrawler"

echo ""

# ========================================
# 8. Verify Installation
# ========================================
print_status "Verifying installation..."

# Test import
if python -c "import ipcrawler" 2>/dev/null; then
    print_success "ipcrawler module imports successfully"
else
    print_error "Failed to import ipcrawler module"
    exit 1
fi

# Test command line
if python ipcrawler.py --help >/dev/null 2>&1; then
    print_success "ipcrawler command line works"
else
    print_error "ipcrawler command line failed"
    exit 1
fi

echo ""

# ========================================
# 9. Summary
# ========================================
echo "🎉 Cache reset complete for $OS_ID!"
echo ""
echo "✅ Cleared:"
echo "   • Python bytecode cache (__pycache__, .pyc files)"
echo "   • ipcrawler application cache (OS-specific paths)"
echo "   • Virtual environment"
echo "   • Build artifacts"
echo "   • Docker cache (if available)"
echo "   • System package cache ($OS_ID)"
if [ "$WSL_DETECTED" = "yes" ]; then
    echo "   • WSL/Windows integration cache"
fi
echo ""
echo "✅ Rebuilt:"
echo "   • Fresh virtual environment"
echo "   • Python dependencies"
echo "   • ipcrawler application"
echo ""
echo "🚀 Ready to use! Try: python ipcrawler.py --help"
echo ""
echo "💡 If you still see cached behavior:"
echo "   1. Restart your terminal"
echo "   2. Run: source venv/bin/activate"
echo "   3. Check: python ipcrawler.py --version"
if [ "$OS_ID" = "kali" ] || [ "$OS_ID" = "parrot" ]; then
    echo "   4. Kali/Parrot: Consider restarting services if needed"
elif [ "$WSL_DETECTED" = "yes" ]; then
    echo "   4. WSL: Consider restarting WSL with 'wsl --shutdown'"
fi
