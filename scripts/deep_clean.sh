#!/usr/bin/env bash

# IPCrawler Deep Clean Script
# Removes all traces of IPCrawler from the system

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== IPCrawler Deep Clean ===${NC}"
echo "This will remove all traces of IPCrawler from your system."
echo -e "${RED}Warning: This action cannot be undone!${NC}"
echo
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo -e "\n${YELLOW}Starting cleanup...${NC}"

# 1. Remove Python packages
echo -e "\n${GREEN}1. Removing Python packages...${NC}"
# User packages
python3 -m pip uninstall -y httpx dnspython typer rich pydantic pyyaml 2>/dev/null || echo "  User packages not found"
# System packages (if sudo available)
if command -v sudo >/dev/null 2>&1; then
    sudo python3 -m pip uninstall -y httpx dnspython typer rich pydantic pyyaml 2>/dev/null || echo "  System packages not found"
fi

# 2. Clean Python cache
echo -e "\n${GREEN}2. Cleaning Python cache...${NC}"

# Detect OS for cache locations
if [[ "$OSTYPE" == "darwin"* ]]; then
    PIP_CACHE_DIR="$HOME/Library/Caches/pip"
else
    PIP_CACHE_DIR="$HOME/.cache/pip"
fi

# User pip cache
python3 -m pip cache purge 2>/dev/null || echo "  No user pip cache to clean"
# System pip cache
if command -v sudo >/dev/null 2>&1; then
    sudo python3 -m pip cache purge 2>/dev/null || echo "  No system pip cache to clean"
fi

# Clean OS-specific pip cache directory
if [ -d "$PIP_CACHE_DIR" ]; then
    echo "  Cleaning pip cache at $PIP_CACHE_DIR"
    rm -rf "$PIP_CACHE_DIR"/* 2>/dev/null || true
fi

# Find and remove all __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find ~ -type d -name "__pycache__" -path "*ipcrawler*" -exec rm -rf {} + 2>/dev/null || true

# Remove user site-packages remnants
rm -rf ~/.local/lib/python*/site-packages/ipcrawler* 2>/dev/null || true
rm -rf ~/.local/lib/python*/site-packages/__pycache__/*ipcrawler* 2>/dev/null || true

# 3. Remove command symlinks
echo -e "\n${GREEN}3. Removing command symlinks...${NC}"

# Detect OS for proper paths
OS_TYPE="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    SYSTEM_LOCATIONS=(
        "/usr/local/bin/ipcrawler"
        "/opt/homebrew/bin/ipcrawler"
        "/opt/local/bin/ipcrawler"
    )
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    SYSTEM_LOCATIONS=(
        "/usr/local/bin/ipcrawler"
        "/usr/bin/ipcrawler"
        "/opt/bin/ipcrawler"
    )
else
    SYSTEM_LOCATIONS=(
        "/usr/local/bin/ipcrawler"
        "/usr/bin/ipcrawler"
    )
fi

# User locations (cross-platform)
USER_LOCATIONS=(
    "$HOME/.local/bin/ipcrawler"
    "$HOME/bin/ipcrawler"
)

LOCATIONS=("${USER_LOCATIONS[@]}" "${SYSTEM_LOCATIONS[@]}")

for loc in "${LOCATIONS[@]}"; do
    if [ -L "$loc" ] || [ -f "$loc" ]; then
        if [[ "$loc" == /usr/* ]] || [[ "$loc" == /opt/* ]]; then
            sudo rm -f "$loc" 2>/dev/null && echo "  Removed: $loc" || echo "  Could not remove: $loc"
        else
            rm -f "$loc" 2>/dev/null && echo "  Removed: $loc" || echo "  Could not remove: $loc"
        fi
    fi
done

# 4. Remove workspace directories
echo -e "\n${GREEN}4. Removing workspace directories...${NC}"
if [ -d "workspaces" ]; then
    rm -rf workspaces && echo "  Removed workspaces directory"
fi

# 5. Remove temporary and test files
echo -e "\n${GREEN}5. Removing temporary files...${NC}"
rm -f test_*.py debug_*.py check_deps.sh 2>/dev/null && echo "  Removed test files" || echo "  No test files found"

# 6. Clean shell history (optional)
echo -e "\n${GREEN}6. Clean shell history?${NC}"
echo "Remove IPCrawler commands from shell history?"
read -p "[y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Clean bash history
    if [ -f ~/.bash_history ]; then
        grep -v "ipcrawler" ~/.bash_history > ~/.bash_history.tmp 2>/dev/null || true
        mv ~/.bash_history.tmp ~/.bash_history 2>/dev/null || true
        echo "  Cleaned bash history"
    fi
    
    # Clean zsh history
    if [ -f ~/.zsh_history ]; then
        grep -v "ipcrawler" ~/.zsh_history > ~/.zsh_history.tmp 2>/dev/null || true
        mv ~/.zsh_history.tmp ~/.zsh_history 2>/dev/null || true
        echo "  Cleaned zsh history"
    fi
fi

# 7. Reset Python bytecode generation
echo -e "\n${GREEN}7. Resetting Python settings...${NC}"
unset PYTHONDONTWRITEBYTECODE 2>/dev/null || true
echo "  Python bytecode generation reset"

echo -e "\n${GREEN}=== Cleanup Complete ===${NC}"
echo "IPCrawler has been completely removed from your system."
echo
echo "To reinstall, run: make install"