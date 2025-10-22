#!/bin/bash
# Advanced web reconnaissance script
# Usage: web-recon.sh <target> <port> <output_file>

TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

if [ -z "$TARGET" ] || [ -z "$PORT" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <target> <port> <output_file>"
    exit 1
fi

PROTO="http"
if [ "$PORT" = "443" ] || [ "$PORT" = "8443" ]; then
    PROTO="https"
fi

BASE_URL="$PROTO://$TARGET:$PORT"

echo "=== WEB RECONNAISSANCE FOR $BASE_URL ===" > "$OUTPUT_FILE"
echo "Scan started at: $(date)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 1. HTTP headers analysis
echo "=== HTTP HEADERS ===" >> "$OUTPUT_FILE"
timeout 10 curl -s -I "$BASE_URL/" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 2. Server technology detection
echo "=== TECHNOLOGY DETECTION ===" >> "$OUTPUT_FILE"
timeout 15 whatweb --no-errors --log-scan="$OUTPUT_FILE.tmp" "$BASE_URL/" 2>/dev/null
if [ -f "$OUTPUT_FILE.tmp" ]; then
    cat "$OUTPUT_FILE.tmp" >> "$OUTPUT_FILE" 2>/dev/null
    rm -f "$OUTPUT_FILE.tmp"
fi
echo "" >> "$OUTPUT_FILE"

# 3. Robots.txt analysis
echo "=== ROBOTS.TXT ===" >> "$OUTPUT_FILE"
timeout 10 curl -s "$BASE_URL/robots.txt" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 4. Sitemap discovery
echo "=== SITEMAP DISCOVERY ===" >> "$OUTPUT_FILE"
timeout 10 curl -s "$BASE_URL/sitemap.xml" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
timeout 10 curl -s "$BASE_URL/sitemap_index.xml" 2>/dev/null >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# 5. Common files discovery
echo "=== COMMON FILES CHECK ===" >> "$OUTPUT_FILE"
COMMON_FILES=(
    "index.html"
    "index.php"
    "index.asp"
    "index.aspx"
    "index.jsp"
    "default.html"
    "home.html"
    "admin.php"
    "login.php"
    "config.php"
    "wp-config.php"
    ".htaccess"
    "web.config"
    "phpinfo.php"
    "test.php"
    "info.php"
    "backup.sql"
    "database.sql"
    "dump.sql"
)

for file in "${COMMON_FILES[@]}"; do
    status=$(timeout 5 curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/$file" 2>/dev/null)
    if [ "$status" = "200" ] || [ "$status" = "301" ] || [ "$status" = "302" ]; then
        echo "Found: $file (Status: $status)" >> "$OUTPUT_FILE"
    fi
done
echo "" >> "$OUTPUT_FILE"

# 6. Directory listing check
echo "=== DIRECTORY LISTING CHECK ===" >> "$OUTPUT_FILE"
COMMON_DIRS=(
    "admin"
    "backup"
    "config"
    "uploads"
    "images"
    "files"
    "documents"
    "logs"
    "tmp"
    "cache"
    "wp-admin"
    "wp-content"
    "phpmyadmin"
    "administrator"
)

for dir in "${COMMON_DIRS[@]}"; do
    status=$(timeout 5 curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/$dir/" 2>/dev/null)
    if [ "$status" = "200" ]; then
        # Check if directory listing is enabled
        listing=$(timeout 5 curl -s "$BASE_URL/$dir/" 2>/dev/null | grep -i "index of\|directory listing")
        if [ -n "$listing" ]; then
            echo "Directory listing enabled: $dir/" >> "$OUTPUT_FILE"
        fi
    fi
done
echo "" >> "$OUTPUT_FILE"

# 7. SSL/TLS analysis (if HTTPS)
if [ "$PROTO" = "https" ]; then
    echo "=== SSL/TLS ANALYSIS ===" >> "$OUTPUT_FILE"
    timeout 10 openssl s_client -connect "$TARGET:$PORT" -servername "$TARGET" 2>/dev/null | openssl x509 -noout -dates -subject -issuer -fingerprint -sha256 2>/dev/null >> "$OUTPUT_FILE" 2>&1
    echo "" >> "$OUTPUT_FILE"
fi

# 8. HTTP methods check
echo "=== HTTP METHODS ===" >> "$OUTPUT_FILE"
for method in GET POST PUT DELETE OPTIONS TRACE HEAD; do
    status=$(timeout 5 curl -s -o /dev/null -w "%{http_code}" -X "$method" "$BASE_URL/" 2>/dev/null)
    echo "$method: $status" >> "$OUTPUT_FILE"
done
echo "" >> "$OUTPUT_FILE"

# 9. Error page analysis
echo "=== ERROR PAGE ANALYSIS ===" >> "$OUTPUT_FILE"
timeout 10 curl -s "$BASE_URL/nonexistent-page-404.html" 2>/dev/null | head -20 >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

echo "=== WEB RECONNAISSANCE COMPLETED ===" >> "$OUTPUT_FILE"
echo "Scan finished at: $(date)" >> "$OUTPUT_FILE"