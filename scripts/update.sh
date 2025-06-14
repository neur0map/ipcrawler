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
    
    if [ ! -d "venv" ]; then
        echo "⚠️  Virtual environment not found. Creating it..."
        ./scripts/setup-python.sh
        return $?
    fi
    
    # Update pip and packages
    echo "📦 Updating Python packages..."
    venv/bin/python3 -m pip install --upgrade pip
    venv/bin/python3 -m pip install --upgrade -r requirements.txt
    
    # Regenerate the command script with latest code
    echo "🔧 Updating ipcrawler command..."
    rm -f ipcrawler-cmd
    
    # Create updated command script
    cat > ipcrawler-cmd << 'EOF'
#!/bin/bash
# Resolve the real path of the script (follow symlinks)
SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$DIR"
source "$DIR/venv/bin/activate" && PYTHONPATH="$DIR" python3 "$DIR/ipcrawler/main.py" "$@"
EOF
    
    chmod +x ipcrawler-cmd
    
    # Update system symlink
    if [ -L "/usr/local/bin/ipcrawler" ]; then
        echo "🔗 Updating system symlink..."
        sudo ln -sf "$(pwd)/ipcrawler-cmd" /usr/local/bin/ipcrawler
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
    echo "  • Python virtual environment and packages" 
    echo "  • ipcrawler command script"
    echo "  • System security tools"
    if command -v docker >/dev/null 2>&1; then
        echo "  • Docker image (if needed)"
    fi
    echo ""
    echo "🎯 Ready to use updated ipcrawler!"
    echo "💡 All changes from 'git pull' are now active!"
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