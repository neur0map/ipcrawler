#!/bin/bash
# Manual SecLists catalog generator for IPCrawler

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}IPCrawler SecLists Catalog Generator${NC}"
echo "====================================="
echo ""

# Check if SecLists is installed
echo -e "${YELLOW}Checking for SecLists installation...${NC}"
if [ -f .seclists_path ]; then
    source .seclists_path
    if [ ! -z "$SECLISTS_PATH" ] && [ -d "$SECLISTS_PATH" ]; then
        echo -e "${GREEN}✓ SecLists found at: $SECLISTS_PATH${NC}"
    else
        echo -e "${RED}✗ SecLists path invalid or not found${NC}"
        echo "Running SecLists checker..."
        # Pass AUTO_INSTALL environment variable if set
        if [ "$AUTO_INSTALL" = "true" ]; then
            AUTO_INSTALL=true bash scripts/check_seclists.sh
        else
            bash scripts/check_seclists.sh
        fi
        source .seclists_path
    fi
else
    echo -e "${YELLOW}No SecLists configuration found. Running installer...${NC}"
    # Pass AUTO_INSTALL environment variable if set
    if [ "$AUTO_INSTALL" = "true" ]; then
        AUTO_INSTALL=true bash scripts/check_seclists.sh
    else
        bash scripts/check_seclists.sh
    fi
    source .seclists_path
fi

# Generate catalog if SecLists is available
if [ ! -z "$SECLISTS_PATH" ] && [ -d "$SECLISTS_PATH" ]; then
    echo ""
    echo -e "${YELLOW}Generating wordlist catalog...${NC}"
    echo "This may take a few minutes depending on your system..."
    
    # Run the catalog generator
    if python3 tools/catalog/generate_catalog.py "$SECLISTS_PATH"; then
        echo ""
        echo -e "${GREEN}✓ Catalog generated successfully!${NC}"
        
        # Show catalog info
        if [ -f database/wordlists/seclists_catalog.json ]; then
            CATALOG_SIZE=$(du -h database/wordlists/seclists_catalog.json | cut -f1)
            WORDLIST_COUNT=$(python3 -c "import json; data=json.load(open('database/wordlists/seclists_catalog.json')); print(len(data.get('wordlists', [])))")
            echo -e "  → Catalog size: ${CATALOG_SIZE}"
            echo -e "  → Wordlists indexed: ${WORDLIST_COUNT}"
            echo ""
            echo -e "${GREEN}IPCrawler will now provide full paths to recommended wordlists!${NC}"
        fi
    else
        echo -e "${RED}✗ Failed to generate catalog${NC}"
        echo "Check the error messages above for details."
        exit 1
    fi
else
    echo -e "${RED}✗ Cannot generate catalog without SecLists${NC}"
    echo "Please install SecLists first by running:"
    echo "  bash scripts/check_seclists.sh"
    exit 1
fi