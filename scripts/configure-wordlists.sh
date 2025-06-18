#!/bin/bash

# Wordlist Configuration Script
# Usage: ./scripts/configure-wordlists.sh [local|htb|kali]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../ipcrawler/global.toml"

show_help() {
    echo "Wordlist Configuration Script"
    echo ""
    echo "Usage: ./scripts/configure-wordlists.sh [mode]"
    echo ""
    echo "Modes:"
    echo "  status - Show current configuration"
    echo "  test   - Test if configured wordlists are accessible"
    echo ""
    echo "💡 To customize wordlists:"
    echo "   Edit ipcrawler/global.toml and change any wordlist path:"
    echo "   directory-wordlist = '/your/custom/wordlist.txt'"
    echo "   vhost-wordlist = '/usr/share/seclists/Discovery/DNS/big-list.txt'"
    echo ""
    echo "💡 ipcrawler will automatically fallback to local wordlists if"
    echo "   your configured paths don't exist (useful for HTB/remote testing)"
    echo ""
    echo "Examples:"
    echo "  ./scripts/configure-wordlists.sh status  # Show current config"
    echo "  ./scripts/configure-wordlists.sh test    # Test wordlist accessibility"
}

show_status() {
    echo "Current wordlist configuration:"
    echo ""
    grep -E "^(directory-wordlist|vhost-wordlist|lfi-parameter-wordlist)" "$CONFIG_FILE" | sed 's/^/  /'
    echo ""
}

test_wordlists() {
    echo "🧪 Testing wordlist accessibility..."
    echo ""
    
    # Test each configured wordlist
    while IFS= read -r line; do
        if [[ "$line" =~ ^([a-z-]+)-wordlist[[:space:]]*=[[:space:]]*[\'\"]*([^\'\"]+)[\'\"]*$ ]]; then
            wordlist_type="${BASH_REMATCH[1]}"
            wordlist_path="${BASH_REMATCH[2]}"
            
            # Resolve relative paths
            if [[ "$wordlist_path" = /* ]]; then
                # Absolute path
                full_path="$wordlist_path"
            else
                # Relative path - resolve relative to config file
                config_dir="$(dirname "$CONFIG_FILE")"
                full_path="$config_dir/$wordlist_path"
            fi
            
            if [ -f "$full_path" ]; then
                lines=$(wc -l < "$full_path" 2>/dev/null || echo "?")
                echo "✅ $wordlist_type: $wordlist_path ($lines lines)"
            else
                echo "❌ $wordlist_type: $wordlist_path (not found)"
                
                # Check if fallback exists
                case "$wordlist_type" in
                    "directory") fallback="wordlists/dirbuster.txt" ;;
                    "vhost"|"subdomain"|"dns") fallback="wordlists/subdomains-top100.txt" ;;
                    "lfi-parameter") fallback="wordlists/lfi-parameters.txt" ;;
                    "lfi-payload") fallback="wordlists/lfi-payloads.txt" ;;
                    "username") fallback="wordlists/usernames-top25.txt" ;;
                    "password") fallback="wordlists/passwords-top25.txt" ;;
                    *) fallback="" ;;
                esac
                
                if [ -n "$fallback" ]; then
                    config_dir="$(dirname "$CONFIG_FILE")"
                    fallback_path="$config_dir/$fallback"
                    if [ -f "$fallback_path" ]; then
                        fallback_lines=$(wc -l < "$fallback_path" 2>/dev/null || echo "?")
                        echo "   💡 Will fallback to: $fallback ($fallback_lines lines)"
                    fi
                fi
            fi
        fi
    done < "$CONFIG_FILE"
    
    echo ""
    echo "💡 ipcrawler automatically uses local fallbacks when configured paths don't exist"
}

# Main execution
case "${1:-}" in
    "test")
        test_wordlists
        ;;
    "status")
        show_status
        ;;
    "help"|"-h"|"--help"|"")
        show_help
        ;;
    *)
        echo "❌ Unknown mode: $1"
        echo ""
        show_help
        exit 1
        ;;
esac