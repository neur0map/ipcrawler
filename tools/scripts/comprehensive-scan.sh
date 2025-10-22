#!/bin/bash
# Comprehensive multi-tool scanning script
# Usage: comprehensive-scan.sh <target> <port> <output_file>

TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

if [ -z "$TARGET" ] || [ -z "$PORT" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <target> <port> <output_file>"
    exit 1
fi

echo "=== COMPREHENSIVE SCAN RESULTS FOR $TARGET:$PORT ===" > "$OUTPUT_FILE"
echo "Scan started at: $(date)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 1. Basic connectivity check
echo "=== CONNECTIVITY CHECK ===" >> "$OUTPUT_FILE"
timeout 5 bash -c "</dev/tcp/$TARGET/$PORT" 2>/dev/null && echo "Port $PORT is OPEN" >> "$OUTPUT_FILE" || echo "Port $PORT is CLOSED or FILTERED" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 2. Service banner grabbing
echo "=== SERVICE BANNER ===" >> "$OUTPUT_FILE"
timeout 10 bash -c "echo '' | nc -w 3 $TARGET $PORT 2>/dev/null | head -10" >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 3. SSL/TLS information (if HTTPS)
if [ "$PORT" = "443" ] || [ "$PORT" = "8443" ]; then
    echo "=== SSL/TLS INFORMATION ===" >> "$OUTPUT_FILE"
    timeout 10 openssl s_client -connect "$TARGET:$PORT" -servername "$TARGET" 2>/dev/null | openssl x509 -noout -dates -subject -issuer 2>/dev/null >> "$OUTPUT_FILE" 2>&1
    timeout 10 sslscan --no-fail "$TARGET:$PORT" 2>/dev/null | grep -E "(Accepted|Version|Cipher|Strength)" >> "$OUTPUT_FILE" 2>&1
    echo "" >> "$OUTPUT_FILE"
fi

# 4. HTTP headers and server info
if [ "$PORT" = "80" ] || [ "$PORT" = "443" ] || [ "$PORT" = "8080" ] || [ "$PORT" = "8443" ]; then
    echo "=== HTTP INFORMATION ===" >> "$OUTPUT_FILE"
    PROTO="http"
    if [ "$PORT" = "443" ] || [ "$PORT" = "8443" ]; then
        PROTO="https"
    fi
    
    timeout 10 curl -s -I "$PROTO://$TARGET:$PORT/" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
    echo "" >> "$OUTPUT_FILE"
    
    # Server technology detection
    timeout 10 whatweb --no-errors "$PROTO://$TARGET:$PORT/" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
    echo "" >> "$OUTPUT_FILE"
fi

# 5. DNS resolution
echo "=== DNS INFORMATION ===" >> "$OUTPUT_FILE"
nslookup "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
dig +short "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
host "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 6. Traceroute
echo "=== NETWORK PATH ===" >> "$OUTPUT_FILE"
timeout 30 traceroute "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 7. WHOIS information
echo "=== WHOIS INFORMATION ===" >> "$OUTPUT_FILE"
timeout 30 whois "$TARGET" 2>/dev/null | grep -E "(Registrar|Created|Expires|Organization|Country)" >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 8. Quick vulnerability patterns
echo "=== QUICK VULNERABILITY CHECKS ===" >> "$OUTPUT_FILE"
if [ "$PORT" = "80" ] || [ "$PORT" = "443" ] || [ "$PORT" = "8080" ] || [ "$PORT" = "8443" ]; then
    PROTO="http"
    if [ "$PORT" = "443" ] || [ "$PORT" = "8443" ]; then
        PROTO="https"
    fi
    
    # Check for common paths
    for path in "/admin" "/login" "/wp-admin" "/phpmyadmin" "/.git/config" "/backup" "/config"; do
        timeout 5 curl -s -o /dev/null -w "%{http_code}" "$PROTO://$TARGET:$PORT$path" 2>/dev/null | grep -E "200|301|302|403" >/dev/null && echo "Interesting path found: $path" >> "$OUTPUT_FILE"
    done
fi

echo "" >> "$OUTPUT_FILE"
echo "=== SCAN COMPLETED ===" >> "$OUTPUT_FILE"
echo "Scan finished at: $(date)" >> "$OUTPUT_FILE"