#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
BACKEND_DIR="$ROOT_DIR/services/game-api"
BACKEND_VENV_DIR="$BACKEND_DIR/.venv"
BACKEND_PYTHON="$BACKEND_VENV_DIR/bin/python"
API_PORT="${SUKUPOL_API_PORT:-8000}"
WEB_PORT="${SUKUPOL_WEB_PORT:-5173}"
API_BASE="${VITE_API_BASE:-http://127.0.0.1:$API_PORT}"

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "$command_name is required to launch the development stack." >&2
    exit 1
  fi
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "${web_pid:-}" ]] && kill -0 "$web_pid" 2>/dev/null; then
    kill "$web_pid" 2>/dev/null || true
  fi

  if [[ -n "${api_pid:-}" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
  fi

  wait "${web_pid:-}" "${api_pid:-}" 2>/dev/null || true
  exit "$exit_code"
}

require_command npm
require_command python3

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (
    cd "$WEB_DIR"
    npm install
  )
fi

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  echo "Creating backend virtual environment..."
  python3 -m venv "$BACKEND_VENV_DIR"
fi

if ! "$BACKEND_PYTHON" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "Installing backend dependencies..."
  (
    cd "$BACKEND_DIR"
    "$BACKEND_PYTHON" -m pip install -e .
  )
fi

trap cleanup EXIT INT TERM

echo "Starting backend on http://127.0.0.1:$API_PORT"
(
  cd "$BACKEND_DIR"
  "$BACKEND_PYTHON" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$API_PORT"
) &
api_pid=$!

echo "Starting frontend on http://127.0.0.1:$WEB_PORT"
(
  cd "$WEB_DIR"
  VITE_API_BASE="$API_BASE" npm run dev -- --host 0.0.0.0 --port "$WEB_PORT"
) &
web_pid=$!

echo "Frontend will use API base: $API_BASE"
echo "Press Ctrl+C to stop both processes."

wait -n "$api_pid" "$web_pid"