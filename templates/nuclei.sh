#!/bin/bash
# Nuclei wrapper that handles URL construction

TARGET="$1"
shift  # Remove first arg, rest are nuclei arguments

# Check if target already has a scheme
if [[ "$TARGET" =~ ^https?:// ]]; then
    URL="$TARGET"
else
    # Try to detect open HTTP/HTTPS ports
    if command -v nmap &> /dev/null; then
        HTTP_OPEN=$(nmap -p 80,8080 --open -T4 "$TARGET" 2>/dev/null | grep -E "80|8080" | grep open)
        HTTPS_OPEN=$(nmap -p 443,8443 --open -T4 "$TARGET" 2>/dev/null | grep -E "443|8443" | grep open)
        
        if [ -n "$HTTPS_OPEN" ]; then
            URL="https://$TARGET"
        elif [ -n "$HTTP_OPEN" ]; then
            URL="http://$TARGET"
        else
            echo "[INFO] No HTTP/HTTPS ports detected on $TARGET. Skipping nuclei."
            exit 0
        fi
    else
        URL="http://$TARGET"
    fi
fi

echo "[*] Running nuclei against: $URL"
nuclei -u "$URL" "$@"
EXIT_CODE=$?

# Nuclei returns 2 when no vulnerabilities found, which is actually good
if [ $EXIT_CODE -eq 2 ]; then
    echo "[INFO] Nuclei scan complete - no vulnerabilities detected"
    exit 0
fi

exit $EXIT_CODE
