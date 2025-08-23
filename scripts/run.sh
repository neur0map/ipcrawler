#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/artifacts/bin/ipcrawler"

if [[ ! -x "$BIN" ]]; then
  echo "Binary not found at $BIN. Run 'make build' first." >&2
  exit 1
fi

export RUST_LOG="${RUST_LOG:-info}"

exec "$BIN" "$@"