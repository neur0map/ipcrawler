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

echo "=== COMPREHENSIVE DNS RECONNAISSANCE FOR $TARGET ==="
echo "Scan started at: $(date)"
echo ""

# Function to run dig and handle errors
run_dig() {
    local query_type="$1"
    local target="$2"
    local description="$3"

    echo "=== $description ==="
    timeout 10 dig "$target" "$query_type" +noall +answer +additional 2>/dev/null || echo "Query failed or timed out"
    echo ""
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
    echo "=== PTR RECORD (Reverse DNS) ==="
    timeout 10 dig -x "$TARGET" +short 2>/dev/null || echo "Reverse DNS lookup failed"
    echo ""
fi

# 11. ANY query (comprehensive)
echo "=== ANY QUERY (All Available Records) ==="
timeout 15 dig "$TARGET" ANY +noall +answer +authority +additional 2>/dev/null || echo "ANY query failed or timed out"
echo ""

# 12. Common subdomain enumeration
echo "=== COMMON SUBDOMAIN CHECKS ==="
COMMON_SUBDOMAINS=("www" "mail" "ftp" "smtp" "pop" "imap" "webmail" "admin" "portal" "vpn" "remote" "api" "dev" "test" "staging")

for subdomain in "${COMMON_SUBDOMAINS[@]}"; do
    result=$(timeout 3 dig "${subdomain}.${TARGET}" A +short 2>/dev/null)
    if [ -n "$result" ]; then
        echo "${subdomain}.${TARGET}: $result"
    fi
done
echo ""

# 13. DNS Server Information
echo "=== DNS SERVER INFORMATION ==="
echo "Authoritative nameservers:"
timeout 10 dig "$TARGET" NS +short 2>/dev/null
echo ""

# 14. DNSSEC Validation
echo "=== DNSSEC VALIDATION ==="
timeout 10 dig "$TARGET" +dnssec +short 2>/dev/null || echo "DNSSEC not available or validation failed"
echo ""

# 15. DNS Trace
echo "=== DNS TRACE (Query Path) ==="
timeout 15 dig "$TARGET" +trace +nodnssec 2>/dev/null | grep -E "^(;|[a-zA-Z0-9])" | head -20
echo ""

# 16. Zone Transfer Attempt (ethical pentesting)
echo "=== ZONE TRANSFER ATTEMPT ==="
nameservers=$(dig "$TARGET" NS +short 2>/dev/null)
if [ -n "$nameservers" ]; then
    for ns in $nameservers; do
        echo "Attempting zone transfer from $ns..."
        timeout 10 dig "@$ns" "$TARGET" AXFR 2>/dev/null | head -20
        echo ""
    done
else
    echo "No nameservers found for zone transfer attempt"
fi
echo ""

# 17. Reverse DNS for resolved IPs
echo "=== REVERSE DNS FOR RESOLVED IPS ==="
ips=$(dig "$TARGET" A +short 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')
if [ -n "$ips" ]; then
    for ip in $ips; do
        hostname=$(dig -x "$ip" +short 2>/dev/null)
        if [ -n "$hostname" ]; then
            echo "$ip -> $hostname"
        else
            echo "$ip -> No PTR record"
        fi
    done
else
    echo "No A records found to reverse lookup"
fi
echo ""

echo "=== DNS RECONNAISSANCE COMPLETED ==="
echo "Scan finished at: $(date)"
