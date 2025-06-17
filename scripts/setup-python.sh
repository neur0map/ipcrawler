#!/bin/bash

# Python Environment Setup Script
# Usage: ./scripts/setup-python.sh

install_system_dependencies() {
    echo "🐍 Installing system Python dependencies..."
    
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
}

install_global_command() {
    echo "🔗 Installing global ipcrawler command..."
    
    # Get absolute path to the main script
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    IPCRAWLER_SCRIPT="$PROJECT_DIR/ipcrawler.py"
    
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
        echo "✅ Global command installed: /usr/local/bin/ipcrawler"
        echo "🎯 You can now run: ipcrawler <target>"
        return 0
        
    elif [ -w ~/.local/bin ] || mkdir -p ~/.local/bin 2>/dev/null; then
        # User-local installation
        [ -L ~/.local/bin/ipcrawler ] && rm ~/.local/bin/ipcrawler
        
        ln -sf "$IPCRAWLER_SCRIPT" ~/.local/bin/ipcrawler
        echo "✅ Global command installed: ~/.local/bin/ipcrawler"
        echo "🎯 You can now run: ipcrawler <target>"
        
        # Check if ~/.local/bin is in PATH
        if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
            echo "💡 Add ~/.local/bin to PATH by adding this to ~/.bashrc:"
            echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
        fi
        return 0
    else
        echo "⚠️  Could not install global command - no writable directory found"
        echo "💡 You can still use: python3 ipcrawler.py <target>"
        return 1
    fi
}

show_completion_message() {
    echo ""
    echo "✅ Global ipcrawler command setup complete!"
    echo ""
    echo "📋 Usage:"
    echo "  • Run: ipcrawler --help"
    echo "  • Test with: ipcrawler 127.0.0.1"
    echo "  • Code updates apply immediately (no reinstall needed)"
    echo ""
    echo "💡 Benefits:"
    echo "  • No virtual environment - uses system Python"
    echo "  • No code copying - symlink points to live code"
    echo "  • Updates apply instantly when you modify the code"
}

# Main execution
main() {
    install_system_dependencies
    install_global_command
    show_completion_message
}

# Run if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi 