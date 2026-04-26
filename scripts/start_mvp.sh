#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/.runtime"

mkdir -p "$RUNTIME_DIR"

# ── Resolve backend Python (Windows uses Scripts/, Unix uses bin/) ──
if [[ -x "$BACKEND_DIR/.venv/Scripts/python" ]]; then
  BACKEND_PYTHON="$BACKEND_DIR/.venv/Scripts/python"
elif [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
else
  echo "Creating backend virtual environment..."
  python3 -m venv "$BACKEND_DIR/.venv"
  if [[ -x "$BACKEND_DIR/.venv/Scripts/python" ]]; then
    BACKEND_PYTHON="$BACKEND_DIR/.venv/Scripts/python"
  else
    BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
  fi
fi

# ── Backend deps: only reinstall if requirements.txt changed ──
REQ_HASH_FILE="$RUNTIME_DIR/requirements.md5"
REQ_HASH_NOW=$(md5sum "$BACKEND_DIR/requirements.txt" 2>/dev/null | cut -d' ' -f1 || echo "unknown")
if [[ ! -f "$REQ_HASH_FILE" ]] || [[ "$(cat "$REQ_HASH_FILE")" != "$REQ_HASH_NOW" ]]; then
  echo "Installing backend dependencies..."
  "$BACKEND_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt" >/dev/null
  echo "$REQ_HASH_NOW" > "$REQ_HASH_FILE"
else
  echo "Backend dependencies up to date, skipping."
fi

# ── Frontend deps: only reinstall if package-lock.json changed ──
PKG_HASH_FILE="$RUNTIME_DIR/package-lock.md5"
PKG_HASH_NOW=$(md5sum "$FRONTEND_DIR/package-lock.json" 2>/dev/null | cut -d' ' -f1 || echo "unknown")
if [[ ! -f "$PKG_HASH_FILE" ]] || [[ "$(cat "$PKG_HASH_FILE")" != "$PKG_HASH_NOW" ]]; then
  echo "Installing frontend dependencies..."
  npm --prefix "$FRONTEND_DIR" install >/dev/null
  echo "$PKG_HASH_NOW" > "$PKG_HASH_FILE"
else
  echo "Frontend dependencies up to date, skipping."
fi

# ── Stop previous processes ──
echo "Stopping previous MVP processes (if any)..."
if [[ -f "$RUNTIME_DIR/backend.pid" ]]; then
  kill "$(cat "$RUNTIME_DIR/backend.pid")" 2>/dev/null || true
  rm -f "$RUNTIME_DIR/backend.pid"
fi
if [[ -f "$RUNTIME_DIR/frontend.pid" ]]; then
  kill "$(cat "$RUNTIME_DIR/frontend.pid")" 2>/dev/null || true
  rm -f "$RUNTIME_DIR/frontend.pid"
fi

# Kill anything still on the ports
if command -v lsof &>/dev/null; then
  lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
  lsof -tiTCP:3000 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
else
  # Windows fallback via PowerShell
  powershell.exe -Command "
    @(3000,8000) | ForEach-Object {
      \$p = \$_
      (netstat -ano | Select-String \":\$p\s.*LISTENING\") -replace '.*\s+(\d+)\s*$','\$1' |
        Where-Object { \$_ -match '^\d+$' } |
        ForEach-Object { Stop-Process -Id \$_ -Force -ErrorAction SilentlyContinue }
    }
  " 2>/dev/null || true
fi

# ── Start servers ──
echo "Starting backend on :8000..."
nohup "$BACKEND_PYTHON" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload \
  >"$RUNTIME_DIR/backend.log" 2>&1 &
echo $! >"$RUNTIME_DIR/backend.pid"

echo "Starting frontend on :3000..."
nohup npm --prefix "$FRONTEND_DIR" run dev \
  >"$RUNTIME_DIR/frontend.log" 2>&1 &
echo $! >"$RUNTIME_DIR/frontend.pid"

echo "Waiting for servers to start..."
sleep 6

echo
echo "MVP started."
echo "Frontend: http://127.0.0.1:3000"
echo "Backend:  http://127.0.0.1:8000/health"
echo "Logs:     $RUNTIME_DIR/backend.log and $RUNTIME_DIR/frontend.log"
