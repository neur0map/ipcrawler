#!/bin/bash

################################################################################
# ipcrawler Update Script
# 
# Quick update script for existing ipcrawler installations
# Usage: curl -sSL https://install.ipcrawler.io/update.sh | bash
#        or: ./update.sh
#
# Copyright (c) 2025 ipcrawler.io
################################################################################

set -euo pipefail

# Colors
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'
readonly BOLD='\033[1m'

# Configuration
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/usr/local/share/ipcrawler"
REPO_URL="https://github.com/neur0map/ipcrawler.git"

# Logging functions
log() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warning() { echo -e "${YELLOW}[⚠]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*" >&2; }

# Check for sudo
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        if command -v sudo >/dev/null 2>&1; then
            SUDO_CMD="sudo"
            if ! sudo -n true 2>/dev/null; then
                warning "This script requires sudo privileges"
                sudo true
            fi
        else
            error "This script requires sudo privileges"
            exit 1
        fi
    else
        SUDO_CMD=""
    fi
}

# Main update function
update_ipcrawler() {
    echo -e "${BLUE}${BOLD}ipcrawler Update Script${NC}"
    echo "=================================="
    echo
    
    # Check if ipcrawler is installed
    if ! command -v ipcrawler >/dev/null 2>&1; then
        error "ipcrawler is not installed"
        echo "Please run the installer first:"
        echo "  curl -sSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash"
        exit 1
    fi
    
    # Get current version
    current_version=$(ipcrawler --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "unknown")
    log "Current version: $current_version"
    
    # Check if cargo is available for building
    if ! command -v cargo >/dev/null 2>&1; then
        error "Rust toolchain not found"
        echo "Installing Rust..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
    fi
    
    # Create temporary directory
    temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT
    
    cd "$temp_dir"
    
    # Clone latest source
    log "Downloading latest source..."
    if ! git clone --quiet "$REPO_URL" . 2>/dev/null; then
        error "Failed to download source"
        exit 1
    fi
    
    # Get new version
    new_version=$(grep "^version" Cargo.toml | cut -d'"' -f2)
    log "Latest version: $new_version"
    
    # Check if update is needed
    if [[ "$current_version" == "$new_version" ]]; then
        success "Already running latest version ($new_version)"
        exit 0
    fi
    
    # Build new version
    log "Building ipcrawler $new_version..."
    if ! cargo build --release --quiet 2>/dev/null; then
        error "Build failed"
        exit 1
    fi
    
    # Backup current installation
    if [[ -f "$INSTALL_DIR/ipcrawler" ]]; then
        $SUDO_CMD cp "$INSTALL_DIR/ipcrawler" "$INSTALL_DIR/ipcrawler.backup"
        log "Backed up current version"
    fi
    
    # Install new binary
    log "Installing new version..."
    $SUDO_CMD cp target/release/ipcrawler "$INSTALL_DIR/"
    $SUDO_CMD chmod +x "$INSTALL_DIR/ipcrawler"
    
    # Update configs if directory exists
    if [[ -d "config" && -d "$CONFIG_DIR" ]]; then
        log "Updating configuration templates..."
        $SUDO_CMD cp -r config/* "$CONFIG_DIR/" 2>/dev/null || true
    fi
    
    # Verify installation
    if ipcrawler --version >/dev/null 2>&1; then
        installed_version=$(ipcrawler --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        if [[ "$installed_version" == "$new_version" ]]; then
            success "Successfully updated to version $new_version"
            
            # Remove backup
            $SUDO_CMD rm -f "$INSTALL_DIR/ipcrawler.backup"
            
            echo
            echo "Update complete! What's new:"
            echo "  • Check release notes at: https://github.com/neur0map/ipcrawler/releases"
            echo "  • Run 'ipcrawler --help' to see new features"
            echo
        else
            error "Version mismatch after update"
            warning "Restoring previous version..."
            $SUDO_CMD mv "$INSTALL_DIR/ipcrawler.backup" "$INSTALL_DIR/ipcrawler"
            exit 1
        fi
    else
        error "Update verification failed"
        warning "Restoring previous version..."
        $SUDO_CMD mv "$INSTALL_DIR/ipcrawler.backup" "$INSTALL_DIR/ipcrawler"
        exit 1
    fi
}

# Run update
check_sudo
update_ipcrawler