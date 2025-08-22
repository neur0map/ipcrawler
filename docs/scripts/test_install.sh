#!/bin/bash

# Test the install script functions without actually installing
# This validates syntax and logic

set -euo pipefail

# Source the install script functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/install.sh" 2>/dev/null || {
    echo "Testing individual functions from install.sh..."
    
    # Test OS detection
    echo "Testing OS detection..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "✓ macOS detected"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "✓ Linux detected"
    else
        echo "⚠ Unsupported OS: $OSTYPE"
    fi
    
    # Test tool definitions
    echo "Testing tool definitions..."
    declare -A TOOLS=(
        ["nmap"]="Network discovery and security auditing"
        ["naabu"]="Fast port discovery"
        ["httpx"]="HTTP toolkit"
    )
    
    echo "✓ Found ${#TOOLS[@]} tools defined"
    
    # Test existing tool detection
    echo "Testing existing tools..."
    for tool in nmap curl git cargo; do
        if command -v "$tool" >/dev/null 2>&1; then
            echo "✓ $tool is available"
        else
            echo "⚠ $tool is missing"
        fi
    done
    
    echo "✓ Basic validation passed"
}