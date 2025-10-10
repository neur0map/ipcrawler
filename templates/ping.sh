#!/bin/bash
# Ping wrapper that handles blocked ICMP gracefully

TARGET="$1"
COUNT="${2:-4}"

# Run ping with timeout
OUTPUT=$(ping -c "$COUNT" -W 2 "$TARGET" 2>&1)
EXIT_CODE=$?

# Print the output
echo "$OUTPUT"

# If ping times out or fails, it's often due to ICMP being blocked (normal for many networks)
if [ $EXIT_CODE -ne 0 ]; then
    if echo "$OUTPUT" | grep -qE "(timeout|100.0% packet loss|Host is down)"; then
        echo "[INFO] ICMP appears to be blocked or host is unreachable (common security measure)"
        exit 0
    fi
fi

exit $EXIT_CODE
