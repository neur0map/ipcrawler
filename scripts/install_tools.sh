#!/usr/bin/env bash
# Don't fail on missing optional tools
set -eo pipefail

echo "🔧 Checking required tools..."

# Check if Go tools (dnsx, httpx) are available
check_go_tool() {
    local tool=$1
    local repo=$2
    
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool is already installed"
        return 0
    else
        echo "⚠ $tool not found"
        echo "  Install with: go install -v $repo@latest"
        return 1
    fi
}

# Check system tools
check_system_tool() {
    local tool=$1
    local install_hint=$2
    
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool is available"
        return 0
    else
        echo "⚠ $tool not found"
        echo "  Install with: $install_hint"
        return 1
    fi
}

echo ""
echo "System DNS tools:"
check_system_tool "nslookup" "Usually pre-installed with system"
check_system_tool "dig" "brew install bind (macOS) or apt install dnsutils (Linux)"

echo ""
echo "Go-based reconnaissance tools (optional for hosts discovery):"
check_go_tool "dnsx" "github.com/projectdiscovery/dnsx/cmd/dnsx" || true
check_go_tool "httpx" "github.com/projectdiscovery/httpx/cmd/httpx" || true

echo ""
echo "📋 Installation Summary:"
echo "  • Basic DNS tools (nslookup, dig) are required"
echo "  • Go tools (dnsx, httpx) are optional but recommended for hosts discovery"
echo "  • If Go tools are missing, hosts discovery plugin will be skipped gracefully"
echo ""
echo "💡 Quick install Go tools (if you have Go installed):"
echo "  go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
echo "  go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest"