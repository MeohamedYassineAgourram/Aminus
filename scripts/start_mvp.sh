#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/.runtime"

mkdir -p "$RUNTIME_DIR"

# ── Resolve backend Python (prefer .venv to avoid PEP 668 system-Python issues) ──
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Creating backend virtual environment..."
  python3 -m venv "$BACKEND_DIR/.venv"
fi
BACKEND_PYTHON="$VENV_PYTHON"

# ── Backend deps: only reinstall if requirements.txt changed ──
REQ_HASH_FILE="$RUNTIME_DIR/requirements.md5"
REQ_HASH_NOW=$(md5 -q "$BACKEND_DIR/requirements.txt" 2>/dev/null || md5sum "$BACKEND_DIR/requirements.txt" | cut -d' ' -f1)
if [[ ! -f "$REQ_HASH_FILE" ]] || [[ "$(cat "$REQ_HASH_FILE")" != "$REQ_HASH_NOW" ]]; then
  echo "Installing backend dependencies..."
  "$BACKEND_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt" >/dev/null
  echo "$REQ_HASH_NOW" > "$REQ_HASH_FILE"
else
  echo "Backend dependencies up to date, skipping."
fi

# ── Frontend deps: only reinstall if package-lock.json changed ──
PKG_HASH_FILE="$RUNTIME_DIR/package-lock.md5"
PKG_HASH_NOW=$(md5 -q "$FRONTEND_DIR/package-lock.json" 2>/dev/null || md5sum "$FRONTEND_DIR/package-lock.json" | cut -d' ' -f1)
if [[ ! -f "$PKG_HASH_FILE" ]] || [[ "$(cat "$PKG_HASH_FILE")" != "$PKG_HASH_NOW" ]]; then
  echo "Installing frontend dependencies..."
  npm --prefix "$FRONTEND_DIR" install >/dev/null
  echo "$PKG_HASH_NOW" > "$PKG_HASH_FILE"
else
  echo "Frontend dependencies up to date, skipping."
fi

# ── Frontend build: only rebuild if source files changed ──
SRC_HASH_FILE="$RUNTIME_DIR/src.md5"
SRC_HASH_NOW=$(find "$FRONTEND_DIR/app" "$FRONTEND_DIR/src" "$FRONTEND_DIR/utils" -type f 2>/dev/null | sort | xargs md5 -q 2>/dev/null || find "$FRONTEND_DIR/app" "$FRONTEND_DIR/src" "$FRONTEND_DIR/utils" -type f 2>/dev/null | sort | xargs md5sum | md5sum | cut -d' ' -f1)
if [[ ! -f "$SRC_HASH_FILE" ]] || [[ "$(cat "$SRC_HASH_FILE")" != "$SRC_HASH_NOW" ]] || [[ ! -f "$FRONTEND_DIR/.next/BUILD_ID" ]]; then
  echo "Building frontend..."
  npm --prefix "$FRONTEND_DIR" run build >/dev/null
  echo "$SRC_HASH_NOW" > "$SRC_HASH_FILE"
else
  echo "Frontend build up to date, skipping."
fi

# ── Stop previous processes ──
echo "Stopping previous MVP processes (if any)..."
if [[ -f "$RUNTIME_DIR/backend.pid" ]]; then
  kill "$(cat "$RUNTIME_DIR/backend.pid")" 2>/dev/null || true
fi
if [[ -f "$RUNTIME_DIR/frontend.pid" ]]; then
  kill "$(cat "$RUNTIME_DIR/frontend.pid")" 2>/dev/null || true
fi

lsof -tiTCP:8000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
lsof -tiTCP:3000 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true

# ── Start servers ──
echo "Starting backend on :8000..."
nohup "$BACKEND_PYTHON" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
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
