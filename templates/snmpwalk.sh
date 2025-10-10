#!/bin/bash
# SNMP enumeration with common community strings

TARGET="$1"
OUTPUT_FILE="$2"

# Try common community strings
for community in public private manager; do
    echo "=== Testing community string: $community ===" >> "$OUTPUT_FILE"
    timeout 30 snmpwalk -v 2c -c "$community" "$TARGET" 2>&1 >> "$OUTPUT_FILE" || true
    
    # If SNMP is not responding, no point trying other strings
    if grep -q "Timeout: No Response" "$OUTPUT_FILE"; then
        echo "[INFO] SNMP not responding on $TARGET" >> "$OUTPUT_FILE"
        exit 0
    fi
done

exit 0
