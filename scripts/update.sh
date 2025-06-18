#!/bin/bash

# Update Script
# Usage: ./scripts/update.sh

update_git() {
    echo "📥 Updating git repository..."
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        echo "❌ Not in a git repository"
        return 1
    fi
    
    # Store current branch and check for uncommitted changes
    CURRENT_BRANCH=$(git branch --show-current)
    
    if ! git diff-index --quiet HEAD --; then
        echo "⚠️  Uncommitted changes detected. Stashing them..."
        git stash push -m "Auto-stash before update $(date)"
        STASHED=true
    fi
    
    # Fetch and pull latest changes
    echo "🔄 Fetching latest changes..."
    git fetch origin
    
    if git pull origin "$CURRENT_BRANCH"; then
        echo "✅ Git repository updated successfully"
        
        # Show what changed
        if [ -n "$(git log HEAD@{1}..HEAD --oneline)" ]; then
            echo ""
            echo "📋 Recent changes:"
            git log HEAD@{1}..HEAD --oneline --decorate
        else
            echo "ℹ️  Already up to date"
        fi
        
        # Restore stashed changes if any
        if [ "$STASHED" = "true" ]; then
            echo ""
            echo "🔄 Restoring stashed changes..."
            git stash pop
        fi
        
        return 0
    else
        echo "❌ Failed to update git repository"
        return 1
    fi
}

clean_cached_files() {
    echo "🧹 Cleaning cached application files..."
    
    # Remove Application Support cache that might override source code
    if [ "$(uname)" = "Darwin" ]; then
        APP_SUPPORT_DIR="$HOME/Library/Application Support/ipcrawler"
    else
        APP_SUPPORT_DIR="$HOME/.local/share/ipcrawler"
    fi
    
    if [ -d "$APP_SUPPORT_DIR" ]; then
        echo "📂 Removing cached files from: $APP_SUPPORT_DIR"
        
        # Backup current config if it exists and differs from source
        if [ -f "$APP_SUPPORT_DIR/config.toml" ] && [ -f "config.toml" ]; then
            if ! diff -q "$APP_SUPPORT_DIR/config.toml" "config.toml" >/dev/null 2>&1; then
                echo "💾 Backing up user config to config.toml.backup"
                cp "$APP_SUPPORT_DIR/config.toml" "config.toml.backup"
            fi
        fi
        
        # Remove cached plugins but preserve wordlists and user configs
        rm -rf "$APP_SUPPORT_DIR/plugins" 2>/dev/null || true
        
        # Recreate plugin symlink to source
        if [ -d "ipcrawler/default-plugins" ]; then
            echo "🔗 Creating symlink from cached plugins to source"
            mkdir -p "$APP_SUPPORT_DIR"
            ln -sf "$(pwd)/ipcrawler/default-plugins" "$APP_SUPPORT_DIR/plugins"
        fi
        
        echo "✅ Cache cleanup complete"
    else
        echo "ℹ️  No application cache found"
    fi
}

update_python() {
    echo "🐍 Updating Python environment..."
    
    # Install dependencies to system Python (user space)
    echo "📦 Installing Python dependencies to user space..."
    
    # Try different approaches for different systems
    if python3 -m pip install --user --upgrade pip 2>/dev/null; then
        echo "✅ Pip upgraded successfully"
    else
        echo "⚠️  Pip upgrade failed - trying with --break-system-packages"
        python3 -m pip install --user --break-system-packages --upgrade pip 2>/dev/null || echo "❌ Pip upgrade failed"
    fi
    
    if [ -f "requirements.txt" ]; then
        echo "📦 Installing requirements..."
        
        # Try normal user install first
        if python3 -m pip install --user -r requirements.txt 2>/dev/null; then
            echo "✅ Dependencies installed to user Python environment"
        # If that fails, try with --break-system-packages (for externally managed environments)
        elif python3 -m pip install --user --break-system-packages -r requirements.txt 2>/dev/null; then
            echo "✅ Dependencies installed to user Python environment (with system override)"
        # If that still fails, provide helpful error message
        else
            echo "❌ Failed to install dependencies"
            echo "💡 Try manually:"
            echo "   python3 -m pip install --user --break-system-packages -r requirements.txt"
            echo "   OR install using your system package manager"
            return 1
        fi
    else
        echo "⚠️  No requirements.txt found - dependencies may need manual installation"
        return 1
    fi
    
    # Update global command to ensure it points to current code
    echo "🔧 Updating global ipcrawler command..."
    
    # Get absolute path to the main script
    IPCRAWLER_SCRIPT="$(pwd)/ipcrawler.py"
    
    # Fix the shebang to use the correct Python
    PYTHON_PATH=$(which python3)
    echo "🔧 Updating shebang to use: $PYTHON_PATH"
    
    # Create a backup and update the shebang
    sed -i.bak "1s|.*|#!${PYTHON_PATH}|" "$IPCRAWLER_SCRIPT"
    
    # Make sure the main script is executable
    chmod +x "$IPCRAWLER_SCRIPT"
    
    # Try system-wide installation first
    if [ -w /usr/local/bin ] && [ -d /usr/local/bin ]; then
        # Remove existing symlink if it exists
        [ -L /usr/local/bin/ipcrawler ] && rm /usr/local/bin/ipcrawler
        
        # Create new symlink
        ln -sf "$IPCRAWLER_SCRIPT" /usr/local/bin/ipcrawler
        echo "✅ Global command updated: /usr/local/bin/ipcrawler"
        
    elif [ -w ~/.local/bin ] || mkdir -p ~/.local/bin 2>/dev/null; then
        # User-local installation
        [ -L ~/.local/bin/ipcrawler ] && rm ~/.local/bin/ipcrawler
        
        ln -sf "$IPCRAWLER_SCRIPT" ~/.local/bin/ipcrawler
        echo "✅ Global command updated: ~/.local/bin/ipcrawler"
        
        # Check if ~/.local/bin is in PATH
        if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
            echo "💡 Add ~/.local/bin to PATH by adding this to ~/.bashrc:"
            echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
        fi
    else
        echo "⚠️  Could not update global command - no writable directory found"
        echo "💡 You can still use: python3 ipcrawler.py <target>"
        return 1
    fi
    
    echo "✅ Python environment updated"
}

