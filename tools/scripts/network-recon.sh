#!/bin/bash
# Advanced network reconnaissance script
# Usage: network-recon.sh <target> <port> <output_file>

TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

if [ -z "$TARGET" ] || [ -z "$PORT" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <target> <port> <output_file>"
    exit 1
fi

echo "=== NETWORK RECONNAISSANCE FOR $TARGET:$PORT ===" > "$OUTPUT_FILE"
echo "Scan started at: $(date)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 1. Basic connectivity and port status
echo "=== CONNECTIVITY TEST ===" >> "$OUTPUT_FILE"
timeout 5 bash -c "</dev/tcp/$TARGET/$PORT" 2>/dev/null && echo "Port $PORT: OPEN" >> "$OUTPUT_FILE" || echo "Port $PORT: CLOSED/FILTERED" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 2. Service banner grabbing
echo "=== SERVICE BANNER ===" >> "$OUTPUT_FILE"
timeout 10 nc -w 3 "$TARGET" "$PORT" 2>/dev/null | head -10 >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 3. Telnet banner (if applicable)
if [ "$PORT" = "23" ] || [ "$PORT" = "21" ] || [ "$PORT" = "25" ] || [ "$PORT" = "110" ] || [ "$PORT" = "143" ]; then
    echo "=== TELNET BANNER ===" >> "$OUTPUT_FILE"
    timeout 5 bash -c "echo '' | telnet $TARGET $PORT 2>/dev/null | head -5" >> "$OUTPUT_FILE" 2>&1
    echo "" >> "$OUTPUT_FILE"
fi

# 4. DNS resolution and reverse DNS
echo "=== DNS INFORMATION ===" >> "$OUTPUT_FILE"
echo "Forward lookup:" >> "$OUTPUT_FILE"
nslookup "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"
echo "Reverse lookup:" >> "$OUTPUT_FILE"
dig -x "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 5. Network path analysis
echo "=== NETWORK PATH ===" >> "$OUTPUT_FILE"
echo "Traceroute:" >> "$OUTPUT_FILE"
timeout 30 traceroute "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 6. WHOIS information
echo "=== WHOIS INFORMATION ===" >> "$OUTPUT_FILE"
timeout 30 whois "$TARGET" 2>/dev/null | grep -E "(Registrar|Organization|Country|Created|Expires|Updated|Name Server)" >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 7. Service-specific reconnaissance
case "$PORT" in
    21)
        echo "=== FTP SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 bash -c "echo 'USER anonymous' | nc $TARGET $PORT 2>/dev/null | head -5" >> "$OUTPUT_FILE" 2>&1
        timeout 10 bash -c "echo 'USER ftp' | nc $TARGET $PORT 2>/dev/null | head -5" >> "$OUTPUT_FILE" 2>&1
        ;;
    22)
        echo "=== SSH SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 ssh-keyscan "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        timeout 10 nmap -sV -p 22 --script ssh2-enum-algos "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        ;;
    23)
        echo "=== TELNET SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 bash -c "echo '' | telnet $TARGET $PORT 2>/dev/null | head -10" >> "$OUTPUT_FILE" 2>&1
        ;;
    25)
        echo "=== SMTP SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 bash -c "echo 'EHLO test.com' | nc $TARGET $PORT 2>/dev/null | head -10" >> "$OUTPUT_FILE" 2>&1
        ;;
    53)
        echo "=== DNS SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 dig @$TARGET ANY example.com 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        timeout 10 nmap -sV -p 53 --script dns-zone-transfer "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        ;;
    80|443|8080|8443)
        echo "=== HTTP SERVICE CHECK ===" >> "$OUTPUT_FILE"
        PROTO="http"
        if [ "$PORT" = "443" ] || [ "$PORT" = "8443" ]; then
            PROTO="https"
        fi
        timeout 10 curl -s -I "$PROTO://$TARGET:$PORT/" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        ;;
    110|143|993|995)
        echo "=== MAIL SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 bash -c "echo 'A001 CAPABILITY' | nc $TARGET $PORT 2>/dev/null | head -5" >> "$OUTPUT_FILE" 2>&1
        ;;
    3306)
        echo "=== MYSQL SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 nmap -sV -p 3306 --script mysql-info "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        ;;
    5432)
        echo "=== POSTGRESQL SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 nmap -sV -p 5432 --script pgsql-info "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        ;;
    3389)
        echo "=== RDP SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 nmap -sV -p 3389 --script rdp-enum-encryption "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        ;;
    5900)
        echo "=== VNC SERVICE CHECK ===" >> "$OUTPUT_FILE"
        timeout 10 nmap -sV -p 5900 --script vnc-info "$TARGET" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
        ;;
esac

echo "" >> "$OUTPUT_FILE"

# 8. Geolocation information
echo "=== GEOLOCATION ===" >> "$OUTPUT_FILE"
timeout 10 curl -s "http://ip-api.com/json/$TARGET" 2>/dev/null | grep -E '"country"\|"city"\|"isp"\|"org"' >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 9. Port scan context
echo "=== PORT CONTEXT ===" >> "$OUTPUT_FILE"
case "$PORT" in
    21) echo "Port 21: FTP - File Transfer Protocol" >> "$OUTPUT_FILE" ;;
    22) echo "Port 22: SSH - Secure Shell" >> "$OUTPUT_FILE" ;;
    23) echo "Port 23: Telnet - Remote Terminal" >> "$OUTPUT_FILE" ;;
    25) echo "Port 25: SMTP - Mail Transfer" >> "$OUTPUT_FILE" ;;
    53) echo "Port 53: DNS - Domain Name System" >> "$OUTPUT_FILE" ;;
    80) echo "Port 80: HTTP - Web Server" >> "$OUTPUT_FILE" ;;
    110) echo "Port 110: POP3 - Mail Retrieval" >> "$OUTPUT_FILE" ;;
    143) echo "Port 143: IMAP - Mail Retrieval" >> "$OUTPUT_FILE" ;;
    443) echo "Port 443: HTTPS - Secure Web Server" >> "$OUTPUT_FILE" ;;
    993) echo "Port 993: IMAPS - Secure Mail Retrieval" >> "$OUTPUT_FILE" ;;
    995) echo "Port 995: POP3S - Secure Mail Retrieval" >> "$OUTPUT_FILE" ;;
    3306) echo "Port 3306: MySQL - Database" >> "$OUTPUT_FILE" ;;
    3389) echo "Port 3389: RDP - Remote Desktop" >> "$OUTPUT_FILE" ;;
    5432) echo "Port 5432: PostgreSQL - Database" >> "$OUTPUT_FILE" ;;
    5900) echo "Port 5900: VNC - Remote Desktop" >> "$OUTPUT_FILE" ;;
    8080) echo "Port 8080: HTTP-Alt - Alternative Web Server" >> "$OUTPUT_FILE" ;;
    8443) echo "Port 8443: HTTPS-Alt - Alternative Secure Web Server" >> "$OUTPUT_FILE" ;;
    *) echo "Port $PORT: Custom/Other Service" >> "$OUTPUT_FILE" ;;
esac

echo "" >> "$OUTPUT_FILE"
echo "=== NETWORK RECONNAISSANCE COMPLETED ===" >> "$OUTPUT_FILE"
echo "Scan finished at: $(date)" >> "$OUTPUT_FILE"