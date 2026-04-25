#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"

if [[ -f "$RUNTIME_DIR/backend.pid" ]]; then
  kill "$(cat "$RUNTIME_DIR/backend.pid")" 2>/dev/null || true
  rm -f "$RUNTIME_DIR/backend.pid"
fi

if [[ -f "$RUNTIME_DIR/frontend.pid" ]]; then
  kill "$(cat "$RUNTIME_DIR/frontend.pid")" 2>/dev/null || true
  rm -f "$RUNTIME_DIR/frontend.pid"
fi

lsof -tiTCP:8000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
lsof -tiTCP:3000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true

echo "MVP stopped."
