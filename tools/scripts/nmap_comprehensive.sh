#!/bin/bash
# Comprehensive multi-phase nmap scan with JSON output
# Usage: nmap_comprehensive.sh <target> <ports> <output_file>

TARGET="$1"
PORTS="$2"
OUTPUT_FILE="$3"

if [ -z "$TARGET" ] || [ -z "$PORTS" ]; then
    echo "Usage: $0 <target> <ports> [output_file]"
    exit 1
fi

# Initialize findings array
findings_json="[]"

# Temporary files for storing results
QUICK_SCAN=$(mktemp)
SERVICE_SCAN=$(mktemp)
SCRIPT_SCAN=$(mktemp)

# Cleanup function
cleanup() {
    rm -f "$QUICK_SCAN" "$SERVICE_SCAN" "$SCRIPT_SCAN"
}
trap cleanup EXIT

echo "===START_RAW_OUTPUT===" >&2
echo "=== COMPREHENSIVE NMAP SCAN FOR $TARGET ===" >&2
echo "Scan started at: $(date)" >&2
echo "" >&2

# Phase 1: Quick SYN scan to discover open ports
echo "=== Phase 1: Port Discovery ===" >&2
if timeout 300 nmap -sS -T4 --open "$TARGET" -p "$PORTS" -oG "$QUICK_SCAN" 2>&1 >&2; then
    open_ports=$(grep -oP '\d+/open' "$QUICK_SCAN" | cut -d/ -f1 | tr '\n' ',' | sed 's/,$//')

    if [ -n "$open_ports" ]; then
        echo "Open ports found: $open_ports" >&2

        # Create JSON findings for open ports
        port_findings=$(echo "$open_ports" | tr ',' '\n' | while read -r port; do
            [ -z "$port" ] && continue
            cat <<EOF
{
  "severity": "info",
  "title": "Open port discovered",
  "description": "Port $port is open",
  "port": $port
}
EOF
        done | jq -s .)

        findings_json=$(echo "$findings_json" | jq --argjson new "$port_findings" '. + $new')
    else
        echo "No open ports found in quick scan" >&2
        open_ports="$PORTS"
    fi
else
    echo "Quick scan failed or timed out, using specified ports" >&2
    open_ports="$PORTS"
fi
echo "" >&2

# Phase 2: Service and version detection
if [ -n "$open_ports" ]; then
    echo "=== Phase 2: Service Detection ===" >&2
    if timeout 600 nmap -sV -sC -T4 "$TARGET" -p "$open_ports" -oX "$SERVICE_SCAN" 2>&1 >&2; then

        # Parse XML output for services
        if command -v xmllint &> /dev/null && [ -s "$SERVICE_SCAN" ]; then
            # Extract service information from XML
            service_findings=$(xmllint --xpath "//port[@protocol='tcp']" "$SERVICE_SCAN" 2>/dev/null | \
                grep -oP '(<port protocol="tcp" portid="\d+">.*?</port>)' | while read -r port_xml; do

                port_num=$(echo "$port_xml" | grep -oP 'portid="\K\d+')
                service=$(echo "$port_xml" | grep -oP '<service name="\K[^"]+' || echo "unknown")
                product=$(echo "$port_xml" | grep -oP 'product="\K[^"]+' || echo "")
                version=$(echo "$port_xml" | grep -oP 'version="\K[^"]+' || echo "")

                # Build description
                desc="$port_num | tcp | $service"
                [ -n "$product" ] && desc="$desc | $product"
                [ -n "$version" ] && desc="$desc $version"

                # Determine severity based on service
                severity="info"
                case "$service" in
                    ftp|telnet|rsh|rlogin)
                        severity="high"
                        desc="$desc | INSECURE: Unencrypted protocol"
                        ;;
                    ssh|http|https|smtp|mysql|postgresql)
                        severity="medium"
                        ;;
                esac

                cat <<EOF
{
  "severity": "$severity",
  "title": "Service: $service on port $port_num",
  "description": "$desc",
  "port": $port_num
}
EOF
            done | jq -s .)

            if [ -n "$service_findings" ] && [ "$service_findings" != "[]" ]; then
                findings_json=$(echo "$findings_json" | jq --argjson new "$service_findings" '. + $new')
            fi
        fi

        # Display service scan output
        cat "$SERVICE_SCAN" >&2
    else
        echo "Service detection failed or timed out" >&2
    fi
fi
echo "" >&2

# Phase 3: OS Detection and aggressive scans (if running as root)
if [ "$(id -u)" -eq 0 ] && [ -n "$open_ports" ]; then
    echo "=== Phase 3: OS Detection & Advanced Scans ===" >&2
    if timeout 600 nmap -O -A --osscan-guess --version-intensity 9 "$TARGET" -p "$open_ports" 2>&1 >&2; then
        echo "OS detection completed" >&2
    else
        echo "OS detection failed or timed out" >&2
    fi
fi
echo "" >&2

echo "=== SCAN COMPLETED ===" >&2
echo "Scan finished at: $(date)" >&2
echo "===END_RAW_OUTPUT===" >&2

# Output JSON findings to stdout
cat <<EOF
{
  "findings": $findings_json,
  "metadata": {
    "scan_type": "comprehensive",
    "target": "$TARGET",
    "ports_scanned": "$PORTS",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
