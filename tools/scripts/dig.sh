#!/bin/bash
# Comprehensive DNS reconnaissance script
# Usage: dig.sh <target> <port> <output_file>
# Note: port parameter is ignored for DNS queries but required for TUI compatibility

TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

if [ -z "$TARGET" ]; then
    echo "Usage: $0 <target> [port] [output_file]"
    exit 1
fi

# Write markers and output to stderr for proper parsing
echo "===START_RAW_OUTPUT===" >&2
echo "=== COMPREHENSIVE DNS RECONNAISSANCE FOR $TARGET ===" >&2
echo "Scan started at: $(date)" >&2
echo "" >&2

# Initialize findings JSON array
findings_json="[]"

# Function to run dig and handle errors
run_dig() {
    local query_type="$1"
    local target="$2"
    local description="$3"

    echo "=== $description ===" >&2
    output=$(timeout 10 dig "$target" "$query_type" +noall +answer +additional 2>/dev/null || echo "Query failed or timed out")
    echo "$output" >&2
    echo "" >&2

    # Parse output for findings
    if [ -n "$output" ] && ! echo "$output" | grep -q "Query failed"; then
        # Count records found
        record_count=$(echo "$output" | grep -c "^$target" || echo "0")
        if [ "$record_count" -gt 0 ]; then
            finding=$(cat <<EOF
{
  "severity": "info",
  "title": "$query_type records found",
  "description": "Found $record_count $query_type record(s) for $target"
}
EOF
)
            findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new')
        fi
    fi
}

# 1. A Records (IPv4 addresses)
run_dig "A" "$TARGET" "A RECORDS (IPv4)"

# 2. AAAA Records (IPv6 addresses)
run_dig "AAAA" "$TARGET" "AAAA RECORDS (IPv6)"

# 3. MX Records (Mail servers)
run_dig "MX" "$TARGET" "MX RECORDS (Mail Servers)"

# 4. NS Records (Name servers)
run_dig "NS" "$TARGET" "NS RECORDS (Name Servers)"

# 5. TXT Records (Text records - SPF, DKIM, DMARC, etc.)
run_dig "TXT" "$TARGET" "TXT RECORDS (SPF, DKIM, DMARC, Verification)"

# 6. SOA Record (Start of Authority)
run_dig "SOA" "$TARGET" "SOA RECORD (Start of Authority)"

# 7. CNAME Records
run_dig "CNAME" "$TARGET" "CNAME RECORDS (Canonical Names)"

# 8. SRV Records (Service records)
run_dig "SRV" "$TARGET" "SRV RECORDS (Service Records)"

# 9. CAA Records (Certificate Authority Authorization)
run_dig "CAA" "$TARGET" "CAA RECORDS (Certificate Authority Authorization)"

# 10. PTR Records (Reverse DNS - only if target is an IP)
if [[ "$TARGET" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "=== PTR RECORD (Reverse DNS) ===" >&2
    ptr_result=$(timeout 10 dig -x "$TARGET" +short 2>/dev/null || echo "Reverse DNS lookup failed")
    echo "$ptr_result" >&2
    echo "" >&2

    if [ -n "$ptr_result" ] && ! echo "$ptr_result" | grep -q "failed"; then
        finding=$(cat <<EOF
{
  "severity": "info",
  "title": "Reverse DNS found",
  "description": "PTR record: $ptr_result"
}
EOF
)
        findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new')
    fi
fi

# 11. ANY query (comprehensive)
echo "=== ANY QUERY (All Available Records) ===" >&2
timeout 15 dig "$TARGET" ANY +noall +answer +authority +additional 2>&1 >&2 || echo "ANY query failed or timed out" >&2
echo "" >&2

# 12. Common subdomain enumeration
echo "=== COMMON SUBDOMAIN CHECKS ===" >&2
COMMON_SUBDOMAINS=("www" "mail" "ftp" "smtp" "pop" "imap" "webmail" "admin" "portal" "vpn" "remote" "api" "dev" "test" "staging")

subdomain_count=0
for subdomain in "${COMMON_SUBDOMAINS[@]}"; do
    result=$(timeout 3 dig "${subdomain}.${TARGET}" A +short 2>/dev/null)
    if [ -n "$result" ]; then
        echo "${subdomain}.${TARGET}: $result" >&2
        ((subdomain_count++))
    fi
done

if [ "$subdomain_count" -gt 0 ]; then
    finding=$(cat <<EOF
{
  "severity": "info",
  "title": "Subdomains discovered",
  "description": "Found $subdomain_count subdomain(s)"
}
EOF
)
    findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new')
fi
echo "" >&2

# 13. DNS Server Information
echo "=== DNS SERVER INFORMATION ===" >&2
echo "Authoritative nameservers:" >&2
timeout 10 dig "$TARGET" NS +short 2>&1 >&2
echo "" >&2

# 14. DNSSEC Validation
echo "=== DNSSEC VALIDATION ===" >&2
timeout 10 dig "$TARGET" +dnssec +short 2>&1 >&2 || echo "DNSSEC not available or validation failed" >&2
echo "" >&2

# 15. DNS Trace
echo "=== DNS TRACE (Query Path) ===" >&2
timeout 15 dig "$TARGET" +trace +nodnssec 2>/dev/null | grep -E "^(;|[a-zA-Z0-9])" | head -20 >&2
echo "" >&2

# 16. Zone Transfer Attempt (ethical pentesting)
echo "=== ZONE TRANSFER ATTEMPT ===" >&2
nameservers=$(dig "$TARGET" NS +short 2>/dev/null)
zone_transfer_found=false
if [ -n "$nameservers" ]; then
    for ns in $nameservers; do
        echo "Attempting zone transfer from $ns..." >&2
        zt_result=$(timeout 10 dig "@$ns" "$TARGET" AXFR 2>/dev/null | head -20)
        echo "$zt_result" >&2
        echo "" >&2

        if echo "$zt_result" | grep -q "XFR size"; then
            zone_transfer_found=true
        fi
    done

    if [ "$zone_transfer_found" = true ]; then
        finding=$(cat <<EOF
{
  "severity": "high",
  "title": "Zone transfer allowed",
  "description": "DNS zone transfer (AXFR) is allowed - security risk"
}
EOF
)
        findings_json=$(echo "$findings_json" | jq --argjson new "[$finding]" '. + $new')
    fi
else
    echo "No nameservers found for zone transfer attempt" >&2
fi
echo "" >&2

# 17. Reverse DNS for resolved IPs
echo "=== REVERSE DNS FOR RESOLVED IPS ===" >&2
ips=$(dig "$TARGET" A +short 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')
if [ -n "$ips" ]; then
    for ip in $ips; do
        hostname=$(dig -x "$ip" +short 2>/dev/null)
        if [ -n "$hostname" ]; then
            echo "$ip -> $hostname" >&2
        else
            echo "$ip -> No PTR record" >&2
        fi
    done
else
    echo "No A records found to reverse lookup" >&2
fi
echo "" >&2

echo "=== DNS RECONNAISSANCE COMPLETED ===" >&2
echo "Scan finished at: $(date)" >&2
echo "===END_RAW_OUTPUT===" >&2

# Output JSON findings to stdout
cat <<EOF
{
  "findings": $findings_json,
  "metadata": {
    "scan_type": "dns_reconnaissance",
    "target": "$TARGET",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
