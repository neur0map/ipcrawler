#!/usr/bin/env bash
set -euo pipefail

ok()  { printf "✔ %s\n" "$1"; }
bad() { printf "✘ %s\n" "$1"; }

missing=0

need() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1 $( "$1" --version 2>&1 | head -n1 )"
  else
    bad "$1 not found"
    missing=1
  fi
}

echo "Checking external tools..."
need nmap
need curl

if [[ $missing -ne 0 ]]; then
  echo "fatal: missing dependencies. Run: make tools" >&2
  exit 1
fi