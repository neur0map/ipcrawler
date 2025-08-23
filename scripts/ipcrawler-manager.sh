#!/bin/sh
# ipcrawler Binary Management Helper
# Handles discovery, verification, and atomic replacement of production binaries
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Common directories to scan
SCAN_DIRS="/usr/local/bin /usr/bin ~/.cargo/bin ~/.local/bin"

# Add Homebrew/MacPorts paths if they exist
if [ -d "/opt/homebrew/bin" ]; then
    SCAN_DIRS="$SCAN_DIRS /opt/homebrew/bin"
fi
if [ -d "/opt/local/bin" ]; then
    SCAN_DIRS="$SCAN_DIRS /opt/local/bin"
fi

# Compute SHA256 (cross-platform)
compute_sha256() {
    local file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$file" | cut -d' ' -f1
    else
        echo "ERROR: No SHA256 tool available" >&2
        exit 1
    fi
}

# Find all ipcrawler binaries
find_all_binaries() {
    local binaries=""
    
    # Find via PATH
    if command -v ipcrawler >/dev/null 2>&1; then
        # Get all PATH instances
        local path_bins
        path_bins=$(command -v -a ipcrawler 2>/dev/null || true)
        if [ -n "$path_bins" ]; then
            binaries="$binaries $path_bins"
        fi
    fi
    
    # Scan common directories
    for dir in $SCAN_DIRS; do
        # Expand tilde
        case "$dir" in
            ~/*) dir="$HOME${dir#~}" ;;
        esac
        
        if [ -d "$dir" ] && [ -f "$dir/ipcrawler" ] && [ -x "$dir/ipcrawler" ]; then
            binaries="$binaries $dir/ipcrawler"
        fi
    done
    
    # Remove duplicates and sort
    echo "$binaries" | tr ' ' '\n' | sort -u | grep -v '^$' || true
}

# Get production binary path (first on PATH)
get_production_path() {
    command -v ipcrawler 2>/dev/null || echo ""
}

# Get canonical production install location
get_canonical_prod_path() {
    local existing_prod
    existing_prod=$(get_production_path)
    
    if [ -n "$existing_prod" ]; then
        echo "$existing_prod"
    else
        # Default location
        echo "/usr/local/bin/ipcrawler"
    fi
}

# Show all binaries with diagnostics
show_binaries() {
    local repo_binary="./target/release/ipcrawler"
    local prod_path
    prod_path=$(get_production_path)
    local all_binaries
    all_binaries=$(find_all_binaries)
    
    echo "${BOLD}📍 IPCRAWLER BINARY LOCATIONS${NC}"
    echo "=================================="
    
    if [ -f "$repo_binary" ]; then
        local repo_sha
        repo_sha=$(compute_sha256 "$repo_binary")
        local repo_size
        repo_size=$(ls -lh "$repo_binary" | awk '{print $5}')
        local repo_mtime
        repo_mtime=$(ls -l "$repo_binary" | awk '{print $6, $7, $8}')
        
        echo "${BLUE}📁 DEVELOPMENT (Repository)${NC}"
        echo "   Path: $repo_binary"
        echo "   Size: $repo_size"
        echo "   Modified: $repo_mtime"
        echo "   SHA256: $repo_sha"
        echo
    fi
    
    if [ -n "$all_binaries" ]; then
        echo "${GREEN}🚀 PRODUCTION BINARIES${NC}"
        echo "$all_binaries" | while read -r binary; do
            if [ -n "$binary" ] && [ -f "$binary" ]; then
                local is_active=""
                if [ "$binary" = "$prod_path" ]; then
                    is_active=" ${BOLD}${GREEN}[ACTIVE]${NC}"
                fi
                
                local sha
                sha=$(compute_sha256 "$binary")
                local size
                size=$(ls -lh "$binary" | awk '{print $5}')
                local mtime
                mtime=$(ls -l "$binary" | awk '{print $6, $7, $8}')
                
                echo "   ${YELLOW}→${NC} $binary$is_active"
                echo "     Size: $size, Modified: $mtime"
                echo "     SHA256: $sha"
                
                # Check if it's the same as repo binary
                if [ -f "$repo_binary" ]; then
                    local repo_sha
                    repo_sha=$(compute_sha256 "$repo_binary")
                    if [ "$sha" = "$repo_sha" ]; then
                        echo "     ${RED}⚠️  WARNING: Same as repository binary, if you do not see this messageyou have a problem${NC}"
                    fi
                fi
                echo
            fi
        done
    else
        echo "${YELLOW}⚠️  No production binaries found on PATH${NC}"
        echo
    fi
    
    if [ -n "$prod_path" ]; then
        echo "${GREEN}🎯 ACTIVE PRODUCTION: $prod_path${NC}"
    else
        echo "${YELLOW}🎯 NO ACTIVE PRODUCTION BINARY${NC}"
    fi
}

# Verify binary separation and detect issues
verify_separation() {
    local repo_binary="./target/release/ipcrawler"
    local prod_path
    prod_path=$(get_production_path)
    local issues=0
    
    echo "${BOLD}🔍 VERIFYING BINARY SEPARATION${NC}"
    echo "================================"
    
    # Check 1: Production binary exists
    if [ -z "$prod_path" ]; then
        echo "${YELLOW}⚠️  No production binary found on PATH${NC}"
        issues=$((issues + 1))
    else
        echo "${GREEN}✓ Production binary found: $prod_path${NC}"
        
        # Check 2: Production binary is not the repo binary
        if [ "$prod_path" = "$(realpath "$repo_binary" 2>/dev/null || echo "$repo_binary")" ]; then
            echo "${RED}❌ CRITICAL: Production binary IS the repository binary${NC}"
            issues=$((issues + 1))
        else
            echo "${GREEN}✓ Production binary is separate from repository${NC}"
        fi
        
        # Check 3: SHA verification if just built
        if [ -f "./target/release/.ipcrawler-built" ]; then
            local built_sha
            built_sha=$(cat "./target/release/.ipcrawler-built" 2>/dev/null || echo "")
            if [ -n "$built_sha" ]; then
                local prod_sha
                prod_sha=$(compute_sha256 "$prod_path")
                if [ "$built_sha" = "$prod_sha" ]; then
                    echo "${GREEN}✓ Production binary matches freshly built artifact${NC}"
                else
                    echo "${RED}❌ Production binary SHA mismatch with built artifact${NC}"
                    echo "   Built:      $built_sha"
                    echo "   Production: $prod_sha"
                    issues=$((issues + 1))
                fi
            fi
        fi
    fi
    
    # Check 4: Detect duplicates that could shadow
    local all_binaries
    all_binaries=$(find_all_binaries)
    local binary_count
    binary_count=$(echo "$all_binaries" | wc -l)
    
    if [ "$binary_count" -gt 1 ]; then
        echo "${RED}❌ Multiple ipcrawler binaries found (shadowing risk):${NC}"
        echo "$all_binaries" | while read -r binary; do
            if [ -n "$binary" ]; then
                echo "   → $binary"
            fi
        done
        echo
        echo "${YELLOW}💡 To fix: Remove or rename duplicate binaries${NC}"
        echo "   Example: mv ~/.cargo/bin/ipcrawler ~/.cargo/bin/ipcrawler.backup"
        issues=$((issues + 1))
    else
        echo "${GREEN}✓ No duplicate binaries detected${NC}"
    fi
    
    echo
    if [ "$issues" -eq 0 ]; then
        echo "${GREEN}🎉 ALL CHECKS PASSED - Binary separation is correct${NC}"
        return 0
    else
        echo "${RED}💥 FAILED: $issues issue(s) found${NC}"
        return 1
    fi
}

# Atomic replacement of production binary
atomic_replace() {
    local src="$1"
    local dest="$2"
    
    # Verify source exists
    if [ ! -f "$src" ]; then
        echo "${RED}❌ Source binary not found: $src${NC}" >&2
        exit 1
    fi
    
    # Create destination directory if needed
    local dest_dir
    dest_dir=$(dirname "$dest")
    if [ ! -d "$dest_dir" ]; then
        echo "${YELLOW}📁 Creating directory: $dest_dir${NC}"
        if ! mkdir -p "$dest_dir" 2>/dev/null; then
            echo "${RED}❌ Cannot create directory: $dest_dir${NC}" >&2
            echo "   Run with sudo or check permissions" >&2
            exit 1
        fi
    fi
    
    # Check if we can write to the destination
    if [ -f "$dest" ] && [ ! -w "$dest" ]; then
        echo "${RED}❌ Cannot write to: $dest${NC}" >&2
        echo "   Run with: sudo make build-prod" >&2
        exit 1
    fi
    
    if [ ! -w "$dest_dir" ]; then
        echo "${RED}❌ Cannot write to directory: $dest_dir${NC}" >&2
        echo "   Run with: sudo make build-prod" >&2
        exit 1
    fi
    
    # Atomic replacement using install command
    local temp_dest="$dest.tmp.$$"
    
    echo "${BLUE}📦 Installing binary atomically...${NC}"
    if install -m 0755 "$src" "$temp_dest"; then
        if mv "$temp_dest" "$dest"; then
            echo "${GREEN}✅ Successfully installed to: $dest${NC}"
            
            # Store SHA for verification
            local sha
            sha=$(compute_sha256 "$dest")
            echo "$sha" > "./target/release/.ipcrawler-built"
            
            # Clear shell hash cache
            echo
            echo "${YELLOW}🔄 Clear shell command cache:${NC}"
            echo "   Run: hash -r   (or restart terminal)"
        else
            rm -f "$temp_dest"
            echo "${RED}❌ Failed to move binary to final location${NC}" >&2
            exit 1
        fi
    else
        rm -f "$temp_dest"
        echo "${RED}❌ Failed to install binary${NC}" >&2
        exit 1
    fi
}

# Main command dispatcher
case "${1:-}" in
    "show")
        show_binaries
        ;;
    "verify")
        verify_separation
        ;;
    "replace")
        if [ $# -ne 3 ]; then
            echo "Usage: $0 replace <source> <destination>" >&2
            exit 1
        fi
        atomic_replace "$2" "$3"
        ;;
    *)
        echo "Usage: $0 {show|verify|replace <src> <dest>}" >&2
        echo
        echo "Commands:"
        echo "  show     - Display all ipcrawler binaries with diagnostics"
        echo "  verify   - Verify binary separation and detect issues"
        echo "  replace  - Atomically replace production binary"
        exit 1
        ;;
esac