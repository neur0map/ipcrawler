#!/bin/bash
# Example advanced scan script for IPCrawler
# This demonstrates how to create custom scanning scripts
# Available variables: $1=target, $2=port, $3=output_file

TARGET="$1"
PORT="$2"
OUTPUT_FILE="$3"

echo "Starting advanced scan on $TARGET:$PORT"
echo "Output will be saved to: $OUTPUT_FILE"

# Example: Combine multiple tools in a single script
{
    echo "=== Advanced Scan Results ==="
    echo "Target: $TARGET"
    echo "Port: $PORT"
    echo "Timestamp: $(date)"
    echo ""

    # Example: Banner grab
    echo "=== Banner Grab ==="
    timeout 5 nc -v -n "$TARGET" "$PORT" 2>&1 || echo "Banner grab failed or timed out"
    echo ""

    # Example: SSL/TLS check if port is 443
    if [ "$PORT" = "443" ]; then
        echo "=== SSL/TLS Information ==="
        echo | timeout 5 openssl s_client -connect "$TARGET:$PORT" 2>/dev/null | \
            grep -E "(subject=|issuer=|Protocol|Cipher)" || echo "SSL check failed"
        echo ""
    fi

    # Example: HTTP header check
    if [ "$PORT" = "80" ] || [ "$PORT" = "8080" ]; then
        echo "=== HTTP Headers ==="
        timeout 5 curl -I "http://$TARGET:$PORT" 2>/dev/null || echo "HTTP check failed"
        echo ""
    fi

    echo "=== Scan Complete ==="
} > "$OUTPUT_FILE" 2>&1

echo "Scan completed. Results saved to $OUTPUT_FILE"
exit 0
