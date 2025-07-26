#!/bin/bash
# SecLists Installation Checker and Installer for IPCrawler

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# SecLists info
SECLISTS_REPO="https://github.com/danielmiessler/SecLists.git"
SECLISTS_SIZE="~1.5GB"

# Possible SecLists locations (in order of preference)
SECLISTS_PATHS=(
    "/opt/SecLists"
    "/usr/share/SecLists" 
    "/usr/local/share/SecLists"
    "/usr/share/seclists"          # Kali/Ubuntu package manager location
    "/usr/share/wordlists/seclists" # Alternative Kali location
    "/usr/share/wordlists/SecLists" # Alternative Kali location
    "/opt/seclists"                # Lowercase variant
    "/home/kali/SecLists"          # Default Kali user
    "/root/SecLists"               # Root user location
    "$HOME/SecLists"
    "$HOME/.local/share/SecLists"
    "$HOME/seclists"               # Lowercase in home
    "$HOME/tools/SecLists"         # Common tools directory
    "$HOME/tools/seclists"         # Lowercase tools directory
    "/pentest/SecLists"            # Pentest environment
    "/tools/SecLists"              # Common tools location
)

# Function to check if SecLists exists and is valid
check_seclists_installation() {
    local found_paths=()
    
    # Check predefined paths
    for path in "${SECLISTS_PATHS[@]}"; do
        if validate_seclists_directory "$path"; then
            found_paths+=("$path")
        fi
    done
    
    # Additional dynamic searches
    # Search for seclists in common package manager locations
    if command -v find >/dev/null 2>&1; then
        # Search in /usr/share for any seclists-related directories
        while IFS= read -r -d '' dir; do
            if validate_seclists_directory "$dir"; then
                found_paths+=("$dir")
            fi
        done < <(find /usr/share -maxdepth 2 -type d -iname "*seclists*" 2>/dev/null | head -10 | tr '\n' '\0')
        
        # Search in /opt for seclists
        while IFS= read -r -d '' dir; do
            if validate_seclists_directory "$dir"; then
                found_paths+=("$dir")
            fi
        done < <(find /opt -maxdepth 2 -type d -iname "*seclists*" 2>/dev/null | head -5 | tr '\n' '\0')
    fi
    
    # Return the best match (prefer standard locations)
    if [ ${#found_paths[@]} -gt 0 ]; then
        # Sort by preference (shorter paths and standard locations first)
        printf '%s\n' "${found_paths[@]}" | sort -t/ -k2,2n | head -1
        return 0
    fi
    
    return 1
}

# Function to validate if a directory contains valid SecLists structure
validate_seclists_directory() {
    local path="$1"
    
    # Skip if path doesn't exist or isn't a directory
    [ -d "$path" ] || return 1
    
    # Check for key SecLists directories/files
    local required_indicators=(
        "Discovery/Web-Content"
        "Discovery/DNS"
        "Passwords"
        "Usernames"
    )
    
    local found_indicators=0
    for indicator in "${required_indicators[@]}"; do
        if [ -d "$path/$indicator" ] || [ -f "$path/$indicator" ]; then
            ((found_indicators++))
        fi
    done
    
    # Also check for common wordlist files
    local wordlist_files=(
        "Discovery/Web-Content/common.txt"
        "Discovery/Web-Content/directory-list-2.3-medium.txt"
        "Discovery/DNS/subdomains-top1million-5000.txt"
    )
    
    for wordlist in "${wordlist_files[@]}"; do
        if [ -f "$path/$wordlist" ]; then
            ((found_indicators++))
        fi
    done
    
    # Require at least 2 indicators to consider it valid SecLists
    [ $found_indicators -ge 2 ]
}

# Function to get best installation path
get_install_path() {
    # If auto-installing, always use home directory to avoid sudo issues
    if [ "$AUTO_INSTALL" = "true" ]; then
        echo "$HOME/SecLists"
    # Try /opt/SecLists if we have sudo access
    elif sudo -n true 2>/dev/null; then
        echo "/opt/SecLists"
    else
        echo "$HOME/SecLists"
    fi
}

# Function to check available disk space
check_disk_space() {
    local install_path="$1"
    local install_dir=$(dirname "$install_path")
    
    # Get available space in GB
    local available_gb
    if command -v df >/dev/null 2>&1; then
        available_gb=$(df -BG "$install_dir" 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G//')
        if [ -n "$available_gb" ] && [ "$available_gb" -lt 2 ]; then
            echo -e "${RED}Error: Not enough disk space. Need at least 2GB, have ${available_gb}GB${NC}"
            return 1
        fi
    fi
    return 0
}

# Function to install SecLists
install_seclists() {
    local install_path="$1"
    local install_dir=$(dirname "$install_path")
    
    echo -e "${BLUE}Installing SecLists to $install_path...${NC}"
    
    # Check disk space
    if ! check_disk_space "$install_path"; then
        return 1
    fi
    
    # Create parent directory if needed
    if [ "$install_path" = "/opt/SecLists" ]; then
        sudo mkdir -p "$install_dir"
        echo -e "${YELLOW}Cloning SecLists (this may take several minutes)...${NC}"
        sudo git clone --depth 1 "$SECLISTS_REPO" "$install_path"
        sudo chown -R $(whoami):$(whoami) "$install_path" 2>/dev/null || true
    else
        mkdir -p "$install_dir"
        echo -e "${YELLOW}Cloning SecLists (this may take several minutes)...${NC}"
        git clone --depth 1 "$SECLISTS_REPO" "$install_path"
    fi
    
    # Verify installation
    if [ -d "$install_path/Discovery/Web-Content" ]; then
        echo -e "${GREEN}✓ SecLists installed successfully to $install_path${NC}"
        return 0
    else
        echo -e "${RED}✗ SecLists installation failed${NC}"
        return 1
    fi
}

# Function to prompt user for installation
prompt_install() {
    echo -e "${YELLOW}SecLists not found on this system.${NC}"
    echo -e "${BLUE}SecLists is a collection of wordlists for security testing.${NC}"
    echo -e "Repository: $SECLISTS_REPO"
    echo -e "Size: $SECLISTS_SIZE"
    echo ""
    
    local install_path=$(get_install_path)
    echo -e "Installation location: ${BLUE}$install_path${NC}"
    echo ""
    
    # Check if this is an automated install
    if [ "$AUTO_INSTALL" = "true" ]; then
        echo -e "${YELLOW}Auto-installing SecLists...${NC}"
        return 0
    fi
    
    read -p "Would you like to install SecLists now? (Y/n): " response
    case "$response" in
        [nN][oO]|[nN])
            echo -e "${YELLOW}⚠ Skipping SecLists installation.${NC}"
            echo -e "${YELLOW}  Some wordlist features may not work optimally.${NC}"
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

# Function to update existing SecLists
update_seclists() {
    local seclists_path="$1"
    echo -e "${BLUE}Updating existing SecLists at $seclists_path...${NC}"
    
    cd "$seclists_path"
    if git pull origin master >/dev/null 2>&1; then
        echo -e "${GREEN}✓ SecLists updated successfully${NC}"
    else
        echo -e "${YELLOW}⚠ Failed to update SecLists (continuing with existing version)${NC}"
    fi
}

# Function to display SecLists info
display_seclists_info() {
    local seclists_path="$1"
    
    echo -e "${GREEN}✓ SecLists found at: $seclists_path${NC}"
    
    # Count wordlists
    local wordlist_count=0
    if command -v find >/dev/null 2>&1; then
        wordlist_count=$(find "$seclists_path" -name "*.txt" 2>/dev/null | wc -l)
        echo -e "  → Contains ~$wordlist_count wordlist files"
    fi
    
    # Show size
    if command -v du >/dev/null 2>&1; then
        local size=$(du -sh "$seclists_path" 2>/dev/null | cut -f1)
        echo -e "  → Total size: $size"
    fi
}

# Function to debug SecLists detection
debug_seclists_detection() {
    echo -e "${YELLOW}=== SecLists Detection Debug ===${NC}"
    echo -e "Checking predefined paths:"
    
    for path in "${SECLISTS_PATHS[@]}"; do
        if [ -d "$path" ]; then
            echo -e "  ${GREEN}✓${NC} $path (exists)"
            if validate_seclists_directory "$path"; then
                echo -e "    ${GREEN}✓${NC} Valid SecLists structure"
            else
                echo -e "    ${RED}✗${NC} Invalid SecLists structure"
            fi
        else
            echo -e "  ${RED}✗${NC} $path (not found)"
        fi
    done
    
    echo -e "\nSearching dynamically:"
    if command -v find >/dev/null 2>&1; then
        echo -e "  Searching /usr/share..."
        find /usr/share -maxdepth 2 -type d -iname "*seclists*" 2>/dev/null | while read dir; do
            if validate_seclists_directory "$dir"; then
                echo -e "    ${GREEN}✓${NC} $dir (valid)"
            else
                echo -e "    ${YELLOW}?${NC} $dir (invalid structure)"
            fi
        done
        
        echo -e "  Searching /opt..."
        find /opt -maxdepth 2 -type d -iname "*seclists*" 2>/dev/null | while read dir; do
            if validate_seclists_directory "$dir"; then
                echo -e "    ${GREEN}✓${NC} $dir (valid)"
            else
                echo -e "    ${YELLOW}?${NC} $dir (invalid structure)"
            fi
        done
    fi
    echo -e "${YELLOW}================================${NC}\n"
}

# Main execution
main() {
    echo -e "${BLUE}Checking SecLists installation...${NC}"
    
    # Show debug info if requested
    if [ "$DEBUG_SECLISTS" = "true" ]; then
        debug_seclists_detection
    fi
    
    # Check if SecLists is already installed
    if seclists_path=$(check_seclists_installation); then
        display_seclists_info "$seclists_path"
        
        # Offer to update if it's a git repository
        if [ -d "$seclists_path/.git" ]; then
            if [ "$UPDATE_SECLISTS" = "true" ]; then
                update_seclists "$seclists_path"
            fi
        fi
        
        # Export path for other scripts
        echo "SECLISTS_PATH=\"$seclists_path\"" > "$PROJECT_ROOT/.seclists_path"
        return 0
    fi
    
    # SecLists not found, prompt for installation
    if prompt_install; then
        install_path=$(get_install_path)
        
        if install_seclists "$install_path"; then
            echo "SECLISTS_PATH=\"$install_path\"" > "$PROJECT_ROOT/.seclists_path"
            echo -e "${GREEN}✓ SecLists installation completed${NC}"
            return 0
        else
            echo -e "${RED}✗ SecLists installation failed${NC}"
            return 1
        fi
    else
        # User declined installation
        echo "SECLISTS_PATH=\"\"" > "$PROJECT_ROOT/.seclists_path"
        return 0
    fi
}

# Check for command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_INSTALL="true"
            shift
            ;;
        --update)
            UPDATE_SECLISTS="true"
            shift
            ;;
        --debug)
            DEBUG_SECLISTS="true"
            shift
            ;;
        --help)
            echo "SecLists Installation Checker"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --auto    Automatically install SecLists without prompting"
            echo "  --update  Update existing SecLists installation"
            echo "  --debug   Show detailed detection information"
            echo "  --help    Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"