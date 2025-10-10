#!/bin/bash
# Reverse DNS lookup wrapper that handles NXDOMAIN gracefully

TARGET="$1"

# Run host command and capture output and exit code
OUTPUT=$(host "$TARGET" 2>&1)
EXIT_CODE=$?

# Print the output regardless
echo "$OUTPUT"

# Exit 0 even if no PTR record exists (NXDOMAIN is valid information)
if [ $EXIT_CODE -eq 1 ] && echo "$OUTPUT" | grep -q "not found"; then
    echo "[INFO] No reverse DNS (PTR) record found for $TARGET"
    exit 0
fi

# For other errors, preserve the exit code
exit $EXIT_CODE
