#!/usr/bin/env bash
# Wrapper: venv の Python でスクリプトを実行する
# Usage: bash run.sh <script_name.py> [args...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: venv not found. Run setup.sh first:" >&2
    echo "  bash $SCRIPT_DIR/setup.sh" >&2
    exit 1
fi

SCRIPT_NAME="$1"
shift
exec "$VENV_PYTHON" "$SCRIPT_DIR/$SCRIPT_NAME" "$@"