update_tools() {
    echo "🔧 Updating security tools..."
    
    # Source system detection
    source ./scripts/system-check.sh >/dev/null 2>&1
    detect_os >/dev/null 2>&1
    
    if [ -f /etc/os-release ]; then
        OS_ID=$(grep '^ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
        OS_ID_LIKE=$(grep '^ID_LIKE=' /etc/os-release | cut -d'=' -f2 | tr -d '"' 2>/dev/null || echo "")
        
        if [ "$OS_ID" = "kali" ] || [ "$OS_ID" = "parrot" ] || echo "$OS_ID_LIKE" | grep -q "debian\|ubuntu"; then
            echo "Updating apt packages..."
            sudo apt update -qq
            sudo apt upgrade -y
            
        elif [ "$OS_ID" = "arch" ] || [ "$OS_ID" = "manjaro" ]; then
            echo "Updating pacman packages..."
            sudo pacman -Syu --noconfirm
            
        else
            echo "ℹ️  Basic system update..."
            sudo apt update -qq && sudo apt upgrade -y 2>/dev/null || \
            sudo yum update -y 2>/dev/null || \
            sudo dnf update -y 2>/dev/null || \
            echo "Please update system packages manually"
        fi
        
    elif [ "$(uname)" = "Darwin" ]; then
        if command -v brew >/dev/null 2>&1; then
            echo "Updating Homebrew packages..."
            brew update && brew upgrade
        fi
    fi
    
    echo "✅ Security tools updated"
}

update_docker() {
    echo "🐳 Updating Docker image..."
    
    if ! command -v docker >/dev/null 2>&1; then
        echo "ℹ️  Docker not installed, skipping Docker update"
        return 0
    fi
    
    # Check if Dockerfile or requirements.txt changed
    DOCKERFILE_CHANGED=false
    REQUIREMENTS_CHANGED=false
    
    if git diff HEAD@{1}..HEAD --name-only | grep -q "Dockerfile\|requirements.txt\|default-plugins/"; then
        DOCKERFILE_CHANGED=true
        echo "📋 Docker-related files changed, rebuilding image..."
    fi
    
    if [ "$DOCKERFILE_CHANGED" = "true" ] || [ ! -n "$(docker images -q ipcrawler 2>/dev/null)" ]; then
        echo "🔨 Building updated Docker image..."
        if docker build -t ipcrawler .; then
            echo "✅ Docker image updated successfully"
            
            # Clean up old images
            echo "🧹 Cleaning up old Docker images..."
            docker image prune -f >/dev/null 2>&1 || true
        else
            echo "❌ Failed to build Docker image"
            return 1
        fi
    else
        echo "ℹ️  Docker image is up to date"
    fi
    
    return 0
}

check_makefile_update() {
    echo "📋 Checking for Makefile updates..."
    
    if git diff HEAD@{1}..HEAD --name-only | grep -q "Makefile"; then
        echo ""
        echo "⚠️  Makefile was updated!"
        echo "💡 Consider restarting this process to use the latest Makefile commands"
        echo ""
    fi
}

show_summary() {
    echo ""
    echo "✅ Update complete!"
    echo ""
    echo "📋 What was updated:"
    echo "  • Git repository and source code"
    echo "  • Cleaned cached application files"
    echo "  • Python dependencies (user space)" 
    echo "  • Global ipcrawler command symlink"
    echo "  • System security tools"
    if command -v docker >/dev/null 2>&1; then
        echo "  • Docker image (if needed)"
    fi
    echo ""
    echo "🎯 Ready to use updated ipcrawler!"
    echo "💡 All changes from 'git pull' are now active immediately!"
    echo "💡 No virtual environment - uses system Python directly"
}

# Main execution
main() {
    echo "Updating ipcrawler installation..."
    echo ""
    
    # Update git repository first
    if ! update_git; then
        echo "❌ Git update failed, aborting"
        exit 1
    fi
    
    echo ""
    
    # Clean cached files that might override source code updates
    clean_cached_files
    echo ""
    
    # Check if Makefile was updated
    check_makefile_update
    
    # Update Python environment
    update_python
    echo ""
    
    # Update tools
    update_tools
    echo ""
    
    # Update Docker if available
    update_docker
    
    # Show summary
    show_summary
}

# Run if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi 