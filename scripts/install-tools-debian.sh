#!/bin/bash

# Debian/Ubuntu Tool Installation Script
# Usage: ./scripts/install-tools-debian.sh [WSL_DETECTED]

WSL_DETECTED=${1:-$WSL_DETECTED}

install_debian_tools() {
    local OS_ID=${OS_ID:-$(grep '^ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')}
    
    echo "📦 Installing security tools for $OS_ID (Debian-based)..."
    echo "🔄 Updating package cache..."
    sudo apt update -qq
    
    echo "🐍 Installing Python venv package (fixes ensurepip issues)..."
    sudo apt install -y python3-venv python3-pip
    
    echo "📦 Installing core security tools..."
    sudo apt install -y curl wget git nmap nikto whatweb sslscan smbclient
    
    echo "📦 Installing enumeration tools..."
    local FAILED_TOOLS=""
    local INSTALLED_TOOLS=""
    
    # Core enumeration tools that should always work
    local core_tools="seclists dnsrecon enum4linux nbtscan onesixtyone redis-tools smbmap snmp sipvicious"
    
    for tool in $core_tools; do
        echo "  Installing $tool..."
        if sudo apt install -y $tool >/dev/null 2>&1; then
            INSTALLED_TOOLS="$INSTALLED_TOOLS $tool"
            echo "    ✅ $tool installed successfully"
        else
            FAILED_TOOLS="$FAILED_TOOLS $tool"
            echo "    ⚠️  $tool failed to install"
        fi
    done
    
    # Tools that might need alternative installation methods
    echo "📦 Installing tools with fallback methods..."
    
    # Try feroxbuster
    echo "  Installing feroxbuster..."
    if sudo apt install -y feroxbuster >/dev/null 2>&1; then
        INSTALLED_TOOLS="$INSTALLED_TOOLS feroxbuster"
        echo "    ✅ feroxbuster installed successfully"
    else
        echo "    ⚠️  feroxbuster failed via apt, trying alternative methods..."
        # Try snap
        if command -v snap >/dev/null 2>&1 || sudo apt install -y snapd >/dev/null 2>&1; then
            if sudo snap install feroxbuster >/dev/null 2>&1; then
                INSTALLED_TOOLS="$INSTALLED_TOOLS feroxbuster"
                echo "    ✅ feroxbuster installed via snap"
            else
                FAILED_TOOLS="$FAILED_TOOLS feroxbuster"
                echo "    ⚠️  feroxbuster failed via snap"
            fi
        else
            FAILED_TOOLS="$FAILED_TOOLS feroxbuster"
            echo "    ⚠️  feroxbuster failed - no snap available"
        fi
    fi
    
    # Try gobuster
    echo "  Installing gobuster..."
    if sudo apt install -y gobuster >/dev/null 2>&1; then
        INSTALLED_TOOLS="$INSTALLED_TOOLS gobuster"
        echo "    ✅ gobuster installed successfully"
    else
        echo "    ⚠️  gobuster failed via apt, trying alternative methods..."
        # Try snap
        if command -v snap >/dev/null 2>&1 || sudo apt install -y snapd >/dev/null 2>&1; then
            if sudo snap install gobuster >/dev/null 2>&1; then
                INSTALLED_TOOLS="$INSTALLED_TOOLS gobuster"
                echo "    ✅ gobuster installed via snap"
            else
                FAILED_TOOLS="$FAILED_TOOLS gobuster"
                echo "    ⚠️  gobuster failed via snap"
            fi
        else
            FAILED_TOOLS="$FAILED_TOOLS gobuster"
            echo "    ⚠️  gobuster failed - no snap available"
        fi
    fi
    
    # Try impacket-scripts
    echo "  Installing impacket-scripts..."
    if sudo apt install -y impacket-scripts >/dev/null 2>&1; then
        INSTALLED_TOOLS="$INSTALLED_TOOLS impacket-scripts"
        echo "    ✅ impacket-scripts installed successfully"
    else
        echo "    ⚠️  impacket-scripts failed via apt, trying pip..."
        if pip3 install impacket >/dev/null 2>&1; then
            INSTALLED_TOOLS="$INSTALLED_TOOLS impacket"
            echo "    ✅ impacket installed via pip"
        else
            FAILED_TOOLS="$FAILED_TOOLS impacket-scripts"
            echo "    ⚠️  impacket failed via pip"
        fi
    fi
    
    # Try oscanner
    echo "  Installing oscanner..."
    if sudo apt install -y oscanner >/dev/null 2>&1; then
        INSTALLED_TOOLS="$INSTALLED_TOOLS oscanner"
        echo "    ✅ oscanner installed successfully"
    else
        FAILED_TOOLS="$FAILED_TOOLS oscanner"
        echo "    ⚠️  oscanner not available in repositories"
    fi
    
    # Try tnscmd10g with multiple methods
    echo "  Installing tnscmd10g (Oracle TNS tool)..."
    if sudo apt install -y tnscmd10g >/dev/null 2>&1; then
        INSTALLED_TOOLS="$INSTALLED_TOOLS tnscmd10g"
        echo "    ✅ tnscmd10g installed successfully"
    else
        echo "    ⚠️  tnscmd10g failed via apt, trying alternative methods..."
        
        # Try installing oracle-instantclient packages
        if sudo apt install -y oracle-instantclient-basic oracle-instantclient-devel >/dev/null 2>&1; then
            echo "    ✅ Oracle Instant Client installed (alternative to tnscmd10g)"
            INSTALLED_TOOLS="$INSTALLED_TOOLS oracle-instantclient"
        else
            # Try adding Oracle repository for older systems
            echo "    ⚠️  Trying to add Oracle repository..."
            if wget -q https://download.oracle.com/otn_software/linux/instantclient/instantclient-basiclite-linuxx64.zip -O /tmp/oracle-basic.zip 2>/dev/null; then
                echo "    ℹ️  Oracle tools available but require manual setup"
                rm -f /tmp/oracle-basic.zip
            fi
            FAILED_TOOLS="$FAILED_TOOLS tnscmd10g"
            echo "    ⚠️  tnscmd10g not available - Oracle scanning will be limited"
        fi
    fi
    
    # Summary
    echo ""
    echo "📊 Installation Summary:"
    if [ -n "$INSTALLED_TOOLS" ]; then
        echo "✅ Successfully installed:$(echo $INSTALLED_TOOLS | tr ' ' '\n' | sort | tr '\n' ' ')"
    fi
    
    if [ -n "$FAILED_TOOLS" ]; then
        echo "⚠️  Failed to install:$(echo $FAILED_TOOLS | tr ' ' '\n' | sort | tr '\n' ' ')"
        echo ""
        echo "💡 Note: Some tools may not be available on all distributions."
        echo "   ipcrawler will automatically skip unavailable tools during scans."
        echo "   Use --ignore-plugin-checks to bypass tool availability checks."
    fi
    
    echo ""
    echo "✅ Tool installation complete"
}

# Main execution
main() {
    install_debian_tools
}

# Run if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi 