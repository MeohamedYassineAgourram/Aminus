#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/.runtime"

mkdir -p "$RUNTIME_DIR"

echo "Installing backend dependencies..."
python3 -m pip install -r "$BACKEND_DIR/requirements.txt" >/dev/null

echo "Installing frontend dependencies..."
npm --prefix "$FRONTEND_DIR" install >/dev/null

echo "Building frontend..."
npm --prefix "$FRONTEND_DIR" run build >/dev/null

echo "Stopping previous MVP processes (if any)..."
if [[ -f "$RUNTIME_DIR/backend.pid" ]]; then
  kill "$(cat "$RUNTIME_DIR/backend.pid")" 2>/dev/null || true
fi
if [[ -f "$RUNTIME_DIR/frontend.pid" ]]; then
  kill "$(cat "$RUNTIME_DIR/frontend.pid")" 2>/dev/null || true
fi

lsof -tiTCP:8000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
lsof -tiTCP:3000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true

echo "Starting backend on :8000..."
nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
  >"$RUNTIME_DIR/backend.log" 2>&1 &
echo $! >"$RUNTIME_DIR/backend.pid"

echo "Starting frontend on :3000..."
nohup npm --prefix "$FRONTEND_DIR" run start -- --hostname 127.0.0.1 --port 3000 \
  >"$RUNTIME_DIR/frontend.log" 2>&1 &
echo $! >"$RUNTIME_DIR/frontend.pid"

sleep 2

echo
echo "MVP started."
echo "Frontend: http://127.0.0.1:3000"
echo "Backend:  http://127.0.0.1:8000/health"
echo "Logs:     $RUNTIME_DIR/backend.log and $RUNTIME_DIR/frontend.log"
