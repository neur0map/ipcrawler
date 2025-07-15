#!/usr/bin/env bash

echo "=== IPCrawler Dependency Check ==="
echo

echo "1. User Python environment:"
python3 --version
echo "   httpx: $(python3 -c 'import httpx; print("INSTALLED")' 2>&1 || echo "NOT INSTALLED")"
echo "   dnspython: $(python3 -c 'import dns.resolver; print("INSTALLED")' 2>&1 || echo "NOT INSTALLED")"
echo

echo "2. System Python environment (requires sudo password):"
sudo python3 --version 2>/dev/null || echo "   Could not check sudo Python"
echo "   httpx: $(sudo python3 -c 'import httpx; print("INSTALLED")' 2>&1 || echo "NOT INSTALLED")"
echo "   dnspython: $(sudo python3 -c 'import dns.resolver; print("INSTALLED")' 2>&1 || echo "NOT INSTALLED")"
echo

echo "3. Python paths:"
echo "   User python3: $(which python3)"
echo "   User pip3: $(which pip3)"
echo "   Sudo python3: $(sudo which python3 2>/dev/null || echo "Not found")"
echo "   Sudo pip3: $(sudo which pip3 2>/dev/null || echo "Not found")"
echo

echo "4. Suggestions:"
if ! sudo python3 -c 'import httpx' 2>/dev/null; then
    echo "   To install for sudo, try one of these:"
    echo "   - sudo pip3 install httpx dnspython"
    echo "   - sudo python3 -m pip install httpx dnspython"
    echo "   - sudo $(which pip3) install httpx dnspython"
fi