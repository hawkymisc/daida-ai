#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "=== daida-ai setup ==="
echo "Project root: $PROJECT_ROOT"

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$PROJECT_ROOT[dev,voicevox]"

echo "=== Setup complete ==="
echo "Activate with: source $VENV_DIR/bin/activate"
