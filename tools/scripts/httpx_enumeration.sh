#!/bin/bash
# Comprehensive HTTP(S) enumeration with technology detection
# Usage: httpx_enumeration.sh <target> <port> <output_file>

TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

if [ -z "$TARGET" ]; then
    echo "Usage: $0 <target> [port] [output_file]"
    exit 1
fi

# Check if this is a web port - if not, exit early with info finding
WEB_PORTS="80,443,8080,8443,8000,8888,3000,5000,9000,9090"
if [[ -n "$PORT" ]] && [[ "$PORT" != "none" ]]; then
    if ! echo "$WEB_PORTS" | grep -q "\b$PORT\b"; then
        # Not a web port, create info finding and exit
        cat <<EOF
{
  "findings": [
    {
      "severity": "info",
      "title": "Non-web port skipped",
      "description": "Port $PORT is not a common web port, skipping HTTP enumeration",
      "port": $PORT
    }
  ],
  "metadata": {
    "scan_type": "http_enumeration",
    "target": "$TARGET",
    "url": "http://$TARGET:$PORT",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
        exit 0
    fi
fi

# Build target URL
if [ -n "$PORT" ] && [ "$PORT" != "none" ]; then
    if [ "$PORT" = "443" ] || [ "$PORT" = "8443" ]; then
        URL="https://$TARGET:$PORT"
    else
        URL="http://$TARGET:$PORT"
    fi
else
    URL="http://$TARGET"
fi

# Initialize findings array
findings_json="[]"

# Temporary files
HTTPX_OUTPUT=$(mktemp)
TECH_OUTPUT=$(mktemp)

cleanup() {
    rm -f "$HTTPX_OUTPUT" "$TECH_OUTPUT"
}
trap cleanup EXIT

echo "===START_RAW_OUTPUT===" >&2
echo "=== HTTP(S) ENUMERATION FOR $URL ===" >&2
echo "Scan started at: $(date)" >&2
echo "" >&2

# Phase 1: Basic HTTP probing with httpx
echo "=== Phase 1: HTTP Probing ===" >&2
if timeout 120 httpx -u "$URL" -json -status-code -title -content-length \
    -server -tech-detect -ip -cname -location -response-time \
    -websocket -favicon -hash sha256 -cdn -method -tls-grab -probe \
    -no-fallback -threads 10 -timeout 30 -retries 2 -silent > "$HTTPX_OUTPUT" 2>&1; then

    # Display raw httpx output
    cat "$HTTPX_OUTPUT" >&2

    # Parse httpx JSON output
    if [ -s "$HTTPX_OUTPUT" ]; then
        # Get the first valid JSON line from httpx output
        first_json=$(head -n1 "$HTTPX_OUTPUT" 2>/dev/null)
        
        if [ -n "$first_json" ] && echo "$first_json" | jq . >/dev/null 2>&1; then
            # Check if httpx returned successful response or error
            failed_check=$(echo "$first_json" | jq -r '.failed // false' 2>/dev/null)
            error_msg=$(echo "$first_json" | jq -r '.error // ""' 2>/dev/null)
            
            if [ "$failed_check" = "true" ] || [ -n "$error_msg" ]; then
                # Create finding for failed HTTP connection
                error_finding=$(cat <<EOF
{
  "severity": "info",
  "title": "HTTP service not responding",
  "description": "Connection failed: ${error_msg:-Unknown error}",
  "port": ${PORT:-80}
}
EOF
)
            findings_json=$(echo "$findings_json" | jq --argjson new "[$error_finding]" '. + $new' 2>/dev/null || echo "$findings_json" | jq '. + [{"severity": "info", "title": "HTTP service not responding", "description": "Connection failed", "port": '${PORT:-80}'}]')
            else
                # Parse successful response
                status_code=$(echo "$first_json" | jq -r '.status_code // "unknown"' 2>/dev/null)
                title=$(echo "$first_json" | jq -r '.title // ""' 2>/dev/null)
                server=$(echo "$first_json" | jq -r '.webserver // ""' 2>/dev/null)
                technologies=$(echo "$first_json" | jq -r '.tech[]? // ""' 2>/dev/null | tr '\n' ',' | sed 's/,$//')

                # Create finding for HTTP response
                response_finding=$(cat <<EOF
{
  "severity": "info",
  "title": "HTTP service responsive",
  "description": "Status: $status_code | Title: $title | Server: $server",
  "port": ${PORT:-80}
}
EOF
)
                findings_json=$(echo "$findings_json" | jq --argjson new "[$response_finding]" '. + $new' 2>/dev/null || echo "$findings_json")

                # Technology findings
                if [ -n "$technologies" ]; then
                    tech_finding=$(cat <<EOF
{
  "severity": "info",
  "title": "Technologies detected",
  "description": "Technologies: $technologies",
  "port": ${PORT:-80}
}
EOF
)
                    findings_json=$(echo "$findings_json" | jq --argjson new "[$tech_finding]" '. + $new' 2>/dev/null || echo "$findings_json")
                fi
            fi
        else
            # No valid JSON found, create a generic finding
            error_finding=$(cat <<EOF
{
  "severity": "info",
  "title": "HTTP service check completed",
  "description": "No HTTP service detected on port ${PORT:-80}",
  "port": ${PORT:-80}
}
EOF
)
            findings_json=$(echo "$findings_json" | jq --argjson new "[$error_finding]" '. + $new' 2>/dev/null || echo "$findings_json")
        fi
    fi
else
    echo "HTTP probing failed or timed out" >&2
fi
echo "" >&2

# Phase 2: robots.txt and sitemap.xml check
echo "=== Phase 2: Discovery Files ===" >&2
for path in robots.txt sitemap.xml; do
    response=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" "${URL}/${path}" 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "Found: /${path}" >&2
        finding=$(cat <<EOF
{
  "severity": "info",
  "title": "Discovery file found",
  "description": "Found /${path} (HTTP $response)",
  "port": ${PORT:-80}
}
EOF
)
        findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new' 2>/dev/null || echo "$findings_json")
    fi
done
echo "" >&2

# Phase 3: Common security headers check
echo "=== Phase 3: Security Headers ===" >&2
headers=$(timeout 10 curl -s -I "$URL" 2>/dev/null)
missing_headers=""

for header in "Strict-Transport-Security" "Content-Security-Policy" "X-Frame-Options" "X-Content-Type-Options"; do
    if ! echo "$headers" | grep -qi "^$header:"; then
        missing_headers="${missing_headers}${header}, "
    fi
done

if [ -n "$missing_headers" ]; then
    missing_headers=$(echo "$missing_headers" | sed 's/, $//')
    echo "Missing security headers: $missing_headers" >&2
    finding=$(cat <<EOF
{
  "severity": "medium",
  "title": "Missing security headers",
  "description": "Missing headers: $missing_headers",
  "port": ${PORT:-80}
}
EOF
)
    findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new' 2>/dev/null || echo "$findings_json")
else
    echo "All common security headers present" >&2
fi
echo "" >&2

# Phase 4: TLS/SSL certificate analysis (for HTTPS)
if [[ "$URL" == https://* ]]; then
    echo "=== Phase 4: TLS Certificate Analysis ===" >&2
    cert_info=$(timeout 10 echo | openssl s_client -connect "${TARGET}:${PORT:-443}" -servername "$TARGET" 2>/dev/null | \
        openssl x509 -noout -subject -issuer -dates 2>/dev/null)

    if [ -n "$cert_info" ]; then
        echo "$cert_info" >&2

        # Check certificate expiry
        expiry=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
        if [ -n "$expiry" ]; then
            expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo "0")
            now_epoch=$(date +%s)
            days_until_expiry=$(( (expiry_epoch - now_epoch) / 86400 ))

            if [ "$days_until_expiry" -lt 30 ] && [ "$days_until_expiry" -gt 0 ]; then
                finding=$(cat <<EOF
{
  "severity": "medium",
  "title": "TLS certificate expiring soon",
  "description": "Certificate expires in $days_until_expiry days",
  "port": ${PORT:-443}
}
EOF
)
                findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new' 2>/dev/null || echo "$findings_json")
            elif [ "$days_until_expiry" -le 0 ]; then
                finding=$(cat <<EOF
{
  "severity": "high",
  "title": "TLS certificate expired",
  "description": "Certificate expired $((- days_until_expiry)) days ago",
  "port": ${PORT:-443}
}
EOF
)
                findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new' 2>/dev/null || echo "$findings_json")
            fi
        fi
    else
        echo "Could not retrieve TLS certificate information" >&2
    fi
fi
echo "" >&2

echo "=== ENUMERATION COMPLETED ===" >&2
echo "Scan finished at: $(date)" >&2
echo "===END_RAW_OUTPUT===" >&2

# Output JSON findings to stdout
cat <<EOF
{
  "findings": $findings_json,
  "metadata": {
    "scan_type": "http_enumeration",
    "target": "$TARGET",
    "url": "$URL",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
