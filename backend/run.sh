#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/.venv/bin/uvicorn" ]; then
    exec "$SCRIPT_DIR/.venv/bin/uvicorn" app.main:app --reload --port 8000 "$@"
elif [ -f "$HOME/.local/bin/uvicorn" ]; then
    exec "$HOME/.local/bin/uvicorn" app.main:app --reload --port 8000 "$@"
else
    exec uvicorn app.main:app --reload --port 8000 "$@"
fi
