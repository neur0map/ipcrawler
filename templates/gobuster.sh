#!/bin/bash
# Gobuster wrapper that handles URL construction

TARGET="$1"
WORDLIST="$2"
OUTPUT_FILE="$3"

# Check if target already has a scheme
if [[ "$TARGET" =~ ^https?:// ]]; then
    URL="$TARGET"
else
    # Try to detect open HTTP/HTTPS ports
    # For now, default to http:// (could enhance to check nmap results)
    if command -v nmap &> /dev/null; then
        # Quick check for common web ports
        HTTP_OPEN=$(nmap -p 80,8080 --open -T4 "$TARGET" 2>/dev/null | grep -E "80|8080" | grep open)
        HTTPS_OPEN=$(nmap -p 443,8443 --open -T4 "$TARGET" 2>/dev/null | grep -E "443|8443" | grep open)
        
        if [ -n "$HTTPS_OPEN" ]; then
            URL="https://$TARGET"
        elif [ -n "$HTTP_OPEN" ]; then
            URL="http://$TARGET"
        else
            echo "[INFO] No HTTP/HTTPS ports detected on $TARGET. Skipping gobuster."
            exit 0
        fi
    else
        # Fallback: try http first
        URL="http://$TARGET"
    fi
fi

echo "[*] Running gobuster against: $URL"
gobuster dir -u "$URL" -w "$WORDLIST" -o "$OUTPUT_FILE" -q
EXIT_CODE=$?

# Gobuster returns 1 if no results found, which is normal
if [ $EXIT_CODE -eq 1 ] && [ -f "$OUTPUT_FILE" ] && [ ! -s "$OUTPUT_FILE" ]; then
    echo "[INFO] No directories/files found (or target unreachable)"
    exit 0
fi

exit $EXIT_CODE
