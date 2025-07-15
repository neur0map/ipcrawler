#!/usr/bin/env bash

echo "=== Testing IPCrawler sudo dependency access ==="
echo

echo "1. Current user Python:"
python3 --version
python3 -c "import httpx, dns.resolver; print('✓ Dependencies found')" 2>&1 || echo "✗ Dependencies missing"

echo
echo "2. Testing enhanced launcher (without sudo):"
../ipcrawler --help >/dev/null 2>&1 && echo "✓ Launcher works" || echo "✗ Launcher failed"

echo
echo "3. Testing with sudo (requires password):"
echo "Running: sudo ../ipcrawler --help"
sudo ../ipcrawler --help >/dev/null 2>&1 && echo "✓ Sudo execution works" || echo "✗ Sudo execution failed"

echo
echo "4. Python interpreter being used:"
echo "Without sudo:"
../ipcrawler --help 2>&1 | grep -E "Python interpreter being used|Warning:" | head -5

echo
echo "With sudo:"
sudo ../ipcrawler --help 2>&1 | grep -E "Python interpreter being used|Warning:" | head -5

echo
echo "=== Test complete ==="