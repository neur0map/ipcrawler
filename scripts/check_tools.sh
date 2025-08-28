#!/usr/bin/env bash
set -euo pipefail

ok()  { printf "✔ %s\n" "$1"; }
warn() { printf "⚠ %s (optional)\n" "$1"; }
bad() { printf "✘ %s\n" "$1"; }

missing=0
optional_missing=0

# Check required tools (will fail build)
need() {
  local tool=$1
  if command -v "$tool" >/dev/null 2>&1; then
    local version=""
    case "$tool" in
      "nslookup") version="(system DNS tool)" ;;
      "dig") version="$( "$tool" -v 2>&1 | head -n1 | cut -d' ' -f2 2>/dev/null || echo "available" )" ;;
      *) version="$( "$tool" --version 2>&1 | head -n1 | cut -d' ' -f2 2>/dev/null || echo "available" )" ;;
    esac
    ok "$tool $version"
  else
    bad "$tool not found (required)"
    missing=1
  fi
}

# Check optional tools (won't fail build, but plugins may be disabled)
optional() {
  local tool=$1
  if command -v "$tool" >/dev/null 2>&1; then
    local version=""
    case "$tool" in
      "nmap") version="$( "$tool" --version 2>&1 | head -n1 | grep -o '[0-9.]*' | head -n1 2>/dev/null || echo "available" )" ;;
      "rustscan") version="$( "$tool" --version 2>&1 | head -n1 | grep -o '[0-9.]*' | head -n1 2>/dev/null || echo "available" )" ;;
      *) version="$( "$tool" --version 2>&1 | head -n1 | cut -d' ' -f2 2>/dev/null || echo "available" )" ;;
    esac
    ok "$tool $version"
  else
    warn "$tool not found"
    optional_missing=1
  fi
}

echo "🔍 Checking IPCrawler dependencies..."
echo ""

echo "Core DNS tools (required for basic functionality):"
need nslookup
need dig

echo ""
echo "Host discovery tools (optional - for hosts_discovery plugin):"
optional dnsx
optional httpx

echo ""
echo "Port scanning tools (optional - for port_scanner plugin):"
optional nmap
optional rustscan

echo ""
echo "Web application tools (optional - for looter plugin):"
optional katana
optional hakrawler
optional feroxbuster
optional ffuf
optional gobuster
optional xh
optional cewl

echo ""
echo "Development tools:"
optional curl
optional git

echo ""
echo "SecLists wordlists:"
if [ -d "$HOME/.local/share/seclists" ]; then
  ok "SecLists wordlists installed"
else
  warn "SecLists wordlists not found (recommended for looter plugin)"
fi

echo ""
if [[ $missing -ne 0 ]]; then
  echo "❌ Critical tools missing. IPCrawler will not work properly."
  echo "💡 Run 'make build' to auto-install missing tools"
  exit 1
elif [[ $optional_missing -ne 0 ]]; then
  echo "⚠️  Some optional tools missing. Corresponding plugins will be disabled."
  echo "💡 Run 'make build' to auto-install all recommended tools"
  echo "✅ Core functionality available"
else
  echo "✅ All tools available! IPCrawler fully functional"
fi