#!/bin/bash

# Python Environment Setup Script
# Usage: ./scripts/setup-python.sh

setup_venv() {
    echo "🐍 Setting up Python environment..."
    
    # Try to create virtual environment
    if ! python3 -m venv venv 2>/dev/null; then
        echo "⚠️  venv creation failed. Trying to fix..."
        echo "Installing python3-venv package..."
        
        # Try different package managers
        if command -v apt >/dev/null 2>&1; then
            sudo apt install -y python3-venv python3-pip 2>/dev/null
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y python3-venv python3-pip 2>/dev/null
        elif command -v pacman >/dev/null 2>&1; then
            sudo pacman -S --noconfirm python python-pip 2>/dev/null
        else
            echo "⚠️  Could not install python3-venv. Please install manually."
        fi
        
        # Try creating venv again
        python3 -m venv venv
    fi
    
    # Install Python packages
    echo "📦 Installing Python dependencies..."
    venv/bin/python3 -m pip install --upgrade pip
    venv/bin/python3 -m pip install -r requirements.txt
}

create_command() {
    echo "🔧 Creating ipcrawler command..."
    
    # Remove old command file
    rm -f ipcrawler-cmd
    
    # Create new command script
    cat > ipcrawler-cmd << 'EOF'
#!/bin/bash
# Resolve the real path of the script (follow symlinks)
SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$DIR"
source "$DIR/venv/bin/activate" && PYTHONPATH="$DIR" python3 "$DIR/ipcrawler/main.py" "$@"
EOF
    
    # Make it executable
    chmod +x ipcrawler-cmd
    
    # Try to install globally
    echo "🔗 Installing ipcrawler command to /usr/local/bin..."
    if ! sudo ln -sf "$(pwd)/ipcrawler-cmd" /usr/local/bin/ipcrawler 2>/dev/null; then
        echo "⚠️  Could not install to /usr/local/bin (permission issue)"
        echo "💡 You can still use: ./ipcrawler-cmd or add to PATH manually"
        return 1
    fi
    
    return 0
}

show_completion_message() {
    echo ""
    echo "✅ Python setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "  • Run: ipcrawler --help"
    echo "  • Test with: ipcrawler 127.0.0.1"
    echo "  • For full tool support on non-Kali systems, consider: make setup-docker"
}

# Main execution
main() {
    setup_venv
    create_command
    show_completion_message
}

# Run if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi 