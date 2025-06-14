#!/bin/bash

# macOS Tool Installation Script
# Usage: ./scripts/install-tools-macos.sh

install_macos_tools() {
    echo "📦 Installing comprehensive security toolkit for macOS..."
    
    if command -v brew >/dev/null 2>&1; then
        echo "🍺 Using Homebrew to install security tools..."
        
        echo "Installing core network tools..."
        brew install nmap curl wget git gobuster nikto sslscan || echo "⚠️  Some core tools failed"
        
        echo "Installing enumeration tools..."
        brew install feroxbuster redis-tools || echo "⚠️  Some enum tools failed"
        
        echo "Installing additional security tools..."
        brew install hydra john-jumbo hashcat sqlmap exploitdb binwalk exiftool || echo "⚠️  Some additional tools failed"
        
        echo "Installing WhatWeb from source (Homebrew version often broken)..."
        if [ ! -d /tmp/whatweb-install ]; then
            git clone https://github.com/urbanadventurer/WhatWeb.git /tmp/whatweb-install
            cd /tmp/whatweb-install
            sudo make install || echo "⚠️  WhatWeb install failed - permissions issue"
            cd - >/dev/null
            rm -rf /tmp/whatweb-install
        fi
        
        echo "Installing Python security tools via pip..."
        python3 -m pip install impacket crackmapexec enum4linux-ng 2>/dev/null || echo "⚠️  Some Python tools failed"
        
        echo "✅ macOS security toolkit installation complete!"
        echo "📋 Installed tools: nmap, gobuster, nikto, whatweb (from source), sslscan,"
        echo "    feroxbuster, redis-tools, hydra, john-jumbo, hashcat, sqlmap,"
        echo "    exploitdb, binwalk, exiftool, impacket, crackmapexec"
        echo "🔧 Note: WhatWeb installed from source for better compatibility"
    else
        echo "⚠️  Homebrew not found. Please install Homebrew first:"
        echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "ℹ️  Or use Docker setup for full tool support"
        return 1
    fi
}

# Main execution
main() {
    install_macos_tools
}

# Run if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi 