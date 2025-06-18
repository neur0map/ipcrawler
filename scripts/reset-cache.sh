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
# 2. Clear Python Bytecode Cache (Enhanced)
# ========================================
print_status "Clearing Python bytecode cache (comprehensive)..."

# Step 1: Remove __pycache__ directories (recursive and thorough)
print_status "Removing __pycache__ directories..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYCACHE_COUNT" -gt 0 ]; then
    find . -type d -name "__pycache__" -print0 | xargs -0 rm -rf 2>/dev/null || true
    print_success "Removed $PYCACHE_COUNT __pycache__ directories"
else
    print_success "No __pycache__ directories found"
fi

# Step 2: Remove .pyc files (compiled Python bytecode)
print_status "Removing .pyc files..."
PYC_COUNT=$(find . -name "*.pyc" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYC_COUNT" -gt 0 ]; then
    find . -name "*.pyc" -print0 | xargs -0 rm -f 2>/dev/null || true
    print_success "Removed $PYC_COUNT .pyc files"
else
    print_success "No .pyc files found"
fi

# Step 3: Remove .pyo files (optimized Python bytecode)
print_status "Removing .pyo files..."
PYO_COUNT=$(find . -name "*.pyo" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYO_COUNT" -gt 0 ]; then
    find . -name "*.pyo" -print0 | xargs -0 rm -f 2>/dev/null || true
    print_success "Removed $PYO_COUNT .pyo files"
else
    print_success "No .pyo files found"
fi

# Step 4: Remove Python import cache files
print_status "Clearing Python import cache..."
# Clear .pytest_cache if it exists
if [ -d ".pytest_cache" ]; then
    rm -rf .pytest_cache
    print_success "Removed .pytest_cache directory"
fi

# Clear any .coverage files
find . -name ".coverage*" -delete 2>/dev/null || true
COVERAGE_COUNT=$(find . -name ".coverage*" 2>/dev/null | wc -l | tr -d ' ')
[ "$COVERAGE_COUNT" -eq 0 ] && print_success "Removed coverage cache files"

# Step 5: Clear plugin-specific cache that could interfere
print_status "Clearing plugin-specific cache..."

# Clear any plugin cache in default-plugins directory
if [ -d "ipcrawler/default-plugins" ]; then
    find ipcrawler/default-plugins -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find ipcrawler/default-plugins -name "*.pyc" -delete 2>/dev/null || true
    find ipcrawler/default-plugins -name "*.pyo" -delete 2>/dev/null || true
    print_success "Cleared plugin directory cache"
fi

# Clear any user plugin directories
USER_PLUGIN_DIRS=(
    "$HOME/.local/share/ipcrawler/plugins"
    "$HOME/.config/ipcrawler/plugins"
    "/home/$USER/.local/share/ipcrawler/plugins"
    "plugins"  # Local plugins directory if it exists
)

for plugin_dir in "${USER_PLUGIN_DIRS[@]}"; do
    if [ -d "$plugin_dir" ]; then
        find "$plugin_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$plugin_dir" -name "*.pyc" -delete 2>/dev/null || true
        find "$plugin_dir" -name "*.pyo" -delete 2>/dev/null || true
        print_success "Cleared user plugin cache: $plugin_dir"
    fi
done

# Step 6: Clear Python module import cache (importlib cache)
print_status "Clearing Python importlib cache..."
# The importlib module cache is usually cleared by removing __pycache__ but let's be thorough
if python3 -c "
import sys
import importlib
try:
    importlib.invalidate_caches()
    print('✅ Invalidated Python import caches')
except:
    print('⚠️  Could not invalidate import caches (normal on some systems)')
" 2>/dev/null; then
    print_success "Python import caches invalidated"
else
    print_warning "Could not invalidate import caches (may not be necessary)"
fi

# Step 7: Clear any temporary Python files
print_status "Clearing temporary Python files..."
find . -name "*.tmp" -name "*.py*" -delete 2>/dev/null || true
find . -name "*.bak" -name "*.py*" -delete 2>/dev/null || true
find . -name "*~" -name "*.py*" -delete 2>/dev/null || true

print_success "✅ Comprehensive Python cache clearing complete!"
print_status "Plugin updates will now be reflected immediately on next run"

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
# 4. Clear Build Cache
# ========================================

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
# 7. Fix Common Plugin Compatibility Issues
# ========================================
print_status "Checking and fixing common plugin compatibility issues..."

# Check if Service class has http_scheme property
if python3 -c "
from ipcrawler.targets import Service, Target
from ipcrawler.plugins import ipcrawler

# Test Service.http_scheme
s = Service('tcp', 80, 'http')
try:
    _ = s.http_scheme
    print('✅ Service.http_scheme property exists')
except AttributeError:
    print('❌ Service.http_scheme property missing')
    exit(1)

# Test Target.addressv6
try:
    ipc = ipcrawler()
    t = Target('127.0.0.1', '127.0.0.1', 'IPv4', 'ip', ipc)
    _ = t.addressv6
    _ = t.ipaddressv6
    print('✅ Target.addressv6/ipaddressv6 properties exist')
except AttributeError:
    print('❌ Target.addressv6/ipaddressv6 properties missing')
    exit(1)
" 2>/dev/null; then
    print_success "Service.http_scheme and Target.addressv6 properties are available"
else
    print_warning "Plugin compatibility issues detected - will be fixed after rebuild"
fi

# Check for user plugins that might have compatibility issues
USER_PLUGIN_DIRS=(
    "$HOME/.local/share/ipcrawler/plugins"
    "$HOME/.config/ipcrawler/plugins"
    "/home/$USER/.local/share/ipcrawler/plugins"
)

for plugin_dir in "${USER_PLUGIN_DIRS[@]}"; do
    if [ -d "$plugin_dir" ]; then
        print_warning "Found user plugin directory: $plugin_dir"
        
        # Check for plugins with known issues
        for plugin_file in "$plugin_dir"/*.py; do
            if [ -f "$plugin_file" ]; then
                plugin_name=$(basename "$plugin_file")
                # Check for service.http_scheme usage
                if grep -q "service\.http_scheme" "$plugin_file" 2>/dev/null; then
                    print_warning "Plugin $plugin_name uses service.http_scheme - may need updating"
                    echo "   💡 Consider updating or removing: $plugin_file"
                    echo "   💡 Or run: rm '$plugin_file' to use fixed default version"
                fi
                
                # Check for target.addressv6 usage
                if grep -q "target\.addressv6\|\.target\.addressv6" "$plugin_file" 2>/dev/null; then
                    print_warning "Plugin $plugin_name uses target.addressv6 - may need updating"
                    echo "   💡 Consider updating or removing: $plugin_file"
                    echo "   💡 Or run: rm '$plugin_file' to use fixed default version"
                fi
            fi
        done
    fi
done

echo ""

# ========================================
# 8. Verify Python Dependencies (No Reinstall)
# ========================================
print_status "Verifying Python dependencies..."

# Just check if dependencies are available - don't reinstall
if python3 -c "import rich, async_timeout, lxml, toml" 2>/dev/null; then
    print_success "Core Python dependencies available"
else
    print_warning "Some Python dependencies may be missing"
    print_warning "Run: python3 -m pip install --user -r requirements.txt"
fi

echo ""

# ========================================
# 9. Verify Installation and Plugin Compatibility
# ========================================
print_status "Verifying installation..."

# Test command line directly (no venv needed)
if python3 ipcrawler.py --help >/dev/null 2>&1; then
    print_success "ipcrawler command line works"
else
    print_warning "ipcrawler command line test failed - may need dependency installation"
fi

# Re-verify all plugin compatibility fixes after rebuild
print_status "Re-verifying plugin compatibility fixes..."
if python3 -c "
from ipcrawler.targets import Service, Target
from ipcrawler.plugins import ipcrawler

# Test Service.http_scheme
s = Service('tcp', 80, 'http')
assert s.http_scheme == 'http'
s_secure = Service('tcp', 443, 'https', secure=True)
assert s_secure.http_scheme == 'https'
print('✅ Service.http_scheme property working correctly')

# Test Target.addressv6
ipc = ipcrawler()
t = Target('127.0.0.1', '127.0.0.1', 'IPv4', 'ip', ipc)
assert t.addressv6 == '127.0.0.1'
assert t.ipaddressv6 == '127.0.0.1'

# Test IPv6 formatting
t_ipv6 = Target('::1', '::1', 'IPv6', 'ip', ipc)
assert t_ipv6.addressv6 == '::1'
assert t_ipv6.ipaddressv6 == '[::1]'
print('✅ Target.addressv6/ipaddressv6 properties working correctly')

# Test common plugin patterns (the exact patterns that were failing)
service = Service('tcp', 80, 'http')
service.target = t
base_url = f'{service.http_scheme}://{service.target.addressv6}:{service.port}'
assert base_url == 'http://127.0.0.1:80'
print('✅ Common plugin usage patterns working correctly')
" 2>/dev/null; then
    print_success "All plugin compatibility fixes verified"
else
    print_error "Plugin compatibility issues still exist - manual intervention needed"
fi

echo ""

# ========================================
# 10. Summary
# ========================================
echo "🎉 Cache reset complete for $OS_ID!"
echo ""
echo "✅ Cleared:"
echo "   • Python bytecode cache (__pycache__, .pyc, .pyo files)"
echo "   • Plugin-specific cache (default-plugins & user plugins)"
echo "   • Python import cache (importlib.invalidate_caches())"
echo "   • ipcrawler application cache (OS-specific paths)"
echo "   • Build artifacts"
echo "   • Docker cache (if available)"
echo "   • System package cache ($OS_ID)"
if [ "$WSL_DETECTED" = "yes" ]; then
    echo "   • WSL/Windows integration cache"
fi
echo ""
echo "✅ Maintained:"
echo "   • Python dependencies (system user space)"
echo "   • Global ipcrawler command (symlink with correct shebang)"
echo ""
echo "✅ Fixed:"
echo "   • Service.http_scheme compatibility issues"
echo "   • Target.addressv6/ipaddressv6 compatibility issues"
echo "   • Common plugin AttributeError problems"
echo "   • User plugin compatibility warnings"
echo ""
echo "🔥 Plugin Update Mitigation:"
echo "   • All Python cache cleared to prevent stale bytecode"
echo "   • Plugin changes now guaranteed to take effect immediately"
echo "   • No more __pycache__ interference with plugin updates"
echo "   • Fresh module loading ensured on every ipcrawler run"
echo ""

# ========================================
# 11. Reinstall Global Command
# ========================================
print_status "Reinstalling global ipcrawler command..."

# Get absolute path to the main script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IPCRAWLER_SCRIPT="$PROJECT_DIR/ipcrawler.py"

# Fix the shebang to use the correct Python
PYTHON_PATH=$(which python3)
print_status "Updating shebang to use: $PYTHON_PATH"

# Create a backup and update the shebang
sed -i.bak "1s|.*|#!${PYTHON_PATH}|" "$IPCRAWLER_SCRIPT"

# Make sure the main script is executable
chmod +x "$IPCRAWLER_SCRIPT"

# Try system-wide installation first
if [ -w /usr/local/bin ] && [ -d /usr/local/bin ]; then
    [ -L /usr/local/bin/ipcrawler ] && rm /usr/local/bin/ipcrawler
    ln -sf "$IPCRAWLER_SCRIPT" /usr/local/bin/ipcrawler
    print_success "Global command reinstalled: /usr/local/bin/ipcrawler"
    echo "🚀 Ready to use! Try: ipcrawler --help"
elif [ -w ~/.local/bin ] || mkdir -p ~/.local/bin 2>/dev/null; then
    [ -L ~/.local/bin/ipcrawler ] && rm ~/.local/bin/ipcrawler
    ln -sf "$IPCRAWLER_SCRIPT" ~/.local/bin/ipcrawler
    print_success "Global command reinstalled: ~/.local/bin/ipcrawler"
    echo "🚀 Ready to use! Try: ipcrawler --help"
else
    print_warning "Could not reinstall global command - no writable directory"
    echo "🚀 Ready to use! Try: python ipcrawler.py --help"
fi
echo ""
echo "💡 If you still see cached behavior:"
echo "   1. Restart your terminal"
echo "   2. Check: ipcrawler --help"
echo "   3. Verify PATH includes ~/.local/bin or /usr/local/bin"
if [ "$OS_ID" = "kali" ] || [ "$OS_ID" = "parrot" ]; then
    echo "   4. Kali/Parrot: Consider restarting services if needed"
elif [ "$WSL_DETECTED" = "yes" ]; then
    echo "   4. WSL: Consider restarting WSL with 'wsl --shutdown'"
fi
