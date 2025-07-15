#!/usr/bin/env bash
# Quick installation script for IPCrawler
# Focuses on solving the sudo command issue

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}IPCrawler Quick Install${NC}"
echo "======================="
echo ""

# 1. Clean all Python caches
echo "Cleaning Python caches..."
find "$ROOT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$ROOT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$ROOT_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
export PYTHONDONTWRITEBYTECODE=1

# 2. Make scripts executable
echo "Setting permissions..."
chmod +x "$ROOT_DIR/ipcrawler.py"
chmod +x "$ROOT_DIR/ipcrawler"

# 3. Install Python dependencies
echo "Installing Python dependencies..."
if python3 -m pip install --user --no-cache-dir -r "$ROOT_DIR/requirements.txt" 2>/dev/null; then
    echo -e "${GREEN}✓ Dependencies installed${NC}"
elif python3 -m pip install --user --no-cache-dir --break-system-packages -r "$ROOT_DIR/requirements.txt" 2>/dev/null; then
    echo -e "${GREEN}✓ Dependencies installed (with --break-system-packages)${NC}"
else
    echo -e "${YELLOW}⚠ Failed to install dependencies${NC}"
    echo "Try manually: pip3 install --user -r $ROOT_DIR/requirements.txt"
fi

# 4. Create user command
echo "Creating user command..."
mkdir -p ~/.local/bin
ln -sf "$ROOT_DIR/ipcrawler" ~/.local/bin/ipcrawler
echo -e "${GREEN}✓ User command created${NC}"

# 5. Create system command for sudo
echo ""
echo "Creating system command for sudo usage..."
echo "This requires sudo password:"
if sudo mkdir -p /usr/local/bin && sudo ln -sf "$ROOT_DIR/ipcrawler" /usr/local/bin/ipcrawler; then
    echo -e "${GREEN}✓ System command created${NC}"
    echo ""
    echo -e "${GREEN}Success! You can now use:${NC}"
    echo "  ipcrawler <target>       (regular user)"
    echo "  sudo ipcrawler <target>  (privileged scan)"
else
    echo -e "${RED}✗ Failed to create system command${NC}"
    echo "You can try manually:"
    echo "  sudo ln -sf $ROOT_DIR/ipcrawler /usr/local/bin/ipcrawler"
fi

echo ""
echo "Testing installation..."
if command -v ipcrawler >/dev/null 2>&1; then
    echo -e "${GREEN}✓ ipcrawler found in PATH${NC}"
else
    echo -e "${YELLOW}⚠ ipcrawler not in PATH${NC}"
    echo "Add to your shell config: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

if sudo which ipcrawler >/dev/null 2>&1; then
    echo -e "${GREEN}✓ sudo ipcrawler works${NC}"
else
    echo -e "${YELLOW}⚠ sudo ipcrawler not working${NC}"
fi

echo ""
echo "Done!"