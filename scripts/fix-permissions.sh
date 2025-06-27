#!/bin/bash

# IPCrawler Permission Fixer
# Fixes ownership of results directory and files when they were created by root
# This happens when ipcrawler is run with sudo (needed for UDP scans)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/results"

echo -e "${BLUE}🔧 IPCrawler Permission Fixer${NC}"
echo "=================================="

# Check if results directory exists
if [ ! -d "$RESULTS_DIR" ]; then
    echo -e "${YELLOW}ℹ️  No results directory found at: $RESULTS_DIR${NC}"
    echo "Nothing to fix!"
    exit 0
fi

echo -e "${BLUE}📁 Checking results directory: $RESULTS_DIR${NC}"

# Count files and check ownership
TOTAL_FILES=$(find "$RESULTS_DIR" -type f | wc -l | tr -d ' ')
ROOT_OWNED_FILES=$(find "$RESULTS_DIR" -user root 2>/dev/null | wc -l | tr -d ' ' || echo "0")
ROOT_OWNED_DIRS=$(find "$RESULTS_DIR" -type d -user root 2>/dev/null | wc -l | tr -d ' ' || echo "0")

echo "📊 Found $TOTAL_FILES total files"
echo "🔍 Root-owned files: $ROOT_OWNED_FILES"
echo "🔍 Root-owned directories: $ROOT_OWNED_DIRS"

if [ "$ROOT_OWNED_FILES" -eq 0 ] && [ "$ROOT_OWNED_DIRS" -eq 0 ]; then
    echo -e "${GREEN}✅ All files already have correct ownership!${NC}"
    exit 0
fi

# Get current user info
CURRENT_USER=$(whoami)
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

echo ""
echo -e "${YELLOW}⚠️  Found root-owned files that need permission fixing${NC}"
echo "This happens when ipcrawler was run with sudo (for UDP scans)"
echo ""
echo "Current user: $CURRENT_USER (UID: $CURRENT_UID, GID: $CURRENT_GID)"
echo ""

# Check if we need sudo to fix permissions
if [ "$ROOT_OWNED_FILES" -gt 0 ] || [ "$ROOT_OWNED_DIRS" -gt 0 ]; then
    echo -e "${BLUE}🔐 Fixing ownership of root-owned files...${NC}"
    
    # Try to fix permissions
    if [ "$EUID" -eq 0 ]; then
        # Already running as root
        echo "Running as root - fixing permissions directly..."
        chown -R "$CURRENT_USER:$CURRENT_GID" "$RESULTS_DIR" 2>/dev/null || {
            # If we don't know the original user, try to find it from SUDO_USER
            if [ -n "$SUDO_USER" ]; then
                echo "Using SUDO_USER: $SUDO_USER"
                SUDO_UID=$(id -u "$SUDO_USER")
                SUDO_GID=$(id -g "$SUDO_USER")
                chown -R "$SUDO_UID:$SUDO_GID" "$RESULTS_DIR"
            else
                echo -e "${RED}❌ Cannot determine original user. Please run manually:${NC}"
                echo "   sudo chown -R \$USER:\$(id -g) \"$RESULTS_DIR\""
                exit 1
            fi
        }
    else
        # Need to use sudo
        echo "🔑 Need sudo privileges to fix root-owned files..."
        
        # Check if sudo is available
        if ! command -v sudo >/dev/null 2>&1; then
            echo -e "${RED}❌ sudo not available. Please run as root:${NC}"
            echo "   chown -R $CURRENT_USER:$CURRENT_GID \"$RESULTS_DIR\""
            exit 1
        fi
        
        # Use sudo to fix permissions
        echo "Running: sudo chown -R $CURRENT_USER:$CURRENT_GID \"$RESULTS_DIR\""
        if sudo chown -R "$CURRENT_USER:$CURRENT_GID" "$RESULTS_DIR"; then
            echo -e "${GREEN}✅ Permissions fixed successfully!${NC}"
        else
            echo -e "${RED}❌ Failed to fix permissions${NC}"
            exit 1
        fi
    fi
    
    # Verify the fix
    NEW_ROOT_FILES=$(find "$RESULTS_DIR" -user root 2>/dev/null | wc -l | tr -d ' ' || echo "0")
    NEW_ROOT_DIRS=$(find "$RESULTS_DIR" -type d -user root 2>/dev/null | wc -l | tr -d ' ' || echo "0")
    
    if [ "$NEW_ROOT_FILES" -eq 0 ] && [ "$NEW_ROOT_DIRS" -eq 0 ]; then
        echo -e "${GREEN}✅ All files now owned by $CURRENT_USER${NC}"
        echo -e "${GREEN}🗑️  You can now safely delete the results directory if needed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some files may still have root ownership${NC}"
        echo "Remaining root-owned files: $NEW_ROOT_FILES"
        echo "Remaining root-owned directories: $NEW_ROOT_DIRS"
    fi
fi

echo ""
echo -e "${BLUE}💡 To prevent this in the future:${NC}"
echo "   • Run ipcrawler without sudo when possible"
echo "   • Use --no-udp-scan to avoid needing root privileges"
echo "   • Or run this script after scans: ./scripts/fix-permissions.sh"
echo "" 