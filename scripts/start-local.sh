#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_NODE_BIN="$ROOT_DIR/.runtime/node-v22.23.2-darwin-arm64/bin"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID"
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID"
  fi
}

trap cleanup EXIT INT TERM

if [[ ! -x "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
  echo "Missing Python environment. Run: python3 -m venv .venv && .venv/bin/pip install -e backend[dev]"
  exit 1
fi

if [[ ! -x "$LOCAL_NODE_BIN/npm" ]]; then
  echo "Missing local Node runtime. Run: make node-install"
  exit 1
fi

echo "Applying database migrations..."
make -C "$ROOT_DIR" db-upgrade

echo "Starting backend at http://localhost:8000"
make -C "$ROOT_DIR" backend-dev &
BACKEND_PID="$!"

echo "Starting frontend at http://localhost:3000"
PATH="$LOCAL_NODE_BIN:$PATH" make -C "$ROOT_DIR" frontend-dev &
FRONTEND_PID="$!"

echo ""
echo "InvestorAgent is starting."
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "Press Ctrl+C to stop both services."

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    wait "$BACKEND_PID" || exit $?
    exit 0
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    wait "$FRONTEND_PID" || exit $?
    exit 0
  fi
  sleep 1
done
