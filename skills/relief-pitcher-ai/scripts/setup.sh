#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "=== relief-pitcher-ai setup ==="
echo "Project root: $PROJECT_ROOT"

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$PROJECT_ROOT[voicevox,svg]"

echo ""
echo "=== Base setup complete ==="

# ---------------------------------------------------------------------------
# Video generation tools (optional)
# ---------------------------------------------------------------------------
echo ""
echo "--- Video generation options ---"
echo "MP4 video generation requires additional tools (LibreOffice, ffmpeg, pdftoppm)."
echo ""

# Check current availability
LO_OK=false
FFMPEG_OK=false
PDFTOPPM_OK=false

if command -v libreoffice &>/dev/null; then
    LO_OK=true
    echo "  [OK] LibreOffice: $(libreoffice --version 2>/dev/null | head -1)"
else
    echo "  [--] LibreOffice: not installed"
fi

if command -v ffmpeg &>/dev/null; then
    FFMPEG_OK=true
    echo "  [OK] ffmpeg: $(ffmpeg -version 2>/dev/null | head -1)"
else
    echo "  [--] ffmpeg: not installed"
fi

if command -v pdftoppm &>/dev/null; then
    PDFTOPPM_OK=true
    echo "  [OK] pdftoppm: installed"
else
    echo "  [--] pdftoppm: not installed (ffmpeg can be used as fallback)"
fi

echo ""

if $LO_OK && $FFMPEG_OK; then
    echo "All required tools for video generation are installed."
    echo "Step 7 (make_video.py) is available."
else
    echo "To enable video generation, install the following tools:"
    echo ""
    if ! $LO_OK; then
        echo "  # LibreOffice (PPTX → PDF → PNG conversion)"
        echo "  sudo apt install libreoffice        # Ubuntu/Debian"
        echo "  brew install libreoffice             # macOS"
        echo ""
    fi
    if ! $FFMPEG_OK; then
        echo "  # ffmpeg (video composition)"
        echo "  sudo apt install ffmpeg              # Ubuntu/Debian"
        echo "  brew install ffmpeg                  # macOS"
        echo ""
    fi
    if ! $PDFTOPPM_OK; then
        echo "  # pdftoppm (PDF → PNG, recommended but ffmpeg can substitute)"
        echo "  sudo apt install poppler-utils       # Ubuntu/Debian"
        echo "  brew install poppler                 # macOS"
        echo ""
    fi
    echo "If you don't need video generation, you can safely skip this."
fi

echo ""
echo "=== Setup complete ==="
echo "Activate with: source $VENV_DIR/bin/activate"
